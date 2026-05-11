<template>
  <article class="stat-card">
    <div class="stat-top">
      <span class="stat-icon"><component :is="icon" :size="20" /></span>
      <span>{{ label }}</span>
    </div>
    <strong>{{ value }}</strong>
    <small :class="trendClass">{{ trend }}</small>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  icon: unknown;
  label: string;
  value: string | number;
  trend?: string;
  danger?: boolean;
}>();

const trendClass = computed(() => (props.danger ? "danger" : "success"));
</script>

<style scoped>
.stat-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out);
}
.stat-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
.stat-top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
.stat-icon {
  display: inline-flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-primary-600);
  box-shadow: none;
}
strong {
  display: block;
  margin-top: var(--space-4);
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--text-display);
  line-height: 40px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
small {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--text-caption);
}
.success { color: var(--color-success-700); }
.danger { color: var(--color-danger-700); }
</style>
