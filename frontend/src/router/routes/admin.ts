import { defineAsyncComponent } from "vue";
import type { RouteRecordRaw } from "vue-router";
import PageLoader from "../../components/PageLoader.vue";

const AdminView = defineAsyncComponent({
  loader: () => import("../../views/AdminView.vue"),
  loadingComponent: PageLoader,
  delay: 0,
  suspensible: false
});

const adminRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: AdminView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["admin"], pageKey, shellKey: "admin" }
});

export const adminRoutes: RouteRecordRaw[] = [
  adminRoute("/admin", "adminDashboard"),
  adminRoute("/admin/users", "adminUsers"),
  adminRoute("/admin/courses", "adminCourses"),
  adminRoute("/admin/materials", "adminMaterials"),
  adminRoute("/admin/models", "adminModels"),
  adminRoute("/admin/services", "adminServices"),
  adminRoute("/admin/system", "adminSystem"),
  adminRoute("/admin/monitor", "adminMonitor"),
  adminRoute("/admin/logs", "adminLogs"),
  adminRoute("/admin/backups", "adminBackups")
];
