# M3-M6 学习核心接口

## 一、课堂学习 M3

### 1. 课堂列表

- 方法：`GET`
- 路径：`/api/v1/lessons`
- 参数：`course_id`

学生只能看到已发布课堂，教师和管理员可以看到课程下全部课堂。

### 2. 课堂详情

- 方法：`GET`
- 路径：`/api/v1/lessons/{lesson_id}`

返回：

- `lesson`
- `pages`
  - `page_text`
  - `script_text`
  - `audio_url`
  - `subtitle_text`

### 3. 发布 / 取消发布课堂

- `POST /api/v1/lessons/{lesson_id}/publish`
- `POST /api/v1/lessons/{lesson_id}/unpublish`

### 4. 学习进度

- 查询：`GET /api/v1/lessons/{lesson_id}/progress`
- 上报：`POST /api/v1/lessons/{lesson_id}/progress`

请求体示例：

```json
{
  "current_page": 2,
  "added_seconds": 90,
  "completed": false
}
```

## 二、课程问答 M4

### 1. 发起提问

- 方法：`POST`
- 路径：`/api/v1/qa/ask`

请求体示例：

```json
{
  "course_id": 1,
  "lesson_page_id": 10,
  "question": "矩阵可以表示什么",
  "conversation_id": null
}
```

返回重点字段：

- `conversation_id`
- `record_id`
- `answer`
- `is_out_of_scope`
- `sources`

说明：

- 问答会先在 Chroma 中做课程资料向量检索，再调用问答模型生成回答。
- `lesson_page_id` 不为空时，检索范围限定到当前课堂页。
- `sources` 中包含资料、章节、页码信息，前端可直接作为引用来源展示。

### 2. 历史记录

- 方法：`GET`
- 路径：`/api/v1/qa/history`
- 可选参数：`course_id`、`keyword`

### 3. 收藏问答

- 方法：`POST`
- 路径：`/api/v1/qa/{record_id}/favorite`

```json
{
  "is_favorite": true
}
```

### 4. 问答评价

- 方法：`POST`
- 路径：`/api/v1/qa/{record_id}/feedback`

```json
{
  "feedback": "positive",
  "feedback_comment": "解释清晰"
}
```

`feedback` 可选：

- `positive`
- `negative`
- `neutral`

## 三、题目辅导 M5

### 1. 文本题目输入

- 方法：`POST`
- 路径：`/api/v1/tutoring/problems/text`

```json
{
  "course_id": 1,
  "text": "已知矩阵A，求其行列式"
}
```

### 2. 图片题目输入

- 方法：`POST`
- 路径：`/api/v1/tutoring/problems/image`
- 类型：`multipart/form-data`
- 字段：
  - `course_id`
  - `file`

说明：

- 当前未配置真实 OCR 时，会先生成占位识别文本，前端需引导学生手动修正。

### 3. 确认 OCR / 修正题干

- 方法：`POST`
- 路径：`/api/v1/tutoring/problems/{problem_id}/confirm`

```json
{
  "corrected_text": "已知矩阵A，求其行列式"
}
```

### 4. 获取分级辅导

- 方法：`GET`
- 路径：`/api/v1/tutoring/problems/{problem_id}/guidance`
- 参数：`level=1|2|3`

### 5. 辅导历史

- 方法：`GET`
- 路径：`/api/v1/tutoring/history`

## 四、学习支持 M6

### 1. 知识点讲解

- 方法：`GET`
- 路径：`/api/v1/learning/knowledge-points`
- 参数：
  - `course_id`
  - `chapter_id` 可选

返回中 `content_by_level` 已经内置：

- `beginner`
- `standard`
- `advanced`

### 2. 生成测验 / 练习

- 方法：`POST`
- 路径：`/api/v1/learning/quizzes/generate`

教师生成课程测验示例：

```json
{
  "course_id": 1,
  "chapter_id": 1,
  "title": "第一章测验",
  "quiz_type": "course",
  "question_count": 5
}
```

学生生成章节练习示例：

```json
{
  "course_id": 1,
  "chapter_id": 1,
  "title": "章节自练",
  "quiz_type": "practice",
  "question_count": 3
}
```

`quiz_type` 可选：

- `course`
- `practice`
- `wrong_book`

### 3. 发布测验

- 方法：`POST`
- 路径：`/api/v1/learning/quizzes/{quiz_id}/publish`

### 4. 测验列表

- 方法：`GET`
- 路径：`/api/v1/learning/quizzes`
- 参数：`course_id`

### 5. 测验详情

- 方法：`GET`
- 路径：`/api/v1/learning/quizzes/{quiz_id}`

说明：

- 学生查看时不会返回 `reference_answer`
- 教师查看时会保留完整答案

### 6. 提交测验

- 方法：`POST`
- 路径：`/api/v1/learning/quizzes/{quiz_id}/submit`

请求体示例：

```json
{
  "answers": [
    {
      "question_id": 1001,
      "answer": 1
    },
    {
      "question_id": 1002,
      "answer": "矩阵 线性 变换"
    }
  ]
}
```

### 7. 错题本

- 查询：`GET /api/v1/learning/wrong-questions?course_id=1`
- 生成重练：`POST /api/v1/learning/wrong-questions/practice?course_id=1`

### 8. 薄弱点分析

- 方法：`GET`
- 路径：`/api/v1/learning/weak-points`
- 参数：`course_id`

### 9. 学习计划

- 创建：`POST /api/v1/learning/plans`
- 查询：`GET /api/v1/learning/plans`
- 任务列表：`GET /api/v1/learning/plans/{plan_id}/tasks`
- 任务打卡：`POST /api/v1/learning/tasks/{task_id}/checkin`

创建计划示例：

```json
{
  "course_id": 1,
  "title": "期中复习计划",
  "goal": "一周内完成矩阵与行列式复习",
  "available_days": 7,
  "daily_minutes": 40
}
```

### 10. 学习记录

- 方法：`GET`
- 路径：`/api/v1/learning/records`
- 参数：`course_id`

返回字段：

- `progress_count`
- `qa_count`
- `problem_count`
- `attempt_count`

## 当前阶段验证结论

- 已通过课堂发布、课堂详情、学习进度、课程问答、收藏与评价、题目辅导、知识点讲解、课程测验、章节练习、提交判分、错题本、薄弱点、学习计划、学习记录的集成测试。
