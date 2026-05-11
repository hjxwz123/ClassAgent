from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime, timedelta
from io import StringIO

from fastapi import UploadFile
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.enums import LessonStatus, ProcessStatus, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import (
    AsyncTaskLog,
    Chapter,
    Course,
    CourseMaterial,
    CourseMembership,
    KnowledgeChunk,
    KnowledgePoint,
    LearningProgress,
    Lesson,
    LessonPage,
    OperationLog,
    PedagogyArtifact,
    QARecord,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    User,
    UserPreference,
    WrongQuestion,
)
from app.services.analytics import get_course_analytics
from app.services.audit import log_operation
from app.services.avatar import upload_avatar_file
from app.services.courses import _assert_course_owner, _get_course_or_404, list_teaching_courses
from app.services.notifications import active_system_announcement, apply_user_notification_reads, list_user_notifications, mark_user_notifications_read
from app.services.storage import storage_service


TEACHER_PROFILE_KEY = "teacher.profile"
TEACHER_NOTIFICATION_KEY = "teacher.notifications"
STUDENT_REMINDER_KEY = "student.teacher_reminders"

DEFAULT_NOTIFICATION_SETTINGS = [
    {"key": "join", "label": "学生加入课程", "enabled": True},
    {"key": "ppt", "label": "PPT 解析完成", "enabled": True},
    {"key": "script", "label": "脚本生成完成", "enabled": False},
    {"key": "tts", "label": "TTS 合成失败", "enabled": True},
    {"key": "qa", "label": "学生问答汇总", "enabled": True},
    {"key": "ai", "label": "AI 任务状态", "enabled": True},
    {"key": "peak", "label": "提问高峰", "enabled": True},
    {"key": "system", "label": "系统公告", "enabled": True},
]


def _aware_utc(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _as_dict(item) -> dict:
    data = dict(item.__dict__)
    data.pop("_sa_instance_state", None)
    data.pop("password_hash", None)
    if "preview_url" in data:
        data["preview_url"] = storage_service.normalize_public_url(data["preview_url"])
    if "audio_url" in data:
        data["audio_url"] = storage_service.normalize_public_url(data["audio_url"])
    if "cover_url" in data:
        data["cover_url"] = storage_service.normalize_public_url(data["cover_url"])
    if "avatar_url" in data:
        data["avatar_url"] = storage_service.normalize_public_url(data["avatar_url"])
    return data


def _assert_teacher(user: User) -> None:
    if user.role not in {UserRole.TEACHER.value, UserRole.ADMIN.value}:
        raise forbidden("仅教师可访问")


def _get_preference(db: Session, *, user_id: int, key: str):
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.preference_key == key))
    return item.preference_value if item is not None else None


def _set_preference(db: Session, *, user_id: int, key: str, value) -> UserPreference:
    item = db.scalar(select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.preference_key == key))
    if item is None:
        item = UserPreference(user_id=user_id, preference_key=key, preference_value=value)
    else:
        item.preference_value = value
    db.add(item)
    return item


def _assert_course_access(db: Session, *, course_id: int, user: User, require_active: bool = False) -> Course:
    course = _get_course_or_404(db, course_id)
    _assert_course_owner(course, user, require_active=require_active)
    return course


def _course_ids(db: Session, user: User) -> list[int]:
    return [course.id for course in list_teaching_courses(db, user)]


def _student_ids(db: Session, course_id: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(
            select(CourseMembership.user_id).where(
                CourseMembership.course_id == course_id,
                CourseMembership.role == UserRole.STUDENT.value,
            )
        )
    ]


def _course_counts(db: Session, course_id: int) -> dict:
    students = db.scalar(
        select(func.count(CourseMembership.id)).where(
            CourseMembership.course_id == course_id,
            CourseMembership.role == UserRole.STUDENT.value,
        )
    ) or 0
    materials = db.scalar(
        select(func.count(CourseMaterial.id)).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
    ) or 0
    lessons = db.scalar(select(func.count(Lesson.id)).where(Lesson.course_id == course_id)) or 0
    published = db.scalar(
        select(func.count(Lesson.id)).where(Lesson.course_id == course_id, Lesson.status == LessonStatus.PUBLISHED.value)
    ) or 0
    chapters = db.scalar(select(func.count(Chapter.id)).where(Chapter.course_id == course_id)) or 0
    return {
        "student_count": int(students),
        "material_count": int(materials),
        "lesson_count": int(lessons),
        "published_lesson_count": int(published),
        "chapter_count": int(chapters),
    }


