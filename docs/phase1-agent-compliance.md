# AGENT.md 一期验收对照

## 结论

一期 M1-M8 已按 AGENT.md 完成前后端实现，并完成自动化验证。

## 模块对照

| 模块 | 状态 | 覆盖点 |
| --- | --- | --- |
| M1 用户与课程 | 完成 | 注册、登录、资料、改密、邮箱找回、课程、章节、成员、退出 |
| M2 课程资料 | 完成 | PPT/PDF/Word/TXT、章节绑定、解析、脚本、TTS、预览、Chroma 入库 |
| M3 课堂学习 | 完成 | 课堂列表、逐页学习、音频、字幕、控制、进度、时长、课堂提问 |
| M4 课程问答 | 完成 | RAG、引用来源、多轮、超范围、历史、搜索、收藏、评价 |
| M5 题目辅导 | 完成 | 文本、图片 OCR、修正、知识点、三级辅导、易错点、相似题、历史 |
| M6 学习支持 | 完成 | 知识点难度、测验、练习、判分、错题、重练、薄弱点、计划、打卡、记录 |
| M7 教学分析 | 完成 | 高频问题、薄弱点、活跃度、成绩分布、完成率、AI 建议、时间筛选 |
| M8 系统管理 | 完成 | 用户、课程、资料、模型、Embedding、服务、参数、监控、日志、备份恢复 |

## 关键生产能力

- 真实向量库：Chroma 持久化目录 `storage/vectors/chroma`
- RAG：资料解析后写入 Chroma，问答先向量检索再调用模型
- Embedding：生产环境必须配置 `purpose=embedding`
- Celery：生产环境必须 `CELERY_TASK_ALWAYS_EAGER=false`
- Redis：缓存、Broker、结果后端均已配置入口
- MySQL：生产环境禁止 SQLite
- 邮件：生产环境通过 SMTP 发送找回密码验证码
- OSS：管理员可启用 OSS，未配置时自动本地存储

## 验证命令

```bash
. .venv/bin/activate
pytest -q
cd frontend
npm run build
```

当前验证结果：

- 后端：`9 passed`
- 前端：构建通过
