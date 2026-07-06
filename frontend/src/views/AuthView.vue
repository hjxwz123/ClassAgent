<template>
  <PageLoader v-if="loginRedirecting" />
  <main v-else class="auth" :class="{ 'auth-link-invalid': linkValidationStatus === 'invalid' }">
    <div class="auth-bg">
      <AuroraBackground :color-stops="['#00E5FF', '#FF5722', '#FFD54F']" :amplitude="1" :blend="0.55" :speed="0.75" />
    </div>
    <div class="auth-bg auth-bg-soft">
      <ParticleField :count="90" :colors="['#00E5FF', '#FFD54F', '#FF5722']" :speed="0.3" :parallax="0.05" />
    </div>
    <div class="auth-veil" aria-hidden="true"></div>
    <ClickSpark spark-color="#00E5FF" :spark-count="10" :spark-radius="24" />

    <RouterLink to="/" class="auth-back"><ArrowLeft :size="17" />返回首页</RouterLink>

    <div class="auth-stage">
      <aside class="auth-brand-side">
        <div class="auth-brand-logo"><BookOpen :size="22" /><span>智学黑板</span></div>
        <div class="auth-brand-eyebrow"><DecryptedText text="WELCOME BACK" trigger="view" :speed="46" /></div>
        <h1 class="auth-brand-title"><GradientText :animation-speed="7">欢迎回到你的黑板</GradientText></h1>
        <p class="auth-brand-rotate">
          继续你的
          <RotatingText class="auth-rotate-word" :texts="['课时', '错题本', '伴学问答', '复习卷']" :interval="2000" :duration="500" />
        </p>
        <p class="auth-brand-sub">
          加入课程、继续课时、向 AI 提问，把每天的学习进度稳稳记录下来。
        </p>
        <div class="auth-brand-foot"><ShinyText text="ClassAgent Learning Console" :speed="5" /></div>
      </aside>

      <div class="auth-card-wrap">
        <div class="auth-card-glow" aria-hidden="true"></div>
        <section class="auth-card">
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
                  <template v-if="registerForm.token">
                    <label class="label" for="register-email">邮箱</label>
                    <input id="register-email" v-model="registerForm.email" class="input" type="email" autocomplete="username" required readonly :aria-invalid="formError.includes('邮箱')" />
                    <label class="label" for="register-nickname">昵称</label>
                    <input id="register-nickname" v-model="registerForm.nickname" class="input" autocomplete="nickname" required :aria-invalid="formError.includes('昵称')" />
                    <label class="label" for="register-student-no">学号</label>
                    <input id="register-student-no" v-model="studentNo" class="input" autocomplete="off" required :aria-invalid="formError.includes('学号')" />
                    <label class="label" for="register-password">密码</label>
                    <PasswordField id="register-password" v-model="registerForm.password" autocomplete="new-password" required :aria-invalid="formError.includes('密码')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><UserPlus :size="17" />注册学生账号</button>
                  </template>
                  <div v-else-if="linkSent" class="verify-pending">
                    <span class="verify-pending-icon"><Mail :size="30" /></span>
                    <strong class="verify-pending-title">验证邮件已发送</strong>
                    <p class="verify-pending-text">已向 <b>{{ registerForm.email }}</b> 发送验证链接，请在 10 分钟内打开邮件中的链接完成注册。</p>
                    <p class="verify-pending-hint">没收到？请检查垃圾邮件 / 垃圾箱，或稍后重新发送。</p>
                    <button type="button" class="auth-submit" :data-loading="loading" :disabled="loading || resendCountdown > 0" @click="resendLink"><RefreshCw :size="16" />{{ resendCountdown > 0 ? `重新发送（${resendCountdown}s）` : '重新发送' }}</button>
                    <button type="button" class="verify-pending-back" @click="backToEmailStep"><ArrowLeft :size="14" />换一个邮箱</button>
                  </div>
                  <template v-else>
                    <label class="label" for="register-email">邮箱</label>
                    <input id="register-email" v-model="registerForm.email" class="input" type="email" autocomplete="username" required :aria-invalid="formError.includes('邮箱')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><UserPlus :size="17" />发送注册链接</button>
                  </template>
                </form>

                <form v-else key="reset" @submit.prevent="resetForm.token ? resetPassword() : sendResetLink()">
                  <template v-if="resetForm.token">
                    <label class="label" for="reset-email">邮箱</label>
                    <input id="reset-email" v-model="resetForm.email" class="input" type="email" autocomplete="username" required readonly :aria-invalid="formError.includes('邮箱')" />
                    <label class="label" for="reset-new-password">新密码</label>
                    <PasswordField id="reset-new-password" v-model="resetForm.new_password" autocomplete="new-password" required :aria-invalid="formError.includes('密码')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><KeyRound :size="17" />重置密码</button>
                  </template>
                  <div v-else-if="linkSent" class="verify-pending">
                    <span class="verify-pending-icon"><Mail :size="30" /></span>
                    <strong class="verify-pending-title">找回链接已发送</strong>
                    <p class="verify-pending-text">已向 <b>{{ resetForm.email }}</b> 发送重置密码链接，请在 10 分钟内打开邮件中的链接设置新密码。</p>
                    <p class="verify-pending-hint">没收到？请检查垃圾邮件 / 垃圾箱，或稍后重新发送。</p>
                    <button type="button" class="auth-submit" :data-loading="loading" :disabled="loading || resendCountdown > 0" @click="resendLink"><RefreshCw :size="16" />{{ resendCountdown > 0 ? `重新发送（${resendCountdown}s）` : '重新发送' }}</button>
                    <button type="button" class="verify-pending-back" @click="backToEmailStep"><ArrowLeft :size="14" />换一个邮箱</button>
                  </div>
                  <template v-else>
                    <label class="label" for="reset-email">邮箱</label>
                    <input id="reset-email" v-model="resetForm.email" class="input" type="email" autocomplete="username" required :aria-invalid="formError.includes('邮箱')" />
                    <button class="auth-submit" :data-loading="loading" :disabled="loading"><KeyRound :size="17" />发送找回链接</button>
                  </template>
                </form>
              </Transition>
            </template>
          </template>
          </div>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { NavigationFailureType, isNavigationFailure, useRoute, useRouter } from "vue-router";
