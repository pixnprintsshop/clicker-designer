const STORAGE_KEY = "clicker-designer-config";

export interface StoredDesign {
    id: string;
    name: string;
    objectColor?: string;
    keycapColor?: string;
    textBorderColor?: string;
    showBorder?: boolean;
    numberOfKeys?: number;
    keycapPositionsByCount?: Record<string, { x: number; y: number; z: number }[]>;
    keycapLettersByCount?: Record<string, string[]>;
    keycapSvgByCount?: Record<string, (string | null)[]>;
    /** SVG size on keycap in mm (width and height, aspect ratio kept). */
    keycapSvgSizeMm?: number;
}

export interface StoredConfig {
    designs?: StoredDesign[];
    activeIndex?: number;
}

export function loadConfig(): StoredConfig | null {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (data && typeof data === "object") return data;
    } catch (_) { }
    return null;
}

export function saveConfig(config: StoredConfig): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    } catch (_) { }
}
