<template>
  <section class="tutoring-page">
    <PageTitle title="题目辅导">
      <CourseSelect v-model="selectedCourseId" :courses="courses" @reload="ctx.loadActive" @join="ctx.openJoin" />
      <span class="tag tag-ai"><Sparkles :size="12" />分步提示</span>
    </PageTitle>

    <div class="tutoring-stack">
      <section class="panel-card tutor-input">
        <div class="tutor-card-head">
          <div>
            <span class="tutor-eyebrow"><BookOpen :size="14" />题目输入</span>
            <h2>{{ selectedCourseId ? `《${courseScopeName}》` : '请先选择课程后输入题目' }}</h2>
          </div>
          <span class="tutor-status" :class="{ active: !!activeProblem }">{{ activeProblem ? '辅导中' : '待提交' }}</span>
        </div>

        <div class="seg-tabs tutor-mode-tabs">
          <button type="button" :class="{ active: problemMode === 'text' }" @click="problemMode = 'text'"><Type :size="16" />文字输入</button>
          <button type="button" :class="{ active: problemMode === 'image' }" @click="problemMode = 'image'"><Camera :size="16" />图片上传</button>
        </div>

        <div class="problem-editor-wrap">
          <textarea
            v-if="problemMode === 'text'"
            v-model="problemText"
            maxlength="500"
            placeholder="题目内容"
            class="problem-text"
          ></textarea>
          <label v-else class="image-drop" :class="{ 'ocr-scanning': ocrScanning }">
            <input ref="problemFile" type="file" accept="image/*" @change="createImageProblem" />
            <span class="upload-icon"><Camera :size="34" /></span>
            <strong>{{ ocrScanning ? '正在识别题目' : '上传题目截图' }}</strong>
          </label>
        </div>

        <div class="tutor-input-meta">
          <span>{{ problemMode === 'text' ? `${problemText.length} / 500字` : '图片模式' }}</span>
          <span>{{ selectedCourseId ? `《${courseScopeName}》` : '请先选择课程' }}</span>
        </div>

        <div v-if="activeProblem" class="knowledge-box">
          <Sparkles :size="14" />
          <strong>识别知识点</strong>
          <span v-for="item in activeProblem.knowledge_points || []" :key="item" class="tag tag-primary">{{ item }}</span>
          <span v-if="!(activeProblem.knowledge_points || []).length" class="tag">待分析</span>
        </div>

        <button
          type="button"
          class="btn btn-ai full tutor-submit-btn"
          :data-loading="problemSubmitting || ocrScanning"
          :disabled="problemMode === 'text' ? (problemSubmitting || !selectedCourseId || !problemText.trim()) : (ocrScanning || !selectedCourseId)"
          @click="problemMode === 'text' ? createTextProblem() : problemFile?.click()"
        >
          <Sparkles :size="16" />{{ problemMode === 'text' ? '开始辅导' : '上传并识别' }}
        </button>
      </section>

      <section class="panel-card guide-card">
        <div class="section-head">
          <h2><Sparkles :size="18" />{{ activeProblem ? '查看解析' : '等待题目输入' }}</h2>
          <span v-if="activeProblem" class="tag tag-success">3步引导</span>
        </div>

        <article v-if="activeProblem" class="active-problem-card">
          <span>当前题目</span>
          <p>{{ activeProblem.corrected_text || activeProblem.ocr_text || activeProblem.raw_text || problemText || '已提交题目' }}</p>
        </article>

        <EmptyGuide v-if="!activeProblem" />
        <div v-else class="guide-step-list">
          <GuideStep v-for="level in [1, 2, 3]" :key="level" :level="level" :data="guidance[level]" :open="guideOpen[level]" :loading="guideLoading[level]" @toggle="toggleGuide(level)" @load="loadGuidance(level)" />
        </div>
      </section>
    </div>

    <HistoryStrip title="历史辅导记录" :items="problemHistory" @pick="selectProblem" />
  </section>
</template>

