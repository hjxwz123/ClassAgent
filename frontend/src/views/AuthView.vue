<template>
  <main class="auth">
    <RouterLink to="/" class="auth-home-link"><ArrowLeft :size="17" />返回首页</RouterLink>
    <div class="auth-formulas" aria-hidden="true">
      <span class="auth-formula formula-force">F = m · a</span>
      <span class="auth-formula formula-integral">∫ f(x) dx = F(x) + C</span>
      <span class="auth-formula formula-limit">lim(x→0) sin x / x = 1</span>
      <span class="auth-formula formula-energy">E = hν = mc²</span>
      <span class="auth-formula formula-gas">pV = nRT</span>
    </div>
    <section class="auth-board">
      <div class="auth-copy">
        <h1>智学黑板</h1>
        <p>欢迎来到你的学习黑板。加入课程、继续课时、向 AI 提问，把每天的学习进度稳稳记录下来。</p>
        <div class="chalk-line"><i></i><span>ClassAgent Learning Console</span></div>
      </div>

      <section class="auth-card">
        <div class="brand">
          <span><BookOpen :size="20" /></span>
          <div>
            <strong>{{ modeTitle }}</strong>
          </div>
        </div>
        <div class="tabs" role="tablist">
          <button type="button" role="tab" :aria-selected="mode === 'login'" :class="{ active: mode === 'login' }" @click="setMode('login')">登录</button>
          <button type="button" role="tab" :aria-selected="mode === 'register'" :class="{ active: mode === 'register' }" @click="setMode('register')">注册</button>
          <button type="button" role="tab" :aria-selected="mode === 'reset'" :class="{ active: mode === 'reset' }" @click="setMode('reset')">找回</button>
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
            <button class="auth-submit" :data-loading="loading" :disabled="loading"><LogIn :size="17" />{{ loading ? '正在进入...' : '登录' }}</button>
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
            <button class="auth-submit" :data-loading="loading" :disabled="loading"><UserPlus :size="17" />注册学生账号</button>
          </form>

          <form v-else key="reset" @submit.prevent="resetPassword">
            <label class="label">邮箱</label>
            <input v-model="resetForm.email" class="input" type="email" required :aria-invalid="formError.includes('邮箱')" />
            <label class="label">验证码</label>
            <div class="inline">
              <input v-model="resetForm.code" class="input" placeholder="输入验证码" :aria-invalid="formError.includes('验证码')" />
              <button type="button" class="send-code-btn" :data-loading="loading" :disabled="loading" @click="sendCode">发送</button>
            </div>
            <label class="label">新密码</label>
            <PasswordField v-model="resetForm.new_password" required :aria-invalid="formError.includes('密码')" />
            <button class="auth-submit" :data-loading="loading" :disabled="loading"><KeyRound :size="17" />重置密码</button>
          </form>
        </Transition>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { AlertCircle, ArrowLeft, BookOpen, KeyRound, LogIn, UserPlus } from "../icons";
import { api } from "../api/client";
import { defaultRouteForRole } from "../router";
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
const router = useRouter();
const modeTitle = computed(() => (mode.value === "login" ? "欢迎回来" : mode.value === "register" ? "加入学习空间" : "找回密码"));

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

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
    emit("notice", "success", "已登录，正在进入工作台");
    await delay(1000);
    await router.replace(defaultRouteForRole(data.user.role));
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
@font-face {
  font-family: "ClassAgent Chalk";
  src: url("../assets/fonts/home/classagent-chalk.woff") format("woff");
  font-style: normal;
  font-weight: 400;
  font-display: block;
}

@font-face {
  font-family: "ClassAgent Serif";
  src: url("../assets/fonts/home/classagent-serif.woff") format("woff");
  font-style: normal;
  font-weight: 100 900;
  font-display: block;
}

@font-face {
  font-family: "ClassAgent Sans";
  src: url("../assets/fonts/home/classagent-sans.woff") format("woff");
  font-style: normal;
  font-weight: 100 900;
  font-display: block;
}

@font-face {
  font-family: "ClassAgent Mono";
  src: url("../assets/fonts/home/classagent-mono.woff") format("woff");
  font-style: normal;
  font-weight: 100 900;
  font-display: block;
}

