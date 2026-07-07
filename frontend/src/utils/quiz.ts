// 出题/做题域的纯展示辅助函数。原定义在 StudentView.vue，抽出以便被抽出的答题/错题子组件复用。

// 把答案值渲染为 "A. 选项文本"（下标/字母/原文都能识别）。
export function optionText(value: unknown, question?: any) {
  if (value === null || value === undefined || value === "") return "-";
  const options = Array.isArray(question?.options) ? question.options : [];
  const renderOne = (item: unknown) => {
    const index = typeof item === "number"
      ? item
      : (typeof item === "string" && /^\d+$/.test(item) ? Number(item) : (typeof item === "string" && /^[A-Z]$/i.test(item.trim()) ? item.trim().toUpperCase().charCodeAt(0) - 65 : null));
    if (index !== null && options[index] !== undefined) {
      const raw = options[index];
      const text = typeof raw === "object" ? raw.text || raw.label || JSON.stringify(raw) : String(raw);
      return `${String.fromCharCode(65 + index)}. ${text}`;
    }
    return String(item);
  };
  return Array.isArray(value) ? value.map(renderOne).join("；") : renderOne(value);
}

export function statusText(value: string) {
  const map: Record<string, string> = { published: "已发布", review: "待审核", draft: "草稿", active: "正常", done: "已完成", pending: "待处理" };
  return map[value] || value || "-";
}

// 把"下标 / 字母 / 选项原文 / 布尔判断"等各种形态的答案统一解析为选项下标集合，供解析页高亮复现。
export function answerIndexSet(value: unknown, options: any[]): Set<number> {
  const out = new Set<number>();
  const optionTexts = options.map((option) => (typeof option === "object" ? String(option?.text ?? option?.label ?? "") : String(option)));
  const push = (item: unknown) => {
    if (typeof item === "number" && Number.isInteger(item) && item >= 0) { out.add(item); return; }
    if (typeof item === "boolean") {
      const pool = item ? ["正确", "对", "true", "t", "√"] : ["错误", "错", "false", "f", "×"];
      const index = optionTexts.findIndex((text) => pool.includes(text.trim().toLowerCase()) || pool.includes(text.trim()));
      if (index >= 0) out.add(index);
      return;
    }
    if (typeof item !== "string") return;
    const trimmed = item.trim();
    if (!trimmed) return;
    if (/^\d+$/.test(trimmed)) { out.add(Number(trimmed)); return; }
    if (/^[A-Za-z]$/.test(trimmed)) { out.add(trimmed.toUpperCase().charCodeAt(0) - 65); return; }
    const index = optionTexts.findIndex((text) => text.trim() === trimmed);
    if (index >= 0) out.add(index);
  };
  if (Array.isArray(value)) value.forEach(push);
  else if (value !== null && value !== undefined && value !== "") push(value);
  return out;
}

// 参考答案的展示文本：选择题走选项复现，填空/简答展示关键词或原文。
export function referenceDisplayText(row: any): string {
  const questionData = row?.question || {};
  const value = row?.correct_answer;
  if (value === null || value === undefined || value === "") return "—";
  if (["single_choice", "multiple_choice", "judge"].includes(questionData.question_type)) {
    return String(optionText(value, questionData));
  }
  if (Array.isArray(value)) return value.map(String).join("、");
  if (typeof value === "object") {
    const keywords = (value as any).keywords || (value as any).key_points;
    if (Array.isArray(keywords) && keywords.length) return keywords.map(String).join("、");
    if ((value as any).value !== undefined) return String((value as any).value);
    return JSON.stringify(value);
  }
  return String(value);
}

// 错题卡用：从原始 reference_answer 里提取答案值（后端 QuizQuestionPayload 是原始 JSON）。
export function rawReferenceValue(question: any) {
  const reference = question?.reference_answer;
  if (reference && typeof reference === "object" && !Array.isArray(reference)) {
    return (reference as any).value ?? (reference as any).answer ?? (reference as any).correct_answer ?? (reference as any).keywords ?? null;
  }
  return reference ?? null;
}
