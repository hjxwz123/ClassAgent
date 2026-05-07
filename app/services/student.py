from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.enums import CourseStatus, LessonStatus, ProcessStatus, QuizStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import (
    Chapter,
    Course,
    CourseMaterial,
    CourseMembership,
    KnowledgePoint,
    LearningProgress,
    Lesson,
    LessonPage,
    PageNote,
    ProblemRecord,
    QARecord,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    StudyCheckin,
    StudyPlan,
    StudyPlanTask,
    User,
    UserPreference,
    WrongQuestion,
)
from app.services.ai import ai_service
from app.services.courses import _get_course_or_404
from app.services.notifications import active_system_announcement, apply_user_notification_reads, list_user_notifications, mark_user_notifications_read
from app.services.storage import storage_service


STUDENT_PROFILE_KEY = "student.profile"
STUDENT_NOTICE_KEY = "student.notifications"
STUDENT_REMINDER_KEY = "student.teacher_reminders"

DEFAULT_STUDENT_NOTICES = [
    {"key": "lesson", "label": "新课时发布", "enabled": True},
    {"key": "quiz", "label": "测验发布提醒", "enabled": True},
    {"key": "qa", "label": "AI 问答完成", "enabled": True},
    {"key": "teacher", "label": "教师提醒", "enabled": True},
    {"key": "system", "label": "系统公告", "enabled": True},
    {"key": "plan", "label": "学习计划提醒", "enabled": True, "time": "20:00"},
]


def _published_lesson_order():
    return (case((Lesson.published_at.is_(None), 1), else_=0), Lesson.published_at.desc(), Lesson.created_at.desc())


def _as_dict(item) -> dict:
    data = dict(item.__dict__)
    data.pop("_sa_instance_state", None)
    if "preview_url" in data:
        data["preview_url"] = storage_service.normalize_public_url(data["preview_url"])
    if "audio_url" in data:
        data["audio_url"] = storage_service.normalize_public_url(data["audio_url"])
    if "cover_url" in data:
        data["cover_url"] = storage_service.normalize_public_url(data["cover_url"])
    return data


def _assert_student(user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可访问")


def _assert_joined(db: Session, *, course_id: int, user: User) -> Course:
    _assert_student(user)
    course = _get_course_or_404(db, course_id)
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可访问已加入课程")
    return course


def _preference(db: Session, *, user_id: int, key: str):
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.preference_key == key))
    return item.preference_value if item is not None else None


def _set_preference(db: Session, *, user_id: int, key: str, value) -> None:
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.preference_key == key))
    if item is None:
        item = UserPreference(user_id=user_id, preference_key=key, preference_value=value)
    else:
        item.preference_value = value
    db.add(item)


def _joined_courses(db: Session, user: User) -> list[Course]:
    _assert_student(user)
    return list(
        db.scalars(
            select(Course)
            .join(CourseMembership, CourseMembership.course_id == Course.id)
            .where(CourseMembership.user_id == user.id, Course.deleted_at.is_(None))
            .order_by(CourseMembership.joined_at.desc())
        )
    )


def _teacher(db: Session, course: Course) -> User | None:
    return db.get(User, course.teacher_id)


def _course_student_total(db: Session, course_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(CourseMembership.id)).where(
                CourseMembership.course_id == course_id,
                CourseMembership.role == UserRole.STUDENT.value,
            )
        )
        or 0
    )