def _lesson_progress(db: Session, lesson: Lesson, student_total: int) -> dict:
    progress_rows = list(db.scalars(select(LearningProgress).where(LearningProgress.lesson_id == lesson.id)))
    completed = len([item for item in progress_rows if item.completed_at is not None or item.progress_percent >= 100])
    learned = len(progress_rows)
    average = round(sum(item.progress_percent for item in progress_rows) / max(len(progress_rows), 1), 2) if progress_rows else 0
    return {
        "learned_count": learned,
        "completed_count": completed,
        "completion_rate": round(completed / max(student_total, 1) * 100, 2) if student_total else 0,
        "average_progress": average,
    }


def _material_status_counts(db: Session, course_id: int) -> dict:
    from app.services.materials import repair_materials_with_existing_pages

    materials = list(db.scalars(select(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))))
    repair_materials_with_existing_pages(db, materials)
    by_status = Counter(item.parse_status for item in materials)
    by_type = Counter(item.material_type for item in materials)
    total = sum(by_status.values())
    return {
        "total": total,
        "by_status": {status: int(count) for status, count in by_status.items()},
        "by_type": {material_type: int(count) for material_type, count in by_type.items()},
    }


def _recent_activities(db: Session, course_id: int, limit: int = 8) -> list[dict]:
    items = [
        {
            "type": "operation",
            "text": item.action,
            "time": item.created_at,
            "tone": "primary",
        }
        for item in db.scalars(
            select(OperationLog)
            .where(OperationLog.target_id == course_id)
            .order_by(OperationLog.created_at.desc())
            .limit(limit)
        )
    ]
    if len(items) < limit:
        joins = db.execute(
            select(CourseMembership, User)
            .join(User, User.id == CourseMembership.user_id)
            .where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
            .order_by(CourseMembership.joined_at.desc())
            .limit(limit - len(items))
        )
        items.extend(
            {
                "type": "student",
                "text": f"{student.nickname} 加入课程",
                "time": membership.joined_at,
                "tone": "success",
            }
            for membership, student in joins
        )
    return sorted(items, key=lambda row: row["time"], reverse=True)[:limit]


