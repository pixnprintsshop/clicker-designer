<script>
    import * as Popover from "$lib/components/ui/popover/index.js";
    import { COLOR_PALETTE } from "$lib/colorPalette.js";

    /**
     * @typedef {{ color: string, name: string }} PaletteEntry
     */

    /** @type {{ currentColor: string, onPick: (hex: string) => void, compact?: boolean, title?: string, ariaLabel?: string, legendStyle?: boolean }} */
    let {
        currentColor,
        onPick,
        compact = false,
        title = "",
        ariaLabel = "Choose color",
        legendStyle = false,
    } = $props();

    let open = $state(false);
    /** @type {number | null} */
    let hoveredIndex = $state(null);

    const swatchBase =
        "w-7 h-7 p-0 rounded-md cursor-pointer relative transition-all hover:scale-105 hover:border-slate-400 touch-manipulation";
    const swatchBorder = $derived(
        legendStyle ? "border-2 border-transparent" : "border border-gray-300",
    );
    const swatchSelected = "border-slate-800 ring-1 ring-white ring-inset";
</script>

<Popover.Popover bind:open>
    <Popover.PopoverTrigger>
        {#snippet child({ props })}
            {#if compact}
                <button
                    {...props}
                    type="button"
                    class="w-8 h-8 rounded-lg border-2 border-slate-300 shadow-sm hover:border-slate-400 touch-manipulation transition-colors shrink-0"
                    style="background-color: {currentColor};"
                    {title}
                    aria-label={ariaLabel}
                ></button>
            {:else}
                <button
                    {...props}
                    type="button"
                    class="flex items-center gap-2 w-full px-2 py-2.5 text-[13px] border border-slate-200 rounded-md bg-white text-slate-800 text-left cursor-pointer hover:border-slate-300 hover:bg-slate-50 min-h-[44px] touch-manipulation"
                    {title}
                    aria-label={ariaLabel}
                >
                    <span
                        class="w-6 h-6 rounded border border-slate-200 shrink-0"
                        style="background-color: {currentColor};"
                    ></span>
                    <span class="text-xs font-mono text-slate-500"
                        >{currentColor}</span
                    >
                </button>
            {/if}
        {/snippet}
    </Popover.PopoverTrigger>
    <Popover.PopoverContent class="w-auto p-3" align="start" side="bottom">
        <div class="grid grid-cols-6 gap-1.5">
            {#each COLOR_PALETTE as { color, name }, idx}
                <button
                    type="button"
                    class="{swatchBase} {swatchBorder} {currentColor === color
                        ? swatchSelected
                        : ''}"
                    style="background-color: {color};"
                    title="{name} ({color})"
                    aria-label="Color {name}"
                    onmouseenter={() => (hoveredIndex = idx)}
                    onmouseleave={() => (hoveredIndex = null)}
                    onclick={() => {
                        onPick(color);
                        open = false;
                    }}
                >
                    {#if currentColor === color}
                        <span
                            class="absolute inset-0 flex items-center justify-center text-sm font-bold text-white drop-shadow-sm"
                            aria-hidden="true">✓</span
                        >
                    {/if}
                </button>
            {/each}
        </div>
        {#if hoveredIndex !== null}
            <div class="pt-2 text-center">
                <span
                    class="inline-block text-xs font-medium text-slate-600 px-2 py-1 bg-slate-100 rounded"
                    >{COLOR_PALETTE[hoveredIndex]?.name}</span
                >
            </div>
        {/if}
    </Popover.PopoverContent>
</Popover.Popover>
