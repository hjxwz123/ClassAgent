# 学生端接口

统一前缀：`/api/v1/student`

所有接口均需学生登录态，返回格式遵循 `docs/api/00-api-conventions.md`。

## 学习台

### GET `/dashboard`

返回学生首页聚合数据。

响应 `data`：

- `courses`：已加入课程摘要列表
- `today_tasks`：今日学习任务
- `continue_learning`：最近学习课堂
- `stats`：学习时长、完成率、正确率、问答次数、错题数、连续打卡
- `recommendation`：AI 今日推荐
- `activities`：近期学习动态
- `notifications`：通知列表

## 我的课程

### GET `/courses`

返回学生加入的全部课程。一个学生可加入多门课程。

课程项包含：

- `teacher`：授课教师
- `student_count`：课程学生数
- `lesson_total`：已发布课堂数
- `studied_lessons`：已开始课堂数
- `completed_lessons`：已完成课堂数
- `progress_percent`：课程学习进度
- `qa_count`：课程问答次数
- `wrong_count`：错题数
- `last_lesson` / `last_progress`：最近学习记录

### GET `/courses/preview`

加入课程前预览课程码。

Query：

- `course_code`：课程码，5-12 位

响应 `data`：

- `course`
- `teacher`
- `student_count`
- `lesson_count`
- `already_joined`

### GET `/courses/{course_id}/home`

返回课程主页数据。

响应 `data`：

- `course`
- `teacher`
- `chapters`
- `lessons`：已发布课堂及学习进度
- `materials`：课程资料
- `quizzes`：已发布测验
- `recent_qa`
- `stats`
- `student_count`
- `quick_questions`

## 课堂笔记

### GET `/pages/{page_id}/note`

读取某一页的学生笔记。

### PUT `/pages/{page_id}/note`

保存某一页的学生笔记。

请求：

```json
{
  "content": "可靠传输要点"
}
```

限制：

- `content` 最多 8000 字

## 个人中心

### GET `/profile`

返回学生档案。

响应 `data`：

- `user`
- `student_profile`
- `notification_settings`
- `stats`
- `achievements`
- `activities`

### PATCH `/profile`

更新学生资料。

请求：

```json
{
  "nickname": "赵同学",
  "avatar_url": "",
  "bio": "喜欢网络课程",
  "school": "第一中学"
}
```

## 通知设置

### GET `/notifications`

返回学生通知列表。

### PUT `/notifications`

保存通知偏好。

请求：

```json
{
  "settings": [
    { "key": "lesson", "enabled": true },
    { "key": "quiz", "enabled": true },
    { "key": "qa", "enabled": true },
    { "key": "plan", "enabled": true, "time": "20:00" }
  ]
}
```

可用 `key`：

- `lesson`：新课堂发布
- `quiz`：测验发布提醒
- `qa`：AI 问答完成
- `plan`：学习计划提醒

## 测验提交结果

测验接口仍归属 `/api/v1/learning`。

### POST `/api/v1/learning/quizzes/{quiz_id}/submit`

提交后返回总分与题目级解析，学生端结果页直接使用。

响应 `data`：

- `score` / `total_score` / `accuracy`
- `ai_feedback`
- `attempt`：本次提交汇总
- `answers`：每题结果

`answers` 项：

- `question`
- `user_answer`
- `correct_answer`
- `is_correct`
- `score`
- `feedback`

未作答题目也会返回结果项，`feedback` 为 `本题未作答。`。
