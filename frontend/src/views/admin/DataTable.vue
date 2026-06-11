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
  border-radius: var(--radius-xl);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
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
  padding: 14px 16px;
  text-align: left;
  vertical-align: middle;
}

th {
  height: 48px;
  padding-top: 0;
  padding-bottom: 0;
  background: var(--admin-paper-faint, #FAF9F6);
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
  font-weight: 600;
  letter-spacing: .06em;
  white-space: nowrap;
}

thead tr {
  border-bottom: 1px solid var(--color-border-default);
}

:deep(tbody tr) {
  transition: background var(--duration-fast) var(--ease-out);
}

:deep(tbody tr:nth-child(even)) {
  background: var(--admin-paper-faint, #FAF9F6);
}

:deep(tbody tr:hover) {
  background: var(--ca-role-admin-light, #FFF8E1);
}
</style>