def _course_summary_context(db: Session, *, courses: list[Course], user_id: int) -> dict:
    course_ids = [course.id for course in courses]
    if not course_ids:
        return {
            "teachers": {},
            "student_counts": {},
            "material_counts": {},
            "qa_counts": {},
            "wrong_counts": {},
            "progress": {},
            "last_lessons": {},
        }

    teacher_ids = sorted({course.teacher_id for course in courses})
    teachers = {teacher.id: teacher for teacher in db.scalars(select(User).where(User.id.in_(teacher_ids)))} if teacher_ids else {}
    student_counts = {
        int(course_id): int(count or 0)
        for course_id, count in db.execute(
            select(CourseMembership.course_id, func.count(CourseMembership.id))
            .where(CourseMembership.course_id.in_(course_ids), CourseMembership.role == UserRole.STUDENT.value)
            .group_by(CourseMembership.course_id)
        )
    }
    material_counts = {
        int(course_id): int(count or 0)
        for course_id, count in db.execute(
            select(CourseMaterial.course_id, func.count(CourseMaterial.id))
            .where(CourseMaterial.course_id.in_(course_ids), CourseMaterial.deleted_at.is_(None))
            .group_by(CourseMaterial.course_id)
        )
    }
    qa_counts = {
        int(course_id): int(count or 0)
        for course_id, count in db.execute(
            select(QARecord.course_id, func.count(QARecord.id))
            .where(QARecord.course_id.in_(course_ids), QARecord.user_id == user_id)
            .group_by(QARecord.course_id)
        )
    }
    wrong_counts = {
        int(course_id): int(count or 0)
        for course_id, count in db.execute(
            select(WrongQuestion.course_id, func.sum(WrongQuestion.wrong_count))
            .where(WrongQuestion.course_id.in_(course_ids), WrongQuestion.user_id == user_id)
            .group_by(WrongQuestion.course_id)
        )
    }

    lessons_by_course: dict[int, list[Lesson]] = {course_id: [] for course_id in course_ids}
    lesson_by_id: dict[int, Lesson] = {}
    for lesson in db.scalars(select(Lesson).where(Lesson.course_id.in_(course_ids), Lesson.status == LessonStatus.PUBLISHED.value)):
        lessons_by_course.setdefault(lesson.course_id, []).append(lesson)
        lesson_by_id[lesson.id] = lesson

    progress_rows = list(
        db.execute(
            select(LearningProgress, Lesson.course_id)
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(
                LearningProgress.user_id == user_id,
                Lesson.course_id.in_(course_ids),
                Lesson.status == LessonStatus.PUBLISHED.value,
            )
        )
    )
    progress_items: dict[int, list[LearningProgress]] = defaultdict(list)
    for progress, course_id in progress_rows:
        progress_items[int(course_id)].append(progress)

    progress_by_course: dict[int, dict] = {}
    last_lessons: dict[int, Lesson] = {}
    for course_id in course_ids:
        lessons = lessons_by_course.get(course_id, [])
        progresses = progress_items.get(course_id, [])
        last_progress = max(progresses, key=lambda item: item.updated_at, default=None)
        progress_by_course[course_id] = {
            "lesson_total": len(lessons),
            "completed_lessons": len([item for item in progresses if item.completed_at is not None or item.progress_percent >= 100]),
            "studied_lessons": len([item for item in progresses if item.progress_percent > 0]),
            "progress_percent": round(sum(item.progress_percent for item in progresses) / max(len(lessons), 1), 2) if lessons else 0,
            "study_seconds": int(sum(item.total_study_seconds or 0 for item in progresses)),
            "last_progress": _as_dict(last_progress) if last_progress else None,
        }
        if last_progress and last_progress.lesson_id in lesson_by_id:
            last_lessons[course_id] = lesson_by_id[last_progress.lesson_id]

    return {
        "teachers": teachers,
        "student_counts": student_counts,
        "material_counts": material_counts,
        "qa_counts": qa_counts,
        "wrong_counts": wrong_counts,
        "progress": progress_by_course,
        "last_lessons": last_lessons,
    }


def _course_summary_with_context(*, course: Course, context: dict) -> dict:
    progress = context["progress"].get(
        course.id,
        {
            "lesson_total": 0,
            "completed_lessons": 0,
            "studied_lessons": 0,
            "progress_percent": 0,
            "study_seconds": 0,
            "last_progress": None,
        },
    )
    teacher = context["teachers"].get(course.teacher_id)
    last_lesson = context["last_lessons"].get(course.id)
    data = _as_dict(course)
    data.update(
        {
            "teacher": _as_dict(teacher) if teacher else None,
            "student_count": context["student_counts"].get(course.id, 0),
            "material_count": context["material_counts"].get(course.id, 0),
            "qa_count": context["qa_counts"].get(course.id, 0),
            "wrong_count": context["wrong_counts"].get(course.id, 0),
            **progress,
        }
    )
    data["last_lesson"] = _as_dict(last_lesson) if last_lesson else None
    return data


