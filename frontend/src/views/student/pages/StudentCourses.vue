<template>
  <PageTitle title="我的课程" :sub="`共 ${courses.length} 门课程`"><button class="btn btn-primary" @click="openJoin"><Plus :size="16" />加入课程</button></PageTitle>
  <div class="course-tools"><div class="pretty-input"><Search :size="16" /><input v-model="courseKeyword" placeholder="搜索课程名称" /></div><SelectMenu v-model="termFilter" :items="termOptions" /></div>
  <div class="underline-tabs"><button :class="{ active: courseTab === 'active' }" @click="courseTab = 'active'"><BookOpen :size="16" />在学中({{ activeCourses.length }})</button><button :class="{ active: courseTab === 'done' }" @click="courseTab = 'done'"><CheckCircle :size="16" />已完成({{ doneCourses.length }})</button></div>
  <div class="student-course-grid">
    <article v-for="course in pagedCourses" :key="course.id" class="student-course-card">
      <header class="course-art" :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)">
        <span class="course-term-pill">{{ course.term || '本学期' }}</span>
        <strong v-if="!course.cover_url" class="course-cover-text">{{ courseCoverText(course) }}</strong>
        <DropdownMenu :items="courseMenuItems" @select="handleCourseMenu($event, course)" />
      </header>
      <section class="course-card-body">
        <div class="course-card-title">
          <h2>{{ course.name }}</h2>
          <p><User :size="14" />{{ course.teacher?.nickname || '课程教师' }}</p>
        </div>
        <div class="course-progress-panel">
          <div>
            <span>学习进度</span>
            <strong>{{ course.progress_percent || 0 }}%</strong>
          </div>
          <AppProgress :value="course.progress_percent || 0" />
        </div>
        <div class="course-meta">
          <span><BookOpen :size="14" />已学 {{ course.studied_lessons || 0 }}/{{ course.lesson_total || 0 }} 课时</span>
          <span><Clock :size="14" />{{ course.last_lesson ? relativeTime(course.last_progress?.updated_at) : '未开始' }}</span>
        </div>
        <div class="course-card-stats">
          <span><MessageCircle :size="14" /><b>{{ course.qa_count || 0 }}</b>问答</span>
          <span><XCircle :size="14" /><b>{{ course.wrong_count || 0 }}</b>错题</span>
          <span><Users :size="14" /><b>{{ course.student_count || 0 }}</b>同学</span>
        </div>
        <footer class="course-card-actions">
          <button type="button" class="btn btn-primary" @click="openCourse(course.id)"><Play :size="16" />{{ (course.progress_percent || 0) > 0 ? '继续学习' : '开始学习' }}</button>
          <button type="button" class="course-card-link" @click="handleCourseMenu('qa', course)"><MessageCircle :size="15" />问答</button>
        </footer>
      </section>
    </article>
  </div>
  <EmptyState v-if="!filteredCourses.length" text="暂无课程" />
  <nav v-if="coursesPageCount > 1" class="course-pager">
    <button class="btn btn-ghost btn-sm" :disabled="coursesPage <= 1" @click="coursesPage = Math.max(1, coursesPage - 1)"><ChevronLeft :size="14" />上一页</button>
    <span class="course-pager-info">{{ coursesPage }} / {{ coursesPageCount }} · 共 {{ filteredCourses.length }} 门课程</span>
    <button class="btn btn-ghost btn-sm" :disabled="coursesPage >= coursesPageCount" @click="coursesPage = Math.min(coursesPageCount, coursesPage + 1)">下一页<ChevronRight :size="14" /></button>
  </nav>
</template>

<script setup lang="ts">
// 我的课程页（课程卡片网格 + 学期筛选 + 在学/已完成分页）。原为 StudentView 内联区块，抽为独立页面组件。
// 课程列表 courses、打开课程/封面样式/卡片菜单等跨页共享逻辑经 useStudentCtx 注入；
// 本页自持搜索/筛选/分页等局部状态。数据加载仍由外壳 loadActive（active==='studentCourses' 时 loadCourses）负责。
import { computed, ref, watch } from "vue";
import { BookOpen, CheckCircle, ChevronLeft, ChevronRight, Clock, MessageCircle, Play, Plus, Search, User, Users, XCircle } from "../../../icons";
import { PageTitle, EmptyState } from "../components/primitives";
import SelectMenu from "../../../components/SelectMenu";
import DropdownMenu from "../../../components/DropdownMenu";
import AppProgress from "../../../components/AppProgress.vue";
import { relativeTime } from "../../../utils/datetime";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 共享：课程列表 + 打开课程/封面样式/封面文案/卡片菜单/加入课程（由外壳持有并 provide）。
const { courses, openCourse, courseCoverStyle, courseCoverText, handleCourseMenu, openJoin } = ctx;

// 本页私有：搜索/学期筛选/在学-已完成分页态。
const courseKeyword = ref("");
const termFilter = ref("");
const courseTab = ref<"active" | "done">("active");
const coursesPage = ref(1);
const COURSES_PER_PAGE = 9; // 3 列 × 3 行，满一页翻页
const courseMenuItems = [{ label: "课程详情", value: "detail" }, { label: "问答记录", value: "qa" }, { label: "分享课程码", value: "share" }, { label: "退出课程", value: "leave", danger: true }];

const termOptions = computed(() => [{ label: "全部学期", value: "" }, ...Array.from(new Set(courses.value.map((course) => course.term))).filter(Boolean).map((term: any) => ({ label: term, value: term }))]);
const activeCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) < 100));
const doneCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) >= 100));
const filteredCourses = computed(() => (courseTab.value === "active" ? activeCourses.value : doneCourses.value).filter((course) => (!courseKeyword.value || course.name.includes(courseKeyword.value)) && (!termFilter.value || course.term === termFilter.value)));
const coursesPageCount = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / COURSES_PER_PAGE)));
const pagedCourses = computed(() => {
  const start = (coursesPage.value - 1) * COURSES_PER_PAGE;
  return filteredCourses.value.slice(start, start + COURSES_PER_PAGE);
});
// 课程数变化（加入/退出/切库）后夹住页码；筛选/搜索/切 Tab 时回到第 1 页。
watch(filteredCourses, (rows) => {
  const maxPage = Math.max(1, Math.ceil(rows.length / COURSES_PER_PAGE));
  if (coursesPage.value > maxPage) coursesPage.value = maxPage;
});
watch([courseTab, courseKeyword, termFilter], () => { coursesPage.value = 1; });
</script>
