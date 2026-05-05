教师首页和学生首页
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工作台主题重构 - ClassAgent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/@phosphor-icons/web"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        chalk: ['"Hannotate SC"', '"HanziPen SC"', '"Wawati SC"', '"STXingkai"', '"华文行楷"', '"PingFang SC"', 'sans-serif'],
                        serif: ['"Songti SC"', '"STSong"', '"SimSun"', '"宋体"', 'serif'],
                        sans: ['-apple-system', 'BlinkMacSystemFont', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
                        mono: ['"SFMono-Regular"', 'Consolas', '"Liberation Mono"', 'Menlo', 'monospace'],
                    },
                    colors: {
                        slate: '#121614',     // 黑板深墨绿
                        chalk: '#F4F4F0',     // 粉笔白
                        dust: '#8C948F',      // 擦拭粉尘灰
                        'ai-glow': '#00B8D4', // 学生端主色调 (调整为适合浅色底的青蓝)
                        'teacher': '#D94925', // 教师端主色调 (朱砂红/批改红)

                        // 逼真的纸张色彩系统
                        paper: {
                            bg: '#F9F8F6',      // 桌面大背景
                            card: '#FFFFFF',    // 卡片背景
                            border: '#E6E4DD',  // 柔和分割线
                            ink: '#2C2B29',     // 正文墨水色
                            sub: '#666560',     // 次要信息
                        }
                    },
                    boxShadow: {
                        'paper': '0 2px 8px rgba(0,0,0,0.02), 0 1px 2px rgba(0,0,0,0.02)',
                        'paper-hover': '0 8px 24px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.02)'
                    }
                }
            }
        }
    </script>
    <style>
        body { margin: 0; background-color: #F9F8F6; color: #2C2B29; font-family: -apple-system, sans-serif; overflow: hidden; }
        
        /* 桌面纸张微噪点 */
        .paper-texture {
            position: fixed; inset: 0; pointer-events: none; z-index: 0;
            background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noise)" opacity="0.015"/%3E%3C/svg%3E');
        }

        /* 欢迎横幅的黑板质感 */
        .banner-texture {
            position: absolute; inset: 0; pointer-events: none; z-index: 1;
            background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)" opacity="0.05"/%3E%3C/svg%3E');
        }

        /* 自定义滚动条 */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #D1CBB5; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="paper-texture"></div>

    <!-- ========================================== -->
    <!-- 视图 1：教师端工作台 (对应图一布局)          -->
    <!-- ========================================== -->
    <div id="teacher-view" class="flex h-screen relative z-10 w-full transition-opacity duration-300">
        
        <!-- 左侧最窄的工具栏 (深色黑板底) -->
        <aside class="w-16 bg-slate flex flex-col items-center py-4 border-r border-white/10 z-20 shadow-xl relative">
            <div class="banner-texture"></div>
            <!-- Logo 图标 -->
            <div class="w-10 h-10 bg-white/10 rounded flex items-center justify-center text-chalk font-serif font-bold text-xl mb-6 relative z-10">C</div>
            
            <nav class="flex flex-col gap-2 w-full px-2 relative z-10">
                <button class="w-full h-12 flex items-center justify-center text-chalk bg-white/10 rounded border-l-2 border-teacher transition-colors">
                    <i class="ph-duotone ph-squares-four text-xl text-teacher"></i>
                </button>
                <button class="w-full h-12 flex items-center justify-center text-dust hover:text-chalk transition-colors">
                    <i class="ph-duotone ph-book-open text-xl"></i>
                </button>
                <button class="w-full h-12 flex items-center justify-center text-dust hover:text-chalk transition-colors">
                    <i class="ph-duotone ph-target text-xl"></i>
                </button>
                <button class="w-full h-12 flex items-center justify-center text-dust hover:text-chalk transition-colors">
                    <i class="ph-duotone ph-house text-xl"></i>
                </button>
                <button class="w-full h-12 flex items-center justify-center text-dust hover:text-chalk transition-colors">
                    <i class="ph-duotone ph-folder text-xl"></i>
                </button>
            </nav>
            <div class="mt-auto flex flex-col gap-2 w-full px-2 relative z-10">
                <button class="w-full h-12 flex items-center justify-center text-dust hover:text-chalk transition-colors">
                    <i class="ph-duotone ph-user text-xl"></i>
                </button>
            </div>
        </aside>

        <!-- 主内容区 -->
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <!-- 顶部 Header -->
            <header class="h-14 bg-paper-bg border-b border-paper-border flex items-center justify-between px-6 z-10">
                <div class="flex items-center gap-4">
                    <div class="font-sans font-bold text-paper-ink text-sm flex items-center gap-2">
                        <i class="ph-duotone ph-chalkboard-teacher text-teacher text-lg"></i>
                        课程学习助手 <span class="text-paper-border mx-2">|</span> 
                        <span class="text-paper-sub font-normal">编译原理 <i class="ph-bold ph-caret-down text-xs ml-1"></i></span>
                    </div>
                </div>
                <div class="flex items-center gap-6 text-paper-sub text-sm">
                    <a href="#" class="flex items-center gap-1 hover:text-paper-ink"><i class="ph-duotone ph-bell-ringing text-lg"></i> 通知</a>
                    <a href="#" class="flex items-center gap-1 hover:text-paper-ink"><i class="ph-duotone ph-question text-lg"></i> 帮助</a>
                    <div class="flex items-center gap-2 pl-4 border-l border-paper-border cursor-pointer">
                        <div class="w-7 h-7 rounded-full bg-slate text-chalk flex items-center justify-center font-bold text-xs">T</div>
                        <span class="text-paper-ink font-bold">teacher <i class="ph-bold ph-caret-down text-xs ml-1"></i></span>
                    </div>
                </div>
            </header>

            <!-- 面包屑 -->
            <div class="px-8 py-4 flex items-center justify-between">
                <div class="flex items-center gap-2 text-sm text-paper-sub font-sans">
                    <i class="ph-duotone ph-house"></i> 工作台 
                    <i class="ph-bold ph-caret-right text-xs"></i> 
                    <span class="text-paper-ink font-bold">工作台首页</span>
                </div>
                <button class="border border-paper-border text-paper-ink bg-paper-card px-4 py-1.5 rounded flex items-center gap-2 text-sm shadow-paper hover:border-teacher transition-colors">
                    <i class="ph-duotone ph-monitor-play"></i> 最近课程
                </button>
            </div>

            <!-- 可滚动内容区 -->
            <div class="flex-1 overflow-y-auto px-8 pb-10">
                <div class="max-w-7xl mx-auto space-y-6">
                    
                    <!-- 欢迎横幅 (替换紫色渐变为黑板质感) -->
                    <div class="bg-slate rounded-lg overflow-hidden relative p-8 shadow-paper">
                        <div class="banner-texture"></div>
                        <div class="relative z-10 flex justify-between items-center">
                            <div class="flex items-center gap-4 text-chalk">
                                <i class="ph-duotone ph-sparkle text-4xl text-teacher"></i>
                                <div>
                                    <h1 class="text-2xl font-serif font-bold tracking-wide">晚上好，teacher老师</h1>
                                    <p class="text-sm font-sans text-dust mt-1 font-mono">2026年5月4日 星期一 · 3门课程</p>
                                </div>
                            </div>
                            <button class="border border-white/20 text-chalk hover:bg-white/10 px-5 py-2 rounded flex items-center gap-2 text-sm transition-colors font-sans">
                                <i class="ph-duotone ph-monitor-play"></i> 最近课程
                            </button>
                        </div>
                    </div>

                    <!-- 4个统计卡片 (纸张白底) -->
                    <div class="grid grid-cols-4 gap-6">
                        <div class="bg-paper-card border border-paper-border rounded-lg p-5 shadow-paper flex flex-col justify-between h-32">
                            <div class="flex items-center gap-2 text-paper-sub text-sm"><i class="ph-duotone ph-book-open text-teacher text-lg"></i> 我的课程</div>
                            <div>
                                <div class="text-3xl font-mono font-bold text-paper-ink">2<span class="text-xl text-paper-sub">/3</span></div>
                                <div class="text-xs text-paper-sub mt-1">本学期</div>
                            </div>
                        </div>
                        <div class="bg-paper-card border border-paper-border rounded-lg p-5 shadow-paper flex flex-col justify-between h-32">
                            <div class="flex items-center gap-2 text-paper-sub text-sm"><i class="ph-duotone ph-users text-teal-600 text-lg"></i> 学生总数</div>
                            <div>
                                <div class="text-3xl font-mono font-bold text-paper-ink">2</div>
                                <div class="text-xs text-paper-sub mt-1">全部课程</div>
                            </div>
                        </div>
                        <div class="bg-paper-card border border-paper-border rounded-lg p-5 shadow-paper flex flex-col justify-between h-32">
                            <div class="flex items-center gap-2 text-paper-sub text-sm"><i class="ph-duotone ph-chat-teardrop-text text-amber-600 text-lg"></i> 本周提问</div>
                            <div>
                                <div class="text-3xl font-mono font-bold text-paper-ink">23</div>
                                <div class="text-xs text-paper-sub mt-1">AI 问答</div>
                            </div>
                        </div>
                        <div class="bg-paper-card border border-paper-border rounded-lg p-5 shadow-paper flex flex-col justify-between h-32">
                            <div class="flex items-center gap-2 text-paper-sub text-sm"><i class="ph-duotone ph-clock text-indigo-500 text-lg"></i> 待处理</div>
                            <div>
                                <div class="text-3xl font-mono font-bold text-paper-ink">0</div>
                                <div class="text-xs text-paper-sub mt-1">脚本页</div>
                            </div>
                        </div>
                    </div>

                    <!-- 底部双栏结构 -->
                    <div class="grid grid-cols-3 gap-6">
                        <!-- 我的课程列表 -->
                        <div class="col-span-2 bg-paper-card border border-paper-border rounded-lg p-6 shadow-paper">
                            <div class="flex justify-between items-center mb-6">
                                <h3 class="font-serif font-bold text-paper-ink text-lg flex items-center gap-2"><i class="ph-duotone ph-book-open"></i> 我的课程</h3>
                                <a href="#" class="text-teacher text-sm hover:underline">查看全部</a>
                            </div>
                            
                            <div class="space-y-6">
                                <!-- 列表项 1 -->
                                <div class="flex items-center gap-4">
                                    <div class="w-12 h-12 rounded bg-slate text-chalk flex items-center justify-center shadow-md relative overflow-hidden">
                                        <div class="absolute inset-0 bg-teacher opacity-20"></div>
                                        <i class="ph-duotone ph-book-open text-xl relative z-10"></i>
                                    </div>
                                    <div class="flex-1">
                                        <div class="flex justify-between mb-1">
                                            <span class="font-serif font-bold text-paper-ink">编译原理</span>
                                            <a href="#" class="text-sm text-paper-sub hover:text-teacher">进入课程</a>
                                        </div>
                                        <div class="text-xs text-paper-sub font-sans mb-2">2026春 · 1人</div>
                                        <!-- 极细进度条 -->
                                        <div class="w-full h-1 bg-paper-border rounded-full overflow-hidden">
                                            <div class="h-full bg-teacher w-[80%] rounded-full"></div>
                                        </div>
                                    </div>
                                </div>
                                <!-- 列表项 2 -->
                                <div class="flex items-center gap-4">
                                    <div class="w-12 h-12 rounded bg-slate text-chalk flex items-center justify-center shadow-md relative overflow-hidden">
                                        <div class="absolute inset-0 bg-blue-500 opacity-20"></div>
                                        <i class="ph-duotone ph-book-open text-xl relative z-10"></i>
                                    </div>
                                    <div class="flex-1">
                                        <div class="flex justify-between mb-1">
                                            <span class="font-serif font-bold text-paper-ink">测试2</span>
                                            <a href="#" class="text-sm text-paper-sub hover:text-teacher">进入课程</a>
                                        </div>
                                        <div class="text-xs text-paper-sub font-sans mb-2">2026春 · 1人</div>
                                        <div class="w-full h-1 bg-paper-border rounded-full overflow-hidden">
                                            <div class="h-full bg-blue-500 w-[60%] rounded-full"></div>
                                        </div>
                                    </div>
                                </div>
                                <!-- 列表项 3 -->
                                <div class="flex items-center gap-4 border-b border-paper-border pb-6">
                                    <div class="w-12 h-12 rounded bg-slate text-chalk flex items-center justify-center shadow-md relative overflow-hidden">
                                        <div class="absolute inset-0 bg-teal-500 opacity-20"></div>
                                        <i class="ph-duotone ph-book-open text-xl relative z-10"></i>
                                    </div>
                                    <div class="flex-1">
                                        <div class="flex justify-between mb-1">
                                            <span class="font-serif font-bold text-paper-ink">测试1</span>
                                            <a href="#" class="text-sm text-paper-sub hover:text-teacher">进入课程</a>
                                        </div>
                                        <div class="text-xs text-paper-sub font-sans mb-2">2026春 · 0人</div>
                                        <div class="w-full h-1 bg-paper-border rounded-full overflow-hidden"></div>
                                    </div>
                                </div>
                            </div>
                            
                            <button class="w-full mt-4 py-3 border border-dashed border-paper-border text-paper-sub hover:text-teacher hover:border-teacher transition-colors rounded flex items-center justify-center gap-2 text-sm font-sans">
                                <i class="ph-bold ph-plus"></i> 创建新课程
                            </button>
                        </div>

                        <!-- 待办事项 -->
                        <div class="col-span-1 bg-paper-card border border-paper-border rounded-lg p-6 shadow-paper flex flex-col">
                            <div class="flex justify-between items-center mb-6">
                                <h3 class="font-serif font-bold text-paper-ink text-lg flex items-center gap-2"><i class="ph-duotone ph-clipboard-text"></i> 待办事项</h3>
                                <span class="w-5 h-5 rounded-full bg-teacher text-white text-[10px] flex items-center justify-center font-mono">0</span>
                            </div>
                            <div class="flex-1 flex flex-col items-center justify-center text-paper-sub opacity-50 py-10">
                                <i class="ph-duotone ph-inbox text-5xl mb-3"></i>
                                <span class="text-sm">暂无待办</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>


    <!-- ========================================== -->
    <!-- 视图 2：学生端工作台 (对应图二布局)          -->
    <!-- ========================================== -->
    <div id="student-view" class="hidden flex-col h-screen relative z-10 w-full transition-opacity duration-300">
        
        <!-- 顶部通栏导航 (护眼白底) -->
        <header class="h-16 bg-paper-card border-b border-paper-border flex items-center justify-between px-6 shrink-0 z-20">
            <!-- 左侧 Logo -->
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-slate rounded flex items-center justify-center text-chalk shadow-md">
                    <i class="ph-duotone ph-sparkle text-ai-glow"></i>
                </div>
                <span class="font-serif font-bold text-paper-ink text-lg">课程学习助手</span>
            </div>

            <!-- 中间胶囊导航 -->
            <nav class="hidden md:flex bg-paper-bg border border-paper-border rounded-full p-1 shadow-inner">
                <button class="px-6 py-1.5 bg-paper-card shadow text-paper-ink rounded-full text-sm font-bold flex items-center gap-2">
                    <i class="ph-duotone ph-book-open"></i> 工作台
                </button>
                <button class="px-6 py-1.5 text-paper-sub hover:text-paper-ink rounded-full text-sm flex items-center gap-2 transition-colors">
                    <i class="ph-duotone ph-monitor-play"></i> 我的课程
                </button>
                <button class="px-6 py-1.5 text-paper-sub hover:text-paper-ink rounded-full text-sm flex items-center gap-2 transition-colors">
                    <i class="ph-duotone ph-magic-wand"></i> AI 问答
                </button>
                <button class="px-6 py-1.5 text-paper-sub hover:text-paper-ink rounded-full text-sm flex items-center gap-2 transition-colors">
                    <i class="ph-duotone ph-notebook"></i> 错题本
                </button>
            </nav>

            <!-- 右侧动作区 -->
            <div class="flex items-center gap-4">
                <button class="w-8 h-8 rounded-full border border-paper-border flex items-center justify-center text-paper-sub hover:text-paper-ink bg-paper-bg">
                    <i class="ph-bold ph-magnifying-glass"></i>
                </button>
                <div class="relative cursor-pointer w-8 h-8 rounded-full border border-paper-border flex items-center justify-center text-paper-sub hover:text-paper-ink bg-paper-bg">
                    <i class="ph-duotone ph-bell"></i>
                    <span class="absolute -top-1 -right-1 w-3.5 h-3.5 bg-teacher text-white text-[9px] rounded-full flex items-center justify-center font-mono border-2 border-paper-card">4</span>
                </div>
                <div class="w-8 h-8 rounded-full bg-slate text-chalk flex items-center justify-center shadow-md cursor-pointer text-xs font-bold ml-2">
                    <i class="ph-duotone ph-user"></i>
                </div>
            </div>
        </header>

        <!-- 主内容区 -->
        <main class="flex-1 overflow-y-auto p-6 md:p-8">
            <div class="max-w-5xl mx-auto space-y-6">
                
                <!-- 欢迎横幅 (黑板质感) -->
                <div class="bg-slate rounded-xl overflow-hidden relative p-8 shadow-paper h-40 flex items-center">
                    <div class="banner-texture"></div>
                    <div class="relative z-10 flex w-full justify-between items-center px-4">
                        <div class="flex items-center gap-4 text-chalk">
                            <div class="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center bg-white/5">
                                <i class="ph-duotone ph-sun text-2xl text-ai-glow"></i>
                            </div>
                            <div>
                                <h1 class="text-3xl font-serif font-bold tracking-wide mb-1">晚上好，stu1</h1>
                                <p class="text-sm font-sans text-dust font-mono">5月4日 星期一 · 距本学期结束还有 72 天</p>
                            </div>
                        </div>
                        <div class="w-14 h-14 rounded-full border-4 border-ai-glow/30 flex items-center justify-center text-chalk font-mono font-bold">
                            0/1
                        </div>
                    </div>
                </div>

                <!-- 今日计划 (极简纸张条) -->
                <div class="bg-paper-card border border-paper-border rounded-xl p-4 shadow-paper flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded bg-paper-bg border border-paper-border flex items-center justify-center text-paper-sub">
                            <i class="ph-duotone ph-calendar-check text-xl"></i>
                        </div>
                        <div>
                            <div class="font-serif font-bold text-paper-ink text-sm">今日计划</div>
                            <div class="text-xs text-paper-sub mt-0.5">查看并打卡今天的学习任务</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <span class="text-sm font-mono text-paper-sub">0/1</span>
                        <div class="w-32 h-1 bg-paper-bg border border-paper-border rounded-full overflow-hidden"></div>
                        <a href="#" class="text-sm text-ai-glow font-bold ml-2">查看</a>
                    </div>
                </div>

                <!-- 继续学习大卡片 -->
                <div class="bg-paper-card border border-paper-border rounded-xl p-6 shadow-paper flex flex-col md:flex-row gap-6">
                    <!-- 左侧封面图 (原深绿色块，改为书本内页隐喻) -->
                    <div class="w-full md:w-64 h-48 bg-slate rounded-lg relative overflow-hidden flex items-center justify-center shadow-inner group cursor-pointer">
                        <div class="absolute inset-0 bg-gradient-to-br from-slate to-[#1a201d]"></div>
                        <i class="ph-duotone ph-presentation-chart text-5xl text-ai-glow relative z-10 group-hover:scale-110 transition-transform"></i>
                        <div class="absolute bottom-3 right-3 bg-white/10 backdrop-blur text-chalk text-xs font-mono px-2 py-1 rounded">P23</div>
                    </div>
                    
                    <!-- 右侧进度信息 -->
                    <div class="flex-1 flex flex-col justify-between py-2">
                        <div>
                            <div class="flex items-center gap-2 text-xs font-bold text-ai-glow bg-ai-glow/10 px-2 py-1 rounded inline-flex mb-3">
                                <i class="ph-duotone ph-sparkle"></i> 接着上次
                            </div>
                            <h2 class="text-2xl font-serif font-bold text-paper-ink mb-2">第6章_语法制导的翻译</h2>
                            <p class="text-sm text-paper-sub font-sans">第 23 页 / 共 35 页</p>
                            
                            <!-- 进度条 -->
                            <div class="mt-4">
                                <div class="w-full h-1.5 bg-paper-bg border border-paper-border rounded-full overflow-hidden">
                                    <div class="h-full bg-ai-glow w-[65%] rounded-full shadow-[0_0_8px_rgba(0,229,255,0.4)]"></div>
                                </div>
                                <div class="text-xs text-paper-sub mt-2 font-mono">上次学习：10小时前</div>
                            </div>
                        </div>
                        
                        <button class="w-full mt-6 py-3 bg-slate text-chalk hover:bg-black transition-colors rounded flex items-center justify-center gap-2 text-sm font-bold shadow-md">
                            <i class="ph-bold ph-play text-ai-glow"></i> 继续学习
                        </button>
                    </div>
                </div>

                <!-- 底部双栏结构 -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- 我的课程 -->
                    <div class="bg-paper-card border border-paper-border rounded-xl p-6 shadow-paper">
                        <div class="flex justify-between items-center mb-6">
                            <h3 class="font-serif font-bold text-paper-ink text-lg flex items-center gap-2"><i class="ph-duotone ph-book-open"></i> 我的课程</h3>
                            <a href="#" class="px-3 py-1 bg-paper-bg border border-paper-border rounded text-xs text-paper-sub hover:text-paper-ink">查看全部</a>
                        </div>
                        
                        <div class="flex items-center gap-4 bg-paper-bg border border-paper-border p-3 rounded-lg">
                            <div class="w-12 h-12 rounded bg-slate flex items-center justify-center shadow text-ai-glow">
                                <i class="ph-duotone ph-book-open text-xl"></i>
                            </div>
                            <div class="flex-1">
                                <div class="font-serif font-bold text-paper-ink mb-1">编译原理</div>
                                <div class="text-xs text-paper-sub font-sans mb-2">teacher · 2026春</div>
                                <div class="w-full h-1 bg-paper-border rounded-full overflow-hidden">
                                    <div class="h-full bg-ai-glow w-[40%] rounded-full"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 我的学习 (雷达/环形图区) -->
                    <div class="bg-paper-card border border-paper-border rounded-xl p-6 shadow-paper">
                        <div class="flex justify-between items-center mb-6">
                            <h3 class="font-serif font-bold text-paper-ink text-lg flex items-center gap-2"><i class="ph-duotone ph-chart-bar"></i> 我的学习</h3>
                            <a href="#" class="px-3 py-1 bg-paper-bg border border-paper-border rounded text-xs text-paper-sub hover:text-paper-ink">学习报告</a>
                        </div>
                        
                        <div class="flex justify-between px-4 mt-8">
                            <!-- 模拟环形图 1 -->
                            <div class="flex flex-col items-center">
                                <div class="w-16 h-16 rounded-full border-4 border-paper-bg relative flex items-center justify-center mb-2">
                                    <svg class="absolute inset-0 w-full h-full transform -rotate-90">
                                        <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="4" fill="none" class="text-paper-border" />
                                        <circle cx="32" cy="32" r="28" stroke="#00B8D4" stroke-width="4" fill="none" stroke-dasharray="175" stroke-dashoffset="140" stroke-linecap="round" />
                                    </svg>
                                    <span class="font-mono font-bold text-paper-ink text-sm z-10">0.2h</span>
                                </div>
                                <span class="text-xs text-paper-sub">今日时长</span>
                            </div>
                            <!-- 模拟环形图 2 -->
                            <div class="flex flex-col items-center">
                                <div class="w-16 h-16 rounded-full border-4 border-paper-bg relative flex items-center justify-center mb-2">
                                    <svg class="absolute inset-0 w-full h-full transform -rotate-90">
                                        <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="4" fill="none" class="text-paper-border" />
                                    </svg>
                                    <span class="font-mono font-bold text-paper-ink text-sm z-10">0%</span>
                                </div>
                                <span class="text-xs text-paper-sub">今日任务</span>
                            </div>
                            <!-- 模拟环形图 3 -->
                            <div class="flex flex-col items-center">
                                <div class="w-16 h-16 rounded-full border-4 border-paper-bg relative flex items-center justify-center mb-2">
                                    <svg class="absolute inset-0 w-full h-full transform -rotate-90">
                                        <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="4" fill="none" class="text-paper-border" />
                                        <circle cx="32" cy="32" r="28" stroke="#00B8D4" stroke-width="4" fill="none" stroke-dasharray="175" stroke-dashoffset="100" stroke-linecap="round" />
                                    </svg>
                                    <span class="font-mono font-bold text-paper-ink text-sm z-10">42%</span>
                                </div>
                                <span class="text-xs text-paper-sub">正确率</span>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </main>
    </div>

    <!-- 演示用：切换视角按钮 -->
    <button onclick="toggleView()" class="fixed bottom-6 right-6 bg-slate text-chalk px-6 py-3 rounded-full shadow-2xl font-sans font-bold flex items-center gap-2 hover:bg-black transition-all z-50 group border border-white/10">
        <i class="ph-bold ph-arrows-left-right group-hover:rotate-180 transition-transform duration-500"></i>
        <span id="btn-text">切换至：学生端</span>
    </button>

    <script>
        let isTeacher = true;
        const teacherView = document.getElementById('teacher-view');
        const studentView = document.getElementById('student-view');
        const btnText = document.getElementById('btn-text');

        function toggleView() {
            if (isTeacher) {
                teacherView.classList.add('hidden');
                teacherView.classList.remove('flex');
                studentView.classList.remove('hidden');
                studentView.classList.add('flex');
                btnText.innerText = '切换至：教师端';
            } else {
                studentView.classList.add('hidden');
                studentView.classList.remove('flex');
                teacherView.classList.remove('hidden');
                teacherView.classList.add('flex');
                btnText.innerText = '切换至：学生端';
            }
            isTeacher = !isTeacher;
        }
    </script>
