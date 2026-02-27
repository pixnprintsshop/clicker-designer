<script lang="ts">
    import { get } from "svelte/store";
    import { T, useLoader, useThrelte } from "@threlte/core";
    import { Grid, OrbitControls } from "@threlte/extras";
    import {
        Box3,
        Color,
        ExtrudeGeometry,
        Group,
        Mesh,
        PerspectiveCamera,
        type Scene as ThreeScene,
        SRGBColorSpace,
        Vector3,
        type WebGLRenderer,
        WebGLRenderTarget,
    } from "three";
    import { TextGeometry } from "three/addons/geometries/TextGeometry.js";
    import { STLExporter } from "three/addons/exporters/STLExporter.js";
    import { FontLoader } from "three/addons/loaders/FontLoader.js";
    import { STLLoader } from "three/addons/loaders/STLLoader.js";
    import { SVGLoader } from "three/addons/loaders/SVGLoader.js";
    import * as BufferGeometryUtils from "three/addons/utils/BufferGeometryUtils.js";

    import fontUrl from "../assets/font/Daffiys_Regular.json?url";
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
        /** Text label size in mm (for dev/debug). */
        textSizeMm?: number;
        /** Text Y offset in mm above keycap top (for dev/debug). */
        textYOffsetMm?: number;
        /** Called with takeSnapshot() when scene is ready for snapshots. */
        snapshotReady?: (takeSnapshot: () => void) => void;
        /** Called after the snapshot file download has been triggered. */
        onSnapshotDownloaded?: () => void;
        /** Called with exportKeycapStl(keycapIndex?) when scene is ready to export keycap STL(s). */
        exportKeycapStlReady?: (
            exportKeycapStl: (keycapIndex?: number) => void,
        ) => void;
        /** Called after keycap STL file(s) download has been triggered. */
        onKeycapStlDownloaded?: () => void;
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
        textSizeMm = 8.7,
        snapshotReady,
        onSnapshotDownloaded,
        exportKeycapStlReady,
        onKeycapStlDownloaded,
    }: Props = $props();

    const threlte = useThrelte();
    const SNAPSHOT_SIZE = 1536;
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
        composite.height = SNAPSHOT_SIZE * 2;
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

    const stlExporter = new STLExporter();

    /**
     * Export one or all keycaps as STL (keycap + border + letter/SVG) and trigger download.
     * @param keycapIndex - If set, export only this keycap (0-based). Otherwise export all keycaps as separate files.
     */
    function exportKeycapStl(keycapIndex?: number) {
        const keycapGeom = get(keycapGeometryStore);
        const borderGeom = get(borderGeometryStore);
        if (!keycapGeom) return;
        const positions = keycapMeshPositions;
        const borderPositions = borderMeshPositions;
        const indices =
            keycapIndex !== undefined
                ? [keycapIndex]
                : positions.map((_, i) => i);
        const scaleMm = FILE_TO_MM;
        // Use positive scale so normals stay outward (negative scale makes STL non-solid in slicers)
        const textScaleXY = textSizeMm * scaleMm;
        // TextGeometry depth is LEGEND_DEPTH_MM/textSizeMm in size units; scale Z by textSizeMm so final depth = LEGEND_DEPTH_MM (same as SVG).
        const textScaleZ = textSizeMm * scaleMm;
        const legendDepthScaleZ = LEGEND_DEPTH_MM * scaleMm; // for SVG (geometry depth already 1)
        for (const i of indices) {
            if (i >= positions.length) continue;
            const group = new Group();
            // Keycap mesh (same transform as in scene)
            const keycapMesh = new Mesh(keycapGeom.clone());
            keycapMesh.position.set(
                positions[i][0],
                positions[i][1],
                positions[i][2],
            );
            keycapMesh.scale.setScalar(scaleMm);
            keycapMesh.rotation.x = -Math.PI / 2;
            group.add(keycapMesh);
            // Border mesh
            if (showBorder && borderGeom && i < borderPositions.length) {
                const borderMesh = new Mesh(borderGeom.clone());
                borderMesh.position.set(
                    borderPositions[i][0],
                    borderPositions[i][1],
                    borderPositions[i][2],
                );
                borderMesh.scale.setScalar(scaleMm);
                borderMesh.rotation.x = -Math.PI / 2;
                group.add(borderMesh);
            }
            // Label: text or SVG
            const letter = keycapLetters[i]?.trim();
            const svgUrl = keycapSvgUrls[i]?.trim();
            if (svgUrl && svgGeometryByUrl[svgUrl]) {
                const slotPos = (() => {
                    const [x, y, z] = keycapPositions[i];
                    const keycapBottomY = clickerTopY + y - keycapOffset.minZ;
                    const keycapTopY =
                        keycapBottomY + (keycapOffset.maxZ - keycapOffset.minZ);
                    return [x, keycapTopY, z] as [number, number, number];
                })();
                const svgMesh = new Mesh(svgGeometryByUrl[svgUrl].clone());
                svgMesh.position.set(slotPos[0], slotPos[1], slotPos[2]);
                svgMesh.scale.set(
                    keycapSvgSizeMm * scaleMm,
                    keycapSvgSizeMm * scaleMm,
                    legendDepthScaleZ,
                );
                svgMesh.rotation.x = Math.PI / 2;
                svgMesh.rotation.y = Math.PI; // correct X flip in exported STL (Z-up conversion)
                group.add(svgMesh);
            } else if (letter && font) {
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
                    geom.translate(-center.x, -center.y, -center.z);
                }
                const [x, y, z] = (() => {
                    const [px, py, pz] = keycapPositions[i];
                    const keycapBottomY = clickerTopY + py - keycapOffset.minZ;
                    const keycapTopY =
                        keycapBottomY + (keycapOffset.maxZ - keycapOffset.minZ);
                    return [px, keycapTopY, pz] as [number, number, number];
                })();
                const textMesh = new Mesh(geom);
                textMesh.position.set(x, y, z);
                textMesh.scale.set(textScaleXY, textScaleXY, textScaleZ);
                textMesh.rotation.x = Math.PI / 2;
                textMesh.rotation.z = Math.PI; // same orientation as display, keeps normals outward
                textMesh.rotation.y = Math.PI; // correct X flip in exported STL (Z-up conversion)
                group.add(textMesh);
            }
            group.updateMatrixWorld(true);
            // Slicers (Bambu Studio, etc.) expect Z-up; our scene is Y-up. Rotate so model imports upright.
            const root = new Group();
            root.rotation.x = Math.PI / 2;
            root.add(group);
            root.updateMatrixWorld(true);
            const stlData = stlExporter.parse(root, { binary: true });
            const blob = new Blob([stlData], {
                type: "application/octet-stream",
            });
            const name =
                letter && !svgUrl
                    ? `keycap-${i + 1}-${letter.toUpperCase()}.stl`
                    : `keycap-${i + 1}.stl`;
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = name;
            a.click();
            URL.revokeObjectURL(a.href);
            // Dispose geometries we created or cloned
            group.traverse((obj) => {
                if (obj instanceof Mesh) obj.geometry.dispose();
            });
            root.remove(group);
        }
        onKeycapStlDownloaded?.();
    }

    $effect(() => {
        // Subscribe reactively so we run again when the loader finishes
        const keycapGeom = $keycapGeometryStore;
        if (keycapGeom) {
            exportKeycapStlReady?.(exportKeycapStl);
        }
    });

    /** Scene units = mm (1 unit = 1 mm). If STL is in meters, use 1000; if STL is already in mm, use 1. */
    const FILE_TO_MM = 1;

    /** Extrusion depth in mm for letter and logo (same height for both). */
    const LEGEND_DEPTH_MM = 1.2;

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
        (): { center: [number, number, number]; minZ: number } => {
            const geom = $borderGeometryStore;
            if (!geom) return { center: [0, 0, 0], minZ: 0 };
            geom.computeBoundingBox();
            const box = geom.boundingBox;
            if (!box) return { center: [0, 0, 0], minZ: 0 };
            const center = new Vector3();
            box.getCenter(center);
            return {
                center: [center.x, center.y, center.z],
                minZ: box.min.z,
            };
        },
    );
    const keycapHeight = $derived(keycapOffset.maxZ - keycapOffset.minZ);
    /** Border mesh positions: same logic as text — one per keycap, centered at keycap world (x,z), bottom on keycap top Y. */
    const borderMeshPositions = $derived.by((): [number, number, number][] => {
        const positions = keycapPositions;
        const offset = keycapOffset;
        const border = borderOffset;
        const topY = clickerTopY;
        if (!positions?.length) return [];
        return positions.map(([x, y, z]) => {
            const keycapBottomY = topY + y - offset.minZ;
            const keycapTopY = keycapBottomY + keycapHeight;
            const borderPosY = keycapTopY - border.minZ;
            return [x - border.center[0], borderPosY, z + border.center[1]] as [
                number,
                number,
                number,
            ];
        });
    });

    /** Font loaded async for keycap labels */
    let font = $state<ReturnType<FontLoader["parse"]> | null>(null);
    $effect(() => {
        let cancelled = false;
        new FontLoader().loadAsync(fontUrl).then((f) => {
            if (!cancelled) font = f;
        });
        return () => {
            cancelled = true;
        };
    });

    /** Slots that show an SVG instead of text: position + url. Same position as keycap top center. */
    const keycapSvgSlots = $derived.by(
        (): { position: [number, number, number]; url: string }[] => {
            const urls = keycapSvgUrls;
            const positions = keycapPositions;
            const offset = keycapOffset;
            const topY = clickerTopY;
            if (!urls?.length || !positions?.length) return [];
            return positions
                .map((mapped, i) => {
                    const url = urls[i];
                    if (!mapped || !url?.trim()) return null;
                    const [x, y, z] = mapped;
                    const keycapBottomY = topY + y - offset.minZ;
                    const keycapTopY =
                        keycapBottomY + (offset.maxZ - offset.minZ);
                    return {
                        position: [x, keycapTopY, z] as [
                            number,
                            number,
                            number,
                        ],
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
                        merged.translate(-center.x, -center.y, -center.z);
                        merged.computeBoundingBox();
                        box = merged.boundingBox;
                        if (box) {
                            const size = new Vector3();
                            box.getSize(size);
                            const maxDim = Math.max(
                                size.x,
                                size.y,
                                size.z,
                                0.001,
                            );
                            const scale = 1 / maxDim;
                            merged.scale(scale, scale, scale);
                            // Normalize depth to 1 so mesh scale Z = LEGEND_DEPTH_MM gives same height as letter
                            merged.computeBoundingBox();
                            box = merged.boundingBox;
                            if (box) {
                                const zSize = box.max.z - box.min.z;
                                if (zSize > 0.001)
                                    merged.scale(1, 1, 1 / zSize);
                            }
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
            const positions = keycapPositions;
            const offset = keycapOffset;
            const topY = clickerTopY;
            if (!f || !letters?.length || !positions?.length) return [];
            return letters
                .map((letter, i) => {
                    if (urls?.[i]) return null;
                    const mapped = positions[i];
                    if (!mapped || !letter?.trim()) return null;
                    const [x, y, z] = mapped;
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
                        geom.translate(-center.x, -center.y, -center.z);
                    }
                    // Same mapping as keycap mesh: X/Z from centered keycap, Y = keycap top + offset
                    const textX = x;
                    const textZ = z;
                    const keycapBottomY = topY + y - offset.minZ;
                    const keycapTopY =
                        keycapBottomY + (offset.maxZ - offset.minZ);
                    const textY = keycapTopY;
                    return {
                        geometry: geom,
                        position: [textX, textY, textZ] as [
                            number,
                            number,
                            number,
                        ],
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
                scale={FILE_TO_MM}
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
                -textSizeMm * FILE_TO_MM,
                textSizeMm * FILE_TO_MM,
            ]}
            rotation.x={Math.PI / 2}
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
                rotation.x={Math.PI / 2}
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
