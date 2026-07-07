<template>
  <section class="student-profile-page">
    <!-- 1. 身份 Hero -->
    <article class="pf-hero">
      <div class="pf-hero-grain" aria-hidden="true"></div>
      <div class="pf-hero-aside">
        <button
          type="button"
          class="pf-avatar"
          :data-loading="avatarUploading"
          :disabled="avatarUploading"
          title="更换头像"
          aria-label="更换头像"
          @click="studentAvatarInput?.click()"
        >
          <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" />
          <DefaultUserAvatar v-else />
          <span class="pf-avatar-cam"><Camera :size="14" /></span>
        </button>
        <input
          ref="studentAvatarInput"
          class="visually-hidden-file"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          @change="uploadProfileAvatar"
        />
        <span class="pf-hero-tag" aria-hidden="true">个人档案</span>
      </div>

      <div class="pf-identity">
        <div class="pf-identity-top">
          <span class="pf-role-pill"><Sparkles :size="13" />学生</span>
          <button type="button" class="pf-edit-link" @click="focusProfilePanel">
            <Pencil :size="14" />编辑资料
          </button>
        </div>
        <h1 class="pf-name">{{ profileForm.nickname || "同学" }}</h1>
        <p class="pf-greeting">今天也要好好学习呀 ~</p>

        <dl class="pf-meta">
          <div class="pf-meta-item">
            <span class="pf-meta-ic"><IdCard :size="16" /></span>
            <dt>学号</dt>
            <dd class="mono">{{ user.student_no || "—" }}</dd>
          </div>
          <div class="pf-meta-item">
            <span class="pf-meta-ic"><Mail :size="16" /></span>
            <dt>邮箱</dt>
            <dd class="mono">{{ user.email || "—" }}</dd>
          </div>
          <div class="pf-meta-item">
            <span class="pf-meta-ic"><GraduationCap :size="16" /></span>
            <dt>学校</dt>
            <dd>{{ profileForm.school || "未填写" }}</dd>
          </div>
          <div class="pf-meta-item">
            <span class="pf-meta-ic"><CalendarCheck :size="16" /></span>
            <dt>加入时间</dt>
            <dd>{{ joinedLabel }}</dd>
          </div>
        </dl>

        <div class="pf-bio">
          <p v-if="profileForm.bio" class="pf-bio-text">{{ profileForm.bio }}</p>
          <p v-else class="pf-bio-empty">这位同学还没有填写简介，点击右上角「编辑资料」写点什么吧。</p>
          <button type="button" class="pf-bio-edit" title="编辑简介" @click="focusProfilePanel">
            <Pencil :size="14" />
          </button>
        </div>
      </div>
    </article>

    <!-- 2. 学习数据 Banner -->
    <article class="pf-banner">
      <div class="pf-banner-rule" aria-hidden="true"></div>
      <div class="pf-banner-grain" aria-hidden="true"></div>
      <header class="pf-banner-head">
        <h2>学习概览</h2>
        <button type="button" class="pf-refresh" :data-loading="refreshing" :disabled="refreshing" @click="refreshProfile">
          <RefreshCw :size="14" />刷新
        </button>
      </header>
      <div class="pf-stat-grid">
        <div v-for="s in statItems" :key="s.label" class="pf-stat" :class="`is-${s.tone}`">
          <span class="pf-stat-ic"><component :is="s.icon" :size="20" /></span>
          <strong class="pf-stat-num">{{ s.value }}<i>{{ s.unit }}</i></strong>
          <span class="pf-stat-label">{{ s.label }}</span>
        </div>
      </div>
    </article>

    <!-- 3. 成就墙 + 最近动态 -->
    <div class="pf-columns">
      <article ref="achCardRef" class="pf-card pf-ach-card">
        <header class="pf-card-head">
          <h2><Award :size="18" />我的成就</h2>
          <span class="pf-card-sub">已解锁 {{ unlockedCount }}/{{ achievements.length || 5 }}</span>
        </header>
        <div class="pf-ach-grid">
          <div
            v-for="item in achievements"
            :key="item.key"
            class="pf-ach"
            :class="{ unlocked: item.unlocked }"
          >
            <span class="pf-ach-ic">
              <Award v-if="item.unlocked" :size="24" />
              <Lock v-else :size="22" />
            </span>
            <strong class="pf-ach-name">{{ item.name }}</strong>
            <span class="pf-ach-status">{{ item.unlocked ? "已解锁" : "未解锁" }}</span>
          </div>
        </div>
      </article>

      <article ref="timelineCardRef" class="pf-card pf-timeline">
        <ActivityTimeline :items="profilePayload.activities || []" />
      </article>
    </div>

    <!-- 4. 设置区（可折叠） -->
    <div ref="settingsRef" class="pf-settings">
      <!-- 资料编辑 -->
      <section class="pf-panel" :class="{ open: panels.profile }">
        <button type="button" class="pf-panel-head" :aria-expanded="panels.profile" @click="panels.profile = !panels.profile">
          <span class="pf-panel-title"><Pencil :size="17" />资料编辑</span>
          <ChevronDown :size="18" class="pf-chevron" />
        </button>
        <div v-show="panels.profile" class="pf-panel-body">
          <div class="pf-field-grid">
            <label class="pf-field">姓名<input v-model="profileForm.nickname" class="input" /></label>
            <label class="pf-field">学校<input v-model="profileForm.school" class="input" /></label>
            <label class="pf-field wide">简介<textarea v-model="profileForm.bio" class="textarea" placeholder="介绍一下自己吧"></textarea></label>
          </div>
          <footer class="pf-panel-foot">
            <button class="btn btn-primary" :data-loading="profileSaving" :disabled="profileSaving" @click="saveProfile"><Save :size="15" />保存修改</button>
          </footer>
        </div>
      </section>

      <!-- 账号安全 -->
      <section class="pf-panel" :class="{ open: panels.security }">
        <button type="button" class="pf-panel-head" :aria-expanded="panels.security" @click="panels.security = !panels.security">
          <span class="pf-panel-title"><Shield :size="17" />账号安全</span>
          <ChevronDown :size="18" class="pf-chevron" />
        </button>
        <div v-show="panels.security" class="pf-panel-body">
          <div class="pf-pass-grid">
            <div class="pf-field"><span>当前密码</span><PasswordField v-model="passwordForm.old_password" placeholder="请输入当前密码" /></div>
            <div class="pf-field"><span>新密码</span><PasswordField v-model="passwordForm.new_password" placeholder="至少 8 位，建议字母+数字组合" /></div>
            <div class="pf-field"><span>确认新密码</span><PasswordField v-model="passwordConfirm" placeholder="再次输入新密码" /></div>
          </div>
          <footer class="pf-panel-foot">
            <button class="btn btn-primary" :data-loading="passwordSaving" :disabled="passwordSaving" @click="changePassword">确认修改</button>
          </footer>
        </div>
      </section>

      <!-- 通知设置 -->
      <section class="pf-panel" :class="{ open: panels.notify }">
        <button type="button" class="pf-panel-head" :aria-expanded="panels.notify" @click="panels.notify = !panels.notify">
          <span class="pf-panel-title"><Bell :size="17" />通知设置</span>
          <ChevronDown :size="18" class="pf-chevron" />
        </button>
        <div v-show="panels.notify" class="pf-panel-body">
          <div class="pf-notice-grid">
            <div v-for="item in noticeSettings" :key="item.key" class="pf-toggle-line">
              <AppCheckbox v-model="item.enabled" variant="switch" :label="item.label" />
            </div>
          </div>
          <footer class="pf-panel-foot">
            <button class="btn btn-secondary" :data-loading="noticeSaving" :disabled="noticeSaving" @click="saveNotices">保存设置</button>
          </footer>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
