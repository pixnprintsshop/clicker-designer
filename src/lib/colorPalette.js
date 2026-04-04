/** Preset palette: specific colors only (grid in popover) */
export const COLOR_PALETTE = [
    { color: "#000000", name: "Black" },
    { color: "#ffffff", name: "White" },
    { color: "#5dadfa", name: "Blue" },
    { color: "#0d18a8", name: "Navy" },
    { color: "#141f41", name: "Dark Blue" },
    { color: "#eeb9ba", name: "Peach Pink" },
    { color: "#ff7e94", name: "Pink" },
    { color: "#562fa7", name: "Purple" },
    { color: "#7174c0", name: "Very Peri" },
    { color: "#d29dcd", name: "Lilac" },
    { color: "#9bf5c8", name: "Min Green" },
    { color: "#83ed64", name: "Green" },
    { color: "#acb26d", name: "Matcha Green" },
    { color: "#03452e", name: "Dark Green" },
    { color: "#ffeb47", name: "Yellow" },
    { color: "#f5541b", name: "Orange" },
    { color: "#d23724", name: "Red" },
    { color: "#c22856", name: "Magenta" },
    { color: "#d9b99b", name: "Beige" },
    { color: "#623411", name: "Brown" },
    { color: "#722427", name: "Brick Red" },
    { color: "#686c6f", name: "Grey" },
];

/**
 * @param {string} hex
 */
export function colorLabelForHex(hex) {
    const n = (hex || "").trim().toLowerCase();
    const row = COLOR_PALETTE.find((p) => p.color.toLowerCase() === n);
    return row?.name ?? hex;
}
