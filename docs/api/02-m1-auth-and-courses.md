# M1 用户与课程管理接口

## 1. 用户注册

- 方法：`POST`
- 路径：`/api/v1/auth/register`
- 鉴权：否

### 请求体

```json
{
  "email": "teacher@example.com",
  "password": "Teacher123",
  "nickname": "张老师",
  "role": "teacher",
  "employee_no": "T2026001"
}
```

### 说明

- `role` 仅支持 `student`、`teacher`
- 学生必须传 `student_no`
- 教师必须传 `employee_no`

## 2. 登录

- 方法：`POST`
- 路径：`/api/v1/auth/login`

### 请求体

```json
{
  "email": "student@example.com",
  "password": "Student123"
}
```

### 返回重点字段

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "user": {
      "id": 2,
      "email": "student@example.com",
      "role": "student",
      "nickname": "李同学",
      "status": "active"
    }
  }
}
```

## 3. 获取当前用户信息

- 方法：`GET`
- 路径：`/api/v1/auth/me`
- 鉴权：是

## 4. 修改个人资料

- 方法：`PATCH`
- 路径：`/api/v1/auth/me`

### 请求体

```json
{
  "nickname": "李同学-1",
  "avatar_url": "https://example.com/avatar.png",
  "bio": "热爱学习"
}
```

## 5. 修改登录密码

- 方法：`POST`
- 路径：`/api/v1/auth/me/password`

### 请求体

```json
{
  "old_password": "Student123",
  "new_password": "Student456"
}
```

## 6. 请求找回密码验证码

- 方法：`POST`
- 路径：`/api/v1/auth/password/reset/request`

### 请求体

```json
{
  "email": "student@example.com"
}
```

### 返回说明

- 开发环境会返回 `debug_code`，前端联调可直接使用。
- 生产环境 `debug_code` 为 `null`，后续接入真实邮件服务即可。

## 7. 确认重置密码

- 方法：`POST`
- 路径：`/api/v1/auth/password/reset/confirm`

### 请求体

```json
{
  "email": "student@example.com",
  "code": "458356",
  "new_password": "Student789"
}
```

## 8. 教师创建课程

- 方法：`POST`
- 路径：`/api/v1/courses`
- 鉴权：教师 / 管理员

### 请求体

```json
{
  "name": "高等数学",
  "description": "极限与导数",
  "term": "2026春"
}
```

### 返回重点字段

- `course_code`：学生加入课程使用
- `status`：默认 `active`

## 9. 教师查看本人授课课程

- 方法：`GET`
- 路径：`/api/v1/courses/teaching`

## 10. 学生查看已加入课程

- 方法：`GET`
- 路径：`/api/v1/courses/enrolled`

## 11. 学生加入课程

- 方法：`POST`
- 路径：`/api/v1/courses/join`

### 请求体

```json
{
  "course_code": "A1B2C3"
}
```

## 12. 查看课程详情

- 方法：`GET`
- 路径：`/api/v1/courses/{course_id}`

### 返回结构

- `course`：课程基础信息
- `teacher`：授课教师
- `chapters`：章节列表
- `student_count`：当前学生人数

## 13. 修改课程

- 方法：`PATCH`
- 路径：`/api/v1/courses/{course_id}`
- 鉴权：课程教师 / 管理员

## 14. 停用课程

- 方法：`POST`
- 路径：`/api/v1/courses/{course_id}/deactivate`

## 15. 创建章节

- 方法：`POST`
- 路径：`/api/v1/courses/{course_id}/chapters`

### 请求体

```json
{
  "title": "第一章 极限",
  "description": "课程引导",
  "order_index": 1
}
```

## 16. 查看课程学生列表

- 方法：`GET`
- 路径：`/api/v1/courses/{course_id}/members`

## 17. 学生退出课程

- 方法：`POST`
- 路径：`/api/v1/courses/{course_id}/leave`

## 初始化说明

- 服务启动时会自动初始化默认管理员。
- 默认账号来自 `.env`：
  - `ADMIN_DEFAULT_EMAIL`
  - `ADMIN_DEFAULT_PASSWORD`
  - `ADMIN_DEFAULT_NAME`

## 当前阶段验证结论

- 已通过注册、登录、JWT 鉴权、课程创建、课程加入、课程详情、课程成员、修改密码、验证码重置密码的集成测试。