def _ai_tasks(db: Session, course_ids: list[int], limit: int = 5) -> list[dict]:
    if not course_ids:
        return []
    material_ids = [
        row[0]
        for row in db.execute(
            select(CourseMaterial.id).where(CourseMaterial.course_id.in_(course_ids), CourseMaterial.deleted_at.is_(None))
        )
    ]
    task_filters = [AsyncTaskLog.target_type == "quiz"]
    if material_ids:
        task_filters.append((AsyncTaskLog.target_type == "material") & (AsyncTaskLog.target_id.in_(material_ids)))
    task_rows = list(
        db.scalars(
            select(AsyncTaskLog)
            .where(or_(*task_filters))
            .order_by(AsyncTaskLog.created_at.desc())
            .limit(max(limit * 4, 12))
        )
    )
    course_id_set = set(course_ids)
    tasks = [
        task
        for task in task_rows
        if task.target_type != "quiz" or int((task.detail or {}).get("course_id") or 0) in course_id_set
    ][:limit]
    material_by_id = {
        item.id: item
        for item in db.scalars(select(CourseMaterial).where(CourseMaterial.id.in_([task.target_id for task in tasks if task.target_id])))
    }
    quiz_by_id = {
        item.id: item
        for item in db.scalars(
            select(Quiz).where(Quiz.id.in_([int(task.target_id) for task in tasks if task.target_type == "quiz" and task.target_id]))
        )
    }
    return [
        {
            "id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "target_id": task.target_id,
            "title": (
                material_by_id.get(task.target_id).title
                if task.target_type == "material" and task.target_id in material_by_id
                else quiz_by_id.get(task.target_id).title
                if task.target_type == "quiz" and task.target_id in quiz_by_id
                else (task.detail or {}).get("title") or task.task_name
            ),
            "target_type": task.target_type,
            "detail": task.detail,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
        for task in tasks
    ]


def course_summary(db: Session, course: Course) -> dict:
    data = _as_dict(course)
    data.update(_course_counts(db, course.id))
    total_lessons = max(data["lesson_count"], 1)
    data["published_rate"] = round(data["published_lesson_count"] / total_lessons * 100, 2) if data["lesson_count"] else 0
    return data


def list_teacher_course_summaries(db: Session, user: User) -> list[dict]:
    _assert_teacher(user)
    return [course_summary(db, course) for course in list_teaching_courses(db, user)]


def get_teacher_profile(db: Session, user: User) -> dict:
    _assert_teacher(user)
    profile = _get_preference(db, user_id=user.id, key=TEACHER_PROFILE_KEY) or {}
    notifications = _get_preference(db, user_id=user.id, key=TEACHER_NOTIFICATION_KEY) or DEFAULT_NOTIFICATION_SETTINGS
    return {
        "user": _as_dict(user),
        "teacher_profile": {
            "organization": profile.get("organization", "") if isinstance(profile, dict) else "",
            "department": profile.get("department", "") if isinstance(profile, dict) else "",
        },
        "notification_settings": notifications,
    }


def update_teacher_profile(
    db: Session,
    *,
    user: User,
    nickname: str | None,
    avatar_url: str | None,
    bio: str | None,
    organization: str | None,
    department: str | None,
) -> dict:
    _assert_teacher(user)
    if nickname is not None:
        user.nickname = nickname
    if avatar_url is not None:
        user.avatar_url = avatar_url
    if bio is not None:
        user.bio = bio
    current = _get_preference(db, user_id=user.id, key=TEACHER_PROFILE_KEY) or {}
    if not isinstance(current, dict):
        current = {}
    if organization is not None:
        current["organization"] = organization
    if department is not None:
        current["department"] = department
    db.add(user)
    _set_preference(db, user_id=user.id, key=TEACHER_PROFILE_KEY, value=current)
    log_operation(db, user_id=user.id, action="teacher.profile.update", target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return get_teacher_profile(db, user)


def upload_teacher_avatar(db: Session, *, user: User, upload: UploadFile) -> dict:
    _assert_teacher(user)
    meta = upload_avatar_file(db, user=user, upload=upload)
    log_operation(
        db,
        user_id=user.id,
        action="teacher.avatar.upload",
        target_type="user",
        target_id=user.id,
        detail={"filename": upload.filename, "size_bytes": meta["size_bytes"]},
    )
    db.commit()
    db.refresh(user)
    return get_teacher_profile(db, user)


def update_teacher_notifications(db: Session, *, user: User, settings: list[dict]) -> list[dict]:
    _assert_teacher(user)
    normalized = []
    label_by_key = {item["key"]: item["label"] for item in DEFAULT_NOTIFICATION_SETTINGS}
    for item in settings:
        key = str(item.get("key", "")).strip()
        if key not in label_by_key:
            continue
        normalized.append({"key": key, "label": label_by_key[key], "enabled": bool(item.get("enabled", False))})
    if not normalized:
        raise bad_request("通知设置不能为空")
    existing_keys = {item["key"] for item in normalized}
    for item in DEFAULT_NOTIFICATION_SETTINGS:
        if item["key"] not in existing_keys:
            normalized.append(item)
    _set_preference(db, user_id=user.id, key=TEACHER_NOTIFICATION_KEY, value=normalized)
    log_operation(db, user_id=user.id, action="teacher.notifications.update", target_type="user", target_id=user.id)
    db.commit()
    return normalized


def _teacher_notice_enabled(db: Session, *, user_id: int, key: str) -> bool:
    settings = _get_preference(db, user_id=user_id, key=TEACHER_NOTIFICATION_KEY) or DEFAULT_NOTIFICATION_SETTINGS
    if not isinstance(settings, list):
        return True
    for item in settings:
        if isinstance(item, dict) and item.get("key") == key:
            return bool(item.get("enabled", True))
    return True


def get_teacher_dashboard(db: Session, user: User) -> dict:
    _assert_teacher(user)
    courses = list_teaching_courses(db, user)
    ids = [course.id for course in courses]
    since_week = datetime.now(UTC) - timedelta(days=7)
    student_total = 0
    for course_id in ids:
        student_total += len(_student_ids(db, course_id))
    weekly_qa = db.scalar(select(func.count(QARecord.id)).where(QARecord.course_id.in_(ids), QARecord.created_at >= since_week)) if ids else 0
    pending_scripts = (
        db.scalar(
            select(func.count(LessonPage.id))
            .join(Lesson, Lesson.id == LessonPage.lesson_id)
            .where(Lesson.course_id.in_(ids), LessonPage.script_status != ProcessStatus.READY.value)
        )
        if ids
        else 0
    ) or 0
    recent_courses = [course_summary(db, course) for course in courses[:3]]
    todos: list[dict] = []
    if ids:
        failed_materials = list(
            db.scalars(
                select(CourseMaterial)
                .where(CourseMaterial.course_id.in_(ids), CourseMaterial.deleted_at.is_(None), CourseMaterial.parse_status == ProcessStatus.FAILED.value)
                .order_by(CourseMaterial.updated_at.desc())
                .limit(3)
            )
        )
        todos.extend({"type": "error", "title": f"{item.title} 处理失败", "course_id": item.course_id, "created_at": item.updated_at} for item in failed_materials)
        drafts = list(
            db.scalars(
                select(Lesson)
                .where(Lesson.course_id.in_(ids), Lesson.status != LessonStatus.PUBLISHED.value)
                .order_by(Lesson.updated_at.desc())
                .limit(5)
            )
        )
        todos.extend({"type": "lesson", "title": f"{item.title} 待发布", "course_id": item.course_id, "created_at": item.updated_at} for item in drafts)
    weekly_activity = []
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    week_start = (datetime.now(UTC) - timedelta(days=datetime.now(UTC).weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    for course in courses[:6]:
        row = {"course_id": course.id, "course_name": course.name, "days": []}
        for index, day in enumerate(weekdays):
            start = week_start + timedelta(days=index)
            end = start + timedelta(days=1)
            count = db.scalar(
                select(func.count(LearningProgress.id))
                .join(Lesson, Lesson.id == LearningProgress.lesson_id)
                .where(Lesson.course_id == course.id, LearningProgress.updated_at >= start, LearningProgress.updated_at < end)
            ) or 0
            row["days"].append({"day": day, "count": int(count)})
        weekly_activity.append(row)
    script_rows = []
    if ids:
        script_rows = [
            {
                "lesson_id": lesson.id,
                "page_id": page.id,
                "course_id": lesson.course_id,
                "lesson_title": lesson.title,
                "page_number": page.page_number,
                "status": page.script_status,
                "created_at": page.created_at,
            }
            for lesson, page in db.execute(
                select(Lesson, LessonPage)
                .join(LessonPage, LessonPage.lesson_id == Lesson.id)
                .where(Lesson.course_id.in_(ids))
                .order_by(LessonPage.updated_at.desc())
                .limit(5)
            )
        ]
    notifications = list_user_notifications(db, user_id=user.id, limit=8)
    if _teacher_notice_enabled(db, user_id=user.id, key="system"):
        announcement = active_system_announcement(db, role="teacher")
        if announcement:
            notifications = [announcement, *notifications][:8]
    notifications = apply_user_notification_reads(db, user_id=user.id, notifications=notifications)
    return {
        "stats": {
            "course_total": len(courses),
            "active_course_total": len([item for item in courses if item.status == "active"]),
            "student_total": student_total,
            "weekly_qa": int(weekly_qa or 0),
            "pending_scripts": int(pending_scripts),
        },
        "recent_courses": recent_courses,
        "todos": sorted(todos, key=lambda item: item["created_at"], reverse=True)[:8],
        "weekly_activity": weekly_activity,
        "pending_scripts": script_rows,
        "ai_tasks": _ai_tasks(db, ids, limit=5),
        "notifications": notifications,
    }


def mark_teacher_notifications_read(db: Session, *, user: User, notification_ids: list[str] | None = None) -> list[dict]:
    _assert_teacher(user)
    ids = [str(item).strip() for item in (notification_ids or []) if str(item).strip()]
    if not ids:
        ids = [
            str(item.get("id") or "").strip()
            for item in get_teacher_dashboard(db, user).get("notifications", [])
            if str(item.get("id") or "").strip()
        ]
    if ids:
        mark_user_notifications_read(db, user_id=user.id, notification_ids=ids)
        db.commit()
    return get_teacher_dashboard(db, user).get("notifications", [])


def get_teacher_course_home(db: Session, *, course_id: int, user: User) -> dict:
    course = _assert_course_access(db, course_id=course_id, user=user)
    counts = _course_counts(db, course_id)
    student_total = counts["student_count"]
    lessons = []
    for lesson in db.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.created_at.desc()).limit(8)):
        data = _as_dict(lesson)
        data.update(_lesson_progress(db, lesson, student_total))
        lessons.append(data)
    student_progress = get_teacher_students(db, course_id=course_id, user=user)["items"][:10]
    return {
        "course": course_summary(db, course),
        "chapters": [_as_dict(item) for item in db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id))],
        "quick_counts": counts,
        "lessons": lessons,
        "material_stats": _material_status_counts(db, course_id),
        "activities": _recent_activities(db, course_id, limit=8),
        "student_progress": student_progress,
        "ai_tasks": _ai_tasks(db, [course_id], limit=8),
    }


