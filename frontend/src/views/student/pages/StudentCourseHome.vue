<template>
  <article v-if="courseHomeError" class="course-route-state error">
    <span class="course-route-icon error"><AlertTriangle :size="34" /></span>
    <h1>课程加载失败</h1>
    <p>{{ courseHomeError }}</p>
    <footer>
      <button type="button" class="btn btn-primary" @click="loadCourseHome"><RefreshCw :size="16" />重试</button>
      <button type="button" class="btn btn-secondary" @click="go('studentCourses')"><ArrowLeft :size="16" />返回课程列表</button>
    </footer>
  </article>
  <CourseRequired v-else-if="!courseHome.course" @join="ctx.openJoin" />
  <template v-else>
    <article class="course-hero" :class="{ 'has-cover': courseHome.course.cover_url }" :style="courseHeroStyle(courseHome.course)">
      <div class="course-hero__main">
        <div class="course-hero__tags">
          <button type="button" class="course-hero__back" @click="go('studentCourses')"><ArrowLeft :size="14" />所有课程</button>
          <span v-if="courseHome.course.course_code" class="course-hero__code">{{ courseHome.course.course_code }}</span>
          <span class="course-hero__term">{{ courseHome.course.term }}</span>
        </div>
        <h1 class="course-hero__title">{{ courseHome.course.name }}</h1>
        <p class="course-hero__teacher"><User :size="15" /><span>{{ courseHome.teacher?.nickname || '教师' }}</span><i>主讲教师</i></p>
        <div class="course-hero__stats">
          <div class="course-hero__stat"><Presentation :size="16" /><b>{{ courseHome.lessons?.length || 0 }}</b><span>课时</span></div>
          <div class="course-hero__stat"><Users :size="16" /><b>{{ courseHome.student_count || 0 }}</b><span>同学</span></div>
          <div class="course-hero__stat"><FolderOpen :size="16" /><b>{{ courseHome.materials?.length || 0 }}</b><span>资料</span></div>
        </div>
      </div>
      <aside class="course-hero__aside">
        <div class="course-hero__progress">
          <div class="course-hero__progress-top"><span>学习进度</span><strong>{{ courseHome.stats?.completion_rate || 0 }}%</strong></div>
          <div class="course-hero__bar"><i :style="{ width: `${Math.min(100, courseHome.stats?.completion_rate || 0)}%` }"></i></div>
        </div>
        <button class="course-hero__enter" :disabled="isLessonOpening || !latestLesson" @click="latestLesson && openLesson(Number(latestLesson.id))"><LoadingMark v-if="latestLesson && isOpeningLesson(Number(latestLesson.id))" :label="false" class="inline-loading-mark" /><Play v-else :size="18" />{{ latestLesson && isOpeningLesson(Number(latestLesson.id)) ? '正在打开' : '进入课时' }}</button>
      </aside>
    </article>
    <div class="quick-row"><QuickTile :icon="Presentation" label="课时学习" :sub="`${courseHome.lessons?.length || 0} 个课时`" @click="scrollToLessons" /><QuickTile :icon="MessageCircle" label="知识问答" sub="AI 解答" @click="go('studentQa')" /><QuickTile :icon="FolderOpen" label="课程资料" :sub="`${courseHome.materials?.length || 0} 份文件`" @click="scrollToMaterials" /><QuickTile :icon="ClipboardList" label="章节练习" sub="自选练习" @click="openQuizSelection('practice')" /></div>
    <div class="course-layout course-overview-layout">
      <article id="lesson-list" class="panel-card course-lessons-card">
        <div class="section-head"><h2><Presentation :size="18" />课时列表</h2><span class="tag">全部 {{ courseHome.lessons?.length || 0 }}</span></div>
        <div class="course-lessons-scroll">
          <LessonItem v-for="(lesson, index) in courseHome.lessons || []" :key="lesson.id" :lesson="lesson" :index="Number(index)" :loading="isOpeningLesson(Number(lesson.id))" :disabled="isLessonOpening && !isOpeningLesson(Number(lesson.id))" @open="openLesson(Number(lesson.id))" />
        </div>
      </article>
      <article class="panel-card course-data-card"><div class="section-head"><h2><BarChart2 :size="18" />我的数据</h2></div><div class="data-grid"><MiniMetric :icon="Clock" label="学习时长" :value="`${courseHome.stats?.study_hours || 0}h`" /><MiniMetric :icon="CheckCircle" label="完成进度" :value="`${courseHome.stats?.completion_rate || 0}%`" tone="success" /><MiniMetric :icon="MessageCircle" label="问答次数" :value="courseHome.stats?.qa_count || 0" tone="ai" /><MiniMetric :icon="XCircle" label="错题数" :value="courseHome.stats?.wrong_count || 0" tone="danger" /><MiniMetric :icon="Star" label="正确率" :value="`${courseHome.stats?.accuracy || 0}%`" tone="warning" /><MiniMetric :icon="Zap" label="连续打卡" :value="`${courseHome.stats?.streak_days || 0}天`" tone="warning" /></div></article>
      <article id="course-material-section" class="panel-card course-materials-card">
        <div class="section-head"><h2><FolderOpen :size="18" />课程资料</h2><button @click="materialsExpanded = !materialsExpanded">{{ materialsExpanded ? '收起' : '展开' }}</button></div>
        <div class="course-material-list">
          <MaterialRow v-for="item in baseCourseMaterials" :key="item.id" :item="item" @preview="previewMaterial" @download="downloadMaterial" />
          <Transition name="course-materials-expand">
            <div v-if="materialsExpanded && extraCourseMaterials.length" class="course-material-extra">
              <div class="course-material-extra-inner">
                <MaterialRow v-for="item in extraCourseMaterials" :key="item.id" :item="item" @preview="previewMaterial" @download="downloadMaterial" />
              </div>
            </div>
          </Transition>
        </div>
        <button v-if="extraCourseMaterials.length" class="ghost-row course-material-toggle" :class="{ expanded: materialsExpanded }" @click="materialsExpanded = !materialsExpanded"><ChevronDown :size="16" />{{ materialsExpanded ? '收起' : `展开更多` }}</button>
      </article>
    </div>
    <div class="course-qa-wide">
      <article class="ask-card"><Sparkles :size="20" /><h2>向 AI 提问</h2><form @submit.prevent="askCourseQuick"><input v-model="quickCourseQuestion" placeholder="这节课有什么不懂的..." /><button :disabled="!quickCourseQuestion.trim()"><Send :size="16" /></button></form><div class="quick-tags"><button v-for="item in courseHome.quick_questions || []" :key="item" @click="sendCourseQuick(item)">{{ item }}</button></div></article>
      <article class="panel-card recent-qa-card"><div class="section-head"><h2><MessageCircle :size="18" />最近提问</h2><button @click="go('studentQa')">全部</button></div><div v-for="item in courseHome.recent_qa || []" :key="item.id" class="qa-mini qa-mini-clickable" role="button" tabindex="0" title="查看这条问答" @click="openRecentQa(item)" @keydown.enter="openRecentQa(item)"><strong>{{ item.question }}</strong><p>{{ item.answer }}</p></div><EmptyState v-if="!(courseHome.recent_qa || []).length" text="暂无提问" /></article>
    </div>
  </template>
