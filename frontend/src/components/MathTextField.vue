<template>
  <div class="math-field-wrap">
    <!-- 公式小编辑器：MathLive 纯数学模式（方向键进出上标/下标/根号），配 fx 符号盘 -->
    <transition name="fade-slide">
      <div v-if="editorOpen" class="formula-editor-pop" @mousedown.stop>
        <div class="formula-editor-head">
          <strong>{{ editingChip ? "编辑公式" : "插入公式" }}</strong>
          <button type="button" class="formula-editor-x" title="取消" @mousedown.prevent @click="cancelFormula"><X :size="15" /></button>
        </div>
        <math-field ref="mfEditor" class="formula-editor-mf"></math-field>
        <MathKeyboard @insert="insertIntoEditor" @close="cancelFormula" />
        <div class="formula-editor-actions">
          <button type="button" class="fe-btn ghost" @mousedown.prevent @click="cancelFormula">取消</button>
          <button type="button" class="fe-btn primary" @mousedown.prevent @click="commitFormula">{{ editingChip ? "更新" : "插入" }}</button>
        </div>
      </div>
    </transition>

    <button
      type="button"
      class="attach-btn math-btn"
      :class="{ active: editorOpen }"
      :disabled="disabled"
      :aria-pressed="editorOpen"
      title="插入数学公式"
      @mousedown.prevent
      @click="toggleEditor"
    ><FunctionIcon :size="18" /></button>

    <div
      ref="editable"
      class="math-editable"
      :class="{ empty: !modelValue }"
      :contenteditable="!disabled"
      :data-placeholder="placeholder"
      role="textbox"
      aria-multiline="true"
      @input="onInput"
      @keydown="onKeydown"
      @click="onEditableClick"
      @keyup="saveRange"
      @mouseup="saveRange"
      @compositionstart="onCompositionStart"
      @compositionend="onCompositionEnd"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, nextTick, ref, watch } from "vue";
import type { MathfieldElement } from "mathlive";
import katex from "katex";
import "katex/dist/katex.min.css";
import { X, FunctionIcon } from "../icons";
import MathKeyboard from "./MathKeyboard.vue";
import { configureMathfield, toMathfieldInsert, stripOuterMath } from "../utils/mathfield";
import { parsePlainSegments } from "../utils/mathInput";

// 引入即注册 <math-field> 自定义元素并完成字体/音效配置。
configureMathfield();

const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string; disabled?: boolean }>(), {
  placeholder: "",
  disabled: false,
});
const emit = defineEmits<{ (event: "update:modelValue", value: string): void; (event: "submit"): void }>();

const editable = ref<HTMLDivElement | null>(null);
const mfEditor = ref<MathfieldElement | null>(null);
const editorOpen = ref(false);
const editingChip = ref<HTMLElement | null>(null);
let savedRange: Range | null = null;
let lastPlain = props.modelValue; // 字段当前内容对应的散文串，区分改动来源、避免 v-model 回环
let composing = false;

function renderMathHtml(latex: string) {
  try {
    return katex.renderToString(latex, { throwOnError: false, output: "html" });
  } catch {
    return latex;
  }
}

// 内联公式块：contentEditable=false 使其成为不可拆分的原子（光标整体跳过、退格整体删除）。
function createChip(latex: string) {
  const span = document.createElement("span");
  span.className = "formula-chip";
  span.contentEditable = "false";
  span.dataset.latex = latex;
  span.title = latex;
  span.innerHTML = renderMathHtml(latex);
  return span;
}

// contenteditable DOM → 「散文 + $...$」串
function serializeNode(node: Node, notFirst: boolean): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
  if (node.nodeType !== Node.ELEMENT_NODE) return "";
  const el = node as HTMLElement;
  if (el.classList.contains("formula-chip")) return `$${el.dataset.latex || ""}$`;
  if (el.tagName === "BR") return "\n";
  let inner = "";
  el.childNodes.forEach((child, i) => { inner += serializeNode(child, i > 0); });
  const block = el.tagName === "DIV" || el.tagName === "P";
  return block && notFirst ? `\n${inner}` : inner; // 浏览器换行时可能生成 div/p，块级前补换行
}
function serialize(): string {
  const root = editable.value;
  if (!root) return "";
  let out = "";
  root.childNodes.forEach((node, i) => { out += serializeNode(node, i > 0); });
  return out;
}

