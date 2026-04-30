<template>
  <div class="toasts" role="alert" aria-live="polite">
    <div v-for="item in items" :key="item.id" class="toast" :class="item.type">
      <component :is="iconMap[item.type]" :size="20" />
      <span>{{ item.text }}</span>
      <button class="btn btn-ghost btn-xs" aria-label="关闭" @click="$emit('close', item.id)"><X :size="12" /></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle, CheckCircle, Info, X, XCircle } from "lucide-vue-next";

defineProps<{ items: Array<{ id: number; type: "success" | "warning" | "error" | "info"; text: string }> }>();
defineEmits<{ close: [id: number] }>();

const iconMap = { success: CheckCircle, warning: AlertTriangle, error: XCircle, info: Info };
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
.success { border-left-color: var(--color-success-500); }
.warning { border-left-color: var(--color-warning-500); }
.error { border-left-color: var(--color-danger-500); }
.info { border-left-color: var(--color-info-500); }
@media (max-width: 640px) {
  .toasts { left: var(--space-4); right: var(--space-4); width: auto; }
}
</style>
