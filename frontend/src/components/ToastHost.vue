<template>
  <div class="toasts" role="alert" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="item in items"
        :key="item.id"
        class="toast"
        :class="[item.type, { paused: pausedIds.has(item.id), clickable: !!item.action }]"
        @mouseenter="pause(item.id)"
        @mouseleave="resume(item.id)"
        @click="item.action ? activate(item) : undefined"
      >
        <component :is="iconMap[item.type]" :size="20" />
        <span>{{ item.text }}</span>
        <button v-if="item.action" type="button" class="toast-action" @click.stop="activate(item)">{{ item.action.label }}</button>
        <button class="btn btn-ghost btn-xs" aria-label="关闭" @click.stop="close(item.id)"><X :size="12" /></button>
        <i class="toast-progress" :style="{ animationDuration: `${durationFor(item)}ms` }"></i>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, watch } from "vue";
import { AlertTriangle, CheckCircle, Info, X, XCircle } from "../icons";

type ToastItem = { id: number; type: "success" | "warning" | "error" | "info"; text: string; action?: { label: string; onClick: () => void } };
const props = defineProps<{ items: ToastItem[] }>();
const emit = defineEmits<{ close: [id: number] }>();

const iconMap = { success: CheckCircle, warning: AlertTriangle, error: XCircle, info: Info };
const BASE_DURATION = 4000;
const ACTION_DURATION = 8000; // 可点击 Toast 停留更久，给用户时间点击跳转
function durationFor(item: ToastItem) { return item.action ? ACTION_DURATION : BASE_DURATION; }
function durationById(id: number) { const item = props.items.find((entry) => entry.id === id); return item ? durationFor(item) : BASE_DURATION; }
const timers = new Map<number, { timer: number; startedAt: number; remaining: number }>();
const pausedIds = reactive(new Set<number>());

function close(id: number) {
  const record = timers.get(id);
  if (record) window.clearTimeout(record.timer);
  timers.delete(id);
  pausedIds.delete(id);
  emit("close", id);
}
// 点击可交互 Toast：执行动作后立即关闭，避免重复触发
function activate(item: ToastItem) {
  try { item.action?.onClick(); } finally { close(item.id); }
}
function schedule(id: number, remaining = durationById(id)) {
  const record = timers.get(id);
  if (record) window.clearTimeout(record.timer);
  timers.set(id, {
    remaining,
    startedAt: Date.now(),
    timer: window.setTimeout(() => close(id), remaining)
  });
}
function pause(id: number) {
  const record = timers.get(id);
  if (!record) return;
  window.clearTimeout(record.timer);
  record.remaining = Math.max(0, record.remaining - (Date.now() - record.startedAt));
  pausedIds.add(id);
}
function resume(id: number) {
  const record = timers.get(id);
  if (!record) return;
  pausedIds.delete(id);
  schedule(id, record.remaining || durationById(id));
}

watch(
  () => props.items.map((item) => item.id),
  (ids) => {
    const current = new Set(ids);
    ids.forEach((id) => {
      if (!timers.has(id)) schedule(id);
    });
    [...timers.keys()].forEach((id) => {
      if (!current.has(id)) {
        const record = timers.get(id);
        if (record) window.clearTimeout(record.timer);
        timers.delete(id);
        pausedIds.delete(id);
      }
    });
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  timers.forEach((record) => window.clearTimeout(record.timer));
  timers.clear();
});
</script>

<style scoped>
.toasts {
  position: fixed;
  top: var(--space-6);
  right: var(--space-6);
  z-index: var(--z-toast);
  display: grid;
  gap: var(--space-3);
  width: 360px;
}
.toast {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-left: 3px solid var(--color-info-500);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 28px rgba(18, 22, 20, .1), 0 2px 6px rgba(18, 22, 20, .05);
  padding: var(--space-3);
  color: var(--color-text-body);
}
.toast > span { flex: 1 1 auto; min-width: 0; }
.toast > svg:first-child { flex: 0 0 auto; }
.toast.clickable { cursor: pointer; }
.toast.clickable:hover { border-color: var(--color-border-strong, var(--color-border-default)); box-shadow: 0 12px 32px rgba(18, 22, 20, .16), 0 3px 8px rgba(18, 22, 20, .08); }
.toast-action {
  flex: 0 0 auto;
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
  background: transparent;
  color: var(--color-success-600, var(--color-success-500));
  cursor: pointer;
  white-space: nowrap;
}
.toast-action:hover { background: color-mix(in srgb, var(--color-success-500) 12%, transparent); }
.toast > svg:first-child { color: var(--color-info-500); }
.toast.success > svg:first-child { color: var(--color-success-500); }
.toast.warning > svg:first-child { color: var(--color-warning-500); }
.toast.error > svg:first-child { color: var(--color-danger-500); }
.toast-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: currentColor;
  opacity: 0.35;
  transform-origin: left center;
  animation: toast-progress var(--duration-slow) linear forwards;
}
.toast.paused .toast-progress { animation-play-state: paused; }
.success { border-left-color: var(--color-success-500); }
.warning { border-left-color: var(--color-warning-500); }
.error { border-left-color: var(--color-danger-500); }
.info { border-left-color: var(--color-info-500); }
.toast-enter-active { animation: toast-in var(--duration-base) var(--ease-out) both; }
.toast-leave-active { animation: toast-out var(--duration-fast) var(--ease-in) both; }
.toast-move { transition: transform var(--duration-base) var(--ease-out); }
@keyframes toast-in {
  from { opacity: 0; transform: translateX(calc(100% + 24px)); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to { opacity: 0; transform: translateY(-8px) scale(0.98); }
}
@keyframes toast-progress {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}
@media (max-width: 640px) {
  .toasts { left: var(--space-4); right: var(--space-4); width: auto; }
}
</style>
