# ClassAgent 教学开发小组接手指南

ClassAgent 是一个面向课程教学场景的 AI 学习助手平台，包含学生端、教师端和管理员端。本文档给教学开发小组使用，默认读者没有计算机背景，所以尽量按“照着做”的方式说明。

如果只记住一条规则：每次改代码前先 `git pull`，改完先测试，再 `git commit`，最后 `git push`。

## 1. 项目能做什么

学生端：

- 查看课程、课时、学习进度。
- 使用 AI 问答、拍照提问、题目辅导。
- 做测验、查看错题、生成学习计划。

教师端：

- 创建课程、章节、课时。
- 上传 PPT、PDF、DOCX、TXT 等课程资料。
- 使用 AI 生成讲稿、音频和测验。
- 查看学生学习情况和课程分析。

管理员端：

- 管理用户、课程、资料和系统设置。
- 配置 AI 模型、OSS、OCR、TTS、邮箱等服务。
- 查看错误日志、请求日志、备份和健康状态。

## 2. 项目结构

```text
app/                         后端代码
app/api/routes/              后端接口入口
app/services/                主要业务逻辑
app/db/models.py             数据表结构
app/core/config.py           后端配置

frontend/                    前端代码
frontend/src/views/          页面文件
frontend/src/views/ProductHomeView.vue 网站首页
frontend/src/views/AuthView.vue        登录注册
frontend/src/views/StudentView.vue     学生端
frontend/src/views/TeacherView.vue     教师端
frontend/src/views/AdminView.vue       管理端
frontend/src/styles/         样式文件
frontend/src/components/     可复用组件

tests/                       自动测试
storage/                     上传文件、生成文件、向量库和运行数据
.env                         本机配置，不能提交到 GitHub
.env.example                 配置模板，可以提交
README.md                    当前说明文档
```

不要提交这些内容：

- `.env`
- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `storage/uploads/`
- `storage/generated/`
- `storage/vectors/`
- `storage/logs/`
- 密码、Token、AccessKey、SecretKey

## 3. 需要安装的软件

建议安装：

- Chrome 浏览器
- VS Code
- Git
- Node.js 20 或更高版本
- Python 3.12
- MySQL 8
- Redis

如果不会安装，先使用服务器开发，不要先在自己电脑从零配环境。

## 4. 在服务器上启动项目

进入项目目录：

```bash
cd /www/wwwroot/class
```

查看当前代码状态：

```bash
git status
```

拉取 GitHub 最新代码：

```bash
git pull origin main
```

启动后端：

```bash
. .venv/bin/activate
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

另开一个终端，启动前端：

```bash
cd /www/wwwroot/class/frontend
npm run dev
```

访问网站：

```text
http://服务器IP:5173
```

检查后端是否正常：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

看到 `code:0` 或 `message:"ok"` 就说明后端正常。

默认管理员账号：

```text
邮箱：admin@classagent.com
密码：Admin123456
```

## 5. 在自己电脑从零启动

下载代码：

```bash
git clone git@github.com:hjxwz123/ClassAgent.git
cd ClassAgent
```

如果没有配置 GitHub SSH，可以用 HTTPS：

```bash
git clone https://github.com/hjxwz123/ClassAgent.git
cd ClassAgent
```

复制配置文件：

```bash
cp .env.example .env
```

安装后端依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

安装前端依赖：

```bash
cd frontend
npm install
```

启动后端：

```bash
cd ..
. .venv/bin/activate
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

另开一个终端，启动前端：

```bash
cd frontend
npm run dev
```

本地访问：

```text
http://127.0.0.1:5173
```

## 6. 每天开始开发前

进入项目：

```bash
cd /www/wwwroot/class
```

确认当前分支：

```bash
git branch --show-current
```

拉取最新代码：

```bash
git pull origin main
```

查看有没有未提交修改：

```bash
git status
```

如果看到很多自己不认识的修改，不要删除，先问组长。

## 7. 推荐协作方式

不要多人同时直接改 `main`。推荐每个任务建一个自己的分支。

创建分支：

```bash
git checkout -b 姓名/任务名
```

例子：

```bash
git checkout -b lisi/fix-student-menu
```

改完后推送分支：

```bash
git push -u origin lisi/fix-student-menu
```

然后在 GitHub 上创建 Pull Request，让组长检查后合并。

如果负责人要求直接推送到 `main`，才使用：

```bash
git checkout main
git pull origin main
git add .
git commit -m "fix: 修复学生端菜单"
git push origin main
```

## 8. 修改页面时找哪个文件

```text
网站首页                 frontend/src/views/ProductHomeView.vue
登录注册                 frontend/src/views/AuthView.vue
学生页面                 frontend/src/views/StudentView.vue
教师页面                 frontend/src/views/TeacherView.vue
管理员页面               frontend/src/views/AdminView.vue
管理员样式               frontend/src/styles/admin-scoped.css
教师样式                 frontend/src/styles/teacher-classagent.css
学生样式                 frontend/src/styles/student-classagent.css
```

判断方法：

- 按钮位置、颜色、间距、移动端显示问题：通常改 `frontend/src/views/` 或 `frontend/src/styles/`。
- 接口报错、AI 生成失败、数据不对：通常改 `app/services/` 或 `app/api/routes/`。
- 登录和权限问题：看 `app/core/deps.py`、`app/services/auth.py`。
- 数据表字段问题：看 `app/db/models.py`。

## 9. 修改后必须检查

前端检查：

```bash
cd /www/wwwroot/class/frontend
npm run build
```

后端检查：

