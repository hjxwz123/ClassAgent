
# 🌀 课程学习助手智能体 - 交互设计与动效规范

> **文档版本**：V1.0.0
> **核心理念**：克制、流畅、符合物理直觉。
> **动效目标**：指示层级关系、提供触觉反馈、掩盖 API 加载时间、赋予 AI 生命周期感。

---

## 一、 动效物理法则 (Motion Physics)

为确保全平台动效的统一性，系统定义了三种标准时间（Duration）和四种缓动曲线（Easing）。开发中必须使用全局 CSS 变量，严禁在业务代码中硬编码时间。

### 1.1 持续时间 (Durations)
| Token | 时间 | 适用场景 | 心理暗示 |
|-------|------|----------|---------|
| `--duration-fast` | **150ms** | 颜色切换、透明度变化、Hover 状态 | “即时、轻快” |
| `--duration-base` | **250ms** | 弹窗淡入、位置移动、卡片展开 | “标准、流畅” |
| `--duration-slow` | **400ms** | 侧边抽屉滑入、大面积页面路由切换 | “结构变化、稳重” |

### 1.2 缓动曲线 (Easings)
| Token | 贝塞尔值 | 适用场景 | 物理隐喻 |
|-------|----------|----------|---------|
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | **元素入场** (弹窗出现、下拉菜单) | 减速入场，吸引视觉焦点 |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | **元素退场** (关闭弹窗、Toast消失) | 加速离开，不拖泥带水 |
| `--ease-in-out`| `cubic-bezier(0.65, 0, 0.35, 1)` | **状态变化** (开关切换、进度条) | 平滑过渡，无始无终 |
| `--ease-spring`| `cubic-bezier(0.34, 1.56, 0.64, 1)` | **触感反馈** (按钮点击缩放、打卡) | 弹性回弹，真实物理按压感 |

---

## 二、 数据加载与接口延迟反馈 (Data Loading)

**核心原则：任何预期超过 300ms 的 API 请求，必须提供明确的视觉反馈；禁止出现页面“假死”或内容瞬间空缺的突变。**

### 2.1 骨架屏 (Skeleton Screen) —— 【页面/大组件首次加载】
*   **适用场景**：首次进入课程列表、进入课程主页、管理员打开大盘仪表盘等获取大量结构化数据的场景。
*   **交互逻辑**：
    *   接口发起瞬间，使用灰色色块（结构与真实内容一致）占位，防止页面高度塌陷。
    *   骨架屏必须带有**流光扫描动画**（从左至右匀速扫过），向用户暗示系统正在运转。
    *   **平滑替换**：数据返回时，真实数据以 `150ms` 淡入（Fade-in）替换骨架屏，禁止闪烁或剧烈跳动。

### 2.2 局部加载圈 (Spinner) —— 【容器内局部刷新】
*   **适用场景**：分页加载下一页、切换 Tab 拉取分类数据、表格内数据刷新。
*   **交互逻辑**：
    *   保留当前页面的大框架，仅在需要更新的区域中心显示一个主色旋转 Spinner。
    *   **防抖机制 (Debounce)**：若接口在极短时间（<200ms）内返回，不展示 Spinner 以防画面闪烁；超过 200ms 强制展示。

### 2.3 按钮级加载 (Button Loading) —— 【表单提交/单体操作】
*   **适用场景**：点击“保存配置”、“创建课程”、“提交测验”等。
*   **交互逻辑**：
    *   点击后立即进入 Loading 态，**禁止按钮尺寸或位置发生跳动**。
    *   左侧平滑推挤出空间显示 Spinner（旋转动画 0.8s/圈），按钮文字透明度降至 `0.9`。
    *   光标变为 `cursor: wait`，拦截底层二次点击（防重复提交）。

### 2.4 全屏遮罩加载 (Full-screen Blocking) —— 【高危/强阻断操作】
*   **适用场景**：极少使用。仅限管理员执行“数据恢复”、“全量备份”等期间**绝对禁止用户进行其他操作**的场景。
*   **交互逻辑**：弹出深色毛玻璃遮罩（`z-index: 10000`），居中显示大型 Spinner 并伴随**明确文字提示**（如：“正在恢复数据，请勿关闭页面...”）。

