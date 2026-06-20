<template>
  <PageLoader v-if="loginRedirecting" />
  <main v-else class="auth" :class="[authThemeClass, { 'auth-link-invalid': linkValidationStatus === 'invalid', 'entered-from-home': enteredFromHome }]">
    <div class="auth-toolbar">
      <RouterLink to="/" class="auth-home-link"><ArrowLeft :size="17" />返回首页</RouterLink>
      <ThemeToggle class="auth-theme-toggle" />
    </div>
    <div class="auth-accent" aria-hidden="true"></div>
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
        <div class="auth-card-edge" aria-hidden="true"></div>
        <div class="auth-card-body">
          <template v-if="linkValidationStatus === 'invalid'">
            <div class="link-result link-result--error">
              <AlertCircle :size="22" />
              <strong>{{ invalidLinkMessage }}</strong>
            </div>
          </template>
          <template v-else>
            <div class="brand">
              <span><BookOpen :size="20" /></span>
              <div>
                <strong>{{ modeTitle }}</strong>
              </div>
            </div>
            <div v-if="linkValidationStatus === 'checking'" class="link-result">
              <strong>正在验证链接...</strong>
            </div>
            <template v-else>
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
                  <label class="label" for="login-email">邮箱</label>
                  <input id="login-email" v-model="loginForm.email" class="input" type="email" autocomplete="username" required :aria-invalid="formError.includes('邮箱')" />
                  <label class="label" for="login-password">密码</label>
                  <PasswordField id="login-password" v-model="loginForm.password" autocomplete="current-password" required :aria-invalid="formError.includes('密码')" />
                  <button class="auth-submit" :data-loading="loading" :disabled="loading"><LogIn :size="17" />{{ loading ? '正在进入...' : '登录' }}</button>
                </form>

                <form v-else-if="mode === 'register'" key="register" @submit.prevent="registerForm.token ? register() : sendRegistrationLink()">
                  <label class="label" for="register-email">邮箱</label>
                  <input id="register-email" v-model="registerForm.email" class="input" type="email" autocomplete="username" required :readonly="Boolean(registerForm.token)" :aria-invalid="formError.includes('邮箱')" />
                  <template v-if="registerForm.token">
                    <label class="label" for="register-nickname">昵称</label>
                    <input id="register-nickname" v-model="registerForm.nickname" class="input" autocomplete="nickname" required :aria-invalid="formError.includes('昵称')" />
                    <label class="label" for="register-student-no">学号</label>
                    <input id="register-student-no" v-model="studentNo" class="input" autocomplete="off" required :aria-invalid="formError.includes('学号')" />
                    <label class="label" for="register-password">密码</label>
                    <PasswordField id="register-password" v-model="registerForm.password" autocomplete="new-password" required :aria-invalid="formError.includes('密码')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><UserPlus :size="17" />注册学生账号</button>
                  </template>
                  <button v-else class="auth-submit" :data-loading="loading" :disabled="loading"><UserPlus :size="17" />发送注册链接</button>
                </form>

                <form v-else key="reset" @submit.prevent="resetForm.token ? resetPassword() : sendResetLink()">
                  <label class="label" for="reset-email">邮箱</label>
                  <input id="reset-email" v-model="resetForm.email" class="input" type="email" autocomplete="username" required :readonly="Boolean(resetForm.token)" :aria-invalid="formError.includes('邮箱')" />
                  <template v-if="resetForm.token">
                    <label class="label" for="reset-new-password">新密码</label>
                    <PasswordField id="reset-new-password" v-model="resetForm.new_password" autocomplete="new-password" required :aria-invalid="formError.includes('密码')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><KeyRound :size="17" />重置密码</button>
                  </template>
                  <button v-else class="auth-submit" :data-loading="loading" :disabled="loading"><KeyRound :size="17" />发送找回链接</button>
                </form>
              </Transition>
            </template>
          </template>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { NavigationFailureType, isNavigationFailure, useRoute, useRouter } from "vue-router";
import type { NavigationFailure } from "vue-router";
import { AlertCircle, ArrowLeft, BookOpen, KeyRound, LogIn, UserPlus } from "../icons";
import { api } from "../api/client";
import { defaultRouteForRole } from "../router";
import { useSessionStore } from "../stores/session";
import PageLoader from "../components/PageLoader.vue";
import PasswordField from "../components/PasswordField.vue";
import ThemeToggle from "../components/ThemeToggle.vue";
import { readStoredTheme, subscribeAppTheme, type AppTheme } from "../theme";
import type { User } from "../types";

