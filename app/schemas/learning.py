from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class KnowledgePointResponse(ORMModel):
    id: int
    course_id: int
    chapter_id: int | None
    name: str
    description: str | None
    content_by_level: dict | None
    created_at: datetime
    updated_at: datetime


class QuizGenerateRequest(BaseModel):
    course_id: int
    chapter_id: int | None = None
    chapter_ids: list[int] | None = None
    title: str = Field(min_length=2, max_length=255)
    quiz_type: str = "course"
    question_count: int = Field(default=5, ge=1, le=20)
    prefer_weak_points: bool = False


class QuizQuestionPayload(ORMModel):
    id: int
    quiz_id: int
    course_id: int
    chapter_id: int | None
    knowledge_point_id: int | None
    question_type: str
    stem: str
    options: list | None
    reference_answer: dict | list | str | None
    explanation: str | None
    score: float
    difficulty: str
    created_at: datetime
    updated_at: datetime


class QuizResponse(ORMModel):
    id: int
    course_id: int
    chapter_id: int | None
    creator_id: int
    title: str
    description: str | None
    quiz_type: str
    status: str
    total_score: float
    metadata_json: dict | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QuizDetailResponse(BaseModel):
    quiz: QuizResponse
    questions: list[QuizQuestionPayload]


class QuizQuestionEditPayload(BaseModel):
    id: int | None = None
    chapter_id: int | None = None
    knowledge_point_id: int | None = None
    question_type: str = Field(default="single_choice", max_length=32)
    stem: str = Field(min_length=1, max_length=4000)
    options: list | None = None
    reference_answer: dict | list | str | bool | int | float | None = None
    explanation: str | None = Field(default=None, max_length=4000)
    score: float = Field(default=10, gt=0, le=100)
    difficulty: str = Field(default="standard", max_length=32)


class QuizEditRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    questions: list[QuizQuestionEditPayload] = Field(min_length=1, max_length=50)


class QuizSubmitRequest(BaseModel):
    answers: list[dict]


class QuizAttemptResponse(ORMModel):
    id: int
    quiz_id: int
    user_id: int
    score: float
    total_score: float
    accuracy: float
    ai_feedback: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StudyPlanCreateRequest(BaseModel):
    course_id: int
    title: str = Field(min_length=2, max_length=255)
    goal: str = Field(min_length=2, max_length=2000)
    available_days: int = Field(default=7, ge=1, le=60)
    daily_minutes: int = Field(default=30, ge=10, le=240)


class StudyPlanResponse(ORMModel):
    id: int
    user_id: int
    course_id: int
    title: str
    goal: str
    available_days: int
    daily_minutes: int
    status: str
    summary: str | None
    created_at: datetime
    updated_at: datetime


class StudyPlanTaskResponse(ORMModel):
    id: int
    plan_id: int
    title: str
    task_date: str
    task_type: str
    estimated_minutes: int
    metadata_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


class TaskCheckinRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class WrongQuestionResponse(BaseModel):
    wrong_question_id: int
    question: QuizQuestionPayload
    wrong_count: int
    history_count: int | None = None
    is_resolved: bool = False
    knowledge_point_id: int | None = None
    knowledge_point_name: str | None = None
    last_attempt_id: int | None = None
    resolved_at: datetime | None = None
    last_wrong_at: datetime | None = None
    last_correct_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WeakPointResponse(BaseModel):
    knowledge_point: str
    wrong_count: int


class LearningRecordResponse(BaseModel):
    progress_count: int
    qa_count: int
    problem_count: int
    attempt_count: int
    recent_progress: list[dict] = Field(default_factory=list)
    recent_qa: list[dict] = Field(default_factory=list)
    recent_problems: list[dict] = Field(default_factory=list)
    recent_attempts: list[dict] = Field(default_factory=list)