def list_student_course_summaries(db: Session, user: User) -> list[dict]:
    courses = _joined_courses(db, user)
    context = _course_summary_context(db, courses=courses, user_id=user.id)
    return [_course_summary_with_context(course=course, context=context) for course in courses]


def preview_course_by_code(db: Session, *, course_code: str, user: User) -> dict:
    _assert_student(user)
    course = db.scalar(select(Course).where(Course.course_code == course_code.upper(), Course.deleted_at.is_(None)))
    if course is None or course.status != CourseStatus.ACTIVE.value:
        raise not_found("课程码不存在或已停用")
    teacher = _teacher(db, course)
    joined = db.scalar(select(CourseMembership.id).where(CourseMembership.course_id == course.id, CourseMembership.user_id == user.id))
    return {
        "course": _as_dict(course),
        "teacher": _as_dict(teacher) if teacher else None,
        "student_count": _course_student_total(db, course.id),
        "lesson_count": int(db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id == course.id, Lesson.status == LessonStatus.PUBLISHED.value)) or 0),
        "already_joined": joined is not None,
    }


def _recent_lesson(db: Session, *, course_ids: list[int], user: User) -> dict | None:
    if not course_ids:
        return None
    row = db.execute(
        select(LearningProgress, Lesson, Course)
        .join(Lesson, Lesson.id == LearningProgress.lesson_id)
        .join(Course, Course.id == Lesson.course_id)
        .where(LearningProgress.user_id == user.id, Lesson.course_id.in_(course_ids), Lesson.status == LessonStatus.PUBLISHED.value)
        .order_by(LearningProgress.updated_at.desc())
        .limit(1)
    ).first()
    if row:
        progress, lesson, course = row
        return {"progress": _as_dict(progress), "lesson": _as_dict(lesson), "course": _as_dict(course)}
    lesson_row = db.execute(
        select(Lesson, Course)
        .join(Course, Course.id == Lesson.course_id)
        .where(Lesson.course_id.in_(course_ids), Lesson.status == LessonStatus.PUBLISHED.value)
        .order_by(*_published_lesson_order())
        .limit(1)
    ).first()
    if not lesson_row:
        return None
    lesson, course = lesson_row
    return {"progress": None, "lesson": _as_dict(lesson), "course": _as_dict(course)}


def _today_tasks(db: Session, user: User) -> list[dict]:
    today = datetime.now(UTC).date().isoformat()
    rows = list(
        db.execute(
            select(StudyPlanTask, StudyPlan)
            .join(StudyPlan, StudyPlan.id == StudyPlanTask.plan_id)
            .where(StudyPlan.user_id == user.id, StudyPlanTask.task_date == today)
            .order_by(StudyPlanTask.id.asc())
        )
    )
    return [{**_as_dict(task), "plan": _as_dict(plan)} for task, plan in rows]


def _learning_stats(db: Session, *, user: User, course_ids: list[int]) -> dict:
    if not course_ids:
        return {"study_hours": 0, "completion_rate": 0, "accuracy": 0, "qa_count": 0, "wrong_count": 0, "streak_days": 0}
    progress_rows = list(
        db.scalars(
            select(LearningProgress)
            .join(Lesson, Lesson.id == LearningProgress.lesson_id)
            .where(LearningProgress.user_id == user.id, Lesson.course_id.in_(course_ids))
        )
    )
    lesson_total = int(
        db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id.in_(course_ids), Lesson.status == LessonStatus.PUBLISHED.value)) or 0
    )
    completed = len([item for item in progress_rows if item.completed_at is not None or item.progress_percent >= 100])
    attempts = list(
        db.scalars(
            select(QuizAttempt)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(QuizAttempt.user_id == user.id, Quiz.course_id.in_(course_ids))
        )
    )
    checkins = list(db.scalars(select(StudyCheckin).where(StudyCheckin.user_id == user.id).order_by(StudyCheckin.checked_in_at.desc())))
    checkin_days = {item.checked_in_at.date().isoformat() for item in checkins}
    streak = 0
    cursor = datetime.now(UTC).date()
    while cursor.isoformat() in checkin_days:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "study_hours": round(sum(item.total_study_seconds for item in progress_rows) / 3600, 1),
        "completion_rate": round(completed / max(lesson_total, 1) * 100, 2) if lesson_total else 0,
        "accuracy": round(sum(item.accuracy for item in attempts) / max(len(attempts), 1), 2) if attempts else 0,
        "qa_count": int(db.scalar(select(func.count(QARecord.id)).where(QARecord.user_id == user.id, QARecord.course_id.in_(course_ids))) or 0),
        "wrong_count": int(db.scalar(select(func.sum(WrongQuestion.wrong_count)).where(WrongQuestion.user_id == user.id, WrongQuestion.course_id.in_(course_ids))) or 0),
        "streak_days": streak,
    }


