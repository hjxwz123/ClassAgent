<template>
  <div class="exam-answer-page">
    <QuizAnswerView
      v-if="quizDetail"
      :key="viewKey"
      :quiz="quizDetail"
      :answers="quizAnswers"
      :attempt="attempt"
      :submitting="submitting"
      :retaking="retaking"
      :draft="resumeDraft"
      :draft-key="draftKey"
      @answer="setAnswer"
      @submit="submit"
      @exit="exit"
      @retake="onRetake"
      @go-wrong-book="onGoWrongBook"
    />
    <PageLoader v-else />
  </div>
</template>

<script setup lang="ts">
// 独立全屏做题路由 /quizzes/:quizId/answer —— 做题/解析从 StudentView 的 Teleport 覆盖层升级为真实路由。
// 一套题一个 URL：作答、续做（草稿恢复）、看解析（已交卷或 ?attempt=）都在这里，交卷/退出/重做走路由跳转。
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, ApiError } from "../../api/client";
import PageLoader from "../../components/PageLoader.vue";
import type { User } from "../../types";
import { QuizAnswerView } from "./components/QuizAnswerView";
import "../../styles/student/quiz.css";

type NoticeAction = { label: string; onClick: () => void };
const props = defineProps<{ user: User }>();
const emit = defineEmits<{ notice: [type: "success" | "warning" | "error" | "info", text: string, action?: NoticeAction]; logout: []; authed: [user: User] }>();
const route = useRoute();
const router = useRouter();

const quizId = computed(() => Number(route.params.quizId || 0));
const quizDetail = ref<any | null>(null);
const quizAnswers = reactive<Record<number, any>>({});
const attempt = ref<any | null>(null);
const resumeDraft = ref<any | null>(null);
const submitting = ref(false);
const retaking = ref(false);
const draftKey = computed(() => (quizId.value ? `ca_quiz_draft_v1_${props.user.id}_${quizId.value}` : ""));
const viewKey = computed(() => `${quizId.value}-${attempt.value?.id || attempt.value?.attempt?.id || 0}`);

async function run<T>(task: () => Promise<T>, ok?: string): Promise<T | null> {
  try {
    const data = await task();
    if (ok) emit("notice", "success", ok);
    return data;
  } catch (error) {
    emit("notice", "error", (error as Error).message);
    return null;
  }
}

function readDraft(id: number): any | null {
  try {
    const raw = localStorage.getItem(`ca_quiz_draft_v1_${props.user.id}_${id}`);
    if (!raw) return null;
    const data = JSON.parse(raw);
    return data && typeof data === "object" && data.answers && typeof data.answers === "object" ? data : null;
  } catch { return null; }
}
function clearDraft(id: number) {
  try { localStorage.removeItem(`ca_quiz_draft_v1_${props.user.id}_${id}`); } catch { /* 忽略存储异常 */ }
}

function backToList() {
  void router.replace({ path: "/quizzes" });
}

async function viewAttempt(attemptId: number) {
  const detail = await run<any>(() => api.get(`/learning/attempts/${attemptId}`));
  if (!detail) { backToList(); return; }
  Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]);
  quizDetail.value = {
    quiz: detail.quiz || detail.attempt?.quiz || {},
    questions: (detail.answers || []).map((row: any) => row.question).filter(Boolean),
  };
  resumeDraft.value = null;
  attempt.value = detail;
}

async function load() {
  const id = quizId.value;
  if (!id) { backToList(); return; }
  const attemptQuery = Number(route.query.attempt || 0);
  if (attemptQuery > 0) { await viewAttempt(attemptQuery); return; }
  const draft = readDraft(id);
  if (!draft) {
    // 已交过卷 → 直接看解析（后端一卷一次作答）。
    const attempts = await run<any[]>(() => api.get(`/learning/quizzes/${id}/attempts`));
    if (attempts?.length) { await viewAttempt(attempts[0].id); return; }
  }
  const detail = await run<any>(() => api.get(`/learning/quizzes/${id}`));
  if (!detail) { backToList(); return; }
  quizDetail.value = detail;
  Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]);
  if (draft?.answers) {
    const validIds = new Set((detail.questions || []).map((item: any) => Number(item.id)));
    Object.entries(draft.answers).forEach(([key, value]) => {
      if (validIds.has(Number(key))) quizAnswers[Number(key)] = value;
    });
  }
  resumeDraft.value = draft;
  attempt.value = null;
  if (draft) emit("notice", "info", "已恢复上次作答进度");
}

function setAnswer(questionId: number, answer: any) { quizAnswers[questionId] = answer; }

async function submit(durationSeconds?: number) {
  if (!quizDetail.value || submitting.value) return;
  submitting.value = true;
  try {
    const id = Number(quizDetail.value.quiz.id);
    const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer }));
    const duration = Number.isFinite(durationSeconds) ? Math.max(0, Math.round(Number(durationSeconds))) : undefined;
    let result: any = null;
    try {
      result = await api.post(`/learning/quizzes/${id}/submit`, { answers, duration_seconds: duration });
    } catch (error) {
      // 网络重试/并发把同一卷交了两次：后端 400"已提交"。直接带去已有成绩单，别让用户困在答题页反复报错。
      if (error instanceof ApiError && error.status === 400 && String(error.message).includes("已提交")) {
        clearDraft(id);
        const attempts = await run<any[]>(() => api.get(`/learning/quizzes/${id}/attempts`));
        if (attempts?.length) { await viewAttempt(attempts[0].id); return; }
      }
      emit("notice", "error", (error as Error).message);
      return;
    }
    if (!result) return;
    emit("notice", "success", "已交卷");
    attempt.value = result;
    clearDraft(id);
  } finally {
    submitting.value = false;
  }
}

function exit() {
  // QuizAnswerView 在 emit exit 前已把草稿落盘，这里直接回列表。
  backToList();
}

async function onRetake(mode: "full" | "wrong") {
  if (retaking.value) return;
  const id = Number(quizDetail.value?.quiz?.id || attempt.value?.quiz?.id || 0);
  const attemptId = Number(attempt.value?.attempt?.id || attempt.value?.id || 0) || undefined;
  if (!id) return;
  retaking.value = true;
  try {
    // 一卷只能交一次是后端约束；"再练"克隆新卷，历史成绩完整保留。用 replace 让浏览器返回不落回已交的旧卷。
    const clone = await run<any>(() => api.post(`/learning/quizzes/${id}/retake`, { mode, attempt_id: mode === "wrong" ? attemptId : undefined }));
    if (!clone) return;
    if (!clone.id) { emit("notice", "info", "重做卷生成中，稍后可在测验列表打开"); return; }
    void router.replace({ path: `/quizzes/${clone.id}/answer` });
  } finally {
    retaking.value = false;
  }
}

function onGoWrongBook() {
  void router.push({ path: "/wrong-book" });
}

onMounted(load);
</script>
