import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useSessionStore } from "../stores/session";
import type { Role } from "../types";
import AuthView from "../views/AuthView.vue";
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
  if (role === "admin") return routeByPage.adminUsers;
  return routeByPage.courses;
}

const workspaceRoute = (path: string, pageKey: string, roles: Role[]): RouteRecordRaw => ({
  path,
  component: WorkspaceView,
  props: { pageKey },
  meta: { requiresAuth: true, roles, pageKey }
});

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/courses" },
  { path: "/auth", component: AuthView, meta: { public: true } },
  workspaceRoute("/courses", "courses", ["student", "teacher"]),
  workspaceRoute("/courses/detail", "courseDetail", ["student", "teacher"]),
  workspaceRoute("/materials", "materials", ["student", "teacher"]),
  workspaceRoute("/lessons", "lessons", ["student", "teacher"]),
  workspaceRoute("/qa", "qa", ["student"]),
  workspaceRoute("/tutoring", "tutoring", ["student"]),
  workspaceRoute("/learning", "learning", ["student", "teacher"]),
  workspaceRoute("/plans", "plans", ["student"]),
  workspaceRoute("/analytics", "analytics", ["teacher"]),
  workspaceRoute("/profile", "profile", ["student", "teacher", "admin"]),
  workspaceRoute("/admin/users", "adminUsers", ["admin"]),
  workspaceRoute("/admin/courses", "adminCourses", ["admin"]),
  workspaceRoute("/admin/materials", "adminMaterials", ["admin"]),
  workspaceRoute("/admin/models", "adminModels", ["admin"]),
  workspaceRoute("/admin/services", "adminServices", ["admin"]),
  workspaceRoute("/admin/system", "adminSystem", ["admin"]),
  workspaceRoute("/admin/monitor", "adminMonitor", ["admin"]),
  workspaceRoute("/admin/logs", "adminLogs", ["admin"]),
  workspaceRoute("/admin/backups", "adminBackups", ["admin"]),
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
