export type AppTheme = "light" | "dark";

const themeStorageKey = "class_agent_theme";
const themePreferenceStorageKey = "class_agent_theme_preference";
const legacyHomeThemeStorageKey = "class_agent_home_theme";
const themeEventName = "class-agent-theme-change";
const lightThemeStartHour = 7;
const darkThemeStartHour = 19;

function themeTargets() {
  return [document.documentElement, document.body, document.getElementById("app")].filter(
    (item): item is HTMLElement => item instanceof HTMLElement,
  );
}

function isAppTheme(value: string | null): value is AppTheme {
  return value === "light" || value === "dark";
}

function readStoredThemePreference(): AppTheme | "auto" {
  try {
    const value = localStorage.getItem(themePreferenceStorageKey);
    return value === "auto" || isAppTheme(value) ? value : "auto";
  } catch {
    return "auto";
  }
}

function resolveTimeTheme(now = new Date()): AppTheme {
  const hour = now.getHours();
  return hour >= darkThemeStartHour || hour < lightThemeStartHour ? "dark" : "light";
}

function resolveTheme(preference = readStoredThemePreference()): AppTheme {
  return preference === "auto" ? resolveTimeTheme() : preference;
}

function millisecondsUntilNextThemeFlip(now = new Date()) {
  const next = new Date(now);
  if (now.getHours() >= darkThemeStartHour) {
    next.setDate(next.getDate() + 1);
    next.setHours(lightThemeStartHour, 0, 0, 0);
  } else if (now.getHours() >= lightThemeStartHour) {
    next.setHours(darkThemeStartHour, 0, 0, 0);
  } else {
    next.setHours(lightThemeStartHour, 0, 0, 0);
  }
  return Math.max(1000, next.getTime() - now.getTime() + 1000);
}

export function readStoredTheme(): AppTheme {
  return resolveTheme();
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
    localStorage.setItem(themePreferenceStorageKey, theme);
    localStorage.setItem(themeStorageKey, theme);
    localStorage.setItem(legacyHomeThemeStorageKey, theme);
  } catch {
    // Storage can fail in private browsing; the in-memory theme still applies.
  }
  applyAppTheme(theme);
  window.dispatchEvent(new CustomEvent<{ theme: AppTheme }>(themeEventName, { detail: { theme } }));
}

export function subscribeAppTheme(handler: (theme: AppTheme) => void) {
  let autoTimer = 0;
  const emitResolvedTheme = () => {
    const theme = resolveTheme();
    handler(theme);
    if (autoTimer) window.clearTimeout(autoTimer);
    if (readStoredThemePreference() === "auto") {
      autoTimer = window.setTimeout(emitResolvedTheme, millisecondsUntilNextThemeFlip());
    }
  };
  const onThemeChange = (event: Event) => {
    const theme = (event as CustomEvent<{ theme?: AppTheme }>).detail?.theme;
    if (theme === "light" || theme === "dark") {
      handler(theme);
      if (autoTimer) window.clearTimeout(autoTimer);
    } else {
      emitResolvedTheme();
    }
  };
  const onStorage = (event: StorageEvent) => {
    if (
      event.key === themePreferenceStorageKey ||
      event.key === themeStorageKey ||
      event.key === legacyHomeThemeStorageKey
    ) {
      emitResolvedTheme();
    }
  };
  const onVisibilityChange = () => {
    if (!document.hidden) emitResolvedTheme();
  };
  const onFocus = () => emitResolvedTheme();
  emitResolvedTheme();
  window.addEventListener(themeEventName, onThemeChange);
  window.addEventListener("storage", onStorage);
  document.addEventListener("visibilitychange", onVisibilityChange);
  window.addEventListener("focus", onFocus);
  return () => {
    if (autoTimer) window.clearTimeout(autoTimer);
    window.removeEventListener(themeEventName, onThemeChange);
    window.removeEventListener("storage", onStorage);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    window.removeEventListener("focus", onFocus);
  };
}
