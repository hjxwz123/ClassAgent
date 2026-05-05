import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { useSessionStore } from "../stores/session";
import type { Role } from "../types";
import { adminRoutes } from "./routes/admin";
import { studentRoutes } from "./routes/student";
import { teacherRoutes } from "./routes/teacher";
import { defaultRouteForRole, routeByPage } from "./pageMap";

const AuthView = () => import("../views/AuthView.vue");
const ProductHomeView = () => import("../views/ProductHomeView.vue");

export { defaultRouteForRole, routeByPage };

const routes: RouteRecordRaw[] = [
  { path: "/", component: ProductHomeView, meta: { public: true, shellKey: "product-home" } },
  { path: "/auth", component: AuthView, meta: { public: true, guestOnly: true, shellKey: "auth" } },
  ...studentRoutes,
  ...teacherRoutes,
  ...adminRoutes,
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
    if (to.meta.guestOnly && session.user) return defaultRouteForRole(session.user.role);
    return true;
  }
  if (to.meta.requiresAuth && !session.user) return "/auth";
  const roles = to.meta.roles as Role[] | undefined;
  if (roles && session.user && !roles.includes(session.user.role)) return defaultRouteForRole(session.user.role);
  return true;
});
