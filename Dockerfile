FROM node:24-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 容器化部署默认使用 Qdrant 作为向量库（生产推荐）；从源码本地运行时代码默认仍是 chroma（零依赖）。
# 部署时可用环境变量 VECTOR_STORE_PROVIDER / QDRANT_URL 覆盖。
ENV VECTOR_STORE_PROVIDER=qdrant

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install . \
    && apt-get purge -y --auto-remove git

COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

RUN mkdir -p /app/storage/runtime /app/storage/backups /app/storage/uploads /app/storage/generated /app/storage/vectors

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