.auth {
  --ca-font-chalk: "ClassAgent Chalk", "ClassAgent Serif", "ClassAgent Sans",
    "Hannotate SC", "HanziPen SC", "Wawati SC", "STXingkai",
    "华文行楷", "PingFang SC", sans-serif;
  --ca-font-serif: "ClassAgent Serif", "Songti SC", "STSong", "SimSun", "宋体", serif;
  --ca-font-sans: "ClassAgent Sans", -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Microsoft YaHei", "Helvetica Neue", sans-serif;
  --ca-font-mono: "ClassAgent Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo,
    monospace;
  --shared-title-left: max(24px, calc((100vw - 1040px) / 2));
  --shared-title-top: clamp(190px, calc(50vh - 190px), 290px);
  --home-logo-left: max(24px, calc((100vw - 1280px) / 2 + 24px));
  --home-logo-top: 16px;
  --title-to-logo-x: calc(var(--home-logo-left) - var(--shared-title-left));
  --title-to-logo-y: calc(var(--home-logo-top) - var(--shared-title-top));

  min-height: 100vh;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 56px 24px;
  background:
    radial-gradient(circle at 16% 18%, rgba(0, 229, 255, .12), transparent 28%),
    radial-gradient(circle at 84% 78%, rgba(217, 160, 91, .14), transparent 32%),
    var(--ca-color-slate);
  color: var(--ca-color-chalk);
}
.auth::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
  background-size: 48px 48px;
  opacity: .35;
}
.auth-formulas {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.auth-formula {
  --o: .055;
  --r: -4deg;
  position: absolute;
  display: block;
  color: rgba(244,244,240,var(--o));
  font-family: var(--ca-font-chalk);
  line-height: 1;
  text-shadow: 0 0 1px rgba(244,244,240,.12);
  transform: rotate(var(--r));
  white-space: nowrap;
}
.formula-force {
  top: 18%;
  left: 5%;
  --o: .042;
  --r: -5deg;
  font-size: clamp(24px, 4vw, 48px);
}
.formula-integral {
  right: 6%;
  bottom: 9%;
  --o: .052;
  --r: -4deg;
  font-size: clamp(24px, 4vw, 48px);
}
.formula-limit {
  top: 12%;
  right: 12%;
  --o: .038;
  --r: 3deg;
  font-size: clamp(18px, 2.4vw, 30px);
}
.formula-energy {
  top: 66%;
  left: 4%;
  --o: .04;
  --r: 5deg;
  font-size: clamp(18px, 2.6vw, 32px);
}
.formula-gas {
  top: 46%;
  right: 30%;
  --o: .036;
  --r: -2deg;
  font-size: clamp(17px, 2.2vw, 28px);
}
.auth-home-link {
  position: fixed;
  top: 24px;
  left: 28px;
  z-index: 2;
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255,255,255,.14);
  border-radius: var(--ca-radius-full);
  background: rgba(255,255,255,.08);
  color: var(--ca-color-chalk);
  padding: 0 14px;
  text-decoration: none;
  backdrop-filter: blur(10px);
}
.auth-home-link:hover {
  border-color: rgba(255,255,255,.28);
  background: rgba(255,255,255,.12);
}
.auth-board {
  position: relative;
  z-index: 1;
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  align-items: center;
  gap: 48px;
}
.auth-copy {
  position: fixed;
  top: var(--shared-title-top);
  left: var(--shared-title-left);
  z-index: 1;
  width: min(560px, calc(100vw - var(--shared-title-left) - 520px));
  min-width: 0;
}
.auth-copy h1 {
  margin: 0 0 18px;
  color: var(--ca-color-chalk);
  font-family: var(--ca-font-chalk);
  font-size: clamp(64px, 10vw, 128px);
  font-weight: 500;
  letter-spacing: 0;
  line-height: .9;
  text-shadow: 0 0 16px rgba(244,244,240,.2);
}
.auth-copy p {
  max-width: 560px;
  margin: 0;
  color: rgba(244,244,240,.78);
  font-size: 18px;
  line-height: 1.9;
}
.chalk-line {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 34px;
  color: rgba(244,244,240,.52);
  font-family: var(--ca-font-mono);
  font-size: 12px;
}
.chalk-line i {
  width: 130px;
  height: 2px;
  border-radius: 2px;
  background: rgba(244,244,240,.48);
}
.auth-card {
  grid-column: 2;
  justify-self: end;
  width: min(420px, 100%);
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,244,232,.94)),
    var(--ca-color-paper-card);
  box-shadow: 0 30px 80px rgba(0,0,0,.36);
  padding: 28px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
  color: var(--ca-color-paper-ink);
}
.brand span {
  display: inline-flex;
  width: 42px;
  height: 42px;
  align-items: center;
  justify-content: center;
  color: var(--ca-color-chalk);
  border-radius: 8px;
  background: var(--ca-color-slate);
}
.brand div {
  display: grid;
  gap: 3px;
}
.brand strong {
  color: var(--ca-color-paper-ink);
  font-family: var(--ca-font-chalk);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0;
}
.brand small {
  color: var(--ca-color-paper-sub);
  font-size: 13px;
}
.tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 18px;
  border: 1px solid var(--ca-color-paper-border);
  border-radius: 8px;
  background: #EEE6D2;
  padding: 4px;
}
.tabs button {
  min-height: 38px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ca-color-paper-sub);
  font-weight: 800;
}
.tabs button.active {
  background: var(--ca-color-slate);
  color: var(--ca-color-chalk);
  box-shadow: 0 4px 12px rgba(0,0,0,.16);
}
.form-error { display: flex; align-items: center; gap: 6px; min-height: 38px; border: 1px solid var(--color-danger-100); border-radius: 8px; background: var(--color-danger-50); color: var(--color-danger-700); padding: 0 10px; font-size: var(--text-body-sm); }
.label { display: block; margin-top: 16px; color: var(--ca-color-paper-sub); font-size: 13px; font-weight: 800; }
.inline { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 8px; }

