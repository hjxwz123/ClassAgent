# 基础设施接口

## 健康检查

- 方法：`GET`
- 路径：`/api/v1/health`
- 是否鉴权：否

### 返回示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "service": "课程学习助手智能体后端",
    "environment": "development",
    "time": "2026-04-30T11:56:00.000000+00:00"
  },
  "request_id": "8c95a67b-13d4-4d1e-9be4-713f42564ef0"
}
```

## 当前阶段验证结论

- FastAPI 应用可正常启动。
- SQLAlchemy 数据库连接可正常初始化。
- 静态资源目录已挂载到 `/static`。
- 统一返回结构和参数校验错误结构已固定。