def _activities(db: Session, *, user: User, course_ids: list[int], limit: int = 8) -> list[dict]:
    if not course_ids:
        return []
    activities: list[dict] = []
    for progress, lesson in db.execute(
        select(LearningProgress, Lesson)
        .join(Lesson, Lesson.id == LearningProgress.lesson_id)
        .where(LearningProgress.user_id == user.id, Lesson.course_id.in_(course_ids))
        .order_by(LearningProgress.updated_at.desc())
        .limit(limit)
    ):
        activities.append({"type": "lesson", "title": f"学习 {lesson.title}", "meta": f"{progress.progress_percent}%", "time": progress.updated_at})
    for record in db.scalars(select(QARecord).where(QARecord.user_id == user.id, QARecord.course_id.in_(course_ids)).order_by(QARecord.created_at.desc()).limit(limit)):
        activities.append({"type": "qa", "title": record.question, "meta": "AI 问答", "time": record.created_at})
    for attempt, quiz in db.execute(
        select(QuizAttempt, Quiz)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.user_id == user.id, Quiz.course_id.in_(course_ids))
        .order_by(QuizAttempt.created_at.desc())
        .limit(limit)
    ):
        activities.append({"type": "quiz", "title": f"提交 {quiz.title}", "meta": f"{attempt.score}分", "time": attempt.created_at})
    for problem in db.scalars(select(ProblemRecord).where(ProblemRecord.user_id == user.id, ProblemRecord.course_id.in_(course_ids)).order_by(ProblemRecord.created_at.desc()).limit(limit)):
        activities.append({"type": "tutoring", "title": (problem.corrected_text or problem.ocr_text or problem.raw_text or "题目辅导")[:48], "meta": "AI 辅导", "time": problem.created_at})
    return sorted(activities, key=lambda item: item["time"], reverse=True)[:limit]


