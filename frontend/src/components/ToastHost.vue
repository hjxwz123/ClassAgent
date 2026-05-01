<template>
  <div class="toasts" role="alert" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="item in items"
        :key="item.id"
        class="toast"
        :class="[item.type, { paused: pausedIds.has(item.id) }]"
        @mouseenter="pause(item.id)"
        @mouseleave="resume(item.id)"
      >
        <component :is="iconMap[item.type]" :size="20" />
        <span>{{ item.text }}</span>
        <button class="btn btn-ghost btn-xs" aria-label="关闭" @click="close(item.id)"><X :size="12" /></button>
        <i class="toast-progress" :style="{ animationDuration: `${durationMs}ms` }"></i>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, watch } from "vue";
import { AlertTriangle, CheckCircle, Info, X, XCircle } from "lucide-vue-next";

const props = defineProps<{ items: Array<{ id: number; type: "success" | "warning" | "error" | "info"; text: string }> }>();
const emit = defineEmits<{ close: [id: number] }>();

const iconMap = { success: CheckCircle, warning: AlertTriangle, error: XCircle, info: Info };
const durationMs = 4000;
const timers = new Map<number, { timer: number; startedAt: number; remaining: number }>();
const pausedIds = reactive(new Set<number>());

function close(id: number) {
  const record = timers.get(id);
  if (record) window.clearTimeout(record.timer);
  timers.delete(id);
  pausedIds.delete(id);
  emit("close", id);
}
function schedule(id: number, remaining = durationMs) {
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
  schedule(id, record.remaining || durationMs);
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
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-bg-surface);
  border-left: 3px solid var(--color-info-500);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--space-3);
  color: var(--color-text-body);
}
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
  from { opacity: 0; transform: translateX(100%); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes toast-out {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-10px); }
}
@keyframes toast-progress {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}
@media (max-width: 640px) {
  .toasts { left: var(--space-4); right: var(--space-4); width: auto; }
}
</style>