// 「散文 + $...$」串 → contenteditable DOM（文字节点 + 公式块）
function setContent(plain: string) {
  const root = editable.value;
  if (!root) return;
  const frag = document.createDocumentFragment();
  for (const seg of parsePlainSegments(plain)) {
    if (seg.type === "math") {
      frag.appendChild(createChip(seg.value));
      continue;
    }
    seg.value.split("\n").forEach((part, i) => {
      if (i > 0) frag.appendChild(document.createElement("br"));
      if (part) frag.appendChild(document.createTextNode(part));
    });
  }
  root.innerHTML = "";
  root.appendChild(frag);
  // 内容整体重建后旧光标失去意义，浏览器会把残留 selection 钳到 (root, 0)——若编辑区
  // 仍持焦点，这个"开头光标"会让后续打字/插公式全落到最前面。显式把光标移到末尾。
  if (document.activeElement === root) {
    const range = document.createRange();
    range.selectNodeContents(root);
    range.collapse(false);
    const sel = window.getSelection();
    sel?.removeAllRanges();
    sel?.addRange(range);
    savedRange = range.cloneRange();
  } else {
    savedRange = null;
  }
}

function onInput() {
  const plain = serialize();
  lastPlain = plain;
  emit("update:modelValue", plain);
}
function onCompositionStart() {
  composing = true;
}
function onCompositionEnd() {
  composing = false;
  onInput();
}

// 记录 contenteditable 内当前光标位置，供 fx 插入公式块时定位。
// 仅在编辑区确实持有焦点时保存：内容重建后浏览器会把残留 selection 钳到 (root, 0)，
// 焦点不在编辑区时读到的就是这类陈旧位置，存下来会让公式插到最前面。
function saveRange() {
  const root = editable.value;
  if (!root || document.activeElement !== root) return;
  const sel = window.getSelection();
  if (sel && sel.rangeCount && root.contains(sel.anchorNode)) {
    savedRange = sel.getRangeAt(0).cloneRange();
  }
}

function insertChip(latex: string) {
  const root = editable.value;
  if (!root) return;
  const chip = createChip(latex);
  // 先克隆已保存的光标位置再聚焦：focus() 会让浏览器把 selection 挪到内容开头，
  // 若此后再读 savedRange（或经 focus 监听覆盖），公式会永远插到最前面。
  let range = savedRange && root.contains(savedRange.startContainer) ? savedRange.cloneRange() : null;
  root.focus();
  if (!range) {
    range = document.createRange();
    range.selectNodeContents(root);
    range.collapse(false);
  }
  range.deleteContents();
  range.insertNode(chip);
  const after = document.createRange();
  after.setStartAfter(chip);
  after.collapse(true);
  const sel = window.getSelection();
  sel?.removeAllRanges();
  sel?.addRange(after);
  savedRange = after.cloneRange();
  onInput();
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  if (composing || event.isComposing) return; // 中文输入法确认回车
  if (event.shiftKey) {
    event.preventDefault();
    document.execCommand("insertLineBreak");
    onInput();
    return;
  }
  event.preventDefault();
  emit("submit");
}

// —— 公式小编辑器 ——
function openEditorForNew() {
  saveRange();
  editingChip.value = null;
  editorOpen.value = true;
}
function openEditorForChip(chip: HTMLElement) {
  editingChip.value = chip;
  editorOpen.value = true;
}
function toggleEditor() {
  if (editorOpen.value) cancelFormula();
  else openEditorForNew();
}
function cancelFormula() {
  editorOpen.value = false;
  editingChip.value = null;
  editable.value?.focus();
}
function insertIntoEditor(template: string) {
  const mf = mfEditor.value;
  if (!mf) return;
  mf.focus();
  mf.insert(toMathfieldInsert(template, !mf.selectionIsCollapsed), { mode: "math", format: "latex", selectionMode: "placeholder" });
}
function commitFormula() {
  const mf = mfEditor.value;
  if (!mf) return;
  const latex = stripOuterMath(mf.getValue("latex"));
  if (!latex) { cancelFormula(); return; } // 空公式 → 视为取消
  if (editingChip.value) {
    editingChip.value.dataset.latex = latex;
    editingChip.value.title = latex;
    editingChip.value.innerHTML = renderMathHtml(latex);
    onInput();
    cancelFormula();
  } else {
    insertChip(latex);
    editorOpen.value = false;
    editingChip.value = null;
  }
}