// 个人中心页（身份 Hero + 学习概览 Banner + 成就墙/最近动态 + 可折叠设置区）。
// 依 UI.md「智学黑板」纸张系统重设计：纸张白卡 + 分形噪点颗粒 + 宋体标题 + mono 数字/学号 + 一处克制的粉笔黑板角标。
// 跨页共享的资料表单、成就负载、统计、头像 URL、通知设置及 applyStudentProfile/loadProfile/normalizeNoticeSettings 经 useStudentCtx 注入；
// 本页自持折叠面板状态、头像上传中态、密码表单等局部状态与仅本页调用的动作。
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { api, setToken } from "../../../api/client";
import {
  Award, Bell, CalendarCheck, Camera, CheckCircle, ChevronDown, Clock, Flame, GraduationCap,
  IdCard, Lock, Mail, MessageCircle, Pencil, RefreshCw, Save, Shield, Sparkles, Star, XCircle,
} from "../../../icons";
import { DefaultUserAvatar } from "../components/primitives";
import { ActivityTimeline } from "../components/cards";
import AppCheckbox from "../../../components/AppCheckbox.vue";
import PasswordField from "../../../components/PasswordField.vue";
import { parseAppDate } from "../../../utils/datetime";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 共享来源：user/资料表单/成就负载/统计/头像URL/通知设置均由外壳持有并 provide，页面与外壳共享同一实例。
const { user, profileForm, profilePayload, stats, currentAvatarUrl, noticeSettings } = ctx;