def get_teacher_materials_summary(db: Session, *, course_id: int, user: User) -> dict:
    from app.services.materials import repair_materials_with_existing_pages

    _assert_course_access(db, course_id=course_id, user=user)
    materials = list(db.scalars(select(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))))
    repair_materials_with_existing_pages(db, materials)
    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    by_chapter = []
    for chapter in chapters:
        count = len([item for item in materials if item.chapter_id == chapter.id])
        by_chapter.append({"id": chapter.id, "title": chapter.title, "count": count})
    total_size = sum(item.size_bytes or 0 for item in materials)
    ready = len([item for item in materials if item.parse_status == ProcessStatus.READY.value])
    return {
        "total": len(materials),
        "ready": ready,
        "pending": len(materials) - ready,
        "size_bytes": total_size,
        "chapters": by_chapter,
        "stats": _material_status_counts(db, course_id),
    }

def get_teacher_students(db: Session, *, course_id: int, user: User) -> dict:
    _assert_course_access(db, course_id=course_id, user=user)
    lessons = list(db.scalars(select(Lesson).where(Lesson.course_id == course_id)))
    lesson_ids = [lesson.id for lesson in lessons]
    rows = list(
        db.execute(
            select(CourseMembership, User)
            .join(User, User.id == CourseMembership.user_id)
            .where(CourseMembership.course_id == course_id, CourseMembership.role == UserRole.STUDENT.value)
            .order_by(CourseMembership.joined_at.asc())
        )
    )
    items = []
    active_count = 0
    inactive_14 = 0
    since_7 = datetime.now(UTC) - timedelta(days=7)
    since_14 = datetime.now(UTC) - timedelta(days=14)
    for membership, student in rows:
        progresses = list(db.scalars(select(LearningProgress).where(LearningProgress.user_id == student.id, LearningProgress.lesson_id.in_(lesson_ids)))) if lesson_ids else []
        progress_percent = round(sum(item.progress_percent for item in progresses) / max(len(lessons), 1), 2) if lessons else 0
        studied_lessons = len([item for item in progresses if item.progress_percent > 0])
        last_progress = max([item.updated_at for item in progresses], default=None)
        last_progress_for_compare = _aware_utc(last_progress)
        qa_count = db.scalar(select(func.count(QARecord.id)).where(QARecord.user_id == student.id, QARecord.course_id == course_id)) or 0
        wrong_count = db.scalar(select(func.sum(WrongQuestion.wrong_count)).where(WrongQuestion.user_id == student.id, WrongQuestion.course_id == course_id)) or 0
        if last_progress_for_compare and last_progress_for_compare >= since_7:
            active_count += 1
        if not last_progress_for_compare or last_progress_for_compare < since_14:
            inactive_14 += 1
        items.append(
            {
                "membership_id": membership.id,
                "joined_at": membership.joined_at,
                "student": _as_dict(student),
                "progress_percent": progress_percent,
                "studied_lessons": studied_lessons,
                "lesson_total": len(lessons),
                "qa_count": int(qa_count),
                "wrong_count": int(wrong_count or 0),
                "last_study_at": last_progress,
            }
        )
    average = round(sum(item["progress_percent"] for item in items) / max(len(items), 1), 2) if items else 0
    return {
        "stats": {
            "total": len(items),
            "active_7d": active_count,
            "average_completion": average,
            "inactive_14d": inactive_14,
        },
        "items": items,
    }


