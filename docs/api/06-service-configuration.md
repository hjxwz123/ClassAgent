# 服务 API 配置说明

当前项目的服务配置分成两层：`基础运行配置` 和 `外部服务 API 配置`。不要把所有参数都写到一个地方。

## 1. 基础运行配置

基础运行配置放在项目根目录的 `.env` 文件中。

首次使用时，先参考 `.env.example` 创建 `.env`：

```bash
cp .env.example .env
```

当前支持的基础配置项如下：

| 配置项 | 说明 |
| --- | --- |
| `APP_ENV` | 运行环境，例如 `development` |
| `SECRET_KEY` | JWT / 会话签名密钥 |
| `DATABASE_URL` | 数据库连接串 |
| `REDIS_URL` | Redis 连接串 |
| `CELERY_BROKER_URL` | Celery Broker 地址 |
| `CELERY_RESULT_BACKEND` | Celery 结果存储地址 |
| `CELERY_TASK_ALWAYS_EAGER` | 是否同步执行任务，开发环境默认 `true` |
| `EXTERNAL_AI_MODE` | AI 调用模式，生产建议 `strict` |
| `EXTERNAL_STORAGE_MODE` | 存储模式，默认 `auto` |
| `CHROMA_PERSIST_DIR` | Chroma 向量库持久化目录 |
| `EMBEDDING_DIMENSION` | 开发环境本地 embedding 维度 |
| `EXTERNAL_SERVICE_TIMEOUT_SECONDS` | 外部服务请求超时时间 |
| `PUBLIC_BASE_URL` | 对外访问地址 |
| `ADMIN_DEFAULT_EMAIL` | 默认管理员邮箱 |
| `ADMIN_DEFAULT_PASSWORD` | 默认管理员密码 |
| `ADMIN_DEFAULT_NAME` | 默认管理员名称 |

示例：

```env
APP_ENV=development
SECRET_KEY=change-this-secret-key-in-production
DATABASE_URL=sqlite:///./storage/app.db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_ALWAYS_EAGER=true
EXTERNAL_AI_MODE=auto
EXTERNAL_STORAGE_MODE=auto
EXTERNAL_SERVICE_TIMEOUT_SECONDS=30
PUBLIC_BASE_URL=http://127.0.0.1:8000
ADMIN_DEFAULT_EMAIL=admin@classagent.com
ADMIN_DEFAULT_PASSWORD=Admin123456
ADMIN_DEFAULT_NAME=系统管理员
```

说明：

- 仓库默认提供的是 `.env.example`
- 你需要自己创建实际生效的 `.env`

## 2. 外部服务 API 配置

大模型、Embedding、OSS、OCR、TTS、邮件这类外部服务，不通过 `.env` 直接维护，而是通过管理员接口写入数据库。

这样做的原因：

- 方便在后台动态修改
- 支持多套配置切换
- 便于后续做启停、测试、默认值选择

其中存储是例外规则：

- 未配置 OSS 时，系统自动使用本地存储
- 配置并启用 `service_type=oss` 后，系统上传到 OSS，并返回 OSS 地址
- 管理员禁用 OSS 配置后，系统恢复本地存储

## 3. 配置入口

后端启动后，打开 Swagger 文档：

```text
http://127.0.0.1:8000/docs
```

先登录获取管理员 token，再调用管理员接口。

默认管理员账号：

- 邮箱：`admin@classagent.com`
- 密码：`Admin123456`

登录接口：

- `POST /api/v1/auth/login`

## 4. 模型 API 配置

模型相关配置走下面这组接口：

- `GET /api/v1/admin/model-configs`
- `POST /api/v1/admin/model-configs`
- `POST /api/v1/admin/model-configs/{config_id}/test`
- `DELETE /api/v1/admin/model-configs/{config_id}`

生产问答必须额外配置 Embedding：

```json
{
  "provider": "openai",
  "model_name": "text-embedding-3-small",
  "purpose": "embedding",
  "endpoint": "https://api.openai.com/v1",
  "api_key": "sk-xxxx",
  "is_default": true,
  "extra_config": {
    "dimensions": 1536
  }
}
```
- `GET /api/v1/admin/model-usage`

适用场景：

- OpenAI
- 通义千问
- DeepSeek
- 其他聊天、问答、生成类模型

示例请求：

