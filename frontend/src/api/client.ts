import type { ApiResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

let token = localStorage.getItem("class_agent_token") || "";

export function setToken(value: string) {
  token = value;
  localStorage.setItem("class_agent_token", value);
}

export function clearToken() {
  token = "";
  localStorage.removeItem("class_agent_token");
}

function buildUrl(path: string, query?: Record<string, unknown>) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.pathname + url.search;
}

type ValidationIssue = {
  loc?: Array<string | number>;
  msg?: string;
  message?: string;
  type?: string;
  ctx?: Record<string, unknown>;
};

function fieldName(loc?: Array<string | number>) {
  const parts = (loc || []).filter((item) => !["body", "query", "path"].includes(String(item)));
  return parts.length ? parts.join(".") : "参数";
}

function issueText(issue: ValidationIssue) {
  const type = String(issue.type || "");
  const ctx = issue.ctx || {};
  if (type.includes("missing")) return "不能为空";
  if (type.includes("string_too_short")) return `至少 ${ctx.min_length || 1} 位`;
  if (type.includes("string_too_long")) return `最多 ${ctx.max_length || ""} 位`;
  if (type.includes("greater_than_equal")) return `不能小于 ${ctx.ge || ""}`;
  if (type.includes("less_than_equal")) return `不能大于 ${ctx.le || ""}`;
  if (type.includes("int_parsing") || type.includes("float_parsing")) return "必须为数字";
  if (type.includes("bool_parsing")) return "必须为布尔值";
  return issue.msg || issue.message || "格式不正确";
}

function errorMessage(payload: ApiResponse<unknown> | null) {
  if (!payload) return "请求失败";
  if (Array.isArray(payload.data) && payload.data.length) {
    const details = payload.data
      .slice(0, 3)
      .map((item) => {
        const issue = item as ValidationIssue;
        return `${fieldName(issue.loc)}：${issueText(issue)}`;
      })
      .join("；");
    const suffix = payload.data.length > 3 ? "；更多参数有误" : "";
    return `${payload.message || "请求参数校验失败"}：${details}${suffix}`;
  }
  return payload.message || "请求失败";
}

async function request<T>(path: string, init: RequestInit = {}, query?: Record<string, unknown>) {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(buildUrl(path, query), { ...init, headers });
  const payload = (await response.json().catch(() => null)) as ApiResponse<T> | null;
  if (!response.ok || !payload || payload.code !== 0) {
    throw new Error(errorMessage(payload as ApiResponse<unknown> | null));
  }
  return payload.data;
}

async function download(path: string, filename?: string, query?: Record<string, unknown>) {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(buildUrl(path, query), { headers });
  if (!response.ok) throw new Error("下载失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "download";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string, query?: Record<string, unknown>) => request<T>(path, {}, query),
  post: <T>(path: string, body?: unknown, query?: Record<string, unknown>) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }, query),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  download
};
