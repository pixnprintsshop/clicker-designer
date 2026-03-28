<script lang="ts">
    import { Button } from "$lib/components/ui/button";
    import * as Command from "$lib/components/ui/command";
    import * as Popover from "$lib/components/ui/popover";
    import {
      KEYCAP_FONT_OPTIONS,
      getKeycapFontOption,
    } from "$lib/keycapFonts";
    import { untrack } from "svelte";
    import type { ButtonProps } from "./ui/button";

    /** @type {{ keycapFontId: string, onPick: (id: string) => void }} */
    let { keycapFontId, onPick } = $props();

    let open = $state(false);

    /** Remount Command when opening so the search field resets. */
    let commandKey = $state(0);
    $effect(() => {
        if (!open) return;
        untrack(() => {
            commandKey += 1;
        });
    });
</script>

<div class="flex flex-col gap-2">
    <span class="text-[13px] font-medium text-slate-700">Letter font</span>
    <Popover.Popover bind:open>
        <Popover.PopoverTrigger>
            {#snippet child({ props }: { props: ButtonProps })}
                <Button
                    {...props}
                    variant="outline"
                    type="button"
                    class="h-auto min-h-11 w-full justify-start border-slate-200 py-2.5 text-left font-normal"
                    aria-label="Choose letter font"
                    aria-expanded={open}
                >
                    <span style={getKeycapFontOption(keycapFontId).previewStyle}>
                        {getKeycapFontOption(keycapFontId).label}
                    </span>
                </Button>
            {/snippet}
        </Popover.PopoverTrigger>
        <Popover.PopoverContent
            class="w-[min(calc(100vw-24px),320px)] gap-0 p-0"
            align="start"
        >
            {#key commandKey}
                <Command.Command
                    label="Letter fonts"
                    class="rounded-lg border-0 shadow-none"
                >
                    <Command.CommandInput
                        placeholder="Search fonts…"
                        aria-label="Search fonts"
                    />
                    <Command.CommandList class="max-h-[min(60vh,360px)]">
                        <Command.CommandEmpty>No font found.</Command.CommandEmpty>
                        {#each KEYCAP_FONT_OPTIONS as fontOpt (fontOpt.id)}
                            <Command.CommandItem
                                value={fontOpt.id}
                                keywords={[fontOpt.label, fontOpt.id]}
                                class="h-auto cursor-pointer py-2.5 font-normal {keycapFontId ===
                                fontOpt.id
                                    ? 'border-2 border-brand bg-brand-light'
                                    : 'border-2 border-transparent'}"
                                onSelect={() => {
                                    onPick(fontOpt.id);
                                    open = false;
                                }}
                            >
                                <span style={fontOpt.previewStyle}
                                    >{fontOpt.label}</span
                                >
                            </Command.CommandItem>
                        {/each}
                    </Command.CommandList>
                </Command.Command>
            {/key}
        </Popover.PopoverContent>
    </Popover.Popover>
</div>
