import type { Role } from "../types";

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
