// 数学公式键盘的键位数据（分类符号盘）。
// - 面板按键用 KaTeX 把 label 渲染成真实符号，做到「所见即所得」的键盘（类似 Word 插入公式）；
// - insert 模板里的占位符 CARET(▮) 标记「插入后光标应落点」；toMathfieldInsert() 会把它转成
//   MathLive 的 #?/#@ 语法插入到公式输入栏（见 utils/mathfield.ts）。

export const CARET = "▮";

export type PlainSegment = { type: "text" | "math"; value: string };

/** 把「散文 + $...$」拆成文本段与数学段（未配对的 $ 当普通文本）。 */
export function parsePlainSegments(plain: string): PlainSegment[] {
  const segments: PlainSegment[] = [];
  let text = "";
  let i = 0;
  const flushText = () => {
    if (text) segments.push({ type: "text", value: text });
    text = "";
  };
  while (i < plain.length) {
    const ch = plain[i];
    if (ch === "$" && plain[i - 1] !== "\\") {
      const end = plain.indexOf("$", i + 1);
      if (end > i) {
        const inner = plain.slice(i + 1, end).trim();
        if (inner) {
          flushText();
          segments.push({ type: "math", value: inner });
        }
        i = end + 1;
        continue;
      }
    }
    text += ch;
    i += 1;
  }
  flushText();
  return segments;
}

export type MathKey = {
  /** 渲染在按键上的 KaTeX 源码（所见即所得的符号）。为空时回退显示 fallback 文本。 */
  label: string;
  /** 插入到输入框的 LaTeX 模板，用 CARET 标记光标落点。 */
  insert: string;
  /** 无障碍/悬浮提示。 */
  title: string;
  /** 按键上直接显示的文本（用于三角函数名等不便用 KaTeX 渲染的键）。 */
  text?: string;
  /** 占两格宽（如分数、矩阵）。 */
  wide?: boolean;
};

export type MathGroup = { key: string; name: string; keys: MathKey[] };

