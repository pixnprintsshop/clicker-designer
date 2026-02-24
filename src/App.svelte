<script>
    import { Canvas } from "@threlte/core";
    import { NoToneMapping } from "three";
    import Scene from "./lib/Scene.svelte";
    import { loadConfig, saveConfig } from "./lib/configStorage.js";
    import { KEYCAP_POSITIONS } from "./lib/keycapPositions.js";
    import { SVG_ASSETS, SVG_URL_BY_ID } from "./lib/svgAssets.js";

    /**
     * @param {number} n
     * @returns {{ x: number; y: number; z: number }[]}
     */
    function getDefaultPositions(n) {
        const defaults =
            KEYCAP_POSITIONS[Math.min(7, Math.max(1, n)) - 1] ?? [];
        return defaults.map(([x, y, z]) => ({ x, y, z }));
    }

    /**
     * @param {string} name
     * @param {import("./lib/configStorage.js").StoredConfig | null | undefined} [fromSaved] - optional config for migration (legacy flat shape or StoredConfig)
     * @returns {import("./lib/configStorage.js").StoredDesign}
     */
    const DEFAULT_KEYCAP_SVG_ID = "heart.svg";

    function createDefaultDesign(
        /** @type {string} */ name,
        /** @type {import("./lib/configStorage.js").StoredConfig | null | undefined} */ fromSaved = undefined,
    ) {
        const raw = fromSaved && typeof fromSaved === "object" ? fromSaved : {};
        const from =
            /** @type {Partial<import("./lib/configStorage.js").StoredDesign>} */ (
                raw
            );
        const n = Math.min(7, Math.max(1, from.numberOfKeys ?? 1));
        const hasExistingSvg =
            from.keycapSvgByCount &&
            Object.keys(from.keycapSvgByCount).length > 0;
        return {
            id:
                crypto.randomUUID?.() ??
                `d-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            name,
            objectColor: from.objectColor ?? "#ec4899",
            keycapColor: from.keycapColor ?? "#6366f1",
            textBorderColor: from.textBorderColor ?? "#ffffff",
            showBorder: from.showBorder !== false,
            numberOfKeys: n,
            keycapPositionsByCount: from.keycapPositionsByCount ?? {},
            keycapLettersByCount: from.keycapLettersByCount ?? {},
            keycapSvgByCount: hasExistingSvg
                ? from.keycapSvgByCount
                : { [String(n)]: Array(n).fill(DEFAULT_KEYCAP_SVG_ID) },
            keycapSvgSizeMm: from.keycapSvgSizeMm ?? 8,
        };
    }

    const saved = loadConfig();
    const initialDesigns = saved?.designs?.length
        ? saved.designs
        : [createDefaultDesign("Design 1", saved ?? undefined)];
    const initialActive = Math.min(
        Math.max(0, saved?.activeIndex ?? 0),
        initialDesigns.length - 1,
    );

    let designs = $state([...initialDesigns]);
    let activeIndex = $state(initialActive);
    let svgPickerKeyIndex = $state(/** @type {number | null} */ (null));
    let svgPickerOpen = $derived(svgPickerKeyIndex !== null);
    let deleteConfirmIndex = $state(/** @type {number | null} */ (null));
    let sidebarOpen = $state(false);
    let presetModalOpen = $state(false);
    let takeSnapshot = $state(/** @type {(() => void) | null} */ (null));
    let showSnapshotThankYou = $state(false);
    let exportKeycapStl = $state(
        /** @type {((keycapIndex?: number) => void) | null} */ (null),
    );

    const WELCOME_SESSION_KEY = "clicker-designer-welcome-seen";
    let showWelcome = $state(
        typeof sessionStorage !== "undefined" &&
            !sessionStorage.getItem(WELCOME_SESSION_KEY),
    );
    function closeWelcome() {
        try {
            sessionStorage.setItem(WELCOME_SESSION_KEY, "1");
        } catch (_) {}
        showWelcome = false;
    }

    const activeDesign = $derived(designs[activeIndex] ?? designs[0]);

    function updateActiveDesign(
        /** @type {Partial<import("./lib/configStorage.js").StoredDesign>} */ patch,
    ) {
        const i = activeIndex;
        if (i < 0 || i >= designs.length) return;
        designs = designs.map((d, idx) => (idx === i ? { ...d, ...patch } : d));
    }

    const numberOfKeys = $derived(activeDesign?.numberOfKeys ?? 1);
    const objectColor = $derived(activeDesign?.objectColor ?? "#ec4899");
    const keycapColor = $derived(activeDesign?.keycapColor ?? "#6366f1");
    const textBorderColor = $derived(
        activeDesign?.textBorderColor ?? "#1f2937",
    );
    const showBorder = $derived(activeDesign?.showBorder !== false);
    const keycapPositions = $derived(
        (
            activeDesign?.keycapPositionsByCount?.[String(numberOfKeys)] ??
            getDefaultPositions(numberOfKeys)
        ).map((/** @type {{ x: number; y: number; z: number }} */ p) => ({
            ...p,
        })),
    );
    const keycapLetters = $derived(
        (
            activeDesign?.keycapLettersByCount?.[String(numberOfKeys)] ??
            Array(numberOfKeys).fill("")
        ).map((/** @type {string} */ c) =>
            typeof c === "string" ? c.slice(0, 1) : "",
        ),
    );
    const keycapSvg = $derived(
        (
            activeDesign?.keycapSvgByCount?.[String(numberOfKeys)] ??
            Array(numberOfKeys).fill(null)
        ).map((/** @type {string | null} */ s) => s ?? null),
    );
    const keycapSvgSizeMm = $derived(activeDesign?.keycapSvgSizeMm ?? 8);
    const hasAnySvg = $derived(keycapSvg.some((s) => !!s));

    $effect(() => {
        if (!activeDesign) return;
        saveConfig({ designs: [...designs], activeIndex });
    });

    const keycapPositionsForScene = $derived(
        keycapPositions.map(
            (/** @type {{ x: number; y: number; z: number }} */ p) =>
                /** @type {[number, number, number]} */ ([p.x, p.y, p.z]),
        ),
    );

    /** Per-keycap SVG URL or null; passed to Scene for rendering. */
    const keycapSvgUrlsForScene = $derived(
        keycapSvg.map((/** @type {string | null} */ id) =>
            id ? (SVG_URL_BY_ID.get(id) ?? null) : null,
        ),
    );

    function addDesign() {
        const name = `Design ${designs.length + 1}`;
        designs = [...designs, createDefaultDesign(name)];
        activeIndex = designs.length - 1;
    }

    /**
     * @param {number} index
     */
    function deleteDesign(index) {
        if (designs.length <= 1) return;
        designs = designs.filter((_, i) => i !== index);
        activeIndex = Math.min(activeIndex, designs.length - 1);
        if (activeIndex >= designs.length) activeIndex = designs.length - 1;
    }

    /**
     * Position a color popover next to its trigger (called when popover opens).
     * @param {HTMLElement} popoverEl - The popover element (has id, trigger has popovertarget="id")
     * @param {HTMLElement} [explicitTrigger] - If provided, use this element as the position anchor
     */
    function positionColorPopover(popoverEl, explicitTrigger) {
        const trigger =
            explicitTrigger ??
            document.querySelector(`[popovertarget="${popoverEl.id}"]`);
        if (!trigger) return;
        const rect = trigger.getBoundingClientRect();
        const gap = 4;
        popoverEl.style.top = `${rect.bottom + gap}px`;
        popoverEl.style.left = `${rect.left}px`;
        // Keep on screen horizontally
        popoverEl.style.right = "auto";
        popoverEl.style.minWidth = "auto";
        requestAnimationFrame(() => {
            const popRect = popoverEl.getBoundingClientRect();
            if (popRect.right > window.innerWidth)
                popoverEl.style.left = `${window.innerWidth - popRect.width - 8}px`;
            if (popRect.left < 0) popoverEl.style.left = "8px";
        });
    }

    /**
     * Color name map corresponding to COLOR_PALETTE.
     *
     * Add/change names as desired.
     */
    const COLOR_NAMES = [
        "Black",
        "White",
        "Dark Blue",
        "Blue",
        "Pink",
        "Peach Pink",
        "Purple",
        "Green",
        "Dark Green",
        "Matcha Green",
        "Min Green",
        "Yellow",
        "Orange",
        "Red",
        "Magenta",
        "Brick Red",
        "Very Peri",
        "Beige",
        "Brown",
        "Grey",
    ];

    /** Preset palette: specific colors only (grid in popover) */
    const COLOR_PALETTE = [
        "#000000", // black
        "#ffffff", // White
        "#5dadfa", // Dark Blue
        "#141f41", // Blue
        "#ff7e94", // Pink
        "#eeb9ba", // Peach Pink
        "#3d1590", // Purple
        "#83ed64", // Green
        "#03452e", // Dark Green
        "#acb26d", // Matcha Green
        "#9bf5c8", // Min Green
        "#ffeb47", // Yellow
        "#f5541b", // Orange
        "#d23724", // Red
        "#c22856", // Magenta
        "#722427", // Brick Red
        "#7174c0", // Very Peri
        "#d9b99b", // Beige
        "#623411", // Brown
        "#686c6f", // Grey
    ];

    /** Preset color combinations for the gallery (name + base, keycap, legend). */
    const PRESET_GALLERY = [
        {
            name: "Classic Pink",
            objectColor: "#ff7e94",
            keycapColor: "#ffffff",
            textBorderColor: "#1f2937",
        },
        {
            name: "Ocean",
            objectColor: "#5dadfa",
            keycapColor: "#141f41",
            textBorderColor: "#ffffff",
        },
        {
            name: "Forest",
            objectColor: "#03452e",
            keycapColor: "#83ed64",
            textBorderColor: "#ffffff",
        },
        {
            name: "Sunset",
            objectColor: "#f5541b",
            keycapColor: "#ffeb47",
            textBorderColor: "#722427",
        },
        {
            name: "Lavender",
            objectColor: "#7174c0",
            keycapColor: "#e8e8ff",
            textBorderColor: "#3d1590",
        },
        {
            name: "Rose",
            objectColor: "#c22856",
            keycapColor: "#eeb9ba",
            textBorderColor: "#722427",
        },
        {
            name: "Mint",
            objectColor: "#9bf5c8",
            keycapColor: "#03452e",
            textBorderColor: "#ffffff",
        },
        {
            name: "Neutral",
            objectColor: "#686c6f",
            keycapColor: "#d9b99b",
            textBorderColor: "#623411",
        },
        {
            name: "Bold Red",
            objectColor: "#d23724",
            keycapColor: "#000000",
            textBorderColor: "#ffffff",
        },
        {
            name: "Pure White",
            objectColor: "#ffffff",
            keycapColor: "#f1f5f9",
            textBorderColor: "#475569",
        },
        {
            name: "Dark",
            objectColor: "#141f41",
            keycapColor: "#686c6f",
            textBorderColor: "#ffffff",
        },
        {
            name: "Matcha",
            objectColor: "#acb26d",
            keycapColor: "#03452e",
            textBorderColor: "#ffffff",
        },
        {
            name: "Navy & Gold",
            objectColor: "#141f41",
            keycapColor: "#ffeb47",
            textBorderColor: "#141f41",
        },
        {
            name: "Berry",
            objectColor: "#3d1590",
            keycapColor: "#eeb9ba",
            textBorderColor: "#ffffff",
        },
        {
            name: "Coral",
            objectColor: "#eeb9ba",
            keycapColor: "#ffffff",
            textBorderColor: "#722427",
        },
        {
            name: "Chocolate",
            objectColor: "#623411",
            keycapColor: "#d9b99b",
            textBorderColor: "#ffffff",
        },
        {
            name: "Cherry",
            objectColor: "#d23724",
            keycapColor: "#ffffff",
            textBorderColor: "#141f41",
        },
        {
            name: "Plum",
            objectColor: "#3d1590",
            keycapColor: "#c22856",
            textBorderColor: "#ffffff",
        },
        {
            name: "Lime",
            objectColor: "#9bf5c8",
            keycapColor: "#83ed64",
            textBorderColor: "#03452e",
        },
        {
            name: "Tangerine",
            objectColor: "#f5541b",
            keycapColor: "#ffffff",
            textBorderColor: "#722427",
        },
        {
            name: "Storm",
            objectColor: "#686c6f",
            keycapColor: "#141f41",
            textBorderColor: "#ffffff",
        },
        {
            name: "Honey",
            objectColor: "#d9b99b",
            keycapColor: "#ffeb47",
            textBorderColor: "#623411",
        },
        {
            name: "Black & Mint",
            objectColor: "#000000",
            keycapColor: "#9bf5c8",
            textBorderColor: "#ffffff",
        },
        {
            name: "Blush",
            objectColor: "#eeb9ba",
            keycapColor: "#c22856",
            textBorderColor: "#ffffff",
        },
        {
            name: "Cream & Brown",
            objectColor: "#d9b99b",
            keycapColor: "#623411",
            textBorderColor: "#ffffff",
        },
        {
            name: "Pink & Navy",
            objectColor: "#ff7e94",
            keycapColor: "#141f41",
            textBorderColor: "#ffffff",
        },
        {
            name: "Brick & Cream",
            objectColor: "#722427",
            keycapColor: "#d9b99b",
            textBorderColor: "#ffffff",
        },
        {
            name: "Periwinkle Deep",
            objectColor: "#7174c0",
            keycapColor: "#3d1590",
            textBorderColor: "#ffffff",
        },
        {
            name: "Midnight",
            objectColor: "#000000",
            keycapColor: "#141f41",
            textBorderColor: "#ffeb47",
        },
    ];

    /** Index in PRESET_GALLERY for syncing when applying from gallery (sidebar or modal). */
    let lastPresetIndex = $state(0);

    // --- 1. Hovered color index state
    /** @type {number | null} */
    let hoveredColorIndex = $state(/** @type {number | null} */ (null));
    /**
     * @param {number} idx
     * @returns {void}
     */
    function handleColorHover(idx) {
        hoveredColorIndex = idx;
    }
    function handleColorLeave() {
        hoveredColorIndex = null;
    }
</script>

<div class="flex flex-col md:flex-row w-full h-full min-h-dvh overflow-hidden">
    <!-- Mobile sidebar backdrop -->
    <button
        type="button"
        class="fixed inset-0 z-30 bg-black/40 md:hidden transition-opacity duration-200 {sidebarOpen
            ? 'opacity-100 pointer-events-auto'
            : 'opacity-0 pointer-events-none'}"
        aria-hidden="true"
        tabindex="-1"
        onclick={() => (sidebarOpen = false)}
    ></button>

    <!-- Welcome dialog (once per session) -->
    {#if showWelcome}
        <div
            class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/40"
            role="presentation"
            onclick={() => closeWelcome()}
        >
            <div
                class="bg-white rounded-xl shadow-2xl w-full max-w-[95vw] overflow-hidden max-h-[90vh] flex flex-col"
                role="dialog"
                aria-modal="true"
                aria-labelledby="welcome-title"
                tabindex="-1"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => {
                    if (e.key === "Escape") closeWelcome();
                }}
            >
                <div class="py-6 px-5 flex flex-col items-center text-center">
                    <img
                        src="/logo.png"
                        alt="App logo"
                        class="w-20 h-20 object-contain mb-4"
                    />
                    <h2
                        id="welcome-title"
                        class="m-0 mb-1 text-xl font-bold text-slate-800"
                    >
                        Fidget Clicker Designer
                        <br />
                    </h2>
                    <span class="text-sm text-slate-500">by</span>
                    <img
                        src="/pixnprints-logo.png"
                        alt="PixnPrints logo"
                        class="h-10 object-contain mb-4"
                    />
                    <p class="m-0 mb-5 text-sm text-slate-500 leading-snug">
                        Design your custom clicker keychains. Choose colors, add
                        letters or icons to each key, and create multiple
                        designs. Print. Personalize. Cherish.
                    </p>
                    <p
                        class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400"
                    >
                        Follow us & shop
                    </p>
                    <div class="flex flex-wrap justify-center gap-2 mb-5">
                        <a
                            href="https://www.facebook.com/pixnprints.shop"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-3 py-2 text-[13px] font-medium text-white rounded-md bg-[#1877f2] hover:bg-[#166fe5] transition-colors"
                            title="Facebook"
                            aria-label="Facebook"
                        >
                            Facebook
                        </a>
                        <a
                            href="https://shopee.ph/pixnprints"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-3 py-2 text-[13px] font-medium text-white rounded-md bg-[#ee4d2d] hover:bg-[#d94522] transition-colors"
                            title="Shopee"
                            aria-label="Shopee"
                        >
                            Shopee
                        </a>
                        <a
                            href="https://www.lazada.com.ph/shop/pixnprints"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-3 py-2 text-[13px] font-medium text-white rounded-md bg-[#0f146d] hover:bg-[#0c0f52] transition-colors"
                            title="Lazada"
                            aria-label="Lazada"
                        >
                            Lazada
                        </a>
                        <a
                            href="https://www.tiktok.com/@pixnprints.shop_"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-3 py-2 text-[13px] font-medium text-white rounded-md bg-black hover:bg-[#212121] transition-colors"
                            title="TikTok"
                            aria-label="TikTok"
                        >
                            TikTok
                        </a>
                    </div>
                    <button
                        type="button"
                        class="w-full py-3 px-4 text-[15px] font-semibold text-white bg-brand rounded-lg hover:bg-brand-hover transition-colors touch-manipulation min-h-[44px]"
                        onclick={() => closeWelcome()}
                    >
                        Get started
                    </button>
                </div>
            </div>
        </div>
    {/if}

    <aside
        class="fixed md:relative inset-y-0 left-0 z-40 w-[260px] max-w-[85vw] md:max-w-none flex-shrink-0 flex flex-col gap-4 overflow-y-auto bg-surface border-r border-brand-border p-4 md:p-5 transition-transform duration-200 ease-out {sidebarOpen
            ? 'translate-x-0'
            : '-translate-x-full md:translate-x-0'}"
        aria-label="Options"
    >
        <div class="flex items-center justify-between md:block">
            <h2
                class="m-0 text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
                Options
            </h2>
            <button
                type="button"
                class="md:hidden w-10 h-10 flex items-center justify-center rounded-lg text-slate-600 hover:bg-slate-200"
                aria-label="Close options"
                onclick={() => (sidebarOpen = false)}
            >
                ×
            </button>
        </div>
        <label class="flex flex-col gap-2">
            <span class="text-[13px] font-medium text-slate-700"
                >Number of keys</span
            >
            <select
                class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-md bg-white text-slate-800 cursor-pointer touch-manipulation min-h-[44px]"
                value={numberOfKeys}
                onchange={(e) =>
                    updateActiveDesign({
                        numberOfKeys: Number(e.currentTarget.value),
                    })}
                aria-label="Number of keys"
            >
                {#each Array.from({ length: 7 }, (_, i) => i + 1) as n}
                    <option value={n}>{n} key{n === 1 ? "" : "s"}</option>
                {/each}
            </select>
        </label>
        <div class="flex flex-col gap-2">
            <span class="text-[13px] font-medium text-slate-700"
                >Base Color</span
            >
            <button
                type="button"
                class="flex items-center gap-2 w-full px-2 py-2.5 text-[13px] border border-slate-200 rounded-md bg-white text-slate-800 text-left cursor-pointer hover:border-slate-300 hover:bg-slate-50 min-h-[44px] touch-manipulation"
                popovertarget="object-color-popover"
                popovertargetaction="toggle"
                title="Object color"
                aria-label="Choose object color"
            >
                <span
                    class="w-6 h-6 rounded border border-slate-200 flex-shrink-0"
                    style="background-color: {objectColor};"
                ></span>
                <span class="text-xs font-mono text-slate-500"
                    >{objectColor}</span
                >
            </button>
            <div
                id="object-color-popover"
                class="color-popover fixed p-3 rounded-lg border border-slate-200 bg-white shadow-lg"
                popover="auto"
                onbeforetoggle={(e) => {
                    if (e.newState === "open")
                        positionColorPopover(e.currentTarget);
                }}
            >
                <div class="grid grid-cols-6 gap-1.5">
                    {#each COLOR_PALETTE as hex, idx}
                        <button
                            type="button"
                            class="w-7 h-7 p-0 border border-gray-300 rounded-md cursor-pointer relative transition-all hover:scale-105 hover:border-slate-400 {objectColor ===
                            hex
                                ? 'border-slate-800 ring-1 ring-white ring-inset'
                                : ''}"
                            style="background-color: {hex};"
                            title={hex}
                            aria-label="Color {hex}"
                            onmouseenter={() => handleColorHover(idx)}
                            onmouseleave={handleColorLeave}
                            onclick={() => {
                                updateActiveDesign({ objectColor: hex });
                                document
                                    .getElementById("object-color-popover")
                                    ?.hidePopover?.();
                            }}
                        >
                            {#if objectColor === hex}
                                <span
                                    class="absolute inset-0 flex items-center justify-center text-sm font-bold text-white drop-shadow-sm"
                                    aria-hidden="true">✓</span
                                >
                            {/if}
                        </button>
                    {/each}
                </div>
                {#if hoveredColorIndex !== null}
                    <div class="pt-2 text-center">
                        <span
                            class="inline-block text-xs font-medium text-slate-600 px-2 py-1 bg-slate-100 rounded"
                            >{COLOR_NAMES[hoveredColorIndex]}</span
                        >
                    </div>
                {/if}
            </div>
        </div>
        <div class="flex flex-col gap-2">
            <span class="text-[13px] font-medium text-slate-700"
                >Keycaps color</span
            >
            <button
                type="button"
                class="flex items-center gap-2 w-full px-2 py-2.5 text-[13px] border border-slate-200 rounded-md bg-white text-slate-800 text-left cursor-pointer hover:border-slate-300 hover:bg-slate-50 min-h-[44px] touch-manipulation"
                popovertarget="keycap-color-popover"
                popovertargetaction="toggle"
                title="Keycaps color"
                aria-label="Choose keycaps color"
            >
                <span
                    class="w-6 h-6 rounded border border-slate-200 flex-shrink-0"
                    style="background-color: {keycapColor};"
                ></span>
                <span class="text-xs font-mono text-slate-500"
                    >{keycapColor}</span
                >
            </button>
            <div
                id="keycap-color-popover"
                class="color-popover fixed p-3 rounded-lg border border-slate-200 bg-white shadow-lg"
                popover="auto"
                onbeforetoggle={(e) => {
                    if (e.newState === "open")
                        positionColorPopover(e.currentTarget);
                }}
            >
                <div class="grid grid-cols-6 gap-1.5">
                    {#each COLOR_PALETTE as hex, idx}
                        <button
                            type="button"
                            class="w-7 h-7 p-0 border border-gray-300 rounded-md cursor-pointer relative transition-all hover:scale-105 hover:border-slate-400 {keycapColor ===
                            hex
                                ? 'border-slate-800 ring-1 ring-white ring-inset'
                                : ''}"
                            style="background-color: {hex};"
                            title={hex}
                            aria-label="Color {hex}"
                            onmouseenter={() => handleColorHover(idx)}
                            onmouseleave={handleColorLeave}
                            onclick={() => {
                                updateActiveDesign({ keycapColor: hex });
                                document
                                    .getElementById("keycap-color-popover")
                                    ?.hidePopover?.();
                            }}
                        >
                            {#if keycapColor === hex}
                                <span
                                    class="absolute inset-0 flex items-center justify-center text-sm font-bold text-white drop-shadow-sm"
                                    aria-hidden="true">✓</span
                                >
                            {/if}
                        </button>
                    {/each}
                </div>
                {#if hoveredColorIndex !== null}
                    <div class="pt-2 text-center">
                        <span
                            class="inline-block text-xs font-medium text-slate-600 px-2 py-1 bg-slate-100 rounded"
                            >{COLOR_NAMES[hoveredColorIndex]}</span
                        >
                    </div>
                {/if}
            </div>
        </div>
        <div class="flex flex-col gap-2">
            <span class="text-[13px] font-medium text-slate-700"
                >Legend color</span
            >
            <button
                type="button"
                class="flex items-center gap-2 w-full px-2 py-2.5 text-[13px] border border-slate-200 rounded-md bg-white text-slate-800 text-left cursor-pointer hover:border-slate-300 hover:bg-slate-50 min-h-[44px] touch-manipulation"
                popovertarget="text-border-color-popover"
                popovertargetaction="toggle"
                title="Text and border color"
                aria-label="Choose text and border color"
            >
                <span
                    class="w-6 h-6 rounded border border-slate-200 flex-shrink-0"
                    style="background-color: {textBorderColor};"
                ></span>
                <span class="text-xs font-mono text-slate-500"
                    >{textBorderColor}</span
                >
            </button>
            <div
                id="text-border-color-popover"
                class="color-popover fixed p-3 rounded-lg border border-slate-200 bg-white shadow-lg"
                popover="auto"
                onbeforetoggle={(e) => {
                    if (e.newState === "open")
                        positionColorPopover(e.currentTarget);
                }}
            >
                <div class="grid grid-cols-6 gap-1.5">
                    {#each COLOR_PALETTE as hex, idx}
                        <button
                            type="button"
                            class="w-7 h-7 p-0 rounded-md border-2 border-transparent cursor-pointer relative transition-all hover:scale-105 hover:border-slate-400 {textBorderColor ===
                            hex
                                ? 'border-slate-800 ring-1 ring-white ring-inset'
                                : ''}"
                            style="background-color: {hex};"
                            title={hex}
                            aria-label="Color {hex}"
                            onmouseenter={() => handleColorHover(idx)}
                            onmouseleave={handleColorLeave}
                            onclick={() => {
                                updateActiveDesign({ textBorderColor: hex });
                                document
                                    .getElementById("text-border-color-popover")
                                    ?.hidePopover?.();
                            }}
                        >
                            {#if textBorderColor === hex}
                                <span
                                    class="absolute inset-0 flex items-center justify-center text-sm font-bold text-white drop-shadow-sm"
                                    aria-hidden="true">✓</span
                                >
                            {/if}
                        </button>
                    {/each}
                </div>
                {#if hoveredColorIndex !== null}
                    <div class="pt-2 text-center">
                        <span
                            class="inline-block text-xs font-medium text-slate-600 px-2 py-1 bg-slate-100 rounded"
                            >{COLOR_NAMES[hoveredColorIndex]}</span
                        >
                    </div>
                {/if}
            </div>
        </div>
        <label
            class="flex flex-row items-center justify-between gap-2 py-1 min-h-[44px]"
        >
            <span class="text-[13px] font-medium text-slate-700"
                >Show border</span
            >
            <input
                type="checkbox"
                class="w-[18px] h-[18px] accent-brand cursor-pointer touch-manipulation"
                checked={showBorder}
                onchange={(e) =>
                    updateActiveDesign({ showBorder: e.currentTarget.checked })}
                aria-label="Toggle border on keycaps"
            />
        </label>

        {#if hasAnySvg}
            <div class="flex flex-col gap-2">
                <div class="flex items-center justify-between">
                    <span class="text-[13px] font-medium text-slate-700"
                        >SVG size (mm)</span
                    >
                    <span
                        class="text-[13px] tabular-nums text-slate-600"
                        aria-hidden="true"
                        >{keycapSvgSizeMm}</span
                    >
                </div>
                <p class="text-[11px] text-slate-500 m-0">
                    Uniform scale; aspect ratio is kept.
                </p>
                <input
                    type="range"
                    min="1"
                    max="30"
                    step="0.5"
                    class="w-full h-2 accent-brand cursor-pointer touch-manipulation"
                    value={keycapSvgSizeMm}
                    oninput={(e) => {
                        const v = parseFloat(
                            e.currentTarget?.value ?? "8",
                        );
                        if (!Number.isNaN(v))
                            updateActiveDesign({
                                keycapSvgSizeMm: Math.max(
                                    1,
                                    Math.min(30, v),
                                ),
                            });
                    }}
                    aria-label="SVG size in mm"
                />
            </div>
        {/if}

        <div class="flex flex-col gap-2">
            <span class="text-[13px] font-medium text-slate-700"
                >Preset gallery</span
            >
            <p class="text-[11px] text-slate-500 m-0">
                Click a preset to apply its colors.
            </p>
            <div class="grid grid-cols-3 gap-2">
                {#each PRESET_GALLERY as preset, idx}
                    <button
                        type="button"
                        class="flex flex-col items-stretch rounded-lg border-2 overflow-hidden cursor-pointer touch-manipulation transition-all hover:scale-[1.02] hover:border-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-1 {objectColor ===
                            preset.objectColor &&
                        keycapColor === preset.keycapColor &&
                        textBorderColor === preset.textBorderColor
                            ? 'border-brand ring-1 ring-brand ring-offset-1'
                            : 'border-slate-200'}"
                        title={preset.name}
                        aria-label="Apply preset {preset.name}"
                        onclick={() => {
                            lastPresetIndex = idx;
                            updateActiveDesign({
                                objectColor: preset.objectColor,
                                keycapColor: preset.keycapColor,
                                textBorderColor: preset.textBorderColor,
                            });
                        }}
                    >
                        <div class="flex h-10 border-b border-slate-200">
                            <span
                                class="flex-1 min-w-0"
                                style="background-color: {preset.objectColor};"
                            ></span>
                            <span
                                class="flex-1 min-w-0"
                                style="background-color: {preset.keycapColor};"
                            ></span>
                            <span
                                class="flex-1 min-w-0"
                                style="background-color: {preset.textBorderColor};"
                            ></span>
                        </div>
                        <span
                            class="text-[8px] font-medium text-slate-600 py-1.5 px-1 truncate bg-slate-50"
                            >{preset.name}</span
                        >
                    </button>
                {/each}
            </div>
        </div>

        <!-- <h2 class="sidebar-title">Keycap positions (mm)</h2>
        <p class="sidebar-hint">X/Z = position. Y = offset from clicker top (0 = on clicker). Copy into <code>keycapPositions.ts</code>.</p>
        {#each keycapPositions as pos, i}
            <div class="keycap-row">
                <span class="keycap-label">Key {i + 1}</span>
                <div class="keycap-inputs">
                    <label class="axis-input">
                        <span>X</span>
                        <input type="number" bind:value={pos.x} step="0.5" class="number-input" />
                    </label>
                    <label class="axis-input">
                        <span>Y</span>
                        <input type="number" bind:value={pos.y} step="0.5" class="number-input" />
                    </label>
                    <label class="axis-input">
                        <span>Z</span>
                        <input type="number" bind:value={pos.z} step="0.5" class="number-input" />
                    </label>
                </div>
            </div>
        {/each} -->
    </aside>

    <!-- Preset gallery modal (mobile: choose preset, closes on select) -->
    {#if presetModalOpen}
        <div
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40"
            role="presentation"
            onclick={() => (presetModalOpen = false)}
        >
            <div
                class="bg-white rounded-xl shadow-2xl w-full max-w-[360px] max-h-[85dvh] flex flex-col overflow-hidden"
                role="dialog"
                aria-modal="true"
                aria-label="Choose preset"
                tabindex="-1"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => {
                    if (e.key === "Escape") presetModalOpen = false;
                }}
            >
                <div
                    class="flex items-center justify-between px-4 py-3 border-b border-slate-200 shrink-0"
                >
                    <h3 class="m-0 text-[15px] font-semibold text-slate-800">
                        Choose preset
                    </h3>
                    <button
                        type="button"
                        class="w-8 h-8 flex items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 text-2xl leading-none touch-manipulation"
                        aria-label="Close"
                        onclick={() => (presetModalOpen = false)}
                    >
                        ×
                    </button>
                </div>
                <div class="grid grid-cols-3 gap-2 p-4 overflow-y-auto">
                    {#each PRESET_GALLERY as preset, idx}
                        <button
                            type="button"
                            class="flex flex-col items-stretch rounded-lg border-2 overflow-hidden cursor-pointer touch-manipulation transition-all hover:scale-[1.02] hover:border-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-1 {objectColor ===
                                preset.objectColor &&
                            keycapColor === preset.keycapColor &&
                            textBorderColor === preset.textBorderColor
                                ? 'border-brand ring-1 ring-brand ring-offset-1'
                                : 'border-slate-200'}"
                            title={preset.name}
                            aria-label="Apply preset {preset.name}"
                            onclick={() => {
                                lastPresetIndex = idx;
                                updateActiveDesign({
                                    objectColor: preset.objectColor,
                                    keycapColor: preset.keycapColor,
                                    textBorderColor: preset.textBorderColor,
                                });
                                presetModalOpen = false;
                            }}
                        >
                            <div class="flex h-10 border-b border-slate-200">
                                <span
                                    class="flex-1 min-w-0"
                                    style="background-color: {preset.objectColor};"
                                ></span>
                                <span
                                    class="flex-1 min-w-0"
                                    style="background-color: {preset.keycapColor};"
                                ></span>
                                <span
                                    class="flex-1 min-w-0"
                                    style="background-color: {preset.textBorderColor};"
                                ></span>
                            </div>
                            <span
                                class="text-[8px] font-medium text-slate-600 py-1.5 px-1 truncate bg-slate-50"
                                >{preset.name}</span
                            >
                        </button>
                    {/each}
                </div>
            </div>
        </div>
    {/if}

    <!-- SVG picker modal (outside sidebar so it overlays viewport) -->
    {#if svgPickerOpen}
        <div
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40"
            role="presentation"
            onclick={() => (svgPickerKeyIndex = null)}
        >
            <div
                class="bg-white rounded-xl shadow-2xl w-[320px] max-w-[90vw] max-h-[85dvh] flex flex-col overflow-hidden"
                role="dialog"
                aria-modal="true"
                aria-label="Pick SVG icon"
                tabindex="-1"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => {
                    if (e.key === "Escape") svgPickerKeyIndex = null;
                }}
            >
                <div
                    class="flex items-center justify-between px-4 py-4 border-b border-slate-200"
                >
                    <h3 class="m-0 text-[15px] font-semibold text-slate-800">
                        Pick icon for Key {svgPickerKeyIndex !== null
                            ? svgPickerKeyIndex + 1
                            : ""}
                    </h3>
                    <button
                        type="button"
                        class="w-8 h-8 flex items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 text-2xl leading-none touch-manipulation"
                        aria-label="Close"
                        onclick={() => (svgPickerKeyIndex = null)}
                    >
                        ×
                    </button>
                </div>
                <div class="grid grid-cols-4 gap-2 p-4 overflow-y-auto">
                    <button
                        type="button"
                        class="aspect-square p-2 border-2 rounded-lg bg-white cursor-pointer flex items-center justify-center text-xs text-slate-500 transition-colors touch-manipulation min-h-[44px] {svgPickerKeyIndex !==
                            null && !keycapSvg[svgPickerKeyIndex]
                            ? 'border-brand bg-brand-light text-brand'
                            : 'border-slate-200 hover:border-brand-muted hover:bg-brand-light'}"
                        title="None"
                        onclick={() => {
                            if (svgPickerKeyIndex !== null && activeDesign) {
                                const next = keycapSvg.map(
                                    (
                                        /** @type {string | null} */ s,
                                        /** @type {number} */ j,
                                    ) => (j === svgPickerKeyIndex ? null : s),
                                );
                                updateActiveDesign({
                                    keycapSvgByCount: {
                                        ...activeDesign.keycapSvgByCount,
                                        [numberOfKeys]: next,
                                    },
                                });
                                svgPickerKeyIndex = null;
                            }
                        }}
                    >
                        None
                    </button>
                    {#each SVG_ASSETS as asset}
                        <button
                            type="button"
                            class="aspect-square p-2 border-2 rounded-lg bg-white cursor-pointer flex items-center justify-center transition-colors touch-manipulation min-h-[44px] {svgPickerKeyIndex !==
                                null &&
                            keycapSvg[svgPickerKeyIndex] === asset.id
                                ? 'border-brand bg-brand-light'
                                : 'border-slate-200 hover:border-brand-muted hover:bg-brand-light'}"
                            title={asset.name}
                            onclick={() => {
                                if (
                                    svgPickerKeyIndex !== null &&
                                    activeDesign
                                ) {
                                    const next = keycapSvg.map(
                                        (
                                            /** @type {string | null} */ s,
                                            /** @type {number} */ j,
                                        ) =>
                                            j === svgPickerKeyIndex
                                                ? asset.id
                                                : s,
                                    );
                                    updateActiveDesign({
                                        keycapSvgByCount: {
                                            ...activeDesign.keycapSvgByCount,
                                            [numberOfKeys]: next,
                                        },
                                    });
                                    svgPickerKeyIndex = null;
                                }
                            }}
                        >
                            <img
                                src={asset.url}
                                alt=""
                                class="w-7 h-7 object-contain"
                            />
                        </button>
                    {/each}
                </div>
            </div>
        </div>
    {/if}

    <!-- Snapshot thank-you dialog (after download) -->
    {#if showSnapshotThankYou}
        <div
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40"
            role="dialog"
            aria-modal="true"
            aria-labelledby="snapshot-thankyou-title"
            tabindex="-1"
            onclick={() => (showSnapshotThankYou = false)}
            onkeydown={(e) => {
                if (e.key === "Escape") showSnapshotThankYou = false;
            }}
        >
            <div
                class="bg-white rounded-xl shadow-2xl w-full max-w-md p-6"
                role="document"
                tabindex="-1"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) =>
                    e.key === "Escape" && (showSnapshotThankYou = false)}
            >
                <h3
                    id="snapshot-thankyou-title"
                    class="m-0 mb-3 text-lg font-semibold text-slate-800"
                >
                    Thank you for using Clicker Designer
                </h3>
                <p class="m-0 mb-3 text-sm text-slate-600 leading-snug">
                    Your snapshot has been saved. Check your <strong
                        >Downloads</strong
                    >
                    folder (or <strong>Photos / Gallery</strong> on mobile) for the
                    image.
                </p>
                <p class="m-0 mb-5 text-sm text-slate-600 leading-snug">
                    When you order your fidget clicker from <strong
                        >PixnPrints</strong
                    >, share this design so we can personalize it for you.
                </p>
                <button
                    type="button"
                    class="w-full py-3 px-4 text-sm font-semibold text-white bg-brand rounded-lg hover:bg-brand-hover touch-manipulation min-h-[44px]"
                    onclick={() => (showSnapshotThankYou = false)}
                >
                    Got it
                </button>
            </div>
        </div>
    {/if}

    <!-- Delete design confirmation (outside sidebar so it overlays viewport) -->
    {#if deleteConfirmIndex !== null}
        <div
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40"
            role="presentation"
            onclick={() => (deleteConfirmIndex = null)}
        >
            <div
                class="bg-white rounded-xl shadow-2xl w-[320px] max-w-[90vw] p-5"
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="delete-confirm-title"
                tabindex="-1"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => {
                    if (e.key === "Escape") deleteConfirmIndex = null;
                }}
            >
                <h3
                    id="delete-confirm-title"
                    class="m-0 mb-2 text-[15px] font-semibold text-slate-800"
                >
                    Delete design?
                </h3>
                <p class="m-0 mb-5 text-sm text-slate-500 leading-snug">
                    {designs[deleteConfirmIndex]?.name ?? "This design"} will be
                    removed. This cannot be undone.
                </p>
                <div class="flex justify-end gap-2">
                    <button
                        type="button"
                        class="px-4 py-2.5 text-sm font-medium rounded-md bg-slate-100 text-slate-700 border border-slate-200 hover:bg-slate-200 touch-manipulation min-h-[44px]"
                        onclick={() => (deleteConfirmIndex = null)}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2.5 text-sm font-medium rounded-md bg-red-600 text-white border border-red-600 hover:bg-red-700 touch-manipulation min-h-[44px]"
                        onclick={() => {
                            if (deleteConfirmIndex !== null) {
                                deleteDesign(deleteConfirmIndex);
                                deleteConfirmIndex = null;
                            }
                        }}
                    >
                        Delete
                    </button>
                </div>
            </div>
        </div>
    {/if}

    <div class="flex-1 min-w-0 flex flex-col overflow-hidden">
        <header
            class="shrink-0 flex items-center gap-3 md:gap-4 px-3 py-2 md:px-4 md:py-2.5 bg-surface border-b border-brand-border"
        >
            <button
                type="button"
                class="md:hidden w-10 h-10 shrink-0 flex items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 touch-manipulation"
                aria-label="Open options"
                onclick={() => (sidebarOpen = true)}
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 6h16M4 12h16M4 18h16"
                    /></svg
                >
            </button>

            <div class="flex flex-wrap items-center gap-2 min-w-0">
                {#each keycapLetters as letter, i}
                    <div class="flex items-center gap-1.5">
                        <label class="flex items-center gap-2 flex-1 min-w-0">
                            <span
                                class="text-xs font-medium text-slate-600 min-w-9"
                                >Key {i + 1}</span
                            >
                            <input
                                id="letter-input-{i}"
                                type="text"
                                class="w-8 h-8 md:w-9 md:h-9 p-0 text-sm md:text-base text-center uppercase border border-slate-200 rounded bg-white touch-manipulation aspect-square"
                                maxlength="1"
                                placeholder=""
                                value={letter}
                                onfocus={(e) => e.currentTarget?.select()}
                                oninput={(e) => {
                                    const v = (
                                        e.currentTarget?.value ?? ""
                                    ).slice(0, 1);
                                    if (!activeDesign) return;
                                    const next = keycapLetters.map(
                                        (
                                            /** @type {string} */ l,
                                            /** @type {number} */ j,
                                        ) => (j === i ? v : l),
                                    );
                                    updateActiveDesign({
                                        keycapLettersByCount: {
                                            ...activeDesign.keycapLettersByCount,
                                            [numberOfKeys]: next,
                                        },
                                    });
                                    if (v && i + 1 < keycapLetters.length) {
                                        requestAnimationFrame(() => {
                                            document
                                                .getElementById(
                                                    `letter-input-${i + 1}`,
                                                )
                                                ?.focus();
                                        });
                                    }
                                }}
                                aria-label="Letter for key {i + 1}"
                            />
                        </label>
                        <button
                            tabindex="-1"
                            type="button"
                            class="w-8 h-8 md:h-9 md:w-9 flex items-center justify-center p-1 border border-slate-200 rounded-md bg-white hover:border-brand hover:bg-brand-light touch-manipulation min-h-[30px] md:min-h-0"
                            title="Pick SVG icon"
                            aria-label="Pick SVG for key {i + 1}"
                            onclick={() => (svgPickerKeyIndex = i)}
                        >
                            {#if keycapSvg[i]}
                                <img
                                    src={SVG_ASSETS.find(
                                        (a) => a.id === keycapSvg[i],
                                    )?.url}
                                    alt=""
                                    class="w-full h-full object-contain"
                                />
                            {:else}
                                <span
                                    class="text-[10px] font-medium text-slate-400"
                                    >SVG</span
                                >
                            {/if}
                        </button>
                    </div>
                {/each}
            </div>
        </header>
        <div
            class="md:hidden flex-shrink-0 flex items-center justify-center gap-3 px-3 py-2 bg-brand-light/60 border-b border-brand-border flex-wrap"
        >
            <button
                type="button"
                class="flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 touch-manipulation shrink-0"
                aria-label="Choose preset"
                title="Choose preset"
                onclick={() => (presetModalOpen = true)}
            >
                <span class="flex gap-0.5">
                    <span
                        class="w-3 h-3 rounded-sm border border-slate-300 shrink-0"
                        style="background-color: {objectColor};"
                    ></span>
                    <span
                        class="w-3 h-3 rounded-sm border border-slate-300 shrink-0"
                        style="background-color: {keycapColor};"
                    ></span>
                    <span
                        class="w-3 h-3 rounded-sm border border-slate-300 shrink-0"
                        style="background-color: {textBorderColor};"
                    ></span>
                </span>
                Preset
            </button>
            <select
                class="h-8 min-w-[3rem] px-2 text-sm border border-slate-300 rounded-lg bg-white text-slate-700 cursor-pointer touch-manipulation"
                value={numberOfKeys}
                onchange={(e) =>
                    updateActiveDesign({
                        numberOfKeys: Number(e.currentTarget.value),
                    })}
                aria-label="Number of keys"
                title="Number of keys"
            >
                {#each Array.from({ length: 7 }, (_, i) => i + 1) as n}
                    <option value={n}>{n}</option>
                {/each}
            </select>
            <button
                type="button"
                class="w-8 h-8 rounded-lg border-2 border-slate-300 shadow-sm hover:border-slate-400 touch-manipulation transition-colors"
                style="background-color: {objectColor};"
                title="Base color"
                aria-label="Base color"
                onclick={(e) => {
                    const popover = document.getElementById(
                        "object-color-popover",
                    );
                    if (popover?.showPopover) {
                        popover.showPopover();
                        positionColorPopover(popover, e.currentTarget);
                    }
                }}
            ></button>
            <button
                type="button"
                class="w-8 h-8 rounded-lg border-2 border-slate-300 shadow-sm hover:border-slate-400 touch-manipulation transition-colors"
                style="background-color: {keycapColor};"
                title="Keycaps color"
                aria-label="Keycaps color"
                onclick={(e) => {
                    const popover = document.getElementById(
                        "keycap-color-popover",
                    );
                    if (popover?.showPopover) {
                        popover.showPopover();
                        positionColorPopover(popover, e.currentTarget);
                    }
                }}
            ></button>
            <button
                type="button"
                class="w-8 h-8 rounded-lg border-2 border-slate-300 shadow-sm hover:border-slate-400 touch-manipulation transition-colors"
                style="background-color: {textBorderColor};"
                title="Legend color"
                aria-label="Legend color"
                onclick={(e) => {
                    const popover = document.getElementById(
                        "text-border-color-popover",
                    );
                    if (popover?.showPopover) {
                        popover.showPopover();
                        positionColorPopover(popover, e.currentTarget);
                    }
                }}
            ></button>

            <label
                class="flex items-center gap-1.5 cursor-pointer touch-manipulation"
            >
                <input
                    type="checkbox"
                    class="w-3.5 h-3.5 rounded border-slate-300 text-brand focus:ring-brand"
                    checked={showBorder}
                    onchange={(e) =>
                        updateActiveDesign({
                            showBorder: e.currentTarget.checked,
                        })}
                    aria-label="Show border"
                />
                <span class="text-[11px] text-slate-500 font-medium select-none"
                    >Border</span
                >
            </label>
        </div>
        <div class="relative flex-1 min-h-0 min-w-0">
            <main class="canvas-wrap flex-1 min-h-0 min-w-0 h-full">
                <Canvas toneMapping={NoToneMapping}>
                    <Scene
                        {objectColor}
                        {keycapColor}
                        {textBorderColor}
                        {showBorder}
                        {numberOfKeys}
                        keycapPositions={keycapPositionsForScene}
                        {keycapLetters}
                        keycapSvgUrls={keycapSvgUrlsForScene}
                        keycapSvgSizeMm={keycapSvgSizeMm}
                        snapshotReady={(fn) => {
                            takeSnapshot = fn;
                        }}
                        onSnapshotDownloaded={() => {
                            showSnapshotThankYou = true;
                        }}
                        exportKeycapStlReady={(fn) => {
                            exportKeycapStl = fn;
                        }}
                        onKeycapStlDownloaded={() => {}}
                    />
                </Canvas>
            </main>
            <button
                type="button"
                class="absolute bottom-4 right-32 md:right-28 w-12 h-12 md:w-10 md:h-10 flex items-center justify-center rounded-full bg-white border-2 border-slate-300 shadow-lg text-slate-600 hover:text-brand hover:border-brand touch-manipulation z-[50] hover:bg-brand-light"
                title="Save snapshot (front + top view)"
                aria-label="Save snapshot (front and top view)"
                onclick={() => takeSnapshot?.()}
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                >
                    <path
                        d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                    />
                    <path d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path d="M19 17v-2a2 2 0 00-2-2H7a2 2 0 00-2 2v2" />
                </svg>
            </button>
            <button
                type="button"
                class="absolute bottom-4 right-20 md:right-16 w-12 h-12 md:w-10 md:h-10 flex items-center justify-center rounded-full bg-white border-2 border-slate-300 shadow-lg text-slate-600 hover:text-brand hover:border-brand touch-manipulation z-[50] hover:bg-brand-light"
                title="Download keycap STL (one file per keycap: keycap + border + letter/SVG)"
                aria-label="Download keycap STL"
                onclick={() => exportKeycapStl?.()}
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                >
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2 2v-4" />
                    <path d="M7 10l5 5 5-5" />
                    <path d="M12 15V3" />
                </svg>
            </button>
            <button
                type="button"
                class="absolute bottom-4 right-4 w-12 h-12 md:w-10 md:h-10 flex items-center justify-center rounded-full bg-white border-2 border-slate-300 shadow-lg text-slate-600 hover:text-red-600 hover:border-red-200 touch-manipulation z-[50] {designs.length <=
                1
                    ? 'opacity-60 cursor-not-allowed pointer-events-none'
                    : 'hover:bg-red-50'}"
                title={designs.length <= 1
                    ? "Add another design to delete"
                    : "Delete current design"}
                aria-label={designs.length <= 1
                    ? "Add another design to delete"
                    : "Delete current design"}
                disabled={designs.length <= 1}
                onclick={() =>
                    designs.length > 1 && (deleteConfirmIndex = activeIndex)}
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                >
                    <path
                        d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"
                    />
                    <path d="M10 11v6M14 11v6" />
                </svg>
            </button>
        </div>
        <div
            class="flex-shrink-0 flex items-center gap-1 px-2 py-2 md:px-3 md:py-2.5 bg-surface border-t border-brand-border overflow-x-auto"
        >
            {#each designs as design, i (design.id)}
                <button
                    type="button"
                    class="flex-shrink-0 py-1 px-2 rounded-md border touch-manipulation min-h-[44px] md:min-h-0 text-[13px] font-medium whitespace-nowrap {i ===
                    activeIndex
                        ? 'bg-brand border-brand text-white'
                        : 'bg-white border-slate-200 text-slate-500 hover:text-slate-800'}"
                    onclick={() => (activeIndex = i)}
                    title={design.name}
                >
                    {design.name}
                </button>
            {/each}
            <button
                type="button"
                class="flex-shrink-0 py-2 px-2.5 text-lg leading-none rounded border border-slate-200 bg-white text-slate-500 hover:border-slate-400 hover:text-slate-700 touch-manipulation min-h-[44px] md:min-h-0 min-w-8"
                title="Add design"
                aria-label="Add design"
                onclick={addDesign}
            >
                +
            </button>
        </div>
    </div>
</div>

<style>
    /* Threlte Canvas needs min-height:0 to fill flex area */
    .canvas-wrap {
        min-height: 0;
    }
</style>
