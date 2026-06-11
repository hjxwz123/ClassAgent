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
  position: relative;
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.stat-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--ca-role-primary, var(--color-primary-600));
  opacity: 0;
  transition: opacity var(--duration-base) var(--ease-out);
}
.stat-card:hover { transform: translateY(-4px); border-color: var(--color-border-strong); box-shadow: var(--shadow-md); }
.stat-card:hover::before { opacity: 1; }
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
  border-radius: 10px;
  background: var(--ca-role-light, var(--color-primary-50));
  color: var(--ca-role-primary, var(--color-primary-600));
  box-shadow: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
strong {
  display: block;
  margin-top: var(--space-4);
  overflow: hidden;
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-display);
  line-height: 40px;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
small {
  display: block;
  margin-top: var(--space-2);
  font-size: var(--text-caption);
  font-variant-numeric: tabular-nums;
}
.success { color: var(--color-success-700); }
.danger { color: var(--color-danger-700); }
</style>
