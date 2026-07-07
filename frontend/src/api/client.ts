import type { ApiResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const TOKEN_KEY = "class_agent_token";

// 记住登录为默认行为：token 持久化在 localStorage，关浏览器重开仍保持登录，
// 仅用户主动退出（或后端判定 401/403）时清除；改密码/重置密码时后端会提升
// token_version 吊销全部旧 token。兼容迁移历史版本短暂使用过的 sessionStorage。
let token = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || "";
sessionStorage.removeItem(TOKEN_KEY);
if (token) localStorage.setItem(TOKEN_KEY, token);

export function setToken(value: string) {
  token = value;
  localStorage.setItem(TOKEN_KEY, value);
}

export function clearToken() {
  token = "";
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return token;
}

// 全局未授权(401)回调：token 中途失效(改密吊销/会话过期/账号禁用)时，
// 已打开页面的请求会拿到 401，需要统一清理会话并跳转登录，避免界面"卡死"。
// 由 session store 在应用初始化时通过 setUnauthorizedHandler 注册。
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

// 登录/引导自身的鉴权失败属正常业务流(密码错误、未登录探测 /auth/me)，
// 不应触发全局登出跳转，否则会与调用方的局部处理冲突或造成重复跳转。
const UNAUTHORIZED_EXEMPT_PATHS = ["/auth/login", "/auth/me"];

function isUnauthorizedExempt(path: string) {
  // path 形如 "/auth/login" 或带 query，取 pathname 前缀判断
  const pathname = path.split("?")[0];
  return UNAUTHORIZED_EXEMPT_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

// 防重入：多个并发请求同时 401 时只触发一次清理/跳转
let handlingUnauthorized = false;

function handleUnauthorized(status: number, path: string) {
  // 仅 401 触发全局登出跳转。后端对一切“鉴权/会话失效”都返回 401：缺失/非法/过期令牌、
  // 改密吊销(token_version 不匹配)、用户被删除、账号被禁用(见 app/core/deps.get_current_user)。
  // 403(forbidden) 是“已认证但无权访问该资源”——未加入的课程、未发布课时、角色不匹配等业务授权错误，
  // 必须由调用方局部处理(提示/错误态)，绝不能登出。否则在问答里点开一个无权来源(如未发布课时)就会被误登出。
  if (status !== 401) return;
  if (isUnauthorizedExempt(path)) return;
  if (handlingUnauthorized) return;
  handlingUnauthorized = true;
  try {
    clearToken();
    onUnauthorized?.();
  } finally {
    // 跳转/清理在同一事件循环内完成后即解锁，后续真正的新会话不受影响
    handlingUnauthorized = false;
  }
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

type UploadProgress = {
  loaded: number;
  total: number;
  percent: number;
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

function parsePayload<T>(raw: string) {
  try {
    return raw ? (JSON.parse(raw) as ApiResponse<T>) : null;
  } catch {
    return null;
  }
}

/* 带 HTTP 状态码的请求错误：调用方可据此区分鉴权失败(401/403)与网络/服务端异常(0/5xx) */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}, query?: Record<string, unknown>) {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    // cache:"no-store"：API 返回的是按用户鉴权的私有数据，禁止浏览器缓存/复用，
    // 避免切换账号后从缓存读到上一个用户的数据（如问答历史）。
    response = await fetch(buildUrl(path, query), { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError("网络连接失败，请稍后重试", 0);
  }
  const payload = (await response.json().catch(() => null)) as ApiResponse<T> | null;
  if (!response.ok || !payload || payload.code !== 0) {
    // 先触发全局未授权处理(清 token + 登出跳转)，再照常抛 ApiError，
    // 这样调用方的局部 catch 仍能运行，但全局已确保回到登录页。
    handleUnauthorized(response.status, path);
    throw new ApiError(errorMessage(payload as ApiResponse<unknown> | null), response.status);
  }
  return payload.data;
}

function upload<T>(
  path: string,
  body: FormData,
  options: {
    query?: Record<string, unknown>;
    onProgress?: (progress: UploadProgress) => void;
  } = {}
) {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl(path, options.query), true);
    xhr.setRequestHeader("Accept", "application/json");
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      const total = event.lengthComputable ? event.total : 0;
      const percent = total > 0 ? Math.min(100, Math.round((event.loaded / total) * 100)) : 0;
      options.onProgress?.({ loaded: event.loaded, total, percent });
    };

    xhr.onerror = () => reject(new Error("网络异常，上传失败"));
    xhr.onabort = () => reject(new Error("上传已取消"));
    xhr.onload = () => {
      const payload = parsePayload<T>(xhr.responseText || "");
      if (xhr.status >= 200 && xhr.status < 300 && payload && payload.code === 0) {
        resolve(payload.data);
        return;
      }
      handleUnauthorized(xhr.status, path);
      reject(new Error(errorMessage(payload as ApiResponse<unknown> | null)));
    };

    xhr.send(body);
  });
}

