# M7-M8 教学分析与系统管理接口

## 一、教学分析 M7

### 1. 课程分析总览

- 方法：`GET`
- 路径：`/api/v1/analytics/courses/{course_id}`
- 鉴权：课程教师 / 管理员
- 可选参数：`days`，默认 `30`

返回字段：

- `high_frequency_questions`
- `weak_points`
- `inactive_students`
- `score_distribution`
- `completion_rate`
- `suggestion`

## 二、管理员能力 M8

### 0. 总览与健康

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/service-health`
- `POST /api/v1/admin/service-health/test-all`

说明：

- `dashboard` 返回总览仪表盘所需的统计卡、趋势图、服务状态、最近操作、课程排行、最近注册、待处理事项。
- `dashboard` 可选参数：`activity_days=7|30|90`，默认 `30`，用于活跃度趋势切换。
- `service-health` 返回数据库、Redis、向量数据库、Celery、OSS、OCR、TTS、邮件、LLM 状态。

### 1. 用户管理

- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/stats`
- `GET /api/v1/admin/users/{user_id}`
- `POST /api/v1/admin/users/admin`
- `PATCH /api/v1/admin/users/{user_id}`
- `POST /api/v1/admin/users/{user_id}/reset-password`
- `DELETE /api/v1/admin/users/{user_id}`

#### 创建管理员示例

```json
{
  "email": "admin2@example.com",
  "password": "Admin123456",
  "nickname": "二号管理员"
}
```

### 2. 课程管理

- `GET /api/v1/admin/courses`
- `GET /api/v1/admin/courses/stats`
- `GET /api/v1/admin/courses/{course_id}`
- `POST /api/v1/admin/courses/{course_id}/deactivate`
- `POST /api/v1/admin/courses/{course_id}/takeover`

#### 接管课程示例

```json
{
  "teacher_id": 12
}
```

### 3. 资料审核

- `GET /api/v1/admin/materials`
- `GET /api/v1/admin/materials/stats`
- `DELETE /api/v1/admin/materials/{material_id}`

### 4. 模型配置

- `GET /api/v1/admin/model-configs`
- `POST /api/v1/admin/model-configs`
- `POST /api/v1/admin/model-configs/{config_id}/test`
- `DELETE /api/v1/admin/model-configs/{config_id}`
- `GET /api/v1/admin/model-usage`

#### 保存模型配置示例

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

### 5. 阿里云 / 外部服务配置

- `GET /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs`
- `POST /api/v1/admin/service-configs/{config_id}/test`
- `DELETE /api/v1/admin/service-configs/{config_id}`

#### OSS 配置建议字段

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

#### OCR 配置建议字段

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

#### TTS 配置建议字段

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

#### 文档解析配置建议字段

```json
{
  "service_type": "doc_parser",
  "provider": "aliyun",
  "name": "aliyun-doc-parser",
  "config": {
    "access_key_id": "xxx",
    "access_key_secret": "xxx",
    "endpoint": "docmind-api.cn-hangzhou.aliyuncs.com",
    "region": "cn-hangzhou",
    "timeout_seconds": 600,
    "poll_interval_seconds": 5,
    "layout_step_size": 100,
    "output_format": "markdown",
    "llm_enhancement": true,
    "enhancement_mode": "VLM"
  },
  "is_enabled": true
}
```

#### 邮件配置建议字段

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

说明：

- 当前后端已支持对配置进行加密存储和连通性测试。
- `provider=mock` 时，测试接口会直接返回成功，便于本地联调。
- 未配置 OSS 或禁用 OSS 时，文件会自动使用本地存储。

### 6. 系统参数

- `GET /api/v1/admin/system-settings`
- `PUT /api/v1/admin/system-settings/{key}`
- `POST /api/v1/admin/system-settings/restore-defaults`

默认参数含义：

- `upload.max_size_mb`：单文件上传上限，单位 MB
- `course.material.max_count`：单课程资料数量上限
- `lesson.script.max_length`：课堂讲解脚本最大长度
- `qa.context.turn_limit`：问答多轮上下文轮数
- `quiz.default_question_count`：默认测验题量
- `tutoring.default_release_level`：题目辅导默认开放级别
- `tts.default_voice`：默认 TTS 音色
- `tts.default_rate`：默认 TTS 语速
- `tts.default_volume`：默认 TTS 音量
- `system.announcement`：系统公告内容
- `system.announcement_enabled`：公告是否启用
- `system.announcement_scope`：公告展示对象
- `system.logo_url`：平台 Logo 地址
- `backup.schedule`：数据库定期备份计划
- `backup.notify_email`：备份失败通知邮箱

#### 更新公告示例

```json
{
  "value": "期中周系统维护公告"
}
```

### 7. 系统监控

- `GET /api/v1/admin/monitoring/overview`
- `GET /api/v1/admin/monitoring/timeseries`

返回字段：

- `online_users`
- `api_call_count_30m`
- `ai_call_count_30m`
- `ai_failure_count_30m`
- `async_queue_pending`
- `celery_queue_length`
- `database_status`
- `cache_status`

### 8. 日志管理

- `GET /api/v1/admin/logs/login`
- `GET /api/v1/admin/logs/operations`
- `GET /api/v1/admin/logs/errors`
- `POST /api/v1/admin/logs/errors/{error_id}/resolve`

通用参数：

- `limit`
- `start_at`
- `end_at`

登录日志额外支持：

- `user_id`
- `success`

操作日志额外支持：

- `user_id`
- `action`
- `target_type`

错误日志额外支持：

- `level`
- `source`

### 9. 数据备份

- `GET /api/v1/admin/backups/summary`
- `GET /api/v1/admin/backups`
- `POST /api/v1/admin/backups`
- `POST /api/v1/admin/backups/{backup_id}/restore`
- `POST /api/v1/admin/backups/{backup_id}/verify`
- `GET /api/v1/admin/backups/{backup_id}/download`
- `DELETE /api/v1/admin/backups/{backup_id}`

说明：

- SQLite 环境会备份数据库文件和 Chroma 向量库。
- MySQL 环境会调用 `mysqldump` 生成 SQL 备份，并同步打包 Chroma 向量库。
- 恢复后需要重启 API 与 Celery 服务。

## 阿里云官方参考

- OSS 初始化与 Endpoint / Region / Bucket 要求：
  - https://www.alibabacloud.com/help/en/oss/initialization-2
- OCR Python SDK 与 `RecognizeGeneral`：
  - https://help.aliyun.com/zh/ocr/developer-reference/api-ocr-api-2021-07-07-recognizegeneral
- TTS RESTful API 与 `appkey/token/voice/speech_rate/volume`：
  - https://www.alibabacloud.com/help/en/isi/developer-reference/restful-api-3

## 当前阶段验证结论

- 已通过教师课程分析、管理员用户管理、课程接管、资料审核、模型配置、服务配置、系统设置、监控总览、日志查询、备份创建的集成测试。
