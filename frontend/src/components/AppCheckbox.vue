<template>
  <button
    type="button"
    class="app-checkbox"
    :class="[variant, { checked: modelValue, disabled }]"
    :disabled="disabled"
    :role="variant === 'switch' ? 'switch' : 'checkbox'"
    :aria-checked="modelValue"
    @click="toggle"
  >
    <span v-if="variant === 'switch'" class="switch-track"><i></i></span>
    <span v-else class="check-box"><Check v-if="modelValue" :size="13" /></span>
    <span v-if="label || $slots.default" class="check-label"><slot>{{ label }}</slot></span>
  </button>
</template>

<script setup lang="ts">
import { Check } from "../icons";

const props = withDefaults(defineProps<{
  modelValue: boolean;
  label?: string;
  disabled?: boolean;
  variant?: "box" | "switch";
}>(), {
  label: "",
  disabled: false,
  variant: "box"
});

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  change: [value: boolean];
}>();

function toggle() {
  if (props.disabled) return;
  const next = !props.modelValue;
  emit("update:modelValue", next);
  emit("change", next);
}
</script>

<style scoped>
.app-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0;
  text-align: left;
  transition: color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.app-checkbox:active:not(:disabled) {
  transform: scale(.97);
}
.app-checkbox:hover:not(:disabled) {
  color: var(--color-text-primary);
}
.app-checkbox:hover:not(:disabled) .check-box,
.app-checkbox:hover:not(:disabled) .switch-track {
  border-color: var(--color-primary-400);
  box-shadow: var(--shadow-sm);
}
.check-box {
  width: 20px;
  height: 20px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 20px;
  border: 1px solid var(--color-border-strong);
  border-radius: 5px;
  background: var(--color-bg-surface);
  color: white;
  box-shadow: inset 0 0 0 0 var(--color-primary-600);
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
}
.app-checkbox.checked .check-box {
  border-color: var(--color-primary-600);
  background: var(--color-primary-600);
  box-shadow: inset 0 0 0 9px var(--color-primary-600);
}
.check-label {
  line-height: 20px;
}
.switch-track {
  width: 44px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  flex: 0 0 42px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  padding: 2px;
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.switch-track i {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  box-shadow: var(--shadow-sm);
  transform: translateX(0);
  transition: transform var(--duration-base) var(--ease-spring), background var(--duration-fast) var(--ease-out);
}
.app-checkbox.switch.checked .switch-track {
  border-color: var(--color-primary-600);
  background: var(--color-primary-600);
}
.app-checkbox.switch.checked .switch-track i {
  transform: translateX(18px);
}
.app-checkbox.disabled {
  opacity: .55;
  cursor: not-allowed;
}
</style>
