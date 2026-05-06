export type Role = "student" | "teacher" | "admin";

export type ApiResponse<T> = {
  code: number;
  message: string;
  data: T;
  request_id?: string;
};

export type User = {
  id: number;
  email: string;
  role: Role;
  status: string;
  nickname: string;
  avatar_url?: string | null;
  student_no?: string | null;
  employee_no?: string | null;
  bio?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type Course = {
  id: number;
  name: string;
  description?: string | null;
  term: string;
  course_code: string;
  teacher_id: number;
  status: string;
  cover_url?: string | null;
  cover_color?: string | null;
  allow_general_ai_answer?: boolean;
  created_at: string;
  updated_at: string;
};

export type Chapter = {
  id: number;
  course_id: number;
  title: string;
  description?: string | null;
  order_index: number;
  created_at: string;
  updated_at: string;
};

export type CourseDetail = {
  course: Course;
  teacher: User;
  chapters: Chapter[];
  student_count: number;
};

export type Material = {
  id: number;
  course_id: number;
  chapter_id?: number | null;
  title: string;
  category: string;
  material_type: string;
  size_bytes: number;
  original_filename: string;
  preview_url?: string | null;
  parse_status: string;
  vector_status: string;
  extracted_text?: string | null;
  created_at: string;
  updated_at: string;
};

export type LessonPage = {
  id: number;
  lesson_id: number;
  page_number: number;
  page_title?: string | null;
  page_text: string;
  script_text?: string | null;
  script_status: string;
  audio_url?: string | null;
  audio_duration_seconds?: number | null;
  subtitle_text?: string | null;
};

export type MaterialDetail = {
  material: Material;
  lesson_id?: number | null;
  lesson_status?: string | null;
  lesson_page_count: number;
  pages: LessonPage[];
};

export type Lesson = {
  id: number;
  course_id: number;
  chapter_id?: number | null;
  material_id?: number | null;
  title: string;
  summary?: string | null;
  page_count: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Quiz = {
  id: number;
  course_id: number;
  chapter_id?: number | null;
  title: string;
  description?: string | null;
  quiz_type: string;
  status: string;
  total_score: number;
  metadata_json?: Record<string, unknown> | null;
  published_at?: string | null;
  attempts?: Array<Record<string, any>>;
  latest_attempt?: Record<string, any> | null;
  attempt_count?: number;
  has_attempted?: boolean;
  created_at: string;
  updated_at: string;
};
