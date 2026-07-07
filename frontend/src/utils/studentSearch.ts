// 学生端全局搜索的纯函数（分词/打分/摘要）。原定义在 StudentView.vue，抽出以缩短主文件；无响应式状态。
import { extractStructuredText } from "./richText";

export function searchTeacherName(course: any) {
  return course?.teacher_name || course?.teacher?.nickname || course?.teacher?.name || "";
}

export function normalizeSearchText(value?: unknown) {
  return String(value ?? "").replace(/\s+/g, " ").trim().toLowerCase();
}

export function splitSearchTokens(value: string) {
  const tokens = normalizeSearchText(value).split(/[\s,，。；;、/|]+/).filter(Boolean);
  return tokens.length ? Array.from(new Set(tokens)) : [];
}

// 关键词与若干字段的匹配打分：完全相等 > 前缀 > 包含，再叠加分词命中；不匹配返回 -1。
export function searchScore(query: string, ...fields: unknown[]) {
  const haystack = normalizeSearchText(fields.filter(Boolean).map((field) => String(field)).join(" "));
  const keyword = normalizeSearchText(query);
  if (!haystack || !keyword) return -1;
  let score = 0;
  if (haystack === keyword) score += 120;
  if (haystack.startsWith(keyword)) score += 75;
  else if (haystack.includes(keyword)) score += 50;
  const tokens = splitSearchTokens(keyword);
  let matched = 0;
  tokens.forEach((token) => {
    if (haystack.includes(token)) {
      matched += 1;
      score += token.length > 1 ? 16 : 8;
    }
  });
  if (!haystack.includes(keyword) && tokens.length > 1 && matched < tokens.length) return -1;
  if (!haystack.includes(keyword) && matched === 0) return -1;
  return score;
}

export function searchExcerpt(value?: unknown, max = 72) {
  const text = extractStructuredText(String(value ?? "")).replace(/\s+/g, " ").trim();
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

export function knowledgeExcerpt(item: any) {
  const preferred = item?.content_by_level?.standard || item?.content_by_level?.beginner || item?.content_by_level?.advanced || {};
  return searchExcerpt([preferred.definition, preferred.principle, preferred.example, preferred.common_mistake, item?.content, item?.description].filter(Boolean).join(" "));
}
