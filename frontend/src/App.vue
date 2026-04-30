<template>
  <AuthView v-if="!user" @authed="setUser" @notice="pushToast" />
  <WorkspaceView v-else :user="user" @logout="logout" @notice="pushToast" />
  <ToastHost :items="toasts" @close="closeToast" />
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, clearToken } from "./api/client";
import ToastHost from "./components/ToastHost.vue";
import AuthView from "./views/AuthView.vue";
import WorkspaceView from "./views/WorkspaceView.vue";
import type { User } from "./types";

const user = ref<User | null>(null);
const toasts = ref<Array<{ id: number; type: "success" | "warning" | "error" | "info"; text: string }>>([]);

function setUser(value: User) {
  user.value = value;
}
function logout() {
  clearToken();
  user.value = null;
  pushToast("info", "已退出");
}
function pushToast(type: "success" | "warning" | "error" | "info", text: string) {
  const id = Date.now() + Math.random();
  toasts.value.push({ id, type, text });
  if (type !== "error") window.setTimeout(() => closeToast(id), 4000);
}
function closeToast(id: number) {
  toasts.value = toasts.value.filter((item) => item.id !== id);
}

onMounted(async () => {
  if (!localStorage.getItem("class_agent_token")) return;
  try {
    user.value = await api.get<User>("/auth/me");
  } catch {
    clearToken();
  }
});
</script>
