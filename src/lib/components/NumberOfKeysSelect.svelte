<script>
    import * as Select from "$lib/components/ui/select/index.js";

    /** @type {{ value: number, onChange: (n: number) => void, compact?: boolean }} */
    let { value, onChange, compact = false } = $props();

    const keys = Array.from({ length: 7 }, (_, i) => i + 1);
</script>

<Select.Select
    type="single"
    value={String(value)}
    onValueChange={(v) => {
        const n = parseInt(String(v), 10);
        if (!Number.isNaN(n) && n >= 1 && n <= 7) onChange(n);
    }}
>
    <Select.SelectTrigger
        class={compact
            ? "h-8 min-w-[3rem] border-slate-300"
            : "w-full min-h-11 border-slate-200"}
        aria-label="Number of keys"
    >
        {#if compact}
            {value}
        {:else}
            {value} key{value === 1 ? "" : "s"}
        {/if}
    </Select.SelectTrigger>
    <Select.SelectContent>
        {#each keys as n}
            <Select.SelectItem
                value={String(n)}
                label={compact
                    ? String(n)
                    : `${n} key${n === 1 ? "" : "s"}`}
            />
        {/each}
    </Select.SelectContent>
</Select.Select>
