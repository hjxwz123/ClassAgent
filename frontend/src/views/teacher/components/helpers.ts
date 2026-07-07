// 从 TeacherView.vue 抽出的教师端纯函数。原定义在 TeacherView，抽出以便被抽出的子组件复用。
// 注意：statusText/relativeTime 的语义与学生端不同（映射表、"从未"文案有别），故保持教师端本地实现，不与 utils/* 合并。
import { File, FileEdit, FileText, Presentation } from "../../../icons";

export function firstChar(value?: string) {
  return (value || "-").slice(0, 1);
}

export function relativeTime(value?: string | null) {
  if (!value) return "从未";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "刚刚";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
  return `${Math.floor(seconds / 86400)}天前`;
}

export function statusClass(status?: string) {
  if (["ready", "published", "active", "success"].includes(String(status))) return "tag-success";
  if (["pending", "processing", "review"].includes(String(status))) return "tag-warning";
  if (["failed", "inactive", "disabled"].includes(String(status))) return "tag-danger";
  return "";
}

export function statusText(status?: string) {
  return { ready: "已解析", published: "已发布", active: "进行中", inactive: "已下架", pending: "待处理", processing: "处理中", failed: "失败", draft: "草稿", review: "待发布", closed: "已关闭" }[String(status)] || String(status || "-");
}

export function fileIcon(type: string) {
  if (type === "pptx") return Presentation;
  if (type === "pdf") return FileText;
  if (type === "docx") return FileEdit;
  return File;
}

export function typeText(type: string) {
  return { pptx: "PPT", pdf: "PDF", docx: "Word", txt: "TXT/Markdown" }[type] || type;
}