def get_teacher_student_detail(db: Session, *, course_id: int, student_id: int, user: User) -> dict:
    _assert_course_access(db, course_id=course_id, user=user)
    membership = db.scalar(
        select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == student_id)
    )
    student = db.get(User, student_id)
    if membership is None or student is None:
        raise not_found("学生不存在")
    lessons = list(db.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.created_at.desc())))
    lesson_progress = []
    for lesson in lessons:
        progress = db.scalar(select(LearningProgress).where(LearningProgress.lesson_id == lesson.id, LearningProgress.user_id == student_id))
        lesson_progress.append(
            {
                "lesson": _as_dict(lesson),
                "progress_percent": progress.progress_percent if progress else 0,
                "current_page": progress.current_page if progress else 0,
                "last_study_at": progress.updated_at if progress else None,
            }
        )
    qa_records = [
        _as_dict(item)
        for item in db.scalars(
            select(QARecord).where(QARecord.course_id == course_id, QARecord.user_id == student_id).order_by(QARecord.created_at.desc()).limit(20)
        )
    ]
    wrong_rows = db.execute(
        select(WrongQuestion, QuizQuestion)
        .join(QuizQuestion, QuizQuestion.id == WrongQuestion.question_id)
        .where(WrongQuestion.course_id == course_id, WrongQuestion.user_id == student_id)
    )
    weak = Counter()
    for wrong, question in wrong_rows:
        if question.knowledge_point_id:
            point = db.get(KnowledgePoint, question.knowledge_point_id)
            weak[point.name if point else "未命名"] += wrong.wrong_count
        else:
            weak["未标注"] += wrong.wrong_count
    attempts = list(
        db.scalars(
            select(QuizAttempt)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(Quiz.course_id == course_id, QuizAttempt.user_id == student_id)
        )
    )
    return {
        "membership": _as_dict(membership),
        "student": _as_dict(student),
        "lesson_progress": lesson_progress,
        "qa_records": qa_records,
        "stats": {
            "qa_total": len(qa_records),
            "attempt_total": len(attempts),
            "average_score": round(sum(item.score for item in attempts) / max(len(attempts), 1), 2) if attempts else 0,
            "wrong_total": sum(weak.values()),
        },
        "weak_points": [{"name": key, "count": value} for key, value in weak.most_common(10)],
    }


