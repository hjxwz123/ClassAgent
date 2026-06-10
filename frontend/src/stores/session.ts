import { defineStore } from "pinia";
import { api, clearToken, setToken } from "../api/client";
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
      if (!sessionStorage.getItem("class_agent_token")) {
        this.initialized = true;
        return;
      }
      try {
        this.user = await api.get<User>("/auth/me");
      } catch {
        clearToken();
        this.user = null;
      } finally {
        this.initialized = true;
      }
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
