<template>
  <main class="auth">
    <section class="auth-card">
      <div class="brand">
        <span><Bot :size="20" /></span>
        <strong>课程学习助手</strong>
      </div>
      <div class="tabs" role="tablist">
        <button type="button" role="tab" class="btn btn-sm" :aria-selected="mode === 'login'" :class="mode === 'login' ? 'btn-primary' : 'btn-ghost'" @click="setMode('login')">登录</button>
        <button type="button" role="tab" class="btn btn-sm" :aria-selected="mode === 'register'" :class="mode === 'register' ? 'btn-primary' : 'btn-ghost'" @click="setMode('register')">注册</button>
        <button type="button" role="tab" class="btn btn-sm" :aria-selected="mode === 'reset'" :class="mode === 'reset' ? 'btn-primary' : 'btn-ghost'" @click="setMode('reset')">找回</button>
      </div>
      <Transition name="fade-slide">
        <p v-if="formError" class="form-error input-error-shake"><AlertCircle :size="15" />{{ formError }}</p>
      </Transition>

      <Transition name="page-switch" mode="out-in">
        <form v-if="mode === 'login'" key="login" @submit.prevent="login">
          <label class="label">邮箱</label>
          <input v-model="loginForm.email" class="input" type="email" required :aria-invalid="formError.includes('邮箱')" />
          <label class="label">密码</label>
          <PasswordField v-model="loginForm.password" required :aria-invalid="formError.includes('密码')" />
          <button class="btn btn-primary wide" :data-loading="loading" :disabled="loading"><LogIn :size="16" />登录</button>
        </form>

        <form v-else-if="mode === 'register'" key="register" @submit.prevent="register">
          <label class="label">邮箱</label>
          <input v-model="registerForm.email" class="input" type="email" required :aria-invalid="formError.includes('邮箱')" />
          <label class="label">昵称</label>
          <input v-model="registerForm.nickname" class="input" required :aria-invalid="formError.includes('昵称')" />
          <label class="label">学号</label>
          <input v-model="studentNo" class="input" required :aria-invalid="formError.includes('学号')" />
          <label class="label">密码</label>
          <PasswordField v-model="registerForm.password" required :aria-invalid="formError.includes('密码')" />
          <button class="btn btn-primary wide" :data-loading="loading" :disabled="loading"><UserPlus :size="16" />注册</button>
        </form>

        <form v-else key="reset" @submit.prevent="resetPassword">
          <label class="label">邮箱</label>
          <input v-model="resetForm.email" class="input" type="email" required :aria-invalid="formError.includes('邮箱')" />
          <div class="inline">
            <input v-model="resetForm.code" class="input" placeholder="验证码" :aria-invalid="formError.includes('验证码')" />
            <button type="button" class="btn btn-secondary" :data-loading="loading" :disabled="loading" @click="sendCode">发送</button>
          </div>
          <label class="label">新密码</label>
          <PasswordField v-model="resetForm.new_password" required :aria-invalid="formError.includes('密码')" />
          <button class="btn btn-primary wide" :data-loading="loading" :disabled="loading"><KeyRound :size="16" />重置</button>
        </form>
      </Transition>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { AlertCircle, Bot, KeyRound, LogIn, UserPlus } from "lucide-vue-next";
import { api } from "../api/client";
import { useSessionStore } from "../stores/session";
import PasswordField from "../components/PasswordField.vue";
import type { User } from "../types";

const emit = defineEmits<{ authed: [user: User]; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();

const mode = ref<"login" | "register" | "reset">("login");
const loading = ref(false);
const formError = ref("");
const loginForm = reactive({ email: "", password: "" });
const registerForm = reactive({ email: "", password: "", nickname: "" });
const studentNo = ref("");
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
  if (!studentNo.value.trim()) return fail("学号不能为空");
  if (!validatePassword(registerForm.password)) return;
  loading.value = true;
  try {
    const payload: Record<string, unknown> = { ...registerForm, role: "student", student_no: studentNo.value };
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
  background:
    radial-gradient(circle at 20% 24%, rgba(0,229,255,.08), transparent 34%),
    radial-gradient(circle at 82% 76%, rgba(217,160,91,.1), transparent 30%),
    var(--ca-color-slate);
  color: var(--ca-color-paper-ink);
}
.auth-card {
  width: min(420px, 100%);
  background: var(--ca-color-paper-card);
  border: 1px solid var(--ca-color-paper-border);
  border-radius: var(--ca-radius-xl);
  box-shadow: var(--ca-shadow-dropdown);
  padding: var(--space-8);
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  color: var(--ca-color-paper-ink);
  font-size: var(--text-h3);
}
.brand span {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  color: var(--ca-color-slate);
  border-radius: var(--ca-radius-md);
  background: var(--ca-role-student-glow);
}
.tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); margin-bottom: var(--space-6); }
.tabs .btn {
  min-height: 44px;
}
.form-error { display: flex; align-items: center; gap: 6px; min-height: 38px; border: 1px solid var(--color-danger-100); border-radius: var(--radius-md); background: var(--color-danger-50); color: var(--color-danger-700); padding: 0 10px; font-size: var(--text-body-sm); }
.label { display: block; margin-top: var(--space-4); color: var(--ca-color-paper-sub); font-weight: 700; }
.wide { width: 100%; margin-top: var(--space-6); }
.inline { display: grid; grid-template-columns: 1fr auto; gap: var(--space-2); margin-top: var(--space-2); }

form {
  display: grid;
}

.input:focus,
:deep(.password-field input:focus) {
  border-color: var(--ca-role-student-primary);
  box-shadow: 0 0 0 3px rgba(0, 184, 212, .18);
}

@media (max-width: 520px) {
  .auth {
    padding: 18px;
  }

  .auth-card {
    padding: 24px;
  }

  .inline {
    grid-template-columns: 1fr;
  }
}
</style>
