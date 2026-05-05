# ClassAgent

<div align="center">

**面向课程教学场景的 AI 学习、授课与运维一体化平台**

让课程资料、课堂学习、AI 问答、测验练习、错题复盘和教学分析形成完整闭环。

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-42B883?style=flat-square&logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=flat-square&logo=vite&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-ready-4479A1?style=flat-square&logo=mysql&logoColor=white)

</div>

## Overview

ClassAgent 是一个以课程为边界的数据隔离式 AI 教学系统。学生可以围绕单门课程学习课件、提问、做题和复盘错题；教师可以上传资料、生成课时、审核讲稿、创建测验并追踪学情；管理员可以统一管理用户、课程、模型、存储、外部 AI 服务与系统运维。

项目适合课堂辅助教学、在线课程管理、校内私有化智能学习平台和课程资料知识库建设。

## Highlights

- **课程级 AI 问答**：按课程隔离上下文、历史记录和资料召回，支持文本与图片提问。
- **资料解析与向量化**：支持 PPT、PDF、Word、TXT、Markdown 等课程资料上传、解析、切片和向量检索。
- **沉浸式课件学习**：课件页、文稿、AI 问答、笔记、音频播放和学习进度联动。
- **智能测验生成**：基于课程资料、章节、薄弱知识点生成练习，教师可二次编辑后发布。
- **错题本与重练**：按课程保存历史错题，支持知识点筛选、错题重练和掌握度跟踪。
- **教师教学分析**：统计学习时长、课时完成率、问答热度、成绩分布和薄弱知识点。
- **管理员控制台**：管理用户、课程、资料、模型配置、阿里云服务、日志、监控和备份。

## Roles

| 角色 | 核心能力 |
| --- | --- |
| 学生 | 加入课程、学习课件、AI 问答、题目辅导、章节练习、课堂测验、错题本、学习计划、个人档案 |
| 教师 | 课程管理、章节管理、资料上传、课件预览、课时生成、讲稿审核、TTS 合成、学生提醒、教学分析、AI 出题 |
| 管理员 | 用户管理、课程管理、资料审计、模型配置、Embedding 配置、OSS/OCR/文档解析/TTS 服务配置、系统监控 |

## Architecture

```mermaid
flowchart LR
  User[Student / Teacher / Admin] --> Web[Vue 3 + Vite Frontend]
  Web --> API[FastAPI API /api/v1]
  API --> DB[(MySQL)]
  API --> Redis[(Redis / Celery)]
  API --> Vector[(ChromaDB Vectors)]
  API --> Storage[(Local / OSS Storage)]
  API --> AI[LLM + Embedding]
  API --> Aliyun[Aliyun OCR / DocMind / TTS]
```

## Tech Stack

**Backend**

- Python 3.12
- FastAPI, Uvicorn
- SQLAlchemy 2.x, Pydantic Settings
- MySQL, Redis, Celery
- ChromaDB, LangChain Core
- Aliyun OSS / OCR / DocMind / TTS integrations

**Frontend**

- Vue 3, TypeScript, Vite
- Vue Router, Pinia
- ECharts, KaTeX, Markdown-it
- lucide-vue-next

## Project Structure

```text
.
├── app/                    # FastAPI backend
│   ├── api/routes/         # auth, courses, student, teacher, admin, qa, tutoring...
│   ├── core/               # settings, security, shared utilities
│   ├── db/                 # SQLAlchemy models and session
│   ├── schemas/            # request / response schemas
│   ├── services/           # AI, parser, material, quiz, storage, TTS services
│   └── tasks/              # async jobs
├── frontend/               # Vue frontend
│   ├── src/components/     # shared UI components
│   ├── src/router/         # modular route definitions
│   ├── src/styles/         # design tokens and role/page styles
│   └── src/views/          # product, auth, student, teacher, admin views
├── scripts/                # utility scripts
├── storage/                # uploads, generated files, logs, vectors, runtime files
├── tests/                  # backend tests
├── .env.example            # local configuration template
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

Runtime configuration is loaded from `.env`. Start from `.env.example`:

```text
APP_ENV=development
SECRET_KEY=change-this-secret-key-in-production
DATABASE_URL=mysql+pymysql://class_agent:class_agent_2026@127.0.0.1:3306/class_agent?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
PUBLIC_BASE_URL=http://127.0.0.1:8000
CHROMA_PERSIST_DIR=storage/vectors/chroma
EMBEDDING_DIMENSION=1536
EXTERNAL_AI_MODE=auto
EXTERNAL_STORAGE_MODE=auto
```

Default administrator:

```text
ADMIN_DEFAULT_EMAIL=admin@classagent.com
ADMIN_DEFAULT_PASSWORD=Admin123456
ADMIN_DEFAULT_NAME=系统管理员
```

Replace `SECRET_KEY`, administrator credentials, database credentials, model keys and storage credentials before production use.

## Common Commands

```bash
# Backend tests
pytest

# Frontend dev server
cd frontend
npm run dev

# Frontend production build
cd frontend
npm run build

# Frontend preview
cd frontend
npm run preview
```

## API Modules

All versioned APIs are mounted under:

```text
/api/v1
```

Representative modules:

- `/auth`
- `/courses`
- `/materials`
- `/learning`
- `/qa`
- `/tutoring`
- `/student`
- `/teacher`
- `/admin`
- `/analytics`
- `/health`

## Product Status

ClassAgent is under active development. The current focus is the full teaching workflow:

1. Upload course materials.
2. Parse, persist and vectorize course content.
3. Generate lessons, scripts and speech.
4. Support course-scoped AI Q&A and tutoring.
5. Generate quizzes from materials and weak points.
6. Track wrong questions, learning progress and teaching analytics.

## Security Notes

- Use MySQL and Redis in production.
- Rotate default administrator credentials before deployment.
- Store AI, OSS, OCR, DocMind and TTS credentials through environment variables or admin configuration.
- Keep uploaded files, generated audio, vector data and logs out of public repositories.