</template>

<script setup lang="ts">
// 课程主页（课程 hero + 快捷入口 + 课时/数据/资料 + 课程问答）。原为 StudentView 内联区块，抽为独立页面组件。
// 课程作用域数据 courseHome、课时打开/练习/资料预览下载、全局问答入口经 useStudentCtx 注入；
// 本页自持 hero 样式、课时/资料派生、资料展开与"向 AI 提问"输入等局部状态与逻辑。
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  AlertTriangle, ArrowLeft, BarChart2, CheckCircle, ChevronDown, ClipboardList, Clock,
  FolderOpen, MessageCircle, Play, Presentation, RefreshCw, Send, Sparkles, Star, User, Users, XCircle, Zap,
} from "../../../icons";
import { EmptyState, QuickTile, LessonItem, MiniMetric } from "../components/primitives";
import { CourseRequired, MaterialRow } from "../components/course";
import LoadingMark from "../../../components/LoadingMark.vue";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
const router = useRouter();
// 共享来源：课程作用域数据、课时打开态/操作、练习入口、资料预览下载、全局问答、导航与课程加载。
const {
  courseHome,
  courseHomeError,
  isLessonOpening,
  openLesson,
  isOpeningLesson,
  openQuizSelection,
  previewMaterial,
  downloadMaterial,
  globalQuestion,
  askGlobal,
  go,
  loadCourseHome,
} = ctx;

// 点击"最近提问"跳到对应问答会话页；无会话 id 时退回问答主页。
function openRecentQa(item: any) {
  const conversationId = Number(item?.conversation_id || 0);
  if (conversationId) void router.push(`/qa/${conversationId}`);
  else void go("studentQa");
}

// —— 本页私有状态与派生 ——
const materialsExpanded = ref(false);
const quickCourseQuestion = ref("");

const latestLesson = computed(() => (courseHome.value.lessons || [])[0] || null);
const baseCourseMaterials = computed(() => (courseHome.value.materials || []).slice(0, 5));
const extraCourseMaterials = computed(() => (courseHome.value.materials || []).slice(5));

function courseGradient(id = 1) { const items = ["linear-gradient(135deg,#121614,#00B8D4)", "linear-gradient(135deg,#121614,#2E7D32)", "linear-gradient(135deg,#121614,#D9A05B)", "linear-gradient(135deg,#121614,#D94925)"]; return items[id % items.length]; }
function courseHeroStyle(course?: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(135deg, rgba(18,22,20,0.82), rgba(0,184,212,0.34)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseGradient(Number(course?.id || 1)) };
}

function scrollToLessons() { document.getElementById("lesson-list")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
function scrollToMaterials() { document.getElementById("course-material-section")?.scrollIntoView({ behavior: "smooth", block: "start" }); }

async function sendCourseQuick(text: string) { quickCourseQuestion.value = text; await askCourseQuick(); }
async function askCourseQuick() { if (!quickCourseQuestion.value.trim()) return; globalQuestion.value = quickCourseQuestion.value; quickCourseQuestion.value = ""; await go("studentQa"); await askGlobal(); }

// 课程主页数据由外壳 loadActive 按路由载入并共享；组件独立挂载（或外壳尚未载入）时补拉一次。
onMounted(() => { if (!courseHome.value.course) void loadCourseHome(); });
</script>
