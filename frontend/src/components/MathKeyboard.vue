<template>
  <div class="math-kb" role="dialog" aria-label="数学公式键盘">
    <div class="math-kb-head">
      <div class="math-kb-tabs" role="tablist">
        <button
          v-for="group in groups"
          :key="group.key"
          type="button"
          role="tab"
          class="math-kb-tab"
          :class="{ active: group.key === activeKey }"
          :aria-selected="group.key === activeKey"
          @mousedown.prevent
          @click="activeKey = group.key"
        >{{ group.name }}</button>
      </div>
      <button type="button" class="math-kb-close" title="关闭公式键盘" aria-label="关闭公式键盘" @mousedown.prevent @click="emit('close')">
        <X :size="15" />
      </button>
    </div>
    <div class="math-kb-keys" role="tabpanel">
      <button
        v-for="(key, index) in activeKeys"
        :key="`${activeKey}-${index}`"
        type="button"
        class="math-kb-key"
        :class="{ wide: key.wide }"
        :title="key.title"
        :aria-label="key.title"
        @mousedown.prevent
        @click="emit('insert', key.insert)"
        v-html="renderKey(key)"
      ></button>
    </div>
    <p class="math-kb-hint">点击符号插入到问题中，发送后将以公式排版显示</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import katex from "katex";
import "katex/dist/katex.min.css";
import { X } from "../icons";
import { MATH_GROUPS, type MathKey } from "../utils/mathInput";

const groups = MATH_GROUPS;
const activeKey = ref(groups[0]?.key ?? "");
const activeKeys = computed(() => groups.find((group) => group.key === activeKey.value)?.keys ?? []);

const emit = defineEmits<{ (event: "insert", template: string): void; (event: "close"): void }>();

function escapeHtml(value: string) {
  return value.replace(/[&<>"]/g, (char) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[char] || char
  ));
}

// 按键 label 用 KaTeX 渲染成真实数学符号（所见即所得的键盘）；渲染失败时退回纯文本。
function renderKey(key: MathKey) {
  try {
    return katex.renderToString(key.label, { throwOnError: true, displayMode: false, output: "html" });
  } catch {
    return escapeHtml(key.text || key.label);
  }
}
</script>

<style>
.math-kb {
  width: 100%;
  max-width: var(--qa-content-width, 760px);
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--qa-border, var(--color-border-default, #e6e4dd));
  border-radius: 18px;
  background: var(--qa-surface, #fff);
  box-shadow: var(--qa-shadow-float, 0 18px 40px rgba(15, 23, 42, .16));
  padding: 10px 12px 8px;
  pointer-events: auto;
}

.math-kb-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.math-kb-tabs {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.math-kb-tab {
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--qa-secondary, var(--color-text-secondary, #64748b));
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background .15s, color .15s, border-color .15s;
}

.math-kb-tab:hover {
  background: var(--qa-primary-50, var(--color-primary-50, #eef7f8));
  color: var(--qa-primary-600, var(--color-primary-600, #0097a7));
}

.math-kb-tab.active {
  background: var(--qa-primary-50, var(--color-primary-50, #eef7f8));
  border-color: var(--qa-primary-100, var(--color-primary-100, #cfeef2));
  color: var(--qa-primary-600, var(--color-primary-600, #0097a7));
}

.math-kb-close {
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 9px;
  background: var(--qa-muted-bg, var(--color-bg-muted, #f1f5f4));
  color: var(--qa-hint, var(--color-text-muted, #94a3b8));
  cursor: pointer;
}

.math-kb-close:hover {
  background: var(--qa-primary-50, var(--color-primary-50, #eef7f8));
  color: var(--qa-primary-600, var(--color-primary-600, #0097a7));
}

.math-kb-keys {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(52px, 1fr));
  gap: 6px;
  max-height: 208px;
  overflow-y: auto;
  padding: 2px;
}

.math-kb-key {
  min-height: 44px;
  display: grid;
  place-items: center;
  border: 1px solid var(--qa-border, var(--color-border-default, #e6e4dd));
  border-radius: 12px;
  background: var(--qa-surface, #fff);
  color: var(--qa-text, var(--color-text-default, #1f2937));
  padding: 4px 6px;
  cursor: pointer;
  overflow: hidden;
  transition: background .12s, border-color .12s, transform .08s;
}

.math-kb-key.wide {
  grid-column: span 2;
}

.math-kb-key:hover {
  border-color: var(--qa-primary-400, var(--color-primary-400, #3fbccb));
  background: var(--qa-primary-50, var(--color-primary-50, #eef7f8));
}

.math-kb-key:active {
  transform: translateY(1px);
}

.math-kb-key .katex {
  font-size: 1.02em;
  color: inherit;
  white-space: nowrap;
  pointer-events: none;
}

.math-kb-hint {
  margin: 0;
  padding: 0 2px;
  color: var(--qa-hint, var(--color-text-muted, #94a3b8));
  font-size: 11px;
  text-align: center;
}

@media (max-width: 560px) {
  .math-kb-keys {
    grid-template-columns: repeat(auto-fill, minmax(46px, 1fr));
    max-height: 176px;
  }
}
</style>