form {
  display: grid;
}
.input {
  height: 44px;
  border: 1px solid var(--ca-color-paper-border);
  border-radius: 8px;
  background: rgba(255,255,255,.9);
  color: var(--ca-color-paper-ink);
  padding: 0 12px;
}

.input:focus {
  outline: none;
  border-color: var(--ca-color-slate);
  box-shadow: 0 0 0 3px rgba(18,22,20,.14);
}
:deep(.password-field) {
  min-height: 44px;
  border-color: var(--ca-color-paper-border);
  border-radius: 8px;
  background: rgba(255,255,255,.9);
  color: var(--ca-color-paper-ink);
}
:deep(.password-field:hover) {
  border-color: var(--ca-color-paper-border-strong);
}
:deep(.password-field:focus-within) {
  border-color: var(--ca-color-slate);
  box-shadow: 0 0 0 3px rgba(18,22,20,.14);
}
:deep(.password-field.invalid) {
  border-color: var(--color-danger-500);
  box-shadow: var(--shadow-focus-danger);
}
:deep(.password-field input) {
  border: 0;
  background: transparent;
  color: var(--ca-color-paper-ink);
  box-shadow: none;
}
:deep(.password-field input:focus),
:deep(.password-field input:focus-visible) {
  outline: 0;
  border: 0;
  box-shadow: none;
}
:deep(.password-tool) {
  color: var(--ca-color-paper-muted);
}
:deep(.password-tool:hover) {
  background: rgba(18,22,20,.08);
  color: var(--ca-color-paper-ink);
}
.auth-submit,
.send-code-btn {
  display: inline-flex;
  min-height: 46px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 8px;
  background: var(--ca-color-slate);
  color: var(--ca-color-chalk);
  padding: 0 16px;
  font-weight: 900;
}
.auth-submit {
  width: 100%;
  margin-top: 24px;
}
.auth-submit:hover,
.send-code-btn:hover {
  background: #222925;
}
.auth-submit:disabled,
.send-code-btn:disabled {
  opacity: .72;
  cursor: wait;
}