const emit = defineEmits<{ authed: [user: User]; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();

const mode = ref<"login" | "register" | "reset">("login");
const loading = ref(false);
const enteredFromHome = ref(false);
const loginRedirecting = ref(false);
const formError = ref("");
const authTheme = ref<AppTheme>(readStoredTheme());
const loginForm = reactive({ email: "", password: "" });
const registerForm = reactive({ email: "", token: "", password: "", nickname: "" });
const studentNo = ref("");
const resetForm = reactive({ email: "", token: "", new_password: "" });
const session = useSessionStore();
const route = useRoute();
const router = useRouter();
const loginFailedMessage = "登录失败，请检查用户名或者密码";
const invalidLinkMessage = "链接无效或已过期";
const linkValidationStatus = ref<"idle" | "checking" | "valid" | "invalid">("idle");
const modeTitle = computed(() => {
  if (mode.value === "register") return registerForm.token ? "完成注册" : "邮件注册";
  if (mode.value === "reset") return resetForm.token ? "设置新密码" : "找回密码";
  return "欢迎回来";
});
const authThemeClass = computed(() => `auth-${authTheme.value}`);
let unsubscribeTheme: (() => void) | null = null;
let linkValidationRun = 0;

watch(() => route.query, applyAuthQuery, { immediate: true });

onMounted(() => {
  // 经由首页转场进入时打上持久标记：转场类移除后由它禁止直载入场动画重播（视觉用途）
  enteredFromHome.value = Boolean(document.querySelector(".auth.route-home-auth-enter-active"));
  unsubscribeTheme = subscribeAppTheme((theme) => {
    authTheme.value = theme;
  });
});

onBeforeUnmount(() => {
  unsubscribeTheme?.();
});

function setMode(value: "login" | "register" | "reset") {
  mode.value = value;
  formError.value = "";
  registerForm.token = "";
  resetForm.token = "";
  resetLinkValidation();
}

function queryString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function resetLinkValidation() {
  linkValidationRun += 1;
  linkValidationStatus.value = "idle";
}

function applyAuthQuery() {
  const queryMode = queryString(route.query.mode);
  const email = queryString(route.query.email);
  const token = queryString(route.query.token);
  formError.value = "";
  if (queryMode === "login" || queryMode === "register" || queryMode === "reset") {
    mode.value = queryMode;
  }
  if (queryMode === "register") {
    registerForm.email = email || registerForm.email;
    registerForm.token = token;
    resetForm.token = "";
    if (token) void validateLinkedToken("register", email, token);
    else resetLinkValidation();
    return;
  }
  if (queryMode === "reset") {
    resetForm.email = email || resetForm.email;
    resetForm.token = token;
    registerForm.token = "";
    if (token) void validateLinkedToken("reset", email, token);
    else resetLinkValidation();
    return;
  }
  resetLinkValidation();
}

function fail(text: string) {
  formError.value = text;
  return false;
}
function validatePassword(value: string) {
  return value.length >= 8 || fail("密码至少8位");
}

async function validateLinkedToken(modeValue: "register" | "reset", email: string, token: string) {
  const run = ++linkValidationRun;
  linkValidationStatus.value = "checking";
  try {
    if (!email || !token) throw new Error(invalidLinkMessage);
    await api.post("/auth/link/validate", { mode: modeValue, email, token });
    if (run === linkValidationRun) linkValidationStatus.value = "valid";
  } catch {
    if (run === linkValidationRun) {
      formError.value = "";
      linkValidationStatus.value = "invalid";
    }
  }
}

function isStuckNavigationFailure(failure: void | NavigationFailure) {
  // 守卫返回 false / next(false)（aborted）或被更晚的导航打断（cancelled）时不会抛错，
  // 而是 resolve 出 NavigationFailure，PageLoader 会卡死。守卫重定向会正常 resolve 到目标路由
  // （不返回 failure），duplicated 表示已在目标路由——两者都不算卡死
  return isNavigationFailure(failure, NavigationFailureType.aborted | NavigationFailureType.cancelled);
}

function recoverFromStuckRedirect() {
  // 复位到可重试状态并提示，避免整屏卡在 PageLoader 需手动刷新
  loginRedirecting.value = false;
  formError.value = "登录已完成，但页面跳转失败，请重试或刷新页面";
  emit("notice", "warning", "登录已完成，但页面跳转失败，请重试或刷新页面");
}

async function login() {
  formError.value = "";
  if (!validatePassword(loginForm.password)) return;
  loading.value = true;
  loginRedirecting.value = true;
  // 兜底：若 N 秒内导航仍未完成（守卫挂起/静默失败），复位 loading，避免整屏卡死需手动刷新
  const redirectTimeout = window.setTimeout(() => {
    if (loginRedirecting.value) recoverFromStuckRedirect();
  }, 8000);
  try {
    const data = await api.post<{ access_token: string; user: User }>("/auth/login", loginForm);
    session.setSession(data.access_token, data.user);
    emit("authed", data.user);
    // vue-router 在导航被取消/重定向时不抛错而是 resolve 出 NavigationFailure，需显式判断
    const failure = await router.replace(defaultRouteForRole(data.user.role));
    if (isStuckNavigationFailure(failure)) {
      recoverFromStuckRedirect();
    }
  } catch (error) {
    loginRedirecting.value = false;
    formError.value = loginFailedMessage;
    emit("notice", "error", loginFailedMessage);
  } finally {
    window.clearTimeout(redirectTimeout);
    loading.value = false;
  }
}

async function sendRegistrationLink() {
  formError.value = "";
  if (!registerForm.email.trim()) return fail("邮箱不能为空");
  loading.value = true;
  try {
    await api.post("/auth/register/request", { email: registerForm.email });
    emit("notice", "success", "注册链接已发送，请查收邮箱；找不到请查看垃圾邮件或垃圾箱");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function register() {
  formError.value = "";
  if (!registerForm.token || linkValidationStatus.value !== "valid") {
    linkValidationStatus.value = "invalid";
    return;
  }
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

async function sendResetLink() {
  formError.value = "";
  if (!resetForm.email.trim()) return fail("邮箱不能为空");
  loading.value = true;
  try {
    await api.post("/auth/password/reset/request", { email: resetForm.email });
    emit("notice", "success", "找回链接已发送，请查收邮箱；找不到请查看垃圾邮件或垃圾箱");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

async function resetPassword() {
  formError.value = "";
  if (!resetForm.token || linkValidationStatus.value !== "valid") {
    linkValidationStatus.value = "invalid";
    return;
  }
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
  --ca-font-chalk: "ClassAgent Chalk", "ClassAgent Sans", sans-serif;
  --ca-font-serif: "ClassAgent Serif", serif;
  --ca-font-sans: "ClassAgent Sans", -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Microsoft YaHei", "Helvetica Neue", sans-serif;
  --ca-font-mono: "ClassAgent Mono", "SFMono-Regular", Consolas, "Liberation Mono", Menlo,
    monospace;
  --shared-title-left: max(24px, calc((100vw - 1040px) / 2));
  --shared-title-top: clamp(190px, calc(50vh - 190px), 290px);
  --shared-title-size: clamp(64px, 10vw, 128px);
  --home-logo-left: max(24px, calc((100vw - 1280px) / 2 + 24px));
  /* 首页品牌字静止时的真实视口坐标（nav 上内边距 12px + (44 − 18)/2 = 25px）。
     与 ProductHomeView.vue 同名变量保持同步 */
  --home-logo-text-top: 25px;
  --home-logo-text-offset: 68px;
  --brand-flight-glow: 0 0 2px rgba(244, 244, 240, 0.7), 0 0 18px rgba(244, 244, 240, 0.18);
  --title-to-logo-x: calc(var(--home-logo-left) + var(--home-logo-text-offset) - var(--shared-title-left));
  --title-to-logo-y: calc(var(--home-logo-text-top) - var(--shared-title-top));

  min-height: 100vh;
  position: relative;
  isolation: isolate;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 56px 24px;
  /* 底色与噪点纹理同 ProductHomeView 的黑板逐像素一致，转场穿透/揭幕才无缝；
     青/铜辉光移入 .auth-accent 单独淡入，不参与底色交接 */
  background: radial-gradient(ellipse 100% 80% at 50% 38%, #1B211D 0%, #121614 56%, #0A0D0B 100%);
  background-attachment: fixed;
  color: var(--ca-color-chalk);
}
/* 与 ProductHomeView .board-texture 完全同款（同 SVG、同混合、同透明度、拉伸非平铺） */
.auth::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)" opacity="0.12"/%3E%3C/svg%3E'),
    url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="grain"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.4" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23grain)" opacity="0.08"/%3E%3C/svg%3E');
  background-blend-mode: overlay, soft-light;
  mix-blend-mode: overlay;
  opacity: 0.85;
}
/* 与 ProductHomeView .board-smudge 完全同款（擦拭高光/粉笔灰痕/暗角/擦痕条纹） */
.auth::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 70% 50% at 50% 45%, rgba(220, 230, 215, 0.06) 0%, transparent 60%),
    radial-gradient(ellipse 30% 25% at 22% 28%, rgba(244, 244, 240, 0.05) 0%, transparent 65%),
    radial-gradient(ellipse 35% 30% at 78% 72%, rgba(244, 244, 240, 0.04) 0%, transparent 60%),
    radial-gradient(ellipse 120% 100% at 50% 50%, transparent 55%, rgba(0, 0, 0, 0.22) 100%),
    repeating-linear-gradient(90deg, rgba(244, 244, 240, 0.012) 0px, rgba(244, 244, 240, 0.012) 1px, transparent 1px, transparent 3px),
    repeating-linear-gradient(88deg, transparent 0px, transparent 60px, rgba(244, 244, 240, 0.018) 60px, rgba(244, 244, 240, 0.018) 62px, transparent 62px, transparent 140px);
}
/* 登录页专属的青/铜环境光：垫在纹理之下，入场时单独淡入 */
.auth-accent {
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(circle at 16% 18%, rgba(0, 229, 255, .1), transparent 30%),
    radial-gradient(circle at 84% 78%, rgba(217, 160, 91, .1), transparent 32%);
  animation: auth-formula-mount 1100ms ease-out 120ms both;
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
  animation: auth-formula-mount 1100ms ease-out both;
}
.formula-force { animation-delay: 160ms; }
.formula-integral { animation-delay: 280ms; }
.formula-limit { animation-delay: 400ms; }
.formula-energy { animation-delay: 520ms; }
.formula-gas { animation-delay: 640ms; }
@keyframes auth-formula-mount {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes auth-rise {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes auth-card-pop {
  from { opacity: 0; transform: translateY(20px) scale(.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
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
  color: rgba(0, 229, 255, calc(var(--o) * 1.7));
  text-shadow: 0 0 10px rgba(0, 229, 255, .1);
}
.formula-gas {
  top: 46%;
  right: 30%;
  --o: .036;
  --r: -2deg;
  font-size: clamp(17px, 2.2vw, 28px);
}
.auth-toolbar {
  position: fixed;
  top: 24px;
  left: 28px;
  right: 28px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none;
}
.auth-home-link {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(244,244,240,.14);
  border-radius: var(--ca-radius-full);
  background: rgba(244,244,240,.08);
  color: var(--ca-color-chalk);
  padding: 0 16px;
  font-size: 13px;
  text-decoration: none;
  backdrop-filter: blur(10px);
  pointer-events: auto;
  transition: border-color 200ms var(--ease-out), background-color 200ms var(--ease-out),
    transform 200ms var(--ease-out);
}
.auth-home-link:hover {
  border-color: rgba(244,244,240,.3);
  background: rgba(244,244,240,.13);
  transform: translateY(-1px);
}
.auth-home-link:active {
  transform: translateY(0) scale(.97);
}
.auth-theme-toggle {
  color: var(--ca-color-chalk);
  pointer-events: auto;
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
.auth-link-invalid .auth-toolbar,
.auth-link-invalid .auth-formulas,
.auth-link-invalid .auth-copy {
  display: none;
}
.auth-link-invalid .auth-board {
  width: min(420px, 100%);
  grid-template-columns: 1fr;
}
.auth-link-invalid .auth-card {
  grid-column: auto;
  justify-self: stretch;
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
  margin: 0 0 20px;
  color: var(--ca-color-chalk);
  font-family: var(--ca-font-chalk);
  font-size: var(--shared-title-size);
  font-weight: 500;
  font-synthesis: none;
  letter-spacing: 0;
  line-height: .9;
  text-shadow: 0 0 2px rgba(244,244,240,.7), 0 0 18px rgba(244,244,240,.18);
  animation: auth-rise 640ms var(--ease-out) both;
}
.auth-copy p {
  max-width: 30em;
  margin: 0;
  color: rgba(244,244,240,.82);
  font-size: 17px;
  line-height: 1.9;
  letter-spacing: 0.02em;
  animation: auth-rise 640ms var(--ease-out) 90ms both;
}
.chalk-line {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 36px;
  color: rgba(244,244,240,.55);
  font-family: var(--ca-font-mono);
  font-size: 12px;
  letter-spacing: .08em;
  animation: auth-rise 640ms var(--ease-out) 170ms both;
}
.chalk-line i {
  width: 120px;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, rgba(0,229,255,.75), rgba(244,244,240,.4) 55%, rgba(244,244,240,.06));
  box-shadow: 0 0 8px rgba(0,229,255,.25);
}
.auth-card {
  grid-column: 2;
  justify-self: end;
  width: 420px;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1px solid rgba(244,244,240,.22);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.97), rgba(248,244,232,.95)),
    var(--ca-color-paper-card);
  box-shadow:
    0 30px 80px rgba(0,0,0,.4),
    0 8px 24px rgba(0,0,0,.24),
    inset 0 1px 0 rgba(255,255,255,.6);
  padding: 0;
  overflow: hidden;
  animation: auth-card-pop 680ms var(--ease-out) 120ms both;
}
.auth-card-edge {
  position: relative;
  height: 10px;
  background: linear-gradient(90deg, #121614, #1d231f 50%, #121614);
}
.auth-card-edge::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 4%, rgba(0,229,255,.65) 32%, rgba(0,229,255,.65) 68%, transparent 96%);
  box-shadow: 0 0 12px rgba(0,229,255,.4);
}
.auth-card-body {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 32px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
  color: var(--ca-color-paper-ink);
}
.brand span {
  display: inline-flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  color: #00E5FF;
  border-radius: 10px;
  background: var(--ca-color-slate);
  box-shadow: 0 4px 10px rgba(18,22,20,.24), 0 0 14px rgba(0,229,255,.16);
}
.brand div {
  display: grid;
  gap: 3px;
}
.brand strong {
  color: var(--ca-color-paper-ink);
  font-family: var(--ca-font-serif);
  font-size: 23px;
  font-weight: 800;
  font-synthesis: none;
  letter-spacing: -0.01em;
  line-height: 1.18;
}
.brand small {
  color: var(--ca-color-paper-sub);
  font-size: 13px;
}
.tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin-bottom: 20px;
  border: 1px solid var(--ca-color-paper-border);
  border-radius: 8px;
  background: #F4F1EA;
  padding: 4px;
}
.tabs button {
  min-height: 38px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ca-color-paper-sub);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .04em;
  cursor: pointer;
  transition: color 180ms var(--ease-out), background-color 180ms var(--ease-out),
    box-shadow 180ms var(--ease-out);
}
.tabs button:hover:not(.active) {
  color: var(--ca-color-paper-ink);
}
.tabs button.active {
  background: var(--ca-color-slate);
  color: var(--ca-color-chalk);
  box-shadow: 0 4px 12px rgba(18,22,20,.2);
}
.form-error {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  border: 1px solid var(--color-danger-100);
  border-left: 3px solid var(--color-danger-500);
  border-radius: 6px;
  background: var(--color-danger-50);
  color: var(--color-danger-700);
  padding: 8px 12px;
  font-size: var(--text-body-sm);
  line-height: 1.5;
}
.form-error svg {
  flex: 0 0 auto;
}
.link-result {
  display: grid;
  min-height: 168px;
  place-items: center;
  gap: 12px;
  color: var(--ca-color-paper-sub);
  text-align: center;
}
.link-result strong {
  color: var(--ca-color-paper-ink);
  font-size: 17px;
  line-height: 1.45;
}
.link-result--error {
  color: var(--color-danger-600);
}
.link-result--error strong {
  color: var(--color-danger-700);
}
.label {
  display: block;
  margin-top: 18px;
  color: var(--ca-color-paper-sub);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .06em;
}
.inline { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 8px; }
.inline .input {
  margin-top: 0;
}

form {
  display: grid;
  min-width: 0;
  width: 100%;
  max-width: 100%;
}
.input {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: 44px;
  margin-top: 8px;
  box-sizing: border-box;
  border: 1px solid var(--ca-color-paper-border);
  border-radius: 6px;
  background: rgba(255,255,255,.92);
  color: var(--ca-color-paper-ink);
  padding: 0 12px;
  font-size: 14px;
  -webkit-appearance: none;
  appearance: none;
  transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out),
    background-color 160ms var(--ease-out);
}
.input:hover {
  border-color: var(--ca-color-paper-border-strong);
}
.input:focus {
  outline: none;
  border-color: #00B8D4;
  box-shadow: 0 0 0 3px rgba(0,184,212,.16), 0 0 14px rgba(0,229,255,.12);
}
.input[aria-invalid="true"] {
  border-color: var(--color-danger-500);
}
.input[aria-invalid="true"]:focus {
  box-shadow: var(--shadow-focus-danger);
}
.input[readonly] {
  color: var(--ca-color-paper-sub);
  background: rgba(244,241,234,.85);
}
:deep(.password-field) {
  margin-top: 8px;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 44px;
  border-color: var(--ca-color-paper-border);
  border-radius: 6px;
  background: rgba(255,255,255,.92);
  color: var(--ca-color-paper-ink);
  transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
}
:deep(.password-field:hover) {
  border-color: var(--ca-color-paper-border-strong);
}
:deep(.password-field:focus-within) {
  border-color: #00B8D4;
  box-shadow: 0 0 0 3px rgba(0,184,212,.16), 0 0 14px rgba(0,229,255,.12);
}
:deep(.password-field.invalid) {
  border-color: var(--color-danger-500);
  box-shadow: var(--shadow-focus-danger);
}
:deep(.password-field input) {
  width: 100%;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--ca-color-paper-ink);
  box-shadow: none;
  -webkit-appearance: none;
  appearance: none;
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
  background: transparent;
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
  border-radius: 6px;
  background: var(--ca-color-slate);
  color: var(--ca-color-chalk);
  padding: 0 16px;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: .04em;
  cursor: pointer;
  transition: background-color 200ms var(--ease-out), transform 200ms var(--ease-out),
    box-shadow 200ms var(--ease-out);
}
.auth-submit {
  width: 100%;
  margin-top: 26px;
}
.auth-submit:hover:not(:disabled),
.send-code-btn:hover:not(:disabled) {
  background: #1d231f;
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(18,22,20,.22), 0 0 16px rgba(0,229,255,.14);
}
.auth-submit:active:not(:disabled),
.send-code-btn:active:not(:disabled) {
  transform: translateY(0) scale(.98);
}
.auth-submit:disabled,
.send-code-btn:disabled {
  opacity: .72;
  cursor: wait;
}
.auth-submit[data-loading="true"] :deep(svg) {
  display: none;
}
.auth-submit[data-loading="true"]::before {
  content: "";
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(244,244,240,.32);
  border-top-color: var(--ca-color-chalk);
  animation: auth-spin 720ms linear infinite;
}
@keyframes auth-spin {
  to { transform: rotate(360deg); }
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
  .auth-toolbar {
    top: 18px;
    left: 18px;
    right: 18px;
  }
  .auth-card-body {
    padding: 24px;
  }
  .inline {
    grid-template-columns: 1fr;
  }
  .auth-copy p {
    font-size: 15px;
  }
}