<script setup lang="ts">
// 题目辅导页（拍照/输入题目 → AI 分步提示）。原为 StudentView 内联区块，抽为独立页面组件。
// 共享的当前课程/请求助手经 useStudentCtx 注入；本页自持题目/引导等局部状态与逻辑。
import { onMounted, reactive, ref, watch } from "vue";
import { api } from "../../../api/client";
import { BookOpen, Camera, Sparkles, Type } from "../../../icons";
import { PageTitle, EmptyGuide, GuideStep } from "../components/primitives";
import { HistoryStrip } from "../components/cards";
import { CourseSelect } from "../components/course";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 顶层 ref 绑定，模板中自动解包；v-model 直接写回共享的 selectedCourseId。
const { selectedCourseId, courses, courseScopeName } = ctx;

const problemMode = ref<"text" | "image">("text");
const problemText = ref("");
const problemFile = ref<HTMLInputElement | null>(null);
const problemSubmitting = ref(false);
const ocrScanning = ref(false);
const activeProblem = ref<any | null>(null);
const problemHistory = ref<any[]>([]);
const guidance = reactive<Record<number, any>>({});
const guideOpen = reactive<Record<number, boolean>>({ 1: true, 2: false, 3: false });
const guideLoading = reactive<Record<number, boolean>>({ 1: false, 2: false, 3: false });

function resetGuidanceState() {
  Object.keys(guidance).forEach((key) => delete guidance[Number(key)]);
  guideOpen[1] = true;
  guideOpen[2] = false;
  guideOpen[3] = false;
}
async function loadProblemHistory() {
  problemHistory.value = (await ctx.run<any[]>(() => api.get("/tutoring/history", { course_id: ctx.selectedCourseId.value || undefined }))) || [];
}
async function createTextProblem() {
  if (!problemText.value.trim()) {
    ctx.notice("warning", "请先输入题目");
    return;
  }
  problemSubmitting.value = true;
  try {
    activeProblem.value = await ctx.run<any>(() => api.post("/tutoring/problems/text", { course_id: ctx.selectedCourseId.value, text: problemText.value }), "已提交");
    resetGuidanceState();
    await loadProblemHistory();
    if (activeProblem.value) await loadGuidance(1);
  } finally {
    problemSubmitting.value = false;
  }
}
async function createImageProblem(event: Event) {
  const file = ((event.target as HTMLInputElement).files || [])[0];
  if (!file) return;
  if (!ctx.selectedCourseId.value) {
    ctx.notice("warning", "请先选择课程");
    (event.target as HTMLInputElement).value = "";
    return;
  }
  const form = new FormData();
  form.set("course_id", String(ctx.selectedCourseId.value));
  form.set("file", file);
  ocrScanning.value = true;
  try {
    activeProblem.value = await ctx.run<any>(() => api.post("/tutoring/problems/image", form), "已识别");
    problemText.value = activeProblem.value?.ocr_text || "";
    resetGuidanceState();
    await loadProblemHistory();
  } finally {
    ocrScanning.value = false;
    (event.target as HTMLInputElement).value = "";
  }
}
function selectProblem(item: any) {
  activeProblem.value = item;
  problemText.value = item.corrected_text || item.ocr_text || item.raw_text || "";
  resetGuidanceState();
}
async function loadGuidance(level: number) {
  if (!activeProblem.value || guideLoading[level]) return;
  // 首次展开要请求 AI 分步提示（数秒）：期间给该步 loading，避免“点了没反应”的空窗。
  guideLoading[level] = true;
  try {
    const data = await ctx.run(() => api.get(`/tutoring/problems/${activeProblem.value.id}/guidance`, { level }));
    if (data) { guidance[level] = data; guideOpen[level] = true; }
  } finally {
    guideLoading[level] = false;
  }
}
async function toggleGuide(level: number) {
  if (!guidance[level]) await loadGuidance(level);
  else guideOpen[level] = !guideOpen[level];
}

// 换课时清空本页局部状态并重拉历史（原 resetCourseScopedState 里对辅导态的清理搬到这里）。
watch(ctx.selectedCourseId, () => {
  activeProblem.value = null;
  problemText.value = "";
  resetGuidanceState();
  void loadProblemHistory();
});

onMounted(loadProblemHistory);
</script>
