# ClassAgent

ClassAgent 是一个面向课程教学场景的 AI 学习与授课平台。系统以课程为边界组织资料、课时、问答、练习、错题、学习数据和教学分析，提供学生端、教师端和管理员端三类工作台。

## 核心能力

- 学生端：加入课程、学习课件、向 AI 提问、题目辅导、章节练习、课堂测验、错题本、学习计划和个人档案。
- 教师端：课程和章节管理、资料上传、课时生成、讲稿审核、TTS 合成、测验出题、学生提醒和学情分析。
- 管理员端：用户管理、课程管理、资料审计、模型配置、Embedding 配置、OSS/OCR/文档解析/TTS 服务配置和系统监控。
- AI 能力：课程级知识问答、资料召回、图片 OCR 提问、课程资料解析、向量检索、智能练习生成和个性化学习建议。

## 技术栈

**后端**

- Python 3.12
- FastAPI, Uvicorn
- SQLAlchemy 2.x, Pydantic Settings
- MySQL, Redis, Celery
- ChromaDB, LangChain Core
- Aliyun OSS / OCR / DocMind / TTS

**前端**

- Vue 3, TypeScript, Vite
- Vue Router, Pinia
- ECharts, KaTeX, Markdown-it
- lucide-vue-next

## 目录结构

```text
.
├── app/                    # FastAPI 后端
│   ├── api/routes/         # auth, courses, student, teacher, admin, qa, tutoring 等接口
│   ├── core/               # 配置、安全、依赖和通用响应
│   ├── db/                 # SQLAlchemy 模型和数据库会话
│   ├── schemas/            # 请求和响应结构
│   ├── services/           # AI、课程、资料、学习、存储、分析等业务服务
│   └── tasks/              # Celery 异步任务
├── frontend/               # Vue 前端
│   ├── src/components/     # 通用组件
│   ├── src/router/         # 路由定义
│   ├── src/styles/         # 设计变量和页面样式
│   └── src/views/          # 学生端、教师端、管理员端和认证页
├── scripts/                # 工具脚本
├── storage/                # 上传文件、生成文件、日志和向量数据
├── tests/                  # 后端测试
├── .env.example            # 本地环境变量模板
├── pyproject.toml          # 后端包配置
└── README.md
```

## 本地启动

### 后端

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 前端测试端口

前端测试端口固定使用 `5173`：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

访问：

```text
http://127.0.0.1:5173
```

## 常用命令

```bash
# 后端测试
pytest

# 前端开发服务，测试端口 5173
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort

# 前端生产构建
cd frontend
npm run build

# 前端构建预览
cd frontend
npm run preview
```

## 环境变量

运行配置从 `.env` 读取，建议从 `.env.example` 复制后修改：

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
ADMIN_DEFAULT_EMAIL=admin@classagent.com
ADMIN_DEFAULT_PASSWORD=Admin123456
ADMIN_DEFAULT_NAME=系统管理员
```

生产环境需要替换 `SECRET_KEY`、默认管理员账号、数据库账号、模型密钥和外部存储服务密钥。

## API 入口

所有版本化接口挂载在：

```text
/api/v1
```

主要模块：

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

## 构建和发布

前端构建产物输出到 `frontend/dist`：

```bash
cd frontend
npm run build
```

后端建议使用 MySQL、Redis 和独立对象存储运行。上传文件、生成音频、向量库和日志默认位于 `storage/`，这些运行时数据不应提交到 Git。

## 安全注意事项

- 生产环境必须更换默认管理员账号和 `SECRET_KEY`。
- AI、OSS、OCR、DocMind、TTS 等密钥应通过环境变量或管理员配置保存。
- 上传文件、生成文件、向量数据和日志需要按环境隔离。
- 对外部署时应限制后台管理入口、开启 HTTPS，并配置反向代理请求大小和超时时间。
