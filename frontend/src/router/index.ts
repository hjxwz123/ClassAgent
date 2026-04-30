import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useSessionStore } from "../stores/session";
import type { Role } from "../types";
import AdminView from "../views/AdminView.vue";
import AuthView from "../views/AuthView.vue";
import TeacherView from "../views/TeacherView.vue";
import WorkspaceView from "../views/WorkspaceView.vue";

export const routeByPage: Record<string, string> = {
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
  return routeByPage.courses;
}

const workspaceRoute = (path: string, pageKey: string, roles: Role[]): RouteRecordRaw => ({
  path,
  component: WorkspaceView,
  props: { pageKey },
  meta: { requiresAuth: true, roles, pageKey }
});

const adminRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: AdminView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["admin"], pageKey }
});

const teacherRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: TeacherView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["teacher"], pageKey }
});

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/courses" },
  { path: "/auth", component: AuthView, meta: { public: true } },
  workspaceRoute("/courses", "courses", ["student"]),
  workspaceRoute("/courses/detail", "courseDetail", ["student"]),
  workspaceRoute("/materials", "materials", ["student"]),
  workspaceRoute("/lessons", "lessons", ["student"]),
  workspaceRoute("/qa", "qa", ["student"]),
  workspaceRoute("/tutoring", "tutoring", ["student"]),
  workspaceRoute("/learning", "learning", ["student"]),
  workspaceRoute("/plans", "plans", ["student"]),
  workspaceRoute("/profile", "profile", ["student"]),
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
  { path: "/:pathMatch(.*)*", redirect: "/courses" }
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
