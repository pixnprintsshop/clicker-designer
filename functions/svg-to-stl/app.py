"""
Cloud Run service: accepts an SVG URL, converts to STL with optional scale and thickness.
Uses OpenSCAD for import(), linear_extrude(), and STL export.
Preprocesses SVG to keep only the main (largest) path so small artifacts are not extruded.
Optional solid base from outer contour only (no holes), with smooth path sampling and buffer.
"""
import logging
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import urllib.request
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from shapely.geometry import Polygon as ShapelyPolygon
from svg.path import parse_path

log = logging.getLogger("svg-to-stl")

# OpenSCAD env: no display in containers
_OPENSCAD_ENV = {**os.environ, "DISPLAY": ""}
OPENSCAD_CMD = "openscad"
# Sample points along path to estimate bbox/area for filtering
_PATH_SAMPLE = 64
# Sample points for building polygon from path (exterior/base); higher = smoother curves
_PATH_POLY_SAMPLE = 256


def download_svg(url: str, path: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "clicker-designer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    svg = data.decode("utf-8", errors="replace")
    with open(path, "w") as f:
        f.write(svg)


def _normalize_svg(svg_str: str) -> str:
    """Replace currentColor so paths are visible in OpenSCAD."""
    return re.sub(r"currentColor", "#000000", svg_str, flags=re.IGNORECASE)


def _path_bbox_area(d: str) -> Optional[float]:
    """Approximate bounding-box area of an SVG path 'd' (for filtering by size)."""
    try:
        path = parse_path(d)
        if not path:
            return None
        xs, ys = [], []
        for i in range(_PATH_SAMPLE):
            p = path.point(i / _PATH_SAMPLE)
            xs.append(p.real)
            ys.append(-p.imag)
        if not xs:
            return None
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        return w * h
    except Exception:
        return None


def _svg_keep_largest_path_only(svg_path: str) -> None:
    """
    Rewrite the SVG file to contain only the single path with the largest bbox area.
    Removes small shapes (icons, dots, metadata paths) that would otherwise be extruded.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = "http://www.w3.org/2000/svg"

    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    paths_with_area = []
    for elem in root.iter():
        if strip_ns(elem.tag) != "path":
            continue
        d = elem.get("d")
        if not d or not d.strip():
            continue
        area = _path_bbox_area(d.strip())
        if area is not None and area > 0:
            paths_with_area.append((area, elem))

    if not paths_with_area:
        return
    if len(paths_with_area) == 1:
        return

    # Keep only the largest path
    paths_with_area.sort(key=lambda x: -x[0])
    _, keep_elem = paths_with_area[0]

    # Build a minimal SVG containing only the kept path (preserve viewBox/width/height)
    new_root = ET.Element("svg", xmlns=ns)
    if root.get("viewBox"):
        new_root.set("viewBox", root.get("viewBox"))
    if root.get("width"):
        new_root.set("width", root.get("width"))
    if root.get("height"):
        new_root.set("height", root.get("height"))

    # Copy the single path as a clean <path> element with same attributes
    new_path = ET.Element("path", keep_elem.attrib)
    new_root.append(new_path)

    tree = ET.ElementTree(new_root)
    ET.indent(tree, space=" ", level=0)
    tree.write(svg_path, encoding="unicode", method="xml")


def _path_d_to_polygon(d: str) -> Optional[ShapelyPolygon]:
    """Parse SVG path 'd' to a Shapely polygon in SVG coordinates (Y down)."""
    try:
        path = parse_path(d)
        if not path:
            return None
        points = []
        for i in range(_PATH_POLY_SAMPLE):
            p = path.point(i / _PATH_POLY_SAMPLE)
            points.append((p.real, p.imag))
        if points and points[0] != points[-1]:
            points.append(points[0])
        if len(points) < 4:
            return None
        poly = ShapelyPolygon(points)
        if poly.is_empty or not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return None
        return poly
    except Exception:
        return None


def _polygon_to_svg_path_d(poly: ShapelyPolygon) -> str:
    """Turn a polygon's exterior ring into an SVG path d string."""
    if poly.is_empty or not poly.exterior:
        return ""
    coords = list(poly.exterior.coords)
    if len(coords) < 2:
        return ""
    parts = [f"M {coords[0][0]},{coords[0][1]}"]
    for x, y in coords[1:]:
        parts.append(f"L {x},{y}")
    parts.append("Z")
    return " ".join(parts)


def _make_base_svg(main_svg_path: str, base_svg_path: str, offset: float) -> Tuple[float, float, float]:
    """
    Create an SVG containing only the outer contour of the main shape (no holes),
    expanded by `offset`. E.g. for "O" the base becomes a filled disk. Write to base_svg_path.
    Returns (centroid_x, centroid_y, width) in SVG coordinates for hole centering and size scaling.
    """
    tree = ET.parse(main_svg_path)
    root = tree.getroot()
    ns = "http://www.w3.org/2000/svg"

    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    path_d = None
    for elem in root.iter():
        if strip_ns(elem.tag) != "path":
            continue
        d = elem.get("d")
        if d and d.strip():
            path_d = d.strip()
            break

    if not path_d:
        raise ValueError("No path in main SVG to derive base from")

    poly = _path_d_to_polygon(path_d)
    if poly is None or poly.is_empty:
        raise ValueError("Could not parse main path as polygon")

    # If we got MultiPolygon/GeometryCollection, take the largest polygon part
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda p: p.area)
    elif poly.geom_type == "GeometryCollection":
        polys = [g for g in poly.geoms if g.geom_type == "Polygon"]
        if not polys:
            raise ValueError("No polygon geometry found for base")
        poly = max(polys, key=lambda p: p.area)

    # Exterior only: filled shape with no holes (e.g. "O" -> disk)
    exterior_only = ShapelyPolygon(poly.exterior.coords)
    if exterior_only.is_empty or not exterior_only.is_valid:
        exterior_only = exterior_only.buffer(0)
    # Expand/offset the outline (quad_segs = segments per quadrant for smooth rounding)
    buffered = exterior_only.buffer(offset, quad_segs=64)
    if buffered.is_empty:
        buffered = exterior_only

    # Buffer can yield MultiPolygon or Polygon; take largest if multiple
    if buffered.geom_type == "MultiPolygon":
        buffered = max(buffered.geoms, key=lambda p: p.area)
    elif buffered.geom_type == "GeometryCollection":
        polys = [g for g in buffered.geoms if g.geom_type == "Polygon"]
        if not polys:
            raise ValueError("Buffer produced no polygon")
        buffered = max(polys, key=lambda p: p.area)

    path_d_base = _polygon_to_svg_path_d(buffered)
    if not path_d_base:
        raise ValueError("Could not build base path")

    new_root = ET.Element("svg", xmlns=ns)
    if root.get("viewBox"):
        new_root.set("viewBox", root.get("viewBox"))
    if root.get("width"):
        new_root.set("width", root.get("width"))
    if root.get("height"):
        new_root.set("height", root.get("height"))
    path_elem = ET.Element("path", attrib={"d": path_d_base, "fill": "#000000"})
    new_root.append(path_elem)

    tree = ET.ElementTree(new_root)
    ET.indent(tree, space=" ", level=0)
    tree.write(base_svg_path, encoding="unicode", method="xml")
    cx, cy = buffered.centroid.x, buffered.centroid.y
    minx, _, maxx, _ = buffered.bounds
    width = float(maxx - minx) if maxx > minx else 1.0
    return (float(cx), float(cy), width)


