import type { RouteRecordRaw } from "vue-router";

const StudentView = () => import("../../views/StudentView.vue");

const studentRoute = (path: string, pageKey: string): RouteRecordRaw => ({
  path,
  component: StudentView,
  props: { pageKey },
  meta: { requiresAuth: true, roles: ["student"], pageKey, shellKey: "student" }
});

export const studentRoutes: RouteRecordRaw[] = [
  studentRoute("/home", "studentHome"),
  studentRoute("/courses", "studentCourses"),
  { path: "/courses/detail", redirect: "/courses" },
  studentRoute("/courses/:courseId", "studentCourseHome"),
  studentRoute("/materials", "studentMaterials"),
  studentRoute("/lessons/:lessonId", "studentLessonStudy"),
  studentRoute("/lessons", "studentCourseHome"),
  studentRoute("/qa/:conversationId", "studentQa"),
  studentRoute("/qa", "studentQa"),
  studentRoute("/tutoring", "studentTutoring"),
  studentRoute("/knowledge", "studentKnowledge"),
  studentRoute("/quizzes", "studentQuizzes"),
  studentRoute("/wrong-book", "studentWrongBook"),
  studentRoute("/learning", "studentQuizzes"),
  studentRoute("/plans", "studentPlans"),
  studentRoute("/profile", "studentProfile")
];
