# ClassAgent Backend

课程学习助手智能体后端，基于 FastAPI + SQLAlchemy + Celery。

## 功能范围

- M1 用户与课程管理
- M2 资料上传、解析、脚本与音频生成
- M3 课堂学习、发布与进度记录
- M4 课程知识问答
- M5 题目辅导
- M6 知识点、测验、错题本、学习计划
- M7 教学分析
- M8 管理员配置、监控、日志、备份

## 本地启动

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 前端启动

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

## 测试

```bash
. .venv/bin/activate
pytest
```

## 默认配置

- 配置样例见 `.env.example`
- 默认管理员：
  - `ADMIN_DEFAULT_EMAIL=admin@classagent.com`
  - `ADMIN_DEFAULT_PASSWORD=Admin123456`

## 接口文档

- [API 统一规范](docs/api/00-api-conventions.md)
- [基础设施](docs/api/01-foundation.md)
- [M1 用户与课程](docs/api/02-m1-auth-and-courses.md)
- [M2 资料管理](docs/api/03-m2-materials.md)
- [M3-M6 学习核心](docs/api/04-m3-m6-learning-core.md)
- [M7-M8 分析与管理](docs/api/05-m7-m8-analytics-admin.md)
- [服务 API 配置说明](docs/api/06-service-configuration.md)
- [一期生产部署说明](docs/production-deployment.md)