import type { NavigationFailure } from "vue-router";
import { AlertCircle, ArrowLeft, BookOpen, KeyRound, LogIn, Mail, RefreshCw, UserPlus } from "../icons";
import { api } from "../api/client";
import { defaultRouteForRole } from "../router";
import { useSessionStore } from "../stores/session";
import PageLoader from "../components/PageLoader.vue";
import PasswordField from "../components/PasswordField.vue";
import ThemeToggle from "../components/ThemeToggle.vue";
import { readStoredTheme, subscribeAppTheme, type AppTheme } from "../theme";
import type { User } from "../types";
// React Bits 特效（已移植为 Vue）
import AuroraBackground from "../components/reactbits/AuroraBackground.vue";
import ParticleField from "../components/reactbits/ParticleField.vue";
import ClickSpark from "../components/reactbits/ClickSpark.vue";
import GradientText from "../components/reactbits/GradientText.vue";
import SplitText from "../components/reactbits/SplitText.vue";
import ShinyText from "../components/reactbits/ShinyText.vue";
import RotatingText from "../components/reactbits/RotatingText.vue";
import DecryptedText from "../components/reactbits/DecryptedText.vue";

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
// 发送注册链接后进入「待验证」页：显示已发送到哪个邮箱 + 重新发送(带冷却)
const linkSent = ref(false);
const resendCountdown = ref(0);
let resendTimer: number | undefined;
function startResendCountdown(seconds = 60) {
  resendCountdown.value = seconds;
  if (resendTimer) window.clearInterval(resendTimer);
  resendTimer = window.setInterval(() => {
    resendCountdown.value -= 1;
    if (resendCountdown.value <= 0 && resendTimer) {
      window.clearInterval(resendTimer);
      resendTimer = undefined;
    }
  }, 1000);
}
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
  if (resendTimer) window.clearInterval(resendTimer);
});

function setMode(value: "login" | "register" | "reset") {
  mode.value = value;
  formError.value = "";
  registerForm.token = "";
  resetForm.token = "";
  linkSent.value = false;
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
    linkSent.value = true;
    startResendCountdown(60);
    emit("notice", "success", "注册链接已发送，请查收邮箱；找不到请查看垃圾邮件或垃圾箱");
  } catch (error) {
    formError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  } finally {
    loading.value = false;
  }
}

// 注册 / 找回共用一套「待验证」重新发送：按当前模式发对应的链接
function resendLink() {
  if (loading.value || resendCountdown.value > 0) return;
  if (mode.value === "register") void sendRegistrationLink();
  else void sendResetLink();
}

