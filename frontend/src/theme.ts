export type AppTheme = "light" | "dark";

const themeStorageKey = "class_agent_theme";
const legacyHomeThemeStorageKey = "class_agent_home_theme";
const themeEventName = "class-agent-theme-change";

function themeTargets() {
  return [document.documentElement, document.body, document.getElementById("app")].filter(
    (item): item is HTMLElement => item instanceof HTMLElement,
  );
}

export function readStoredTheme(): AppTheme {
  try {
    const value = localStorage.getItem(themeStorageKey) || localStorage.getItem(legacyHomeThemeStorageKey);
    return value === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function applyAppTheme(theme: AppTheme) {
  const isDark = theme === "dark";
  themeTargets().forEach((element) => {
    element.classList.toggle("theme-dark", isDark);
    element.classList.toggle("theme-light", !isDark);
  });
  document.documentElement.dataset.theme = theme;
}

export function setStoredTheme(theme: AppTheme) {
  try {
    localStorage.setItem(themeStorageKey, theme);
    localStorage.setItem(legacyHomeThemeStorageKey, theme);
  } catch {
    // Storage can fail in private browsing; the in-memory theme still applies.
  }
  applyAppTheme(theme);
  window.dispatchEvent(new CustomEvent<{ theme: AppTheme }>(themeEventName, { detail: { theme } }));
}

export function subscribeAppTheme(handler: (theme: AppTheme) => void) {
  const onThemeChange = (event: Event) => {
    const theme = (event as CustomEvent<{ theme?: AppTheme }>).detail?.theme;
    if (theme === "light" || theme === "dark") handler(theme);
  };
  const onStorage = (event: StorageEvent) => {
    if (event.key === themeStorageKey || event.key === legacyHomeThemeStorageKey) {
      handler(readStoredTheme());
    }
  };
  window.addEventListener(themeEventName, onThemeChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(themeEventName, onThemeChange);
    window.removeEventListener("storage", onStorage);
  };
}
