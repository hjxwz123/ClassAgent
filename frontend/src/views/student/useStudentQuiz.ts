// 学生端「练习与测验」子系统：课程测验 / 自选章节 AI 组卷 / 生成任务占位卡 / 错题本 / 错题重练。
// 原为 StudentView.vue 内联，逐字抽出为独立 composable 以缩短主文件；模板仍留在 StudentView，
// 由其解构本 composable 的返回值使用（调用点不变）。行为与原实现保持逐字一致。
// 依赖外壳的导航/请求/通知等能力经 deps 注入；api 与 useStudentSearch 一样直接 import（同一单例）。
import { computed, ref, watch, type Ref } from "vue";
import type { Router, RouteLocationNormalizedLoaded } from "vue-router";
import { api } from "../../api/client";
import { pollGenerationProgress } from "../../composables/useGenerationProgress";
import { useGenerationTasksStore } from "../../stores/generationTasks";
import type { Quiz, User as UserType } from "../../types";
import { timestampMs } from "../../utils/datetime";
import { statusText } from "../../utils/quiz";

type QuizDeps = {
  // run() 包裹请求并统一弹提示：成功可选 ok 文案，异常走 notice("error")；返回数据或 null。
  run: <T>(task: () => Promise<T>, ok?: string) => Promise<T | null>;
  // 只用到 "notice" 一种事件；外壳 defineEmits 的 emit（含 logout/notice/authed 重载）可赋值给此单签名。
  emit: (
    event: "notice",
    type: "success" | "warning" | "error" | "info",
    text: string,
    action?: { label: string; onClick: () => void }
  ) => void;
  router: Router;
  route: RouteLocationNormalizedLoaded;
  active: Ref<string>;
  go: (key: string) => Promise<void>;
  selectedCourseId: Ref<number>;
  weakPoints: Ref<any[]>;
  courseHome: Ref<any>;
  selectedChapterId: Ref<number | null>;
  loadCourseHome: () => Promise<void>;
  loadNotifications: (silent?: boolean) => Promise<void>;
  user: UserType;
};

