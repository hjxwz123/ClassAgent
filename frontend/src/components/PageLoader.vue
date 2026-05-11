<template>
  <div class="page-loader" role="status" aria-label="页面加载中">
    <LoadingMark class="page-loader-mark" />
  </div>
</template>

<script setup lang="ts">
import LoadingMark from "./LoadingMark.vue";
</script>

<style scoped>
.page-loader {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal, 1310);
  display: grid;
  place-items: center;
  pointer-events: none;
}

.page-loader-mark {
  width: min(200px, 48vw);
  height: min(200px, 48vw);
  display: block;
}
</style>
