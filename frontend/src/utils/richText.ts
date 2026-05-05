import MarkdownIt from "markdown-it";
import katex from "katex";
import "katex/dist/katex.min.css";

const markdownRenderer = new MarkdownIt({ html: false, linkify: true, breaks: true });
const textPayloadKeys = [
  "markdownContent",
  "markdown_content",
  "llmResult",
  "llm_result",
  "page_text",
  "script_text",
  "content",
  "text"
] as const;

function renderMath(source: string, displayMode: boolean) {
  try {
    return katex.renderToString(source, {
      displayMode,
      throwOnError: false,
      strict: false,
      output: "html",
    });
  } catch {
    return source;
  }
}

function extractSerializedTextValues(value: string) {
  const keyPattern = new RegExp(String.raw`['"](?:${textPayloadKeys.join("|")})['"]\s*:\s*`, "g");
  const pieces: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = keyPattern.exec(value))) {
    let cursor = match.index + match[0].length;
    while (/\s/.test(value[cursor] || "")) cursor += 1;
    const quote = value[cursor];
    if (quote !== "'" && quote !== "\"") continue;
    cursor += 1;
    let raw = "";
    let escaped = false;
    for (; cursor < value.length; cursor += 1) {
      const char = value[cursor];
      if (escaped) {
        raw += `\\${char}`;
        escaped = false;
        continue;
      }
      if (char === "\\") {
        escaped = true;
        continue;
      }
      if (char === quote) {
        if (raw.trim()) pieces.push(raw);
        keyPattern.lastIndex = cursor + 1;
        break;
      }
      raw += char;
    }
    if (escaped && raw.trim()) pieces.push(`${raw}\\`);
  }
  return pieces.join("\n\n");
}

export function extractStructuredText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(extractStructuredText).filter(Boolean).join("\n\n");
  if (typeof value === "object") {
    const payload = value as Record<string, unknown>;
    for (const key of textPayloadKeys) {
      const text = extractStructuredText(payload[key]);
      if (text) return text;
    }
    return Object.values(payload).map(extractStructuredText).filter(Boolean).join("\n\n");
  }
  let text = String(value).trim();
  if (!text) return "";
  if (text.startsWith("{") || text.startsWith("[")) {
    try {
      return extractStructuredText(JSON.parse(text));
    } catch {
      text = extractSerializedTextValues(text) || text;
    }
  }
  return text
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\'/g, "'")
    .replace(/\\"/g, "\"")
    .trim();
}

function normalizeLatexEscapes(value: string) {
  if (!value.includes("\\")) return value;
  return value.replace(/(^|[^\\])\\\\([A-Za-z])/g, (_match, prefix: string, command: string) => `${prefix}\\${command}`);
}

function wrapBareLatexBlocks(value: string) {
  if (!value.includes("\\")) return value;
  const command = String.raw`(?:frac|mathrm|mathbf|mathbb|sqrt|sum|int|lim|left|right|begin|end|cdot|times|leq|geq|neq|approx|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|Delta|Omega|infty)`;
  const commandPattern = new RegExp(String.raw`\\${command}`, "g");
  let inFence = false;
  return value.split("\n").map((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      inFence = !inFence;
      return line;
    }
    if (
      inFence ||
      !trimmed ||
      trimmed.includes("@@MATH_") ||
      trimmed.startsWith("$$") ||
      trimmed.endsWith("$$") ||
      trimmed.startsWith("\\[") ||
      trimmed.startsWith("\\(")
    ) {
      return line;
    }
    const commands = trimmed.match(commandPattern) || [];
    const syntaxWeight = (trimmed.match(/[\\{}_^=&]/g) || []).length / Math.max(trimmed.length, 1);
    const formulaLike = commands.length > 0 && (/\\begin\{|\\left|\\right|\\frac|\\mathbb|\\mathrm|[_^=]/.test(trimmed));
    if (formulaLike && (trimmed.startsWith("\\") || syntaxWeight > 0.12 || trimmed.length > 32)) {
      const leading = line.match(/^\s*/)?.[0] || "";
      return `${leading}$$ ${trimmed} $$`;
    }
    return line;
  }).join("\n");
}

function wrapInlineBareLatex(value: string) {
  if (!value.includes("\\")) return value;
  const command = String.raw`(?:frac|mathrm|mathbf|mathbb|sqrt|sum|int|lim|left|right|cdot|times|div|pm|leq|geq|neq|approx|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|Delta|Omega|infty)`;
  const pattern = new RegExp(String.raw`(^|[\s：:，,（(])((?:\\${command}(?:\{[^{}]*\}|\[[^\]]*\]|[^\s。；;!?！？])*)+)`, "g");
  return value.split("\n").map((line) => {
    if (line.includes("@@MATH_") || line.includes("$$") || line.includes("\\[") || line.includes("\\(")) return line;
    return line.replace(pattern, (match, prefix: string, expr: string) => {
      if (!expr) return match;
      return `${prefix}$${expr.trim()}$`;
    });
  }).join("\n");
}

export function renderRichText(value?: unknown) {
  if (!value) return "";
  const mathParts: string[] = [];
  const stash = (html: string) => {
    const token = `@@MATH_${mathParts.length}@@`;
    mathParts.push(html);
    return token;
  };
  const renderDelimitedMath = (text: string) => text
    .replace(/\$\$([\s\S]+?)\$\$/g, (_match, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), true)))
    .replace(/\\\[([\s\S]+?)\\\]/g, (_match, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), true)))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_match, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), false)))
    .replace(/(^|[^\\])\$([^$\n]+?)\$/g, (_match, prefix: string, expr: string) => `${prefix}${stash(renderMath(normalizeLatexEscapes(expr.trim()), false))}`);
  const extracted = normalizeLatexEscapes(extractStructuredText(value));
  const delimitedRendered = renderDelimitedMath(extracted);
  const inferredMath = wrapInlineBareLatex(wrapBareLatexBlocks(delimitedRendered));
  const textWithDelimitedMath = renderDelimitedMath(inferredMath);
  return markdownRenderer.render(textWithDelimitedMath).replace(/@@MATH_(\d+)@@/g, (_match, index: string) => mathParts[Number(index)] || "");
}
