<template>
  <!-- default-mode/虚拟键盘策略用属性写在模板里：元素升级(connectedCallback)时即读到，
       比 onMounted 里设属性更早，能保证空字段一开始就处于文本模式（中文提问照常输入）。 -->
  <math-field
    ref="host"
    class="math-textfield"
    default-mode="text"
    math-virtual-keyboard-policy="manual"
  ></math-field>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { MathfieldElement } from "mathlive";
import { configureMathfield, mathfieldLatexToPlain, plainToMathfieldLatex, toMathfieldInsert } from "../utils/mathfield";

// 引入即注册 <math-field> 自定义元素并完成字体/音效配置。
configureMathfield();

const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string; disabled?: boolean }>(), {
  placeholder: "",
  disabled: false,
});
const emit = defineEmits<{ (event: "update:modelValue", value: string): void; (event: "submit"): void }>();

const host = ref<MathfieldElement | null>(null);
// lastPlain 记录「字段当前内容对应的散文串」，用于区分改动来自字段本身还是外部 v-model 写入，避免回环。
let lastPlain = props.modelValue;
let composing = false;
let composedAt = 0;

function syncFromField() {
  const node = host.value;
  if (!node) return;
  const plain = mathfieldLatexToPlain(node.getValue("latex"));
  if (plain === lastPlain) return;
  lastPlain = plain;
  emit("update:modelValue", plain);
}

function applyModel(plain: string) {
  const node = host.value;
  if (!node) return;
  // mode:'text' 让 setValue 按文本解析（纯中文保持文本、$...$ 才切数学）；
  // silenceNotifications：程序化写入不再触发 input 事件，避免 setValue→input→emit 回环。
  node.setValue(plainToMathfieldLatex(plain), { silenceNotifications: true, mode: "text" });
  lastPlain = plain;
}

// 回车提交：MathLive 不把按键冒泡到宿主，但会在 Enter(insertLineBreak) 时派发 change 事件；
// blur 只有在内容变化时才派发 change。用「派发时字段是否仍聚焦」区分 Enter(聚焦中) 与 blur(已失焦)，
// 再用合成态去抖排除中文输入法确认回车。发送后父级会清空输入，故 Enter 的 no-op 换行无副作用。
function onChange() {
  const node = host.value;
  if (!node || document.activeElement !== node) return; // 失焦提交：忽略
  if (composing || Date.now() - composedAt < 150) return; // 输入法确认回车：忽略
  emit("submit");
}
function onCompositionStart() {
  composing = true;
}
function onCompositionEnd() {
  composing = false;
  composedAt = Date.now();
}
// 空字段获得焦点时确保处于文本模式：中文/文字提问从一开始就是文本，而非落进数学模式。
function onFocusIn() {
  const node = host.value;
  if (node && !node.getValue("latex").trim()) node.executeCommand(["switchMode", "text"]);
}

onMounted(() => {
  const node = host.value;
  if (!node) return;
  node.smartMode = true; // 智能识别：打中文=文本，打 x^2 / a/b 等自动转数学
  node.defaultMode = "text"; // 默认文本模式，中文提问照常输入
  node.mathVirtualKeyboardPolicy = "manual"; // 不弹 MathLive 自带虚拟键盘（我们有 fx 公式键盘）
  node.placeholder = props.placeholder;
  node.disabled = props.disabled;
  applyModel(props.modelValue);
  node.addEventListener("input", syncFromField);
  node.addEventListener("change", onChange);
  node.addEventListener("focusin", onFocusIn);
  node.addEventListener("compositionstart", onCompositionStart, true);
  node.addEventListener("compositionend", onCompositionEnd, true);
});

onBeforeUnmount(() => {
  const node = host.value;
  if (!node) return;
  node.removeEventListener("input", syncFromField);
  node.removeEventListener("change", onChange);
  node.removeEventListener("focusin", onFocusIn);
  node.removeEventListener("compositionstart", onCompositionStart, true);
  node.removeEventListener("compositionend", onCompositionEnd, true);
});

watch(() => props.modelValue, (value) => { if (value !== lastPlain) applyModel(value); });
watch(() => props.placeholder, (value) => { if (host.value) host.value.placeholder = value; });
watch(() => props.disabled, (value) => { if (host.value) host.value.disabled = value; });

function focus() {
  host.value?.focus();
}
// 供父级 fx 公式键盘调用：把模板作为数学原子插入，光标落在第一个占位符，可继续用方向键进出结构。
function insertTemplate(template: string) {
  const node = host.value;
  if (!node) return;
  node.focus();
  node.insert(toMathfieldInsert(template, !node.selectionIsCollapsed), {
    mode: "math",
    format: "latex",
    selectionMode: "placeholder",
  });
  syncFromField();
}
defineExpose({ focus, insertTemplate });
</script>

<style>
math-field.math-textfield {
  flex: 1;
  align-self: center;
  min-width: 0;
  min-height: 40px;
  max-height: 120px;
  display: block;
  border: none;
  background: transparent;
  color: var(--qa-text, var(--color-text-default));
  padding: 8px 0;
  font-size: 16px;
  line-height: 1.5;
  overflow-x: auto;
  overflow-y: auto;
  outline: none;
  /* MathLive 主题变量，贴合问答页配色 */
  --caret-color: var(--qa-primary-600, var(--color-primary-600));
  --primary-color: var(--qa-primary-600, var(--color-primary-600));
  --selection-background-color: var(--qa-primary-100, var(--color-primary-100));
  --contains-highlight-background-color: transparent;
  --smart-fence-color: var(--qa-secondary, var(--color-text-secondary));
  --placeholder-color: var(--qa-hint, var(--color-text-muted));
}

math-field.math-textfield:focus,
math-field.math-textfield:focus-within {
  outline: none;
}

/* 隐藏 MathLive 自带的菜单/虚拟键盘触发按钮，保持输入栏干净 */
math-field.math-textfield::part(menu-toggle),
math-field.math-textfield::part(virtual-keyboard-toggle) {
  display: none;
}

math-field.math-textfield[disabled] {
  opacity: .6;
}
</style>