// 「换一个邮箱」：退回邮箱输入
function backToEmailStep() {
  linkSent.value = false;
  formError.value = "";
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
    linkSent.value = true;
    startResendCountdown(60);
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
.auth {
  --a-ink: #eef2f5;
  --a-muted: #93a0aa;
  --a-cyan: #00e5ff;
  --a-orange: #ff5722;
  --a-gold: #ffd54f;
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  background: #060809;
  color: var(--a-ink);
  overflow: hidden;
  font-family: var(--ca-font-sans, -apple-system, "PingFang SC", sans-serif);
}

/* 背景层 */
.auth-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.auth-bg-soft { opacity: 0.6; }
.auth-veil {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background:
    radial-gradient(60% 55% at 50% 45%, transparent 45%, rgba(6, 8, 9, 0.7) 100%),
    linear-gradient(to bottom, rgba(6, 8, 9, 0.4), transparent 40%, rgba(6, 8, 9, 0.85));
}

/* 返回首页 */
.auth-back {
  position: absolute;
  top: 24px;
  left: 28px;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(10px);
  color: var(--a-ink);
  font-size: 14px;
  text-decoration: none;
  transition: border-color 0.2s, color 0.2s, transform 0.18s;
}
.auth-back:hover { border-color: var(--a-cyan); color: var(--a-cyan); transform: translateX(-2px); }

/* 舞台：左品牌 + 右卡片 */
.auth-stage {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 980px;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 56px;
  align-items: center;
}

/* 左侧品牌区 */
.auth-brand-side { padding: 12px 0; }
.auth-brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 18px;
  color: var(--a-cyan);
  margin-bottom: 26px;
}
.auth-brand-logo span { color: var(--a-ink); }
.auth-brand-eyebrow {
  font-family: var(--ca-font-mono, monospace);
  font-size: 12px;
  letter-spacing: 0.28em;
  color: var(--a-cyan);
  margin-bottom: 14px;
}
.auth-brand-title {
  font-size: clamp(2.2rem, 4.6vw, 3.3rem);
  font-weight: 900;
  line-height: 1.15;
  margin: 0 0 16px;
}
.auth-brand-rotate {
  font-size: clamp(1.05rem, 2.4vw, 1.4rem);
  font-weight: 600;
  color: #d7dee3;
  margin: 0 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.auth-rotate-word { color: var(--a-cyan); font-weight: 800; }
.auth-brand-sub {
  font-size: 15px;
  line-height: 1.9;
  color: var(--a-muted);
  margin: 0 0 28px;
  max-width: 420px;
}
.auth-brand-foot {
  font-family: var(--ca-font-mono, monospace);
  font-size: 12px;
  letter-spacing: 0.14em;
}

/* 右侧卡片 */
.auth-card-wrap { position: relative; }
.auth-card-glow {
  position: absolute;
  inset: -1px;
  border-radius: 24px;
  padding: 1px;
  background: linear-gradient(130deg, var(--a-cyan), transparent 30%, transparent 70%, var(--a-orange));
  background-size: 300% 300%;
  animation: auth-glow-move 8s ease infinite;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.8;
  pointer-events: none;
}
@keyframes auth-glow-move {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.auth-card {
  position: relative;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(18, 24, 27, 0.86), rgba(10, 14, 16, 0.92));
  backdrop-filter: blur(20px);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5), 0 0 60px rgba(0, 229, 255, 0.06);
  overflow: hidden;
}
.auth-card-body { padding: 38px 34px 34px; }

/* 卡片内标题 */
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
}
.brand span {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--a-cyan);
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid rgba(0, 229, 255, 0.28);
}
.brand strong { font-size: 21px; font-weight: 800; }

/* Tab 切换 */
.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 22px;
}
.tabs button {
  flex: 1;
  padding: 9px 0;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--a-muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
}
.tabs button:hover { color: var(--a-ink); }
.tabs button.active {
  color: #041014;
  background: linear-gradient(120deg, var(--a-cyan), #7ff0ff);
  box-shadow: 0 4px 16px rgba(0, 229, 255, 0.3);
}

/* 表单错误 */
.form-error {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(198, 40, 40, 0.14);
  border: 1px solid rgba(239, 154, 154, 0.3);
  color: #ff9a9a;
  font-size: 13px;
  margin-bottom: 16px;
}

/* 表单字段 */
form { display: flex; flex-direction: column; }
.label {
  font-size: 13px;
  font-weight: 600;
  color: var(--a-muted);
  margin: 14px 0 7px;
}
.label:first-child { margin-top: 0; }
.input,
.auth-card-body :deep(input) {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: var(--a-ink);
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.input::placeholder,
.auth-card-body :deep(input)::placeholder { color: rgba(147, 160, 170, 0.55); }
.input:focus,
.auth-card-body :deep(input:focus) {
  outline: none;
  border-color: var(--a-cyan);
  background: rgba(0, 229, 255, 0.05);
  box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.14);
}
.input[aria-invalid="true"],
.auth-card-body :deep(input[aria-invalid="true"]) {
  border-color: rgba(239, 83, 80, 0.7);
  box-shadow: 0 0 0 3px rgba(239, 83, 80, 0.14);
}
/* PasswordField 组件容器：覆盖其默认浅色底(--color-bg-surface)，统一为暗色玻璃 */
.auth-card-body :deep(.password-field) {
  width: 100%;
  box-sizing: border-box;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  min-height: 46px;
  padding: 0 6px 0 14px;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.auth-card-body :deep(.password-field:focus-within) {
  border-color: var(--a-cyan);
  background: rgba(0, 229, 255, 0.05);
  box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.14);
}
.auth-card-body :deep(.password-field.invalid) {
  border-color: rgba(239, 83, 80, 0.7);
  box-shadow: 0 0 0 3px rgba(239, 83, 80, 0.14);
}
/* 容器内的 input 保持透明，去掉通用 :deep(input) 给它加的填充底与边框 */
.auth-card-body :deep(.password-field input) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  color: var(--a-ink);
}
.auth-card-body :deep(.password-field input:focus) {
  background: transparent;
  box-shadow: none;
}
.auth-card-body :deep(.password-tool) { color: var(--a-muted); }
.auth-card-body :deep(.password-tool:hover) { color: var(--a-ink); background: rgba(255, 255, 255, 0.06); }

