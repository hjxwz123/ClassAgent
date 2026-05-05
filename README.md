# ClassAgent

ClassAgent 是一个面向课程教学场景的 AI 学习助手平台，提供学生学习、教师授课管理和管理员运维配置三类工作台。项目围绕课程资料解析、AI 问答、课时学习、测验生成、错题复盘和教学分析构建，适用于课堂辅助教学、在线课程管理和学习过程追踪。

## Features

- 学生端：课程学习、课时进度、AI 问答、拍照提问、题目辅导、测验练习、错题本、学习计划。
- 教师端：课程与章节管理、资料上传、课时生成、讲稿审核、语音合成、测验生成、薄弱题目管理、学生分析。
- 管理员端：用户管理、课程管理、资料管理、模型配置、外部服务配置、系统监控、日志与备份。
- AI 能力：课程资料理解、知识点提取、问答检索、测验出题、主观题评分、学习建议。
- 文件能力：支持 PPT、PDF、Word、TXT/Markdown 等课程资料解析与管理。

## Tech Stack

后端：

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Pydantic Settings
- Celery + Redis
- ChromaDB
- MySQL / SQLite

前端：

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- ECharts
- KaTeX
- lucide-vue-next

## Project Structure

```text
.
├── app/                    # FastAPI backend
│   ├── api/routes/         # API routes
│   ├── core/               # config, auth, common utilities
│   ├── db/                 # database models and session
│   ├── schemas/            # request/response schemas
│   └── services/           # business services
├── frontend/               # Vue frontend
│   ├── src/components/     # shared components
│   ├── src/router/         # route definitions
│   ├── src/styles/         # global and page styles
│   └── src/views/          # product, auth, student, teacher, admin views
├── tests/                  # backend tests
├── scripts/                # utility scripts
├── storage/                # runtime files, uploads, generated assets, vectors
├── pyproject.toml          # backend package metadata
└── README.md
```

## Quick Start

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Configuration

Runtime configuration is loaded from `.env`. Use `.env.example` as the local development template.

Common settings:

```text
APP_ENV=development
SECRET_KEY=change-this-secret-key-in-production
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/class_agent?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
PUBLIC_BASE_URL=http://127.0.0.1:8000
EXTERNAL_AI_MODE=auto
EXTERNAL_STORAGE_MODE=auto
```

Production deployments should replace the default secret key, use a production database, configure Redis, and avoid mock AI mode.

## Scripts

Backend tests:

```bash
pytest
```

Frontend development server:

```bash
cd frontend
npm run dev
```

Frontend production build:

```bash
cd frontend
npm run build
```

Frontend preview:

```bash
cd frontend
npm run preview
```

## Default Account

On first startup, the backend creates a default administrator account from environment variables:

```text
ADMIN_DEFAULT_EMAIL=admin@classagent.com
ADMIN_DEFAULT_PASSWORD=Admin123456
ADMIN_DEFAULT_NAME=系统管理员
```

Change these values before production use.

## API

The backend mounts all versioned APIs under:

```text
/api/v1
```

Representative modules:

- `/api/v1/auth`
- `/api/v1/courses`
- `/api/v1/student`
- `/api/v1/teacher`
- `/api/v1/learning`
- `/api/v1/admin`
- `/api/v1/health`

## Status

ClassAgent is under active development. The current focus is the complete teaching workflow from course material ingestion to AI-assisted learning, quiz generation, weak-point remediation, and operational management.
