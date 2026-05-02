<template>
  <div
    ref="trackRef"
    class="app-slider"
    :class="{ disabled }"
    role="slider"
    tabindex="0"
    :aria-valuemin="min"
    :aria-valuemax="max"
    :aria-valuenow="modelValue"
    @pointerdown="startDrag"
    @keydown.left.prevent="nudge(-1)"
    @keydown.down.prevent="nudge(-1)"
    @keydown.right.prevent="nudge(1)"
    @keydown.up.prevent="nudge(1)"
  >
    <span class="slider-track"></span>
    <span class="slider-fill" :style="{ width: `${percent}%` }"></span>
    <span class="slider-thumb" :style="{ left: `${percent}%` }"></span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

const props = withDefaults(defineProps<{
  modelValue: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}>(), {
  min: 0,
  max: 100,
  step: 1,
  disabled: false
});

const emit = defineEmits<{
  "update:modelValue": [value: number];
  input: [value: number];
  change: [value: number];
}>();

const trackRef = ref<HTMLElement | null>(null);
const percent = computed(() => {
  const span = props.max - props.min || 1;
  return Math.min(100, Math.max(0, ((Number(props.modelValue) - props.min) / span) * 100));
});

function normalize(value: number) {
  const clamped = Math.min(props.max, Math.max(props.min, value));
  const stepped = Math.round((clamped - props.min) / props.step) * props.step + props.min;
  const decimals = String(props.step).split(".")[1]?.length || 0;
  return Number(stepped.toFixed(decimals));
}
function valueFromClientX(clientX: number) {
  const rect = trackRef.value?.getBoundingClientRect();
  if (!rect) return props.modelValue;
  const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
  return normalize(props.min + ratio * (props.max - props.min));
}
function setValue(value: number, final = false) {
  const next = normalize(value);
  emit("update:modelValue", next);
  emit("input", next);
  if (final) emit("change", next);
}
function startDrag(event: PointerEvent) {
  if (props.disabled) return;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  setValue(valueFromClientX(event.clientX));
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", stopDrag, { once: true });
}
function onMove(event: PointerEvent) {
  setValue(valueFromClientX(event.clientX));
}
function stopDrag(event: PointerEvent) {
  window.removeEventListener("pointermove", onMove);
  setValue(valueFromClientX(event.clientX), true);
}
function nudge(direction: number) {
  if (props.disabled) return;
  setValue(Number(props.modelValue || 0) + props.step * direction, true);
}
onBeforeUnmount(() => window.removeEventListener("pointermove", onMove));
</script>

<style scoped>
.app-slider {
  position: relative;
  height: 28px;
  display: flex;
  align-items: center;
  touch-action: none;
  cursor: pointer;
}
.slider-track,
.slider-fill {
  position: absolute;
  left: 0;
  right: 0;
  height: 6px;
  border-radius: var(--radius-full);
}
.slider-track {
  background: var(--color-border-default);
}
.slider-fill {
  right: auto;
  background: var(--color-primary-600);
  transition: width var(--duration-fast) var(--ease-out);
}
.slider-thumb {
  position: absolute;
  top: 50%;
  width: 18px;
  height: 18px;
  border: 3px solid var(--color-primary-600);
  border-radius: 50%;
  background: white;
  box-shadow: var(--shadow-sm);
  transform: translate(-50%, -50%);
  transition: left var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
}
.app-slider:hover .slider-thumb,
.app-slider:focus-visible .slider-thumb {
  transform: translate(-50%, -50%) scale(1.08);
  box-shadow: var(--shadow-md);
}
.app-slider.disabled {
  opacity: .55;
  cursor: not-allowed;
}
</style>
