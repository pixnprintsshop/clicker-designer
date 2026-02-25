"""
Cloud Run service: accepts an SVG icon URL, runs the mask pipeline, returns output SVG.
Each disconnected shape becomes its own <path> for proper Three.js extrusion.
"""
import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from process_mask import run_components

log = logging.getLogger("svg-processor")

# Inkscape env: disable dbus and GUI to prevent intermittent hangs in containers
_INKSCAPE_ENV = {
    **os.environ,
    "DBUS_SESSION_BUS_ADDRESS": "",
    "DISPLAY": "",
    "HOME": "/tmp",
}

MAX_RETRIES = 3


def download_svg(url: str, path: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "clicker-designer/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(path, "wb") as f:
        f.write(data)


def _rasterize(input_svg: str, output_png: str) -> None:
    """Rasterize SVG to PNG with retry — Inkscape can be flaky in containers."""
    for attempt in range(1, MAX_RETRIES + 1):
        # Remove stale output from previous attempt
        if os.path.exists(output_png):
            os.remove(output_png)

        r = subprocess.run(
            [
                "inkscape", input_svg,
                "--export-type=png",
                f"--export-filename={output_png}",
                "--export-dpi=1200",
                "--export-background=white",
                "--export-area-drawing",
            ],
            capture_output=True, text=True, timeout=60,
            env=_INKSCAPE_ENV,
        )

        if r.returncode != 0:
            log.warning("Inkscape attempt %d failed (rc=%d): %s",
                        attempt, r.returncode, r.stderr or r.stdout)
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Inkscape failed after {MAX_RETRIES} attempts: {r.stderr or r.stdout}")
            time.sleep(0.5)
            continue

        if not os.path.exists(output_png) or os.path.getsize(output_png) < 100:
            log.warning("Inkscape attempt %d produced empty/missing PNG (%s)",
                        attempt, output_png)
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Inkscape produced empty output after {MAX_RETRIES} attempts"
                )
            time.sleep(0.5)
            continue

        log.info("Inkscape succeeded on attempt %d, PNG size: %d bytes",
                 attempt, os.path.getsize(output_png))
        return

    raise RuntimeError("Inkscape rasterization failed")


def _trace(pbm_path: str, svg_path: str) -> None:
    r = subprocess.run(
        [
            "potrace", pbm_path, "-s", "-o", svg_path,
            "--blacklevel", "0.5",
            "--turdsize", "10",
            "--alphamax", "1.334",
            "--opttolerance", "0.1",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0:
        raise RuntimeError(f"Potrace failed: {r.stderr or r.stdout}")


_PATH_RE = re.compile(r'<path\s[^>]*d="([^"]+)"[^/]*/>', re.DOTALL)
_VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')
_WIDTH_RE = re.compile(r'width="([^"]+)"')
_HEIGHT_RE = re.compile(r'height="([^"]+)"')
_TRANSFORM_RE = re.compile(r'<g\s+transform="([^"]+)"')


def _extract_paths(svg_text: str) -> list[str]:
    """Pull all path `d` attributes from a potrace SVG."""
    return _PATH_RE.findall(svg_text)


def _extract_svg_meta(svg_text: str) -> dict:
    """Extract viewBox, dimensions, and group transform from potrace SVG."""
    meta = {}
    m = _VIEWBOX_RE.search(svg_text)
    if m:
        meta["viewBox"] = m.group(1)
    m = _WIDTH_RE.search(svg_text)
    if m:
        meta["width"] = m.group(1)
    m = _HEIGHT_RE.search(svg_text)
    if m:
        meta["height"] = m.group(1)
    m = _TRANSFORM_RE.search(svg_text)
    if m:
        meta["transform"] = m.group(1)
    return meta


def _build_merged_svg(meta: dict, path_ds: list[str]) -> str:
    """Build an SVG with each shape as a separate <path>."""
    width = meta.get("width", "400.000000pt")
    height = meta.get("height", "400.000000pt")
    viewbox = meta.get("viewBox", "0 0 400.000000 400.000000")
    transform = meta.get("transform", "")

    paths = "\n".join(
        f'<path d="{d}" fill="#000000" stroke="none"/>' for d in path_ds
    )
    transform_attr = f' transform="{transform}"' if transform else ""
    return (
        '<?xml version="1.0" standalone="no"?>\n'
        '<svg version="1.0" xmlns="http://www.w3.org/2000/svg"\n'
        f' width="{width}" height="{height}"\n'
        f' viewBox="{viewbox}"\n'
        ' preserveAspectRatio="xMidYMid meet">\n'
        f'<g{transform_attr}>\n'
        f'{paths}\n'
        '</g>\n'
        '</svg>\n'
    )


def run_pipeline(input_svg_path: str, output_svg_path: str) -> None:
    """
    Inkscape → split mask by component → Potrace each → merge <path> elements.
    """
    tmpdir = os.path.dirname(input_svg_path)
    temp_png = os.path.join(tmpdir, "__temp_raster.png")
    components_dir = os.path.join(tmpdir, "components")
    os.makedirs(components_dir, exist_ok=True)

    try:
        _rasterize(input_svg_path, temp_png)

        png_size = os.path.getsize(temp_png)
        log.info("PNG rasterized: %d bytes", png_size)

        pbm_paths = run_components(temp_png, components_dir)
        log.info("Found %d components", len(pbm_paths))

        if not pbm_paths:
            raise RuntimeError(
                f"No shapes found in image (PNG was {png_size} bytes). "
                "The SVG may use currentColor or have no visible strokes/fills."
            )

        all_path_ds: list[str] = []
        meta: dict = {}

        for pbm_path in pbm_paths:
            svg_path = pbm_path.replace(".pbm", ".svg")
            _trace(pbm_path, svg_path)
            with open(svg_path) as f:
                svg_text = f.read()
            if not meta:
                meta = _extract_svg_meta(svg_text)
            all_path_ds.extend(_extract_paths(svg_text))

        log.info("Traced %d total paths", len(all_path_ds))
        merged = _build_merged_svg(meta, all_path_ds)
        with open(output_svg_path, "w") as f:
            f.write(merged)
    finally:
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
            except OSError:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    for cmd in ("inkscape", "potrace"):
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            raise RuntimeError(f"Required command not found: {cmd}")
    r = subprocess.run(
        ["inkscape", "--version"],
        capture_output=True, text=True, env=_INKSCAPE_ENV,
    )
    log.info("Inkscape version: %s", r.stdout.strip())
    yield


app = FastAPI(
    title="SVG Icon Processor",
    description="Fetch an SVG icon by URL, process through mask pipeline, return output SVG.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "svg-icon-processor",
        "usage": "GET /process?url=<svg_url>",
        "example": "GET /process?url=https://api.iconify.design/tabler:zodiac-leo.svg",
    }


@app.get("/process")
async def process(
    url: str = Query(..., description="URL of the SVG icon to process"),
):
    """Download SVG from URL, run pipeline, return output SVG."""
    if not url.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must be http or https")
    with tempfile.TemporaryDirectory() as tmpdir:
        input_svg = os.path.join(tmpdir, "input.svg")
        output_svg = os.path.join(tmpdir, "output.svg")
        try:
            download_svg(url, input_svg)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch SVG: {e}")
        try:
            run_pipeline(input_svg, output_svg)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        with open(output_svg, "rb") as f:
            svg_bytes = f.read()
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={"Content-Disposition": "inline; filename=output.svg"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
