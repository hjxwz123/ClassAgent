# 向量库与 RAG 接口说明

## 功能范围

- 向量库：Chroma 持久化存储
- 入库时机：资料解析完成后自动写入
- 检索范围：课程资料、章节、课堂页
- 问答链路：向量检索 → 课程上下文 → LLM 回答 → 来源引用

## 配置项

生产环境必须配置 `purpose=embedding` 的模型。

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

通义千问兼容模式可将 `endpoint` 配成兼容 OpenAI 的基础地址，系统会自动请求 `/embeddings`。

## 资料上传后的状态

`POST /api/v1/materials` 成功后返回：

- `parse_status=ready`：资料已解析
- `vector_status=ready`：知识块已写入 Chroma

若向量入库失败，`vector_status=failed`，资料需要重新处理。

## RAG 提问

- 方法：`POST`
- 路径：`/api/v1/qa/ask`

```json
{
  "course_id": 1,
  "chapter_id": 1,
  "lesson_page_id": 10,
  "question": "矩阵可以表示什么",
  "conversation_id": null
}
```

返回：

```json
{
  "conversation_id": 1,
  "record_id": 12,
  "question": "矩阵可以表示什么",
  "answer": "根据当前课程资料...",
  "is_out_of_scope": false,
  "sources": [
    {
      "material_id": 3,
      "material_title": "矩阵基础课件",
      "page_number": 1,
      "chapter_id": 1,
      "lesson_page_id": 10
    }
  ]
}
```

## 前端处理

- `sources` 用于展示资料名、章节、页码。
- `is_out_of_scope=true` 时展示回答正文即可，不再渲染来源。
- 课堂内提问传 `lesson_page_id`，系统优先检索当前页内容。

## 验证结果

- 已验证资料上传后 `KnowledgeChunk.embedding` 写入真实向量。
- 已验证 Chroma 查询可返回课程知识块。
- 已验证课程问答接口通过 RAG 返回答案和引用来源。
