from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import GENERATED_DIR, STORAGE_DIR, UPLOAD_DIR, get_settings
from app.db import session as db_session
from app.services.bootstrap import ensure_default_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    db_session.init_db()
    for directory in (STORAGE_DIR, UPLOAD_DIR, GENERATED_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    with db_session.SessionLocal() as db:
        ensure_default_admin(db)
    yield


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
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time"] = f"{(perf_counter() - start):.4f}"
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
        raise exc

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.mount("/static", StaticFiles(directory=STORAGE_DIR), name="static")
    return app


app = create_app()