export const MATH_GROUPS: MathGroup[] = [
  {
    key: "common",
    name: "常用",
    keys: [
      { label: "x^{2}", insert: "^{2}", title: "平方" },
      { label: "x^{\\square}", insert: "^{▮}", title: "指数（上标）" },
      { label: "x_{\\square}", insert: "_{▮}", title: "下标" },
      { label: "\\sqrt{\\square}", insert: "\\sqrt{▮}", title: "根号" },
      { label: "\\frac{a}{b}", insert: "\\frac{▮}{}", title: "分数", wide: true },
      { label: "\\pi", insert: "\\pi", title: "圆周率 π" },
      { label: "\\infty", insert: "\\infty", title: "无穷" },
      { label: "\\times", insert: "\\times ", title: "乘号" },
      { label: "\\div", insert: "\\div ", title: "除号" },
      { label: "\\pm", insert: "\\pm ", title: "正负号" },
      { label: "\\cdot", insert: "\\cdot ", title: "点乘" },
      { label: "\\leq", insert: "\\leq ", title: "小于等于" },
      { label: "\\geq", insert: "\\geq ", title: "大于等于" },
      { label: "\\neq", insert: "\\neq ", title: "不等于" },
      { label: "\\approx", insert: "\\approx ", title: "约等于" },
      { label: "\\rightarrow", insert: "\\rightarrow ", title: "趋向 / 箭头" },
    ],
  },
  {
    key: "script",
    name: "上下标",
    keys: [
      { label: "\\square^{\\square}", insert: "^{▮}", title: "上标（指数）" },
      { label: "\\square_{\\square}", insert: "_{▮}", title: "下标" },
      { label: "\\square_{\\square}^{\\square}", insert: "_{▮}^{}", title: "上下标同时" },
      { label: "x^{2}", insert: "x^{2}", title: "x 平方" },
      { label: "x^{n}", insert: "x^{n}", title: "x 的 n 次方" },
      { label: "x_{i}", insert: "x_{i}", title: "x 下标 i" },
      { label: "a_{n}", insert: "a_{n}", title: "数列 aₙ" },
      { label: "e^{x}", insert: "e^{▮}", title: "e 指数" },
      { label: "10^{n}", insert: "10^{▮}", title: "科学计数" },
      { label: "\\sqrt{\\square}", insert: "\\sqrt{▮}", title: "平方根" },
      { label: "\\sqrt[n]{\\square}", insert: "\\sqrt[▮]{}", title: "n 次根" },
      { label: "\\overline{x}", insert: "\\overline{▮}", title: "平均值 / 上划线" },
      { label: "\\vec{a}", insert: "\\vec{▮}", title: "向量" },
      { label: "\\hat{x}", insert: "\\hat{▮}", title: "帽号" },
      { label: "\\dot{x}", insert: "\\dot{▮}", title: "一阶导（点）" },
    ],
  },
  {
    key: "fraction",
    name: "根号分数",
    keys: [
      { label: "\\frac{a}{b}", insert: "\\frac{▮}{}", title: "分数", wide: true },
      { label: "\\frac{\\square}{\\square}", insert: "\\frac{▮}{}", title: "空白分数", wide: true },
      { label: "\\sqrt{\\square}", insert: "\\sqrt{▮}", title: "平方根" },
      { label: "\\sqrt[3]{\\square}", insert: "\\sqrt[3]{▮}", title: "立方根" },
      { label: "\\sqrt[n]{\\square}", insert: "\\sqrt[▮]{}", title: "n 次根" },
      { label: "\\frac{dy}{dx}", insert: "\\frac{dy}{dx}", title: "导数", wide: true },
      { label: "\\frac{\\partial y}{\\partial x}", insert: "\\frac{\\partial ▮}{\\partial }", title: "偏导", wide: true },
      { label: "\\sum_{i=1}^{n}", insert: "\\sum_{i=1}^{n} ▮", title: "求和", wide: true },
      { label: "\\prod_{i=1}^{n}", insert: "\\prod_{i=1}^{n} ▮", title: "连乘", wide: true },
      { label: "\\int_{a}^{b}", insert: "\\int_{▮}^{} ", title: "定积分", wide: true },
      { label: "\\int", insert: "\\int ▮\\, dx", title: "不定积分", wide: true },
      { label: "\\lim_{x\\to 0}", insert: "\\lim_{x \\to ▮} ", title: "极限", wide: true },
      { label: "\\binom{n}{k}", insert: "\\binom{▮}{}", title: "组合数" },
    ],
  },
  {
    key: "trig",
    name: "三角函数",
    keys: [
      { label: "\\sin", text: "sin", insert: "\\sin(▮)", title: "正弦 sin" },
      { label: "\\cos", text: "cos", insert: "\\cos(▮)", title: "余弦 cos" },
      { label: "\\tan", text: "tan", insert: "\\tan(▮)", title: "正切 tan" },
      { label: "\\cot", text: "cot", insert: "\\cot(▮)", title: "余切 cot" },
      { label: "\\sec", text: "sec", insert: "\\sec(▮)", title: "正割 sec" },
      { label: "\\csc", text: "csc", insert: "\\csc(▮)", title: "余割 csc" },
      { label: "\\arcsin", text: "arcsin", insert: "\\arcsin(▮)", title: "反正弦" },
      { label: "\\arccos", text: "arccos", insert: "\\arccos(▮)", title: "反余弦" },
      { label: "\\arctan", text: "arctan", insert: "\\arctan(▮)", title: "反正切" },
      { label: "\\sinh", text: "sinh", insert: "\\sinh(▮)", title: "双曲正弦" },
      { label: "\\cosh", text: "cosh", insert: "\\cosh(▮)", title: "双曲余弦" },
      { label: "\\tanh", text: "tanh", insert: "\\tanh(▮)", title: "双曲正切" },
      { label: "\\log", text: "log", insert: "\\log(▮)", title: "对数 log" },
      { label: "\\log_{a}", text: "logₐ", insert: "\\log_{▮} ", title: "以 a 为底对数" },
      { label: "\\ln", text: "ln", insert: "\\ln(▮)", title: "自然对数 ln" },
      { label: "\\theta", insert: "\\theta", title: "角 θ" },
      { label: "^{\\circ}", insert: "^{\\circ}", title: "角度 °" },
      { label: "\\pi", insert: "\\pi", title: "π" },
    ],
  },
  {
    key: "greek",
    name: "希腊字母",
    keys: [
      { label: "\\alpha", insert: "\\alpha", title: "alpha α" },
      { label: "\\beta", insert: "\\beta", title: "beta β" },
      { label: "\\gamma", insert: "\\gamma", title: "gamma γ" },
      { label: "\\delta", insert: "\\delta", title: "delta δ" },
      { label: "\\epsilon", insert: "\\epsilon", title: "epsilon ε" },
      { label: "\\zeta", insert: "\\zeta", title: "zeta ζ" },
      { label: "\\eta", insert: "\\eta", title: "eta η" },
      { label: "\\theta", insert: "\\theta", title: "theta θ" },
      { label: "\\lambda", insert: "\\lambda", title: "lambda λ" },
      { label: "\\mu", insert: "\\mu", title: "mu μ" },
      { label: "\\nu", insert: "\\nu", title: "nu ν" },
      { label: "\\xi", insert: "\\xi", title: "xi ξ" },
      { label: "\\rho", insert: "\\rho", title: "rho ρ" },
      { label: "\\sigma", insert: "\\sigma", title: "sigma σ" },
      { label: "\\tau", insert: "\\tau", title: "tau τ" },
      { label: "\\phi", insert: "\\phi", title: "phi φ" },
      { label: "\\chi", insert: "\\chi", title: "chi χ" },
      { label: "\\psi", insert: "\\psi", title: "psi ψ" },
      { label: "\\omega", insert: "\\omega", title: "omega ω" },
      { label: "\\Delta", insert: "\\Delta", title: "大 Delta Δ" },
      { label: "\\Sigma", insert: "\\Sigma", title: "大 Sigma Σ" },
      { label: "\\Pi", insert: "\\Pi", title: "大 Pi Π" },
      { label: "\\Omega", insert: "\\Omega", title: "大 Omega Ω" },
      { label: "\\Phi", insert: "\\Phi", title: "大 Phi Φ" },
    ],
  },
  {
    key: "relation",
    name: "运算关系",
    keys: [
      { label: "+", insert: "+", title: "加" },
      { label: "-", insert: "-", title: "减" },
      { label: "\\times", insert: "\\times ", title: "乘" },
      { label: "\\div", insert: "\\div ", title: "除" },
      { label: "\\pm", insert: "\\pm ", title: "正负" },
      { label: "\\mp", insert: "\\mp ", title: "负正" },
      { label: "\\cdot", insert: "\\cdot ", title: "点乘" },
      { label: "=", insert: "=", title: "等于" },
      { label: "\\neq", insert: "\\neq ", title: "不等于" },
      { label: "\\approx", insert: "\\approx ", title: "约等于" },
      { label: "\\equiv", insert: "\\equiv ", title: "恒等 / 同余" },
      { label: "\\leq", insert: "\\leq ", title: "小于等于" },
      { label: "\\geq", insert: "\\geq ", title: "大于等于" },
      { label: "<", insert: "<", title: "小于" },
      { label: ">", insert: ">", title: "大于" },
      { label: "\\to", insert: "\\to ", title: "趋向" },
      { label: "\\Rightarrow", insert: "\\Rightarrow ", title: "推出" },
      { label: "\\Leftrightarrow", insert: "\\Leftrightarrow ", title: "等价" },
      { label: "\\infty", insert: "\\infty", title: "无穷" },
      { label: "\\partial", insert: "\\partial ", title: "偏微分" },
      { label: "\\nabla", insert: "\\nabla ", title: "梯度算子" },
      { label: "\\in", insert: "\\in ", title: "属于" },
      { label: "\\notin", insert: "\\notin ", title: "不属于" },
      { label: "\\subseteq", insert: "\\subseteq ", title: "子集" },
      { label: "\\cup", insert: "\\cup ", title: "并集" },
      { label: "\\cap", insert: "\\cap ", title: "交集" },
      { label: "\\forall", insert: "\\forall ", title: "任意" },
      { label: "\\exists", insert: "\\exists ", title: "存在" },
    ],
  },
  {
    key: "bracket",
    name: "括号绝对值",
    keys: [
      { label: "\\left| \\square \\right|", insert: "\\left|▮\\right|", title: "绝对值" },
      { label: "\\left\\| \\square \\right\\|", insert: "\\left\\|▮\\right\\|", title: "范数（双竖线）" },
      { label: "\\left( \\square \\right)", insert: "\\left(▮\\right)", title: "自适应圆括号" },
      { label: "\\left[ \\square \\right]", insert: "\\left[▮\\right]", title: "方括号" },
      { label: "\\left\\{ \\square \\right\\}", insert: "\\left\\{▮\\right\\}", title: "花括号 / 集合" },
      { label: "\\lfloor \\square \\rfloor", insert: "\\lfloor ▮\\rfloor", title: "向下取整" },
      { label: "\\lceil \\square \\rceil", insert: "\\lceil ▮\\rceil", title: "向上取整" },
      { label: "\\langle \\square \\rangle", insert: "\\langle ▮\\rangle", title: "尖括号 / 内积" },
      { label: "( )", insert: "(▮)", title: "普通圆括号" },
      { label: "\\%", insert: "\\%", title: "百分号" },
      { label: "\\begin{cases}a\\\\b\\end{cases}", insert: "\\begin{cases} ▮ \\\\  \\end{cases}", title: "分段函数", wide: true },
      { label: "\\begin{pmatrix}a&b\\\\c&d\\end{pmatrix}", insert: "\\begin{pmatrix} ▮ &  \\\\  &  \\end{pmatrix}", title: "2×2 矩阵", wide: true },
    ],
  },
];