.auth.auth-light {
  /* 浅色 h1 无粉笔辉光（下方有 text-shadow:none!important），飞行字同步关掉 */
  --brand-flight-glow: 0 0 2px rgba(44, 43, 41, 0), 0 0 18px rgba(44, 43, 41, 0);
  /* 与 ProductHomeView 浅色世界同底：纯暖纸 + 同款纹理/顶部柔光 */
  background: #F9F8F6 !important;
  color: #2C2B29 !important;
}

.auth.auth-light::before {
  mix-blend-mode: multiply !important;
  background-blend-mode: normal !important;
  opacity: .4 !important;
}

.auth.auth-light::after {
  background:
    radial-gradient(ellipse 90% 60% at 50% 0%, rgba(255, 255, 255, 0.85) 0%, transparent 55%),
    radial-gradient(ellipse 130% 110% at 50% 50%, transparent 64%, rgba(44, 43, 41, 0.05) 100%) !important;
}

.auth.auth-light .auth-accent {
  background:
    radial-gradient(circle at 14% 16%, rgba(0, 184, 212, .06), transparent 30%),
    radial-gradient(circle at 86% 80%, rgba(217, 160, 91, .08), transparent 34%);
}

.auth.auth-light .auth-formula {
  color: rgba(44,43,41, calc(var(--o) * 1.6)) !important;
  text-shadow: none !important;
}

