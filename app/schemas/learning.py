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
    knowledge_point_ids: list[int] | None = None
    title: str = Field(min_length=2, max_length=255)
    quiz_type: str = "course"
    question_count: int = Field(default=5, ge=1, le=20)
    question_type_counts: dict[str, int] | None = None
    prefer_weak_points: bool = False
    # mixed=易:中:难≈3:5:2 梯度组卷；easy/standard/hard 为整卷单一难度
    difficulty: str = "mixed"
    # 用户自定义出题要求（如"多考应用题""侧重第3章"），仅作为补充提示，不覆盖上述结构化约束
    custom_instructions: str | None = Field(default=None, max_length=300)


class WeakQuizGenerateRequest(BaseModel):
    course_id: int
    weak_point_id: int | None = None
    weak_point_ids: list[int] | None = None
    all_weak_points: bool = False
    # 针对"未标注知识点"的错题（没有真实 KnowledgePoint 可用）单独生成练习；为 True 时忽略
    # weak_point_id/weak_point_ids/all_weak_points，走错题原题变式生成而非知识点出题路径。
    target_untagged: bool = False
    title: str | None = Field(default=None, min_length=2, max_length=255)
    question_count: int = Field(default=5, ge=1, le=20)
    question_type_counts: dict[str, int] | None = None
    difficulty: str = "mixed"
    custom_instructions: str | None = Field(default=None, max_length=300)


class QuizQuestionPayload(ORMModel):
    id: int
    quiz_id: int
    course_id: int
    chapter_id: int | None
    knowledge_point_id: int | None
    # 由接口层按 knowledge_point_id 补名称，供教师审核界面展示知识点徽标
    knowledge_point_name: str | None = None
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


class AsyncTaskResponse(ORMModel):
    id: int
    task_name: str
    target_type: str
    target_id: int | None
    status: str
    detail: dict | None
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
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)


class QuizRetakeRequest(BaseModel):
    # full=整卷重做；wrong=只重做某次作答中的错题（默认取最近一次作答）
    mode: str = Field(default="full", pattern="^(full|wrong)$")
    attempt_id: int | None = None


class QuizAttemptResponse(ORMModel):
    id: int
    quiz_id: int
    user_id: int
    score: float
    total_score: float
    accuracy: float
    ai_feedback: str | None
    submitted_at: datetime | None
    duration_seconds: int | None = None
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
    # 掌握状态机：pending=未掌握 / consolidating=巩固中(复习曲线进行中) / resolved=已掌握(走完整条曲线)
    correct_streak: int = 0
    mastery: str = "pending"
    knowledge_point_id: int | None = None
    knowledge_point_name: str | None = None
    last_attempt_id: int | None = None
    resolved_at: datetime | None = None
    last_wrong_at: datetime | None = None
    last_correct_at: datetime | None = None
    # 艾宾浩斯遗忘曲线复习调度：next_review_at=下次应复习时间；is_due=是否已到期待复习；
    # review_stage=已走过档位(=correct_streak)，review_total=曲线总档数。
    next_review_at: datetime | None = None
    is_due: bool = False
    review_stage: int = 0
    review_total: int = 6
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WeakPointResponse(BaseModel):
    knowledge_point: str
    wrong_count: int = 0
    knowledge_point_id: int | None = None
    learning_signal_count: int = 0
    qa_signal_count: int = 0
    signal_score: float = 0.0
    weak_score: float = 0.0


class LearningRecordResponse(BaseModel):
    progress_count: int
    qa_count: int
    problem_count: int
    attempt_count: int
    recent_progress: list[dict] = Field(default_factory=list)
    recent_qa: list[dict] = Field(default_factory=list)
    recent_problems: list[dict] = Field(default_factory=list)
    recent_attempts: list[dict] = Field(default_factory=list)