@media (max-width: 860px) {
  .auth-copy {
    position: relative;
    top: auto;
    left: auto;
    width: auto;
  }
  .auth-board {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .auth-card {
    grid-column: auto;
    justify-self: stretch;
  }
  .auth-copy h1 {
    font-size: 64px;
  }
}

@media (max-width: 520px) {
  .auth { padding: 78px 18px 24px; }
  .auth-card {
    padding: 24px;
  }
  .inline {
    grid-template-columns: 1fr;
  }
  .auth-copy p {
    font-size: 15px;
  }
  .auth-home-link {
    left: 18px;
    top: 18px;
  }
}

/* ====== 页面进入：黑板底色常驻，标题从左上承接，登录卡右侧滑入 ====== */
.auth.route-home-auth-enter-active {
  transition: opacity 980ms linear;
}
.auth.route-home-auth-enter-from {
  opacity: .999;
  filter: none;
  transform: none;
}
.auth.route-home-auth-enter-active .auth-home-link {
  animation: auth-link-in 620ms cubic-bezier(.22, .61, .36, 1) 260ms both;
}
.auth.route-home-auth-enter-active .auth-formula {
  animation: auth-formula-in 820ms cubic-bezier(.22, .61, .36, 1) both;
}
.auth.route-home-auth-enter-active .formula-force {
  animation-delay: 60ms;
}
.auth.route-home-auth-enter-active .formula-integral {
  animation-delay: 120ms;
}
.auth.route-home-auth-enter-active .formula-limit {
  animation-delay: 180ms;
}
.auth.route-home-auth-enter-active .formula-energy {
  animation-delay: 220ms;
}
.auth.route-home-auth-enter-active .formula-gas {
  animation-delay: 260ms;
}
.auth.route-home-auth-enter-active .auth-copy h1 {
  transform-origin: left top;
  animation: auth-h1-takeover 980ms linear both;
}
.auth.route-home-auth-enter-active .auth-copy p {
  animation: auth-copy-in 900ms cubic-bezier(.22, .61, .36, 1) 220ms both;
}
.auth.route-home-auth-enter-active .chalk-line {
  animation: auth-copy-in 900ms cubic-bezier(.22, .61, .36, 1) 300ms both;
}
.auth.route-home-auth-enter-active .auth-card {
  animation: auth-card-in 960ms cubic-bezier(.22, .61, .36, 1) 200ms both;
}
.auth.route-auth-home-leave-active {
  transition: opacity 980ms linear;
}
.auth.route-auth-home-leave-active .auth-home-link {
  animation: auth-link-out 620ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-formula {
  animation: auth-formula-out 760ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-copy h1 {
  transform-origin: left top;
  animation: auth-h1-to-home-logo 940ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-copy p,
.auth.route-auth-home-leave-active .chalk-line {
  animation: auth-copy-out 760ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-card {
  animation: auth-card-out 900ms cubic-bezier(.55, .06, .68, .19) both;
}

@keyframes auth-link-in {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes auth-link-out {
  to { opacity: 0; transform: translateY(-10px); }
}
@keyframes auth-formula-in {
  from { opacity: 0; transform: rotate(var(--r)); }
  to { opacity: 1; transform: translateX(0) rotate(var(--r)); }
}
@keyframes auth-formula-out {
  to { opacity: 0; transform: rotate(var(--r)); }
}
@keyframes auth-h1-takeover {
  0%,
  96% { opacity: 0; transform: translate3d(0, 0, 0); }
  100% { opacity: 1; transform: translate3d(0, 0, 0); }
}
@keyframes auth-h1-to-home-logo {
  0% { opacity: 1; transform: translate3d(0, 0, 0); font-size: clamp(64px, 10vw, 128px); }
  78% { opacity: 1; transform: translate3d(var(--title-to-logo-x), var(--title-to-logo-y), 0); font-size: 20px; }
  100% { opacity: 1; transform: translate3d(var(--title-to-logo-x), var(--title-to-logo-y), 0); font-size: 20px; }
}
@keyframes auth-copy-in {
  from { opacity: 0; transform: translateX(-26px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes auth-copy-out {
  to { opacity: 0; transform: translateX(-26px); }
}
@keyframes auth-card-in {
  from {
    opacity: 0;
    transform: translate3d(min(32vw, 360px), 0, 0);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0);
  }
  60% {
    opacity: 1;
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
    box-shadow: 0 30px 80px rgba(0, 0, 0, .36);
  }
}
@keyframes auth-card-out {
  from {
    opacity: 1;
    transform: translate3d(0, 0, 0);
    box-shadow: 0 30px 80px rgba(0, 0, 0, .36);
  }
  to {
    opacity: 0;
    transform: translate3d(min(32vw, 360px), 0, 0);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0);
  }
}
</style>
