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
