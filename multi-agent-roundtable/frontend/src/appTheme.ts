export type AppThemeId = "telegram-blue" | "spy-manga" | "mythic-china";

export type AppTheme = {
  id: AppThemeId;
  name: string;
  nameZh: string;
  description: string;
  className: string;
  swatches: string[];
  previewBackground: string;
  preview: {
    background: string;
    rail: string;
    surface: string;
    selectedRow: string;
    humanBubble: string;
    agentBubble: string;
    composer: string;
    accent: string;
    accentStrong: string;
    text: string;
    muted: string;
    line: string;
    status: string;
  };
  agentAvatars: Partial<Record<string, string>>;
  agentPersonas: Partial<Record<string, { name: string; initials: string }>>;
};

export type AppThemeStorage = Pick<Storage, "getItem" | "setItem">;

export const appThemeStorageKey = "agentelegram_app_theme";
export const defaultAppThemeId: AppThemeId = "telegram-blue";

export const APP_THEMES: AppTheme[] = [
  {
    id: "telegram-blue",
    name: "Telegram Blue",
    nameZh: "电报码蓝",
    description: "Current calm blue workspace, kept as the practical default.",
    className: "theme-telegram-blue",
    swatches: ["#eef5fa", "#fbfdff", "#1685d8", "#20364a", "#118566"],
    previewBackground: "linear-gradient(135deg, #f4f9fd 0%, #e4f0f8 58%, #fbfdff 100%)",
    preview: {
      background: "linear-gradient(135deg, #f4f9fd 0%, #e4f0f8 58%, #fbfdff 100%)",
      rail: "#20364a",
      surface: "#fbfdff",
      selectedRow: "#dceffd",
      humanBubble: "#c9e5f7",
      agentBubble: "#fbfdff",
      composer: "#f7fbfe",
      accent: "#1685d8",
      accentStrong: "#0f6fb8",
      text: "#1d2b3a",
      muted: "#5d7182",
      line: "rgba(31, 62, 90, 0.14)",
      status: "#118566",
    },
    agentAvatars: {
      main: "/theme-avatars/default-main.png",
      kai: "/theme-avatars/default-kai.png",
      sarah: "/theme-avatars/default-sarah.png",
      alex: "/theme-avatars/default-alex.png",
    },
    agentPersonas: {},
  },
  {
    id: "spy-manga",
    name: "Manga Spy Room",
    nameZh: "日漫间谍室",
    description: "Warm spy-comedy manga mood with original agent portraits.",
    className: "theme-spy-manga",
    swatches: ["#f2dfbd", "#fff7e6", "#b7382f", "#26382d", "#476f86"],
    previewBackground: "linear-gradient(135deg, #f6e7c7 0%, #efd0b1 50%, #d7e1d2 100%)",
    preview: {
      background: "linear-gradient(135deg, #f6e7c7 0%, #efd0b1 50%, #d7e1d2 100%)",
      rail: "#26382d",
      surface: "#fff7e6",
      selectedRow: "#f2d0b9",
      humanBubble: "#f4d3b8",
      agentBubble: "#fff7e6",
      composer: "#fbecd3",
      accent: "#b7382f",
      accentStrong: "#8c2d26",
      text: "#261f18",
      muted: "#665140",
      line: "rgba(82, 53, 34, 0.18)",
      status: "#476f86",
    },
    agentAvatars: {
      main: "/theme-avatars/spy-main.png",
      kai: "/theme-avatars/spy-kai.png",
      sarah: "/theme-avatars/spy-sarah.png",
      alex: "/theme-avatars/spy-alex.png",
    },
    agentPersonas: {
      main: { name: "main", initials: "A" },
      kai: { name: "kai", initials: "R" },
      sarah: { name: "sarah", initials: "S" },
      alex: { name: "alex", initials: "M" },
    },
  },
  {
    id: "mythic-china",
    name: "Mythic China",
    nameZh: "山海神话",
    description: "Jade, bronze, ink, and mineral-pigment colors with mythic agents.",
    className: "theme-mythic-china",
    swatches: ["#e6dcc2", "#fbf3e3", "#0b6f68", "#9a651b", "#8b2635"],
    previewBackground: "linear-gradient(135deg, #efe3c7 0%, #dce7d7 46%, #b5cec0 100%)",
    preview: {
      background: "linear-gradient(135deg, #efe3c7 0%, #dce7d7 46%, #b5cec0 100%)",
      rail: "#123833",
      surface: "#fbf3e3",
      selectedRow: "#d5e9df",
      humanBubble: "#d2e7db",
      agentBubble: "#fbf3e3",
      composer: "#f5ead5",
      accent: "#0b6f68",
      accentStrong: "#07544f",
      text: "#1f302c",
      muted: "#586459",
      line: "rgba(48, 83, 71, 0.18)",
      status: "#9a651b",
    },
    agentAvatars: {
      main: "/theme-avatars/myth-main.png",
      kai: "/theme-avatars/myth-kai.png",
      sarah: "/theme-avatars/myth-sarah.png",
      alex: "/theme-avatars/myth-alex.png",
    },
    agentPersonas: {
      main: { name: "main", initials: "F" },
      kai: { name: "kai", initials: "P" },
      sarah: { name: "sarah", initials: "C" },
      alex: { name: "alex", initials: "N" },
    },
  },
];

export function getAppTheme(themeId: AppThemeId): AppTheme {
  return APP_THEMES.find((theme) => theme.id === themeId) ?? APP_THEMES[0];
}

export function normalizeAppThemeId(value: unknown): AppThemeId {
  return APP_THEMES.some((theme) => theme.id === value) ? (value as AppThemeId) : defaultAppThemeId;
}

export function readAppThemeId(storage: AppThemeStorage | undefined = browserStorage()): AppThemeId {
  return normalizeAppThemeId(storage?.getItem(appThemeStorageKey));
}

export function writeAppThemeId(
  storage: AppThemeStorage | undefined = browserStorage(),
  themeId: AppThemeId,
): AppThemeId {
  const normalized = normalizeAppThemeId(themeId);
  storage?.setItem(appThemeStorageKey, normalized);
  return normalized;
}

function browserStorage(): AppThemeStorage | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}
