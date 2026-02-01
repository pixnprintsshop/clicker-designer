/**
 * Predefined SVGs from src/assets/svg. Used by the keycap SVG picker.
 * Keys are filenames (e.g. "heart.svg"); values are resolved URLs.
 */
const modules = import.meta.glob<string>("../assets/svg/*.svg", {
    query: "?url",
    import: "default",
    eager: true,
});

export interface SvgAsset {
    id: string;
    name: string;
    url: string;
}

const nameFromId = (id: string): string => {
    const base = id.replace(/\.svg$/i, "");
    return base
        .split(/[-_]/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
        .join(" ");
};

export const SVG_ASSETS: SvgAsset[] = Object.entries(modules).map(
    ([path, mod]) => {
        const filename = path.replace(/^.*\//, "");
        const url =
            typeof mod === "string"
                ? mod
                : (mod as { default: string })?.default ?? "";
        return {
            id: filename,
            name: nameFromId(filename),
            url,
        };
    }
);

/** Map id (filename) -> url for quick lookup */
export const SVG_URL_BY_ID = new Map(SVG_ASSETS.map((a) => [a.id, a.url]));
