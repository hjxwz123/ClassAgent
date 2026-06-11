import { defineStore } from "pinia";
import { api, ApiError, clearToken, getToken, setToken } from "../api/client";
import type { User } from "../types";

type NoticeType = "success" | "warning" | "error" | "info";

export const useSessionStore = defineStore("session", {
  state: () => ({
    user: null as User | null,
    initialized: false,
    toasts: [] as Array<{ id: number; type: NoticeType; text: string }>
  }),
  actions: {
    async bootstrap() {
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
