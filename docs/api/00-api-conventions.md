# API 统一规范

## 基础约定

- 基础前缀：`/api/v1`
- 数据格式：`application/json`
- 字符编码：`UTF-8`
- 鉴权方式：`Authorization: Bearer <token>`

## 成功响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "f198b727-faa3-4352-8911-508bd0ae63f4"
}
```

## 分页响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "pagination": {
      "total": 0,
      "page": 1,
      "page_size": 20
    }
  },
  "request_id": "0bb947c6-3da5-4bcc-b0ba-1cf9a4e0d4ab"
}
```

## 错误响应格式

```json
{
  "code": 401,
  "message": "未认证或令牌无效",
  "data": null,
  "request_id": "91b1b97d-5b9f-4d91-9782-9e0ce9588288"
}
```

## 常用状态码

- `200`：请求成功
- `400`：业务参数错误
- `401`：未登录或令牌失效
- `403`：无权限
- `404`：资源不存在
- `422`：请求体校验失败
- `500`：服务内部异常

## 统一前端约定

- 所有时间字段均返回 ISO 8601 字符串。
- 文件和音频等资源统一返回可直接访问的 URL。
- 列表接口默认使用 `page`、`page_size`。
- 可选筛选项保持扁平结构，避免嵌套查询对象。
