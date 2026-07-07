// 学生端全局搜索（跨课程/课时/资料/知识点/问答，带缓存与防抖）。原为 StudentView 内联，抽为独立 composable。
// 命中结果的跳转依赖外壳提供的导航动作（deps），搜索自身状态与请求逻辑内聚于此。
import { computed, nextTick, onScopeDispose, reactive, ref, watch, type Ref } from "vue";
import { api } from "../../api/client";
import { FolderOpen, Layers, MessageCircle, Play, Presentation } from "../../icons";
import { formatTime } from "../../utils/datetime";
import { knowledgeExcerpt, normalizeSearchText, searchExcerpt, searchScore, searchTeacherName } from "../../utils/studentSearch";

export type StudentSearchResultType = "course" | "lesson" | "material" | "knowledge" | "qa";
export type StudentSearchResult = {
  key: string;
  type: StudentSearchResultType;
  title: string;
  subtitle: string;
  excerpt?: string;
  courseId?: number;
  lessonId?: number;
  knowledgeId?: number | null;
  chapterId?: number | null;
  qaItem?: any;
  rank: number;
  order: number;
};

type SearchDeps = {
  courses: Ref<any[]>;
  selectedCourseId: Ref<number>;
  selectedChapterId: Ref<number | null>;
  selectedKnowledgeId: Ref<number | null>;
  openCourse: (courseId: number) => Promise<void>;
  openLesson: (lessonId: number) => Promise<void>;
  loadCourseHome: () => Promise<void>;
  go: (key: string) => Promise<void>;
  loadQaHistory: () => Promise<void>;
  reuseHistory: (qaItem: any) => void;
};

const studentSearchTypeMeta: Record<StudentSearchResultType, { label: string; icon: any }> = {
  course: { label: "课程", icon: Presentation },
  lesson: { label: "课时", icon: Play },
  material: { label: "资料", icon: FolderOpen },
  knowledge: { label: "知识点", icon: Layers },
  qa: { label: "问答", icon: MessageCircle },
};

