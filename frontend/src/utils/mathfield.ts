// MathLive 混合「文本 + 公式」编辑器的接线层：
// - configureMathfield(): 全局配置字体目录、禁用音效（只需调用一次）。
// - mathfieldLatexToPlain(): 把 MathLive 的 getValue('latex')（文本用 \text{} 包、数学裸露）
//   转成我们全站统一的「散文 + $...$」格式，供发送后端 / renderRichText 渲染。
// - plainToMathfieldLatex(): 反向把「散文 + $...$」转成 MathLive 可 setValue 的 latex
//   （文本段转义后包进 \text{}，$...$ 内数学裸露），用于外部程序化写入（快捷提问、清空、解释选中）。
// - toMathfieldInsert(): 把公式键盘的模板（用 ▮ 标记光标）转成 MathLive insert 语法（#? 占位符 / #@ 选区）。
import { MathfieldElement } from "mathlive";
import { CARET } from "./mathInput";

let configured = false;
export function configureMathfield() {
  if (configured) return;
  configured = true;
  // 字体拷贝到 public/mathlive/fonts，随构建进 dist；关掉按键音效（无需额外 244K 音频资源）。
  MathfieldElement.fontsDirectory = "/mathlive/fonts";
  MathfieldElement.soundsDirectory = null;
}

/** 读取 \text{...} 的平衡花括号内容，返回 [原始内层文本, 花括号结束后的下标]。遇 \{ \} 转义不计入深度。 */
function readBracedText(latex: string, from: number): [string, number] {
  let depth = 1;
  let raw = "";
  let i = from;
  while (i < latex.length && depth > 0) {
    const ch = latex[i];
    if (ch === "\\") {
      raw += ch + (latex[i + 1] ?? "");
      i += 2;
      continue;
    }
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) { i += 1; break; }
    }
    raw += ch;
    i += 1;
  }
  return [raw, i];
}

/** 反转义 \text{} 内的常见 LaTeX 转义，得到用户可见的纯文本。 */
function unescapeText(raw: string): string {
  return raw
    .replace(/\\textbackslash\s?/g, "\\")
    .replace(/\\textasciicircum\s?/g, "^")
    .replace(/\\textasciitilde\s?/g, "~")
    .replace(/\\([{}$%#&_])/g, "$1")
    .replace(/\\,|\\;|\\:|\\!/g, " ")
    .replace(/\\\\/g, " ")
    .replace(/~/g, " ");
}

/** 清掉 MathLive 专有的占位符标记，避免把 \placeholder{} 发给后端 / KaTeX。 */
function stripMathfieldArtifacts(math: string): string {
  return math.replace(/\\placeholder(?:\[[^\]]*\])?\{([^{}]*)\}/g, "$1");
}

export function mathfieldLatexToPlain(latex: string): string {
  if (!latex) return "";
  // MathLive 的 getValue('latex') 会把整段内容外包一层数学定界（$...$ / \[...\] / \(...\)），
  // 其内部才是「\text{} 包文本、数学裸露」；先剥掉这层外包，否则会多包出 $$ / $$$。
  let src = latex.trim();
  if (src.startsWith("$$") && src.endsWith("$$") && src.length >= 4) src = src.slice(2, -2);
  else if (src.startsWith("$") && src.endsWith("$") && src.length >= 2) src = src.slice(1, -1);
  else if ((src.startsWith("\\[") && src.endsWith("\\]")) || (src.startsWith("\\(") && src.endsWith("\\)"))) src = src.slice(2, -2);
  src = src.trim();
  if (!src) return "";
  let out = "";
  let math = "";
  let i = 0;
  const flushMath = () => {
    const cleaned = stripMathfieldArtifacts(math);
    const trimmed = cleaned.trim();
    if (trimmed) {
      const lead = cleaned.slice(0, cleaned.length - cleaned.trimStart().length);
      const tail = cleaned.slice(cleaned.trimEnd().length);
      out += `${lead}$${trimmed}$${tail}`;
    } else {
      out += cleaned;
    }
    math = "";
  };
  while (i < src.length) {
    if (src.startsWith("\\text{", i)) {
      flushMath();
      const [raw, next] = readBracedText(src, i + 6);
      out += unescapeText(raw);
      i = next;
      continue;
    }
    math += src[i];
    i += 1;
  }
  flushMath();
  return out;
}

// 把「散文 + $...$」转成可直接喂给 setValue(..., { mode: 'text' }) 的字符串：
// MathLive 文本模式解析下，$...$ 会切到数学、其余按文本处理，故只需把「数学区之外」会破坏
// latex 文本解析的注释/特殊符号转义（%、#、&），$ 定界原样保留。中文与常见标点无需处理。
export function plainToMathfieldLatex(plain: string): string {
  if (!plain) return "";
  let out = "";
  let i = 0;
  while (i < plain.length) {
    const ch = plain[i];
    if (ch === "$" && plain[i - 1] !== "\\") {
      const end = plain.indexOf("$", i + 1);
      if (end > i) {
        out += plain.slice(i, end + 1); // 含两端 $ 的数学段原样保留
        i = end + 1;
        continue;
      }
    }
    out += ch === "%" ? "\\%" : ch === "#" ? "\\#" : ch === "&" ? "\\&" : ch;
    i += 1;
  }
  return out;
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
