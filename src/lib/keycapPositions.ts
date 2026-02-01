/**
 * Default keycap positions per key count (1–7). Copy values from the UI controls into here.
 * Each entry is [x, y, z] in mm: x/z = horizontal, y = height offset from clicker top (0 = on clicker).
 * Keycaps are centered; height defaults to clicker top.
 */
export const KEYCAP_POSITIONS: [number, number, number][][] = [
    [[4.5, 0, 0]], // 1 key (centered; y=0 = on clicker)
    [[-6.5, 0, 0], [15.5, 0, 0]], // 2 keys
    [[-17.7, 0, 0], [4.5, 0, 0], [26.7, 0, 0]], // 3 keys
    [[-28.8, 0, 0], [-6.6, 0, 0], [15.6, 0, 0], [37.8, 0, 0]], // 4 keys
    [[-39.9, 0, 0], [-17.7, 0, 0], [4.5, 0, 0], [26.7, 0, 0], [48.8, 0, 0]], // 5 keys
    [[-51, 0, 0], [-28.8, 0, -0], [-6.7, 0, 0], [15.5, 0, 0], [37.7, 0, 0], [60, 0, 0]], // 6 keys
    [
        [-62, 0, 0],
        [-40, 0, 0],
        [-17.8, 0, 0],
        [4.5, 0, 0],
        [26.7, 0, 0],
        [49, 0, 0],
        [71, 0, 0],
    ], // 7 keys
];