def get_student_dashboard(db: Session, user: User) -> dict:
    courses = list_student_course_summaries(db, user)
    course_ids = [course["id"] for course in courses]
    tasks = _today_tasks(db, user)
    stats = _learning_stats(db, user=user, course_ids=course_ids)
    weak = []
    if course_ids:
        point_name = func.coalesce(KnowledgePoint.name, "未标注知识点")
        rows = db.execute(
            select(point_name, func.sum(WrongQuestion.wrong_count))
            .select_from(WrongQuestion)
            .outerjoin(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
            .outerjoin(
                KnowledgePoint,
                KnowledgePoint.id == func.coalesce(WrongQuestion.knowledge_point_id, QuizQuestion.knowledge_point_id),
            )
            .where(WrongQuestion.user_id == user.id, WrongQuestion.course_id.in_(course_ids))
            .group_by(point_name)
            .order_by(func.sum(WrongQuestion.wrong_count).desc(), point_name.asc())
            .limit(5)
        )
        weak = [{"name": name, "count": int(count or 0)} for name, count in rows]
    recent_lesson = _recent_lesson(db, course_ids=course_ids, user=user)
    recommendation = {
        "text": "",
        "lesson": recent_lesson,
        "weak_points": weak,
        "status": "no_courses" if not course_ids else "ready",
        "based_on": {
            "courses": len(course_ids),
            "today_tasks": len(tasks),
            "weak_points": len(weak),
            "stats": bool(course_ids),
        },
    }
    if course_ids:
        recommendation["text"] = ai_service.generate_student_recommendation(
            course_count=len(course_ids),
            pending_tasks=len([task for task in tasks if task.get("status") != "done"]),
            recent_lesson_title=recent_lesson["lesson"]["title"] if recent_lesson else None,
            weak_points=[item["name"] for item in weak],
            study_hours=stats["study_hours"],
            completion_rate=stats["completion_rate"],
            accuracy=stats["accuracy"],
            db=db,
        )
    return {
        "courses": courses,
        "today_tasks": tasks,
        "continue_learning": recent_lesson,
        "stats": stats,
        "recommendation": recommendation,
        "activities": _activities(db, user=user, course_ids=course_ids, limit=8),
        "notifications": get_student_notifications(db, user),
    }


def get_student_course_home(db: Session, *, course_id: int, user: User) -> dict:
    course = _assert_joined(db, course_id=course_id, user=user)
    teacher = _teacher(db, course)
    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    published_lessons = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.course_id == course_id, Lesson.status == LessonStatus.PUBLISHED.value)
            .order_by(Lesson.created_at.asc())
        )
    )
    lesson_ids = [lesson.id for lesson in published_lessons]
    progress_by_lesson = {
        progress.lesson_id: progress
        for progress in (
            db.scalars(select(LearningProgress).where(LearningProgress.user_id == user.id, LearningProgress.lesson_id.in_(lesson_ids)))
            if lesson_ids
            else []
        )
    }
    lessons = []
    for lesson in published_lessons:
        progress = progress_by_lesson.get(lesson.id)
        row = _as_dict(lesson)
        row["progress"] = _as_dict(progress) if progress else None
        row["progress_percent"] = progress.progress_percent if progress else 0
        row["current_page"] = progress.current_page if progress else 1
        lessons.append(row)
    materials = [
        _as_dict(item)
        for item in db.scalars(
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
            .order_by(CourseMaterial.created_at.desc())
            .limit(8)
        )
    ]
    quizzes = [
        _as_dict(item)
        for item in db.scalars(
            select(Quiz)
            .where(Quiz.course_id == course_id, Quiz.status == QuizStatus.PUBLISHED.value)
            .order_by(Quiz.created_at.desc())
            .limit(6)
        )
    ]
    recent_qa = [
        _as_dict(item)
        for item in db.scalars(
            select(QARecord)
            .where(QARecord.course_id == course_id, QARecord.user_id == user.id)
            .order_by(QARecord.created_at.desc())
            .limit(4)
        )
    ]
    stats = _learning_stats(db, user=user, course_ids=[course_id])
    return {
        "course": _as_dict(course),
        "teacher": _as_dict(teacher) if teacher else None,
        "chapters": [_as_dict(item) for item in chapters],
        "lessons": lessons,
        "materials": materials,
        "quizzes": quizzes,
        "recent_qa": recent_qa,
        "stats": stats,
        "student_count": _course_student_total(db, course_id),
        "quick_questions": _course_quick_questions(course=course, chapters=chapters, lessons=lessons, materials=materials),
    }


def _course_quick_questions(*, course: Course, chapters: list[Chapter], lessons: list[dict], materials: list[dict]) -> list[str]:
    lesson_title = next((item.get("title") for item in lessons if item.get("title")), "")
    chapter_title = next((item.title for item in chapters if item.title), "")
    material_title = next((item.get("title") for item in materials if item.get("title")), "")
    base = lesson_title or chapter_title or material_title or course.name
    questions = [
        f"{base} 的重点是什么？",
        f"请用例子解释 {chapter_title or base}",
        f"根据 {lesson_title or base} 出一道练习题",
        f"帮我总结 {material_title or chapter_title or base} 的复习提纲",
    ]
    return list(dict.fromkeys(questions))


