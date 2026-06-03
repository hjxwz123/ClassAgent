// 相对时间、日期、数字格式化等小工具

function pad(n) { return n < 10 ? '0' + n : '' + n; }

function parseDate(value) {
  if (!value) return null;
  if (value instanceof Date) return value;
  // 兼容 ISO 字符串（iOS 对 '-' 分隔不友好）
  const s = String(value).replace(/-/g, '/').replace('T', ' ').replace(/\.\d+/, '').replace(/Z$/, '');
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function relativeTime(value) {
  const d = parseDate(value);
  if (!d) return '';
  const diff = Date.now() - d.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return '刚刚';
  const min = Math.floor(sec / 60);
  if (min < 60) return min + ' 分钟前';
  const hour = Math.floor(min / 60);
  if (hour < 24) return hour + ' 小时前';
  const day = Math.floor(hour / 24);
  if (day < 30) return day + ' 天前';
  return formatDate(d);
}

function formatDate(value) {
  const d = parseDate(value);
  if (!d) return '';
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}

function formatTime(value) {
  const d = parseDate(value);
  if (!d) return '';
  return pad(d.getHours()) + ':' + pad(d.getMinutes());
}

// 字节 -> 可读体积
function fileSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return n.toFixed(n >= 10 || i === 0 ? 0 : 1) + ' ' + units[i];
}

// 百分比（0-1 或 0-100 自适应）
function percent(value) {
  if (value === null || value === undefined) return 0;
  const n = Number(value);
  if (isNaN(n)) return 0;
  const p = n <= 1 ? n * 100 : n;
  return Math.max(0, Math.min(100, Math.round(p)));
}

// 问候语
function greeting() {
  const h = new Date().getHours();
  if (h < 6) return '夜深了';
  if (h < 12) return '早上好';
  if (h < 14) return '中午好';
  if (h < 18) return '下午好';
  return '晚上好';
}

// 时长（秒 -> X 分钟）
function minutes(seconds) {
  return Math.round((Number(seconds) || 0) / 60);
}

module.exports = { relativeTime, formatDate, formatTime, fileSize, percent, greeting, minutes };
