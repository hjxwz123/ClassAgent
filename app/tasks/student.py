from app.db import session as db_session
from app.services.student import run_student_recommendation_generation
from app.tasks.celery_app import celery_app


@celery_app.task(name="student.recommendation")
def generate_student_recommendation_task(
    user_id: int,
    course_count: int,
    pending_tasks: int,
    recent_lesson_title: str | None,
    weak_points: list[str],
    study_hours: float,
    completion_rate: float,
    accuracy: float,
) -> None:
    with db_session.SessionLocal() as db:
        run_student_recommendation_generation(
            db,
            user_id=user_id,
            course_count=course_count,
            pending_tasks=pending_tasks,
            recent_lesson_title=recent_lesson_title,
            weak_points=list(weak_points or []),
            study_hours=study_hours,
            completion_rate=completion_rate,
            accuracy=accuracy,
        )
