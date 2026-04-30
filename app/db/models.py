from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    BackupStatus,
    ConfigScope,
    CourseStatus,
    LessonStatus,
    MaterialCategory,
    MaterialType,
    ProblemSourceType,
    ProcessStatus,
    QAFeedback,
    QuestionType,
    QuizStatus,
    QuizType,
    StudyPlanStatus,
    TaskStatus,
    UserRole,
    UserStatus,
)
from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.STUDENT.value)
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.ACTIVE.value)
    nickname: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    student_no: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    employee_no: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "preference_key", name="uq_user_preference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    preference_key: Mapped[str] = mapped_column(String(128), index=True)
    preference_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)


class EmailCode(TimestampMixin, Base):
    __tablename__ = "email_codes"
    __table_args__ = (UniqueConstraint("email", "purpose", "code", name="uq_email_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    purpose: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Course(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    term: Mapped[str] = mapped_column(String(64))
    course_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=CourseStatus.ACTIVE.value)


class CourseMembership(TimestampMixin, Base):
    __tablename__ = "course_memberships"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.STUDENT.value)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=1)


class CourseMaterial(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "course_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(32), default=MaterialCategory.COURSEWARE.value)
    material_type: Mapped[str] = mapped_column(String(32), default=MaterialType.PDF.value)
    size_bytes: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    preview_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(32), default=ProcessStatus.PENDING.value)
    vector_status: Mapped[str] = mapped_column(String(32), default=ProcessStatus.PENDING.value)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class Lesson(TimestampMixin, Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("course_materials.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=LessonStatus.DRAFT.value)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LessonPage(TimestampMixin, Base):
    __tablename__ = "lesson_pages"
    __table_args__ = (UniqueConstraint("lesson_id", "page_number", name="uq_lesson_page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    page_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_text: Mapped[str] = mapped_column(Text)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_status: Mapped[str] = mapped_column(String(32), default=ProcessStatus.PENDING.value)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    subtitle_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class PageNote(TimestampMixin, Base):
    __tablename__ = "page_notes"
    __table_args__ = (UniqueConstraint("user_id", "lesson_page_id", name="uq_page_note"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    lesson_page_id: Mapped[int] = mapped_column(ForeignKey("lesson_pages.id"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")


class KnowledgeChunk(TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("course_materials.id"), nullable=True, index=True)
    lesson_page_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_pages.id"), nullable=True, index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LearningProgress(TimestampMixin, Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("lesson_id", "user_id", name="uq_learning_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    current_page: Mapped[int] = mapped_column(Integer, default=1)
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    total_study_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_from_page: Mapped[int | None] = mapped_column(Integer, nullable=True)


class QAConversation(TimestampMixin, Base):
    __tablename__ = "qa_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))


class QARecord(TimestampMixin, Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("qa_conversations.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lesson_page_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_pages.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    is_out_of_scope: Mapped[bool] = mapped_column(Boolean, default=False)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str] = mapped_column(String(32), default=QAFeedback.NEUTRAL.value)
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProblemRecord(TimestampMixin, Base):
    __tablename__ = "problem_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), default=ProblemSourceType.TEXT.value)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    common_mistakes: Mapped[list | None] = mapped_column(JSON, nullable=True)


class ProblemGuidance(TimestampMixin, Base):
    __tablename__ = "problem_guidance"
    __table_args__ = (UniqueConstraint("problem_id", "level", name="uq_problem_level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problem_records.id"), index=True)
    level: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    similar_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)


class KnowledgePoint(TimestampMixin, Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_by_level: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Quiz(TimestampMixin, Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quiz_type: Mapped[str] = mapped_column(String(32), default=QuizType.COURSE.value)
    status: Mapped[str] = mapped_column(String(32), default=QuizStatus.DRAFT.value)
    total_score: Mapped[float] = mapped_column(Float, default=100)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizQuestion(TimestampMixin, Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id"), nullable=True, index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    question_type: Mapped[str] = mapped_column(String(32), default=QuestionType.SINGLE_CHOICE.value)
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reference_answer: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=10)
    difficulty: Mapped[str] = mapped_column(String(32), default="standard")


class QuizAttempt(TimestampMixin, Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    total_score: Mapped[float] = mapped_column(Float, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizAnswer(TimestampMixin, Base):
    __tablename__ = "quiz_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("quiz_attempts.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    user_answer: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)


class WrongQuestion(TimestampMixin, Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_wrong_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    knowledge_point_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"), nullable=True, index=True)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("quiz_attempts.id"), nullable=True)


class StudyPlan(TimestampMixin, Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    goal: Mapped[str] = mapped_column(Text)
    available_days: Mapped[int] = mapped_column(Integer, default=7)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(32), default=StudyPlanStatus.ACTIVE.value)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class StudyPlanTask(TimestampMixin, Base):
    __tablename__ = "study_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("study_plans.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    task_date: Mapped[str] = mapped_column(String(32))
    task_type: Mapped[str] = mapped_column(String(64))
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.TODO.value)


class StudyCheckin(TimestampMixin, Base):
    __tablename__ = "study_checkins"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_checkin"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("study_plan_tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ModelConfig(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model_name: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ServiceConfig(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "service_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), default=ConfigScope.SERVICE.value)
    service_type: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="aliyun")
    name: Mapped[str] = mapped_column(String(128))
    config_encrypted: Mapped[str] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (UniqueConstraint("setting_key", name="uq_setting_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64), default=ConfigScope.SYSTEM.value)
    setting_key: Mapped[str] = mapped_column(String(128), index=True)
    setting_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperationLog(TimestampMixin, Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class LoginLog(TimestampMixin, Base):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)


class ApiRequestLog(TimestampMixin, Base):
    __tablename__ = "api_request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(255), index=True)
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[float] = mapped_column(Float)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class AIUsageLog(TimestampMixin, Base):
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(128))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AsyncTaskLog(TimestampMixin, Base):
    __tablename__ = "async_task_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_name: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ProcessStatus.PENDING.value)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SystemErrorLog(TimestampMixin, Base):
    __tablename__ = "system_error_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(32), default="error")
    source: Mapped[str] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class BackupRecord(TimestampMixin, Base):
    __tablename__ = "backup_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    trigger_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=BackupStatus.PENDING.value)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