```json
{
  "provider": "openai",
  "model_name": "gpt-4o-mini",
  "purpose": "qa",
  "endpoint": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "is_default": true,
  "extra_config": {
    "temperature": 0.2
  }
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `provider` | 服务提供方，例如 `openai`、`aliyun`、`deepseek` |
| `model_name` | 模型名称 |
| `purpose` | 用途，例如 `qa`、`summary`、`script` |
| `endpoint` | 模型服务地址 |
| `api_key` | 模型 API Key |
| `is_default` | 是否作为该用途默认模型 |
| `extra_config` | 额外配置 |

`endpoint` 支持 OpenAI 兼容格式。可以填写：

- `https://api.openai.com/v1`
- `https://api.deepseek.com`
- `https://dashscope.aliyuncs.com/compatible-mode/v1`

后端会自动拼接 `/chat/completions`。如果你已经填写完整的 `/chat/completions` 地址，也可以直接使用。

建议按用途分别配置：

| purpose | 用途 |
| --- | --- |
| `general` | 通用兜底模型 |
| `qa` | 课程问答 |
| `script` | 讲解脚本生成 |
| `summary` | 课堂摘要 |
| `knowledge` | 知识点抽取与讲解 |
| `quiz` | 测验生成与主观题评分 |
| `tutoring` | 题目辅导 |
| `study_plan` | 学习计划 |
| `analysis` | 教学分析建议 |

## 5. OSS / OCR / TTS 配置

外部基础服务走下面这组接口：

- `GET /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`
- `DELETE /api/v1/admin/service-configs/{config_id}`

适用场景：

- 阿里云 OSS
- 阿里云 OCR
- 阿里云 TTS
- SMTP 邮件服务

### 5.1 OSS 配置示例

```json
{
  "service_type": "oss",
  "provider": "aliyun",
  "name": "aliyun-oss",
  "config": {
    "access_key_id": "xxx",
    "access_key_secret": "xxx",
    "endpoint": "https://oss-cn-hangzhou.aliyuncs.com",
    "region": "cn-hangzhou",
    "bucket": "examplebucket"
  },
  "is_enabled": true
}
```

说明：

- OSS 不是强制配置项
- 不配置 OSS 时自动使用本地存储
- 如果配置了 `public_base_url` 或 `cdn_domain`，返回文件地址时会优先使用该地址

### 5.2 OCR 配置示例

```json
{
  "service_type": "ocr",
  "provider": "aliyun",
  "name": "aliyun-ocr",
  "config": {
    "access_key_id": "xxx",
    "access_key_secret": "xxx",
    "endpoint": "green.cn-shanghai.aliyuncs.com",
    "region": "cn-shanghai"
  },
  "is_enabled": true
}
```

### 5.3 TTS 配置示例

```json
{
  "service_type": "tts",
  "provider": "aliyun",
  "name": "aliyun-tts",
  "config": {
    "appkey": "xxx",
    "token": "xxx",
    "url": "https://nls-gateway-ap-southeast-1.aliyuncs.com/stream/v1/tts",
    "method": "GET",
    "voice": "xiaoyun",
    "format": "wav",
    "sample_rate": 16000,
    "speech_rate": 0,
    "volume": 50
  },
  "is_enabled": true
}
```

### 5.4 邮件配置示例

用于找回密码验证码。

```json
{
  "service_type": "email",
  "provider": "smtp",
  "name": "smtp-mail",
  "config": {
    "host": "smtp.example.com",
    "port": 587,
    "username": "noreply@example.com",
    "password": "邮箱授权码",
    "sender": "noreply@example.com",
    "use_tls": true,
    "use_ssl": false
  },
  "is_enabled": true
}
```

## 6. 配置建议

建议按下面方式区分：

- `model-configs`：配置大模型接口
- `service-configs`：配置 OSS / OCR / TTS / Email 等基础服务
- `.env`：配置应用自身运行参数

不要把阿里云的所有信息都硬编码到代码里，也不要把可动态调整的服务配置全部塞进 `.env`。

## 7. 当前项目现状

当前后端已经提供真实服务接入：

- OSS：阿里云 OSS SDK
- OCR：阿里云 OCR SDK
- TTS：阿里云 TTS REST 调用
- Email：SMTP
- Embedding：OpenAI 兼容 `/embeddings`

开发环境未配置时可使用本地占位能力，生产环境必须配置真实服务。

如果你接下来要接阿里云，优先看：

- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`
- `POST /api/v1/admin/model-configs`

## 8. 官方参考

- 阿里云 OSS Python SDK 上传对象：<https://help.aliyun.com/zh/oss/developer-reference/upload-an-object>
- 阿里云 OCR 通用文字识别 RecognizeGeneral：<https://help.aliyun.com/zh/ocr/developer-reference/api-ocr-api-2021-07-07-recognizegeneral>
- 阿里云智能语音交互 RESTful TTS：<https://help.aliyun.com/zh/isi/developer-reference/restful-api-3>
