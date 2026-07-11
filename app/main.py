from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import GENERATED_DIR, PUBLIC_DIR, STORAGE_DIR, UPLOAD_DIR, VECTOR_DIR, get_settings, validate_production_settings
from app.core.security import decode_access_token
from app.db.models import SystemErrorLog
from app.db import session as db_session
from app.services.bootstrap import ensure_default_admin, ensure_system_settings
from app.services.request_logging import request_log_writer


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    db_session.init_db()
    for directory in (STORAGE_DIR, UPLOAD_DIR, PUBLIC_DIR, GENERATED_DIR, VECTOR_DIR):
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
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.openapi_enabled else None,
        redoc_url="/redoc" if settings.openapi_enabled else None,
        openapi_url="/openapi.json" if settings.openapi_enabled else None,
    )
    allow_origins = settings.cors_origin_list
    if settings.app_env != "production" and not allow_origins:
        allow_origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=settings.cors_allow_credentials,
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
        if settings.security_headers_enabled:
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "object-src 'none'; "
                "img-src 'self' data: blob: https:; "
                "media-src 'self' blob: https:; "
                "connect-src 'self' https:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self'",
            )
            if settings.app_env == "production":
                response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith(settings.api_v1_prefix):
            # 默认禁止缓存 API 响应：这些是按 token 鉴权的用户私有数据（如问答历史/会话），
            # 同一 URL(/qa/history 等)对不同用户内容不同。若无 no-store，浏览器可能把用户 A 的
            # 响应缓存后又喂给用户 B，导致"看到别人的聊天记录"。用 setdefault 不覆盖
            # 媒体/资料等显式设置了可缓存 Cache-Control 的接口。
            response.headers.setdefault("Cache-Control", "no-store")
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
                # 自定义 field_validator 抛 ValueError 时，exc.errors() 的 ctx 会含不可 JSON 序列化的
                # 异常对象，直接下发会在 JSONResponse 渲染时抛 TypeError 变成 500；用 jsonable_encoder
                # 统一清洗，保证任何入参校验失败都返回规范 422。（修复 DEF-04）
                "data": jsonable_encoder(exc.errors()),
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
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")
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
