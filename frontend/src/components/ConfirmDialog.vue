<template>
  <teleport to="body">
    <Transition name="modal-pop">
      <div v-if="open" class="modal-mask confirm-mask" @click.self="cancel">
        <article class="confirm-card" role="dialog" aria-modal="true">
          <header>
            <span class="confirm-icon" :class="tone"><AlertTriangle v-if="tone === 'danger'" :size="20" /><Info v-else :size="20" /></span>
            <div>
              <h2>{{ title }}</h2>
              <p>{{ message }}</p>
            </div>
          </header>
          <footer>
            <button class="btn btn-ghost" @click="cancel">{{ cancelText }}</button>
            <button class="btn" :class="tone === 'danger' ? 'btn-danger' : 'btn-primary'" @click="confirmAction">{{ confirmText }}</button>
          </footer>
        </article>
      </div>
    </Transition>
  </teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { AlertTriangle, Info } from "lucide-vue-next";

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "primary" | "danger";
}>(), {
  confirmText: "确认",
  cancelText: "取消",
  tone: "primary"
});

const emit = defineEmits<{ confirm: []; cancel: [] }>();
function confirmAction() {
  emit("confirm");
}
function cancel() {
  emit("cancel");
}
function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && props.open) cancel();
}
onMounted(() => document.addEventListener("keydown", onDocumentKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onDocumentKeydown));
</script>

<style scoped>
.confirm-mask {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-bg);
  display: grid;
  place-items: center;
  background: var(--color-bg-overlay);
  backdrop-filter: blur(4px);
  padding: 24px;
}
.confirm-card {
  width: min(420px, 100%);
  display: grid;
  gap: 18px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xl);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-xl);
  padding: 20px;
}
.confirm-card header {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
}
.confirm-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}
.confirm-icon.danger {
  background: var(--color-danger-50);
  color: var(--color-danger-700);
}
.confirm-card h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-h3);
}
.confirm-card p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
.confirm-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.confirm-card footer button:focus-visible {
  outline: 2px solid var(--color-primary-600);
  outline-offset: 2px;
}
</style>