async function download(path: string, filename?: string, query?: Record<string, unknown>) {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(buildUrl(path, query), { headers });
  if (!response.ok) {
    handleUnauthorized(response.status, path);
    throw new Error("下载失败");
  }
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

type StreamHandler = (event: string, data: any) => void;

async function streamPost(path: string, body: unknown, onEvent: StreamHandler, query?: Record<string, unknown>, signal?: AbortSignal) {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "text/event-stream");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(buildUrl(path, query), {
    method: "POST",
    headers,
    body: JSON.stringify(body ?? {}),
    signal,
  });
  if (!response.ok || !response.body) {
    handleUnauthorized(response.status, path);
    const payload = (await response.json().catch(() => null)) as ApiResponse<unknown> | null;
    throw new Error(errorMessage(payload));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  // 让出渲染：只在距上次绘制超过一帧(~16ms)时才真正让出，并用 requestAnimationFrame 在帧边界绘制。
  // 旧实现对每个 SSE 事件都 await setTimeout(0)，而浏览器会把 setTimeout(0) 钳到 ~4ms（嵌套后更久），
  // 于是即便后端/网络已把整段答案一次性送达，前端也被迫每 token 至少等 4ms，表现为"后端很快、前端逐字卡顿"。
  const nowMs = () => (typeof performance !== "undefined" && performance.now ? performance.now() : Date.now());
  let lastPaint = nowMs();
  const yieldToRenderer = async () => {
    if (nowMs() - lastPaint < 16) return; // 同一帧内的多个 token 同步处理、合并为一次绘制
    lastPaint = nowMs();
    await new Promise<void>((resolve) => {
      if (typeof requestAnimationFrame === "function") requestAnimationFrame(() => resolve());
      else window.setTimeout(resolve, 0);
    });
  };

  const consume = async (block: string) => {
    const lines = block.split(/\r?\n/);
    let event = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim() || "message";
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    }
    if (!dataLines.length) return;
    const raw = dataLines.join("\n");
    const data = raw ? JSON.parse(raw) : null;
    if (event === "error") throw new Error(data?.message || "请求失败");
    onEvent(event, data);
    await yieldToRenderer();
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    let separator = buffer.search(/\r?\n\r?\n/);
    while (separator >= 0) {
      const block = buffer.slice(0, separator);
      const match = buffer.slice(separator).match(/^\r?\n\r?\n/);
      buffer = buffer.slice(separator + (match?.[0].length || 2));
      await consume(block);
      separator = buffer.search(/\r?\n\r?\n/);
    }
    if (done) break;
  }
  if (buffer.trim()) await consume(buffer);
}

export const api = {
  get: <T>(path: string, query?: Record<string, unknown>) => request<T>(path, {}, query),
  post: <T>(path: string, body?: unknown, query?: Record<string, unknown>) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }, query),
  upload: <T>(
    path: string,
    body: FormData,
    options?: {
      query?: Record<string, unknown>;
      onProgress?: (progress: UploadProgress) => void;
    }
  ) => upload<T>(path, body, options),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  download,
  streamPost: (path: string, body: unknown, onEvent: StreamHandler, query?: Record<string, unknown>, signal?: AbortSignal) =>
    streamPost(path, body, onEvent, query, signal)
};
