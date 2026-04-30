from app.db import session as db_session
from app.services.materials import process_material_pipeline
from app.tasks.celery_app import celery_app


@celery_app.task(name="materials.process")
def process_material_task(material_id: int) -> None:
    with db_session.SessionLocal() as db:
        process_material_pipeline(db, material_id)
