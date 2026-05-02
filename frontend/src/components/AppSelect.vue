<template>
  <div ref="rootRef" class="app-select" :class="{ open, disabled }">
    <button
      type="button"
      class="app-select-trigger"
      :disabled="disabled"
      :aria-expanded="open"
      @click="toggle"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="move(-1)"
      @keydown.enter.prevent="open ? choose(activeIndex) : toggle()"
      @keydown.space.prevent="open ? choose(activeIndex) : toggle()"
      @keydown.esc.prevent="close"
    >
      <span>{{ currentLabel }}</span>
      <ChevronDown :size="15" />
    </button>
    <Transition name="popover">
      <div v-if="open" class="app-select-pop" role="listbox">
        <button
          v-for="(item, index) in normalizedOptions"
          :key="`${item.value}`"
          type="button"
          role="option"
          :aria-selected="isSelected(item.value)"
          :class="{ active: isSelected(item.value), danger: item.danger, focused: index === activeIndex }"
          @mouseenter="activeIndex = index"
          @click="choose(index)"
        >
          <span>{{ item.label }}</span>
          <Check v-if="isSelected(item.value)" :size="14" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Check, ChevronDown } from "lucide-vue-next";

type SelectValue = string | number | boolean | null;
type SelectOption = { label: string; value: SelectValue; danger?: boolean };

const props = withDefaults(defineProps<{
  modelValue: SelectValue;
  options: Array<SelectOption | string | number>;
  placeholder?: string;
  disabled?: boolean;
}>(), {
  placeholder: "请选择",
  disabled: false
});

const emit = defineEmits<{
  "update:modelValue": [value: SelectValue];
  change: [value: SelectValue];
}>();

const rootRef = ref<HTMLElement | null>(null);
const open = ref(false);
const activeIndex = ref(0);

const normalizedOptions = computed<SelectOption[]>(() =>
  props.options.map((item) => {
    if (typeof item === "string" || typeof item === "number") return { label: String(item), value: item };
    return item;
  })
);
const selectedIndex = computed(() => normalizedOptions.value.findIndex((item) => isSelected(item.value)));
const currentLabel = computed(() => normalizedOptions.value[selectedIndex.value]?.label || props.placeholder);

function isSelected(value: SelectValue) {
  return Object.is(value, props.modelValue) || String(value ?? "") === String(props.modelValue ?? "");
}
function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  activeIndex.value = Math.max(0, selectedIndex.value);
}
function close() {
  open.value = false;
}
function move(step: number) {
  if (!open.value) {
    toggle();
    return;
  }
  const count = normalizedOptions.value.length;
  if (!count) return;
  activeIndex.value = (activeIndex.value + step + count) % count;
}
function choose(index: number) {
  const item = normalizedOptions.value[index];
  if (!item) return;
  emit("update:modelValue", item.value);
  emit("change", item.value);
  close();
}
function onDocumentPointerDown(event: PointerEvent) {
  if (!rootRef.value?.contains(event.target as Node)) close();
}
function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") close();
}

watch(open, (value) => {
  if (value) activeIndex.value = Math.max(0, selectedIndex.value);
});
onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeydown);
});
</script>

<style scoped>
.app-select {
  position: relative;
  min-width: 128px;
  color: var(--color-text-body);
}
.app-select-trigger {
  width: 100%;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-body);
  padding: 0 10px 0 12px;
  text-align: left;
  transition: border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.app-select-trigger span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-select-trigger svg {
  transition: transform var(--duration-fast) var(--ease-out);
}
.app-select.open .app-select-trigger {
  border-color: var(--color-primary-600);
  box-shadow: var(--shadow-focus);
}
.app-select.open .app-select-trigger svg {
  transform: rotate(180deg);
}
.app-select-trigger:hover:not(:disabled) {
  border-color: var(--color-border-strong);
}
.app-select-trigger:active:not(:disabled) {
  transform: scale(0.98);
}
.app-select.disabled {
  opacity: .55;
  pointer-events: none;
}
.app-select-pop {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 6px);
  z-index: var(--z-popover);
  min-width: 100%;
  max-height: 260px;
  overflow: auto;
  display: grid;
  gap: 4px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-lg);
  padding: 6px;
  transform-origin: top center;
  animation: popover-in var(--duration-fast) var(--ease-out) both;
  will-change: opacity, transform;
}
.app-select-pop button {
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-body);
  padding: 0 8px;
  text-align: left;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}
.app-select-pop button:hover,
.app-select-pop button.focused {
  background: var(--color-bg-muted);
}
.app-select-pop button.active {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  font-weight: 600;
}
.app-select-pop button.danger {
  color: var(--color-danger-700);
}
</style>