---

## 三、 基础组件交互逻辑

### 3.1 按钮 (Button)
*   **Hover (悬停)**: 背景色加深一级，时长 `150ms linear`。
*   **Active/Mousedown (按压)**: 触发微缩放触感 `transform: scale(0.96)`，使用 `--ease-spring`，松开瞬间回弹。
*   **Disabled (禁用)**: `opacity: 0.5`，光标变为 `cursor: not-allowed`，屏蔽一切 Hover/Active 动画。

### 3.2 输入框 (Input / Textarea)
*   **Hover**: 边框颜色平滑过渡至加深色。
*   **Focus**: 边框变为主色，四周弥散出 3px 的主色半透明光晕 (`--shadow-focus`)，过渡时长 `150ms ease-out`。
*   **Error (校验错误)**:
    *   失焦触发校验。若错误，边框瞬间变红，呈现红色光晕。
    *   **错误抖动 (Shake)**：伴随强烈的左右抖动，`translateX` 往复移动 `[-4px, 4px, -2px, 2px, 0]`，持续 `400ms`，强制吸引注意。

### 3.3 卡片 (Card)
*   **可点击卡片 (如学生端课程卡片)**: 
    *   Hover 时：整卡 `transform: translateY(-4px)`，阴影从 `--shadow-sm` 扩散至 `--shadow-md` 或 `lg`。过渡时长 `250ms ease-out`。
    *   内部封面图或大图标微缩放 `scale(1.05)`，增加纵深感。

---

## 四、 弹窗与浮层交互 (Overlays)

弹窗的出现必须打断上下文，让用户聚焦于当前操作。

### 4.1 居中模态框 (Modal)
*   **背景遮罩**: `opacity: 0 -> 1`，模糊度 `blur(0) -> blur(4px)`，时长 `250ms`。
*   **主体入场**: `opacity: 0 -> 1`，伴随轻微缩放 `scale(0.95) -> 1` 和上浮 `translateY(15px) -> 0`。缓动曲线 `--ease-out`。
*   **主体退场**: 缩放回 `scale(0.95)`，透明度归 0。缓动曲线 `--ease-in`。
*   **焦点陷阱 (Focus Trap)**: 弹出时强制锁定底层页面滚动（`body { overflow: hidden }`），键盘 `Tab` 键焦点自动在弹窗内循环，按 `ESC` 键触发关闭。

### 4.2 侧滑抽屉 (Drawer)
*   **适用场景**：查看学生详情、课程详情等信息密集的临时视图。
*   **入场**: 背景遮罩淡入。抽屉从屏幕右侧边缘滑入，`transform: translateX(100%) -> translateX(0)`。时长 `400ms --ease-out`（距离较长，时间略慢于 Modal）。
*   **退场**: 滑回右侧 `translateX(100%)`。

### 4.3 下拉菜单与气泡 (Dropdown / Popover)
*   **展开**: 以触发点为 Transform-origin（如顶部导航栏下拉，原点在顶部）。`opacity: 0 -> 1`，`transform: scaleY(0.9) translateY(-4px) -> scaleY(1) translateY(0)`。时长 `150ms`。
*   **收起**: 100ms 快速淡出，不拖沓。

---

## 五、 提示与警告交互 (Feedback)

### 5.1 吐司通知 (Toast)
*   **入场**: 从页面右上角滑入，`transform: translateX(100%) -> translateX(0)`。
*   **停留与进度**: 默认停留 4000ms。Toast 底部附带极细的进度条（100% 缩减到 0），给用户时间预期。
*   **悬停暂停**: 鼠标 Hover 到 Toast 上时，倒计时进度条暂停，方便阅读；移开后继续。
*   **退场**: 向上滑动淡出，为后方的 Toast 让出空间。

