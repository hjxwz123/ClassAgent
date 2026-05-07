from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class CourseStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class MaterialCategory(StrEnum):
    COURSEWARE = "courseware"
    HANDOUT = "handout"
    EXERCISE = "exercise"
    REFERENCE = "reference"


class MaterialType(StrEnum):
    PPTX = "pptx"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"


class ProcessStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class LessonStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PUBLISHED = "published"


class QAFeedback(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ProblemSourceType(StrEnum):
    TEXT = "text"
    IMAGE = "image"


class LearningSignalSource(StrEnum):
    QA = "qa"
    TUTORING = "tutoring"


class QuizType(StrEnum):
    COURSE = "course"
    PRACTICE = "practice"
    WRONG_BOOK = "wrong_book"


class QuizStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    CLOSED = "closed"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    JUDGE = "judge"
    BLANK = "blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class StudyPlanStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    TODO = "todo"
    DONE = "done"
    SKIPPED = "skipped"


class ConfigScope(StrEnum):
    MODEL = "model"
    SERVICE = "service"
    SYSTEM = "system"


class BackupStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