def get_page_note(db: Session, *, page_id: int, user: User) -> dict:
    page = db.get(LessonPage, page_id)
    if page is None:
        raise not_found("页面不存在")
    lesson = db.get(Lesson, page.lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_joined(db, course_id=lesson.course_id, user=user)
    note = db.scalar(select(PageNote).where(PageNote.user_id == user.id, PageNote.lesson_page_id == page_id))
    if note is None:
        return {"id": None, "lesson_id": lesson.id, "lesson_page_id": page_id, "content": "", "updated_at": None}
    return _as_dict(note)


def save_page_note(db: Session, *, page_id: int, user: User, content: str) -> dict:
    if len(content) > 8000:
        raise bad_request("笔记不能超过8000字")
    page = db.get(LessonPage, page_id)
    if page is None:
        raise not_found("页面不存在")
    lesson = db.get(Lesson, page.lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_joined(db, course_id=lesson.course_id, user=user)
    note = db.scalar(select(PageNote).where(PageNote.user_id == user.id, PageNote.lesson_page_id == page_id))
    if note is None:
        note = PageNote(user_id=user.id, lesson_id=lesson.id, lesson_page_id=page_id, content=content)
    else:
        note.content = content
    db.add(note)
    db.commit()
    db.refresh(note)
    return _as_dict(note)


def get_student_profile(db: Session, user: User) -> dict:
    courses = list_student_course_summaries(db, user)
    course_ids = [course["id"] for course in courses]
    stats = _learning_stats(db, user=user, course_ids=course_ids)
    achievements = [
        {"key": "streak7", "name": "连续7天", "unlocked": stats["streak_days"] >= 7},
        {"key": "quiz", "name": "完成测验", "unlocked": stats["accuracy"] > 0},
        {"key": "qa", "name": "提问达人", "unlocked": stats["qa_count"] >= 10},
        {"key": "finish", "name": "课时完成", "unlocked": stats["completion_rate"] >= 80},
        {"key": "streak30", "name": "连续30天", "unlocked": stats["streak_days"] >= 30},
    ]
    return {
        "user": _as_dict(user),
        "student_profile": _preference(db, user_id=user.id, key=STUDENT_PROFILE_KEY) or {"school": "", "bio": user.bio or ""},
        "notification_settings": _preference(db, user_id=user.id, key=STUDENT_NOTICE_KEY) or DEFAULT_STUDENT_NOTICES,
        "stats": stats,
        "achievements": achievements,
        "activities": _activities(db, user=user, course_ids=course_ids, limit=20),
    }


def update_student_profile(
    db: Session,
    *,
    user: User,
    nickname: str | None,
    avatar_url: str | None,
    bio: str | None,
    school: str | None,
) -> dict:
    _assert_student(user)
    if nickname is not None:
        user.nickname = nickname
    if avatar_url is not None:
        user.avatar_url = avatar_url
    if bio is not None:
        user.bio = bio
    current = _preference(db, user_id=user.id, key=STUDENT_PROFILE_KEY) or {}
    if not isinstance(current, dict):
        current = {}
    if school is not None:
        current["school"] = school
    if bio is not None:
        current["bio"] = bio
    db.add(user)
    _set_preference(db, user_id=user.id, key=STUDENT_PROFILE_KEY, value=current)
    db.commit()
    db.refresh(user)
    return get_student_profile(db, user)


def update_student_notifications(db: Session, *, user: User, settings: list[dict]) -> list[dict]:
    _assert_student(user)
    label_map = {item["key"]: item["label"] for item in DEFAULT_STUDENT_NOTICES}
    normalized = []
    for item in settings:
        key = str(item.get("key", "")).strip()
        if key not in label_map:
            continue
        normalized.append({"key": key, "label": label_map[key], "enabled": bool(item.get("enabled", False)), "time": item.get("time") or "20:00"})
    if not normalized:
        raise bad_request("通知设置不能为空")
    existing = {item["key"] for item in normalized}
    for item in DEFAULT_STUDENT_NOTICES:
        if item["key"] not in existing:
            normalized.append(item)
    _set_preference(db, user_id=user.id, key=STUDENT_NOTICE_KEY, value=normalized)
    db.commit()
    return normalized


def _notice_enabled(db: Session, *, user_id: int, key: str) -> bool:
    settings = _preference(db, user_id=user_id, key=STUDENT_NOTICE_KEY) or DEFAULT_STUDENT_NOTICES
    if not isinstance(settings, list):
        return True
    for item in settings:
        if isinstance(item, dict) and item.get("key") == key:
            return bool(item.get("enabled", True))
    return True


def _notification_sort_time(item: dict) -> float:
    value = item.get("time") or item.get("created_at")
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return normalized.timestamp()
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            normalized_time = parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
            return normalized_time.timestamp()
        except ValueError:
            return 0
    return 0


def get_student_notifications(db: Session, user: User) -> list[dict]:
    _assert_student(user)
    course_ids = [course.id for course in _joined_courses(db, user)]
    course_id_set = set(course_ids)
    notifications: list[dict] = []
    if _notice_enabled(db, user_id=user.id, key="system"):
        announcement = active_system_announcement(db, role="student")
        if announcement:
            notifications.append(announcement)
    if course_ids:
        if _notice_enabled(db, user_id=user.id, key="quiz"):
            notifications.extend(
                item
                for item in list_user_notifications(db, user_id=user.id, limit=8)
                if item.get("type") in {"quiz_generated", "quiz_generation_failed"}
            )
        if _notice_enabled(db, user_id=user.id, key="teacher"):
            reminders = _preference(db, user_id=user.id, key=STUDENT_REMINDER_KEY)
            if isinstance(reminders, list):
                for item in reminders:
                    if not isinstance(item, dict):
                        continue
                    if item.get("course_id") not in course_id_set:
                        continue
                    notifications.append(
                        {
                            "id": item.get("id"),
                            "type": "teacher_reminder",
                            "title": item.get("title") or "教师提醒",
                            "message": item.get("message") or "",
                            "course_id": item.get("course_id"),
                            "course_name": item.get("course_name") or "",
                            "teacher_name": item.get("teacher_name") or "教师",
                            "time": item.get("time"),
                            "unread": bool(item.get("unread", True)),
                        }
                    )
        for lesson in db.scalars(
            select(Lesson)
            .where(Lesson.course_id.in_(course_ids), Lesson.status == LessonStatus.PUBLISHED.value)
            .order_by(*_published_lesson_order())
            .limit(4)
        ):
            lesson_time = lesson.published_at or lesson.created_at
            notifications.append(
                {
                    "id": f"lesson-{lesson.id}-{int(_notification_sort_time({'time': lesson_time}))}",
                    "type": "lesson",
                    "title": f"新课时：{lesson.title}",
                    "time": lesson_time,
                    "unread": True,
                }
            )
        failed_material = db.scalar(
            select(CourseMaterial)
            .where(CourseMaterial.course_id.in_(course_ids), CourseMaterial.parse_status == ProcessStatus.FAILED.value)
            .order_by(CourseMaterial.updated_at.desc())
        )
        if failed_material:
            notifications.append(
                {
                    "id": f"material-{failed_material.id}-{int(_notification_sort_time({'time': failed_material.updated_at}))}",
                    "type": "material",
                    "title": f"资料处理失败：{failed_material.title}",
                    "time": failed_material.updated_at,
                    "unread": True,
                }
            )
    notifications.sort(key=_notification_sort_time, reverse=True)
    return apply_user_notification_reads(db, user_id=user.id, notifications=notifications[:8])


def mark_student_notifications_read(db: Session, *, user: User, notification_ids: list[str] | None = None) -> list[dict]:
    _assert_student(user)
    ids = [str(item).strip() for item in (notification_ids or []) if str(item).strip()]
    if not ids:
        ids = [str(item.get("id") or "").strip() for item in get_student_notifications(db, user) if str(item.get("id") or "").strip()]
    if ids:
        mark_user_notifications_read(db, user_id=user.id, notification_ids=ids)
        reminders = _preference(db, user_id=user.id, key=STUDENT_REMINDER_KEY)
        if isinstance(reminders, list):
            changed = False
            id_set = set(ids)
            for item in reminders:
                if isinstance(item, dict) and str(item.get("id") or "").strip() in id_set:
                    item["unread"] = False
                    changed = True
            if changed:
                _set_preference(db, user_id=user.id, key=STUDENT_REMINDER_KEY, value=reminders)
        db.commit()
    return get_student_notifications(db, user)
