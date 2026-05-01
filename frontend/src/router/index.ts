import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useSessionStore } from "../stores/session";
import type { Role } from "../types";
import AdminView from "../views/AdminView.vue";
import AuthView from "../views/AuthView.vue";
import StudentView from "../views/StudentView.vue";
import TeacherView from "../views/TeacherView.vue";

export const routeByPage: Record<string, string> = {
  studentHome: "/home",
  studentCourses: "/courses",
  studentCourseHome: "/courses/detail",
  studentMaterials: "/materials",
  studentLessons: "/lessons",
  studentQa: "/qa",
  studentTutoring: "/tutoring",
  studentKnowledge: "/knowledge",
  studentQuizzes: "/quizzes",
  studentWrongBook: "/wrong-book",
  studentPlans: "/plans",
  studentProfile: "/profile",
  courses: "/courses",
  courseDetail: "/courses/detail",
  materials: "/materials",
  lessons: "/lessons",
  qa: "/qa",
  tutoring: "/tutoring",
  learning: "/learning",
  plans: "/plans",
  analytics: "/analytics",
  profile: "/profile",
  teacherDashboard: "/teacher",
  teacherCourses: "/teacher/courses",
  teacherCourseForm: "/teacher/courses/new",
  teacherCourseHome: "/teacher/course",
  teacherMaterials: "/teacher/materials",
  teacherPpt: "/teacher/materials/workbench",
  teacherLessons: "/teacher/lessons",
  teacherStudents: "/teacher/students",
  teacherAnalytics: "/teacher/analytics",
  teacherProfile: "/teacher/profile",
  adminDashboard: "/admin",
  adminUsers: "/admin/users",
  adminCourses: "/admin/courses",
  adminMaterials: "/admin/materials",
  adminModels: "/admin/models",
  adminServices: "/admin/services",
  adminSystem: "/admin/system",
  adminMonitor: "/admin/monitor",
  adminLogs: "/admin/logs",
  adminBackups: "/admin/backups"
};

export function defaultRouteForRole(role?: Role | null) {
  if (role === "admin") return routeByPage.adminDashboard;
  if (role === "teacher") return routeByPage.teacherDashboard;
  return routeByPage.studentHome;
}

const studentRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: StudentView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["student"], pageKey, shellKey: "student" }
});

const adminRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: AdminView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["admin"], pageKey, shellKey: "admin" }
});

const teacherRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: TeacherView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["teacher"], pageKey, shellKey: "teacher" }
});

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/home" },
  { path: "/auth", component: AuthView, meta: { public: true, shellKey: "auth" } },
  studentRoute("/home", "studentHome"),
  studentRoute("/courses", "studentCourses"),
  studentRoute("/courses/detail", "studentCourseHome"),
  studentRoute("/materials", "studentMaterials"),
  studentRoute("/lessons", "studentCourseHome"),
  studentRoute("/qa", "studentQa"),
  studentRoute("/tutoring", "studentTutoring"),
  studentRoute("/knowledge", "studentKnowledge"),
  studentRoute("/quizzes", "studentQuizzes"),
  studentRoute("/wrong-book", "studentWrongBook"),
  studentRoute("/learning", "studentQuizzes"),
  studentRoute("/plans", "studentPlans"),
  studentRoute("/profile", "studentProfile"),
  teacherRoute("/teacher", "teacherDashboard"),
  teacherRoute("/teacher/courses", "teacherCourses"),
  teacherRoute("/teacher/courses/new", "teacherCourseForm"),
  teacherRoute("/teacher/course", "teacherCourseHome"),
  teacherRoute("/teacher/materials", "teacherMaterials"),
  teacherRoute("/teacher/materials/workbench", "teacherPpt"),
  teacherRoute("/teacher/lessons", "teacherLessons"),
  teacherRoute("/teacher/students", "teacherStudents"),
  teacherRoute("/teacher/analytics", "teacherAnalytics"),
  teacherRoute("/teacher/profile", "teacherProfile"),
  adminRoute("/admin", "adminDashboard"),
  adminRoute("/admin/users", "adminUsers"),
  adminRoute("/admin/courses", "adminCourses"),
  adminRoute("/admin/materials", "adminMaterials"),
  adminRoute("/admin/models", "adminModels"),
  adminRoute("/admin/services", "adminServices"),
  adminRoute("/admin/system", "adminSystem"),
  adminRoute("/admin/monitor", "adminMonitor"),
  adminRoute("/admin/logs", "adminLogs"),
  adminRoute("/admin/backups", "adminBackups"),
  { path: "/:pathMatch(.*)*", redirect: "/home" }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to) => {
  const session = useSessionStore();
  await session.bootstrap();
  if (to.meta.public) {
    if (session.user) return defaultRouteForRole(session.user.role);
    return true;
  }
  if (to.meta.requiresAuth && !session.user) return "/auth";
  const roles = to.meta.roles as Role[] | undefined;
  if (roles && session.user && !roles.includes(session.user.role)) return defaultRouteForRole(session.user.role);
  return true;
});
