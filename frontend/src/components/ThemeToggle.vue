<template>
  <button
    type="button"
    class="theme-toggle-control"
    :class="{ 'is-light': theme === 'light', 'is-dark': theme === 'dark' }"
    role="switch"
    :aria-checked="theme === 'dark'"
    :aria-label="label"
    :title="label"
    @click="toggleTheme"
  >
    <Sun :size="15" />
    <Moon :size="15" />
    <span aria-hidden="true"></span>
  </button>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Moon, Sun } from "../icons";
import { applyAppTheme, readStoredTheme, setStoredTheme, subscribeAppTheme, type AppTheme } from "../theme";

const theme = ref<AppTheme>(readStoredTheme());
const label = computed(() => (theme.value === "dark" ? "切换浅色主题" : "切换深色主题"));
let unsubscribe: (() => void) | null = null;

function toggleTheme() {
  setStoredTheme(theme.value === "dark" ? "light" : "dark");
}

onMounted(() => {
  applyAppTheme(theme.value);
  unsubscribe = subscribeAppTheme((nextTheme) => {
    theme.value = nextTheme;
    applyAppTheme(nextTheme);
  });
});

onBeforeUnmount(() => {
  unsubscribe?.();
});
</script>

<style scoped>
.theme-toggle-control {
  --theme-toggle-shift: 28px;

  position: relative;
  width: 62px;
  height: 34px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 7%, transparent);
  color: var(--color-text-secondary);
  padding: 0 9px;
  box-shadow: none;
}

.theme-toggle-control:hover {
  border-color: transparent;
  background: color-mix(in srgb, currentColor 10%, transparent);
}

.theme-toggle-control svg {
  position: relative;
  z-index: 2;
  background: transparent !important;
  box-shadow: none !important;
}

.theme-toggle-control > span {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 1;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, currentColor 16%, transparent);
  transition: transform 240ms cubic-bezier(.22, .61, .36, 1), background-color 200ms, box-shadow 200ms;
}

.theme-toggle-control.is-dark > span {
  transform: translateX(var(--theme-toggle-shift));
}

.theme-toggle-control.is-light svg:first-child {
  color: #B45309;
}

.theme-toggle-control.is-dark svg:last-of-type {
  color: #67E8F9;
}
</style>
