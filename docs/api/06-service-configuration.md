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
PUBLIC_BASE_URL=http://127.0.0.1:8000
ADMIN_DEFAULT_EMAIL=admin@classagent.com
ADMIN_DEFAULT_PASSWORD=Admin123456
ADMIN_DEFAULT_NAME=系统管理员
```

说明：

- 仓库默认提供的是 `.env.example`
- 你需要自己创建实际生效的 `.env`

## 2. 外部服务 API 配置

大模型、OSS、OCR、TTS 这类外部服务，不通过 `.env` 直接维护，而是通过管理员接口写入数据库。

这样做的原因：

- 方便在后台动态修改
- 支持多套配置切换
- 便于后续做启停、测试、默认值选择

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
- `GET /api/v1/admin/model-usage`

适用场景：

- OpenAI
- 通义千问
- DeepSeek
- 其他聊天、问答、生成类模型

示例请求：

```json
{
  "provider": "mock",
  "model_name": "mock-v1",
  "purpose": "qa",
  "endpoint": null,
  "api_key": "mock-key",
  "is_default": true,
  "extra_config": {
    "note": "test"
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

## 5. OSS / OCR / TTS 配置

外部基础服务走下面这组接口：

- `GET /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`

适用场景：

- 阿里云 OSS
- 阿里云 OCR
- 阿里云 TTS
- 后续其他第三方服务

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
    "voice": "xiaoyun",
    "speech_rate": 0,
    "volume": 50
  },
  "is_enabled": true
}
```

## 6. 配置建议

建议按下面方式区分：

- `model-configs`：配置大模型接口
- `service-configs`：配置 OSS / OCR / TTS 等基础服务
- `.env`：配置应用自身运行参数

不要把阿里云的所有信息都硬编码到代码里，也不要把可动态调整的服务配置全部塞进 `.env`。

## 7. 当前项目现状

当前后端已经预留了完整的配置入口和测试接口，但部分第三方能力仍是本地 mock 实现。也就是说：

- 配置入口已经有了
- 接口文档已经有了
- 真实接入某些云服务时，仍需要把对应服务实现替换成正式 SDK / HTTP 调用

如果你接下来要接阿里云，优先看：

- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`
- `POST /api/v1/admin/model-configs`

