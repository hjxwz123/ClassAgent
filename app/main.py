from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import GENERATED_DIR, STORAGE_DIR, UPLOAD_DIR, VECTOR_DIR, get_settings, validate_production_settings
from app.core.security import decode_access_token
from app.db.models import SystemErrorLog
from app.db import session as db_session
from app.services.bootstrap import ensure_default_admin, ensure_system_settings
from app.services.request_logging import request_log_writer


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    db_session.init_db()
    for directory in (STORAGE_DIR, UPLOAD_DIR, GENERATED_DIR, VECTOR_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    requeue_material_ids: list[int] = []
    with db_session.SessionLocal() as db:
        ensure_default_admin(db)
        ensure_system_settings(db)
        from app.services.materials import recover_interrupted_material_processing, recover_stale_material_processing_tasks

        if settings.celery_task_always_eager:
            requeue_material_ids = recover_interrupted_material_processing(db, assume_local_queue_lost=True)
        else:
            recover_stale_material_processing_tasks(db)
    if settings.celery_task_always_eager:
        from app.services.materials import dispatch_material_processing, start_material_processing_runtime

        start_material_processing_runtime()
        for material_id in requeue_material_ids:
            dispatch_material_processing(material_id)
    request_log_writer.start()
    try:
        yield
    finally:
        request_log_writer.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid4()))
        request.state.request_id = request_id
        start = perf_counter()
        response = await call_next(request)
        duration = perf_counter() - start
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        if request.url.path.startswith(settings.api_v1_prefix):
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    payload = decode_access_token(auth_header.removeprefix("Bearer ").strip())
                    user_id = int(payload["sub"])
                except Exception:
                    user_id = None
            try:
                request_log_writer.enqueue(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                    user_id=user_id,
                )
            except Exception:
                pass
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "data": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": exc.status_code, "message": str(exc.detail)}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": detail.get("code", exc.status_code),
                "message": detail.get("message", "请求失败"),
                "data": None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def app_exception_handler(request: Request, exc: Exception):
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "code": exc.detail.get("code", exc.status_code),
                    "message": exc.detail.get("message", "请求失败"),
                    "data": None,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        try:
            with db_session.SessionLocal() as db:
                db.add(
                    SystemErrorLog(
                        level="error",
                        source=request.url.path,
                        message=str(exc),
                        detail={"request_id": getattr(request.state, "request_id", None)},
                    )
                )
                db.commit()
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.mount("/static", StaticFiles(directory=STORAGE_DIR), name="static")
    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    frontend_assets = frontend_dist / "assets"
    if frontend_dist.exists():
        if frontend_assets.exists():
            app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            if full_path.startswith(("api/", "static/", "assets/")):
                raise HTTPException(status_code=404, detail="Not Found")
            index_file = frontend_dist / "index.html"
            if not index_file.exists():
                raise HTTPException(status_code=404, detail="Frontend not built")
            return FileResponse(index_file)

    return app


app = create_app()
