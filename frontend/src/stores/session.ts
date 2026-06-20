import { defineStore } from "pinia";
import { api, ApiError, clearToken, getToken, setToken, setUnauthorizedHandler } from "../api/client";
import { router } from "../router";
import type { User } from "../types";

type NoticeType = "success" | "warning" | "error" | "info";

const LOGIN_ROUTE = "/auth";

// 只注册一次全局未授权回调，且避免在登录页重复跳转
let unauthorizedHandlerInstalled = false;

export const useSessionStore = defineStore("session", {
  state: () => ({
    user: null as User | null,
    initialized: false,
    toasts: [] as Array<{ id: number; type: NoticeType; text: string }>
  }),
  actions: {
    // 注册 client.ts 的全局未授权回调：token 任意时刻失效(改密吊销/会话过期)
    // → 清理本地会话并回到登录页。在 bootstrap 时安装一次即可覆盖整个应用生命周期。
    installUnauthorizedHandler() {
      if (unauthorizedHandlerInstalled) return;
      unauthorizedHandlerInstalled = true;
      setUnauthorizedHandler(() => {
        // client.ts 已调用 clearToken()，这里再次调用保证幂等，并清空内存中的用户态
        clearToken();
        this.user = null;
        this.initialized = true;
        this.pushToast("warning", "登录状态已失效，请重新登录");
        // 已经在登录页则不重复跳转；否则用 router 做 SPA 跳转，失败兜底 window.location
        const current = router.currentRoute.value;
        if (current.path === LOGIN_ROUTE) return;
        router.replace(LOGIN_ROUTE).catch(() => {
          if (window.location.pathname !== LOGIN_ROUTE) window.location.assign(LOGIN_ROUTE);
        });
      });
    },
    async bootstrap() {
      this.installUnauthorizedHandler();
      if (this.initialized) return;
      if (!getToken()) {
        this.initialized = true;
        return;
      }
      // 只有鉴权确实失效(401/403)才清 token；网络抖动/后端重启等瞬时故障
      // 保留 token 并重试一次，避免"刷新页面就被登出"
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          this.user = await api.get<User>("/auth/me");
          break;
        } catch (error) {
          const status = error instanceof ApiError ? error.status : -1;
          if (status === 401 || status === 403) {
            clearToken();
            this.user = null;
            break;
          }
          if (attempt === 0) {
            await new Promise((resolve) => setTimeout(resolve, 600));
            continue;
          }
          this.user = null;
        }
      }
      this.initialized = true;
    },
    setSession(token: string, user: User) {
      setToken(token);
      this.user = user;
      this.initialized = true;
    },
    setUser(user: User) {
      this.user = user;
      this.initialized = true;
    },
    logout() {
      clearToken();
      this.user = null;
      this.initialized = true;
      this.pushToast("info", "已退出");
    },
    pushToast(type: NoticeType, text: string) {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, type, text });
    },
    closeToast(id: number) {
      this.toasts = this.toasts.filter((item) => item.id !== id);
    }
  }
});
