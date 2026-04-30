# M2 课程资料管理接口

## 支持类型与限制

- 支持文件：`.pptx`、`.pdf`、`.docx`、`.txt`
- 默认大小上限：`50MB`
- 分类枚举：
  - `courseware`
  - `handout`
  - `exercise`
  - `reference`

## 1. 上传资料

- 方法：`POST`
- 路径：`/api/v1/materials`
- 鉴权：教师 / 管理员
- 请求类型：`multipart/form-data`

### 表单字段

- `course_id`：课程 ID
- `title`：资料标题
- `category`：资料分类
- `chapter_id`：可选，章节 ID
- `file`：上传文件

### 返回重点字段

- `parse_status`
- `vector_status`
- `preview_url`

上传成功后会自动触发：

1. 文档解析
2. 课堂页面生成
3. 每页脚本生成
4. 音频生成
5. 向量化入库

默认开发环境下采用同步执行，前端上传后可立即刷新详情查看结果。

## 2. 资料列表

- 方法：`GET`
- 路径：`/api/v1/materials`
- 鉴权：是

### 查询参数

- `course_id`：可选
- `chapter_id`：可选
- `keyword`：可选，按标题和解析文本检索
- `category`：可选

### 权限规则

- 教师：只能看自己课程下的资料
- 学生：只能看已加入课程下的资料
- 管理员：可看全部资料

## 3. 资料详情

- 方法：`GET`
- 路径：`/api/v1/materials/{material_id}`

### 返回结构

- `material`：资料基础信息
- `lesson_id`：自动生成的课堂 ID
- `lesson_status`：课堂状态
- `lesson_page_count`：总页数
- `pages`：每页原文、脚本、音频地址、字幕

## 4. 修改资料

- 方法：`PATCH`
- 路径：`/api/v1/materials/{material_id}`
- 鉴权：课程教师 / 管理员

### 请求体示例

```json
{
  "title": "矩阵基础课件-修订版",
  "category": "handout",
  "chapter_id": 1
}
```

说明：

- `chapter_id` 传 `null` 表示取消章节绑定
- 不传 `chapter_id` 表示保持原值不变

## 5. 删除资料

- 方法：`DELETE`
- 路径：`/api/v1/materials/{material_id}`
- 鉴权：课程教师 / 管理员

说明：当前为软删除。

## 6. 重新处理资料

- 方法：`POST`
- 路径：`/api/v1/materials/{material_id}/reprocess`

用途：

- 重新解析文档
- 重建课堂页
- 重建脚本和音频
- 重建知识块索引

## 7. 手动修改页面脚本

- 方法：`PATCH`
- 路径：`/api/v1/materials/pages/{page_id}/script`

### 请求体

```json
{
  "script_text": "这是教师手动修订后的讲解脚本。"
}
```

说明：保存脚本后会自动重生成音频与字幕。

## 8. 重新生成页面脚本

- 方法：`POST`
- 路径：`/api/v1/materials/pages/{page_id}/script/regenerate`

说明：基于当前页原文重新生成脚本，并同步重建音频。

## 前端接入建议

- 上传成功后直接调用资料详情接口，展示解析结果和页面脚本。
- 资料列表页可使用 `keyword + chapter_id + category` 做组合筛选。
- 页面详情里 `audio_url` 可直接给音频播放器使用。
- `preview_url` 可直接作为 PDF/PPT 原文件预览入口。

## 当前阶段验证结论

- 已通过 `pptx/pdf/docx/txt` 四类解析测试。
- 已通过资料上传、自动处理、详情查询、页面脚本编辑、页面脚本重生成、资料检索、重新处理、软删除的集成测试。