// 三张设置面板的折叠态（资料编辑默认展开）。
const panels = reactive({ profile: true, security: false, notify: false });
const settingsRef = ref<HTMLElement | null>(null);
// 学习动态（最近动态）过长：把它的高度限制到"我的成就"卡一样高、内部滚动（仅桌面双列时）。
const achCardRef = ref<HTMLElement | null>(null);
const timelineCardRef = ref<HTMLElement | null>(null);
let heightObserver: ResizeObserver | null = null;
function syncTimelineHeight() {
  const ach = achCardRef.value;
  const timeline = timelineCardRef.value;
  if (!ach || !timeline) return;
  if (window.innerWidth <= 1024) { timeline.style.maxHeight = ""; return; }
  timeline.style.maxHeight = `${ach.offsetHeight}px`;
}
const avatarUploading = ref(false);
const studentAvatarInput = ref<HTMLInputElement | null>(null);
const passwordForm = reactive({ old_password: "", new_password: "" });
const passwordConfirm = ref("");
// 各提交/刷新的独立 loading 态：请求期间按钮转圈+禁用，防重复提交、给即时反馈。
const profileSaving = ref(false);
const passwordSaving = ref(false);
const noticeSaving = ref(false);
const refreshing = ref(false);

// 加入时间：user.created_at 归一化后按中文长日期显示；无法解析则 —。
const joinedLabel = computed(() => {
  const date = parseAppDate((user as any).created_at);
  return date ? date.toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" }) : "—";
});

// 学习概览六格：stats 的 6 项指标全部体现（含此前遗漏的连续打卡 streak_days、错题总数 wrong_count）；
// qa_count 只作普通指标，不再单独当"积分卡"。stats 是 Ref，computed 里必须走 .value。
const statItems = computed(() => [
  { icon: Clock, label: "总学习时长", value: stats.value?.study_hours ?? 0, unit: "h", tone: "teal" },
  { icon: CheckCircle, label: "课时完成率", value: stats.value?.completion_rate ?? 0, unit: "%", tone: "green" },
  { icon: Star, label: "测验正确率", value: stats.value?.accuracy ?? 0, unit: "%", tone: "amber" },
  { icon: Flame, label: "连续打卡", value: stats.value?.streak_days ?? 0, unit: "天", tone: "flame" },
  { icon: MessageCircle, label: "累计提问", value: stats.value?.qa_count ?? 0, unit: "次", tone: "ai" },
  { icon: XCircle, label: "错题总数", value: stats.value?.wrong_count ?? 0, unit: "道", tone: "rose" },
]);

