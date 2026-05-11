import { defineAsyncComponent } from "vue";
import type { RouteRecordRaw } from "vue-router";
import PageLoader from "../../components/PageLoader.vue";

const TeacherView = defineAsyncComponent({
  loader: () => import("../../views/TeacherView.vue"),
  loadingComponent: PageLoader,
  delay: 0,
  suspensible: false
});

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
  teacherRoute("/teacher/weak-quizzes", "teacherWeakQuizzes"),
  teacherRoute("/teacher/profile", "teacherProfile")
];
