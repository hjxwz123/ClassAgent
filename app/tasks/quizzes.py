from app.db import session as db_session
from app.services.learning import process_quiz_generation_task as run_quiz_generation_task
from app.tasks.celery_app import celery_app


@celery_app.task(name="quizzes.generate")
def process_quiz_generation_task(task_id: int) -> None:
    with db_session.SessionLocal() as db:
        run_quiz_generation_task(db, task_id)
