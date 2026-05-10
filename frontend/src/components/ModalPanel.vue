<template>
  <teleport to="body">
    <Transition name="modal-pop">
      <div v-if="open" class="overlay modal-mask" @click.self="emit('close')">
      <section ref="dialogRef" class="modal" role="dialog" aria-modal="true" tabindex="-1" @keydown="trapFocus">
        <header>
          <h2>{{ title }}</h2>
          <button class="btn btn-ghost icon-btn" aria-label="关闭" @click="emit('close')"><X :size="18" /></button>
        </header>
        <main><slot /></main>
        <footer v-if="$slots.footer"><slot name="footer" /></footer>
      </section>
      </div>
    </Transition>
  </teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { X } from "../icons";

const props = defineProps<{ open: boolean; title: string }>();
const emit = defineEmits<{ close: [] }>();
const dialogRef = ref<HTMLElement | null>(null);
let previousOverflow = "";

function focusableItems() {
  return Array.from(dialogRef.value?.querySelectorAll<HTMLElement>('a[href], button:not(:disabled), textarea:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])') || []);
}
function trapFocus(event: KeyboardEvent) {
  if (event.key === "Escape") {
    emit("close");
    return;
  }
  if (event.key !== "Tab") return;
  const items = focusableItems();
  if (!items.length) {
    event.preventDefault();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && props.open) emit("close");
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onDocumentKeydown);
      await nextTick();
      (focusableItems()[0] || dialogRef.value)?.focus();
    } else {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onDocumentKeydown);
    }
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow;
  document.removeEventListener("keydown", onDocumentKeydown);
});
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
header .icon-btn {
  min-width: 44px;
  min-height: 44px;
}
</style>
