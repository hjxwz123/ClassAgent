<template>
  <div class="password-field" :class="{ invalid }">
    <input
      v-bind="attrs"
      :value="modelValue"
      :type="visible ? 'text' : 'password'"
      @input="onInput"
    />
    <button
      v-if="modelValue"
      type="button"
      class="password-tool"
      aria-label="清空密码"
      @click="emit('update:modelValue', '')"
    >
      <X :size="14" />
    </button>
    <button
      type="button"
      class="password-tool"
      :aria-label="visible ? '隐藏密码' : '显示密码'"
      @click="visible = !visible"
    >
      <EyeOff v-if="visible" :size="15" />
      <Eye v-else :size="15" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useAttrs } from "vue";
import { Eye, EyeOff, X } from "lucide-vue-next";

defineOptions({ inheritAttrs: false });

defineProps<{ modelValue: string }>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const attrs = useAttrs();
const visible = ref(false);
const invalid = computed(() => String(attrs["aria-invalid"]) === "true");

function onInput(event: Event) {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.password-field {
  width: 100%;
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  padding: 0 6px 0 12px;
  transition: border-color var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out);
}
.password-field:hover {
  border-color: var(--color-border-strong);
}
.password-field:focus-within {
  border-color: var(--color-primary-600);
  box-shadow: var(--shadow-focus);
}
.password-field.invalid {
  border-color: var(--color-danger-500);
  box-shadow: var(--shadow-focus-danger);
}
.password-field input {
  min-width: 0;
  flex: 1;
  height: 42px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text-body);
}
.password-field input::placeholder {
  color: var(--color-text-muted);
}
.password-tool {
  width: 44px;
  height: 44px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 44px;
  border-radius: 7px;
  color: var(--color-text-muted);
}
.password-tool:hover {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}
.password-tool:active {
  transform: scale(0.94);
}
</style>
