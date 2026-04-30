<template>
  <main class="auth">
    <section class="auth-card">
      <div class="brand">
        <span><Bot :size="20" /></span>
        <strong>课程学习助手</strong>
      </div>
      <div class="tabs" role="tablist">
        <button class="btn btn-sm" :class="mode === 'login' ? 'btn-primary' : 'btn-ghost'" @click="setMode('login')">登录</button>
        <button class="btn btn-sm" :class="mode === 'register' ? 'btn-primary' : 'btn-ghost'" @click="setMode('register')">注册</button>
        <button class="btn btn-sm" :class="mode === 'reset' ? 'btn-primary' : 'btn-ghost'" @click="setMode('reset')">找回</button>
      </div>
      <p v-if="formError" class="form-error"><AlertCircle :size="15" />{{ formError }}</p>

      <form v-if="mode === 'login'" @submit.prevent="login">
        <label class="label">邮箱</label>
        <input v-model="loginForm.email" class="input" type="email" required />
        <label class="label">密码</label>
        <input v-model="loginForm.password" class="input" type="password" required />
        <button class="btn btn-primary wide" :disabled="loading"><LogIn :size="16" />登录</button>
      </form>

      <form v-else-if="mode === 'register'" @submit.prevent="register">
        <label class="label">邮箱</label>
        <input v-model="registerForm.email" class="input" type="email" required />
        <label class="label">昵称</label>
        <input v-model="registerForm.nickname" class="input" required />
        <div class="form-row">
          <div>
            <label class="label">角色</label>
            <select v-model="registerForm.role" class="select">
              <option value="student">学生</option>
              <option value="teacher">教师</option>
            </select>
          </div>
          <div>
            <label class="label">{{ registerForm.role === 'student' ? '学号' : '工号' }}</label>
            <input v-model="identityNo" class="input" required />
          </div>
        </div>
        <label class="label">密码</label>
        <input v-model="registerForm.password" class="input" type="password" required />
        <button class="btn btn-primary wide" :disabled="loading"><UserPlus :size="16" />注册</button>
      </form>

      <form v-else @submit.prevent="resetPassword">
        <label class="label">邮箱</label>
        <input v-model="resetForm.email" class="input" type="email" required />
        <div class="inline">
          <input v-model="resetForm.code" class="input" placeholder="验证码" />
          <button type="button" class="btn btn-secondary" :disabled="loading" @click="sendCode">发送</button>
        </div>
        <label class="label">新密码</label>
        <input v-model="resetForm.new_password" class="input" type="password" required />
        <button class="btn btn-primary wide" :disabled="loading"><KeyRound :size="16" />重置</button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { AlertCircle, Bot, KeyRound, LogIn, UserPlus } from "lucide-vue-next";
import { api } from "../api/client";
import { useSessionStore } from "../stores/session";
import type { Role, User } from "../types";

const emit = defineEmits<{ authed: [user: User]; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();

const mode = ref<"login" | "register" | "reset">("login");
const loading = ref(false);
const formError = ref("");
const loginForm = reactive({ email: "", password: "" });
const registerForm = reactive({ email: "", password: "", nickname: "", role: "student" as Role });
const identityNo = ref("");
const resetForm = reactive({ email: "", code: "", new_password: "" });
const session = useSessionStore();

function setMode(value: "login" | "register" | "reset") {
  mode.value = value;
  formError.value = "";
}
function fail(text: string) {
  formError.value = text;
  return false;
}
function validatePassword(value: string) {
  return value.length >= 8 || fail("密码至少8位");
}

async function login() {
  formError.value = "";
  if (!validatePassword(loginForm.password)) return;
  loading.value = true;
  try {
    const data = await api.post<{ access_token: string; user: User }>("/auth/login", loginForm);
    session.setSession(data.access_token, data.user);
    emit("authed", data.user);
    emit("notice", "success", "已登录");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function register() {
  formError.value = "";
  if (!registerForm.nickname.trim()) return fail("昵称不能为空");
  if (!identityNo.value.trim()) return fail(registerForm.role === "student" ? "学号不能为空" : "工号不能为空");
  if (!validatePassword(registerForm.password)) return;
  loading.value = true;
  try {
    const payload: Record<string, unknown> = { ...registerForm };
    if (registerForm.role === "student") payload.student_no = identityNo.value;
    else payload.employee_no = identityNo.value;
    await api.post<User>("/auth/register", payload);
    mode.value = "login";
    emit("notice", "success", "已注册");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function sendCode() {
  formError.value = "";
  if (!resetForm.email.trim()) return fail("邮箱不能为空");
  loading.value = true;
  try {
    const data = await api.post<{ debug_code?: string | null }>("/auth/password/reset/request", { email: resetForm.email });
    if (data.debug_code) resetForm.code = data.debug_code;
    emit("notice", "success", "已发送");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function resetPassword() {
  formError.value = "";
  if (!resetForm.code.trim()) return fail("验证码不能为空");
  if (!validatePassword(resetForm.new_password)) return;
  loading.value = true;
  try {
    await api.post("/auth/password/reset/confirm", resetForm);
    mode.value = "login";
    emit("notice", "success", "已重置");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-6);
}
.auth-card {
  width: min(420px, 100%);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: var(--space-8);
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  color: var(--color-text-primary);
  font-size: var(--text-h3);
}
.brand span {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  background: var(--color-ai-gradient);
}
.tabs { display: flex; gap: var(--space-2); margin-bottom: var(--space-6); }
.form-error { display: flex; align-items: center; gap: 6px; min-height: 34px; border: 1px solid var(--color-danger-200); border-radius: var(--radius-md); background: var(--color-danger-50); color: var(--color-danger-700); padding: 0 10px; font-size: var(--text-body-sm); }
.label { margin-top: var(--space-4); }
.wide { width: 100%; margin-top: var(--space-6); }
.inline { display: grid; grid-template-columns: 1fr auto; gap: var(--space-2); margin-top: var(--space-2); }
</style>
