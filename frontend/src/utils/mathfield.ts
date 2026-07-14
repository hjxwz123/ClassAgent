// MathLive / 公式输入的接线工具。
// 交互模型：输入栏是普通 contenteditable 文本区（中文/IME/光标全原生可靠），公式以「内联渲染块(chip)」
// 嵌在行文里，底层以 $...$ 存储；编辑单个公式时弹出 MathLive 小编辑器（纯数学模式，方向键进出上下标）。
// - configureMathfield(): 全局配置 MathLive 字体目录、禁用音效（只需一次）。
// - toMathfieldInsert(): 把公式键盘模板（▮=光标）转成 MathLive insert 语法（#? 占位 / #@ 选区）。
// - stripOuterMath(): 剥掉 MathLive getValue('latex') 的外层数学定界，得到裸公式 LaTeX。
import { MathfieldElement } from "mathlive";
import { CARET } from "./mathInput";

let configured = false;
export function configureMathfield() {
  if (configured) return;
  configured = true;
  // 字体拷到 public/mathlive/fonts，随构建进 dist；关掉按键音效（省 244K 音频资源）。
  MathfieldElement.fontsDirectory = "/mathlive/fonts";
  MathfieldElement.soundsDirectory = null;
}

/** 把公式键盘模板（▮=光标落点）转成 MathLive insert 串：有选区时首个 ▮ 用 #@ 包裹选区，否则用 #? 占位。 */
export function toMathfieldInsert(template: string, hasSelection: boolean): string {
  let first = true;
  return template.split(CARET).reduce((acc, part, index) => {
    if (index === 0) return part;
    const token = first && hasSelection ? "#@" : "#?";
    first = false;
    return acc + token + part;
  }, "");
}

/** 剥掉 MathLive getValue('latex') 外层的一层数学定界（$...$ / $$...$$ / \[..\] / \(..\)），返回裸公式 LaTeX。 */
export function stripOuterMath(latex: string): string {
  let s = (latex || "").trim();
  if (s.startsWith("$$") && s.endsWith("$$") && s.length >= 4) s = s.slice(2, -2);
  else if (s.startsWith("$") && s.endsWith("$") && s.length >= 2) s = s.slice(1, -1);
  else if ((s.startsWith("\\[") && s.endsWith("\\]")) || (s.startsWith("\\(") && s.endsWith("\\)"))) s = s.slice(2, -2);
  return s.trim();
}

// parsePlainSegments（「散文 + $...$」拆段）在 utils/mathInput.ts：
// 该函数也被消息渲染(richText)使用，放在无 mathlive 依赖的模块里，避免把 mathlive 拖进公共 chunk。
