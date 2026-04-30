from fastapi import APIRouter

from app.api.routes.classroom import router as classroom_router
from app.api.routes.learning import router as learning_router
from app.api.routes.auth import router as auth_router
from app.api.routes.courses import router as courses_router
from app.api.routes.health import router as health_router
from app.api.routes.materials import router as materials_router
from app.api.routes.qa import router as qa_router
from app.api.routes.tutoring import router as tutoring_router


api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(courses_router, prefix="/courses", tags=["courses"])
api_router.include_router(materials_router, prefix="/materials", tags=["materials"])
api_router.include_router(classroom_router, prefix="/lessons", tags=["classroom"])
api_router.include_router(qa_router, prefix="/qa", tags=["qa"])
api_router.include_router(tutoring_router, prefix="/tutoring", tags=["tutoring"])
api_router.include_router(learning_router, prefix="/learning", tags=["learning"])