def remind_student(db: Session, *, course_id: int, student_id: int, user: User, title: str | None = None, message: str | None = None) -> dict:
    course = _assert_course_access(db, course_id=course_id, user=user, require_active=True)
    student = db.get(User, student_id)
    membership = db.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == student_id))
    if student is None or student.role != UserRole.STUDENT.value or membership is None:
        raise not_found("学生不存在")
    reminder_title = (title or f"{course.name}学习提醒").strip()
    reminder_message = (message or f"{user.nickname}老师提醒你查看《{course.name}》的学习进度，及时完成课时学习、练习或待办任务。").strip()
    if not reminder_title:
        raise bad_request("提醒标题不能为空")
    if not reminder_message:
        raise bad_request("提醒内容不能为空")
    if len(reminder_title) > 80:
        raise bad_request("提醒标题不能超过80字")
    if len(reminder_message) > 500:
        raise bad_request("提醒内容不能超过500字")
    now = datetime.now(UTC)
    reminder = {
        "id": f"{int(now.timestamp() * 1000)}-{course_id}-{student_id}-{user.id}",
        "type": "teacher_reminder",
        "title": reminder_title,
        "message": reminder_message,
        "course_id": course_id,
        "course_name": course.name,
        "teacher_id": user.id,
        "teacher_name": user.nickname,
        "time": now.isoformat(),
        "unread": True,
    }
    reminders = _get_preference(db, user_id=student_id, key=STUDENT_REMINDER_KEY)
    if not isinstance(reminders, list):
        reminders = []
    _set_preference(db, user_id=student_id, key=STUDENT_REMINDER_KEY, value=[reminder, *reminders][:50])
    log_operation(
        db,
        user_id=user.id,
        action="teacher.student.remind",
        target_type="student",
        target_id=student_id,
        detail={"course_id": course_id, "title": reminder_title, "message": reminder_message[:120]},
    )
    db.commit()
    return {"sent": True, "student_id": student_id, "reminder": reminder}


