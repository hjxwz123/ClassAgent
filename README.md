# ClassAgent

<p align="center">
  <strong>面向课程教学场景的 AI 学习助手平台</strong>
</p>

<p align="center">
  <a href="#quick-start">快速开始</a>
  ·
  <a href="#features">功能能力</a>
  ·
  <a href="#architecture">系统架构</a>
  ·
  <a href="#documentation">项目文档</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="Vue" src="https://img.shields.io/badge/Vue-3.5+-42B883?style=flat-square&logo=vuedotjs&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.9+-3178C6?style=flat-square&logo=typescript&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-Private-lightgrey?style=flat-square">
</p>

ClassAgent 是一个覆盖学生学习、教师教学和管理员运维的课程学习助手系统。项目围绕课程资料构建 RAG 知识库，支持课时学习、AI 问答、图片 OCR 提问、题目辅导、智能组卷、错题重练、学习计划、教学分析和系统配置。

## Features

### 学生端

- 工作台：学习进度、今日推荐、学习动态、继续学习入口
- 课程学习：沉浸式课件播放、脚本阅读、字幕、笔记、课时进度记录
- AI 问答：课程范围内 RAG 问答、Markdown/LaTeX 渲染、SSE 流式输出、思考过程展示
- 图片提问：上传图片后 OCR 识别，并将识别内容并入课程检索和回答
- 题目辅导：文字题和图片题输入，按提示、思路、详解逐级辅导
- 知识点精讲：按章节查看知识点、掌握度和针对性练习
- 练习测验：章节练习、薄弱点优先组卷、错题重练、答题卡和交卷反馈
- 学习计划：AI 生成任务、日历打卡、周统计和成就徽章
- 个人中心：PC 端学习档案、资料维护、账号安全和通知设置

### 教师端

- 课程管理：课程、章节、资料、课时发布与重处理
- 资料处理：PPT/PDF/DOCX/TXT 上传、解析、脚本生成、音频生成和向量化
- 作业与测验：测验发布、提交统计、错题与薄弱点分析
- 学生管理：学生列表、学习进度、问答记录、成绩和风险提示
- 教学分析：课程热度、活跃度、掌握情况和 AI 教学建议

### 管理端

- 用户、课程、公告、权限和系统设置管理
- 模型配置：按 `qa`、`embedding`、`script`、`quiz`、`tutoring`、`analysis` 等用途配置 OpenAI-compatible 模型
- 外部服务：阿里云文档解析、OCR、TTS、OSS、SMTP 等运行时配置
- 监控运维：请求日志、系统日志、备份恢复、服务健康检查

## Architecture

```text
frontend/                 Vue 3 + TypeScript + Vite
  src/views               学生端、教师端、管理员端页面
  src/components          复用表单、弹窗、进度、选择器组件

app/                      FastAPI 后端
  api/routes              REST API 与 SSE 流式接口
  services                业务服务、AI 调用、RAG 检索、资料处理
  db                      SQLAlchemy 模型、会话、轻量 schema 升级
  schemas                 Pydantic 请求与响应模型

docs/                     API、部署、前端阶段文档
tests/                    Pytest 端到端业务流测试
storage/                  本地上传、生成文件、向量库和运行时数据
```

核心链路：

```text
课程资料上传
  -> 文档解析
  -> 课时页面与讲解稿
  -> 向量化知识片段
  -> 学生学习 / AI 问答 / 练习生成 / 教学分析
```

## Tech Stack

| Layer | Stack |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Pinia, ECharts, Markdown-It, KaTeX, lucide-vue-next |
| Backend | FastAPI, SQLAlchemy 2, Pydantic Settings, Uvicorn, Celery, Redis |
| AI/RAG | OpenAI-compatible Chat API, Chroma, langchain-core `ChatPromptTemplate`, local fallback logic |
| Storage | Local storage by default, optional Aliyun OSS |
| External services | Aliyun DocMind, Aliyun OCR, Aliyun TTS, SMTP |
| Test | Pytest, FastAPI TestClient, frontend production build |

## Quick Start

### 1. Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

API health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Default administrator:

```text
email: admin@classagent.com
password: Admin123456
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server proxies:

```text
/api    -> http://127.0.0.1:8000
/static -> http://127.0.0.1:8000
```

### 3. Worker

Development mode defaults to eager Celery execution. In production or async mode, start a worker:

```bash
. .venv/bin/activate
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --concurrency=2
```

## Configuration

Create `.env` from `.env.example`:

```env
APP_ENV=development
DATABASE_URL=mysql+pymysql://class_agent:class_agent_2026@127.0.0.1:3306/class_agent?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=true
EXTERNAL_AI_MODE=auto
EXTERNAL_STORAGE_MODE=auto
PUBLIC_BASE_URL=http://127.0.0.1:8000
```

Important modes:

| Variable | Description |
| --- | --- |
| `EXTERNAL_AI_MODE=auto` | Development fallback is allowed when model config is missing |
| `EXTERNAL_AI_MODE=strict` | Production mode should require configured AI services |
| `EXTERNAL_STORAGE_MODE=auto` | Use OSS when enabled, otherwise local storage |
| `CELERY_TASK_ALWAYS_EAGER=true` | Run background tasks synchronously for local development |

Production setup is documented in [docs/production-deployment.md](docs/production-deployment.md).

## Scripts

Backend:

```bash
. .venv/bin/activate
pytest
python3 -m py_compile app/services/qa.py app/api/routes/qa.py
```

Frontend:

```bash
cd frontend
npm run build
npm run preview
```

## Documentation

- [API 统一规范](docs/api/00-api-conventions.md)
- [基础设施](docs/api/01-foundation.md)
- [M1 用户与课程](docs/api/02-m1-auth-and-courses.md)
- [M2 资料管理](docs/api/03-m2-materials.md)
- [M3-M6 学习核心](docs/api/04-m3-m6-learning-core.md)
- [M7-M8 分析与管理](docs/api/05-m7-m8-analytics-admin.md)
- [服务 API 配置说明](docs/api/06-service-configuration.md)
- [向量检索与 RAG](docs/api/07-vector-rag.md)
- [教师控制台](docs/api/08-teacher-console.md)
- [学生控制台](docs/api/09-student-console.md)
- [前端阶段说明](docs/frontend-phase1.md)
- [生产部署说明](docs/production-deployment.md)

## Repository Notes

- The backend owns API contracts, permissions, RAG retrieval, model invocation, usage logs and persistence.
- The frontend keeps student, teacher and admin experiences in dedicated Vue views.
- AI calls are configured at runtime through admin APIs. The code keeps local fallback logic for development.
- Uploaded course files and generated assets are stored under `storage/` unless OSS is enabled.
- The project currently uses `langchain-core` only for prompt templates; RAG orchestration is implemented in local services.

## License

Private project. Add a license before public distribution.