/* 提交按钮 */
.auth-submit {
  margin-top: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px 20px;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  color: #041014;
  font-size: 15px;
  font-weight: 800;
  background: linear-gradient(120deg, var(--a-cyan), #58ecff 55%, var(--a-gold));
  background-size: 180% 100%;
  box-shadow: 0 10px 30px rgba(0, 229, 255, 0.28);
  transition: transform 0.18s, box-shadow 0.2s, background-position 0.4s, opacity 0.2s;
}
.auth-submit:hover { transform: translateY(-2px); background-position: 100% 0; box-shadow: 0 14px 40px rgba(0, 229, 255, 0.4); }
.auth-submit:active { transform: translateY(0); }
.auth-submit:disabled { opacity: 0.7; cursor: default; transform: none; }
.auth-submit[data-loading="true"] { position: relative; color: transparent; }
.auth-submit[data-loading="true"]::after {
  content: "";
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(4, 16, 20, 0.35);
  border-top-color: #041014;
  border-radius: 50%;
  animation: auth-spin 0.7s linear infinite;
}
@keyframes auth-spin { to { transform: rotate(360deg); } }

/* 链接校验结果 */
.link-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  padding: 30px 10px;
  color: var(--a-muted);
}
.link-result strong { color: var(--a-ink); font-size: 16px; }
.link-result--error { color: #ff9a9a; }
.link-result--error strong { color: #ff9a9a; }

/* 发送注册链接后的「待验证」面板 */
.verify-pending {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  padding: 6px 2px 2px;
}
.verify-pending-icon {
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  color: var(--a-cyan);
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid rgba(0, 229, 255, 0.28);
  margin-bottom: 2px;
}
.verify-pending-title { color: var(--a-ink); font-size: 18px; font-weight: 800; }
.verify-pending-text { color: var(--a-muted); font-size: 14px; line-height: 1.7; }
.verify-pending-text b { color: var(--a-ink); font-weight: 700; word-break: break-all; }
.verify-pending-hint { color: var(--a-muted); font-size: 12.5px; opacity: 0.85; }
.verify-pending .auth-submit { margin-top: 8px; }
.verify-pending-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--a-muted);
  font-size: 13px;
  transition: color 0.18s;
}
.verify-pending-back:hover { color: var(--a-ink); }

/* 过渡动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: opacity 0.25s, transform 0.25s; }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(-6px); }
.page-switch-enter-active, .page-switch-leave-active { transition: opacity 0.28s ease, transform 0.28s ease; }
.page-switch-enter-from { opacity: 0; transform: translateX(16px); }
.page-switch-leave-to { opacity: 0; transform: translateX(-16px); }
.input-error-shake { animation: auth-shake 0.4s; }
@keyframes auth-shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-5px); }
  40%, 80% { transform: translateX(5px); }
}

/* 响应式 */
@media (max-width: 820px) {
  .auth-stage { grid-template-columns: 1fr; gap: 30px; max-width: 460px; }
  .auth-brand-side { text-align: center; padding: 0; }
  .auth-brand-logo, .auth-brand-rotate { justify-content: center; }
  .auth-brand-sub { margin-left: auto; margin-right: auto; }
  .auth-brand-rotate { display: flex; }
}
@media (max-width: 520px) {
  .auth { padding: 20px 16px; }
  .auth-card-body { padding: 30px 24px 26px; }
  .auth-back { top: 16px; left: 16px; }
}

@media (prefers-reduced-motion: reduce) {
  .auth-card-glow, .auth-submit[data-loading="true"]::after { animation: none; }
}
</style>