def remove_student(db: Session, *, course_id: int, student_id: int, user: User) -> None:
    _assert_course_access(db, course_id=course_id, user=user, require_active=True)
    membership = db.scalar(select(CourseMembership).where(CourseMembership.course_id == course_id, CourseMembership.user_id == student_id))
    if membership is None:
        raise not_found("学生不存在")
    db.delete(membership)
    log_operation(db, user_id=user.id, action="teacher.student.remove", target_type="student", target_id=student_id, detail={"course_id": course_id})
    db.commit()


def delete_teacher_course(db: Session, *, course_id: int, user: User) -> None:
    course = _assert_course_access(db, course_id=course_id, user=user, require_active=True)
    course.deleted_at = datetime.now(UTC)
    db.add(course)
    log_operation(db, user_id=user.id, action="teacher.course.delete", target_type="course", target_id=course_id)
    db.commit()


def export_teacher_students_csv(db: Session, *, course_id: int, user: User) -> str:
    payload = get_teacher_students(db, course_id=course_id, user=user)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["姓名", "邮箱", "学号", "加入时间", "课时进度", "已学课时", "课时总数", "提问次数", "错题数", "最近学习"])
    for item in payload["items"]:
        student = item["student"]
        writer.writerow(
            [
                student.get("nickname", ""),
                student.get("email", ""),
                student.get("student_no", "") or "",
                item["joined_at"].isoformat() if item.get("joined_at") else "",
                item["progress_percent"],
                item["studied_lessons"],
                item["lesson_total"],
                item["qa_count"],
                item["wrong_count"],
                item["last_study_at"].isoformat() if item.get("last_study_at") else "",
            ]
        )
    return "\ufeff" + output.getvalue()


def export_teacher_analysis_csv(db: Session, *, course_id: int, user: User, days: int) -> str:
    payload = get_teacher_analysis(db, course_id=course_id, user=user, days=days)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["类型", "名称", "数值"])
    for key, value in payload.get("metrics", {}).items():
        writer.writerow(["指标", key, value])
    for item in payload.get("lesson_completion", []):
        writer.writerow(["课时完成率", item.get("title", ""), item.get("completion_rate", 0)])
    for item in payload.get("weak_points", []):
        writer.writerow(["薄弱点", item.get("knowledge_point", ""), item.get("wrong_count", 0)])
    for item in payload.get("high_frequency_questions", []):
        writer.writerow(["高频问题", item.get("question", ""), item.get("count", 0)])
    return "\ufeff" + output.getvalue()