export function useStudentQuiz(deps: QuizDeps) {
  const {
    run, emit, router, route, active, go,
    selectedCourseId, weakPoints, courseHome, selectedChapterId,
    loadCourseHome, loadNotifications, user,
  } = deps;
  const generation = useGenerationTasksStore();

  // ─── 状态 ───
  const quizTab = ref<"course" | "practice">("practice");
  const quizzes = ref<Quiz[]>([]);
  const selectedPracticeChapters = ref<number[]>([]);
  const quizQuestionCount = ref(10);
  const practiceDifficulty = ref("mixed");
  const smartQuiz = ref(true);
  // NotebookLM 式自定义出题要求：默认收起，非空时随生成请求一起提交
  const showCustomInstructions = ref(false);
  const quizCustomInstructions = ref("");
  const quizGenerating = ref(false);
  const wrongPracticeGenerating = ref(false);
  const quizRetaking = ref(false);
  // 进行中/失败的 AI 出题任务（占位卡）：生成不再阻塞界面，任务在后台跑、完成后占位卡变真卡。
  const generatingTasks = ref<any[]>([]);
  const quizListFilter = ref<"all" | "pending" | "done">("all");
  // 做题草稿：逐题答案自动落 localStorage（做题在独立路由页写入），列表用它标"进行中"；version 号驱动重算。
  const quizDraftVersion = ref(0);

  const wrongQuestions = ref<any[]>([]);
  const wrongKeyword = ref("");
  const wrongStatus = ref("");
  const selectedWrongKnowledge = ref("");

  // ─── 常量 ───
  const quizCountOptions = [5, 10, 15, 20];
  const quizTypeOptions = [
    { label: "单选", value: "single_choice" },
    { label: "多选", value: "multiple_choice" },
    { label: "判断", value: "judge" },
    { label: "填空", value: "blank" },
    { label: "简答", value: "short_answer" },
  ];
  const selectedQuizTypes = ref<string[]>(["single_choice", "judge"]);
  function toggleQuizType(value: string) {
    if (selectedQuizTypes.value.includes(value)) {
      if (selectedQuizTypes.value.length <= 1) return; // 至少保留一种题型
      selectedQuizTypes.value = selectedQuizTypes.value.filter((item) => item !== value);
    } else {
      selectedQuizTypes.value = [...selectedQuizTypes.value, value];
    }
  }
  // 把所选题型均分到总题量（余数给靠前的题型），转成后端 question_type_counts。
  function quizTypeCounts(total: number): Record<string, number> | undefined {
    const types = selectedQuizTypes.value;
    if (!types.length) return undefined;
    const base = Math.floor(total / types.length);
    const remainder = total % types.length;
    const counts: Record<string, number> = {};
    types.forEach((type, index) => {
      const value = base + (index < remainder ? 1 : 0);
      if (value > 0) counts[type] = value;
    });
    return Object.keys(counts).length ? counts : undefined;
  }
  const quizDifficultyOptions = [
    { label: "混合（易中难梯度）", value: "mixed" },
    { label: "基础", value: "easy" },
    { label: "标准", value: "standard" },
    { label: "较难", value: "hard" },
  ];
  const wrongStatusOptions = [
    { label: "全部状态", value: "" },
    { label: "未掌握", value: "pending" },
    { label: "巩固中", value: "consolidating" },
    { label: "已掌握", value: "resolved" },
    { label: "多次错误", value: "repeat" },
  ];

  // ─── 派生（列表/错题统计） ───
  const courseQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type === "course"));
  // 排序原则：先看"该做的事"——进行中(有草稿) > 未开始 > 已完成，段内按时间倒序。
  const practiceQuizzes = computed(() => {
    void quizDraftVersion.value;
    const rank: Record<string, number> = { doing: 0, todo: 1, done: 2 };
    return quizzes.value
      .filter((quiz) => quiz.quiz_type !== "course")
      .slice()
      .sort((left, right) => {
        const byStatus = rank[quizCardStatus(left)] - rank[quizCardStatus(right)];
        if (byStatus !== 0) return byStatus;
        return timestampMs(practiceRecordTime(right)) - timestampMs(practiceRecordTime(left));
      });
  });
  const filteredPracticeQuizzes = computed(() => practiceQuizzes.value.filter((quiz) => {
    const status = quizCardStatus(quiz);
    if (quizListFilter.value === "pending") return status !== "done";
    if (quizListFilter.value === "done") return status === "done";
    return true;
  }));
  const wrongKnowledgeFilters = computed(() => {
    const counter = new Map<string, number>();
    wrongQuestions.value.forEach((item: any) => {
      const name = item.knowledge_point_name || "未标注知识点";
      counter.set(name, (counter.get(name) || 0) + 1);
    });
    return Array.from(counter.entries()).map(([name, count]) => ({ name, count })).sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
  });
  function wrongMastery(item: any): "pending" | "consolidating" | "resolved" {
    if (item?.mastery === "consolidating" || item?.mastery === "resolved" || item?.mastery === "pending") return item.mastery;
    if (item?.is_resolved) return "resolved";
    return Number(item?.correct_streak || 0) >= 1 ? "consolidating" : "pending";
  }
  const pendingWrongCount = computed(() => wrongQuestions.value.filter((item) => wrongMastery(item) === "pending").length);
  const consolidatingWrongCount = computed(() => wrongQuestions.value.filter((item) => wrongMastery(item) === "consolidating").length);
  const resolvedWrongCount = computed(() => wrongQuestions.value.filter((item) => wrongMastery(item) === "resolved").length);
  const repeatedWrongCount = computed(() => wrongQuestions.value.filter((item) => Number(item.wrong_count || 0) > 1).length);
  // 艾宾浩斯：到复习时间（后端 is_due）的错题数，驱动"今日待复习"提醒。
  const dueWrongCount = computed(() => wrongQuestions.value.filter((item) => item.is_due).length);
  const filteredWrongQuestions = computed(() => wrongQuestions.value.filter((item) => {
    const keyword = wrongKeyword.value.trim();
    const stem = item.question?.stem || "";
    const explanation = item.question?.explanation || "";
    const knowledgeName = item.knowledge_point_name || "未标注知识点";
    const statusMatched = !wrongStatus.value
      || (wrongStatus.value === "repeat" && Number(item.wrong_count || 0) > 1)
      || wrongStatus.value === wrongMastery(item);
    return (!keyword || stem.includes(keyword) || explanation.includes(keyword))
      && (!selectedWrongKnowledge.value || knowledgeName === selectedWrongKnowledge.value)
      && statusMatched;
  }));
  const wrongFilterSummary = computed(() => {
    const parts = [];
    if (selectedWrongKnowledge.value) parts.push(selectedWrongKnowledge.value);
    if (wrongStatus.value) parts.push(String(wrongStatusOptions.find((item) => item.value === wrongStatus.value)?.label || ""));
    if (wrongKeyword.value.trim()) parts.push(`关键词：${wrongKeyword.value.trim()}`);
    return parts.filter(Boolean).join(" · ") || "全部错题";
  });
  // 错题分页：一页 10 道。切换筛选/知识点回到第 1 页；总数变化时夹住页码。
  const WRONG_PER_PAGE = 10;
  const wrongPage = ref(1);
  const wrongPageCount = computed(() => Math.max(1, Math.ceil(filteredWrongQuestions.value.length / WRONG_PER_PAGE)));
  const pagedWrongQuestions = computed(() => {
    const start = (wrongPage.value - 1) * WRONG_PER_PAGE;
    return filteredWrongQuestions.value.slice(start, start + WRONG_PER_PAGE);
  });
  watch([selectedWrongKnowledge, wrongStatus, wrongKeyword], () => { wrongPage.value = 1; });
  watch(wrongPageCount, (count) => { if (wrongPage.value > count) wrongPage.value = count; });
  function setWrongPage(page: number) { wrongPage.value = Math.min(wrongPageCount.value, Math.max(1, page)); }
  const weeklyWrongCount = computed(() => wrongQuestions.value.filter((item) => {
    const time = item.last_wrong_at || item.updated_at || item.created_at;
    const timeMs = timestampMs(time);
    return timeMs > 0 && Date.now() - timeMs < 7 * 86400000;
  }).length);

  function queuedQuizMessage(result: any, fallback = "题目已加入生成队列，生成成功后会通知你") {
    if (result?.id) return "";
    return result?.status === "failed" ? "题目生成失败，请稍后重试" : fallback;
  }

  // 出卷成功消息点击 / 直达链接带 ?open=<quizId> 落到测验页：直接跳到该卷的独立做题路由。
  async function maybeOpenQuizFromQuery() {
    if (active.value !== "studentQuizzes") return;
    const openId = Number(route.query.open || 0);
    if (openId <= 0) return;
    await router.replace({ path: `/quizzes/${openId}/answer` });
  }

  // 出题/错题重练完成的通知(quiz_generated)携带 resource_id，可点击直达答题页；
  // 失败通知(resource_id 为空)与公告/教师提醒/新课时等暂不导航，返回 0 表示不可点击。
  function notificationQuizId(item: any): number {
    if (!item || item.type !== "quiz_generated") return 0;
    return Number(item.resource_id || 0) || 0;
  }

  async function openQuizSelection(tab: "course" | "practice" = "practice") {
    quizTab.value = tab;
    // 从答题路由返回后草稿状态可能变化，bump 让列表的"进行中"标记重算。
    quizDraftVersion.value += 1;
    if (active.value === "studentQuizzes") {
      await loadQuizPage();
      return;
    }
    await go("studentQuizzes");
  }

  async function generateKnowledgeQuiz(count: number, opts: { name?: string; chapterId?: number | null } = {}) {
    if (quizGenerating.value) return;
    if (!selectedCourseId.value) return void emit("notice", "warning", "请先选择课程");
    quizGenerating.value = true;
    emit("notice", "info", "AI 已开始出题，约需 1-3 分钟；可切换页面，进度看右下角，完成后会提醒你");
    startGenerationRefresh();
    try {
      const title = `${opts.name || "知识点"}练习`;
      const result = await run<any>(() => api.post("/learning/quizzes/generate", { course_id: selectedCourseId.value, chapter_id: opts.chapterId || undefined, title, quiz_type: "practice", question_count: count }));
      if (!result) return;
      await openQuizSelection("practice");
      await handleGenerateResult(result, { title, kind: "quiz" });
    } finally {
      quizGenerating.value = false;
      stopGenerationRefresh();
      void refreshGenerationTasks();
    }
  }

  async function loadQuizPage() {
    if (!selectedCourseId.value) return;
    quizzes.value = (await run<Quiz[]>(() => api.get("/learning/quizzes", { course_id: selectedCourseId.value }))) || [];
    if (!courseHome.value.course) await loadCourseHome();
    await loadWrongBook();
    await refreshGenerationTasks();
  }

  // ─── 做题草稿（逐题自动保存，退出/刷新不丢） ───
  function quizDraftKey(quizId: number) { return `ca_quiz_draft_v1_${user.id}_${quizId}`; }
  function readQuizDraft(quizId: number): any | null {
    try {
      const raw = localStorage.getItem(quizDraftKey(quizId));
      if (!raw) return null;
      const data = JSON.parse(raw);
      return data && typeof data === "object" && data.answers && typeof data.answers === "object" ? data : null;
    } catch { return null; }
  }
  function clearQuizDraft(quizId: number) {
    try { localStorage.removeItem(quizDraftKey(quizId)); } catch { /* 忽略存储异常 */ }
    quizDraftVersion.value += 1;
  }
  function hasQuizDraft(quizId: number) {
    void quizDraftVersion.value;
    return readQuizDraft(quizId) !== null;
  }
  function quizCardStatus(quiz: any): "done" | "doing" | "todo" {
    if (latestQuizAttempt(quiz)?.id) return "done";
    if (hasQuizDraft(Number(quiz.id))) return "doing";
    return "todo";
  }

  // ─── 生成任务占位卡（非阻塞出题） ───
  // 出题期间轮询任务列表：部署为 Celery 同步档（CELERY_TASK_ALWAYS_EAGER=true，开发/单机常见）时
  // POST 会阻塞到出题完成，按钮全程"出卷中"，用户误以为卡死不敢切页。靠这里把后台任务
  // （含 detail.step 实时步骤）拉进右下角进度面板，用户能看到真实进展、可放心离开本页；
  // 异步档下 POST 秒回，轮询随 finally 立即停止，无额外开销。引用计数支持多路生成并发共用一个定时器。
  let generationRefreshTimer = 0;
  let generationRefreshUsers = 0;
  function startGenerationRefresh() {
    generationRefreshUsers += 1;
    if (!generationRefreshTimer) {
      generationRefreshTimer = window.setInterval(() => { void refreshGenerationTasks(); }, 2500);
    }
  }
  function stopGenerationRefresh() {
    generationRefreshUsers = Math.max(0, generationRefreshUsers - 1);
    if (!generationRefreshUsers && generationRefreshTimer) {
      window.clearInterval(generationRefreshTimer);
      generationRefreshTimer = 0;
    }
  }
  // 同步一份到全局 generationTasks store，供 App.vue 根级挂载的右侧步骤清单浮层读取；
  // 面板需要在做题路由(无 shellKey，会整卸载 StudentView)之上常驻，因此不能只放本地 ref。
  function syncGenerationPanelTask(task: any) {
    const id = Number(task.task_id || task.id || 0);
    if (!id) return;
    generation.upsertTask({
      id,
      title: String(task.title || "AI 出题"),
      status: (task.status || "pending") as any,
      step: task.detail?.step ?? null,
    });
  }
  async function refreshGenerationTasks() {
    if (!selectedCourseId.value) { generatingTasks.value = []; return; }
    try {
      const previousIds = new Set(generatingTasks.value.map((item) => Number(item.task_id || item.id)));
      const items = (await api.get<any[]>("/learning/generation-tasks", { course_id: selectedCourseId.value })) || [];
      generatingTasks.value = items;
      const nextIds = new Set(items.map((item) => Number(item.task_id || item.id)));
      previousIds.forEach((id) => { if (!nextIds.has(id)) generation.removeTask(id); });
      items.forEach((item) => syncGenerationPanelTask(item));
    } catch { /* 占位卡刷新失败保持现状，不打扰用户 */ }
  }
  function upsertGeneratingTask(task: any) {
    const id = Number(task.task_id || task.id || 0);
    if (!id) return;
    generatingTasks.value = [{ ...task, task_id: id }, ...generatingTasks.value.filter((item) => Number(item.task_id || item.id) !== id)];
    syncGenerationPanelTask({ ...task, task_id: id });
  }
  function removeGeneratingTask(taskId: number) {
    generatingTasks.value = generatingTasks.value.filter((item) => Number(item.task_id || item.id) !== taskId);
    generation.removeTask(taskId);
  }
  async function ignoreGenerationTask(taskId: number) {
    const result = await run(() => api.delete(`/learning/generation-tasks/${taskId}`));
    if (result !== null) removeGeneratingTask(taskId);
  }
  async function trackGenerationTask(taskId: number, kind: string) {
    const outcome = await pollGenerationProgress(taskId, {
      intervalMs: 2500,
      timeoutMs: 300000,
      onTick: (step, status) => generation.updateTask(taskId, { status: status as any, step }),
    });
    if (outcome.status === "ready") {
      removeGeneratingTask(taskId);
      await loadQuizPage();
      const label = kind === "wrong_book_practice" ? "错题重练已生成" : "练习已生成";
      emit("notice", "success", `${label}，点击进入答题`, { label: "进入答题", onClick: () => void openQuizById(outcome.quizId) });
      return;
    }
    if (outcome.status === "failed") {
      generatingTasks.value = generatingTasks.value.map((item) => (Number(item.task_id || item.id) === taskId ? { ...item, status: "failed" } : item));
      generation.updateTask(taskId, { status: "failed" });
      emit("notice", "error", "AI 出题失败，可在练习列表中重试或忽略该任务");
      return;
    }
    // 超时：任务可能仍在跑，保留占位卡，交给通知与下次刷新兜底。
    await refreshGenerationTasks();
  }
  async function handleGenerateResult(result: any, { title, kind }: { title: string; kind: string }) {
    if (String(result.status) === "failed") return void emit("notice", "error", "出卷失败，请稍后重试");
    const quizId = Number(result.id || 0);
    if (quizId > 0) {
      await loadQuizPage();
      emit("notice", "success", "出卷成功，点击进入答题", { label: "进入答题", onClick: () => void openQuizById(quizId) });
      return;
    }
    const taskId = Number(result.task_id || 0);
    if (!taskId) {
      emit("notice", "info", queuedQuizMessage(result) || "题目已加入生成队列，生成成功后会通知你");
      await loadNotifications(true);
      return;
    }
    // "已开始出题"的提示已提前到点击瞬间（见 generateQuiz 等调用方），此处不再重复弹
    upsertGeneratingTask({ task_id: taskId, title, status: String(result.status || "pending"), kind });
    void trackGenerationTask(taskId, kind);
  }
  // 出卷成功后点击“进入答题”：直接跳该卷的独立做题路由。
  async function openQuizById(quizId: number) {
    await router.push({ path: `/quizzes/${quizId}/answer` });
  }
  function practiceQuizTitle(chapterIds: number[]) {
    const chapters = (courseHome.value.chapters || []).filter((item: any) => chapterIds.includes(item.id));
    const scope = chapters.length === 1 ? chapters[0].title : chapters.length > 1 ? `${chapters[0].title} 等${chapters.length}章` : "全课程";
    return `${scope} · ${smartQuiz.value ? "薄弱点强化" : "章节练习"}`;
  }
  async function generateQuiz() {
    if (quizGenerating.value) return;
    if (!selectedCourseId.value) return void emit("notice", "warning", "请先选择课程");
    quizGenerating.value = true;
    emit("notice", "info", "AI 已开始出题，约需 1-3 分钟；可切换页面，进度看右下角，完成后会提醒你");
    startGenerationRefresh();
    try {
      const chapterIds = selectedPracticeChapters.value.length ? selectedPracticeChapters.value : (selectedChapterId.value ? [selectedChapterId.value] : []);
      const title = practiceQuizTitle(chapterIds);
      const result = await run<any>(() => api.post("/learning/quizzes/generate", {
        course_id: selectedCourseId.value,
        chapter_id: chapterIds.length === 1 ? chapterIds[0] : undefined,
        chapter_ids: chapterIds,
        title,
        quiz_type: "practice",
        question_count: quizQuestionCount.value,
        question_type_counts: quizTypeCounts(quizQuestionCount.value),
        prefer_weak_points: smartQuiz.value,
        difficulty: practiceDifficulty.value || "mixed",
        custom_instructions: quizCustomInstructions.value.trim() || undefined,
      }));
      if (!result) return; // run() 已弹出错误提示
      // 生成全程不再锁按钮空等：占位卡进列表、任务后台轮询，完成/失败都有回执。
      await handleGenerateResult(result, { title, kind: "quiz" });
    } finally {
      quizGenerating.value = false;
      stopGenerationRefresh();
      // 收尾再刷一次：同步档下任务已 ready/failed，列表口径（仅进行中/失败）会自动把面板卡清掉或转失败态
      void refreshGenerationTasks();
    }
  }
  function latestQuizAttempt(quiz: any) {
    return quiz?.latest_attempt || quiz?.last_attempt || quiz?.best_attempt || (Array.isArray(quiz?.attempts) ? quiz.attempts[0] : null);
  }
  function practiceRecordTime(quiz: any) {
    const attempt = latestQuizAttempt(quiz);
    return attempt?.submitted_at || attempt?.created_at || quiz?.updated_at || quiz?.created_at || null;
  }
  // 做题/解析已升级为独立全屏路由 /quizzes/:quizId/answer（StudentQuizAnswer.vue）。
  // 列表侧只负责“跳到那套题的 URL”，作答/续做/看解析由路由组件按草稿与作答记录自行判定。
  async function openQuiz(quiz: any) {
    await router.push({ path: `/quizzes/${quiz.id}/answer` });
  }
  async function startQuiz(id: number) {
    await router.push({ path: `/quizzes/${id}/answer` });
  }
  function reviewAttempt(quizId: number, attemptId?: number) {
    void router.push({ path: `/quizzes/${quizId}/answer`, query: attemptId ? { attempt: String(attemptId) } : {} });
  }
  async function retakeQuiz(quizId: number, mode: "full" | "wrong", attemptId?: number) {
    if (quizRetaking.value) return;
    quizRetaking.value = true;
    try {
      // 一卷只能交一次是后端约束；"再练"通过克隆新卷实现，历史成绩完整保留。
      const quiz = await run<any>(() => api.post(`/learning/quizzes/${quizId}/retake`, { mode, attempt_id: attemptId || undefined }));
      if (!quiz) return; // run 已弹错误提示
      if (!quiz.id) { emit("notice", "info", "重做卷生成中，稍后可在测验列表打开"); return; } // 不再静默 no-op
      await router.push({ path: `/quizzes/${quiz.id}/answer` });
    } finally {
      quizRetaking.value = false;
    }
  }
  async function deletePractice(quiz: any) {
    const quizId = Number(quiz?.id || 0);
    if (!quizId) return;
    const result = await run(() => api.delete(`/learning/quizzes/${quizId}`), "已删除练习");
    if (result === null) return;
    clearQuizDraft(quizId);
    await loadQuizPage();
  }
  function togglePracticeChapter(id: number) { selectedPracticeChapters.value = selectedPracticeChapters.value.includes(id) ? selectedPracticeChapters.value.filter((item) => item !== id) : [...selectedPracticeChapters.value, id]; }

  async function loadWrongBook() { if (!selectedCourseId.value) return; wrongQuestions.value = (await run<any[]>(() => api.get("/learning/wrong-questions", { course_id: selectedCourseId.value }))) || []; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; }
  async function loadWrongPractice(wrongQuestionId?: number) {
    if (!selectedCourseId.value || wrongPracticeGenerating.value) return;
    wrongPracticeGenerating.value = true;
    startGenerationRefresh();
    try {
      if (!wrongQuestions.value.length) await loadWrongBook();
      if (!wrongQuestions.value.length) {
        emit("notice", "info", "暂无错题可重练");
        return;
      }
      emit("notice", "info", "错题重练生成中，约需 1-2 分钟；可切换页面，完成后会提醒你");
      const quiz = await run<any>(() => api.post("/learning/wrong-questions/practice", undefined, { course_id: selectedCourseId.value, ...(wrongQuestionId ? { wrong_question_id: wrongQuestionId } : {}) }));
      if (!quiz) return;
      if (Number(quiz.id || 0) > 0) {
        await go("studentQuizzes");
        await loadQuizPage();
        await startQuiz(quiz.id);
        return;
      }
      // 异步生成：跳到练习页展示"生成中"占位卡，后台跟踪任务。
      await go("studentQuizzes");
      await loadQuizPage();
      await handleGenerateResult(quiz, { title: "错题重练", kind: "wrong_book_practice" });
    } finally {
      wrongPracticeGenerating.value = false;
      stopGenerationRefresh();
      void refreshGenerationTasks();
    }
  }
  function practiceWrong(item: any) { loadWrongPractice(item?.wrong_question_id); }
  function clearWrongFilters() { wrongKeyword.value = ""; wrongStatus.value = ""; selectedWrongKnowledge.value = ""; }

  function quizQuestionMeta(quiz: any) {
    const count = quiz.question_count || quiz.questions_count || quiz.questions?.length || 0;
    return count ? `${count}题` : `${quiz.total_score || 0}分`;
  }
  function quizScoreLabel(quiz: any) {
    const attempt = quiz.latest_attempt || quiz.last_attempt || quiz.best_attempt;
    if (attempt?.correct_count !== undefined && attempt?.total_count) return `${attempt.correct_count}/${attempt.total_count}`;
    if (attempt?.score !== undefined) return `${Math.round(Number(attempt.score))}分`;
    return statusText(quiz.status || "published");
  }

  return {
    // 状态
    quizTab, quizzes, selectedPracticeChapters, quizQuestionCount, practiceDifficulty, smartQuiz,
    quizGenerating, wrongPracticeGenerating, quizRetaking, generatingTasks, quizListFilter, quizDraftVersion,
    wrongQuestions, wrongKeyword, wrongStatus, selectedWrongKnowledge, selectedQuizTypes,
    // 常量
    quizCountOptions, quizTypeOptions, quizDifficultyOptions, wrongStatusOptions,
    // 派生
    courseQuizzes, practiceQuizzes, filteredPracticeQuizzes, wrongKnowledgeFilters,
    pendingWrongCount, consolidatingWrongCount, resolvedWrongCount, repeatedWrongCount, dueWrongCount,
    filteredWrongQuestions, pagedWrongQuestions, wrongPage, wrongPageCount, setWrongPage, wrongFilterSummary, weeklyWrongCount,
    // 方法
    toggleQuizType, quizTypeCounts, wrongMastery, queuedQuizMessage, maybeOpenQuizFromQuery, notificationQuizId,
    openQuizSelection, generateKnowledgeQuiz, loadQuizPage,
    quizDraftKey, readQuizDraft, clearQuizDraft, hasQuizDraft, quizCardStatus,
    refreshGenerationTasks, upsertGeneratingTask, removeGeneratingTask, ignoreGenerationTask,
    trackGenerationTask, handleGenerateResult, openQuizById,
    practiceQuizTitle, generateQuiz, latestQuizAttempt, practiceRecordTime,
    showCustomInstructions, quizCustomInstructions,
    openQuiz, startQuiz, reviewAttempt, retakeQuiz, deletePractice, togglePracticeChapter,
    loadWrongBook, loadWrongPractice, practiceWrong, clearWrongFilters,
    quizQuestionMeta, quizScoreLabel,
  };
}