export function useStudentSearch(deps: SearchDeps) {
  const { courses, selectedCourseId, selectedChapterId, selectedKnowledgeId, openCourse, openLesson, loadCourseHome, go, loadQaHistory, reuseHistory } = deps;

  const searchOpen = ref(false);
  const globalSearch = ref("");
  const searchInput = ref<HTMLInputElement | null>(null);
  const searchLoading = ref(false);
  const searchError = ref("");
  const searchResults = ref<StudentSearchResult[]>([]);
  const searchActiveIndex = ref(-1);
  const searchCourseHomeCache = reactive<Record<number, any>>({});
  const searchKnowledgeCache = reactive<Record<number, any[]>>({});
  const searchQaCache = reactive<Record<string, any[]>>({});
  const searchCourseHomePending = new Map<number, Promise<any>>();
  const searchKnowledgePending = new Map<number, Promise<any[]>>();
  const searchQaPending = new Map<string, Promise<any[]>>();
  let searchTimer: number | undefined;
  let searchRequestSeq = 0;

  function searchTypeMeta(type: StudentSearchResultType) { return studentSearchTypeMeta[type]; }
  const searchResultGroups = computed(() => (["course", "lesson", "material", "knowledge", "qa"] as StudentSearchResultType[])
    .map((type) => ({
      type,
      label: studentSearchTypeMeta[type].label,
      items: searchResults.value.filter((item) => item.type === type),
    }))
    .filter((group) => group.items.length));
  const flatSearchResults = computed(() => searchResultGroups.value.flatMap((group) => group.items));

  function pruneSearchCache() {
    const validIds = new Set(courses.value.map((course) => Number(course.id)));
    Object.keys(searchCourseHomeCache).forEach((key) => {
      if (!validIds.has(Number(key))) delete searchCourseHomeCache[Number(key)];
    });
    Object.keys(searchKnowledgeCache).forEach((key) => {
      if (!validIds.has(Number(key))) delete searchKnowledgeCache[Number(key)];
    });
    Object.keys(searchQaCache).forEach((key) => {
      const [courseId] = key.split(":");
      if (!validIds.has(Number(courseId))) delete searchQaCache[key];
    });
  }
  function resetSearchState(clearKeyword = false) {
    if (searchTimer) window.clearTimeout(searchTimer);
    searchTimer = undefined;
    searchRequestSeq += 1;
    searchLoading.value = false;
    searchError.value = "";
    searchResults.value = [];
    searchActiveIndex.value = -1;
    if (clearKeyword) globalSearch.value = "";
  }
  function closeSearch() {
    searchOpen.value = false;
    resetSearchState(true);
  }
  async function openSearch() {
    searchOpen.value = true;
    if (!courses.value.length) void ensureSearchCoursesLoaded();
    await nextTick();
    searchInput.value?.focus();
  }
  async function ensureSearchCoursesLoaded() {
    if (courses.value.length) return courses.value;
    const data = await api.get<any[]>("/student/courses");
    courses.value = Array.isArray(data) ? data : [];
    pruneSearchCache();
    if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = Number(courses.value[0].id);
    return courses.value;
  }
  async function ensureSearchCourseHome(courseId: number) {
    if (searchCourseHomeCache[courseId]) return searchCourseHomeCache[courseId];
    const pending = searchCourseHomePending.get(courseId);
    if (pending) return pending;
    const task = api.get(`/student/courses/${courseId}/home`)
      .then((data) => {
        searchCourseHomeCache[courseId] = data || {};
        return searchCourseHomeCache[courseId];
      })
      .catch(() => null)
      .finally(() => { searchCourseHomePending.delete(courseId); });
    searchCourseHomePending.set(courseId, task);
    return task;
  }
  async function ensureSearchKnowledge(courseId: number) {
    if (searchKnowledgeCache[courseId]) return searchKnowledgeCache[courseId];
    const pending = searchKnowledgePending.get(courseId);
    if (pending) return pending;
    const task = api.get<any[]>("/learning/knowledge-points", { course_id: courseId })
      .then((data) => {
        searchKnowledgeCache[courseId] = Array.isArray(data) ? data : [];
        return searchKnowledgeCache[courseId];
      })
      .catch(() => [])
      .finally(() => { searchKnowledgePending.delete(courseId); });
    searchKnowledgePending.set(courseId, task);
    return task;
  }
  async function ensureSearchQa(courseId: number, keyword: string) {
    const cacheKey = `${courseId}:${normalizeSearchText(keyword)}`;
    if (searchQaCache[cacheKey]) return searchQaCache[cacheKey];
    const pending = searchQaPending.get(cacheKey);
    if (pending) return pending;
    const task = api.get<any[]>("/qa/history", { course_id: courseId, keyword })
      .then((data) => {
        searchQaCache[cacheKey] = Array.isArray(data) ? data : [];
        return searchQaCache[cacheKey];
      })
      .catch(() => [])
      .finally(() => { searchQaPending.delete(cacheKey); });
    searchQaPending.set(cacheKey, task);
    return task;
  }
  async function performGlobalSearch(keyword: string, currentSearchSeq: number) {
    searchLoading.value = true;
    searchError.value = "";
    try {
      const courseList = await ensureSearchCoursesLoaded();
      const results: StudentSearchResult[] = [];
      let order = 0;
      courseList.forEach((course: any) => {
        const score = searchScore(keyword, course?.name, course?.term, searchTeacherName(course), course?.description, course?.intro);
        if (score < 0) return;
        results.push({
          key: `course-${course.id}`,
          type: "course",
          title: course?.name || "未命名课程",
          subtitle: [course?.term, searchTeacherName(course)].filter(Boolean).join(" · ") || "课程",
          excerpt: searchExcerpt(course?.description || course?.intro),
          courseId: Number(course.id),
          rank: score + 80,
          order: order += 1,
        });
      });
      const shouldSearchQa = normalizeSearchText(keyword).length >= 2;
      const scopedData = await Promise.all(courseList.map(async (course: any) => {
        const courseId = Number(course.id);
        const [home, points, qa] = await Promise.all([
          ensureSearchCourseHome(courseId),
          ensureSearchKnowledge(courseId),
          shouldSearchQa ? ensureSearchQa(courseId, keyword) : Promise.resolve([]),
        ]);
        return { course, home: home || {}, points: Array.isArray(points) ? points : [], qa: Array.isArray(qa) ? qa : [] };
      }));
      if (currentSearchSeq !== searchRequestSeq) return;
      scopedData.forEach(({ course, home, points, qa }) => {
        const courseId = Number(course.id);
        const courseName = course?.name || home?.course?.name || "课程";
        const chapters = Array.isArray(home?.chapters) ? home.chapters : [];
        (Array.isArray(home?.lessons) ? home.lessons : []).forEach((lesson: any) => {
          const score = searchScore(keyword, lesson?.title, lesson?.summary, lesson?.description, courseName);
          if (score < 0) return;
          results.push({
            key: `lesson-${lesson.id}`,
            type: "lesson",
            title: lesson?.title || `课时 ${lesson.id}`,
            subtitle: `${courseName} · 课时`,
            excerpt: searchExcerpt(lesson?.summary || lesson?.description),
            courseId,
            lessonId: Number(lesson.id),
            rank: score + 70,
            order: order += 1,
          });
        });
        (Array.isArray(home?.materials) ? home.materials : []).forEach((material: any) => {
          const title = material?.title || material?.name || material?.filename || material?.original_name || "课程资料";
          const score = searchScore(keyword, title, material?.description, material?.filename, courseName);
          if (score < 0) return;
          results.push({
            key: `material-${material.id || `${courseId}-${title}`}`,
            type: "material",
            title,
            subtitle: `${courseName} · 课程资料`,
            excerpt: searchExcerpt(material?.description || material?.filename || material?.original_name),
            courseId,
            rank: score + 60,
            order: order += 1,
          });
        });
        points.forEach((item: any) => {
          const chapterTitle = chapters.find((chapter: any) => Number(chapter.id) === Number(item?.chapter_id))?.title || item?.chapter_title || "知识点";
          const excerpt = knowledgeExcerpt(item);
          const score = searchScore(keyword, item?.name, chapterTitle, excerpt, courseName);
          if (score < 0) return;
          results.push({
            key: `knowledge-${item.id}`,
            type: "knowledge",
            title: item?.name || `知识点 ${item.id}`,
            subtitle: `${courseName} · ${chapterTitle}`,
            excerpt,
            courseId,
            knowledgeId: Number(item.id),
            chapterId: item?.chapter_id ? Number(item.chapter_id) : null,
            rank: score + 65,
            order: order += 1,
          });
        });
        qa.forEach((item: any) => {
          const answerPreview = item?.answer_preview || item?.answer || "";
          const score = searchScore(keyword, item?.title, item?.question, answerPreview, courseName);
          if (score < 0) return;
          results.push({
            key: `qa-${item.conversation_id || item.id}`,
            type: "qa",
            title: item?.title || item?.question || "历史问答",
            subtitle: `${courseName} · ${formatTime(item?.created_at)}`,
            excerpt: searchExcerpt(answerPreview),
            courseId,
            qaItem: item,
            rank: score + 55,
            order: order += 1,
          });
        });
      });
      const seen = new Set<string>();
      searchResults.value = results
        .sort((left, right) => right.rank - left.rank || left.order - right.order)
        .filter((item) => {
          if (seen.has(item.key)) return false;
          seen.add(item.key);
          return true;
        })
        .slice(0, 24);
      searchActiveIndex.value = searchResults.value.length ? 0 : -1;
    } catch (error) {
      if (currentSearchSeq !== searchRequestSeq) return;
      searchError.value = (error as Error).message || "搜索失败，请稍后重试";
      searchResults.value = [];
      searchActiveIndex.value = -1;
    } finally {
      if (currentSearchSeq === searchRequestSeq) searchLoading.value = false;
    }
  }
  function moveSearchSelection(step: number) {
    const items = flatSearchResults.value;
    if (!items.length) return;
    if (searchActiveIndex.value < 0) {
      searchActiveIndex.value = 0;
      return;
    }
    const next = (searchActiveIndex.value + step + items.length) % items.length;
    searchActiveIndex.value = next;
  }
  function focusSearchResult(key: string) {
    const index = flatSearchResults.value.findIndex((item) => item.key === key);
    if (index >= 0) searchActiveIndex.value = index;
  }
  function isSearchResultActive(item: StudentSearchResult) { return flatSearchResults.value[searchActiveIndex.value]?.key === item.key; }
  async function openSearchResult(item: StudentSearchResult) {
    const courseId = Number(item.courseId || 0);
    closeSearch();
    if (item.type === "course" && courseId) {
      await openCourse(courseId);
      return;
    }
    if (item.type === "lesson" && item.lessonId) {
      await openLesson(Number(item.lessonId));
      return;
    }
    if (item.type === "material" && courseId) {
      selectedCourseId.value = courseId;
      await loadCourseHome();
      await go("studentMaterials");
      return;
    }
    if (item.type === "knowledge" && courseId) {
      selectedCourseId.value = courseId;
      selectedChapterId.value = item.chapterId || null;
      selectedKnowledgeId.value = item.knowledgeId || null;
      await go("studentKnowledge");
      await loadCourseHome();
      if (item.knowledgeId) selectedKnowledgeId.value = Number(item.knowledgeId);
      return;
    }
    if (item.type === "qa" && courseId && item.qaItem) {
      selectedCourseId.value = courseId;
      await go("studentQa");
      await loadCourseHome();
      await loadQaHistory();
      reuseHistory(item.qaItem);
    }
  }
  async function openActiveSearchResult() {
    const item = flatSearchResults.value[searchActiveIndex.value];
    if (!item) return;
    await openSearchResult(item);
  }

  watch(globalSearch, (value) => {
    if (searchTimer) window.clearTimeout(searchTimer);
    if (!searchOpen.value) return;
    const keyword = value.trim();
    const requestSeq = ++searchRequestSeq;
    if (!keyword) {
      searchLoading.value = false;
      searchError.value = "";
      searchResults.value = [];
      searchActiveIndex.value = -1;
      return;
    }
    searchLoading.value = true;
    searchError.value = "";
    searchTimer = window.setTimeout(() => { void performGlobalSearch(keyword, requestSeq); }, 220);
  });
  watch(flatSearchResults, (items) => {
    if (!items.length) {
      searchActiveIndex.value = -1;
      return;
    }
    if (searchActiveIndex.value < 0 || searchActiveIndex.value >= items.length) searchActiveIndex.value = 0;
  });

  onScopeDispose(() => { if (searchTimer) window.clearTimeout(searchTimer); });

  return {
    searchOpen, globalSearch, searchInput, searchLoading, searchError, searchActiveIndex,
    searchResultGroups, flatSearchResults, searchTypeMeta,
    pruneSearchCache, closeSearch, openSearch, moveSearchSelection, focusSearchResult, isSearchResultActive,
    openSearchResult, openActiveSearchResult,
  };
}