function onEditableClick(event: MouseEvent) {
  const chip = (event.target as HTMLElement)?.closest?.(".formula-chip") as HTMLElement | null;
  if (chip && editable.value?.contains(chip)) {
    event.preventDefault();
    openEditorForChip(chip);
  }
}

// 编辑器打开时初始化 MathLive（纯数学模式）
watch(editorOpen, async (open) => {
  if (!open) return;
  await nextTick();
  const mf = mfEditor.value;
  if (!mf) return;
  mf.smartMode = true;
  mf.mathVirtualKeyboardPolicy = "manual";
  mf.setValue(editingChip.value?.dataset.latex || "", { silenceNotifications: true });
  mf.focus();
});

// 外部写入 v-model（清空 / 快捷提问 / 解释选中）→ 重建 DOM；与自身改动区分避免回环、避免打断输入光标
watch(() => props.modelValue, (value) => {
  if (value === lastPlain) return;
  lastPlain = value;
  setContent(value);
});

onBeforeUnmount(() => { savedRange = null; });

// 初始内容
nextTick(() => setContent(props.modelValue));

function focus() {
  editable.value?.focus();
}
defineExpose({ focus });
</script>

<style>
.math-field-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.math-editable {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  max-height: 120px;
  align-self: center;
  overflow-y: auto;
  outline: none;
  padding: 8px 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--qa-text, var(--color-text-default));
  white-space: pre-wrap;
  word-break: break-word;
}

.math-editable.empty::before {
  content: attr(data-placeholder);
  color: var(--qa-hint, var(--color-text-muted));
  pointer-events: none;
}

.formula-chip {
  display: inline-block;
  vertical-align: -0.25em;
  margin: 0 2px;
  padding: 1px 6px;
  border: 1px solid var(--qa-primary-100, var(--color-primary-100));
  border-radius: 8px;
  background: var(--qa-primary-50, var(--color-primary-50));
  cursor: pointer;
  user-select: none;
  transition: border-color .12s, background .12s;
}

.formula-chip:hover {
  border-color: var(--qa-primary-400, var(--color-primary-400));
  background: var(--qa-primary-100, var(--color-primary-100));
}

.formula-chip .katex {
  font-size: 1.02em;
  pointer-events: none;
}

/* 公式小编辑器浮层 */
.formula-editor-pop {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 12px);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--qa-border, var(--color-border-default, #e6e4dd));
  border-radius: 18px;
  background: var(--qa-surface, #fff);
  box-shadow: var(--qa-shadow-float, 0 18px 40px rgba(15, 23, 42, .16));
  padding: 12px;
}

.formula-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--qa-text, var(--color-text-default));
  font-size: 14px;
}

.formula-editor-x {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: var(--qa-muted-bg, var(--color-bg-muted, #f1f5f4));
  color: var(--qa-hint, var(--color-text-muted));
  cursor: pointer;
}

.formula-editor-x:hover {
  background: var(--qa-primary-50, var(--color-primary-50));
  color: var(--qa-primary-600, var(--color-primary-600));
}

math-field.formula-editor-mf {
  display: block;
  min-height: 46px;
  border: 1px solid var(--qa-border, var(--color-border-default, #e6e4dd));
  border-radius: 12px;
  background: var(--qa-muted-bg, var(--color-bg-muted, #f8fafc));
  padding: 8px 12px;
  font-size: 20px;
  --caret-color: var(--qa-primary-600, var(--color-primary-600));
  --selection-background-color: var(--qa-primary-100, var(--color-primary-100));
}

math-field.formula-editor-mf::part(menu-toggle),
math-field.formula-editor-mf::part(virtual-keyboard-toggle) {
  display: none;
}

.formula-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.fe-btn {
  border-radius: 10px;
  padding: 7px 18px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
}

.fe-btn.ghost {
  border-color: var(--qa-border, var(--color-border-default));
  background: transparent;
  color: var(--qa-secondary, var(--color-text-secondary));
}

.fe-btn.primary {
  background: var(--qa-primary-600, var(--color-primary-600));
  color: #fff;
}

.fe-btn.primary:hover {
  filter: brightness(1.05);
}
</style>