```bash
cd /www/wwwroot/class
. .venv/bin/activate
pytest
```

只改某一块后端时，可以先跑相关测试：

```bash
pytest tests/test_student_console.py
pytest tests/test_teacher_console.py
pytest tests/test_m3_m6_learning_flow.py
pytest tests/test_m7_m8_admin_analytics.py
```

测试失败时不要推送，先看终端最后几行错误。

## 10. 提交和推送

查看改了哪些文件：

```bash
git status
```

查看具体改动：

```bash
git diff
```

添加单个文件：

```bash
git add 文件名
```

例子：

```bash
git add frontend/src/views/StudentView.vue
```

如果确认所有修改都要提交：

```bash
git add .
```

提交：

```bash
git commit -m "fix: 修复学生端菜单弹出位置"
```

推送：

```bash
git push
```

第一次推送新分支：

```bash
git push -u origin 分支名
```

## 11. 提交信息怎么写

格式：

```text
类型: 做了什么
```

常用类型：

- `fix:` 修复问题
- `feat:` 新功能
- `style:` 样式调整
- `docs:` 文档修改
- `test:` 测试修改
- `refactor:` 重构代码，功能不变

例子：

```bash
git commit -m "style: 去掉管理员侧边栏分隔线"
git commit -m "fix: 修复 AI 出题有效题目不足"
git commit -m "docs: 更新项目接手说明"
```

## 12. 常见 Git 问题

### 12.1 git pull 失败

先查看状态：

```bash
git status
```

如果修改都是你自己的，先提交：

```bash
git add .
git commit -m "wip: 保存当前修改"
git pull origin main
```

如果修改不是你的，不要乱删，先问组长。

### 12.2 push 被拒绝

通常是别人先推送了。先拉取：

```bash
git pull origin main
```

没有冲突后再推：

```bash
git push origin main
```

### 12.3 出现 conflict 或冲突

冲突表示两个人改了同一个地方。

处理步骤：

1. 打开冲突文件。
2. 搜索 `<<<<<<<`。
3. 和另一个人确认保留哪部分。
4. 删除 `<<<<<<<`、`=======`、`>>>>>>>`。
5. 保存文件。
6. 重新测试。
7. 提交。

## 13. 常见启动问题

### 13.1 端口被占用

查看后端端口：

```bash
ss -ltnp | grep 8000
```

查看前端端口：

```bash
ss -ltnp | grep 5173
```

### 13.2 npm install 很慢

重试：

```bash
cd frontend
npm install
```

不要把 `node_modules` 上传到 GitHub。

### 13.3 登录成功但接口报错

检查后端：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

开发环境前端默认把 `/api` 转发到：

```text
http://127.0.0.1:8000
```

代理配置在：

```text
frontend/vite.config.ts
```

### 13.4 AI 出题失败

先检查管理员页面里的模型配置。

项目要求 AI 出题，不能用本地假题兜底。相关代码：

```text
app/services/ai.py
app/services/learning.py
```

### 13.5 管理员错误日志

管理员页面：

```text
/admin/logs
```

相关代码：

```text
app/services/admin.py
app/api/routes/admin.py
```

## 14. 开发原则

- 每次只解决一个明确问题。
- 不要顺手大改无关页面。
- 不要删除别人刚改的文件。
- 不要提交 `.env`、密码、Token、AccessKey。
- 不确定就先 `git status`，再问组长。
- 推送前必须至少跑自己改动相关的检查。

## 15. 分工建议

可以按区域分工：

- 学生端：`StudentView.vue` 和学生端样式。
- 教师端：`TeacherView.vue` 和教师端样式。
- 管理端：`AdminView.vue` 和管理员样式。
- 后端接口：`app/api/routes/`、`app/services/`。
- 测试验收：`tests/`、手动打开页面检查。

每个人只改自己负责的区域，可以减少冲突。

## 16. 一次完整任务示例

任务：去掉管理员侧边栏底部白线。

```bash
cd /www/wwwroot/class
git checkout main
git pull origin main
git checkout -b zhangsan/remove-admin-sidebar-line
```

修改文件：

```text
frontend/src/styles/admin-scoped.css
```

检查：

```bash
cd frontend
npm run build
```

提交并推送：

```bash
cd /www/wwwroot/class
git status
git add frontend/src/styles/admin-scoped.css
git commit -m "style: 去掉管理员侧边栏底部分隔线"
git push -u origin zhangsan/remove-admin-sidebar-line
```

## 17. 推送前检查清单

推送前确认：

- 页面能打开。
- 登录正常。
- 自己改的功能能用。
- `npm run build` 通过。
- 后端改动跑过相关 `pytest`。
- `git status` 里没有不该提交的文件。
- 没有提交 `.env`、密码、密钥。
- 提交信息能说明这次改了什么。

## 18. 常用命令速查

```bash
# 进入项目
cd /www/wwwroot/class

# 查看当前分支
git branch --show-current

# 拉取最新代码
git pull origin main

# 查看改动
git status
git diff

# 启动后端
. .venv/bin/activate
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

# 启动前端
cd frontend
npm run dev

# 前端构建
cd frontend
npm run build

# 后端测试
cd /www/wwwroot/class
. .venv/bin/activate
pytest

# 提交
git add .
git commit -m "fix: 描述这次修改"
git push
```

## 19. 求助时发什么

请发：

1. 你正在做什么任务。
2. 你执行了哪条命令。
3. 终端最后 20 行报错。
4. `git status` 输出。
5. 浏览器截图或接口报错截图。

不要只说“坏了”或“打不开”，这样别人很难判断问题。