### 5.2 全局严重警告 (Critical Alert)
*   **适用场景**：系统级断网、数据恢复高危操作警告。
*   **动画表现**：背景出现红色微光闪烁（Pulse 动画），提示图标（`alert-triangle`）保持 2 秒一次的轻微跳动（Bounce）。

---

## 六、 AI 专属交互动效 (The "Agentic" Feel)

AI 是本系统的核心，AI 相关的交互必须体现出“思考、生成、生命力”。

### 6.1 接口加载态：AI 正在思考 (Thinking)
*   针对耗时较长的 LLM 请求，**禁止使用普通 Spinner**。
*   在对话流中立即渲染一个带有“AI 渐变边框”的占位气泡。
*   **视觉表现**：
    *   文字：“AI 正在思考...” 伴随三个点依次出现和消失（Typing Dots 动画，每个点错开 0.2s）。
    *   **呼吸发光**：气泡边框执行透明度呼吸动画 `opacity: 0.4 -> 1 -> 0.4`，周期 `2s ease-in-out`。

### 6.2 AI 流式输出 (Streaming / Typewriter)
*   **出现方式**: AI 文字像打字机一样逐字/逐句流式渲染。
*   **视觉光标**: 在正在输出的文字末尾，跟随一个主色的闪烁光标块 `▍`（周期 0.8s）。
*   **自动滚动**: 输出过程中，页面滚动条自动平滑向下滚动，始终保持最新文字在视口底部上方 20px 处；输出结束光标消失。

### 6.3 OCR 识别扫描 (题目上传)
*   用户上传图片后，图片上方覆盖半透明深色遮罩。
*   一条充满科技感的青紫色渐变扫描线（Scanner Line）在图片上从上到下往复平移，直到 OCR 接口返回结果。

### 6.4 渐进式辅导展开 (Progressive Disclosure)
*   **场景**: 题目辅导的三级提示（思路 -> 步骤 -> 解析）。
*   **展开动画**: 点击解锁下一级时，面板通过计算 `height` 进行流畅的手风琴展开，持续 `300ms ease-out`。
*   内容元素（文字）在面板展开后，以 `150ms` 延迟进行淡入（Fade-in），避免内容和容器同时拉扯导致视觉撕裂感。

---

## 七、 场景级复杂交互逻辑

### 7.1 沉浸式课时学习 (M3 - 自动隐藏 UI)
*   **UI 隐身防干扰**: 鼠标在 PPT 播放区停留超过 3 秒且无移动（视频/语音播放中）时：
    *   顶栏向上滑出 (`translateY(-100%)`)。
    *   底部播放控制条向下滑出 (`translateY(150%)`)。
*   **唤醒**: 鼠标只要产生 `mousemove`，控制栏立刻（0ms 延迟）淡入恢复显示。
*   **字幕卡拉OK同步**: 当前正在发音的词组，文字颜色无延迟渐变为纯白色并加粗；已读文字变灰；与 TTS 时间戳严格对齐。

### 7.2 错题重练与打卡消除 (Delightful Interaction)
*   **任务完成瞬间**: 用户勾选待办任务或答对错题时。
*   **消除反馈**:
    *   勾选框执行强烈回弹放大 `scale(1.3) -> scale(1)`。
    *   文字产生中划线，颜色渐变为浅灰。
    *   若完成今日所有打卡，屏幕中央触发 CSS 纸屑/撒花动画（Confetti），时长 `1.5s`，模拟重力下落，提供情绪价值。

### 7.3 后台仪表盘数据刷新 (M8)
*   **倒计时刷新**: 页面右上角有 30 秒倒计时。倒计时归零时：
    *   数字更新采用翻页时钟效果（Roll-up）：旧数字向上滑出，新数字从下方滑入，持续 `300ms`。
    *   图表禁止白屏重载，调用 ECharts 的 `setOption` 执行平滑的增量动画（从右侧推入新数据）。

---

## 八、 前端开发实现参考 (CSS Snippets)

请前端研发在全局 `global.css` 中植入以下动画核心类，直接通过添加 Class Name 实现交互：

