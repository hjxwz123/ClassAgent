# 一期生产部署说明

本文档用于把后端从开发模式切到一期生产可运行模式。

## 1. 基础依赖

当前项目生产运行需要：

| 组件 | 用途 |
| --- | --- |
| MySQL 8.x | 主数据库 |
| Redis 7.x | 缓存、Celery Broker、任务结果 |
| Chroma | 课程资料向量库与 RAG 检索 |
| mysqldump / mysql | MySQL 备份与恢复 |
| FastAPI / Uvicorn | 后端 API 服务 |
| Celery Worker | 资料解析、讲解生成、音频生成等后台任务 |

当前服务器已检测到：

- Redis 已运行，`redis://localhost:6379/1` 可用
- MySQL 已运行，但当前 shell 没有免密 root 权限，需要你提供或创建业务库账号
- Celery 依赖已安装在 `.venv`

## 2. 生产环境变量

参考 `.env.production.example` 创建 `.env`：

```bash
cp .env.production.example .env
```

必须修改：

| 配置项 | 要求 |
| --- | --- |
| `SECRET_KEY` | 换成足够长的随机字符串 |
| `DATABASE_URL` | 换成真实 MySQL 连接串 |
| `CELERY_TASK_ALWAYS_EAGER` | 生产必须是 `false` |
| `PUBLIC_BASE_URL` | 换成线上访问域名 |
| `ADMIN_DEFAULT_PASSWORD` | 换成真实管理员初始密码 |
| `CHROMA_PERSIST_DIR` | Chroma 持久化目录，默认 `storage/vectors/chroma` |

推荐生产配置：

```env
APP_ENV=production
CELERY_TASK_ALWAYS_EAGER=false
EXTERNAL_AI_MODE=strict
EXTERNAL_STORAGE_MODE=auto
```

说明：

- `EXTERNAL_AI_MODE=strict`：生产环境没有模型配置时直接报错，避免继续使用本地 mock 结果。
- `EXTERNAL_STORAGE_MODE=auto`：管理员启用 OSS 时上传到 OSS，未配置 OSS 时自动使用本地存储。

## 3. MySQL 初始化

如果你有 MySQL root 权限，可以执行类似命令：

```sql
CREATE DATABASE class_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'class_agent'@'127.0.0.1' IDENTIFIED BY 'replace-password';
GRANT ALL PRIVILEGES ON class_agent.* TO 'class_agent'@'127.0.0.1';
FLUSH PRIVILEGES;
```

然后设置：

```env
DATABASE_URL=mysql+pymysql://class_agent:replace-password@127.0.0.1:3306/class_agent?charset=utf8mb4
```

## 4. 启动 API 服务

```bash
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

生产建议由进程管理器托管，例如 systemd、Supervisor 或宝塔的 Python 项目管理器。

## 5. 启动 Celery Worker

生产环境必须启动 worker：

```bash
. .venv/bin/activate
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --concurrency=2
```

当前 worker 已验证可以识别任务：

```text
materials.process
```

## 6. 管理员配置 API 信息

启动后打开：

```text
http://127.0.0.1:8000/docs
```

先用管理员账号登录：

- `POST /api/v1/auth/login`

然后配置模型：

- `POST /api/v1/admin/model-configs`
- `POST /api/v1/admin/model-configs/{config_id}/test`

至少需要配置：

- `purpose=qa`：课程问答
- `purpose=embedding`：资料向量化和 RAG 检索
- `purpose=script`：讲解脚本生成
- `purpose=quiz`：测验生成
- `purpose=tutoring`：题目辅导
- `purpose=analysis`：教学建议

再按需配置外部服务：

- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`

资料上传解析必须配置 `service_type=doc_parser`、`provider=aliyun` 的阿里云文档解析（大模型版）服务。

生产找回密码需要配置 `service_type=email` 的 SMTP 服务。

## 7. 存储模式

管理员可以选择本地存储或 OSS：

- 不配置 OSS：自动使用本地存储
- 配置并启用 `service_type=oss`：上传文件和生成音频会同步写入 OSS，并返回 OSS 访问地址
- 禁用 OSS 配置：恢复本地存储

OSS 配置示例见 `docs/api/06-service-configuration.md`。

## 8. 上线前验证

建议上线前至少验证：

```bash
. .venv/bin/activate
pytest
```

还需要人工验证：

- 管理员登录
- 模型配置测试通过
- 资料上传后 Celery worker 能完成解析
- 资料上传后 `vector_status=ready`
- PPT/PDF/DOCX/TXT 至少各上传一个样例
- 学生问答能返回真实模型结果
- 题目图片 OCR 能识别
- 讲解音频能播放
