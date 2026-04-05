<script lang="ts">
    import { get } from "svelte/store";
    import { T, useLoader, useThrelte } from "@threlte/core";
    import { Grid, OrbitControls } from "@threlte/extras";
    import {
        Box3,
        BufferGeometry,
        Color,
        DoubleSide,
        ExtrudeGeometry,
        Group,
        Mesh,
        MeshBasicMaterial,
        Object3D,
        PerspectiveCamera,
        Raycaster,
        Scene,
        type Scene as ThreeScene,
        SRGBColorSpace,
        Vector3,
        type WebGLRenderer,
        WebGLRenderTarget,
    } from "three";
    import { TextGeometry } from "three/addons/geometries/TextGeometry.js";
    import { FontLoader } from "three/addons/loaders/FontLoader.js";
    import { STLLoader } from "three/addons/loaders/STLLoader.js";
    import { SVGLoader } from "three/addons/loaders/SVGLoader.js";
    import * as BufferGeometryUtils from "three/addons/utils/BufferGeometryUtils.js";
    import { exportTo3MF } from "three-3mf-exporter";

    import {
        DEFAULT_KEYCAP_FONT_ID,
        getKeycapFontOption,
    } from "./keycapFonts";
    import borderStl from "../assets/stl/border.stl?url";
    import clicker1Stl from "../assets/stl/clicker_1.stl?url";
    import clicker2Stl from "../assets/stl/clicker_2.stl?url";
    import clicker3Stl from "../assets/stl/clicker_3.stl?url";
    import clicker4Stl from "../assets/stl/clicker_4.stl?url";
    import clicker5Stl from "../assets/stl/clicker_5.stl?url";
    import clicker6Stl from "../assets/stl/clicker_6.stl?url";
    import clicker7Stl from "../assets/stl/clicker_7.stl?url";
    import keycapStl from "../assets/stl/keycap.stl?url";
    import { KEYCAP_POSITIONS } from "./keycapPositions.js";

    const CLICKER_URLS = [
        clicker1Stl,
        clicker2Stl,
        clicker3Stl,
        clicker4Stl,
        clicker5Stl,
        clicker6Stl,
        clicker7Stl,
    ] as const;

    interface Props {
        objectColor?: string;
        keycapColor?: string;
        /** Shared color for keycap text labels and border. */
        textBorderColor?: string;
        /** Whether to show the border mesh on each keycap. */
        showBorder?: boolean;
        numberOfKeys?: number;
        /** Keycap positions in mm [x,y,z][] from sidebar controls; falls back to KEYCAP_POSITIONS when not provided. */
        keycapPositions?: [number, number, number][];
        /** One letter per keycap (shown on top of each keycap). */
        keycapLetters?: string[];
        /** Per-keycap SVG URL or null; when set, SVG is rendered instead of letter. */
        keycapSvgUrls?: (string | null)[];
        /** SVG size on keycap in mm (uniform width & height, aspect ratio kept). */
        keycapSvgSizeMm?: number;
        /** Three.js JSON typeface URL for keycap letters (from keycapFonts). */
        keycapTypefaceUrl?: string;
        /** Text label size in mm (for dev/debug). */
        textSizeMm?: number;
        /** Text Y offset in mm above keycap top (for dev/debug). */
        textYOffsetMm?: number;
        /** Human-readable names for snapshot footer (from palette or hex). */
        snapshotBaseColorLabel?: string;
        snapshotKeycapColorLabel?: string;
        snapshotLegendColorLabel?: string;
        /** Keycap letter font name for snapshot footer. */
        snapshotKeycapFontLabel?: string;
        /** Called with takeSnapshot() when scene is ready for snapshots. */
        snapshotReady?: (takeSnapshot: () => void) => void;
        /** Called after the snapshot file download has been triggered. */
        onSnapshotDownloaded?: () => void;
        /** Called with exportKeycap3mf(keycapIndex?) when scene is ready. All keys → one 3MF; optional index → single keycap. */
        exportKeycap3mfReady?: (
            exportKeycap3mf: (keycapIndex?: number) => Promise<void>,
        ) => void;
        /** Called after keycap 3MF download has been triggered. */
        onKeycap3mfDownloaded?: () => void;
    }
    let {
        objectColor = "#ec4899",
        keycapColor = "#6366f1",
        textBorderColor = "#1f2937",
        showBorder = true,
        numberOfKeys = 1,
        keycapPositions: keycapPositionsProp,
        keycapLetters = [],
        keycapSvgUrls = [],
        keycapSvgSizeMm = 10,
        keycapTypefaceUrl = getKeycapFontOption(DEFAULT_KEYCAP_FONT_ID)
            .typefaceUrl,
        textSizeMm = 8.7,
        snapshotBaseColorLabel = "",
        snapshotKeycapColorLabel = "",
        snapshotLegendColorLabel = "",
        snapshotKeycapFontLabel = "",
        snapshotReady,
        onSnapshotDownloaded,
        exportKeycap3mfReady,
        onKeycap3mfDownloaded,
    }: Props = $props();

    const threlte = useThrelte();
    const SNAPSHOT_SIZE = 1536;
    /** Extra height below front+top panels for color name legend. */
    const SNAPSHOT_COLOR_FOOTER_H = 268;
    const FOV_DEG = 45;
    /** Max size of a mesh's bbox to include in framing (exclude huge grid). */
    const MAX_MESH_SIZE = 150;

    /** Same gray background as live T.Scene. */
    const SNAPSHOT_BG = new Color("#d4d4d4");

    function captureView(
        renderer: WebGLRenderer,
        scene: ThreeScene,
        position: [number, number, number],
        target: [number, number, number],
    ): Uint8Array {
        const rt = new WebGLRenderTarget(SNAPSHOT_SIZE, SNAPSHOT_SIZE);
        rt.texture.colorSpace = SRGBColorSpace;
        const cam = new PerspectiveCamera(FOV_DEG, 1, 1, 2000);
        cam.position.set(...position);
        cam.lookAt(target[0], target[1], target[2]);
        cam.updateMatrixWorld(true);
        scene.updateMatrixWorld(true);
        const prevClearColor = renderer.getClearColor(new Color());
        const prevClearAlpha = renderer.getClearAlpha();
        renderer.setClearColor(
            scene.background instanceof Color ? scene.background : SNAPSHOT_BG,
        );
        renderer.setClearAlpha(1);
        renderer.setRenderTarget(rt);
        renderer.clear();
        renderer.render(scene, cam);
        const pixels = new Uint8Array(SNAPSHOT_SIZE * SNAPSHOT_SIZE * 4);
        renderer.readRenderTargetPixels(
            rt,
            0,
            0,
            SNAPSHOT_SIZE,
            SNAPSHOT_SIZE,
            pixels,
        );
        renderer.setRenderTarget(null);
        renderer.setClearColor(prevClearColor);
        renderer.setClearAlpha(prevClearAlpha);
        rt.dispose();
        return pixels;
    }

    function pixelsToDataUrl(
        pixels: Uint8Array,
        width: number,
        height: number,
    ): string {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) return "";
        const imageData = ctx.createImageData(width, height);
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const src = (height - 1 - y) * width * 4 + x * 4;
                const dst = y * width * 4 + x * 4;
                imageData.data[dst] = pixels[src];
                imageData.data[dst + 1] = pixels[src + 1];
                imageData.data[dst + 2] = pixels[src + 2];
                imageData.data[dst + 3] = pixels[src + 3];
            }
        }
        ctx.putImageData(imageData, 0, 0);
        return canvas.toDataURL("image/png");
    }

    /** Compute bounding box of model meshes (exclude grid and other huge geometry). */
    function getModelBox(scene: ThreeScene): {
        center: Vector3;
        size: Vector3;
        maxDim: number;
    } {
        const box = new Box3();
        scene.traverse((obj) => {
            if (obj instanceof Mesh && obj.geometry) {
                obj.geometry.computeBoundingBox();
                const geomBox = obj.geometry.boundingBox;
                if (!geomBox) return;
                const dim = Math.max(
                    geomBox.max.x - geomBox.min.x,
                    geomBox.max.y - geomBox.min.y,
                    geomBox.max.z - geomBox.min.z,
                );
                if (dim > MAX_MESH_SIZE) return;
                obj.updateMatrixWorld(true);
                const worldBox = geomBox.clone().applyMatrix4(obj.matrixWorld);
                box.union(worldBox);
            }
        });
        const center = new Vector3();
        const size = new Vector3();
        box.getCenter(center);
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z) || 80;
        return { center, size, maxDim };
    }

    /** Camera distance so the whole model fits in view (fov in deg). */
    function distanceToFit(
        maxDim: number,
        fovDeg: number,
        margin = 1.4,
    ): number {
        const halfFovRad = (fovDeg / 2) * (Math.PI / 180);
        return (maxDim / 2 / Math.tan(halfFovRad)) * margin;
    }

    function takeSnapshot(): void {
        const renderer = threlte.renderer;
        const scene = threlte.scene;
        const camera = threlte.camera;
        if (!renderer || !scene || !camera) return;

        const { center, maxDim } = getModelBox(scene);
        const cx = center.x;
        const cy = center.y;
        const cz = center.z;
        const dist = distanceToFit(maxDim, FOV_DEG);

        const frontPixels = captureView(
            renderer,
            scene,
            [cx, cy, cz + dist],
            [cx, cy, cz],
        );
        const topPixels = captureView(
            renderer,
            scene,
            [cx, cy + dist, cz],
            [cx, cy, cz],
        );

        const frontDataUrl = pixelsToDataUrl(
            frontPixels,
            SNAPSHOT_SIZE,
            SNAPSHOT_SIZE,
        );
        const topDataUrl = pixelsToDataUrl(
            topPixels,
            SNAPSHOT_SIZE,
            SNAPSHOT_SIZE,
        );

        const composite = document.createElement("canvas");
        composite.width = SNAPSHOT_SIZE;
        composite.height = SNAPSHOT_SIZE * 2 + SNAPSHOT_COLOR_FOOTER_H;
        const ctx = composite.getContext("2d");
        if (!ctx) return;
        const frontImg = new Image();
        frontImg.onload = () => {
            ctx.drawImage(frontImg, 0, 0, SNAPSHOT_SIZE, SNAPSHOT_SIZE);
            const topImg = new Image();
            topImg.onload = () => {
                ctx.drawImage(
                    topImg,
                    0,
                    SNAPSHOT_SIZE,
                    SNAPSHOT_SIZE,
                    SNAPSHOT_SIZE,
                );

                const footerY = SNAPSHOT_SIZE * 2;
                ctx.fillStyle = "#f1f5f9";
                ctx.fillRect(0, footerY, SNAPSHOT_SIZE, SNAPSHOT_COLOR_FOOTER_H);
                ctx.strokeStyle = "#cbd5e1";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, footerY + 0.5);
                ctx.lineTo(SNAPSHOT_SIZE, footerY + 0.5);
                ctx.stroke();

                const rows: {
                    title: string;
                    name: string;
                    swatch: string;
                }[] = [
                    {
                        title: "Base",
                        name: snapshotBaseColorLabel || objectColor,
                        swatch: objectColor,
                    },
                    {
                        title: "Keycaps",
                        name: snapshotKeycapColorLabel || keycapColor,
                        swatch: keycapColor,
                    },
                    {
                        title: "Legend",
                        name: snapshotLegendColorLabel || textBorderColor,
                        swatch: textBorderColor,
                    },
                ];
                const colW = SNAPSHOT_SIZE / 3;
                const sw = 52;
                const sh = 52;
                const textY = footerY + 132;
                ctx.textBaseline = "middle";
                ctx.font = "600 42px system-ui, -apple-system, sans-serif";
                for (let i = 0; i < rows.length; i++) {
                    const { title, name, swatch } = rows[i]!;
                    const colX = i * colW + 22;
                    ctx.fillStyle = swatch;
                    ctx.fillRect(colX, textY - sh / 2, sw, sh);
                    ctx.strokeStyle = "#94a3b8";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(colX, textY - sh / 2, sw, sh);
                    ctx.lineWidth = 1;
                    ctx.fillStyle = "#0f172a";
                    const line = `${title}: ${name}`;
                    ctx.fillText(line, colX + sw + 16, textY);
                }
                ctx.fillStyle = "#64748b";
                ctx.font = "600 34px system-ui, -apple-system, sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("Colors", SNAPSHOT_SIZE / 2, footerY + 44);
                ctx.fillStyle = "#0f172a";
                ctx.font = "600 40px system-ui, -apple-system, sans-serif";
                ctx.fillText(
                    `Letter font: ${snapshotKeycapFontLabel || "—"}`,
                    SNAPSHOT_SIZE / 2,
                    footerY + SNAPSHOT_COLOR_FOOTER_H - 40,
                );
                ctx.textAlign = "left";

                const dataUrl = composite.toDataURL("image/png");
                const a = document.createElement("a");
                a.download = `clicker-snapshot-${Date.now()}.png`;
                a.href = dataUrl;
                a.click();
                onSnapshotDownloaded?.();
            };
            topImg.src = topDataUrl;
        };
        frontImg.src = frontDataUrl;
    }

    $effect(() => {
        if (threlte.renderer && threlte.scene && threlte.camera) {
            snapshotReady?.(takeSnapshot);
        }
    });

    const MESH_NAME_KEYCAP = "keycap";
    const MESH_NAME_BORDER = "border";
    const MESH_NAME_LEGEND = "legend";

    /**
     * After keycap mesh position + uniform scale + rotation.x = -π/2, local +Z maps to world +Y.
     * Top surface world Y is mesh Y plus scaled local maxZ (not bottom + (maxZ−minZ) unless minZ === 0).
     */
    function keycapTopWorldY(
        keycapMeshY: number,
        keycapLocalMaxZ: number,
        scaleMm: number,
    ): number {
        return keycapMeshY + keycapLocalMaxZ * scaleMm;
    }

    /**
     * World position of the keycap bbox top-center: local (center.x, center.y, maxZ) after the same
     * transform as the keycap mesh (uniform scale + rotation.x = −π/2 maps (lx,ly,lz) → (lx, lz, −ly) in parent space).
     * Legends must use this, not the mesh pivot kp alone — kp is offset by (−cx, +cy) in X/Z.
     */
    function keycapLegendAnchorWorld(
        kp: [number, number, number],
        center: [number, number, number],
        maxZ: number,
        scaleMm: number,
    ): [number, number, number] {
        const [cx, cy] = center;
        const s = scaleMm;
        return [
            kp[0] + s * cx,
            keycapTopWorldY(kp[1], maxZ, s),
            kp[2] - s * cy,
        ];
    }

    /**
     * World anchor per keycap: ray (+Y → −Y) through layout center hits the actual outer surface (domes, STLs).
     * Bbox (cx, cy, maxZ) is not guaranteed to lie on the mesh, so analytical Y can sit wrong vs the visible top.
     */
    function computeKeycapLegendAnchorsWorld(
        geom: BufferGeometry,
        center: [number, number, number],
        maxZ: number,
        kpos: [number, number, number][],
        scaleMm: number,
    ): [number, number, number][] {
        if (!kpos.length) return [];
        const g = geom.clone();
        const mat = new MeshBasicMaterial({ side: DoubleSide });
        const mesh = new Mesh(g, mat);
        mesh.scale.setScalar(scaleMm);
        mesh.rotation.x = -Math.PI / 2;

        const raycaster = new Raycaster();
        const rayOrigin = new Vector3();
        const down = new Vector3(0, -1, 0);
        const out: [number, number, number][] = [];

        for (let i = 0; i < kpos.length; i++) {
            const kp = kpos[i]!;
            const ax = kp[0] + scaleMm * center[0];
            const az = kp[2] - scaleMm * center[1];
            mesh.position.set(kp[0], kp[1], kp[2]);
            mesh.updateMatrixWorld(true);

            rayOrigin.set(ax, 1e6, az);
            raycaster.set(rayOrigin, down);
            const hits = raycaster.intersectObject(mesh, false);
            const topY =
                hits.length > 0
                    ? hits[0]!.point.y
                    : keycapTopWorldY(kp[1], maxZ, scaleMm);
            out.push([ax, topY, az]);
        }

        g.dispose();
        mat.dispose();
        return out;
    }

    /**
     * Z-up assembly root for keycap i (keycap + optional border + legend). Caller disposes mesh geometries when done.
     */
    function buildKeycapAssemblyRootGroup(i: number): Group | null {
        const keycapGeom = get(keycapGeometryStore);
        const borderGeom = get(borderGeometryStore);
        if (!keycapGeom) return null;
        const positions = keycapMeshPositions;
        const borderPositions = borderMeshPositions;
        if (i >= positions.length) return null;

        const scaleMm = FILE_TO_MM;
        const textScaleXY = textSizeMm * scaleMm;
        const textScaleZ = textSizeMm * scaleMm;
        const legendDepthScaleZ = LEGEND_DEPTH_MM * scaleMm;

        const group = new Group();
        const keycapMesh = new Mesh(keycapGeom.clone());
        keycapMesh.name = MESH_NAME_KEYCAP;
        keycapMesh.position.set(
            positions[i][0],
            positions[i][1],
            positions[i][2],
        );
        keycapMesh.scale.setScalar(scaleMm);
        keycapMesh.rotation.x = -Math.PI / 2;
        group.add(keycapMesh);
        if (showBorder && borderGeom && i < borderPositions.length) {
            borderGeom.computeBoundingBox();
            const bBox = borderGeom.boundingBox;
            const zSpan = bBox
                ? Math.max(bBox.max.z - bBox.min.z, 1e-6)
                : 1;
            const borderSz = BORDER_HEIGHT_MM / zSpan;
            const borderMesh = new Mesh(borderGeom.clone());
            borderMesh.name = MESH_NAME_BORDER;
            borderMesh.position.set(
                borderPositions[i][0],
                borderPositions[i][1],
                borderPositions[i][2],
            );
            borderMesh.scale.set(scaleMm, scaleMm, borderSz);
            borderMesh.rotation.x = -Math.PI / 2;
            group.add(borderMesh);
        }
        const letter = keycapLetters[i]?.trim();
        const svgUrl = keycapSvgUrls[i]?.trim();
        const needsLegend =
            (!!svgUrl && !!svgGeometryByUrl[svgUrl]) ||
            (!!letter && !!font);
        const legendAnchors = needsLegend
            ? computeKeycapLegendAnchorsWorld(
                  keycapGeom,
                  keycapOffset.center,
                  keycapOffset.maxZ,
                  positions,
                  scaleMm,
              )
            : null;
        if (svgUrl && svgGeometryByUrl[svgUrl] && legendAnchors) {
            const slotPos = legendAnchors[i]!;
            const svgMesh = new Mesh(svgGeometryByUrl[svgUrl].clone());
            svgMesh.name = MESH_NAME_LEGEND;
            svgMesh.position.set(slotPos[0], slotPos[1], slotPos[2]);
            svgMesh.scale.set(
                keycapSvgSizeMm * scaleMm,
                keycapSvgSizeMm * scaleMm,
                legendDepthScaleZ,
            );
            svgMesh.rotation.x = -Math.PI / 2;
            group.add(svgMesh);
        } else if (letter && font && legendAnchors) {
            const geom = new TextGeometry(
                letter.toUpperCase().slice(0, 1),
                {
                    font,
                    size: 1,
                    depth: LEGEND_DEPTH_MM / textSizeMm,
                    curveSegments: 6,
                    bevelEnabled: false,
                },
            );
            geom.computeBoundingBox();
            const box = geom.boundingBox;
            if (box) {
                const center = new Vector3();
                box.getCenter(center);
                geom.translate(-center.x, -center.y, -box.min.z);
            }
            const [lx, ly, lz] = legendAnchors[i]!;
            const textMesh = new Mesh(geom);
            textMesh.name = MESH_NAME_LEGEND;
            textMesh.position.set(lx, ly, lz);
            textMesh.scale.set(textScaleXY, textScaleXY, textScaleZ);
            textMesh.rotation.x = -Math.PI / 2;
            group.add(textMesh);
        }
        group.updateMatrixWorld(true);
        const root = new Group();
        root.rotation.x = Math.PI / 2;
        root.add(group);
        root.updateMatrixWorld(true);
        return root;
    }

    function disposeAssemblyRootGeometries(root: Group): void {
        root.traverse((obj) => {
            if (obj instanceof Mesh && obj.geometry) obj.geometry.dispose();
        });
    }

    /**
     * Flat group of meshes with world-space geometry and MeshBasicMaterial (three-3mf-exporter expects this pattern).
     */
    function bakeAssemblyRootTo3mfGroup(root: Group): Group {
        root.updateMatrixWorld(true);
        const exportGroup = new Group();
        const cKeycap = new Color(keycapColor);
        const cLegend = new Color(textBorderColor);

        root.traverse((obj) => {
            if (!(obj instanceof Mesh)) return;
            const gWorld = obj.geometry.clone();
            gWorld.applyMatrix4(obj.matrixWorld);
            const g = gWorld.toNonIndexed();
            if (g !== gWorld) gWorld.dispose();
            for (const name of Object.keys(g.attributes)) {
                if (name !== "position") g.deleteAttribute(name);
            }
            if (g.index) g.setIndex(null);

            const color =
                obj.name === MESH_NAME_KEYCAP
                    ? cKeycap
                    : cLegend;
            const mat = new MeshBasicMaterial({ color });
            const m = new Mesh(g, mat);
            m.name = obj.name || "part";
            exportGroup.add(m);
        });

        exportGroup.updateMatrixWorld(true);
        return exportGroup;
    }

    function dispose3mfExportGroup(group: Object3D): void {
        group.traverse((obj) => {
            if (obj instanceof Mesh) {
                obj.geometry?.dispose();
                const mat = obj.material;
                if (Array.isArray(mat)) {
                    for (const m of mat) m.dispose();
                } else {
                    mat?.dispose();
                }
            }
        });
    }

    /**
     * Pass a Scene when exporting multiple top-level objects: three-3mf-exporter only
     * iterates `object.children` when `object.type === "Scene"`; a Group wrapper becomes a single merged assembly.
     */
    async function download3mfFromRoot(
        root: Object3D,
        filename: string,
    ): Promise<void> {
        root.updateMatrixWorld(true);
        const blob = await exportTo3MF(root, {
            metadata: {
                Application: "Clicker Designer",
                ApplicationTitle: "Clicker Designer keycap",
            },
        });
        dispose3mfExportGroup(root);
        if (!blob || blob.size === 0) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    /**
     * Export one or all keycaps as 3MF (Group + MeshBasicMaterial + baked transforms; matches three-3mf-exporter expectations).
     */
    async function exportKeycap3mf(keycapIndex?: number) {
        const keycapGeom = get(keycapGeometryStore);
        if (!keycapGeom) return;
        const positions = keycapMeshPositions;
        const indices =
            keycapIndex !== undefined
                ? [keycapIndex]
                : positions.map((_, i) => i);

        const exportOne = async (i: number) => {
            const root = buildKeycapAssemblyRootGroup(i);
            if (!root) return;
            const exportGroup = bakeAssemblyRootTo3mfGroup(root);
            exportGroup.name = `Keycap ${i + 1}`;
            disposeAssemblyRootGeometries(root);
            const letter = keycapLetters[i]?.trim();
            const svgUrl = keycapSvgUrls[i]?.trim();
            const name =
                letter && !svgUrl
                    ? `keycap-${i + 1}-${letter.toUpperCase()}.3mf`
                    : `keycap-${i + 1}.3mf`;
            await download3mfFromRoot(exportGroup, name);
        };

        if (keycapIndex !== undefined) {
            await exportOne(keycapIndex);
        } else if (indices.length <= 1) {
            if (indices.length === 1) await exportOne(indices[0]!);
        } else {
            const exportScene = new Scene();
            for (const i of indices) {
                if (i >= positions.length) continue;
                const root = buildKeycapAssemblyRootGroup(i);
                if (!root) continue;
                const part = bakeAssemblyRootTo3mfGroup(root);
                disposeAssemblyRootGeometries(root);
                part.name = `Keycap ${i + 1}`;
                exportScene.add(part);
            }
            if (exportScene.children.length === 0) {
                onKeycap3mfDownloaded?.();
                return;
            }
            exportScene.updateMatrixWorld(true);
            await download3mfFromRoot(
                exportScene,
                `clicker-${numberOfKeys}-keycaps.3mf`,
            );
        }
        onKeycap3mfDownloaded?.();
    }

    $effect(() => {
        // Subscribe reactively so we run again when the loader finishes
        const keycapGeom = $keycapGeometryStore;
        if (keycapGeom) {
            exportKeycap3mfReady?.(exportKeycap3mf);
        }
    });

    /** Scene units = mm (1 unit = 1 mm). Source meshes; if in meters, use 1000. */
    const FILE_TO_MM = 1;

    /** Border ring thickness in world mm (local Z of border STL → world Y after rotation.x = -π/2). */
    const BORDER_HEIGHT_MM = 0.8;

    /** Legend extrusion height in mm (text depth × Z scale, SVG mesh scale Z). */
    const LEGEND_DEPTH_MM = 1;

    /** Extrusion depth for SVG geometry (before normalize); normalized depth becomes 1. */
    const SVG_EXTRUDE_DEPTH = 2;

    const { load } = useLoader(STLLoader);
    const geometryStores = $derived(CLICKER_URLS.map((url) => load(url)));
    const keyIndex = $derived(Math.min(7, Math.max(1, numberOfKeys)) - 1);
    const currentGeometryStore = $derived(geometryStores[keyIndex]);
    const stlGeometry = $derived(currentGeometryStore);

    const keycapGeometryStore = load(keycapStl);
    const borderGeometryStore = load(borderStl);
    const keycapPositions = $derived(
        keycapPositionsProp?.length
            ? keycapPositionsProp
            : (KEYCAP_POSITIONS[keyIndex] ?? []),
    );

    /**
     * Position so object is centered in XZ and sits on the grid (y=0).
     * With rotation.x = -π/2 (Tinkercad Z-up → Y-up), geometry's Z becomes world Y,
     * so bottom is at geometry's min Z; center in XZ from (center.x, -center.y).
     */
    const meshPosition = $derived.by((): [number, number, number] => {
        const geom = $stlGeometry;
        if (!geom) return [0, 0, 0];
        geom.computeBoundingBox();
        const box = geom.boundingBox;
        if (!box) return [0, 0, 0];
        const center = new Vector3();
        box.getCenter(center);
        // After -90° X: world Y = local Z, world Z = -local Y
        return [-center.x, -box.min.z, center.y];
    });

    /** Clicker top Y in world (so keycaps sit on it by default). After -90° X, local Z = world Y. */
    const clickerTopY = $derived.by(() => {
        const geom = $stlGeometry;
        if (!geom) return 0;
        geom.computeBoundingBox();
        const box = geom.boundingBox;
        if (!box) return 0;
        return meshPosition[1] + box.max.z;
    });

    /** Keycap bbox center, minZ and maxZ for centering and placing bottom/top. Same rotation as clicker. */
    const keycapOffset = $derived.by(
        (): {
            center: [number, number, number];
            minZ: number;
            maxZ: number;
        } => {
            const geom = $keycapGeometryStore;
            if (!geom) return { center: [0, 0, 0], minZ: 0, maxZ: 0 };
            geom.computeBoundingBox();
            const box = geom.boundingBox;
            if (!box) return { center: [0, 0, 0], minZ: 0, maxZ: 0 };
            const center = new Vector3();
            box.getCenter(center);
            return {
                center: [center.x, center.y, center.z],
                minZ: box.min.z,
                maxZ: box.max.z,
            };
        },
    );

    /** Final keycap mesh positions: centered at (pos[0], clickerTopY + pos[1], pos[2]), bottom on clicker when pos[1]=0. */
    const keycapMeshPositions = $derived.by((): [number, number, number][] => {
        const offset = keycapOffset;
        const topY = clickerTopY;
        return keycapPositions.map(([x, y, z]) => [
            x - offset.center[0],
            topY + y - offset.minZ,
            z + offset.center[1],
        ]);
    });

    /** Border bbox for centering and placing on keycap top (same Z-up convention, -90° X). */
    const borderOffset = $derived.by(
        (): {
            center: [number, number, number];
            minZ: number;
            maxZ: number;
        } => {
            const geom = $borderGeometryStore;
            if (!geom) return { center: [0, 0, 0], minZ: 0, maxZ: 0 };
            geom.computeBoundingBox();
            const box = geom.boundingBox;
            if (!box) return { center: [0, 0, 0], minZ: 0, maxZ: 0 };
            const center = new Vector3();
            box.getCenter(center);
            return {
                center: [center.x, center.y, center.z],
                minZ: box.min.z,
                maxZ: box.max.z,
            };
        },
    );

    /** XY = file units → mm; Z = squash/stretch so border is exactly BORDER_HEIGHT_MM tall in world Y. */
    const borderMeshScale = $derived.by((): [number, number, number] => {
        const b = borderOffset;
        const zSpan = Math.max(b.maxZ - b.minZ, 1e-6);
        const sz = BORDER_HEIGHT_MM / zSpan;
        return [FILE_TO_MM, FILE_TO_MM, sz];
    });
    /** Border mesh positions: bottom of border (local minZ) on keycap top surface world Y. */
    const borderMeshPositions = $derived.by((): [number, number, number][] => {
        const positions = keycapPositions;
        const offset = keycapOffset;
        const border = borderOffset;
        const topY = clickerTopY;
        const s = FILE_TO_MM;
        if (!positions?.length) return [];
        const [, , sz] = borderMeshScale;
        return positions.map(([x, y, z]) => {
            const keycapMeshY = topY + y - offset.minZ;
            const capTopY = keycapTopWorldY(keycapMeshY, offset.maxZ, s);
            const borderPosY = capTopY - border.minZ * sz;
            return [x - border.center[0], borderPosY, z + border.center[1]] as [
                number,
                number,
                number,
            ];
        });
    });

    /** Per-keycap world position for legends (raycast surface Y at layout center in XZ). */
    const keycapLegendAnchorsWorld = $derived.by((): [number, number, number][] => {
        const geom = $keycapGeometryStore;
        if (!geom) return [];
        return computeKeycapLegendAnchorsWorld(
            geom,
            keycapOffset.center,
            keycapOffset.maxZ,
            keycapMeshPositions,
            FILE_TO_MM,
        );
    });

    /** Font loaded async for keycap labels */
    let font = $state<ReturnType<FontLoader["parse"]> | null>(null);
    $effect(() => {
        const url = keycapTypefaceUrl;
        let cancelled = false;
        font = null;
        new FontLoader()
            .loadAsync(url)
            .then((f) => {
                if (!cancelled) font = f;
            })
            .catch(() => {
                if (!cancelled) font = null;
            });
        return () => {
            cancelled = true;
        };
    });

    /** Slots that show an SVG instead of text: position + url. Same position as keycap top center. */
    const keycapSvgSlots = $derived.by(
        (): { position: [number, number, number]; url: string }[] => {
            const urls = keycapSvgUrls;
            const mappedList = keycapPositions;
            const anchors = keycapLegendAnchorsWorld;
            if (!urls?.length || !mappedList?.length) return [];
            return mappedList
                .map((mapped, i) => {
                    const url = urls[i];
                    if (!mapped || !url?.trim()) return null;
                    const pos = anchors[i];
                    if (!pos) return null;
                    return {
                        position: pos,
                        url,
                    };
                })
                .filter(
                    (
                        x,
                    ): x is {
                        position: [number, number, number];
                        url: string;
                    } => x != null,
                );
        },
    );

    /** Load SVG URLs into extruded geometries (no background, shape only). */
    let svgGeometryByUrl = $state<
        Record<string, import("three").BufferGeometry>
    >({});
    $effect(() => {
        const urls = [
            ...new Set((keycapSvgUrls ?? []).filter((u): u is string => !!u)),
        ];
        const current = svgGeometryByUrl;
        urls.forEach((url) => {
            if (current[url]) return;
            fetch(url)
                .then((r) => r.text())
                .then((svgText) => {
                    const loader = new SVGLoader();
                    const data = loader.parse(svgText);
                    const geometries: import("three").BufferGeometry[] = [];
                    for (const path of data.paths) {
                        const shapes = SVGLoader.createShapes(path);
                        for (const shape of shapes) {
                            const geom = new ExtrudeGeometry(shape, {
                                depth: SVG_EXTRUDE_DEPTH,
                                bevelEnabled: false,
                            });
                            geometries.push(geom);
                        }
                    }
                    if (geometries.length === 0) return;
                    let merged =
                        geometries.length === 1
                            ? geometries[0]
                            : BufferGeometryUtils.mergeGeometries(geometries);
                    if (!merged) return;
                    for (const g of geometries) if (g !== merged) g.dispose();
                    merged.computeBoundingBox();
                    let box = merged.boundingBox;
                    if (box) {
                        const center = new Vector3();
                        box.getCenter(center);
                        // Bottom of extrusion at z=0 (not centered in z), so legend sits on keycap without sinking in.
                        merged.translate(-center.x, -center.y, -box.min.z);
                        merged.computeBoundingBox();
                        box = merged.boundingBox;
                        if (box) {
                            const size = new Vector3();
                            box.getSize(size);
                            const maxDim = Math.max(
                                size.x,
                                size.y,
                                size.z,
                                0,
                            );
                            const scale = 1 / maxDim;
                            merged.scale(scale, scale, scale);
                            // Normalize depth to 1 so mesh scale Z = LEGEND_DEPTH_MM gives same height as letter
                            merged.computeBoundingBox();
                            box = merged.boundingBox;
                            // if (box) {
                            //     const zSize = box.max.z - box.min.z;
                            //     if (zSize > 0.001)
                            //         merged.scale(1, 1, 1 / zSize);
                            // }
                        }
                    }
                    svgGeometryByUrl = { ...svgGeometryByUrl, [url]: merged };
                })
                .catch(() => {});
        });
    });

    /** Per-keycap label: geometry (centered) and world position. Only for keys that do NOT have an SVG selected. */
    const keycapLabels = $derived.by(
        (): {
            geometry: InstanceType<typeof TextGeometry>;
            position: [number, number, number];
        }[] => {
            const f = font;
            const letters = keycapLetters;
            const urls = keycapSvgUrls;
            const mappedList = keycapPositions;
            const anchors = keycapLegendAnchorsWorld;
            if (!f || !letters?.length || !mappedList?.length) return [];
            return letters
                .map((letter, i) => {
                    if (urls?.[i]) return null;
                    const mapped = mappedList[i];
                    if (!mapped || !letter?.trim()) return null;
                    const pos = anchors[i];
                    if (!pos) return null;
                    const geom = new TextGeometry(
                        letter.toUpperCase().slice(0, 1),
                        {
                            font: f,
                            size: 1,
                            depth: LEGEND_DEPTH_MM / textSizeMm,
                            curveSegments: 6,
                            bevelEnabled: false,
                        },
                    );
                    geom.computeBoundingBox();
                    const box = geom.boundingBox;
                    if (box) {
                        const center = new Vector3();
                        box.getCenter(center);
                        geom.translate(-center.x, -center.y, -box.min.z);
                    }
                    return {
                        geometry: geom,
                        position: pos,
                    };
                })
                .filter((x): x is NonNullable<typeof x> => x != null);
        },
    );
</script>

<T.Scene background={new Color("#d4d4d4")}>
    <!-- Camera ~150 mm from origin; orbit target stays at origin so grid stays fixed. -->
    <T.PerspectiveCamera makeDefault position={[150, 150, 150]}>
        <OrbitControls target={[0, 0, 0]} minDistance={100} maxDistance={300} />
    </T.PerspectiveCamera>
    <!-- Fixed 200×200 mm square grid on XZ plane; does not follow camera. -->
    <Grid
        plane="xz"
        type="grid"
        gridSize={[200, 200]}
        cellSize={1}
        sectionSize={10}
        cellColor="#9ca3af"
        sectionColor="#6b7280"
        backgroundColor="#e5e7eb"
        backgroundOpacity={0.25}
        infiniteGrid={false}
        followCamera={false}
        fadeDistance={10000}
        fadeStrength={0.5}
    />
    <!-- Realistic lighting: ambient fill + key light + fill + rim -->
    <T.AmbientLight intensity={0.45} color="#ffffff" />
    <T.HemisphereLight
        color="#ffffff"
        groundColor="#b0b0b0"
        intensity={0.5}
        position={[0, 100, 0]}
    />
    <T.DirectionalLight
        position={[120, 180, 120]}
        intensity={1.2}
        color="#ffffff"
        castShadow
    />
    <T.DirectionalLight
        position={[-80, 80, -80]}
        intensity={0.35}
        color="#e8e8ff"
    />
    <T.DirectionalLight
        position={[0, -50, 100]}
        intensity={0.25}
        color="#ffffff"
    />

    {#if $stlGeometry}
        <!-- Tinkercad exports with Z-up; rotate -90° around X so model stands on grid (Y-up). -->
        <T.Mesh
            geometry={$stlGeometry}
            position={meshPosition}
            scale={FILE_TO_MM}
            rotation.x={-Math.PI / 2}
        >
            <T.MeshStandardMaterial
                color={objectColor}
                roughness={0.3}
                envMapIntensity={0.4}
            />
        </T.Mesh>
    {/if}
    {#if $keycapGeometryStore}
        {#each keycapMeshPositions as pos, i (i)}
            <T.Mesh
                geometry={$keycapGeometryStore}
                position={pos}
                scale={FILE_TO_MM}
                rotation.x={-Math.PI / 2}
            >
                <T.MeshStandardMaterial
                    color={keycapColor}
                    roughness={0.5}
                    envMapIntensity={0.4}
                />
            </T.Mesh>
        {/each}
    {/if}
    {#if showBorder && $borderGeometryStore}
        {#each borderMeshPositions as pos, i (i)}
            <T.Mesh
                geometry={$borderGeometryStore}
                position={pos}
                scale={borderMeshScale}
                rotation.x={-Math.PI / 2}
            >
                <T.MeshStandardMaterial
                    color={textBorderColor}
                    metalness={0.1}
                />
            </T.Mesh>
        {/each}
    {/if}
    {#each keycapLabels as { geometry, position }, labelIdx (labelIdx)}
        <T.Mesh
            {geometry}
            {position}
            scale={[
                textSizeMm * FILE_TO_MM,
                textSizeMm * FILE_TO_MM,
                textSizeMm * FILE_TO_MM,
            ]}
            rotation.x={-Math.PI / 2}
        >
            <T.MeshStandardMaterial
                color={textBorderColor}
                roughness={0.6}
                metalness={0}
            />
        </T.Mesh>
    {/each}
    {#each keycapSvgSlots as slot, slotIdx (slotIdx)}
        {#if svgGeometryByUrl[slot.url]}
            <T.Mesh
                position={slot.position}
                geometry={svgGeometryByUrl[slot.url]}
                scale={[
                    keycapSvgSizeMm * FILE_TO_MM,
                    keycapSvgSizeMm * FILE_TO_MM,
                    LEGEND_DEPTH_MM * FILE_TO_MM,
                ]}
                rotation.x={-Math.PI / 2}
            >
                <T.MeshStandardMaterial
                    color={textBorderColor}
                    roughness={0.6}
                    metalness={0}
                />
            </T.Mesh>
        {/if}
    {/each}
</T.Scene>
