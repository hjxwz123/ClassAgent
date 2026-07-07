<template>
  <article class="hello-card">
    <div class="hello-main">
      <span class="hello-badge"><Sun :size="26" /></span>
      <section>
        <h1>{{ greeting }}，{{ user.nickname }}</h1>
        <p class="hello-meta"><i class="hello-dot"></i>{{ todayText }}<template v-if="currentTermLabel"> · {{ currentTermLabel }}</template></p>
      </section>
    </div>
    <div class="hello-glance">
      <div class="hello-stat"><BookOpen :size="18" /><b>{{ courses.length }}</b><small>门课程</small></div>
      <div class="hello-stat"><Flame :size="18" /><b>{{ stats.streak_days || 0 }}</b><small>连续天数</small></div>
      <div v-if="todayTasks.length" class="hello-stat"><CalendarCheck :size="18" /><b>{{ doneTasks }}/{{ todayTasks.length }}</b><small>今日任务</small></div>
      <div v-else class="hello-stat"><Clock :size="18" /><b>{{ stats.study_hours || 0 }}h</b><small>累计学习</small></div>
    </div>
  </article>
  <article class="today-plan" :class="{ 'is-empty': !todayTasks.length }">
    <CalendarCheck :size="20" />
    <div class="today-plan-copy">
      <strong>今日计划</strong>
      <small>{{ todayTasks.length ? todayPlanSummary : '今天还没有学习安排，点击制定计划后可在首页直接查看和打卡' }}</small>
    </div>
    <span v-if="todayTasks.length" class="today-plan-count">{{ doneTasks }}/{{ todayTasks.length }}</span>
    <AppProgress v-if="todayTasks.length" :value="todayDoneRate" />
    <button @click="go('studentPlans')">{{ todayTasks.length ? '查看' : '制定计划' }}</button>
  </article>
  <article class="continue-card">
    <div class="continue-cover" :style="courseCoverStyle(continueLesson?.course || activeCourse)"><Presentation :size="32" /><span>P{{ continueProgressPage }}</span></div>
    <section v-if="continueLesson">
      <span class="tag tag-ai"><Sparkles :size="12" />接续上次</span>
      <h2>{{ continueLesson.lesson.title }}</h2>
      <p>第 {{ continueProgressPage }} 页 / 共 {{ continueLesson.lesson.page_count || 1 }} 页</p>
      <AppProgress :value="continueProgress" />
      <small>{{ continueTime }}</small>
      <button class="btn btn-primary" :disabled="isLessonOpening" @click="openLesson(continueLesson.lesson.id)"><LoadingMark v-if="isOpeningLesson(continueLesson.lesson.id)" :label="false" class="inline-loading-mark" /><Play v-else :size="16" />{{ isOpeningLesson(continueLesson.lesson.id) ? '正在打开' : '继续学习' }}</button>
    </section>
    <section v-else class="empty-continue"><BookOpen :size="42" /><h2>还没有学习</h2><button class="btn btn-primary" @click="go('studentCourses')">浏览课程</button></section>
  </article>
  <div class="home-grid">
    <article class="panel-card">
      <div class="section-head"><h2><BookOpen :size="18" />我的课程</h2><button @click="go('studentCourses')">查看全部</button></div>
      <div v-if="courses.length" class="home-course-strip" :class="{ 'single-course': courses.length === 1 }">
        <button v-for="course in courses" :key="course.id" class="home-course" @click="openCourse(course.id)">
          <span :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)">
            <strong v-if="!course.cover_url" class="course-cover-mini-text">{{ courseCoverText(course) }}</strong>
          </span>
          <div><strong>{{ course.name }}</strong><small>{{ course.teacher?.nickname || '教师' }} · {{ course.term }}</small><AppProgress :value="course.progress_percent || 0" /><em>{{ course.progress_percent || 0 }}%</em></div>
        </button>
      </div>
      <button class="join-dashed" @click="openJoin()"><Plus :size="16" />加入新课程</button>
    </article>
    <article class="panel-card">
      <div class="section-head"><h2><BarChart2 :size="18" />我的学习</h2><button @click="go('studentProfile')">学习报告</button></div>
      <div class="rings"><RingBlock label="累计学习" :value="hourTargetRate" :text="`${stats.study_hours || 0}h`" sub="累计时长" /><RingBlock label="完成率" :value="stats.completion_rate || 0" :text="`${stats.completion_rate || 0}%`" sub="课时" tone="success" /><RingBlock label="正确率" :value="stats.accuracy || 0" :text="`${stats.accuracy || 0}%`" sub="练习" tone="ai" /></div>
      <div class="week-check"><span v-for="item in weekDays" :key="item.label" :class="{ done: item.done, today: item.today }">{{ item.label }}</span></div>
      <div class="streak"><Flame :size="16" />连续 {{ stats.streak_days || 0 }} 天</div>
    </article>
  </div>
  <article class="home-ai-recommend-card" :class="{ 'is-empty': !hasJoinedCourses }">
    <div class="home-ai-rec-left">
      <div class="home-ai-rec-header">
        <div class="home-ai-icon-wrap">
          <Sparkles v-if="hasJoinedCourses" :size="24" />
          <BookOpen v-else :size="24" />
        </div>
        <h2>{{ hasJoinedCourses ? 'AI 今日推荐' : '加入课程后生成推荐' }}</h2>
      </div>
      <p class="home-ai-rec-content" v-if="hasJoinedCourses">
        {{ studentRecommendationText }}
      </p>
      <p class="home-ai-rec-content" v-else>
        AI 今日推荐会基于你加入的课程、学习进度、今日计划和错题薄弱点生成。当前账号还没有课程数据，所以不会生成课程学习建议。
      </p>
      <div class="home-ai-rec-footer">
        <div class="home-data-tag">
          <Sparkles :size="14" />{{ hasJoinedCourses ? '基于你的学习数据生成' : '等待课程数据' }}
        </div>
        <button class="home-refresh-btn" :data-loading="recRefreshing" :disabled="recRefreshing" @click="hasJoinedCourses ? refreshRecommendation() : openJoin()">
          <LoadingMark v-if="hasJoinedCourses && recRefreshing" :label="false" class="inline-loading-mark" />
          <RefreshCw v-else-if="hasJoinedCourses" :size="14" />
          <Plus v-else :size="14" />
          {{ hasJoinedCourses ? '刷新建议' : '加入课程' }}
        </button>
      </div>
    </div>

    <div class="home-ai-rec-actions">
      <button class="home-action-task-card" @click="openHomeRecommendedLesson">
        <div class="home-task-info">
          <span class="home-task-type"><BookOpen :size="14" />{{ hasJoinedCourses ? '推荐课时' : '课程入口' }}</span>
          <span class="home-task-title">{{ homeRecommendedLessonTitle }}</span>
        </div>
        <div class="home-task-arrow"><ArrowRight :size="16" /></div>
      </button>
      <button class="home-action-task-card" @click="openHomeRecommendedPractice">
        <div class="home-task-info">
          <span class="home-task-type"><Pencil :size="14" />{{ hasJoinedCourses ? '推荐练习' : '练习入口' }}</span>
          <span class="home-task-title">{{ homeRecommendedPracticeTitle }}</span>
        </div>
        <div class="home-task-arrow"><ArrowRight :size="16" /></div>
      </button>
    </div>
  </article>

  <article class="home-activity-card">
    <div class="home-ac-header">
      <div class="home-ac-title">
        <Clock :size="24" />
        学习动态
      </div>
      <button class="home-ac-view-all" @click="go('studentProfile')">查看全部记录 <ArrowRight :size="14" /></button>
    </div>
    <div v-if="homeActivityItems.length" class="home-activity-list">
      <div v-for="item in homeActivityItems" :key="item.key" class="home-activity-item">
        <div class="home-ac-icon-wrapper" :class="item.tone">
          <component :is="item.icon" :size="20" />
        </div>
        <div class="home-ac-content-wrap">
          <div class="home-ac-meta">
            <span class="home-ac-action-name">{{ item.action }}</span>
            <span class="home-ac-time">{{ item.timeText }}</span>
          </div>
          <div class="home-ac-detail" :class="{ quote: item.quote }">{{ item.detail }}</div>
          <div v-if="item.progress !== null" class="home-mini-progress-bar">
            <div class="home-mp-track">
              <div class="home-mp-fill" :style="{ width: `${item.progress}%` }"></div>
            </div>
            <span class="home-mp-text">{{ item.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="home-activity-empty">
      <BookOpen :size="28" />
      <span>{{ hasJoinedCourses ? '暂无学习动态' : '加入课程后开始记录学习动态' }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
// 学生端首页（问候/今日计划/接续学习/我的课程与学习/AI 推荐/学习动态）。
// 原为 StudentView 内联区块，抽为独立页面组件，模板逐字保留，仅把共享来源换成 ctx。
// 首页只读共享看板态（dashboard/stats/todayTasks/…）派生展示，看板的加载仍由外壳负责，
// 因此本组件不含生命周期加载逻辑，随 ctx 里的响应式来源自动更新。
import { computed, ref } from "vue";
import { ArrowRight, BarChart2, BookOpen, CalendarCheck, ClipboardList, Clock, Flame, MessageCircle, Pencil, Play, Plus, Presentation, RefreshCw, Sparkles, Sun } from "../../../icons";
import { relativeTime } from "../../../utils/datetime";
import { RingBlock } from "../components/primitives";
import AppProgress from "../../../components/AppProgress.vue";
import LoadingMark from "../../../components/LoadingMark.vue";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 共享态经 ctx 注入：user 为当前用户；courses/stats/todayTasks/doneTasks/checkinDays/hasJoinedCourses
// 为外壳持有的响应式来源；dashboard 为外壳看板原始态（stats/todayTasks 亦由其派生），首页只读它做本地派生；
// go/openCourse/openLesson/openJoin/openQuizSelection/courseCoverStyle/courseCoverText/isOpeningLesson 为外壳函数。
const {
  user,
  courses,
  stats,
  todayTasks,
  doneTasks,
  checkinDays,
  hasJoinedCourses,
  selectedCourseId,
  dashboard,
  go,
  openCourse,
  openLesson,
  isLessonOpening,
  isOpeningLesson,
  openJoin,
  openQuizSelection,
  courseCoverStyle,
  courseCoverText,
} = ctx;

// context.ts 把 loadDashboard 收窄为无参；外壳实现接受 { refreshRecommendation } 选项，
// 首页“刷新建议”按钮需透传该选项，这里本地放宽签名（运行时仍指向同一实现）。
const loadDashboard: (options?: { refreshRecommendation?: boolean }) => Promise<void> = ctx.loadDashboard;

// “刷新建议”触发 AI 重新生成推荐（耗时）：加 loading 态防连点，并在完成后给成功提示。
const recRefreshing = ref(false);
async function refreshRecommendation() {
  if (recRefreshing.value) return;
  recRefreshing.value = true;
  try { await loadDashboard({ refreshRecommendation: true }); ctx.notice("success", "已刷新推荐"); }
  finally { recRefreshing.value = false; }
}

// 本地日期键（yyyy-mm-dd，按本地时区），用于把打卡日与本周格对齐。
function localDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function normalizePercent(value: unknown) { const percent = Number.parseFloat(String(value ?? "").replace("%", "")); return Number.isFinite(percent) ? Math.max(0, Math.min(100, Math.round(percent))) : null; }

const todayDoneRate = computed(() => todayTasks.value.length ? Math.round(doneTasks.value / todayTasks.value.length * 100) : 0);
const nextTodayTask = computed(() => todayTasks.value.find((task: any) => task.status !== "done") || todayTasks.value[0] || null);
const todayPlanSummary = computed(() => {
  const task = nextTodayTask.value;
  if (!task) return "";
  const title = String(task.title || "学习任务").trim();
  const minutes = Number(task.estimated_minutes || 0);
  const timeText = Number.isFinite(minutes) && minutes > 0 ? `${minutes}分钟` : (task.task_type || "学习");
  return `${task.status === "done" ? "已完成" : "待完成"}：${title} · ${timeText}`;
});
const continueLesson = computed(() => dashboard.value.continue_learning || null);
const continueProgress = computed(() => continueLesson.value?.progress?.progress_percent || 0);
const continueProgressPage = computed(() => continueLesson.value?.progress?.current_page || 1);
const continueTime = computed(() => continueLesson.value?.progress?.updated_at ? `上次学习：${relativeTime(continueLesson.value.progress.updated_at)}` : "从第一节开始");
const studentRecommendationText = computed(() => dashboard.value.recommendation?.text || "建议选择一门课程完成一个课时，并用练习检查掌握情况。");
const hourTargetRate = computed(() => Math.min(100, Math.round((stats.value.study_hours || 0) / 5 * 100)));
const activities = computed(() => dashboard.value.activities || []);
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" }));
// 学期信息来源于后端课程的 term 字段，没有真实学期起止日期时只展示学期名，不再编造“距结束 X 天”的假倒计时。
const currentTermLabel = computed(() => {
  const terms = Array.from(new Set(courses.value.map((course) => String(course.term || "").trim()).filter(Boolean)));
  return terms.length === 1 ? terms[0] : "";
});
const activeCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value) || courses.value[0] || null);
const homeRecommendedLesson = computed(() => dashboard.value.recommendation?.lesson || continueLesson.value || null);
const homeRecommendedLessonTitle = computed(() => {
  if (!hasJoinedCourses.value) return "输入课程码加入课程";
  return homeRecommendedLesson.value?.lesson?.title || activeCourse.value?.last_lesson?.title || "暂无推荐课时";
});
const homeRecommendedPracticeTitle = computed(() => {
  if (!hasJoinedCourses.value) return "加入后查看推荐练习";
  const weakPoint = dashboard.value.recommendation?.weak_points?.[0]?.name;
  return weakPoint ? `${weakPoint}专项练习 (10题)` : "章节巩固练习 (10题)";
});
const homeActivityItems = computed(() => activities.value.map((item: any, index: number) => {
  const type = item?.type || "activity";
  const rawTitle = item?.title || "学习记录";
  const meta = item?.meta || "";
  const progress = type === "lesson" ? normalizePercent(meta) : null;
  if (type === "qa") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: MessageCircle, tone: "ai", action: "向 AI 发起提问", detail: rawTitle, quote: true, progress: null, timeText: relativeTime(item?.time) };
  }
  if (type === "lesson") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: Play, tone: "learning", action: "学习课时", detail: rawTitle.replace(/^学习\s*/, ""), quote: false, progress, timeText: relativeTime(item?.time) };
  }
  if (type === "quiz") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: ClipboardList, tone: "learning", action: "提交练习", detail: `${rawTitle.replace(/^提交\s*/, "")}${meta ? ` · ${meta}` : ""}`, quote: false, progress: null, timeText: relativeTime(item?.time) };
  }
  return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: Sparkles, tone: "ai", action: type === "tutoring" ? "AI 题目辅导" : "学习记录", detail: meta ? `${rawTitle} · ${meta}` : rawTitle, quote: false, progress: null, timeText: relativeTime(item?.time) };
}));
const weekDays = computed(() => {
  const now = new Date();
  // Monday(0) .. Sunday(6) index of today; getDay() => 0=Sun..6=Sat
  const todayIndex = (now.getDay() + 6) % 7;
  // Date of this week's Monday at local midnight
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - todayIndex);
  return ["一", "二", "三", "四", "五", "六", "日"].map((label, index) => {
    const dayDate = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + index);
    const iso = localDateKey(dayDate);
    return { label, done: checkinDays.value.includes(iso), today: index === todayIndex };
  });
});

async function openHomeRecommendedLesson() {
  if (!hasJoinedCourses.value) { openJoin(); return; }
  const lessonId = homeRecommendedLesson.value?.lesson?.id || activeCourse.value?.last_lesson?.id;
  if (lessonId) { await openLesson(Number(lessonId)); return; }
  await go("studentCourses");
}
async function openHomeRecommendedPractice() {
  if (!hasJoinedCourses.value) { openJoin(); return; }
  await openQuizSelection("practice");
}
</script>
