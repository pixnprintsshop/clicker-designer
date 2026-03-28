import coinyUrl from "../assets/font/Coiny_Regular.json?url";
import daffiysUrl from "../assets/font/Daffiys_Regular.json?url";
import dynapuffUrl from "../assets/font/DynaPuff_Bold.json?url";
import kindergoUrl from "../assets/font/Kindergo_Regular.json?url";
import milkywayUrl from "../assets/font/Milkyway_Regular.json?url";
import roadsideUrl from "../assets/font/Roadside Sans_Regular.json?url";
import showpopUrl from "../assets/font/Showpop_Regular.json?url";
import titanUrl from "../assets/font/Titan One_Regular.json?url";

export interface KeycapFontOption {
    id: string;
    label: string;
    typefaceUrl: string;
    /** Full inline style for the font name in the selector (Google Fonts in index.html). */
    previewStyle: string;
}

export const DEFAULT_KEYCAP_FONT_ID = "daffiys";

/** Order: display order in UI. Typeface JSON paths under src/assets/font. */
export const KEYCAP_FONT_OPTIONS: KeycapFontOption[] = [
    {
        id: "daffiys",
        label: "Daffiys",
        typefaceUrl: daffiysUrl,
        previewStyle:
            "font-family: 'Sniglet', system-ui, cursive; font-size: 1.05rem;",
    },
    {
        id: "coiny",
        label: "Coiny",
        typefaceUrl: coinyUrl,
        previewStyle:
            "font-family: 'Coiny', system-ui, fantasy; font-size: 1.05rem;",
    },
    {
        id: "dynapuff",
        label: "DynaPuff",
        typefaceUrl: dynapuffUrl,
        previewStyle:
            "font-family: 'Dyna Puff', system-ui, sans-serif; font-weight: 700; font-size: 1.05rem;",
    },
    {
        id: "kindergo",
        label: "Kindergo",
        typefaceUrl: kindergoUrl,
        previewStyle:
            "font-family: 'Kindergo', system-ui, sans-serif; font-size: 1.05rem;",
    },
    {
        id: "milkyway",
        label: "Milkyway",
        typefaceUrl: milkywayUrl,
        previewStyle:
            "font-family: 'Nunito', system-ui, sans-serif; font-weight: 800; font-size: 1.05rem;",
    },
    {
        id: "roadside",
        label: "Roadside Sans",
        typefaceUrl: roadsideUrl,
        previewStyle:
            "font-family: 'Rubik', system-ui, sans-serif; font-weight: 600; font-size: 1.05rem;",
    },
    {
        id: "showpop",
        label: "Showpop",
        typefaceUrl: showpopUrl,
        previewStyle:
            "font-family: 'Bowlby One SC', system-ui, sans-serif; font-size: 0.95rem;",
    },
    {
        id: "titan",
        label: "Titan One",
        typefaceUrl: titanUrl,
        previewStyle:
            "font-family: 'Titan One', system-ui, sans-serif; font-size: 1.05rem;",
    },
];

const BY_ID = new Map(KEYCAP_FONT_OPTIONS.map((f) => [f.id, f]));

export function getKeycapFontOption(id: string): KeycapFontOption {
    return BY_ID.get(id) ?? KEYCAP_FONT_OPTIONS[0]!;
}

export function normalizeKeycapFontId(id: string | undefined): string {
    if (id && BY_ID.has(id)) return id;
    return DEFAULT_KEYCAP_FONT_ID;
}