def update_chapter(db: Session, *, course_id: int, chapter_id: int, title: str, description: str | None, order_index: int, user: User) -> Chapter:
    _assert_course_access(db, course_id=course_id, user=user, require_active=True)
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.course_id != course_id:
        raise not_found("章节不存在")
    chapter.title = title
    chapter.description = description
    chapter.order_index = order_index
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def delete_chapter(db: Session, *, course_id: int, chapter_id: int, user: User) -> None:
    _assert_course_access(db, course_id=course_id, user=user, require_active=True)
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.course_id != course_id:
        raise not_found("章节不存在")
    db.execute(update(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(Lesson).where(Lesson.course_id == course_id, Lesson.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(KnowledgeChunk).where(KnowledgeChunk.course_id == course_id, KnowledgeChunk.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(PedagogyArtifact).where(PedagogyArtifact.course_id == course_id, PedagogyArtifact.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(KnowledgePoint).where(KnowledgePoint.course_id == course_id, KnowledgePoint.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(Quiz).where(Quiz.course_id == course_id, Quiz.chapter_id == chapter_id).values(chapter_id=None))
    db.execute(update(QuizQuestion).where(QuizQuestion.course_id == course_id, QuizQuestion.chapter_id == chapter_id).values(chapter_id=None))
    db.delete(chapter)
    log_operation(
        db,
        user_id=user.id,
        action="course.chapter.delete",
        target_type="chapter",
        target_id=chapter_id,
        detail={"course_id": course_id, "title": chapter.title},
    )
    db.commit()


def update_lesson(db: Session, *, lesson_id: int, user: User, title: str | None, chapter_id: int | None, status: str | None) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_course_access(db, course_id=lesson.course_id, user=user, require_active=True)
    if title is not None:
        lesson.title = title
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None or chapter.course_id != lesson.course_id:
            raise bad_request("章节不存在")
        lesson.chapter_id = chapter_id
    if status is not None:
        lesson.status = status
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def delete_lesson(db: Session, *, lesson_id: int, user: User) -> None:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_course_access(db, course_id=lesson.course_id, user=user, require_active=True)
    db.execute(delete(LearningProgress).where(LearningProgress.lesson_id == lesson_id))
    db.execute(delete(PedagogyArtifact).where(PedagogyArtifact.lesson_id == lesson_id))
    db.execute(delete(LessonPage).where(LessonPage.lesson_id == lesson_id))
    db.delete(lesson)
    db.commit()


def duplicate_lesson(db: Session, *, lesson_id: int, user: User) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("课时不存在")
    _assert_course_access(db, course_id=lesson.course_id, user=user, require_active=True)
    clone = Lesson(
        course_id=lesson.course_id,
        chapter_id=lesson.chapter_id,
        material_id=lesson.material_id,
        title=f"{lesson.title} 副本",
        summary=lesson.summary,
        page_count=lesson.page_count,
        status=LessonStatus.READY.value,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    pages = list(db.scalars(select(LessonPage).where(LessonPage.lesson_id == lesson_id).order_by(LessonPage.page_number)))
    for page in pages:
        db.add(
            LessonPage(
                lesson_id=clone.id,
                page_number=page.page_number,
                page_title=page.page_title,
                page_text=page.page_text,
                script_text=page.script_text,
                script_status=page.script_status,
                audio_url=page.audio_url,
                audio_duration_seconds=page.audio_duration_seconds,
                subtitle_text=page.subtitle_text,
            )
        )
    db.commit()
    db.refresh(clone)
    return clone


def get_teacher_analysis(db: Session, *, course_id: int, user: User, days: int) -> dict:
    base = get_course_analytics(db, course_id=course_id, user=user, days=days)
    students = get_teacher_students(db, course_id=course_id, user=user)
    lessons = list(db.scalars(select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.created_at.asc())))
    lesson_completion = []
    for lesson in lessons:
        progress = _lesson_progress(db, lesson, students["stats"]["total"])
        lesson_completion.append({"lesson_id": lesson.id, "title": lesson.title, **progress})
    attempts = list(
        db.scalars(select(QuizAttempt).join(Quiz, Quiz.id == QuizAttempt.quiz_id).where(Quiz.course_id == course_id))
    )
    average_score = round(sum(item.score for item in attempts) / max(len(attempts), 1), 2) if attempts else 0
    qa_total = db.scalar(select(func.count(QARecord.id)).where(QARecord.course_id == course_id)) or 0
    period_study_seconds = int(base.get("period_study_seconds") or base.get("study_seconds") or 0)
    total_study_seconds = int(base.get("study_seconds") or 0)
    return {
        **base,
        "metrics": {
            "active_rate": round(students["stats"]["active_7d"] / max(students["stats"]["total"], 1) * 100, 2) if students["stats"]["total"] else 0,
            "completion_rate": base["completion_rate"],
            "qa_total": int(qa_total),
            "average_score": average_score,
            "weak_point_count": len(base["weak_points"]),
            "study_hours": round(period_study_seconds / 3600, 1),
            "total_study_hours": round(total_study_seconds / 3600, 1),
            "avg_study_minutes": round(period_study_seconds / max(students["stats"]["total"], 1) / 60, 1) if students["stats"]["total"] else 0,
        },
        "lesson_completion": lesson_completion,
        "student_layers": {
            "high": len([item for item in students["items"] if item["last_study_at"] and item["progress_percent"] >= 70]),
            "normal": len([item for item in students["items"] if 30 <= item["progress_percent"] < 70]),
            "low": len([item for item in students["items"] if 5 <= item["progress_percent"] < 30]),
            "inactive": students["stats"]["inactive_14d"],
        },
    }
