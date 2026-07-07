// 日期/时间格式化纯函数。原定义在 StudentView.vue，抽出以便被抽出的子组件复用。
// 后端时间多为"无时区的北京时间字符串"，parseAppDate 负责补 Z 归一，避免被当作本地时区解析。
const BEIJING_TIME_ZONE = "Asia/Shanghai";
const TIMEZONE_SUFFIX_RE = /(Z|[+-]\d{2}:?\d{2})$/i;

export function parseAppDate(value?: string | Date | null) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const text = String(value).trim();
  if (!text) return null;
  const hasTime = /\d{2}:\d{2}/.test(text);
  const normalized = hasTime && !TIMEZONE_SUFFIX_RE.test(text) ? `${text.replace(" ", "T")}Z` : text;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function timestampMs(value?: string | Date | null) {
  return parseAppDate(value)?.getTime() || 0;
}

export function relativeTime(value?: string | Date | null) {
  const date = parseAppDate(value);
  if (!date) return "刚刚";
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return "刚刚";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
  return `${Math.floor(seconds / 86400)}天前`;
}

export function formatTime(value?: string | Date | null) {
  const date = parseAppDate(value);
  return date ? date.toLocaleString("zh-CN", { hour12: false, timeZone: BEIJING_TIME_ZONE }) : "-";
}

// 秒数 → mm:ss，用于做题计时展示。
export function timeLabel(value: number) {
  if (!Number.isFinite(value)) return "00:00";
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(Math.floor(value % 60)).padStart(2, "0")}`;
}
