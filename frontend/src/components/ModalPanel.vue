<template>
  <teleport to="body">
    <div v-if="open" class="overlay" @click.self="$emit('close')">
      <section class="modal" role="dialog" aria-modal="true">
        <header>
          <h2>{{ title }}</h2>
          <button class="btn btn-ghost icon-btn" aria-label="关闭" @click="$emit('close')"><X :size="18" /></button>
        </header>
        <main><slot /></main>
        <footer v-if="$slots.footer"><slot name="footer" /></footer>
      </section>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { X } from "lucide-vue-next";

defineProps<{ open: boolean; title: string }>();
defineEmits<{ close: [] }>();
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-bg);
  display: grid;
  place-items: center;
  background: var(--color-bg-overlay);
  backdrop-filter: blur(4px);
  padding: var(--space-6);
}
.modal {
  width: min(800px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: var(--color-bg-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border-default);
  padding: var(--space-5) var(--space-6);
}
h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h2); line-height: 28px; }
main { padding: var(--space-6); }
footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  border-top: 1px solid var(--color-border-default);
  padding: var(--space-4) var(--space-6);
}
</style>