</body>
</html>
```

# 网站首页
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClassAgent - 智学黑板与会思考的书</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        /* 彻底摒弃外部字体，调用国内系统自带的高级手写体(苹果手札体/Win华文行楷) */
                        chalk: ['"Hannotate SC"', '"HanziPen SC"', '"Wawati SC"', '"STXingkai"', '"华文行楷"', '"PingFang SC"', 'sans-serif'], 
                        serif: ['"Songti SC"', '"STSong"', '"SimSun"', '"宋体"', 'serif'],
                        sans: ['-apple-system', 'BlinkMacSystemFont', '"PingFang SC"', '"Microsoft YaHei"', '"Helvetica Neue"', 'sans-serif'],
                        mono: ['"SFMono-Regular"', 'Consolas', '"Liberation Mono"', 'Menlo', 'monospace'],
                    },
                    colors: {
                        slate: '#121614', // 黑板深墨绿
                        chalk: '#F4F4F0', // 粉笔白
                        dust: '#8C948F',  // 擦拭粉尘灰
                        'ai-glow': '#00E5FF', // 觉醒青蓝光芒
                        
                        // 逼真的纸张色彩系统 (严格保持上一版的高级质感)
                        paper: {
                            base: '#F4F1EA',    
                            dark: '#E6E2D6',    
                            edge: '#D1CBB5',    
                            ink: '#2C2B29',     
                            accent: '#C23A22'   
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body { margin: 0; background-color: #121614; color: #F4F4F0; overflow-x: hidden; cursor: default; }

        /* ====== 黑板质感 ====== */
        .board-texture {
            position: fixed; inset: 0; pointer-events: none; z-index: 0;
            background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)" opacity="0.04"/%3E%3C/svg%3E');
        }
        .board-smudge {
            position: fixed; inset: 0; pointer-events: none; z-index: 1;
            background: radial-gradient(circle at 20% 30%, rgba(244, 244, 240, 0.03) 0%, transparent 40%),
                        radial-gradient(circle at 80% 70%, rgba(244, 244, 240, 0.02) 0%, transparent 35%);
        }

        /* ====== 粉笔字特效 ====== */
        .text-chalk {
            text-shadow: 0px 0px 2px rgba(244, 244, 240, 0.7), 1px 1px 1px rgba(244, 244, 240, 0.4);
            letter-spacing: 0.05em;
        }

        /* ====== AI 透视扫描 ====== */
        .ai-scanner-container { position: relative; display: inline-block; }
        .ai-reveal-layer {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            color: #00E5FF; font-family: 'PingFang SC', sans-serif; font-weight: 900;
            text-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
            clip-path: polygon(0 0, 0 0, 0 100%, 0 100%);
            transition: clip-path 0.1s ease-out; pointer-events: none; white-space: nowrap;
        }

        /* ====== 手绘线条 SVG ====== */
        .draw-path {
            stroke-dasharray: 2000; stroke-dashoffset: 2000;
            animation: draw 4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        @keyframes draw { to { stroke-dashoffset: 0; } }

        /* ====== 3D 实体书籍系统 (严格保持逼真阴影和封面) ====== */
        .preserve-3d { transform-style: preserve-3d; }
        .backface-hidden { backface-visibility: hidden; }
        
        .book {
            position: relative;
            width: 90vw; max-width: 1000px; 
            height: 60vh; max-height: 650px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.6), 0 0 40px rgba(0,0,0,0.4);
            border-radius: 4px;
        }

        .paper-texture {
            position: absolute; inset: 0; pointer-events: none; z-index: 100;
            background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="1.5" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noise)" opacity="0.03"/%3E%3C/svg%3E');
        }

        .book-base-left, .book-base-right {
            position: absolute; top: 0; width: 50%; height: 100%;
            background-color: #F4F1EA; overflow: hidden;
        }
        .book-base-left { 
            left: 0; border-radius: 4px 0 0 4px; 
            box-shadow: inset -20px 0 40px rgba(0,0,0,0.06), -1px 1px 0 #E6E2D6, -2px 2px 0 #D1CBB5, -3px 3px 0 #D1CBB5; 
        }
        .book-base-right { 
            right: 0; border-radius: 0 4px 4px 0; 
            box-shadow: inset 20px 0 40px rgba(0,0,0,0.06), 1px 1px 0 #E6E2D6, 2px 2px 0 #D1CBB5, 3px 3px 0 #D1CBB5; 
        }

        .page {
            position: absolute; top: 0; left: 50%;
            width: 50%; height: 100%;
            transform-origin: left center;
            border-radius: 0 4px 4px 0; z-index: 10;
        }
        .page-front, .page-back {
            position: absolute; inset: 0; width: 100%; height: 100%;
            background-color: #F4F1EA; overflow: hidden;
        }
        .page-shadow-front { position: absolute; inset: 0; background: linear-gradient(to right, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%); pointer-events: none; z-index: 50;}
        .page-shadow-back { position: absolute; inset: 0; background: linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%); pointer-events: none; z-index: 50;}

        .page-back { transform: rotateY(180deg); border-radius: 4px 0 0 4px; }
        .text-ink { color: #2C2B29; }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #121614; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    </style>
</head>
<body class="selection:bg-ai-glow/30 selection:text-white">

    <div class="board-texture"></div>
    <div class="board-smudge"></div>

    <!-- 顶部导航 -->
    <nav class="fixed top-0 w-full z-50 py-4 bg-[#121614]/80 backdrop-blur-md border-b border-chalk/5">
        <div class="max-w-7xl mx-auto px-6 flex items-center justify-between">
            <div class="flex items-center gap-2 font-sans font-bold text-xl text-chalk">
                智学黑板<span class="text-ai-glow leading-none">.</span>
            </div>
            <div class="hidden md:flex space-x-10 text-[14px] font-sans text-dust">
                <a href="#hero" class="hover:text-chalk transition-colors">核心指引</a>
                <a href="#book-section" class="hover:text-chalk transition-colors">伴学魔法</a>
                <a href="#roles" class="hover:text-chalk transition-colors">多端教室</a>
            </div>
            <div class="flex items-center gap-5 font-sans">
                <a href="#" class="text-[13px] text-dust hover:text-chalk transition-colors">登录账号</a>
                <a href="#" class="bg-chalk text-slate px-5 py-2 font-bold text-[13px] hover:bg-ai-glow transition-colors duration-300">
                    免费注册学生端
                </a>
            </div>
        </div>
    </nav>

    <!-- ====== 核心：500vh 的粘性滚动轨道 ====== -->
    <!-- 这个轨道包含了黑板的放大淡出、书籍的上浮与翻页 -->
    <div id="scroll-track" style="height: 500vh; position: relative;">
        
        <!-- Sticky 吸附舞台 -->
        <div id="stage" class="sticky top-0 w-full h-screen overflow-hidden flex items-center justify-center">
            
            <!-- ====== 场景 1：完美的黑板首屏 (内容与上一版 100% 一致) ====== -->
            <section id="scene-blackboard" class="absolute inset-0 w-full flex flex-col justify-center items-center z-10 pt-10 origin-center">
                <!-- 左上：物理公式 -->
                <div class="absolute top-32 left-10 md:left-32 opacity-30 pointer-events-none">
                    <svg width="250" height="250" viewBox="0 0 250 250" class="stroke-chalk stroke-[1.5] fill-none">
                        <circle cx="100" cy="100" r="50" class="draw-path"/>
                        <path d="M100,100 L200,40" class="draw-path" style="animation-delay: 0.5s;"/>
                        <path d="M100,100 L110,200" class="draw-path" style="animation-delay: 0.8s;"/>
                        <text x="150" y="30" class="font-serif text-lg stroke-none fill-chalk" style="animation: fadeIn 2s forwards 1.5s; opacity:0; letter-spacing: 2px;">F = m·a</text>
                        <text x="120" y="180" class="font-serif text-lg stroke-none fill-chalk" style="animation: fadeIn 2s forwards 1.5s; opacity:0; letter-spacing: 2px;">m·g</text>
                    </svg>
                </div>

                <!-- 右上：化学六边形 -->
                <div class="absolute top-40 right-10 md:right-32 opacity-30 pointer-events-none">
                    <svg width="200" height="200" viewBox="0 0 200 200" class="stroke-chalk stroke-[1.5] fill-none">
                        <polygon points="100,30 160,65 160,135 100,170 40,135 40,65" class="draw-path" style="animation-delay: 1s;"/>
                        <line x1="100" y1="30" x2="100" y2="0" class="draw-path" style="animation-delay: 2s;"/>
                    </svg>
                </div>

                <!-- 左下：竖排文言文 -->
                <div class="absolute bottom-32 left-10 md:left-24 opacity-60 pointer-events-none font-chalk text-3xl text-chalk vertical-rl tracking-[0.3em] leading-relaxed" style="writing-mode: vertical-rl; animation: fadeIn 3s forwards 1s; opacity:0;">
                    “学而不思则罔，<br>思而不学则殆。”
                </div>

                <!-- 居中核心区 -->
                <div class="text-center relative z-20 max-w-5xl px-6">
                    <p class="font-chalk text-3xl md:text-[2.5rem] text-dust mb-12 -rotate-2 transform -translate-x-10 text-chalk tracking-widest">
                        人类在黑板前仰望了三百年，
                    </p>

                    <div class="ai-scanner-container text-5xl md:text-[6.5rem] font-chalk text-chalk leading-tight mb-16 rotate-1" id="hero-text">
                        <span class="text-chalk drop-shadow-lg tracking-wide text-chalk">今天，黑板开始思考。</span>
                        <div class="ai-reveal-layer flex items-center justify-center tracking-[0.2em]" id="hero-glow">
                            全知伴学引擎_已激活
                        </div>
                    </div>

                    <p class="font-serif font-light text-[17px] text-gray-400 max-w-2xl mx-auto leading-[2] tracking-widest mb-16 opacity-0" style="animation: fadeIn 2s forwards 2s;">
                        上传你的课本、试卷与错题。<br>系统将其化作专属于你的数字导师网。<br>
                        <span class="text-chalk font-bold">告别死记硬背，每一次提问，都直击知识本质。</span>
                    </p>

                    <!-- 操作按钮区 -->
                    <div class="flex flex-col sm:flex-row justify-center items-center gap-12 opacity-0" style="animation: fadeIn 2s forwards 2.5s;">
                        <a href="#book-scroll-track" class="group relative inline-flex items-center gap-2 text-chalk font-serif font-bold text-[19px] tracking-widest cursor-pointer">
                            <span class="relative z-10 group-hover:text-ai-glow transition-colors">进入我的自学空间</span>
                            <i class="ph-bold ph-arrow-right relative z-10 group-hover:text-ai-glow group-hover:translate-x-1 transition-all"></i>
                            <svg class="absolute -inset-4 w-[120%] h-[150%] -z-10 stroke-chalk stroke-2 fill-none opacity-60 group-hover:stroke-ai-glow transition-colors" viewBox="0 0 100 40" preserveAspectRatio="none">
                                <path d="M5,20 Q50,0 95,20 Q50,40 5,20" />
                            </svg>
                        </a>
                        <a href="#" class="group inline-flex items-center gap-2 text-dust font-serif font-bold text-[17px] tracking-widest hover:text-chalk transition-colors">
                            <i class="ph-duotone ph-chalkboard-teacher text-xl"></i> 教师执教控制台
                        </a>
                    </div>
                    
                    <div class="mt-24 text-dust font-sans text-xs tracking-[0.5em] opacity-0 flex flex-col items-center gap-6" style="animation: fadeIn 2s forwards 3s;">
                        向下滚动，见证课堂的进化
                        <div class="w-px h-16 bg-gradient-to-b from-dust to-transparent"></div>
                    </div>
                </div>
            </section>

            <!-- ====== 场景 2：3D 翻页书 (与上一版 UI 一致，加入转场逻辑) ====== -->
            <div id="scene-book" class="absolute inset-0 z-30 flex justify-center items-center pointer-events-none opacity-0 transform translate-y-32">
                <div class="book preserve-3d" id="the-book">
                    <div class="paper-texture"></div>

                    <!-- 封底页 (静止在左) -->
                    <div class="book-base-left relative">
                        <div class="absolute inset-0 p-12 opacity-40 flex flex-col justify-center items-center text-center font-serif">
                            <div class="w-16 h-16 border border-paper-ink rounded-full flex items-center justify-center mb-4">
                                <i class="ph-duotone ph-books text-3xl text-paper-ink"></i>
                            </div>
                            <h2 class="text-2xl text-paper-ink font-bold mb-2">知识的重构</h2>
                            <p class="text-sm text-paper-ink font-sans">The Next Generation of Learning.</p>
                        </div>
                    </div>

                    <!-- 引导文案 (静止在右) -->
                    <div class="book-base-right relative">
                        <div class="absolute inset-0 p-10 md:p-16 flex flex-col justify-center">
                            <span class="absolute top-8 right-8 text-xs font-mono text-gray-400">FIN.</span>
                            <h2 class="text-4xl font-serif font-black text-paper-ink mb-6">这不是结束。</h2>
                            <p class="text-[15px] text-gray-600 font-sans mb-10 leading-relaxed text-justify">
                                这只是一本随时待命的字典。当你遇到难题，当你需要规划，当你想要深究背后的逻辑。<br><br>
                                请随时翻开这本会思考的书。
                            </p>
                            <div class="mt-auto border-t border-gray-300 pt-6">
                                <p class="text-xs text-gray-500 font-sans tracking-widest uppercase mb-4">向下滑动，探索多端教室配置</p>
                                <i class="ph-bold ph-arrow-down text-2xl text-paper-ink animate-bounce"></i>
                            </div>
                        </div>
                    </div>

                    <!-- 【翻页 2：AI 加持体验】 -->
                    <div class="page preserve-3d" id="page2">
                        <div class="page-front backface-hidden p-10 md:p-16 relative">
                            <div class="page-shadow-front" id="shadow2-front"></div>
                            <span class="absolute top-8 right-8 text-xs font-mono text-gray-400">03</span>
                            <h3 class="text-3xl font-serif font-black text-paper-ink mb-8 mt-4 border-l-4 border-ai-glow pl-4">现在，课本活了过来。</h3>
                            <div class="relative bg-white border border-gray-200 shadow-sm p-6 rounded mb-6 font-serif text-[15px] text-paper-ink leading-loose text-justify">
                                “动量定理告诉我们，物体动量的变化量等于它所受合外力的冲量。即：
                                <br><span class="font-mono text-lg bg-gray-50 px-2 my-2 inline-block border border-gray-100">F·Δt = Δp</span>”
                                <!-- AI 弹窗贴纸 -->
                                <div class="absolute -bottom-6 -left-6 w-[110%] bg-[#0A1118] text-white p-5 rounded shadow-xl transform -rotate-1">
                                    <div class="flex items-center gap-2 text-ai-glow text-xs font-bold mb-2">
                                        <i class="ph-fill ph-magic-wand"></i> AI 伴学大脑
                                    </div>
                                    <p class="text-[14px] font-sans font-light leading-relaxed">
                                        注意这个公式！如果把时间 $\Delta t$ 极度缩短，力 $F$ 会极大。这就解释了为何车祸破坏力惊人。
                                    </p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="page-back backface-hidden p-10 md:p-16 relative bg-[#1B1D1C]">
                            <div class="page-shadow-back" id="shadow2-back"></div>
                            <span class="absolute top-8 left-8 text-xs font-mono text-gray-500">04</span>
                            <div class="h-full flex flex-col justify-center">
                                <h3 class="text-2xl font-serif font-black text-chalk mb-6">看不见的学情网络</h3>
                                <p class="text-[14px] text-gray-400 font-sans leading-relaxed mb-8">
                                    系统静默追踪错题，摒弃盲目题海，自动生成知识雷达图，进行靶向提升。
                                </p>
                                <div class="w-full h-40 bg-white/5 border border-white/10 rounded flex items-center justify-center relative overflow-hidden">
                                    <svg viewBox="0 0 100 100" class="w-24 h-24 opacity-50 stroke-ai-glow fill-ai-glow/20">
                                        <polygon points="50,5 90,35 75,85 25,85 10,35" stroke-width="1"/>
                                        <polygon points="50,25 70,45 60,70 40,70 30,45" stroke-width="1" fill="none"/>
                                        <circle cx="50" cy="50" r="2" fill="#fff"/>
                                    </svg>
                                    <div class="absolute bottom-2 right-2 text-[10px] text-ai-glow font-mono">DATA_ACTIVE</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 【翻页 1：旧时代的痛点】 -->
                    <div class="page preserve-3d" id="page1">
                        <div class="page-front backface-hidden p-10 md:p-16 relative">
                            <div class="page-shadow-front" id="shadow1-front"></div>
                            <span class="absolute top-8 right-8 text-xs font-mono text-gray-400">01</span>
                            <div class="text-[10px] font-bold uppercase tracking-[0.2em] text-paper-accent mb-6">Chapter I. The Past</div>
                            <h3 class="text-3xl font-serif font-black text-paper-ink mb-6">曾经，学习是一座孤岛。</h3>
                            <p class="text-[15px] text-gray-600 leading-loose font-serif text-justify indent-8">
                                面对厚重的印刷讲义，跳跃的公式步骤总让人在深夜抓狂。不会做的错题，即使看了答案依然一知半解。在题海中盲目地刷着重复的卷子，却不知真正的薄弱点藏在哪里。
                            </p>
                            <!-- 模拟手写错题 -->
                            <div class="mt-8 p-6 bg-white border border-gray-200 relative transform rotate-1 shadow-sm">
                                <div class="absolute -top-3 left-1/2 -translate-x-1/2 w-8 h-3 bg-gray-300/50 -rotate-2"></div> 
                                <div class="font-chalk text-xl text-gray-500">“这道几何题到底怎么做...”</div>
                                <div class="w-full h-20 border-b-2 border-dashed border-gray-300 mt-2"></div>
                                <div class="absolute right-4 bottom-4 font-chalk text-5xl text-paper-accent opacity-70">X</div>
                            </div>
                        </div>
                        
                        <div class="page-back backface-hidden p-10 md:p-16 relative">
                            <div class="page-shadow-back" id="shadow1-back"></div>
                            <span class="absolute top-8 left-8 text-xs font-mono text-gray-400">02</span>
                            <div class="h-full flex flex-col items-center justify-center text-center opacity-30">
                                <i class="ph-duotone ph-arrow-fat-lines-right text-6xl text-paper-ink mb-4"></i>
                                <div class="font-serif font-bold text-xl text-paper-ink">翻页，<br>唤醒沉睡的文字。</div>
                            </div>
                        </div>
                    </div>

                </div>
            </div>

        </div>
    </div>

    <!-- ====== 正常滚动区域：书籍滑完后接在此处 ====== -->
    <section id="roles" class="relative py-32 px-6 bg-[#181C1A] border-t border-white/5 z-10">
        <div class="max-w-7xl mx-auto">
            <div class="text-center mb-24">
                <h2 class="font-serif text-4xl md:text-5xl text-chalk font-black mb-6">不只是课本，更是教室。</h2>
                <p class="font-sans text-dust text-[15px] tracking-widest">三端协同，构建校园的数字化闭环</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <!-- 伴学端 -->
                <div class="bg-[#121614] border border-white/10 p-10 hover:border-ai-glow/50 transition-colors duration-500 rounded-sm">
                    <div class="w-12 h-12 bg-ai-glow/10 flex items-center justify-center mb-8">
                        <i class="ph-duotone ph-student text-2xl text-ai-glow"></i>
                    </div>
                    <h3 class="text-xl font-serif font-bold text-chalk mb-6">学生伴学控制台</h3>
                    <ul class="space-y-4 font-sans text-[14px] text-gray-400">
                        <li class="flex gap-3"><i class="ph-bold ph-check text-ai-glow mt-1"></i> 沉浸式课件播放与阅读。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-ai-glow mt-1"></i> 课程范围内的精准伴学问答。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-ai-glow mt-1"></i> 错题归档与生成考前复习卷。</li>
                    </ul>
                </div>

                <!-- 教师端 -->
                <div class="bg-[#121614] border border-white/10 p-10 hover:border-[#FF5722]/50 transition-colors duration-500 rounded-sm">
                    <div class="w-12 h-12 bg-[#FF5722]/10 flex items-center justify-center mb-8">
                        <i class="ph-duotone ph-chalkboard-teacher text-2xl text-[#FF5722]"></i>
                    </div>
                    <h3 class="text-xl font-serif font-bold text-chalk mb-6">教师教研指挥舱</h3>
                    <ul class="space-y-4 font-sans text-[14px] text-gray-400">
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#FF5722] mt-1"></i> 极速上传资料，静默切片向量化。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#FF5722] mt-1"></i> 随堂测验下发与客观题秒批。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#FF5722] mt-1"></i> 班级掌握度雷达与预警推送。</li>
                    </ul>
                </div>

                <!-- 管理端 -->
                <div class="bg-[#121614] border border-white/10 p-10 hover:border-[#D9A05B]/50 transition-colors duration-500 rounded-sm">
                    <div class="w-12 h-12 bg-[#D9A05B]/10 flex items-center justify-center mb-8">
                        <i class="ph-duotone ph-sliders text-2xl text-[#D9A05B]"></i>
                    </div>
                    <h3 class="text-xl font-serif font-bold text-chalk mb-6">运维管理底层</h3>
                    <ul class="space-y-4 font-sans text-[14px] text-gray-400">
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#D9A05B] mt-1"></i> 灵活配置各家大模型接口路由。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#D9A05B] mt-1"></i> 阿里云多模态服务无缝集成。</li>
                        <li class="flex gap-3"><i class="ph-bold ph-check text-[#D9A05B] mt-1"></i> RBAC 权限分配与数据隔离。</li>
                    </ul>
                </div>
            </div>
        </div>
    </section>

    <footer class="py-32 px-6 text-center relative bg-[#121614] z-10 border-t border-white/5">
        <h2 class="font-serif font-black text-4xl md:text-[5rem] text-chalk mb-12 tracking-tight">将知识留在校园。</h2>
        <p class="font-sans text-[16px] text-dust mb-16 max-w-2xl mx-auto leading-relaxed">
            支持教育机构完整私有化部署。后端基于 FastAPI，前端搭载 Vue3，接管核心教务数据资产，构建真正属于您自己的智能基建。
        </p>

        <div class="flex flex-col sm:flex-row justify-center gap-6 font-sans">
            <a href="#" class="text-slate font-bold bg-chalk px-12 py-4 hover:bg-ai-glow hover:shadow-[0_0_30px_rgba(0,229,255,0.4)] transition-all duration-300 text-[15px] rounded-sm">
                申请校园试用授权
            </a>
            <a href="#" class="text-chalk border border-dust hover:border-chalk px-12 py-4 transition-colors flex items-center justify-center gap-2 text-[15px] rounded-sm">
                审阅 API 开发文档
            </a>
        </div>
    </footer>

    <!-- ====== JS 引擎：Lerp 平滑转场与 3D 翻页 ====== -->
    <script>
        // 1. 黑板透视扫描
        const heroText = document.getElementById('hero-text');
        const heroGlow = document.getElementById('hero-glow');
        if (heroText && heroGlow) {
            heroText.addEventListener('mousemove', (e) => {
                const rect = heroText.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                heroGlow.style.clipPath = `polygon(${x - 12}% 0, ${x + 12}% 0, ${x + 12}% 100%, ${x - 12}% 100%)`;
            });
            heroText.addEventListener('mouseleave', () => {
                heroGlow.style.clipPath = `polygon(0 0, 0 0, 0 100%, 0 100%)`;
            });
        }

        // 2. 核心插值动画引擎 (复刻你最喜欢的转场逻辑)
        const track = document.getElementById('scroll-track');
        const sceneBlackboard = document.getElementById('scene-blackboard');
        const sceneBook = document.getElementById('scene-book');
        const page1 = document.getElementById('page1');
        const page2 = document.getElementById('page2');
        
        const shadow1Front = document.getElementById('shadow1-front');
        const shadow1Back = document.getElementById('shadow1-back');
        const shadow2Front = document.getElementById('shadow2-front');
        const shadow2Back = document.getElementById('shadow2-back');

        let targetScroll = window.scrollY;
        let currentScroll = window.scrollY;
        const ease = 0.08; // 平滑系数

        window.addEventListener('scroll', () => {
            targetScroll = window.scrollY;
        });

        function render() {
            currentScroll += (targetScroll - currentScroll) * ease;
            
            // 获取轨道相对于文档顶部的绝对高度，并计算虚拟进度
            const trackTop = track.offsetTop;
            const scrollableDistance = track.offsetHeight - window.innerHeight;
            
            let virtualY = currentScroll - trackTop;
            let progress = 0;
            
            if (virtualY > 0) {
                progress = virtualY / scrollableDistance;
            }
            progress = Math.max(0, Math.min(1, progress)); // 锁定在 0-1

            /* 
             * 动画进度编排：
             * 0.00 - 0.15: 黑板放大并淡出
             * 0.15 - 0.30: 书籍从下浮现
             * 0.30 - 0.60: 翻阅第一页
             * 0.60 - 0.90: 翻阅第二页
             */

            // 1. 黑板淡出放大
            if (progress < 0.15) {
                let p = progress / 0.15;
                sceneBlackboard.style.opacity = 1 - p;
                sceneBlackboard.style.transform = `scale(${1 + p * 0.5})`;
                sceneBlackboard.style.pointerEvents = p > 0.5 ? 'none' : 'auto';
            } else {
                sceneBlackboard.style.opacity = 0;
                sceneBlackboard.style.pointerEvents = 'none';
            }

            // 2. 书籍浮现
            if (progress >= 0.15 && progress < 0.30) {
                let p = (progress - 0.15) / 0.15;
                sceneBook.style.opacity = p;
                sceneBook.style.transform = `translateY(${(1 - p) * 100}px) scale(${0.9 + p * 0.1})`;
                sceneBook.style.pointerEvents = 'auto';
            } else if (progress >= 0.30) {
                sceneBook.style.opacity = 1;
                sceneBook.style.transform = `translateY(0) scale(1)`;
                sceneBook.style.pointerEvents = 'auto';
            } else {
                sceneBook.style.opacity = 0;
                sceneBook.style.pointerEvents = 'none';
            }

            // 3. 翻阅第一页 (含逼真动态光影)
            if (progress <= 0.30) {
                page1.style.transform = `rotateY(0deg)`;
                shadow1Front.style.background = `linear-gradient(to right, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)`;
            } else if (progress > 0.30 && progress <= 0.60) {
                let p = (progress - 0.30) / 0.30;
                page1.style.transform = `rotateY(${-180 * p}deg)`;
                shadow1Front.style.background = `linear-gradient(to right, rgba(0,0,0,${0.1 + p*0.4}) 0%, rgba(0,0,0,0) ${20 + p*30}%)`;
                shadow1Back.style.background = `linear-gradient(to left, rgba(0,0,0,${0.5 - p*0.4}) 0%, rgba(0,0,0,0) ${50 - p*30}%)`;
            } else {
                page1.style.transform = `rotateY(-180deg)`;
                shadow1Back.style.background = `linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)`;
            }

            // 4. 翻阅第二页
            if (progress <= 0.60) {
                page2.style.transform = `rotateY(0deg)`;
                shadow2Front.style.background = `linear-gradient(to right, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)`;
            } else if (progress > 0.60 && progress <= 0.90) {
                let p = (progress - 0.60) / 0.30;
                page2.style.transform = `rotateY(${-180 * p}deg)`;
                shadow2Front.style.background = `linear-gradient(to right, rgba(0,0,0,${0.1 + p*0.4}) 0%, rgba(0,0,0,0) ${20 + p*30}%)`;
                shadow2Back.style.background = `linear-gradient(to left, rgba(0,0,0,${0.5 - p*0.4}) 0%, rgba(0,0,0,0) ${50 - p*30}%)`;
            } else {
                page2.style.transform = `rotateY(-180deg)`;
                shadow2Back.style.background = `linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)`;
            }

            requestAnimationFrame(render);
        }

        render();
    </script>
    
    <style>
        @keyframes fadeIn {
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</body>
</html>
```