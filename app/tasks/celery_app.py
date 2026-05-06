from celery import Celery

from app.core.config import get_settings


settings = get_settings()
celery_app = Celery(
    "class_agent_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.materials", "app.tasks.quizzes"],
)
celery_app.conf.task_always_eager = settings.celery_task_always_eager
celery_app.conf.task_eager_propagates = True
