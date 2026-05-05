<template>
  <div class="table-wrap">
    <table class="table">
      <thead><tr><th v-for="header in headers" :key="header">{{ header }}</th></tr></thead>
      <tbody><slot /></tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
defineProps<{ headers: string[] }>();
</script>

<style scoped>
.table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  color: var(--color-text-body);
  font-size: var(--text-body-sm);
}

th,
td {
  border-bottom: 1px solid var(--color-border-subtle);
  padding: 12px 14px;
  text-align: left;
  vertical-align: middle;
}

th {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-weight: 700;
  white-space: nowrap;
}

:deep(tbody tr:nth-child(even)) {
  background: rgba(249,248,246,.72);
}

:deep(tbody tr:hover) {
  background: var(--color-primary-50);
}
</style>