```css
/* =========================================
   1. 变量与基础触感
   ========================================= */
:root {
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 400ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* 按钮按压弹性反馈 */
.btn-interactive { transition: transform 150ms var(--ease-out), background-color 150ms linear; }
.btn-interactive:active:not(:disabled) {
  transform: scale(0.96);
  transition: transform 100ms var(--ease-spring);
}

/* =========================================
   2. 加载与骨架屏 (Data Loading)
   ========================================= */
/* 骨架屏扫描流光 */
@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton-box {
  background: linear-gradient(90deg, var(--bg-muted) 25%, var(--border-default) 50%, var(--bg-muted) 75%);
  background-size: 400% 100%;
  animation: skeleton-shimmer 1.5s infinite linear;
  border-radius: var(--radius-sm);
  color: transparent !important;
  user-select: none;
  pointer-events: none;
}

/* 局部旋转 Spinner */
@keyframes spin {
  to { transform: rotate(360deg); }
}
.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--primary-100);
  border-top-color: var(--primary-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* =========================================
   3. AI 专属动效
   ========================================= */
/* AI 思考边框呼吸灯 */
@keyframes ai-pulse {
  0%, 100% { opacity: 0.5; box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
  50% { opacity: 1; box-shadow: 0 0 15px 2px rgba(139, 92, 246, 0.4); }
}
.ai-thinking-border { animation: ai-pulse 2s ease-in-out infinite; }

/* 思考中点点点 (Typing Dots) */
@keyframes typing-dots {
  0%, 80%, 100% { opacity: 0.3; transform: translateY(0) scale(0.8); }
  40% { opacity: 1; transform: translateY(-3px) scale(1); }
}
.dot-1 { animation: typing-dots 1.4s infinite ease-in-out; }
.dot-2 { animation: typing-dots 1.4s infinite ease-in-out 0.2s; }
.dot-3 { animation: typing-dots 1.4s infinite ease-in-out 0.4s; }

/* 流式输出光标闪烁 */
@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.ai-cursor {
  display: inline-block; width: 6px; height: 14px;
  background-color: var(--primary-600);
  animation: blink-cursor 0.8s step-end infinite;
  vertical-align: middle; margin-left: 4px;
}

/* =========================================
   4. 弹窗与警告反馈
   ========================================= */
/* 弹窗入场 */
@keyframes modal-enter {
  0% { opacity: 0; transform: scale(0.95) translateY(15px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}
.modal-animate-in { animation: modal-enter var(--duration-base) var(--ease-out) forwards; }

/* 校验错误左右抖动 */
@keyframes shake-error {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}
.input-error-shake { animation: shake-error 400ms ease-in-out; border-color: var(--danger-500) !important; }
```

---

## 九、 交互审查清单 (QA Checklist)

研发交付与产品验收前，请逐项核对以下体验细节：

1. **接口加载反馈 (API Delay)**
   - [ ] 断网/弱网测试：开启浏览器 Slow 3G，列表页/卡片在数据返回前，是否展示了**骨架屏 (Skeleton)**？
   - [ ] 按钮防重：点击提交类按钮，是否立刻出现 Loading 态，且无法连击？
   - [ ] 防抖处理：若接口极快（<50ms）返回，是否消除了闪烁现象（没有一闪而过的 Spinner）？

2. **微动效与触感 (Micro-interactions)**
   - [ ] 所有的主要按钮被点击时，是否有按压反馈（scale 缩放）？
   - [ ] Hover 引起的颜色或阴影变化，是否都加了 150ms 的 `transition`，而不是生硬突变？

3. **弹窗与遮罩 (Overlays)**
   - [ ] Modal 弹出时，是否带有 250ms 的上浮淡入动画？
   - [ ] 弹出层出现后，底层的页面滚动是否被禁用了（`overflow: hidden`）？焦点是否被锁定在弹窗内？

4. **AI 交互 (AI Specific)**
   - [ ] AI 正在请求时，是否显示了特有的“思考中...”及渐变呼吸动画，而不是普通的菊花图？
   - [ ] AI 流式生成文字时，光标是否闪烁？长文本生成时，滚动条是否自动跟随到底部？