// 成就固定 5 个；按 unlocked 汇总解锁数，name 恒显示（不再用 "?"）。profilePayload 是 Ref。
const achievements = computed<any[]>(() => profilePayload.value?.achievements ?? []);
const unlockedCount = computed(() => achievements.value.filter((item: any) => item.unlocked).length);

// 点"编辑资料/编辑简介"：展开资料面板并平滑滚动到设置区（否则用户可能察觉不到下方面板已展开）。
function focusProfilePanel() {
  panels.profile = true;
  void nextTick(() => settingsRef.value?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function validAvatarFile(file: File) {
  const nameOk = /\.(jpe?g|png|webp|gif)$/i.test(file.name || "");
  const typeOk = !file.type || file.type.startsWith("image/");
  if (!nameOk || !typeOk) {
    ctx.notice("warning", "请上传 JPG、PNG、WEBP 或 GIF 图片");
    return false;
  }
  if (file.size > 5 * 1024 * 1024) {
    ctx.notice("warning", "头像不能超过 5MB");
    return false;
  }
  return true;
}
async function uploadProfileAvatar(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !validAvatarFile(file)) return;
  avatarUploading.value = true;
  try {
    const form = new FormData();
    form.set("file", file);
    const data = await api.post<any>("/student/profile/avatar", form);
    ctx.applyStudentProfile(data);
    ctx.notice("success", "头像已更新");
  } catch (error) {
    ctx.notice("error", (error as Error).message);
  } finally {
    avatarUploading.value = false;
  }
}
async function saveProfile() {
  if (profileSaving.value) return;
  profileSaving.value = true;
  try {
    const data = await ctx.run<any>(() => api.patch("/student/profile", { nickname: profileForm.nickname, avatar_url: profileForm.avatar_url, bio: profileForm.bio, school: profileForm.school }), "已保存");
    if (data) ctx.applyStudentProfile(data);
  } finally { profileSaving.value = false; }
}
async function changePassword() {
  if (passwordSaving.value) return;
  if (passwordForm.new_password !== passwordConfirm.value) return ctx.notice("warning", "密码不一致");
  passwordSaving.value = true;
  try {
    const res = await ctx.run(() => api.post<{ access_token: string }>("/auth/me/password", passwordForm), "已保存");
    if (res?.access_token) setToken(res.access_token);
    if (res !== null) { Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }
  } finally { passwordSaving.value = false; }
}
async function saveNotices() {
  if (noticeSaving.value) return;
  noticeSaving.value = true;
  try {
    const settings = noticeSettings.map((item) => ({ key: item.key, enabled: Boolean(item.enabled) }));
    const data = await ctx.run<any[]>(() => api.put("/student/notifications", { settings }), "已保存");
    if (data) noticeSettings.splice(0, noticeSettings.length, ...ctx.normalizeNoticeSettings(data));
  } finally { noticeSaving.value = false; }
}
async function refreshProfile() {
  if (refreshing.value) return;
  refreshing.value = true;
  try { await ctx.loadProfile(); ctx.notice("success", "已刷新"); }
  finally { refreshing.value = false; }
}

// 进入个人中心即加载资料（原在外壳 loadActive 的 studentProfile 分支里的加载调用搬到这里）。
onMounted(() => {
  void ctx.loadProfile();
  heightObserver = new ResizeObserver(() => syncTimelineHeight());
  if (achCardRef.value) heightObserver.observe(achCardRef.value);
  window.addEventListener("resize", syncTimelineHeight);
  void nextTick(syncTimelineHeight);
});
onBeforeUnmount(() => {
  heightObserver?.disconnect();
  heightObserver = null;
  window.removeEventListener("resize", syncTimelineHeight);
});
</script>