def _get_shape_centroid_xy(svg_path: str) -> Tuple[float, float]:
    """Get centroid (x, y) in SVG coords of the single path in the SVG. For hole centering when no base."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    for elem in root.iter():
        if strip_ns(elem.tag) != "path":
            continue
        d = elem.get("d")
        if d and d.strip():
            poly = _path_d_to_polygon(d.strip())
            if poly is not None and not poly.is_empty:
                return (float(poly.centroid.x), float(poly.centroid.y))
            break
    return (0.0, 0.0)


def _get_shape_width(svg_path: str) -> float:
    """Get bounding-box width in SVG coords of the single path. For size (width) scaling."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    def strip_ns(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    for elem in root.iter():
        if strip_ns(elem.tag) != "path":
            continue
        d = elem.get("d")
        if d and d.strip():
            poly = _path_d_to_polygon(d.strip())
            if poly is not None and not poly.is_empty:
                minx, _, maxx, _ = poly.bounds
                return float(maxx - minx) if maxx > minx else 1.0
            break
    return 1.0


def _svg_to_stl_openscad(
    input_svg_path: str,
    output_stl_path: str,
    thickness: float = 1.0,
    scale_xy: float = 1.0,
    base_svg_path: Optional[str] = None,
    base_thickness: float = 0.0,
    hole_diameter: float = 0.0,
    flat_top_offset: float = 0.5,
    hole_center_xy: Optional[Tuple[float, float]] = None,
    hole_orientation: str = "horizontal",
) -> None:
    """
    Generate an OpenSCAD script: optional solid base, main shape, optional pass-through hole.
    scale_xy scales only XY (width/height); Z (depth) is unchanged. Hole at hole_center_xy.
    """
    main_name = os.path.basename(input_svg_path)
    total_height = base_thickness + thickness
    cx, cy = hole_center_xy if hole_center_xy else (0.0, 0.0)

    if base_svg_path and base_thickness > 0:
        base_name = os.path.basename(base_svg_path)
        bead_scad = f'''union() {{
  scale([{scale_xy}, {scale_xy}, 1]) {{
    linear_extrude(height={base_thickness}) import("{base_name}");
  }}
  translate([0, 0, {base_thickness}]) {{
    scale([{scale_xy}, {scale_xy}, 1]) {{
      linear_extrude(height={thickness}) import("{main_name}");
    }}
  }}
}}'''
    else:
        bead_scad = f'''scale([{scale_xy}, {scale_xy}, 1]) {{
  linear_extrude(height={thickness}) import("{main_name}");
}}'''

    if hole_diameter > 0 and total_height > 0:
        hole_radius = hole_diameter / 2
        # Center hole in Z on the base only (not the main/top shape)
        hole_center_z = (base_thickness / 2) if base_thickness > 0 else (thickness / 2)
        flat_ceiling_z = hole_center_z + hole_radius - flat_top_offset
        cylinder_length = 500
        # horizontal = cylinder along X (rotate 90° around Y); vertical = along Y (rotate 90° around X)
        if (hole_orientation or "horizontal").lower() == "vertical":
            hole_rotate = "rotate([90, 0, 0])"
        else:
            hole_rotate = "rotate([0, 90, 0])"
        scad_content = f'''// Generated for svg-to-stl (with pass-through hole, flat top for bridge)
difference() {{
  {bead_scad}
  // Flat-topped hole at base centroid; orientation = {hole_orientation or "horizontal"}
  intersection() {{
    translate([{scale_xy * cx}, {scale_xy * cy}, {hole_center_z}]) {hole_rotate}
      cylinder(h={cylinder_length}, r={hole_radius}, center=true, $fn=64);
    translate([0, 0, {flat_ceiling_z - 500}]) cube([1000, 1000, 500], center=false);
  }}
}}
'''
    else:
        scad_content = f'''// Generated for svg-to-stl\n{bead_scad}\n'''
    script_path = os.path.join(os.path.dirname(input_svg_path), "script.scad")
    with open(script_path, "w") as f:
        f.write(scad_content)

    # Run from the same directory so import() resolves
    cwd = os.path.dirname(input_svg_path)
    r = subprocess.run(
        [OPENSCAD_CMD, "-o", output_stl_path, os.path.basename(script_path)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=cwd,
        env=_OPENSCAD_ENV,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"OpenSCAD failed (exit {r.returncode}): {r.stderr or r.stdout or 'no output'}"
        )
    if not os.path.exists(output_stl_path) or os.path.getsize(output_stl_path) < 100:
        raise RuntimeError(
            f"OpenSCAD did not produce a valid STL: {r.stderr or r.stdout or 'no output'}"
        )


app = FastAPI(
    title="SVG to STL",
    description="Convert an SVG from URL to STL with optional scale and thickness (OpenSCAD).",
)

ALLOWED_ORIGINS = [
    "https://keychain-studio.pixnprints.shop",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "svg-to-stl",
        "engine": "OpenSCAD",
        "usage": "GET /convert?url=<svg_url>&size=<width>&thickness=<number>",
        "example": "GET /convert?url=https://example.com/icon.svg&size=50&thickness=2",
        "params": {
            "url": "URL of the SVG (required)",
            "size": "Target width in model units; aspect ratio kept, depth unchanged; 0 = no scaling (default 0)",
            "thickness": "Extrusion height of main shape (default 1.0)",
            "only_largest_path": "If true (default), keep only the largest path",
            "base_thickness": "Height of solid base under main shape; 0 = no base (default 0)",
            "base_offset": "Expand/offset of base outline in SVG units (default 2.0)",
            "hole_diameter": "Pass-through hole diameter in model units; 0 = no hole (default 0, range 2–12 typical)",
            "flat_top_offset": "Flat-top offset in model units: ceiling = dome_top - this (bridge-friendly); 0.1–2 typical",
            "hole_orientation": "Pass-through hole axis: 'horizontal' (X) or 'vertical' (Y)",
        },
    }


@app.get("/convert")
async def convert(
    url: str = Query(..., description="URL of the SVG to convert"),
    size: float = Query(
        0.0,
        ge=0.0,
        le=10000.0,
        description="Target width in model units; scales XY only (keeps aspect ratio), depth unchanged; 0 = no scaling",
    ),
    thickness: float = Query(1.0, ge=0.01, le=1000.0, description="Extrusion thickness of main shape"),
    only_largest_path: bool = Query(
        True,
        description="Keep only the largest path (removes small shapes); set false to extrude all paths",
    ),
    base_thickness: float = Query(
        0.0,
        ge=0.0,
        le=1000.0,
        description="Height of solid base (outer contour only, no holes); 0 = no base",
    ),
    base_offset: float = Query(
        2.0,
        ge=0.0,
        le=1000.0,
        description="Expand/offset of base outline in SVG units (makes base larger than main shape)",
    ),
    hole_diameter: float = Query(
        0.0,
        ge=0.0,
        le=100.0,
        description="Pass-through hole diameter (e.g. for cord) in model units; 0 = no hole; 2–12 typical for beads",
    ),
    flat_top_offset: float = Query(
        0.5,
        ge=0.1,
        le=10.0,
        description="Flat-top offset: hole ceiling is (dome top - this) for a printable bridge; 0.1–2 mm typical",
    ),
    hole_orientation: str = Query(
        "horizontal",
        description="Pass-through hole axis: 'horizontal' (cylinder along X) or 'vertical' (cylinder along Y)",
    ),
):
    """Download SVG from URL, convert to STL with OpenSCAD; optional base and pass-through hole with flat top."""
    if not url.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must be http or https")
    orient = (hole_orientation or "horizontal").lower()
    if orient not in ("horizontal", "vertical"):
        raise HTTPException(status_code=400, detail="hole_orientation must be 'horizontal' or 'vertical'")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_svg = os.path.join(tmpdir, "input.svg")
        output_stl = os.path.join(tmpdir, "output.stl")
        try:
            download_svg(url, input_svg)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch SVG: {e}")

        with open(input_svg) as f:
            normalized = _normalize_svg(f.read())
        with open(input_svg, "w") as f:
            f.write(normalized)

        if only_largest_path:
            _svg_keep_largest_path_only(input_svg)

        base_svg_path = None
        hole_center_xy = None
        shape_width = 1.0
        if base_thickness > 0:
            base_svg_path = os.path.join(tmpdir, "base.svg")
            try:
                cx, cy, shape_width = _make_base_svg(input_svg, base_svg_path, offset=base_offset)
                hole_center_xy = (cx, cy)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
        else:
            if hole_diameter > 0:
                hole_center_xy = _get_shape_centroid_xy(input_svg)
            if size > 0:
                shape_width = _get_shape_width(input_svg)

        # size = target width; scale XY only (aspect ratio kept), depth unchanged
        scale_xy = (size / shape_width) if size > 0 and shape_width > 0 else 1.0

        try:
            _svg_to_stl_openscad(
                input_svg,
                output_stl,
                thickness=thickness,
                scale_xy=scale_xy,
                base_svg_path=base_svg_path,
                base_thickness=base_thickness,
                hole_diameter=hole_diameter,
                flat_top_offset=flat_top_offset,
                hole_center_xy=hole_center_xy,
                hole_orientation=orient,
            )
        except RuntimeError as e:
            log.exception("OpenSCAD conversion failed")
            raise HTTPException(status_code=500, detail=str(e))

        with open(output_stl, "rb") as f:
            stl_bytes = f.read()

    return Response(
        content=stl_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=output.stl"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
