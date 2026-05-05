import type { RouteRecordRaw } from "vue-router";

const TeacherView = () => import("../../views/TeacherView.vue");

const teacherRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: TeacherView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["teacher"], pageKey, shellKey: "teacher" }
});

export const teacherRoutes: RouteRecordRaw[] = [
  teacherRoute("/teacher", "teacherDashboard"),
  teacherRoute("/teacher/courses", "teacherCourses"),
  teacherRoute("/teacher/courses/new", "teacherCourseForm"),
  teacherRoute("/teacher/course", "teacherCourseHome"),
  teacherRoute("/teacher/materials", "teacherMaterials"),
  teacherRoute("/teacher/materials/workbench", "teacherPpt"),
  teacherRoute("/teacher/lessons", "teacherLessons"),
  teacherRoute("/teacher/students", "teacherStudents"),
  teacherRoute("/teacher/analytics", "teacherAnalytics"),
  teacherRoute("/teacher/profile", "teacherProfile")
];
