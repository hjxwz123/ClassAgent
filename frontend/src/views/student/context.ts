// 学生端外壳向各页面子组件提供的共享上下文（provide/inject）。
// StudentView 作为外壳持有跨页共享状态（当前课程、课程列表、通知助手等），
// 抽出的页面子组件通过 useStudentCtx() 注入，避免把这些状态逐层 prop 传递。
// 这是走向"每页独立路由"的过渡：将来 ctx 可平移为 Pinia store，页面组件几乎不用改。
import { inject, type InjectionKey, type Ref } from "vue";
import type { LessonDetail, User } from "../../types";
import type { ChatMessage } from "./useQaEngine";

export type NoticeType = "success" | "warning" | "error" | "info";
export type NoticeAction = { label: string; onClick: () => void };

export type StudentCtx = {
  user: User;
  selectedCourseId: Ref<number>;
  courses: Ref<any[]>;
  courseScopeName: Ref<string>;
  hasJoinedCourses: Ref<boolean>;
  // 跨页共享的课程作用域状态（refs 由外壳持有并原样 provide，页面与外壳共享同一实例）。
  courseHome: Ref<any>;
  selectedChapterId: Ref<number | null>;
  selectedKnowledgeId: Ref<number | null>;
  weakPoints: Ref<any[]>;
  // 统一的请求包装：失败弹错误 toast、成功可选弹提示；返回 null 表示失败。
  run: <T>(task: () => Promise<T>, ok?: string) => Promise<T | null>;
  notice: (type: NoticeType, text: string, action?: NoticeAction) => void;
  loadActive: () => Promise<void>;
  loadCourseHome: () => Promise<void>;
  openJoin: () => void;
  go: (key: string) => Promise<void>;
  chapterName: (id?: number | null) => string;
  // 知识点页"生成练习"：外壳持有出题生成流水线，页面传入题名/章节即可。
  generateKnowledgeQuiz: (count: number, opts: { name?: string; chapterId?: number | null }) => Promise<void>;

  // —— 计划/首页 共享（Plans + Home）——
  dashboard: Ref<any>;
  stats: Ref<any>;
  todayTasks: Ref<any[]>;
  doneTasks: Ref<number>;
  checkinDays: Ref<string[]>;
  profilePayload: Ref<any>;
  planForm: { title: string; goal: string; available_days: number; daily_minutes: number };
  planCreating: Ref<boolean>;
  createPlan: () => Promise<void>;
  loadPlans: () => Promise<void>;
  loadDashboard: () => Promise<void>;
  // —— 个人资料 共享（Profile；身份显示于问答）——
  profileForm: { nickname: string; avatar_url: string; school: string; bio: string };
  currentAvatarUrl: Ref<string>;
  noticeSettings: any[];
  loadProfile: () => Promise<void>;
  applyStudentProfile: (data: any) => void;
  normalizeNoticeSettings: (settings: any) => any[];
  // —— 课程列表/详情 共享（Courses + CourseHome + Home）——
  openCourse: (id: number) => Promise<void>;
  courseCoverStyle: (course?: any) => Record<string, any>;
  courseCoverText: (course?: any) => string;
  handleCourseMenu: (action: string, course: any) => Promise<void>;
  courseHomeError: Ref<string>;
  isLessonOpening: Ref<boolean>;
  openLesson: (id: number) => Promise<void>;
  isOpeningLesson: (id?: number | null) => boolean;
  openQuizSelection: (tab?: "course" | "practice") => Promise<void>;
  previewMaterial: (item: any) => Promise<void>;
  downloadMaterial: (item: any) => Promise<void>;
  globalQuestion: Ref<string>;
  askGlobal: () => Promise<void>;

  // —— 课堂/上课模式 共享（study-room 组件；外壳保留触发与跨边界交互）——
  classroomOpen: Ref<boolean>;
  classroomLesson: Ref<LessonDetail | null>;
  currentPage: Ref<number>;
  pageDirection: Ref<"next" | "prev">;
  studySeconds: Ref<number>;
  completeOpen: Ref<boolean>;
  settingsOpen: Ref<boolean>;
  thumbOpen: Ref<boolean>;
  lessonSelectionMenu: { open: boolean; text: string; x: number; y: number };
  pendingSourcePageNumber: Ref<number | null>;
  pendingSourcePageId: Ref<number | null>;
  jumpPage: (page: number) => Promise<void>;
  prevPage: () => Promise<void>;
  nextPage: () => Promise<void>;
  saveProgress: (completed: boolean, silent?: boolean) => Promise<void>;
  hideLessonSelectionMenu: () => void;
  closeClassroom: () => Promise<void>;
  returnCourse: () => Promise<void>;
  nextLessonAfterComplete: () => Promise<void>;
  resolveSourcePageNumber: (source: any) => number;
  copyText: (text: unknown) => Promise<void>;
  feedbackQaMessage: (message: ChatMessage, feedback?: "positive" | "negative") => Promise<void>;
  toggleThought: (message: ChatMessage) => void;
  qaRecordsToMessages: (records: any[]) => ChatMessage[];
};

export const StudentCtxKey: InjectionKey<StudentCtx> = Symbol("studentCtx");

export function useStudentCtx(): StudentCtx {
  const ctx = inject(StudentCtxKey);
  if (!ctx) throw new Error("useStudentCtx 必须在 StudentView 外壳内使用");
  return ctx;
}