.auth.auth-light .formula-energy {
  color: rgba(0,151,167, calc(var(--o) * 2)) !important;
}

.auth.auth-light .auth-home-link {
  border-color: #E6E4DD !important;
  background: #FFFFFF !important;
  color: #444440 !important;
  backdrop-filter: none !important;
  box-shadow: 0 8px 20px rgba(18,22,20,.05) !important;
}

.auth.auth-light .auth-home-link:hover {
  border-color: #D1CBB5 !important;
  background: #FDFCFA !important;
}

.auth.auth-light .auth-theme-toggle {
  color: #444440 !important;
}

.auth.auth-light .auth-copy h1 {
  color: #2C2B29 !important;
  text-shadow: none !important;
}

.auth.auth-light .brand strong {
  color: #2C2B29 !important;
  text-shadow: none !important;
}

.auth.auth-light .auth-copy p,
.auth.auth-light .label,
.auth.auth-light .brand small,
.auth.auth-light .tabs button,
.auth.auth-light :deep(.password-tool) {
  color: #666560 !important;
}

.auth.auth-light .auth-copy p {
  color: #444440 !important;
}

.auth.auth-light .chalk-line {
  color: #999990 !important;
}

.auth.auth-light .chalk-line i {
  background: linear-gradient(90deg, rgba(0,151,167,.6), #D1CBB5 60%, rgba(209,203,181,.2)) !important;
  box-shadow: none !important;
}

.auth.auth-light .auth-card {
  border-color: #E6E4DD !important;
  background: #FFFFFF !important;
  box-shadow: 0 24px 58px rgba(18,22,20,.09), 0 2px 8px rgba(18,22,20,.04) !important;
}

.auth.auth-light .auth-card-edge {
  background: linear-gradient(90deg, #121614, #1d231f 50%, #121614) !important;
}

.auth.auth-light .brand,
.auth.auth-light .brand span {
  color: #00E5FF !important;
}

.auth.auth-light .brand span {
  background: #121614 !important;
}

.auth.auth-light .tabs {
  border-color: #E6E4DD !important;
  background: #F4F1EA !important;
}

.auth.auth-light .tabs button:hover:not(.active) {
  color: #2C2B29 !important;
}

.auth.auth-light .tabs button.active {
  background: #2C2B29 !important;
  color: #F9F8F6 !important;
  box-shadow: 0 4px 12px rgba(18,22,20,.16) !important;
  text-shadow: none !important;
}

.auth.auth-light .input,
.auth.auth-light :deep(.password-field) {
  border-color: #D1CBB5 !important;
  background: #FFFFFF !important;
  color: #2C2B29 !important;
}

.auth.auth-light .input::placeholder,
.auth.auth-light :deep(.password-field input)::placeholder {
  color: #999990 !important;
}

.auth.auth-light :deep(.password-field input) {
  color: #2C2B29 !important;
}

.auth.auth-light .input:hover,
.auth.auth-light :deep(.password-field:hover) {
  border-color: #999990 !important;
}

.auth.auth-light .input:focus,
.auth.auth-light :deep(.password-field:focus-within) {
  border-color: #0097A7 !important;
  box-shadow: 0 0 0 3px rgba(0,151,167,.15) !important;
}

.auth.auth-light :deep(.password-tool:hover) {
  background: transparent !important;
  color: #2C2B29 !important;
}

.auth.auth-light .form-error {
  border-color: var(--color-danger-100) !important;
  background: var(--color-danger-50) !important;
  color: var(--color-danger-700) !important;
}

.auth.auth-light .auth-submit,
.auth.auth-light .send-code-btn {
  background: #121614 !important;
  color: #F4F4F0 !important;
}

.auth.auth-light .auth-submit:hover:not(:disabled),
.auth.auth-light .send-code-btn:hover:not(:disabled) {
  background: #2C2B29 !important;
  box-shadow: 0 10px 24px rgba(18,22,20,.18), 0 0 16px rgba(0,184,212,.14) !important;
}

.auth.auth-dark {
  background: radial-gradient(ellipse 100% 80% at 50% 38%, #1B211D 0%, #121614 56%, #0A0D0B 100%);
  background-attachment: fixed;
  color: #F4F4F0;
}

.auth.auth-dark .auth-accent {
  background:
    radial-gradient(circle at 16% 18%, rgba(0, 229, 255, .09), transparent 32%),
    radial-gradient(circle at 84% 78%, rgba(217, 160, 91, .07), transparent 36%);
}

.auth.auth-dark .auth-card {
  border-color: rgba(244, 244, 240, .24) !important;
  background: linear-gradient(180deg, rgba(255,254,248,.98), rgba(247,242,228,.96)) !important;
  color: #2C2B29 !important;
  box-shadow:
    0 30px 80px rgba(0,0,0,.46),
    0 8px 24px rgba(0,0,0,.3),
    0 0 28px rgba(0,229,255,.05);
}

.auth.auth-dark .auth-home-link {
  border-color: rgba(244,244,240,.16);
  background: rgba(18,22,20,.6);
  color: #E9EBE7;
}

.auth.auth-dark .auth-home-link:hover {
  border-color: rgba(244,244,240,.3);
  background: rgba(244,244,240,.1);
}

.auth.auth-dark .auth-theme-toggle {
  color: #C6CCC7;
}

.auth.auth-dark .auth-copy h1 {
  color: #F4F4F0;
}

.auth.auth-dark .auth-copy p {
  color: rgba(244,244,240,.82);
}

.auth.auth-dark .chalk-line {
  color: rgba(244,244,240,.55);
}

.auth.auth-dark .brand strong,
.auth.auth-dark .label {
  color: #2C2B29 !important;
}

.auth.auth-dark .label {
  color: #666560 !important;
}

.auth.auth-dark .brand small {
  color: #666560 !important;
}

.auth.auth-dark .brand,
.auth.auth-dark .brand span {
  color: #00E5FF !important;
}

.auth.auth-dark .brand span {
  background: #121614 !important;
}

.auth.auth-dark .tabs {
  border-color: rgba(44,43,41,.14) !important;
  background: #EFEAD9 !important;
}

.auth.auth-dark .tabs button {
  color: #666560 !important;
}

.auth.auth-dark .tabs button:hover:not(.active) {
  color: #2C2B29 !important;
}

.auth.auth-dark .tabs button.active {
  background: #121614 !important;
  color: #F4F4F0 !important;
  box-shadow: 0 4px 12px rgba(18,22,20,.24);
}

.auth.auth-dark .input,
.auth.auth-dark :deep(.password-field) {
  border-color: rgba(44,43,41,.2) !important;
  background: #FFFEF8 !important;
  color: #2C2B29 !important;
}

.auth.auth-dark :deep(.password-field input) {
  background: #FFFEF8 !important;
  color: #2C2B29 !important;
}

.auth.auth-dark .input::placeholder,
.auth.auth-dark :deep(.password-field input)::placeholder {
  color: #999990 !important;
}

.auth.auth-dark .input:hover,
.auth.auth-dark :deep(.password-field:hover) {
  border-color: rgba(44,43,41,.38) !important;
}

.auth.auth-dark .input:focus,
.auth.auth-dark :deep(.password-field:focus-within) {
  border-color: #00B8D4 !important;
  box-shadow: 0 0 0 3px rgba(0,184,212,.18), 0 0 14px rgba(0,229,255,.14) !important;
}

.auth.auth-dark :deep(.password-tool) {
  color: #666560 !important;
}

.auth.auth-dark :deep(.password-tool:hover) {
  background: rgba(44,43,41,.06) !important;
  color: #2C2B29 !important;
}

.auth.auth-dark .form-error {
  border-color: var(--color-danger-100);
  background: var(--color-danger-50);
  color: var(--color-danger-700);
}

.auth.auth-dark .auth-submit,
.auth.auth-dark .send-code-btn {
  background: #121614 !important;
  color: #F4F4F0 !important;
}

.auth.auth-dark .auth-submit:hover:not(:disabled),
.auth.auth-dark .send-code-btn:hover:not(:disabled) {
  background: #1d231f !important;
  box-shadow: 0 10px 24px rgba(0,0,0,.32), 0 0 16px rgba(0,229,255,.16) !important;
}

/* ====== 页面进入：黑板底色常驻，标题从左上承接，登录卡右侧滑入 ====== */
/* 转场类移除瞬间禁止直载入场动画重播（动画名切换会从第 0 帧重来 = 全员闪烁消失再淡入），
   entered-from-home 由脚本在挂载时打上并永久保留。
   注意必须同时排除离场类：本规则特异性高于离场规则，不排除会禁掉返程的离场动画 */
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .auth-formula,
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .auth-copy h1,
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .auth-copy p,
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .chalk-line,
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .auth-card,
.auth.entered-from-home:not(.route-home-auth-enter-active):not(.route-auth-home-leave-active) .auth-accent {
  animation: none;
}
.auth.route-home-auth-enter-active {
  transition: opacity 980ms linear;
}
.auth.route-home-auth-enter-from {
  opacity: .999;
  filter: none;
  transform: none;
}
.auth.route-home-auth-enter-active .auth-toolbar {
  animation: auth-link-in 620ms cubic-bezier(.22, .61, .36, 1) 260ms both;
}
.auth.route-home-auth-enter-active .auth-accent {
  animation: auth-formula-mount 560ms cubic-bezier(.22, .61, .36, 1) 380ms both;
}
.auth.route-home-auth-enter-active .auth-formula {
  /* 所有入场动画必须在 980ms 转场窗口内收尾，否则类移除时被截断产生跳变 */
  animation: auth-formula-in 700ms cubic-bezier(.22, .61, .36, 1) both;
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
  will-change: opacity;
  animation: auth-h1-takeover 980ms linear both;
}
.auth.route-home-auth-enter-active .auth-copy p {
  animation: auth-copy-in 620ms cubic-bezier(.22, .61, .36, 1) 240ms both;
}
.auth.route-home-auth-enter-active .chalk-line {
  animation: auth-copy-in 620ms cubic-bezier(.22, .61, .36, 1) 320ms both;
}
.auth.route-home-auth-enter-active .auth-card {
  animation: auth-card-in 740ms cubic-bezier(.22, .61, .36, 1) 200ms both;
}
/* 返程离场层转透明：下方首页同款黑板从第一帧接管底色，主页内容随转场逐步显形，
   不再在 980ms 揭幕时整页突现（!important 用于压过 .auth-light 的 !important 底色） */
.auth.route-auth-home-leave-active {
  background: transparent !important;
  transition: opacity 980ms linear;
}
/* 透明底上的噪点层失去可混合底色会泛白成磨砂——立即隐藏，由下层首页同款纹理接管 */
.auth.route-auth-home-leave-active::before,
.auth.route-auth-home-leave-active::after {
  opacity: 0 !important;
}
.auth.route-auth-home-leave-active .auth-accent {
  animation: auth-accent-out 420ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.auth.route-auth-home-leave-active .auth-toolbar {
  animation: auth-link-out 620ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-formula {
  animation: auth-formula-out 760ms cubic-bezier(.55, .06, .68, .19) both;
}
.auth.route-auth-home-leave-active .auth-copy h1 {
  transform-origin: left top;
  will-change: transform, opacity;
  animation: auth-h1-to-home-logo 940ms cubic-bezier(.45, .05, .22, 1) both;
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
@keyframes auth-accent-out {
  to { opacity: 0; }
}
@keyframes auth-formula-in {
  from { opacity: 0; transform: rotate(var(--r)); }
  to { opacity: 1; transform: translateX(0) rotate(var(--r)); }
}
@keyframes auth-formula-out {
  to { opacity: 0; transform: rotate(var(--r)); }
}
/* 去程承接：上层飞行字 76% 抵达后，本体在 80→93% 同位淡入，与其 84→96% 的淡出交叉，
   字体/字号/行高/辉光完全一致，交接不可见 */
@keyframes auth-h1-takeover {
  0%, 80% { opacity: 0; transform: translate3d(0, 0, 0); }
  93%, 100% { opacity: 1; transform: translate3d(0, 0, 0); }
}
/* 返程：减速飞抵 nav 角落、停笔落定，再与下层首页品牌字（72→90% 同位淡入）交叉淡出；
   辉光在途中归零，与 nav 文字的无光状态对齐 */
@keyframes auth-h1-to-home-logo {
  0% {
    opacity: 1;
    transform: translate3d(0, 0, 0);
    font-size: var(--shared-title-size);
    text-shadow: var(--brand-flight-glow);
  }
  76%, 84% {
    opacity: 1;
    transform: translate3d(var(--title-to-logo-x), var(--title-to-logo-y), 0);
    font-size: 20px;
    text-shadow: 0 0 2px rgba(244, 244, 240, 0), 0 0 18px rgba(244, 244, 240, 0);
  }
  96%, 100% {
    opacity: 0;
    transform: translate3d(var(--title-to-logo-x), var(--title-to-logo-y), 0);
    font-size: 20px;
    text-shadow: 0 0 2px rgba(244, 244, 240, 0), 0 0 18px rgba(244, 244, 240, 0);
  }
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
    box-shadow: 0 30px 80px rgba(0, 0, 0, .4), 0 8px 24px rgba(0, 0, 0, .24);
  }
}
@keyframes auth-card-out {
  from {
    opacity: 1;
    transform: translate3d(0, 0, 0);
    box-shadow: 0 30px 80px rgba(0, 0, 0, .4), 0 8px 24px rgba(0, 0, 0, .24);
  }
  to {
    opacity: 0;
    transform: translate3d(min(32vw, 360px), 0, 0);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0);
  }
}

/* 窄屏下 .auth-copy 回到流式布局，共享坐标失效——标题退化为柔和淡入/淡出 */
@media (max-width: 860px) {
  .auth.route-home-auth-enter-active .auth-copy h1 {
    animation: auth-copy-in 620ms cubic-bezier(.22, .61, .36, 1) 200ms both;
  }
  .auth.route-auth-home-leave-active .auth-copy h1 {
    animation: auth-copy-out 620ms cubic-bezier(.55, .06, .68, .19) both;
  }
}
</style>
