# 教师端接口

基础前缀：`/api/v1/teacher`

所有 JSON 接口遵循统一响应格式。导出接口返回 `text/csv` 文件流。

## 工作台

- `GET /dashboard`

返回：

- `stats`：课程数、学生数、本周提问、待处理脚本
- `recent_courses`：近期课程
- `todos`：待办事项
- `weekly_activity`：本周学生动态
- `pending_scripts`：待审核脚本
- `ai_tasks`：AI 任务状态

## 我的课程

- `GET /courses`
- `GET /courses/{course_id}/home`
- `DELETE /courses/{course_id}`

`GET /courses` 返回教师名下课程及学生数、资料数、课堂数、发布率。

`GET /courses/{course_id}/home` 返回课程主页聚合数据：课程信息、章节、快捷统计、课堂列表、资料状态、近期活动、学生进度、AI 队列。

## 资料管理

- `GET /courses/{course_id}/materials/summary`

返回课程资料总数、已解析数、存储用量、按章节统计、按解析状态/类型统计。

资料上传、预览、删除、脚本审核沿用：

- `GET /api/v1/materials`
- `POST /api/v1/materials`
- `GET /api/v1/materials/{material_id}`
- `PATCH /api/v1/materials/{material_id}`
- `DELETE /api/v1/materials/{material_id}`
- `PATCH /api/v1/materials/pages/{page_id}/script`
- `POST /api/v1/materials/pages/{page_id}/script/regenerate`

## 章节管理

- `PATCH /courses/{course_id}/chapters/{chapter_id}`
- `DELETE /courses/{course_id}/chapters/{chapter_id}`

更新示例：

```json
{
  "title": "第一章 网络基础",
  "description": "",
  "order_index": 1
}
```

## 课堂管理

- `PATCH /lessons/{lesson_id}`
- `POST /lessons/{lesson_id}/duplicate`
- `DELETE /lessons/{lesson_id}`

发布、下线、学习进度沿用：

- `POST /api/v1/lessons/{lesson_id}/publish`
- `POST /api/v1/lessons/{lesson_id}/unpublish`
- `GET /api/v1/lessons/{lesson_id}`
- `GET /api/v1/lessons/{lesson_id}/progress`
- `POST /api/v1/lessons/{lesson_id}/progress`

## 学生管理

- `GET /courses/{course_id}/students`
- `GET /courses/{course_id}/students/export`
- `GET /courses/{course_id}/students/{student_id}`
- `POST /courses/{course_id}/students/{student_id}/remind`
- `DELETE /courses/{course_id}/students/{student_id}`

`students` 返回统计概览和学生列表。学生详情返回基本信息、课堂进度、问答记录、薄弱点。

## 教学分析

- `GET /courses/{course_id}/analysis?days=30`
- `GET /courses/{course_id}/analysis/export?days=30`

返回：

- `metrics`：活跃率、完成率、问答总量、平均分、薄弱点数量
- `lesson_completion`：各课堂完成率
- `high_frequency_questions`：高频问题
- `weak_points`：薄弱点
- `score_distribution`：成绩分布
- `student_layers`：活跃度分层
- `suggestion`：AI 教学建议

## 个人中心

- `GET /profile`
- `PATCH /profile`
- `PUT /profile/notifications`

个人信息更新示例：

```json
{
  "nickname": "刘明",
  "organization": "信息学院",
  "department": "计算机系",
  "bio": "主讲网络课程"
}
```

通知设置示例：

```json
{
  "settings": [
    {
      "key": "join",
      "enabled": true
    },
    {
      "key": "ppt",
      "enabled": true
    }
  ]
}
```
