<template>
  <section v-if="classroomOpen" class="study-room" :class="{ panelClosed: !aiPanelOpen }" @mousemove="revealChrome">
    <transition name="study-top">
      <header v-show="chromeVisible || !audioPlaying" class="study-head">
        <div>
          <button class="glass-btn" @click="closeClassroom"><ArrowLeft :size="17" />返回</button>
          <span>{{ activeCourse?.name || classroomLesson?.lesson.title }}</span>
          <ChevronRight :size="14" />
          <strong>{{ classroomLesson?.lesson.title }}</strong>
        </div>
        <code>{{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</code>
        <div>
          <Clock :size="16" />
          <code>{{ studyClock }}</code>
          <button class="icon-glass" @click="aiPanelOpen = !aiPanelOpen"><PanelRight :size="18" /></button>
          <button class="icon-glass" @click="settingsOpen = !settingsOpen"><Settings :size="18" /></button>
        </div>
      </header>
    </transition>

    <main class="study-main">
      <transition name="thumb-panel">
        <aside v-if="thumbOpen" class="thumb-panel">
          <strong>全部 {{ classroomLesson?.pages.length || 0 }} 页</strong>
          <div class="thumb-grid">
            <button
              v-for="page in classroomLesson?.pages || []"
              :key="page.id"
              :class="{ active: page.page_number === currentPage, learned: page.page_number < currentPage }"
              @click="jumpPage(page.page_number)"
            >
              <span>P{{ page.page_number }}</span>
              <Check v-if="page.page_number < currentPage" :size="12" />
            </button>
          </div>
        </aside>
      </transition>

      <section class="slide-stage">
        <transition :name="pageDirection === 'next' ? 'slide-next' : 'slide-prev'" mode="out-in">
          <article :key="activePage?.id || currentPage" class="slide-card">
            <span class="page-badge">P{{ currentPage }}</span>
            <span class="knowledge-dot" aria-label="AI知识点"><Sparkles :size="14" /></span>
            <h1>{{ activePage?.page_title || `第${currentPage}页` }}</h1>
            <p>{{ activePage?.page_text }}</p>
          </article>
        </transition>
        <transition name="subtitle">
          <div v-if="subtitleMode !== 'hide' && activePage?.subtitle_text" class="subtitle-line">
            <strong>{{ subtitleLead }}</strong>{{ subtitleRest }}
          </div>
        </transition>
        <transition name="player-pop">
          <div v-show="chromeVisible || !audioPlaying" class="player-bar">
            <button class="round-btn ghost" @click="firstPage"><SkipBack :size="18" /></button>
            <button class="round-btn primary" @click="toggleAudio"><component :is="audioPlaying ? Pause : Play" :size="20" /></button>
            <button class="round-btn ghost" @click="nextPage"><SkipForward :size="18" /></button>
            <span class="time">{{ audioTime }}</span>
            <input v-model.number="audioProgress" class="range" min="0" max="100" type="range" @input="seekAudio" />
            <span class="time">{{ audioDuration }}</span>
            <PopoverButton :items="speedItems" :label="`${playbackRate}x`" @select="setRate" />
            <button class="round-btn ghost" @click="thumbOpen = !thumbOpen"><Grid2X2 :size="18" /></button>
            <button class="round-btn ghost"><Maximize :size="18" /></button>
            <audio v-if="activePage?.audio_url" ref="audioRef" :src="activePage.audio_url" @timeupdate="updateAudio" @loadedmetadata="updateAudio" @ended="handleAudioEnded" @play="audioPlaying = true" @pause="audioPlaying = false"></audio>
          </div>
        </transition>
      </section>

      <aside class="lesson-ai">
        <div class="study-tabs">
          <button :class="{ active: classroomTab === 'script' }" @click="classroomTab = 'script'"><FileText :size="16" />文稿</button>
          <button :class="{ active: classroomTab === 'qa' }" @click="classroomTab = 'qa'"><MessageCircle :size="16" />问答</button>
          <button :class="{ active: classroomTab === 'note' }" @click="classroomTab = 'note'"><ListChecks :size="16" />笔记</button>
        </div>
        <transition name="fade-slide" mode="out-in">
          <section v-if="classroomTab === 'script'" key="script" class="script-view">
            <div class="sticky-tools"><span>当前页 {{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</span><button @click="copyText(activePage?.script_text || '')"><Copy :size="14" />复制</button></div>
            <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
            <p class="reading">{{ activePage?.script_text || "暂无文稿" }}</p>
          </section>
          <section v-else-if="classroomTab === 'qa'" key="qa" class="class-chat">
            <div class="context-bar"><Info :size="14" />第{{ currentPage }}页内容</div>
            <ChatList :messages="classMessages" :thinking="classThinking" @toggle-thought="toggleThought" @copy="copyText" />
            <div class="chat-disclaimer">AI 回答仅供学习参考</div>
            <form class="chat-input compact" @submit.prevent="askInClass">
              <textarea v-model="classQuestion" placeholder="问问 AI 这一页..." rows="1"></textarea>
              <button :disabled="!classQuestion.trim() || classThinking" class="send-btn"><Send :size="18" /></button>
            </form>
            <div class="quick-tags">
              <button v-for="item in quickPageQuestions" :key="item" @click="sendQuickClass(item)">{{ item }}</button>
            </div>
          </section>
          <section v-else key="note" class="note-view">
            <div class="note-tools"><button>B</button><button>I</button><button>标记</button><span>{{ noteState }}</span></div>
            <textarea v-model="pageNote" placeholder="记录你对这一页的理解、疑问或总结..." @input="queueNoteSave"></textarea>
            <footer><button class="btn btn-primary btn-sm" @click="saveCurrentNote">保存笔记</button><span>{{ noteSavedAt }}</span></footer>
          </section>
        </transition>
      </aside>
    </main>

    <transition name="modal-pop">
      <div v-if="completeOpen" class="modal-mask">
        <article class="complete-modal">
          <div class="confetti"><i v-for="n in 28" :key="n" :style="confettiStyle(n)"></i></div>
          <CheckCircle :size="56" />
          <h2>恭喜完成</h2>
          <p>{{ classroomLesson?.lesson.title }}</p>
          <div class="done-stats"><span>本次 {{ Math.max(1, Math.round(studySeconds / 60)) }} 分钟</span><span>{{ classroomLesson?.pages.length || 0 }} 页</span><span>{{ classMessages.filter((m) => m.role === 'user').length }} 次提问</span></div>
          <div class="ai-summary"><Sparkles :size="16" />{{ completionSummary }}</div>
          <footer><button class="btn btn-primary" @click="nextLessonAfterComplete">下一课堂</button><button class="btn btn-secondary" @click="returnCourse">回课程</button><button class="btn btn-ghost" @click="go('studentQuizzes')">做练习</button></footer>
        </article>
      </div>
    </transition>

    <transition name="fade-slide">
      <div v-if="settingsOpen" class="settings-pop">
        <button :class="{ active: subtitleMode === 'full' }" @click="subtitleMode = 'full'">完整字幕</button>
        <button :class="{ active: subtitleMode === 'keyword' }" @click="subtitleMode = 'keyword'">关键词</button>
        <button :class="{ active: subtitleMode === 'hide' }" @click="subtitleMode = 'hide'">隐藏字幕</button>
      </div>
    </transition>
  </section>

  <section v-else class="student-shell">
    <header class="student-top">
      <button class="brand" @click="go('studentHome')"><span><Sparkles :size="16" /></span><strong>课程学习助手</strong></button>
      <transition name="search-expand">
        <div v-if="searchOpen" class="global-search">
          <Search :size="18" />
          <input ref="searchInput" v-model="globalSearch" placeholder="搜索课程、知识点、问答" @keyup.esc="searchOpen = false" />
          <button @click="searchOpen = false"><X :size="18" /></button>
        </div>
      </transition>
      <div class="top-actions">
        <button class="top-icon" @click="openSearch"><Search :size="19" /></button>
        <button class="top-icon" @click="noticeOpen = !noticeOpen"><Bell :size="19" /><em v-if="unreadCount">{{ unreadCount }}</em></button>
        <button class="avatar-btn" @click="userMenuOpen = !userMenuOpen"><span>{{ firstChar(user.nickname) }}</span></button>
      </div>
      <transition name="popover">
        <div v-if="noticeOpen" class="notice-pop">
          <div v-for="item in notifications" :key="`${item.type}-${item.title}`" class="notice-item"><Bell :size="15" /><div><strong>{{ item.title }}</strong><small>{{ relativeTime(item.time) }}</small></div><i v-if="item.unread"></i></div>
          <EmptyState v-if="!notifications.length" text="暂无通知" />
        </div>
      </transition>
      <transition name="popover">
        <div v-if="userMenuOpen" class="user-pop">
          <div class="user-card"><strong>{{ user.nickname }}</strong><small>{{ user.email }}</small></div>
          <button @click="go('studentProfile')"><User :size="15" />个人中心</button>
          <button @click="go('studentProfile')"><BarChart2 :size="15" />学习档案</button>
          <button @click="go('studentWrongBook')"><BookMarked :size="15" />错题本</button>
          <button @click="go('studentPlans')"><CalendarCheck :size="15" />学习计划</button>
          <button @click="$emit('logout')"><LogOut :size="15" />退出登录</button>
        </div>
      </transition>
    </header>

    <main class="student-main">
      <transition name="page-switch" mode="out-in">
        <section :key="active" class="student-page">
          <template v-if="active === 'studentHome'">
            <article class="hello-card">
              <div><Sun :size="24" /><section><h1>{{ greeting }}，{{ user.nickname }}</h1><p>{{ todayText }} · 距本学期结束还有 {{ termLeftDays }} 天</p></section></div>
              <div v-if="todayTasks.length" class="circle-stat"><RingProgress :value="todayDoneRate" /><span>{{ doneTasks }}/{{ todayTasks.length }}</span></div>
              <button v-else class="white-pill" @click="go('studentPlans')"><Plus :size="14" />制定计划</button>
            </article>
            <article v-if="todayTasks.length" class="today-plan">
              <CalendarCheck :size="20" /><div><strong>今日计划</strong><small>查看并打卡今天的学习任务</small></div><span>{{ doneTasks }}/{{ todayTasks.length }}</span><progress :value="todayDoneRate" max="100"></progress><button @click="go('studentPlans')">查看</button>
            </article>
            <article class="continue-card">
              <div class="continue-cover" :style="{ background: courseGradient(continueLesson?.course?.id || 1) }"><Presentation :size="32" /><span>P{{ continueProgressPage }}</span></div>
              <section v-if="continueLesson">
                <span class="tag tag-ai"><Sparkles :size="12" />接续上次</span>
                <h2>{{ continueLesson.lesson.title }}</h2>
                <p>第 {{ continueProgressPage }} 页 / 共 {{ continueLesson.lesson.page_count || 1 }} 页</p>
                <progress :value="continueProgress" max="100"></progress>
                <small>{{ continueTime }}</small>
                <button class="btn btn-primary" @click="openLesson(continueLesson.lesson.id)"><Play :size="16" />继续学习</button>
              </section>
              <section v-else class="empty-continue"><BookOpen :size="42" /><h2>还没有学习</h2><button class="btn btn-primary" @click="go('studentCourses')">浏览课程</button></section>
            </article>
            <div class="home-grid">
              <article class="panel-card">
                <div class="section-head"><h2><BookOpen :size="18" />我的课程</h2><button @click="go('studentCourses')">查看全部</button></div>
                <button v-for="course in courses.slice(0, 3)" :key="course.id" class="home-course" @click="openCourse(course.id)">
                  <span :style="{ background: courseGradient(course.id) }"><BookOpen :size="21" /></span>
                  <div><strong>{{ course.name }}</strong><small>{{ course.teacher?.nickname || '教师' }} · {{ course.term }}</small><progress :value="course.progress_percent || 0" max="100"></progress><em>{{ course.progress_percent || 0 }}%</em></div>
                </button>
                <button class="join-dashed" @click="joinOpen = true"><Plus :size="16" />加入新课程</button>
              </article>
              <article class="panel-card">
                <div class="section-head"><h2><BarChart2 :size="18" />我的学习</h2><button @click="go('studentProfile')">学习报告</button></div>
                <div class="rings"><RingBlock label="本周学习" :value="hourTargetRate" :text="`${stats.study_hours || 0}h`" sub="目标5h" /><RingBlock label="完成率" :value="stats.completion_rate || 0" :text="`${stats.completion_rate || 0}%`" sub="课堂" tone="success" /><RingBlock label="正确率" :value="stats.accuracy || 0" :text="`${stats.accuracy || 0}%`" sub="练习" tone="ai" /></div>
                <div class="week-check"><span v-for="item in weekDays" :key="item.label" :class="{ done: item.done, today: item.today }">{{ item.label }}</span></div>
                <div class="streak"><Flame :size="16" />连续 {{ stats.streak_days || 0 }} 天</div>
              </article>
            </div>
            <article class="ai-reco">
              <section><Sparkles :size="20" /><div><h2>AI 今日推荐</h2><p>{{ dashboard.recommendation?.text || '今天优先完成一节课堂，并复盘一道错题。' }}</p><span class="tag tag-ai">AI生成</span><button @click="loadDashboard"><RefreshCw :size="14" />刷新建议</button></div></section>
              <aside><button @click="continueLesson && openLesson(continueLesson.lesson.id)"><BookOpen :size="16" />推荐课堂<span>前往学习</span></button><button @click="go('studentQuizzes')"><Pencil :size="16" />推荐练习<span>开始练习</span></button></aside>
            </article>
            <ActivityTimeline :items="activities" />
          </template>

          <template v-else-if="active === 'studentCourses'">
            <PageTitle title="我的课程" :sub="`共 ${courses.length} 门课程`"><button class="btn btn-primary" @click="joinOpen = true"><Plus :size="16" />加入课程</button></PageTitle>
            <div class="course-tools"><div class="pretty-input"><Search :size="16" /><input v-model="courseKeyword" placeholder="搜索课程名称" /></div><SelectMenu v-model="termFilter" :items="termOptions" /></div>
            <div class="underline-tabs"><button :class="{ active: courseTab === 'active' }" @click="courseTab = 'active'"><BookOpen :size="16" />在学中({{ activeCourses.length }})</button><button :class="{ active: courseTab === 'done' }" @click="courseTab = 'done'"><CheckCircle :size="16" />已完成({{ doneCourses.length }})</button></div>
            <div class="student-course-grid">
              <article v-for="course in filteredCourses" :key="course.id" class="student-course-card">
                <div class="course-art" :style="{ background: courseGradient(course.id) }"><BookOpen :size="56" /><span>{{ course.term }}</span><em><Check :size="12" />{{ course.progress_percent || 0 }}%</em><DropdownMenu :items="courseMenuItems" @select="handleCourseMenu($event, course)" /></div>
                <section><h2>{{ course.name }}</h2><p><User :size="14" />{{ course.teacher?.nickname || '教师' }} · {{ course.teacher?.bio || '课程教师' }}</p><progress :value="course.progress_percent || 0" max="100"></progress><div class="course-meta"><span>已学 {{ course.studied_lessons || 0 }}/{{ course.lesson_total || 0 }}</span><span>{{ course.last_lesson ? relativeTime(course.last_progress?.updated_at) : '未开始' }}</span></div><div class="mini-data"><span><MessageCircle :size="14" />{{ course.qa_count || 0 }}</span><span><XCircle :size="14" />{{ course.wrong_count || 0 }}</span><span><Users :size="14" />{{ course.student_count || 0 }}</span></div><button class="btn btn-primary full" @click="openCourse(course.id)"><Play :size="16" />继续学习</button></section>
              </article>
            </div>
            <EmptyState v-if="!filteredCourses.length" text="暂无课程" />
          </template>

          <template v-else-if="active === 'studentCourseHome'">
            <CourseRequired v-if="!courseHome.course" />
            <template v-else>
              <article class="course-hero-student" :style="{ background: courseGradient(courseHome.course.id) }">
                <section><h1>{{ courseHome.course.name }}</h1><p><User :size="16" />{{ courseHome.teacher?.nickname || '教师' }} · {{ courseHome.course.term }}</p><div><Check :size="16" />已完成 {{ courseHome.stats?.completion_rate || 0 }}% <progress :value="courseHome.stats?.completion_rate || 0" max="100"></progress><Users :size="16" />{{ courseHome.student_count || 0 }}名同学</div></section>
                <aside><div class="slide-mini">{{ latestLesson?.title?.slice(0, 8) || '课堂' }}</div><button class="btn white-fill" @click="latestLesson && openLesson(Number(latestLesson.id))"><Play :size="16" />进课堂</button></aside>
              </article>
              <div class="quick-row"><QuickTile :icon="Presentation" label="课堂学习" :sub="`${courseHome.lessons?.length || 0} 个课堂`" @click="scrollToLessons" /><QuickTile :icon="MessageCircle" label="知识问答" sub="AI 解答" @click="go('studentQa')" /><QuickTile :icon="FolderOpen" label="课程资料" :sub="`${courseHome.materials?.length || 0} 份文件`" @click="courseSection = 'materials'" /><QuickTile :icon="ClipboardList" label="章节练习" sub="自选练习" @click="go('studentQuizzes')" /></div>
              <div class="course-layout">
                <section>
                  <article id="lesson-list" class="panel-card"><div class="section-head"><h2><Presentation :size="18" />课堂列表</h2><span class="tag">全部 {{ courseHome.lessons?.length || 0 }}</span></div><LessonItem v-for="(lesson, index) in courseHome.lessons || []" :key="lesson.id" :lesson="lesson" :index="Number(index)" @open="openLesson(Number(lesson.id))" /></article>
                  <article class="panel-card"><div class="section-head"><h2><FolderOpen :size="18" />课程资料</h2><button @click="materialsExpanded = !materialsExpanded">{{ materialsExpanded ? '收起' : '展开' }}</button></div><MaterialRow v-for="item in visibleCourseMaterials" :key="item.id" :item="item" /><button v-if="(courseHome.materials || []).length > 5" class="ghost-row" @click="materialsExpanded = !materialsExpanded"><ChevronDown :size="16" />{{ materialsExpanded ? '收起' : `展开更多` }}</button></article>
                </section>
                <aside>
                  <article class="panel-card"><div class="section-head"><h2><BarChart2 :size="18" />我的数据</h2></div><div class="data-grid"><MiniMetric :icon="Clock" label="学习时长" :value="`${courseHome.stats?.study_hours || 0}h`" /><MiniMetric :icon="CheckCircle" label="完成进度" :value="`${courseHome.stats?.completion_rate || 0}%`" tone="success" /><MiniMetric :icon="MessageCircle" label="问答次数" :value="courseHome.stats?.qa_count || 0" tone="ai" /><MiniMetric :icon="XCircle" label="错题数" :value="courseHome.stats?.wrong_count || 0" tone="danger" /><MiniMetric :icon="Star" label="正确率" :value="`${courseHome.stats?.accuracy || 0}%`" tone="warning" /><MiniMetric :icon="Zap" label="连续打卡" :value="`${courseHome.stats?.streak_days || 0}天`" tone="warning" /></div></article>
                  <article class="ask-card"><Sparkles :size="20" /><h2>向 AI 提问</h2><form @submit.prevent="askCourseQuick"><input v-model="quickCourseQuestion" placeholder="这节课有什么不懂的..." /><button><Send :size="16" /></button></form><div class="quick-tags"><button v-for="item in courseHome.quick_questions || []" :key="item" @click="sendCourseQuick(item)">{{ item }}</button></div></article>
                  <article class="panel-card"><div class="section-head"><h2><MessageCircle :size="18" />最近提问</h2><button @click="go('studentQa')">全部</button></div><div v-for="item in courseHome.recent_qa || []" :key="item.id" class="qa-mini"><strong>{{ item.question }}</strong><p>{{ item.answer }}</p></div><EmptyState v-if="!(courseHome.recent_qa || []).length" text="暂无提问" /></article>
                </aside>
              </div>
            </template>
          </template>

          <template v-else-if="active === 'studentQa'">
            <section class="qa-page">
              <div class="qa-top"><div><Sparkles :size="22" /><section><h1>课程知识问答</h1><p>与 AI 探讨课程问题</p></section></div><div class="qa-tools"><CourseSelect /><button class="top-icon" @click="historyOpen = true"><Clock :size="17" /></button><button class="top-icon" @click="showFavorites = !showFavorites"><BookMarked :size="17" /></button></div></div>
              <div v-if="!globalMessages.length" class="qa-welcome"><Sparkles :size="48" /><h2>你好，我是 AI 学习助手</h2><p>基于课程资料为你解答疑问</p><div class="prompt-grid"><button v-for="item in promptCards" :key="item.text" @click="sendGlobalQuick(item.text)"><component :is="item.icon" :size="18" />{{ item.text }}</button></div></div>
              <ChatList v-else :messages="globalMessages" :thinking="globalThinking" large @toggle-thought="toggleThought" @copy="copyText" @favorite="favoriteQaMessage" @feedback="feedbackQaMessage" />
              <form class="qa-fixed" @submit.prevent="askGlobal"><div><BookOpen :size="14" />正在基于《{{ activeCourse?.name || '课程' }}》</div><section><textarea v-model="globalQuestion" placeholder="有什么不明白的？可以随时问我..." rows="1"></textarea><button :disabled="!globalQuestion.trim() || globalThinking" class="send-btn"><Send :size="18" /></button></section><small>AI 回答仅供学习参考</small></form>
              <transition name="drawer"><aside v-if="historyOpen" class="history-drawer"><div class="drawer-head"><h2>问答历史</h2><button @click="historyOpen = false"><X :size="16" /></button></div><div class="pretty-input"><Search :size="15" /><input v-model="qaKeyword" placeholder="搜索历史问答" @keyup.enter="loadQaHistory" /></div><label class="check-line"><input v-model="showFavorites" type="checkbox" />仅看收藏</label><button v-for="item in filteredQaHistory" :key="item.id" class="history-row" @click="reuseHistory(item)"><MessageCircle :size="13" /><span>{{ item.question }}</span><small>{{ formatTime(item.created_at) }}</small></button></aside></transition>
            </section>
          </template>

          <template v-else-if="active === 'studentTutoring'">
            <PageTitle title="题目辅导" sub="AI 带你一步步理解"><span class="tag tag-ai">文字 · 图片</span></PageTitle>
            <div class="tutoring-grid">
              <section class="panel-card tutor-input"><div class="seg-tabs"><button :class="{ active: problemMode === 'text' }" @click="problemMode = 'text'"><Type :size="16" />文字输入</button><button :class="{ active: problemMode === 'image' }" @click="problemMode = 'image'"><Camera :size="16" />图片上传</button></div><textarea v-if="problemMode === 'text'" v-model="problemText" maxlength="500" placeholder="在这里粘贴或输入题目..." class="problem-text"></textarea><label v-else class="image-drop"><Camera :size="36" /><span>拍照或截图上传题目</span><input ref="problemFile" type="file" accept="image/*" @change="createImageProblem" /></label><small>{{ problemText.length }} / 500字</small><div v-if="activeProblem" class="knowledge-box"><Sparkles :size="14" />识别到：<span v-for="item in activeProblem.knowledge_points || []" :key="item" class="tag tag-primary">{{ item }}</span></div><button class="btn btn-ai full" @click="problemMode === 'text' ? createTextProblem() : problemFile?.click()"><Sparkles :size="16" />开始辅导</button></section>
              <aside class="panel-card guide-card"><div class="section-head"><h2><Sparkles :size="18" />{{ activeProblem ? 'AI 辅导进行中' : '等待题目输入' }}</h2></div><EmptyGuide v-if="!activeProblem" /><GuideStep v-for="level in [1,2,3]" v-else :key="level" :level="level" :data="guidance[level]" :open="guideOpen[level]" @toggle="toggleGuide(level)" @load="loadGuidance(level)" /></aside>
            </div>
            <HistoryStrip title="历史辅导记录" :items="problemHistory" @pick="selectProblem" />
          </template>

          <template v-else-if="active === 'studentKnowledge'">
            <PageTitle title="知识点精讲" sub="按需深入学习"><CourseSelect /></PageTitle>
            <div class="knowledge-layout"><aside class="knowledge-tree"><div class="pretty-input"><Search :size="15" /><input v-model="knowledgeKeyword" placeholder="搜索知识点" /></div><button v-for="chapter in courseHome.chapters || []" :key="chapter.id" @click="selectedChapterId = chapter.id; loadKnowledge()"><ChevronRight :size="14" />{{ chapter.title }}</button><div class="weak-tags"><strong><Zap :size="14" />薄弱知识点</strong><span v-for="item in weakPoints.slice(0, 3)" :key="item.knowledge_point" class="tag tag-danger">{{ item.knowledge_point }}</span></div></aside><section class="knowledge-content"><article class="knowledge-head"><h1>{{ selectedKnowledge?.name || '选择知识点' }}</h1><p>所属：{{ chapterName(selectedKnowledge?.chapter_id) }}</p><span class="tag" :class="knowledgeMasteryClass">{{ knowledgeMasteryText }}</span><progress :value="knowledgeMastery" max="100"></progress></article><div class="segmented"><button v-for="item in levelItems" :key="item.value" type="button" :class="{ active: knowledgeLevel === item.value }" @click="knowledgeLevel = String(item.value)">{{ item.label }}</button></div><article class="knowledge-body"><KnowledgeBlock icon="Quote" title="定义" :content="knowledgeContent.definition" /><KnowledgeBlock icon="Layers" title="核心原理" :content="knowledgeContent.principle" ai /><KnowledgeBlock icon="Pencil" title="例题解析" :content="knowledgeContent.example" /><KnowledgeBlock icon="AlertTriangle" title="常见易错点" :content="knowledgeContent.common_mistake" warning /><div class="practice-cta"><Sparkles :size="16" />基于此知识点生成练习题<button @click="generateKnowledgeQuiz(5)">练习5题</button><button @click="generateKnowledgeQuiz(10)">练习10题</button></div></article></section></div>
          </template>

          <template v-else-if="active === 'studentQuizzes'">
            <PageTitle title="练习与测验" sub="课程测验与章节练习"><CourseSelect /></PageTitle>
            <div v-if="answeringQuiz" class="answer-page"><QuizAnswerView :quiz="quizDetail" :answers="quizAnswers" :attempt="attempt" @answer="setQuizAnswer" @submit="submitQuiz" @exit="answeringQuiz = false" /></div>
            <template v-else><div class="underline-tabs"><button :class="{ active: quizTab === 'course' }" @click="quizTab = 'course'"><ClipboardList :size="16" />课程测验</button><button :class="{ active: quizTab === 'practice' }" @click="quizTab = 'practice'"><Layers :size="16" />章节练习</button></div><section v-if="quizTab === 'course'" class="quiz-list"><QuizCard v-for="quiz in courseQuizzes" :key="quiz.id" :quiz="quiz" @open="startQuiz(quiz.id)" /><EmptyState v-if="!courseQuizzes.length" text="暂无测验" /></section><section v-else class="practice-maker"><article class="panel-card"><h2><Sparkles :size="18" />自选章节练习</h2><div class="chapter-checks"><button v-for="chapter in courseHome.chapters || []" :key="chapter.id" :class="{ active: selectedPracticeChapters.includes(chapter.id) }" @click="togglePracticeChapter(chapter.id)">{{ chapter.title }}</button></div><div class="segmented"><button v-for="item in quizCountOptions" :key="item" type="button" :class="{ active: quizQuestionCount === item }" @click="quizQuestionCount = item">{{ item }}</button></div><label class="toggle-line"><input v-model="smartQuiz" type="checkbox" />优先薄弱点</label><button class="btn btn-ai full" @click="generateQuiz"><Sparkles :size="16" />生成练习</button></article><article class="panel-card"><h2>最近练习</h2><QuizCard v-for="quiz in practiceQuizzes" :key="quiz.id" :quiz="quiz" @open="startQuiz(quiz.id)" /></article></section></template>
          </template>

          <template v-else-if="active === 'studentWrongBook'">
            <PageTitle title="我的错题本" :sub="`共 ${wrongQuestions.length} 道`"><button class="btn btn-primary" @click="loadWrongPractice"><RefreshCw :size="16" />开始重练</button></PageTitle>
            <article class="wrong-hero"><BookMarked :size="24" /><div><strong>{{ wrongQuestions.length }}</strong><span>错题总数</span></div><div><strong>{{ wrongQuestions.filter((w) => w.wrong_count > 1).length }}</strong><span>待重练</span></div><div><strong>{{ weeklyWrongCount }}</strong><span>本周新增</span></div></article>
            <div class="wrong-layout"><aside class="wrong-tree"><button class="active"><Layers :size="16" />全部错题({{ wrongQuestions.length }})</button><strong>按知识点</strong><button v-for="item in weakPoints" :key="item.knowledge_point">{{ item.knowledge_point }}({{ item.wrong_count }})</button></aside><section class="wrong-list"><div class="wrong-tools"><div class="pretty-input"><Search :size="15" /><input v-model="wrongKeyword" placeholder="搜索题目关键词" /></div><SelectMenu v-model="wrongStatus" :items="wrongStatusOptions" /></div><WrongCard v-for="item in filteredWrongQuestions" :key="item.wrong_question_id" :item="item" @practice="practiceWrong(item)" /><EmptyState v-if="!filteredWrongQuestions.length" text="暂无错题" /></section></div>
          </template>

          <template v-else-if="active === 'studentPlans'">
            <article class="plan-hero"><CalendarCheck :size="28" /><h1>学习计划 & 打卡</h1><div><strong>{{ stats.streak_days || 0 }}</strong><span>连续打卡</span></div><div><strong>{{ monthlyCheckins }}</strong><span>本月打卡</span></div><div><Flame :size="18" /><strong>{{ Math.max(stats.streak_days || 0, 0) }}</strong><span>最长连续</span></div></article>
            <div class="plans-grid"><CalendarCard :checkins="checkinDays" /><article class="panel-card today-tasks"><div class="section-head"><h2><ListChecks :size="18" />今日任务</h2><span>{{ doneTasks }}/{{ todayTasks.length }}</span></div><div v-if="todayTasks.length"><TaskRow v-for="task in todayTasks" :key="task.id" :task="task" @checkin="checkinTask(task.id)" /></div><div v-else class="plan-empty"><Sparkles :size="32" /><h2>今天还没有计划</h2><input v-model="planForm.goal" class="input" placeholder="输入学习目标" /><button class="btn btn-ai full" @click="planModalOpen = true">AI生成</button></div></article><article class="panel-card study-stat"><h2><BarChart2 :size="18" />本周学习</h2><div class="mini-bars"><i v-for="(value, index) in weeklyHours" :key="index" :style="{ height: `${20 + value * 12}px` }"></i></div><p>共 {{ stats.study_hours || 0 }} 小时</p><div class="badge-wall"><span v-for="item in profilePayload.achievements || []" :key="item.key" :class="{ locked: !item.unlocked }"><Award :size="17" />{{ item.unlocked ? item.name : '?' }}</span></div></article></div>
          </template>

          <template v-else-if="active === 'studentProfile'">
            <section class="profile-page"><article class="profile-hero"><span class="big-avatar">{{ firstChar(profileForm.nickname) }}<Camera :size="14" /></span><div><h1>{{ profileForm.nickname }}</h1><p><IdCard :size="14" />{{ user.student_no || '-' }}</p><p><Mail :size="14" />{{ user.email }}</p></div><aside><strong>{{ learningPoints }}</strong><span>学习积分</span></aside></article><div class="achievement-row"><MiniMetric :icon="Clock" label="总学习时长" :value="`${stats.study_hours || 0}h`" /><MiniMetric :icon="CheckCircle" label="课堂完成" :value="`${stats.completion_rate || 0}%`" tone="success" /><MiniMetric :icon="MessageCircle" label="知识问答" :value="stats.qa_count || 0" tone="ai" /><MiniMetric :icon="Star" label="平均得分" :value="`${stats.accuracy || 0}`" tone="warning" /></div><article class="panel-card badge-card"><div class="section-head"><h2><Award :size="18" />我的成就</h2></div><div class="badges"><span v-for="item in profilePayload.achievements || []" :key="item.key" :class="{ locked: !item.unlocked }"><Award :size="22" />{{ item.unlocked ? item.name : '?' }}</span></div></article><div class="profile-tabs"><button :class="{ active: profileTab === 'info' }" @click="profileTab = 'info'">我的资料</button><button :class="{ active: profileTab === 'records' }" @click="profileTab = 'records'">学习档案</button><button :class="{ active: profileTab === 'account' }" @click="profileTab = 'account'">账号设置</button></div><article v-if="profileTab === 'info'" class="panel-card profile-form"><label>姓名<input v-model="profileForm.nickname" class="input" /></label><label>学校<input v-model="profileForm.school" class="input" /></label><label>简介<textarea v-model="profileForm.bio" class="textarea"></textarea></label><button class="btn btn-primary" @click="saveProfile">保存修改</button></article><article v-if="profileTab === 'records'" class="panel-card"><ActivityTimeline :items="profilePayload.activities || []" /></article><article v-if="profileTab === 'account'" class="panel-card profile-form"><h2>账号安全</h2><input v-model="passwordForm.old_password" class="input" type="password" placeholder="当前密码" /><input v-model="passwordForm.new_password" class="input" type="password" placeholder="新密码" /><input v-model="passwordConfirm" class="input" type="password" placeholder="确认密码" /><button class="btn btn-primary" @click="changePassword">确认修改</button><h2>通知设置</h2><label v-for="item in noticeSettings" :key="item.key" class="toggle-line"><input v-model="item.enabled" type="checkbox" />{{ item.label }}<input v-if="item.key === 'plan'" v-model="item.time" class="time-input" type="time" /></label><button class="btn btn-secondary" @click="saveNotices">保存设置</button></article></section>
          </template>

          <template v-else-if="active === 'studentMaterials'">
            <PageTitle title="课程资料" sub="课程文件与讲义"><CourseSelect /></PageTitle>
            <article class="panel-card"><MaterialRow v-for="item in courseHome.materials || []" :key="item.id" :item="item" /><EmptyState v-if="!(courseHome.materials || []).length" text="暂无资料" /></article>
          </template>
        </section>
      </transition>
    </main>

    <nav class="bottom-tabs">
      <button v-for="item in bottomTabs" :key="item.key" :class="{ active: active === item.key, ai: item.key === 'studentQa' }" @click="go(item.key)">
        <span><component :is="item.icon" :size="item.key === 'studentQa' ? 24 : 22" /></span>{{ item.label }}<i></i>
      </button>
    </nav>

    <transition name="modal-pop">
      <div v-if="joinOpen" class="modal-mask">
        <article class="join-modal">
          <div class="modal-head"><PlusCircle :size="22" /><h2>加入新课程</h2><button @click="joinOpen = false"><X :size="16" /></button></div>
          <label>课程码</label>
          <div class="code-input" :class="{ ok: joinPreview && !joinPreview.already_joined, error: joinError }"><input v-model="joinCode" maxlength="12" @input="formatJoinCode" /><Loader2 v-if="joinChecking" :size="18" /><CheckCircle v-if="joinPreview && !joinChecking" :size="18" /><XCircle v-if="joinError" :size="18" /></div>
          <small class="field-error" v-if="joinError">{{ joinError }}</small>
          <article v-if="joinPreview" class="preview-course"><span :style="{ background: courseGradient(joinPreview.course.id) }"><BookOpen :size="20" /></span><div><strong>{{ joinPreview.course.name }}</strong><small>{{ joinPreview.teacher?.nickname || '教师' }} · {{ joinPreview.course.term }} · {{ joinPreview.student_count }}人</small></div></article>
          <div class="hint-line"><Info :size="14" />加入后即可学习课程内容</div>
          <footer><button class="btn btn-ghost" @click="joinOpen = false">取消</button><button class="btn btn-primary" :disabled="!joinPreview || joinPreview.already_joined" @click="confirmJoin">确认加入</button></footer>
        </article>
      </div>
    </transition>

    <transition name="modal-pop">
      <div v-if="planModalOpen" class="modal-mask">
        <article class="join-modal">
          <div class="modal-head"><Sparkles :size="22" /><h2>AI 学习计划</h2><button @click="planModalOpen = false"><X :size="16" /></button></div>
          <textarea v-model="planForm.goal" class="textarea" placeholder="描述你的学习目标"></textarea>
          <div class="form-row"><input v-model.number="planForm.daily_minutes" class="input" type="number" /><input v-model.number="planForm.available_days" class="input" type="number" /></div>
          <div class="stream-preview"><Sparkles :size="16" />AI 将生成今天的学习任务</div>
          <footer><button class="btn btn-ghost" @click="planModalOpen = false">取消</button><button class="btn btn-primary" @click="createPlan">采用计划</button></footer>
        </article>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, Transition, watch, type PropType } from "vue";
import { useRouter } from "vue-router";
import {
  AlertTriangle, ArrowLeft, Award, BarChart2, Bell, BookMarked, BookOpen, CalendarCheck, Camera, Check,
  CheckCircle, ChevronDown, ChevronRight, ClipboardList, Clock, Copy, Cpu, Download, FileText, Flame, FolderOpen, GitBranch, Grid2X2,
  IdCard, Info, Layers, ListChecks, Loader2, LogOut, Mail, Maximize, MessageCircle, MoreHorizontal, PanelRight,
  Pause, Pencil, Play, Plus, PlusCircle, Presentation, Quote, RefreshCw, Search, Send, Settings, SkipBack,
  Shield, SkipForward, Sparkles, Star, Sun, Type, User, Users, Wifi, X, XCircle, Zap
} from "lucide-vue-next";
import { api } from "../api/client";
import { routeByPage } from "../router";
import type { Lesson, LessonPage, Quiz, User as UserType } from "../types";

type ChatMessage = { id: number; role: "user" | "ai"; text: string; sources?: any[]; thought?: string; thoughtOpen?: boolean; record_id?: number; favorite?: boolean; outOfScope?: boolean };

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();
const router = useRouter();

const active = ref(props.pageKey || "studentHome");
const dashboard = ref<any>({});
const profilePayload = ref<any>({});
const courses = ref<any[]>([]);
const courseHome = ref<any>({});
const selectedCourseId = ref<number>(Number(localStorage.getItem("student_current_course_id") || 0));
const notifications = ref<any[]>([]);
const lessons = ref<any[]>([]);
const materialsExpanded = ref(false);
const courseSection = ref("lessons");

const searchOpen = ref(false);
const globalSearch = ref("");
const searchInput = ref<HTMLInputElement | null>(null);
const noticeOpen = ref(false);
const userMenuOpen = ref(false);
const joinOpen = ref(false);
const joinCode = ref("");
const joinPreview = ref<any | null>(null);
const joinChecking = ref(false);
const joinError = ref("");
let joinTimer: number | undefined;

const courseKeyword = ref("");
const termFilter = ref("");
const courseTab = ref<"active" | "done">("active");
const quickCourseQuestion = ref("");

const classroomOpen = ref(false);
const classroomLesson = ref<{ lesson: Lesson; pages: LessonPage[] } | null>(null);
const currentPage = ref(1);
const pageDirection = ref<"next" | "prev">("next");
const classroomTab = ref<"script" | "qa" | "note">("script");
const classMessages = ref<ChatMessage[]>([]);
const classQuestion = ref("");
const classThinking = ref(false);
const classConversationId = ref<number | null>(null);
const aiPanelOpen = ref(true);
const chromeVisible = ref(true);
const thumbOpen = ref(false);
const settingsOpen = ref(false);
const subtitleMode = ref<"full" | "keyword" | "hide">("full");
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlaying = ref(false);
const playbackRate = ref(1);
const audioProgress = ref(0);
const studySeconds = ref(0);
const completeOpen = ref(false);
const pageNote = ref("");
const noteState = ref("已保存");
const noteSavedAt = ref("尚未保存");
let chromeTimer: number | undefined;
let studyTimer: number | undefined;
let noteTimer: number | undefined;

const globalMessages = ref<ChatMessage[]>([]);
const globalQuestion = ref("");
const globalThinking = ref(false);
const globalConversationId = ref<number | null>(null);
const qaHistory = ref<any[]>([]);
const qaKeyword = ref("");
const historyOpen = ref(false);
const showFavorites = ref(false);

const problemMode = ref<"text" | "image">("text");
const problemText = ref("");
const problemFile = ref<HTMLInputElement | null>(null);
const activeProblem = ref<any | null>(null);
const problemHistory = ref<any[]>([]);
const guidance = reactive<Record<number, any>>({});
const guideOpen = reactive<Record<number, boolean>>({ 1: true, 2: false, 3: false });

const knowledge = ref<any[]>([]);
const selectedChapterId = ref<number | null>(null);
const selectedKnowledgeId = ref<number | null>(null);
const knowledgeKeyword = ref("");
const knowledgeLevel = ref("standard");
const weakPoints = ref<any[]>([]);

const quizTab = ref<"course" | "practice">("course");
const quizzes = ref<Quiz[]>([]);
const quizDetail = ref<any | null>(null);
const quizAnswers = reactive<Record<number, any>>({});
const attempt = ref<any | null>(null);
const answeringQuiz = ref(false);
const selectedPracticeChapters = ref<number[]>([]);
const quizQuestionCount = ref("10题");
const smartQuiz = ref(true);

const wrongQuestions = ref<any[]>([]);
const wrongKeyword = ref("");
const wrongStatus = ref("");

const plans = ref<any[]>([]);
const tasks = ref<any[]>([]);
const planModalOpen = ref(false);
const planForm = reactive({ title: "今日学习计划", goal: "", available_days: 7, daily_minutes: 60 });
const checkinDays = ref<string[]>([]);

const profileTab = ref<"info" | "records" | "account">("info");
const profileForm = reactive({ nickname: props.user.nickname, avatar_url: props.user.avatar_url || "", school: "", bio: props.user.bio || "" });
const passwordForm = reactive({ old_password: "", new_password: "" });
const passwordConfirm = ref("");
const noticeSettings = reactive<any[]>([]);

const bottomTabs = [
  { key: "studentHome", label: "首页", icon: BookOpen },
  { key: "studentCourses", label: "我的课程", icon: BookOpen },
  { key: "studentQa", label: "AI 问答", icon: Sparkles },
  { key: "studentWrongBook", label: "错题本", icon: BookMarked },
  { key: "studentProfile", label: "我的", icon: User }
];
const speedItems = ["0.5", "0.75", "1", "1.25", "1.5", "2"].map((value) => ({ label: `${value}x`, value }));
const promptCards = [
  { text: "OSI七层模型是什么？", icon: Layers },
  { text: "TCP和UDP有什么区别？", icon: Zap },
  { text: "路由算法有哪几种？", icon: GitBranch },
  { text: "HTTPS如何保证安全？", icon: Shield },
  { text: "什么是ARP协议？", icon: Cpu },
  { text: "什么是流量控制？", icon: Wifi }
];
const levelItems = [{ label: "入门", value: "beginner" }, { label: "标准", value: "standard" }, { label: "进阶", value: "advanced" }];
const quizCountOptions = ["5题", "10题", "15题", "20题"];
const wrongStatusOptions = [{ label: "全部状态", value: "" }, { label: "待重练", value: "todo" }, { label: "已掌握", value: "done" }];
const courseMenuItems = [{ label: "课程详情", value: "detail" }, { label: "问答记录", value: "qa" }, { label: "分享课程码", value: "share" }, { label: "退出课程", value: "leave", danger: true }];

const stats = computed(() => dashboard.value.stats || profilePayload.value.stats || {});
const todayTasks = computed(() => dashboard.value.today_tasks || tasks.value || []);
const doneTasks = computed(() => todayTasks.value.filter((task: any) => task.status === "done").length);
const todayDoneRate = computed(() => todayTasks.value.length ? Math.round(doneTasks.value / todayTasks.value.length * 100) : 0);
const continueLesson = computed(() => dashboard.value.continue_learning || null);
const continueProgress = computed(() => continueLesson.value?.progress?.progress_percent || 0);
const continueProgressPage = computed(() => continueLesson.value?.progress?.current_page || 1);
const continueTime = computed(() => continueLesson.value?.progress?.updated_at ? `上次学习：${relativeTime(continueLesson.value.progress.updated_at)}` : "从第一节开始");
const hourTargetRate = computed(() => Math.min(100, Math.round((stats.value.study_hours || 0) / 5 * 100)));
const unreadCount = computed(() => notifications.value.filter((item) => item.unread).length);
const activities = computed(() => dashboard.value.activities || []);
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" }));
const termLeftDays = computed(() => Math.max(1, Math.ceil((new Date(new Date().getFullYear(), 6, 15).getTime() - Date.now()) / 86400000)));
const activeCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value) || courses.value[0] || null);
const termOptions = computed(() => [{ label: "全部学期", value: "" }, ...Array.from(new Set(courses.value.map((course) => course.term))).filter(Boolean).map((term: any) => ({ label: term, value: term }))]);
const activeCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) < 100));
const doneCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) >= 100));
const filteredCourses = computed(() => (courseTab.value === "active" ? activeCourses.value : doneCourses.value).filter((course) => (!courseKeyword.value || course.name.includes(courseKeyword.value)) && (!termFilter.value || course.term === termFilter.value)));
const latestLesson = computed(() => (courseHome.value.lessons || [])[0] || null);
const visibleCourseMaterials = computed(() => materialsExpanded.value ? courseHome.value.materials || [] : (courseHome.value.materials || []).slice(0, 5));
const activePage = computed(() => classroomLesson.value?.pages.find((page) => page.page_number === currentPage.value) || classroomLesson.value?.pages[0] || null);
const subtitleLead = computed(() => (activePage.value?.subtitle_text || "").slice(0, 8));
const subtitleRest = computed(() => (activePage.value?.subtitle_text || "").slice(8));
const quickPageQuestions = computed(() => ["这页重点？", "举个例子", "出道题", "总结一下"]);
const studyClock = computed(() => `${String(Math.floor(studySeconds.value / 60)).padStart(2, "0")}:${String(studySeconds.value % 60).padStart(2, "0")}`);
const audioTime = computed(() => timeLabel(audioRef.value?.currentTime || 0));
const audioDuration = computed(() => timeLabel(audioRef.value?.duration || activePage.value?.audio_duration_seconds || 0));
const completionSummary = computed(() => "本次学习完成度良好，建议继续完成配套练习并整理课堂笔记。");
const filteredQaHistory = computed(() => qaHistory.value.filter((item) => (!showFavorites.value || item.is_favorite) && (!qaKeyword.value || item.question.includes(qaKeyword.value))));
const selectedKnowledge = computed(() => knowledge.value.find((item) => item.id === selectedKnowledgeId.value) || knowledge.value[0] || null);
const knowledgeMastery = computed(() => Math.max(35, 90 - (weakPoints.value.find((item) => item.knowledge_point === selectedKnowledge.value?.name)?.wrong_count || 0) * 12));
const knowledgeMasteryText = computed(() => knowledgeMastery.value > 75 ? "已掌握" : knowledgeMastery.value > 55 ? "待加强" : "薄弱");
const knowledgeMasteryClass = computed(() => knowledgeMastery.value > 75 ? "tag-success" : knowledgeMastery.value > 55 ? "tag-warning" : "tag-danger");
const knowledgeContent = computed(() => selectedKnowledge.value?.content_by_level?.[knowledgeLevel.value] || {});
const courseQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type === "course"));
const practiceQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type !== "course"));
const filteredWrongQuestions = computed(() => wrongQuestions.value.filter((item) => (!wrongKeyword.value || item.question.stem.includes(wrongKeyword.value)) && (!wrongStatus.value || (wrongStatus.value === "todo" ? item.wrong_count > 0 : item.wrong_count <= 0))));
const weeklyWrongCount = computed(() => wrongQuestions.value.filter((item) => item.question?.updated_at && Date.now() - new Date(item.question.updated_at).getTime() < 7 * 86400000).length);
const monthlyCheckins = computed(() => checkinDays.value.filter((day) => day.slice(0, 7) === new Date().toISOString().slice(0, 7)).length);
const weeklyHours = computed(() => [0.8, 1.2, 1.6, 1.1, 2.2, 0.7, 1.4]);
const learningPoints = computed(() => Math.round((stats.value.study_hours || 0) * 10 + (stats.value.qa_count || 0) * 2 + (stats.value.completion_rate || 0)));
const weekDays = computed(() => ["一", "二", "三", "四", "五", "六", "日"].map((label, index) => ({ label, done: index < Math.min(7, stats.value.streak_days || 0), today: index === new Date().getDay() - 1 })));

watch(() => props.pageKey, async (key) => { active.value = key || "studentHome"; await loadActive(); });
watch(selectedCourseId, (id) => { if (id) localStorage.setItem("student_current_course_id", String(id)); });
watch(activePage, async (page) => { if (page) await loadNote(page.id); }, { immediate: false });

async function run<T>(task: () => Promise<T>, ok?: string) { try { const data = await task(); if (ok) emit("notice", "success", ok); return data; } catch (error) { emit("notice", "error", (error as Error).message); return null; } }
async function go(key: string) { await router.push(routeByPage[key] || "/home"); }
async function loadCourses() { courses.value = (await run<any[]>(() => api.get("/student/courses"))) || []; if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id; }
async function loadDashboard() { dashboard.value = (await run(() => api.get("/student/dashboard"))) || {}; notifications.value = dashboard.value.notifications || []; courses.value = dashboard.value.courses || courses.value; if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id; }
async function loadCourseHome() { if (!selectedCourseId.value) return; courseHome.value = (await run(() => api.get(`/student/courses/${selectedCourseId.value}/home`))) || {}; lessons.value = courseHome.value.lessons || []; }
async function loadProfile() { profilePayload.value = (await run(() => api.get("/student/profile"))) || {}; Object.assign(profileForm, { nickname: profilePayload.value.user?.nickname || props.user.nickname, avatar_url: profilePayload.value.user?.avatar_url || "", school: profilePayload.value.student_profile?.school || "", bio: profilePayload.value.user?.bio || "" }); noticeSettings.splice(0, noticeSettings.length, ...(profilePayload.value.notification_settings || [])); }
async function loadActive() { if (active.value === "studentHome") await loadDashboard(); if (active.value === "studentCourses") await loadCourses(); if (["studentCourseHome", "studentMaterials"].includes(active.value)) await loadCourseHome(); if (active.value === "studentQa") await loadQaHistory(); if (active.value === "studentTutoring") await loadProblemHistory(); if (active.value === "studentKnowledge") await loadKnowledge(); if (active.value === "studentQuizzes") await loadQuizPage(); if (active.value === "studentWrongBook") await loadWrongBook(); if (active.value === "studentPlans") await loadPlans(); if (active.value === "studentProfile") await loadProfile(); }
async function openCourse(id: number) { selectedCourseId.value = id; await loadCourseHome(); await go("studentCourseHome"); }
function scrollToLessons() { document.getElementById("lesson-list")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
async function openSearch() { searchOpen.value = true; await nextTick(); searchInput.value?.focus(); }
function firstChar(value?: string) { return (value || "-").slice(0, 1); }
function courseGradient(id = 1) { const items = ["linear-gradient(135deg,#4F46E5,#06B6D4)", "linear-gradient(135deg,#10B981,#3B82F6)", "linear-gradient(135deg,#F59E0B,#EF4444)", "linear-gradient(135deg,#8B5CF6,#EC4899)"]; return items[id % items.length]; }
function relativeTime(value?: string | null) { if (!value) return "刚刚"; const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000)); if (seconds < 60) return "刚刚"; if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`; if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`; return `${Math.floor(seconds / 86400)}天前`; }
function formatTime(value?: string | null) { return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"; }
function timeLabel(value: number) { if (!Number.isFinite(value)) return "00:00"; return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(Math.floor(value % 60)).padStart(2, "0")}`; }
function copyText(text: string) { navigator.clipboard?.writeText(text); emit("notice", "success", "已复制"); }
function chapterName(id?: number | null) { return (courseHome.value.chapters || []).find((item: any) => item.id === id)?.title || "课程章节"; }

function formatJoinCode() { joinCode.value = joinCode.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12); joinPreview.value = null; joinError.value = ""; if (joinTimer) window.clearTimeout(joinTimer); if (joinCode.value.length >= 5) joinTimer = window.setTimeout(validateJoinCode, 350); }
async function validateJoinCode() { joinChecking.value = true; joinError.value = ""; const data = await run<any>(() => api.get("/student/courses/preview", { course_code: joinCode.value })); joinChecking.value = false; if (!data) { joinError.value = "课程码不存在或已停用"; return; } joinPreview.value = data; if (data.already_joined) joinError.value = "你已加入该课程"; }
async function confirmJoin() { if (!joinPreview.value) return; await run(() => api.post("/courses/join", { course_code: joinCode.value }), "已加入"); joinOpen.value = false; joinCode.value = ""; joinPreview.value = null; await loadDashboard(); }
async function handleCourseMenu(action: string, course: any) { if (action === "detail") await openCourse(course.id); if (action === "qa") { selectedCourseId.value = course.id; await go("studentQa"); } if (action === "share") copyText(course.course_code); if (action === "leave") await run(() => api.post(`/courses/${course.id}/leave`), "已退出"); await loadCourses(); }

async function openLesson(id: number) { const detail = await run<{ lesson: Lesson; pages: LessonPage[] }>(() => api.get(`/lessons/${id}`)); if (!detail) return; classroomLesson.value = detail; currentPage.value = 1; classMessages.value = []; classConversationId.value = null; classroomOpen.value = true; completeOpen.value = false; studySeconds.value = 0; startStudyClock(); const progress = await run<any>(() => api.get(`/lessons/${id}/progress`)); if (progress?.current_page) currentPage.value = progress.current_page; await loadNote(activePage.value?.id || 0); }
async function closeClassroom() { await saveProgress(false, true); stopStudyClock(); classroomOpen.value = false; audioPlaying.value = false; classroomLesson.value = null; await loadDashboard(); }
function revealChrome() { chromeVisible.value = true; if (chromeTimer) window.clearTimeout(chromeTimer); chromeTimer = window.setTimeout(() => { if (audioPlaying.value) chromeVisible.value = false; }, 3000); }
function startStudyClock() { stopStudyClock(); studyTimer = window.setInterval(() => { studySeconds.value += 1; }, 1000); }
function stopStudyClock() { if (studyTimer) window.clearInterval(studyTimer); studyTimer = undefined; }
async function jumpPage(page: number) { pageDirection.value = page >= currentPage.value ? "next" : "prev"; currentPage.value = page; thumbOpen.value = false; await saveProgress(false, true); }
async function nextPage() { await jumpPage(Math.min(classroomLesson.value?.pages.length || 1, currentPage.value + 1)); }
async function firstPage() { await jumpPage(1); }
async function saveProgress(completed: boolean, silent = false) { if (!classroomLesson.value) return; await run(() => api.post(`/lessons/${classroomLesson.value!.lesson.id}/progress`, { current_page: currentPage.value, added_seconds: 30, completed }), silent ? undefined : "已保存"); }
async function toggleAudio() { if (!audioRef.value) return; audioRef.value.playbackRate = playbackRate.value; if (audioRef.value.paused) await audioRef.value.play(); else audioRef.value.pause(); revealChrome(); }
function setRate(value: string) { playbackRate.value = Number(value); if (audioRef.value) audioRef.value.playbackRate = playbackRate.value; }
function updateAudio() { if (!audioRef.value) return; audioProgress.value = audioRef.value.duration ? Math.round(audioRef.value.currentTime / audioRef.value.duration * 100) : 0; }
function seekAudio() { if (audioRef.value?.duration) audioRef.value.currentTime = audioRef.value.duration * audioProgress.value / 100; }
async function handleAudioEnded() { if (!classroomLesson.value) return; if (currentPage.value >= classroomLesson.value.pages.length) { await saveProgress(true, true); completeOpen.value = true; } else await nextPage(); }
async function loadNote(pageId: number) { if (!pageId) return; const note = await run<any>(() => api.get(`/student/pages/${pageId}/note`)); pageNote.value = note?.content || ""; noteState.value = "已保存"; noteSavedAt.value = note?.updated_at ? `上次保存：${relativeTime(note.updated_at)}` : "尚未保存"; }
function queueNoteSave() { noteState.value = "未保存"; if (noteTimer) window.clearTimeout(noteTimer); noteTimer = window.setTimeout(saveCurrentNote, 1200); }
async function saveCurrentNote() { if (!activePage.value) return; noteState.value = "保存中"; const note = await run<any>(() => api.put(`/student/pages/${activePage.value!.id}/note`, { content: pageNote.value })); if (note) { noteState.value = "已保存"; noteSavedAt.value = `上次保存：${relativeTime(note.updated_at)}`; } }
function confettiStyle(n: number) { return { left: `${(n * 37) % 100}%`, background: ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EF4444"][n % 5], animationDelay: `${(n % 8) * 0.05}s` }; }
function nextLessonAfterComplete() { const index = (courseHome.value.lessons || []).findIndex((item: any) => item.id === classroomLesson.value?.lesson.id); const next = (courseHome.value.lessons || [])[index + 1]; if (next) openLesson(next.id); else returnCourse(); }
function returnCourse() { completeOpen.value = false; closeClassroom(); }

async function askInClass() { if (!classQuestion.value.trim() || !classroomLesson.value) return; const question = classQuestion.value; classQuestion.value = ""; classMessages.value.push({ id: Date.now(), role: "user", text: question }); classThinking.value = true; const data = await run<any>(() => api.post("/qa/ask", { course_id: classroomLesson.value!.lesson.course_id, conversation_id: classConversationId.value, lesson_page_id: activePage.value?.id, question })); classThinking.value = false; if (data) { classConversationId.value = data.conversation_id; classMessages.value.push({ id: Date.now() + 1, role: "ai", text: data.answer, sources: data.sources || [], thought: "已检索当前页、课程资料和历史上下文。", record_id: data.record_id, outOfScope: data.is_out_of_scope }); } }
function sendQuickClass(text: string) { classQuestion.value = text; askInClass(); }
async function askGlobal() { if (!globalQuestion.value.trim() || !selectedCourseId.value) return; const question = globalQuestion.value; globalQuestion.value = ""; globalMessages.value.push({ id: Date.now(), role: "user", text: question }); globalThinking.value = true; const data = await run<any>(() => api.post("/qa/ask", { course_id: selectedCourseId.value, conversation_id: globalConversationId.value, question })); globalThinking.value = false; if (data) { globalConversationId.value = data.conversation_id; globalMessages.value.push({ id: Date.now() + 1, role: "ai", text: data.answer, sources: data.sources || [], thought: "已检索课程知识库并整理答案结构。", record_id: data.record_id, outOfScope: data.is_out_of_scope }); await loadQaHistory(); } }
function sendGlobalQuick(text: string) { globalQuestion.value = text; askGlobal(); }
async function sendCourseQuick(text: string) { quickCourseQuestion.value = text; await askCourseQuick(); }
async function askCourseQuick() { if (!quickCourseQuestion.value.trim()) return; globalQuestion.value = quickCourseQuestion.value; quickCourseQuestion.value = ""; await go("studentQa"); await askGlobal(); }
async function loadQaHistory() { if (!selectedCourseId.value) return; qaHistory.value = (await run<any[]>(() => api.get("/qa/history", { course_id: selectedCourseId.value, keyword: qaKeyword.value }))) || []; }
function reuseHistory(item: any) { historyOpen.value = false; globalMessages.value = [{ id: item.id * 2, role: "user", text: item.question }, { id: item.id * 2 + 1, role: "ai", text: item.answer, sources: item.sources || [], record_id: item.id, favorite: item.is_favorite }]; }
function toggleThought(message: ChatMessage) { message.thoughtOpen = !message.thoughtOpen; }
async function favoriteQaMessage(message: ChatMessage) { if (!message.record_id) return; await run(() => api.post(`/qa/${message.record_id}/favorite`, { is_favorite: !message.favorite }), "已收藏"); message.favorite = !message.favorite; }
async function feedbackQaMessage(message: ChatMessage, feedback = "positive") { if (!message.record_id) return; await run(() => api.post(`/qa/${message.record_id}/feedback`, { feedback }), "已评价"); }

async function createTextProblem() { if (!selectedCourseId.value || !problemText.value.trim()) return; activeProblem.value = await run<any>(() => api.post("/tutoring/problems/text", { course_id: selectedCourseId.value, text: problemText.value }), "已提交"); await loadProblemHistory(); if (activeProblem.value) await loadGuidance(1); }
async function createImageProblem(event: Event) { const file = ((event.target as HTMLInputElement).files || [])[0]; if (!file || !selectedCourseId.value) return; const form = new FormData(); form.set("course_id", String(selectedCourseId.value)); form.set("file", file); activeProblem.value = await run<any>(() => api.post("/tutoring/problems/image", form), "已识别"); problemText.value = activeProblem.value?.ocr_text || ""; await loadProblemHistory(); }
async function loadProblemHistory() { problemHistory.value = (await run<any[]>(() => api.get("/tutoring/history", { course_id: selectedCourseId.value || undefined }))) || []; }
function selectProblem(item: any) { activeProblem.value = item; problemText.value = item.corrected_text || item.ocr_text || item.raw_text || ""; guideOpen[1] = true; }
async function loadGuidance(level: number) { if (!activeProblem.value) return; guidance[level] = await run(() => api.get(`/tutoring/problems/${activeProblem.value.id}/guidance`, { level })); guideOpen[level] = true; }
async function toggleGuide(level: number) { if (!guidance[level]) await loadGuidance(level); else guideOpen[level] = !guideOpen[level]; }

async function loadKnowledge() { if (!selectedCourseId.value) return; knowledge.value = (await run<any[]>(() => api.get("/learning/knowledge-points", { course_id: selectedCourseId.value, chapter_id: selectedChapterId.value || undefined }))) || []; if (!selectedKnowledgeId.value && knowledge.value[0]) selectedKnowledgeId.value = knowledge.value[0].id; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); }
async function generateKnowledgeQuiz(count: number) { if (!selectedCourseId.value) return; await run(() => api.post("/learning/quizzes/generate", { course_id: selectedCourseId.value, chapter_id: selectedKnowledge.value?.chapter_id || undefined, title: `${selectedKnowledge.value?.name || '知识点'}练习`, quiz_type: "practice", question_count: count }), "已生成"); await go("studentQuizzes"); }

async function loadQuizPage() { if (!selectedCourseId.value) return; quizzes.value = (await run<Quiz[]>(() => api.get("/learning/quizzes", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); }
async function generateQuiz() { if (!selectedCourseId.value) return; const count = Number(quizQuestionCount.value.replace("题", "")); const chapter_id = selectedPracticeChapters.value[0] || selectedChapterId.value || undefined; await run(() => api.post("/learning/quizzes/generate", { course_id: selectedCourseId.value, chapter_id, title: "章节练习", quiz_type: "practice", question_count: count }), "已生成"); await loadQuizPage(); }
async function startQuiz(id: number) { quizDetail.value = await run(() => api.get(`/learning/quizzes/${id}`)); Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]); attempt.value = null; answeringQuiz.value = true; }
function setQuizAnswer(questionId: number, answer: any) { quizAnswers[questionId] = answer; }
async function submitQuiz() { if (!quizDetail.value) return; const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer })); attempt.value = await run(() => api.post(`/learning/quizzes/${quizDetail.value.quiz.id}/submit`, { answers }), "已提交"); await loadWrongBook(); }
function togglePracticeChapter(id: number) { selectedPracticeChapters.value = selectedPracticeChapters.value.includes(id) ? selectedPracticeChapters.value.filter((item) => item !== id) : [...selectedPracticeChapters.value, id]; }

async function loadWrongBook() { if (!selectedCourseId.value) return; wrongQuestions.value = (await run<any[]>(() => api.get("/learning/wrong-questions", { course_id: selectedCourseId.value }))) || []; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; }
async function loadWrongPractice() { if (!selectedCourseId.value) return; const quiz = await run<Quiz>(() => api.post("/learning/wrong-questions/practice", undefined, { course_id: selectedCourseId.value }), "已生成"); if (quiz) { await loadQuizPage(); await startQuiz(quiz.id); await go("studentQuizzes"); } }
function practiceWrong(_: any) { loadWrongPractice(); }

async function loadPlans() { plans.value = (await run<any[]>(() => api.get("/learning/plans", { course_id: selectedCourseId.value || undefined }))) || []; if (plans.value[0]) tasks.value = (await run<any[]>(() => api.get(`/learning/plans/${plans.value[0].id}/tasks`))) || []; checkinDays.value = todayTasks.value.filter((task: any) => task.status === "done").map(() => new Date().toISOString().slice(0, 10)); await loadProfile(); }
async function createPlan() { if (!selectedCourseId.value) return; const data = await run<any>(() => api.post("/learning/plans", { ...planForm, course_id: selectedCourseId.value }), "已生成"); if (data) { planModalOpen.value = false; tasks.value = data.tasks || []; await loadDashboard(); } }
async function checkinTask(id: number) { await run(() => api.post(`/learning/tasks/${id}/checkin`, { notes: "" }), "已打卡"); await loadDashboard(); await loadPlans(); }

async function saveProfile() { const data = await run<any>(() => api.patch("/student/profile", { nickname: profileForm.nickname, avatar_url: profileForm.avatar_url, bio: profileForm.bio, school: profileForm.school }), "已保存"); if (data) profilePayload.value = data; }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); await run(() => api.post("/auth/me/password", passwordForm), "已保存"); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }
async function saveNotices() { await run(() => api.put("/student/notifications", { settings: noticeSettings }), "已保存"); }

type SelectOption = { label: string; value: string | number; danger?: boolean };
function normalizeItems(items: unknown[]): SelectOption[] {
  return items.map((item) => (typeof item === "string" ? { label: item, value: item } : item as SelectOption));
}
function optionText(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  return typeof value === "number" ? String(value) : String(value);
}
function statusText(value: string) {
  const map: Record<string, string> = { published: "已发布", review: "待审核", draft: "草稿", active: "正常", done: "已完成", pending: "待处理" };
  return map[value] || value || "-";
}

const PageTitle = defineComponent({
  props: { title: { type: String, required: true }, sub: { type: String, default: "" } },
  setup(p, { slots }) {
    return () => h("div", { class: "page-title-row" }, [
      h("div", [h("h1", p.title), p.sub ? h("p", p.sub) : null]),
      h("div", { class: "page-title-actions" }, slots.default?.())
    ]);
  }
});

const RingProgress = defineComponent({
  props: { value: { type: Number, default: 0 }, tone: { type: String, default: "primary" } },
  setup(p) {
    return () => {
      const value = Math.max(0, Math.min(100, Number(p.value || 0)));
      const stroke = p.tone === "success" ? "#10B981" : p.tone === "ai" ? "#8B5CF6" : "#4F46E5";
      const radius = 28;
      const circumference = 2 * Math.PI * radius;
      return h("svg", { width: 72, height: 72, viewBox: "0 0 72 72", style: { transform: "rotate(-90deg)" } }, [
        h("circle", { cx: 36, cy: 36, r: radius, fill: "none", stroke: "rgba(148,163,184,.22)", "stroke-width": 8 }),
        h("circle", {
          cx: 36,
          cy: 36,
          r: radius,
          fill: "none",
          stroke,
          "stroke-linecap": "round",
          "stroke-width": 8,
          "stroke-dasharray": circumference,
          "stroke-dashoffset": circumference * (1 - value / 100)
        })
      ]);
    };
  }
});

const RingBlock = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: Number, default: 0 },
    text: { type: String, required: true },
    sub: { type: String, default: "" },
    tone: { type: String, default: "primary" }
  },
  setup(p) {
    return () => h("div", { class: ["ring-block", p.tone] }, [
      h("span", { class: "ring-wrap" }, [h(RingProgress, { value: p.value, tone: p.tone }), h("strong", p.text)]),
      h("span", p.label),
      h("small", p.sub)
    ]);
  }
});

const ActivityTimeline = defineComponent({
  props: { items: { type: Array as PropType<any[]>, default: () => [] } },
  setup(p) {
    return () => h("article", { class: "panel-card activity-card" }, [
      h("div", { class: "section-head" }, [h("h2", [h(Clock, { size: 18 }), "学习动态"])]),
      p.items.length
        ? p.items.map((item) => h("div", { class: "timeline-item", key: `${item.type}-${item.title}-${item.time}` }, [
          h("i"),
          h("strong", item.title || "学习记录"),
          h("time", relativeTime(item.time)),
          h("p", item.meta || "")
        ]))
        : h(EmptyState, { text: "暂无动态" })
    ]);
  }
});

const EmptyState = defineComponent({
  props: { text: { type: String, default: "暂无数据" } },
  setup(p) {
    return () => h("div", { class: "empty" }, [h(BookOpen, { size: 28 }), h("span", p.text)]);
  }
});

const SelectMenu = defineComponent({
  props: {
    modelValue: { type: [String, Number], default: "" },
    items: { type: Array as PropType<Array<string | SelectOption>>, default: () => [] }
  },
  emits: ["update:modelValue"],
  setup(p, { emit: update }) {
    const open = ref(false);
    const options = computed(() => normalizeItems(p.items));
    const current = computed(() => options.value.find((item) => item.value === p.modelValue)?.label || options.value[0]?.label || "请选择");
    return () => h("div", { class: "select-menu" }, [
      h("button", { type: "button", onClick: () => { open.value = !open.value; } }, [h("span", current.value), h(ChevronDown, { size: 15 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop" }, options.value.map((item) =>
          h("button", {
            type: "button",
            key: item.value,
            class: { active: item.value === p.modelValue },
            onClick: () => { update("update:modelValue", item.value); open.value = false; }
          }, item.label)
        )) : null
      })
    ]);
  }
});

const DropdownMenu = defineComponent({
  props: { items: { type: Array as PropType<SelectOption[]>, default: () => [] } },
  emits: ["select"],
  setup(p, { emit: update }) {
    const open = ref(false);
    return () => h("div", { class: "dropdown-menu" }, [
      h("button", { type: "button", class: "dropdown-trigger", onClick: () => { open.value = !open.value; } }, [h(MoreHorizontal, { size: 16 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "dropdown-pop" }, p.items.map((item) =>
          h("button", {
            type: "button",
            key: item.value,
            class: { danger: item.danger },
            onClick: () => { update("select", item.value); open.value = false; }
          }, item.label)
        )) : null
      })
    ]);
  }
});

const CourseSelect = defineComponent({
  setup() {
    async function updateCourse(value: string | number) {
      selectedCourseId.value = Number(value);
      courseHome.value = {};
      await loadCourseHome();
      await loadActive();
    }
    return () => courses.value.length
      ? h("div", { class: "course-select" }, [
        h(SelectMenu, {
          modelValue: selectedCourseId.value,
          items: courses.value.map((course) => ({ label: course.name, value: course.id })),
          "onUpdate:modelValue": updateCourse
        })
      ])
      : h("button", { type: "button", class: "select-menu-empty", onClick: () => { joinOpen.value = true; } }, [h(Plus, { size: 14 }), "加入课程"]);
  }
});

const CourseRequired = defineComponent({
  setup() {
    return () => h("article", { class: "panel-card empty" }, [
      h(BookOpen, { size: 36 }),
      h("strong", "先加入课程"),
      h("button", { type: "button", class: "btn btn-primary", onClick: () => { joinOpen.value = true; } }, [h(Plus, { size: 16 }), "加入课程"])
    ]);
  }
});

const QuickTile = defineComponent({
  props: { icon: { type: Object, required: true }, label: { type: String, required: true }, sub: { type: String, default: "" } },
  emits: ["click"],
  setup(p, { emit: update }) {
    return () => h("button", { type: "button", class: "quick-tile", onClick: () => update("click") }, [
      h("span", [h(p.icon as any, { size: 18 })]),
      h("strong", p.label),
      h("small", p.sub)
    ]);
  }
});

const LessonItem = defineComponent({
  props: { lesson: { type: Object as PropType<any>, required: true }, index: { type: Number, required: true } },
  emits: ["open"],
  setup(p, { emit: update }) {
    return () => h("button", { type: "button", class: ["lesson-item", p.lesson.progress_percent > 0 && p.lesson.progress_percent < 100 ? "current" : ""], onClick: () => update("open") }, [
      h("b", String(p.index + 1).padStart(2, "0")),
      h("div", [h("strong", p.lesson.title), h("small", `第 ${p.lesson.current_page || 1} 页 · ${p.lesson.progress_percent || 0}%`)]),
      p.lesson.progress_percent >= 100 ? h(CheckCircle, { size: 18 }) : h(Play, { size: 18 })
    ]);
  }
});

const MaterialRow = defineComponent({
  props: { item: { type: Object as PropType<any>, required: true } },
  setup(p) {
    return () => h("div", { class: "material-row" }, [
      h("span", { class: "file-badge" }, [h(FileText, { size: 16 })]),
      h("div", [h("strong", p.item.title || p.item.original_filename || "课程资料"), h("small", `${p.item.material_type || "file"} · ${p.item.size_label || optionText(p.item.size_bytes || 0)}`)]),
      p.item.preview_url ? h("a", { href: p.item.preview_url, target: "_blank", class: "link-btn" }, [h(Download, { size: 14 }), "查看"]) : h("span", { class: "tag" }, p.item.parse_status || "待处理")
    ]);
  }
});

const MiniMetric = defineComponent({
  props: {
    icon: { type: Object, required: true },
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    tone: { type: String, default: "primary" }
  },
  setup(p) {
    return () => h("div", { class: ["mini-metric", p.tone] }, [h(p.icon as any, { size: 18 }), h("div", [h("strong", String(p.value)), h("span", p.label)])]);
  }
});

const ChatList = defineComponent({
  props: {
    messages: { type: Array as PropType<ChatMessage[]>, default: () => [] },
    thinking: { type: Boolean, default: false },
    large: { type: Boolean, default: false }
  },
  emits: ["toggle-thought", "copy", "favorite", "feedback"],
  setup(p, { emit: update }) {
    function bubble(message: ChatMessage) {
      const body = [
        message.thought ? h("button", { type: "button", class: "thought-toggle", onClick: () => update("toggle-thought", message) }, [h(Sparkles, { size: 13 }), "思考过程", h(ChevronDown, { size: 13, class: { rotate: message.thoughtOpen } })]) : null,
        h(Transition, { name: "thought-roll" }, { default: () => message.thought && message.thoughtOpen ? h("div", { class: "thought" }, message.thought) : null }),
        message.outOfScope ? h("span", { class: "tag tag-warning" }, "可能超纲") : null,
        h("p", message.text),
        message.sources?.length ? h("div", { class: "source-tags" }, message.sources.slice(0, 3).map((source, index) => h("span", { class: "tag", key: index }, source.title || source.material_title || `来源${index + 1}`))) : null,
        h("div", { class: "msg-actions" }, [
          h("button", { type: "button", onClick: () => update("copy", message.text) }, [h(Copy, { size: 13 }), "复制"]),
          message.role === "ai" ? h("button", { type: "button", onClick: () => update("favorite", message) }, [h(BookMarked, { size: 13 }), message.favorite ? "已藏" : "收藏"]) : null,
          message.role === "ai" ? h("button", { type: "button", onClick: () => update("feedback", message, "positive") }, [h(Check, { size: 13 }), "有用"]) : null
        ])
      ];
      return h("div", { class: "chat-bubble" }, body);
    }
    function avatar(message: ChatMessage) {
      return h("span", { class: "chat-avatar" }, [message.role === "user" ? h(User, { size: 16 }) : h(Sparkles, { size: 16 })]);
    }
    return () => h("div", { class: ["chat-list", p.large ? "large" : ""] }, [
      ...p.messages.map((message) => h("article", { key: message.id, class: ["chat-msg", message.role] }, message.role === "user" ? [bubble(message), avatar(message)] : [avatar(message), bubble(message)])),
      p.thinking ? h("div", { class: "thinking" }, [h("i"), h("i"), h("i"), h("span", "AI 思考中")]) : null
    ]);
  }
});

const EmptyGuide = defineComponent({
  setup() {
    return () => h("div", { class: "empty-guide" }, [h(Sparkles, { size: 38 }), h("strong", "等待题目"), h("span", "输入后开始辅导")]);
  }
});

const GuideStep = defineComponent({
  props: { level: { type: Number, required: true }, data: { type: Object as PropType<any>, default: null }, open: { type: Boolean, default: false } },
  emits: ["toggle", "load"],
  setup(p, { emit: update }) {
    const title = computed(() => p.level === 1 ? "提示" : p.level === 2 ? "思路" : "详解");
    return () => h("section", { class: "guide-step" }, [
      h("button", { type: "button", onClick: () => update(p.data ? "toggle" : "load") }, [h("b", String(p.level)), h("strong", title.value), h(ChevronDown, { size: 16, class: { rotate: p.open } })]),
      h(Transition, { name: "fade-slide" }, {
        default: () => p.open && p.data ? h("div", { class: "guide-body" }, [
          h("p", p.data.hint || p.data.content || p.data.answer || "暂无内容"),
          p.data.steps?.length ? h("ol", p.data.steps.map((step: string, index: number) => h("li", { key: index }, step))) : null,
          p.data.final_answer ? h("strong", `答案：${p.data.final_answer}`) : null
        ]) : null
      })
    ]);
  }
});

const HistoryStrip = defineComponent({
  props: { title: { type: String, required: true }, items: { type: Array as PropType<any[]>, default: () => [] } },
  emits: ["pick"],
  setup(p, { emit: update }) {
    return () => h("article", { class: "panel-card history-strip" }, [
      h("div", { class: "section-head" }, [h("h2", [h(Clock, { size: 18 }), p.title]), h("span", { class: "tag" }, String(p.items.length))]),
      p.items.length ? h("div", p.items.slice(0, 6).map((item) => h("button", { type: "button", key: item.id, onClick: () => update("pick", item) }, [
        h("strong", (item.corrected_text || item.ocr_text || item.raw_text || "题目").slice(0, 48)),
        h("small", relativeTime(item.created_at))
      ]))) : h(EmptyState, { text: "暂无记录" })
    ]);
  }
});

const KnowledgeBlock = defineComponent({
  props: {
    icon: { type: String, default: "Quote" },
    title: { type: String, required: true },
    content: { type: [String, Array, Object], default: "" },
    ai: { type: Boolean, default: false },
    warning: { type: Boolean, default: false }
  },
  setup(p) {
    const icons: Record<string, any> = { Quote, Layers, Pencil, AlertTriangle };
    const content = computed(() => {
      if (Array.isArray(p.content)) return p.content.join("；");
      if (p.content && typeof p.content === "object") return Object.values(p.content).join("；");
      return String(p.content || "暂无内容");
    });
    return () => h("section", { class: ["knowledge-block", p.ai ? "ai" : "", p.warning ? "warning" : ""] }, [
      h("h3", [h(icons[p.icon] || Quote, { size: 17 }), p.title]),
      h("div", content.value)
    ]);
  }
});

const QuizAnswerView = defineComponent({
  props: {
    quiz: { type: Object as PropType<any>, default: null },
    answers: { type: Object as PropType<Record<number, any>>, required: true },
    attempt: { type: Object as PropType<any>, default: null }
  },
  emits: ["answer", "submit", "exit"],
  setup(p, { emit: update }) {
    const current = ref(0);
    const marked = ref<number[]>([]);
    const confirming = ref(false);
    const elapsed = ref(0);
    let timer: number | undefined;
    onMounted(() => { timer = window.setInterval(() => { elapsed.value += 1; }, 1000); });
    onBeforeUnmount(() => { if (timer) window.clearInterval(timer); });
    const questions = computed(() => p.quiz?.questions || []);
    const quizMeta = computed(() => p.quiz?.quiz || {});
    const question = computed(() => questions.value[current.value] || null);
    const answeredCount = computed(() => questions.value.filter((item: any) => p.answers[item.id] !== undefined && p.answers[item.id] !== "").length);
    const attemptData = computed(() => p.attempt?.attempt || p.attempt);
    const attemptAnswers = computed(() => p.attempt?.answers || []);
    function answerValue(item: any) {
      return p.answers[item.id];
    }
    function setAnswer(item: any, value: any) {
      if (item.question_type === "multiple_choice") {
        const currentValues = Array.isArray(p.answers[item.id]) ? [...p.answers[item.id]] : [];
        update("answer", item.id, currentValues.includes(value) ? currentValues.filter((entry) => entry !== value) : [...currentValues, value]);
      } else {
        update("answer", item.id, value);
      }
    }
    function optionLabel(index: number) {
      return String.fromCharCode(65 + index);
    }
    function submit() {
      confirming.value = false;
      update("submit");
    }
    function scoreLevel(value: number) {
      if (value >= 90) return "优秀";
      if (value >= 75) return "良好";
      if (value >= 60) return "及格";
      return "待加强";
    }
    function renderQuestionBody(item: any) {
      if (!item) return null;
      const options = Array.isArray(item.options) ? item.options : [];
      if (["single_choice", "multiple_choice", "judge"].includes(item.question_type)) {
        return h("div", { class: "option-list" }, options.map((option: any, index: number) => {
          const value = index;
          const selected = item.question_type === "multiple_choice" ? (answerValue(item) || []).includes(value) : answerValue(item) === value;
          return h("button", { type: "button", class: ["option-btn", selected ? "active" : ""], onClick: () => setAnswer(item, value) }, [
            h("span", optionLabel(index)),
            h("strong", typeof option === "object" ? option.text || option.label || JSON.stringify(option) : String(option))
          ]);
        }));
      }
      if (item.question_type === "blank") {
        return h("input", { class: "input answer-input", value: answerValue(item) || "", placeholder: "填写答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLInputElement).value) });
      }
      return h("div", [h("textarea", { class: "textarea answer-textarea", value: answerValue(item) || "", maxlength: 500, placeholder: "写下你的答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLTextAreaElement).value) }), h("small", `${String(answerValue(item) || "").length} / 500`)]);
    }
    function renderResult() {
      const accuracy = Number(attemptData.value?.accuracy || 0);
      return h("section", { class: "answer-shell result-shell" }, [
        h("header", { class: "answer-head" }, [
          h("button", { type: "button", class: "btn btn-secondary", onClick: () => update("exit") }, [h(ArrowLeft, { size: 16 }), "返回"]),
          h("strong", quizMeta.value.title || "练习结果"),
          h("span", timeLabel(elapsed.value))
        ]),
        h("main", { class: "result-main" }, [
          h("article", { class: "result-card" }, [
            accuracy >= 60 ? h(CheckCircle, { size: 48 }) : h(XCircle, { size: 48 }),
            h("strong", String(Math.round(Number(attemptData.value?.score || 0)))),
            h("span", `分 / ${Math.round(Number(attemptData.value?.total_score || quizMeta.value.total_score || 100))} 分`),
            h("em", scoreLevel(accuracy)),
            h("small", `用时 ${timeLabel(elapsed.value)} · 正确率 ${accuracy}%`)
          ]),
          h("article", { class: "panel-card result-grid" }, [
            h(RingBlock, { label: "正确率", value: accuracy, text: `${accuracy}%`, sub: "本次" }),
            h("div", [h("h2", [h(Sparkles, { size: 18 }), "AI 建议"]), h("p", attemptData.value?.ai_feedback || "复盘错题，并回看对应知识点。")])
          ]),
          h("article", { class: "panel-card answer-analysis" }, [
            h("div", { class: "section-head" }, [h("h2", "题目解析")]),
            attemptAnswers.value.length
              ? attemptAnswers.value.map((row: any, index: number) => h("details", { key: row.question_id, open: !row.is_correct }, [
                h("summary", [row.is_correct ? h(CheckCircle, { size: 16 }) : h(XCircle, { size: 16 }), `题目 ${index + 1}`, h("span", row.is_correct ? "正确" : "错误")]),
                h("p", row.question?.stem || ""),
                h("small", `你的答案：${optionText(row.user_answer)} · 正确答案：${optionText(row.correct_answer)}`),
                h("div", row.feedback || row.question?.explanation || "暂无解析")
              ]))
              : h("p", attemptData.value?.ai_feedback || "提交完成")
          ])
        ])
      ]);
    }
    return () => {
      if (p.attempt) return renderResult();
      const item = question.value;
      if (!item) return h("div", { class: "answer-shell" }, [h(EmptyState, { text: "暂无题目" })]);
      const unanswered = questions.value.filter((entry: any) => p.answers[entry.id] === undefined || p.answers[entry.id] === "").map((entry: any, index: number) => index + 1);
      return h("section", { class: "answer-shell" }, [
        h("header", { class: "answer-head" }, [
          h("button", { type: "button", class: "btn btn-secondary", onClick: () => update("exit") }, [h(ArrowLeft, { size: 16 }), "退出"]),
          h("strong", quizMeta.value.title || "练习"),
          h("span", [h(Clock, { size: 15 }), timeLabel(elapsed.value)])
        ]),
        h("main", { class: "answer-body" }, [
          h("aside", { class: "question-nav" }, [
            h("div", { class: "answer-stat" }, [h("span", `已答 ${answeredCount.value}`), h("span", `标记 ${marked.value.length}`), h("span", `未答 ${Math.max(0, questions.value.length - answeredCount.value)}`)]),
            h("div", { class: "q-grid" }, questions.value.map((entry: any, index: number) => h("button", {
              type: "button",
              class: { answered: p.answers[entry.id] !== undefined && p.answers[entry.id] !== "", current: index === current.value, marked: marked.value.includes(entry.id) },
              onClick: () => { current.value = index; }
            }, String(index + 1))))
          ]),
          h("article", { class: "question-card" }, [
            h("div", { class: "question-meta" }, [
              h("span", { class: "tag tag-primary" }, `题目 ${current.value + 1}`),
              h("span", { class: "tag" }, item.question_type || "题目"),
              h("span", { class: "tag tag-warning" }, item.difficulty || "standard"),
              h("button", { type: "button", class: "link-btn", onClick: () => { marked.value = marked.value.includes(item.id) ? marked.value.filter((id) => id !== item.id) : [...marked.value, item.id]; } }, [h(BookMarked, { size: 14 }), marked.value.includes(item.id) ? "取消标记" : "标记"])
            ]),
            h("h2", item.stem),
            renderQuestionBody(item)
          ])
        ]),
        h("footer", { class: "answer-foot" }, [
          h("button", { type: "button", class: "btn btn-secondary", disabled: current.value <= 0, onClick: () => { current.value = Math.max(0, current.value - 1); } }, [h(ArrowLeft, { size: 16 }), "上一题"]),
          h("span", `第 ${current.value + 1} / ${questions.value.length} 题`),
          h("button", { type: "button", class: "btn btn-secondary", disabled: current.value >= questions.value.length - 1, onClick: () => { current.value = Math.min(questions.value.length - 1, current.value + 1); } }, [h(ChevronRight, { size: 16 }), "下一题"]),
          h("button", { type: "button", class: "btn btn-primary", onClick: () => { confirming.value = true; } }, [h(CheckCircle, { size: 16 }), "提交"])
        ]),
        h(Transition, { name: "modal-pop" }, {
          default: () => confirming.value ? h("div", { class: "modal-mask" }, [
            h("article", { class: "join-modal confirm-card" }, [
              h("div", { class: "modal-head" }, [h(AlertTriangle, { size: 22 }), h("h2", "确认提交"), h("button", { type: "button", onClick: () => { confirming.value = false; } }, [h(X, { size: 16 })])]),
              h("p", unanswered.length ? `还有 ${unanswered.length} 道未答` : "所有题目已作答"),
              marked.value.length ? h("p", `已标记 ${marked.value.length} 道`) : null,
              h("footer", [h("button", { type: "button", class: "btn btn-ghost", onClick: () => { confirming.value = false; } }, "继续作答"), h("button", { type: "button", class: "btn btn-primary", onClick: submit }, "确认提交")])
            ])
          ]) : null
        })
      ]);
    };
  }
});

const QuizCard = defineComponent({
  props: { quiz: { type: Object as PropType<any>, required: true } },
  emits: ["open"],
  setup(p, { emit: update }) {
    return () => h("article", { class: "quiz-card" }, [
      h("h2", p.quiz.title),
      h("p", p.quiz.description || `${p.quiz.total_score || 0} 分 · ${statusText(p.quiz.status || "published")}`),
      h("footer", [h("span", { class: "tag" }, p.quiz.quiz_type || "practice"), h("button", { type: "button", class: "btn btn-primary btn-sm", onClick: () => update("open") }, [h(Play, { size: 14 }), "开始"])])
    ]);
  }
});

const WrongCard = defineComponent({
  props: { item: { type: Object as PropType<any>, required: true } },
  emits: ["practice"],
  setup(p, { emit: update }) {
    return () => h("article", { class: "wrong-card" }, [
      h("h2", p.item.question?.stem || "错题"),
      h("p", p.item.question?.explanation || "建议重新练习"),
      h("div", [p.item.knowledge_point_name ? h("span", { class: "tag tag-warning" }, p.item.knowledge_point_name) : null, h("span", { class: "tag tag-danger" }, `错误 ${p.item.wrong_count}`)]),
      h("footer", [h("button", { type: "button", class: "btn btn-primary btn-sm", onClick: () => update("practice") }, [h(RefreshCw, { size: 14 }), "重练"])])
    ]);
  }
});

const CalendarCard = defineComponent({
  props: { checkins: { type: Array as PropType<string[]>, default: () => [] } },
  setup(p) {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    const days = new Date(year, month + 1, 0).getDate();
    return () => h("article", { class: "panel-card calendar-card" }, [
      h("div", { class: "calendar-head" }, [h("strong", `${month + 1}月`), h("span", `${year}`)]),
      h("div", { class: "calendar-grid" }, Array.from({ length: days }, (_, index) => {
        const day = index + 1;
        const iso = new Date(year, month, day).toISOString().slice(0, 10);
        return h("span", { class: { done: p.checkins.includes(iso), today: day === today.getDate() } }, String(day));
      }))
    ]);
  }
});

const TaskRow = defineComponent({
  props: { task: { type: Object as PropType<any>, required: true } },
  emits: ["checkin"],
  setup(p, { emit: update }) {
    return () => h("div", { class: ["task-row", p.task.status === "done" ? "done" : ""] }, [
      h("button", { type: "button", onClick: () => update("checkin") }, [p.task.status === "done" ? h(Check, { size: 16 }) : null]),
      h("div", [h("strong", p.task.title), h("small", `${p.task.estimated_minutes || 30} 分钟`)]),
      h("span", { class: "tag" }, p.task.task_type || "学习")
    ]);
  }
});

const PopoverButton = defineComponent({
  props: {
    label: { type: String, required: true },
    items: { type: Array as PropType<SelectOption[]>, default: () => [] }
  },
  emits: ["select"],
  setup(p, { emit: update }) {
    const open = ref(false);
    return () => h("div", { class: "popover-button select-menu" }, [
      h("button", { type: "button", onClick: () => { open.value = !open.value; } }, [p.label, h(ChevronDown, { size: 14 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop" }, p.items.map((item) => h("button", { type: "button", key: item.value, onClick: () => { update("select", String(item.value)); open.value = false; } }, item.label))) : null
      })
    ]);
  }
});

onMounted(async () => { await loadCourses(); await loadActive(); });
onBeforeUnmount(() => { stopStudyClock(); if (chromeTimer) clearTimeout(chromeTimer); if (joinTimer) clearTimeout(joinTimer); if (noteTimer) clearTimeout(noteTimer); });
</script>

<style scoped>
.student-shell { min-height: 100vh; background: var(--color-bg-page); color: var(--color-text-body); padding-bottom: 88px; }
.student-top { position: sticky; top: 0; z-index: var(--z-sticky); height: 64px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: rgba(255,255,255,0.94); backdrop-filter: blur(12px); box-shadow: var(--shadow-xs); padding: 0 24px; }
.brand { display: inline-flex; align-items: center; gap: 8px; border: 0; background: transparent; color: var(--color-text-primary); font-weight: 600; }
.brand span, .avatar, .big-avatar { display: inline-flex; align-items: center; justify-content: center; background: var(--color-ai-gradient); color: white; }
.brand span { width: 28px; height: 28px; border-radius: var(--radius-md); }
.top-actions { display: flex; align-items: center; gap: 10px; }
.top-icon, .avatar-btn, .modal-head button { position: relative; display: inline-flex; width: 38px; height: 38px; align-items: center; justify-content: center; border: 0; border-radius: var(--radius-full); background: white; color: var(--color-text-secondary); box-shadow: var(--shadow-sm); }
.top-icon em { position: absolute; top: 2px; right: 2px; min-width: 16px; height: 16px; border-radius: 8px; background: var(--color-danger-500); color: white; font-size: 10px; font-style: normal; line-height: 16px; }
.avatar-btn span { width: 40px; height: 40px; border-radius: 50%; border: 2px solid white; background: var(--color-ai-gradient); color: white; font-weight: 700; }
.global-search { position: fixed; inset: 0; z-index: var(--z-modal); height: 64px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; background: white; padding: 0 32px; }
.global-search input { border: 0; outline: 0; font-size: 18px; }
.global-search button { border: 0; background: transparent; color: var(--color-text-muted); }
.notice-pop, .user-pop { position: fixed; top: 58px; right: 24px; z-index: var(--z-dropdown); width: 360px; border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-lg); padding: 10px; }
.user-pop { width: 220px; display: grid; gap: 4px; }
.user-pop button, .notice-item { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 10px; text-align: left; }
.user-card { border-bottom: 1px solid var(--color-border-subtle); padding: 10px; }
.user-card strong, .notice-item strong { color: var(--color-text-primary); }
.user-card small, .notice-item small { color: var(--color-text-muted); }
.notice-item i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-primary-600); }
.student-main { max-width: 1100px; margin: 0 auto; padding: 24px 24px 16px; }
.student-page { display: grid; gap: 16px; animation: fade-slide-up 250ms var(--ease-out); }
.hello-card { position: relative; overflow: hidden; min-height: 100px; display: flex; align-items: center; justify-content: space-between; border-radius: 24px; background: linear-gradient(135deg,#4F46E5,#8B5CF6); color: white; padding: 24px 32px; }
.hello-card::before, .hello-card::after { content: ""; position: absolute; right: 80px; width: 150px; height: 150px; border-radius: 50%; background: rgba(255,255,255,0.06); }
.hello-card::before { top: -60px; }.hello-card::after { right: -40px; bottom: -80px; }
.hello-card > div:first-child { position: relative; display: flex; align-items: center; gap: 14px; z-index: 1; }
.hello-card h1 { margin: 0; font-size: 22px; }.hello-card p { margin: 4px 0 0; color: rgba(255,255,255,0.76); font-size: 13px; }
.white-pill, .white-fill { border: 1px solid rgba(255,255,255,0.56); border-radius: var(--radius-full); background: rgba(255,255,255,0.16); color: white; padding: 8px 14px; }
.circle-stat { z-index: 1; display: grid; place-items: center; }.circle-stat span { position: absolute; font-weight: 700; }
.today-plan { min-height: 64px; display: grid; grid-template-columns: auto 1fr auto 100px auto; align-items: center; gap: 12px; border-left: 4px solid var(--color-primary-600); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 12px 16px; }
.today-plan strong { color: var(--color-text-primary); }.today-plan small { display: block; color: var(--color-text-muted); }.today-plan button, .section-head button { border: 0; background: transparent; color: var(--color-primary-700); }
.continue-card { overflow: hidden; display: grid; grid-template-columns: 140px 1fr; min-height: 210px; border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-md); }
.continue-cover { position: relative; display: grid; place-items: center; color: white; }
.continue-cover span { position: absolute; right: 14px; bottom: 14px; border-radius: var(--radius-full); background: rgba(255,255,255,0.9); color: var(--color-text-primary); padding: 2px 8px; font-family: var(--font-family-mono); }
.continue-card section { display: grid; align-content: center; gap: 8px; padding: 22px; }.continue-card h2 { margin: 0; color: var(--color-text-primary); font-size: 17px; }
.continue-card p, .continue-card small { margin: 0; color: var(--color-text-muted); }
.empty-continue { justify-items: start; }
.home-grid, .course-layout, .tutoring-grid, .plans-grid { display: grid; grid-template-columns: 55fr 45fr; gap: 16px; }
.panel-card, .ai-reco, .course-tools, .student-course-card, .knowledge-head, .knowledge-body, .wrong-hero, .plan-hero, .profile-hero, .badge-card { border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 18px; }
.section-head, .page-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-head h2, .page-title-row h1 { display: flex; align-items: center; gap: 8px; margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.page-title-row p { margin: 4px 0 0; color: var(--color-text-muted); }
.page-title-actions { display: flex; align-items: center; gap: 8px; }
.home-course { width: 100%; display: grid; grid-template-columns: 44px 1fr; align-items: center; gap: 12px; border: 0; border-radius: var(--radius-lg); background: white; padding: 12px; text-align: left; transition: transform 200ms var(--ease-out), box-shadow 200ms var(--ease-out); }
.home-course:hover, .student-course-card:hover, .quick-tile:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.home-course > span { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 10px; color: white; }
.home-course strong { color: var(--color-text-primary); }.home-course small { display: block; color: var(--color-text-muted); }.home-course em { color: var(--color-text-muted); font-size: 12px; font-style: normal; }
.join-dashed { width: 100%; min-height: 52px; display: flex; align-items: center; justify-content: center; gap: 8px; border: 1px dashed var(--color-border-strong); border-radius: var(--radius-lg); background: white; color: var(--color-primary-700); }
.rings { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 20px 0; }
.ring-block { display: grid; justify-items: center; gap: 6px; text-align: center; }.ring-wrap { position: relative; width: 72px; height: 72px; display: grid; place-items: center; }.ring-wrap svg { transform: rotate(-90deg); }.ring-wrap strong { position: absolute; color: var(--color-text-primary); }
.week-check { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; border-top: 1px solid var(--color-border-subtle); padding-top: 14px; }
.week-check span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; border: 1px dashed var(--color-border-strong); color: var(--color-text-muted); }
.week-check .done { border: 0; background: var(--color-primary-600); color: white; }.week-check .today { animation: pulse-ring 1.6s infinite; }
.streak { display: flex; align-items: center; gap: 6px; margin-top: 12px; color: var(--color-warning-700); }
.ai-reco { display: grid; grid-template-columns: 1fr 320px; gap: 16px; background: var(--color-ai-light); border-left: 4px solid #8B5CF6; }
.ai-reco section { display: flex; gap: 12px; }.ai-reco h2 { margin: 0; color: var(--color-text-primary); }.ai-reco p { color: var(--color-text-body); line-height: 1.7; }
.ai-reco aside { display: grid; gap: 10px; }.ai-reco aside button { display: grid; grid-template-columns: auto 1fr; gap: 8px; border: 1px solid var(--color-ai-border); border-radius: var(--radius-lg); background: white; padding: 12px; text-align: left; }.ai-reco aside span { grid-column: 2; color: var(--color-primary-700); }
.activity-card { display: grid; gap: 12px; }.timeline-item { display: grid; grid-template-columns: 18px 1fr auto; gap: 10px; position: relative; }.timeline-item::before { content: ""; position: absolute; left: 8px; top: 18px; bottom: -14px; width: 1px; background: var(--color-border-default); }.timeline-item i { width: 9px; height: 9px; border-radius: 50%; background: var(--color-primary-600); margin-top: 6px; }.timeline-item strong { color: var(--color-text-primary); }.timeline-item p, .timeline-item time { margin: 0; color: var(--color-text-muted); font-size: 12px; }
.course-tools { display: grid; grid-template-columns: 220px 160px 1fr; align-items: center; gap: 12px; }
.pretty-input { display: flex; align-items: center; gap: 8px; height: 38px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 0 12px; }
.pretty-input input { width: 100%; border: 0; outline: 0; }
.select-menu, .dropdown-menu { position: relative; }
.select-menu > button, .dropdown-trigger { min-height: 38px; display: inline-flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-text-body); padding: 0 12px; }
.select-pop, .dropdown-pop { position: absolute; top: calc(100% + 6px); z-index: var(--z-dropdown); min-width: 180px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 6px; }
.select-pop button, .dropdown-pop button { width: 100%; min-height: 34px; display: flex; align-items: center; gap: 8px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 0 10px; text-align: left; }.select-pop button.active, .select-pop button:hover, .dropdown-pop button:hover { background: var(--color-primary-50); color: var(--color-primary-700); }.dropdown-pop .danger { color: var(--color-danger-700); }
.course-select { min-width: 180px; }.select-menu-empty { display: inline-flex; align-items: center; gap: 6px; min-height: 38px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-primary-700); padding: 0 12px; }
.underline-tabs, .seg-tabs, .study-tabs, .profile-tabs { display: flex; gap: 14px; border-bottom: 1px solid var(--color-border-default); }
.underline-tabs button, .seg-tabs button, .study-tabs button, .profile-tabs button { display: inline-flex; align-items: center; gap: 7px; min-height: 42px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-secondary); padding: 0 8px; }
.underline-tabs .active, .seg-tabs .active, .study-tabs .active, .profile-tabs .active { border-bottom-color: var(--color-primary-600); color: var(--color-primary-700); font-weight: 600; }
.student-course-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.student-course-card { overflow: hidden; padding: 0; transition: transform 200ms var(--ease-out), box-shadow 200ms var(--ease-out); }
.course-art { position: relative; aspect-ratio: 16/9; display: grid; place-items: center; color: white; }.course-art svg { transition: transform 200ms var(--ease-out); }.student-course-card:hover .course-art > svg { transform: scale(1.05); }
.course-art span, .course-art em { position: absolute; bottom: 12px; border-radius: var(--radius-full); background: rgba(255,255,255,0.22); backdrop-filter: blur(8px); color: white; padding: 4px 8px; font-style: normal; }.course-art span { left: 12px; }.course-art em { right: 12px; display: flex; align-items: center; gap: 4px; }
.course-art .dropdown-menu { position: absolute; top: 12px; right: 12px; width: 34px; }.course-art .dropdown-trigger { width: 34px; height: 34px; min-height: 34px; padding: 0; border: 0; background: rgba(255,255,255,0.2); color: white; }
.student-course-card section { padding: 18px; }.student-course-card h2 { margin: 0; color: var(--color-text-primary); font-size: 16px; }.student-course-card p, .course-meta { display: flex; align-items: center; gap: 6px; color: var(--color-text-muted); font-size: 13px; }.course-meta { justify-content: space-between; }
.mini-data { display: flex; gap: 16px; color: var(--color-text-secondary); font-size: 13px; margin: 12px 0; }.mini-data span { display: flex; align-items: center; gap: 5px; }
.full { width: 100%; }
.course-hero-student { min-height: 180px; display: grid; grid-template-columns: 1fr 180px; align-items: center; gap: 24px; border-radius: 24px; color: white; padding: 32px; overflow: hidden; }.course-hero-student h1 { margin: 0; font-size: 26px; }.course-hero-student p, .course-hero-student div { display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.78); }.course-hero-student progress { width: 100px; accent-color: var(--color-success-500); }.slide-mini { width: 120px; height: 90px; display: grid; place-items: center; border-radius: 12px; background: white; color: var(--color-text-primary); box-shadow: 0 8px 32px rgba(0,0,0,0.35); transform: rotate(-3deg); transition: transform 200ms var(--ease-out); }.slide-mini:hover { transform: rotate(0) scale(1.03); }
.quick-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }.quick-tile { min-height: 80px; display: grid; justify-items: start; gap: 4px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 14px; text-align: left; transition: all 200ms var(--ease-out); }.quick-tile span { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--color-primary-50); color: var(--color-primary-700); }.quick-tile strong { color: var(--color-text-primary); }
.course-layout { grid-template-columns: 60fr 40fr; align-items: start; }.course-layout > section, .course-layout > aside { display: grid; gap: 16px; }
.lesson-item { position: relative; display: grid; grid-template-columns: 40px 1fr auto; align-items: center; gap: 12px; width: 100%; min-height: 72px; border: 0; border-bottom: 1px solid var(--color-border-subtle); background: white; text-align: left; padding: 8px; }.lesson-item.current { background: var(--color-primary-50); box-shadow: inset 3px 0 0 var(--color-primary-600); }.lesson-item b { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 8px; background: var(--color-primary-50); color: var(--color-primary-700); }.lesson-item strong { color: var(--color-text-primary); }.lesson-item small { color: var(--color-text-muted); }
.material-row { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 10px; min-height: 56px; border-bottom: 1px solid var(--color-border-subtle); }.file-badge { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 8px; background: var(--color-primary-600); color: white; }.material-row strong { color: var(--color-text-primary); }.material-row small { display: block; color: var(--color-text-muted); }
.data-grid, .achievement-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }.mini-metric { min-height: 68px; display: grid; grid-template-columns: auto 1fr; gap: 6px; border-radius: 8px; background: var(--color-bg-muted); padding: 12px; }.mini-metric strong { color: var(--color-text-primary); font-size: 22px; }.mini-metric span { color: var(--color-text-muted); font-size: 11px; }.mini-metric.success svg { color: var(--color-success-500); }.mini-metric.ai svg { color: #8B5CF6; }.mini-metric.danger svg { color: var(--color-danger-500); }.mini-metric.warning svg { color: var(--color-warning-500); }
.ask-card { display: grid; gap: 10px; border-radius: var(--radius-xl); background: linear-gradient(135deg, rgba(6,182,212,0.1), rgba(139,92,246,0.1)); border-left: 4px solid #8B5CF6; padding: 18px; }.ask-card h2 { margin: 0; color: var(--color-text-primary); }.ask-card form, .chat-input { display: grid; grid-template-columns: 1fr auto; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 6px; }.ask-card input, .chat-input textarea { border: 0; outline: 0; resize: none; padding: 6px 10px; }.ask-card button:not(.quick-tags button), .send-btn { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 50%; background: var(--color-primary-600); color: white; }
.quick-tags { display: flex; gap: 8px; overflow-x: auto; }.quick-tags button { border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-text-secondary); padding: 5px 10px; white-space: nowrap; transition: all 150ms var(--ease-out); }.quick-tags button:hover { background: var(--color-primary-50); color: var(--color-primary-700); }
.qa-page { min-height: calc(100vh - 152px); max-width: 860px; margin: 0 auto; padding-bottom: 160px; }.qa-top { display: flex; align-items: center; justify-content: space-between; }.qa-top > div:first-child { display: flex; gap: 10px; }.qa-top h1 { margin: 0; color: var(--color-text-primary); }.qa-top p { margin: 2px 0 0; color: var(--color-text-muted); }.qa-tools { display: flex; align-items: center; gap: 8px; }
.qa-welcome { min-height: 520px; display: grid; align-content: center; justify-items: center; gap: 14px; text-align: center; }.qa-welcome > svg { color: #8B5CF6; animation: breathe 2s infinite; }.qa-welcome h2 { margin: 0; color: var(--color-text-primary); }.prompt-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 16px; }.prompt-grid button { display: flex; align-items: center; gap: 8px; min-height: 58px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 0 16px; }
.chat-list { display: grid; gap: 18px; padding: 20px 0; }.chat-msg { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 10px; align-items: start; max-width: 86%; animation: bubble-in 200ms var(--ease-out); }.chat-msg.user { grid-template-columns: minmax(0, 1fr) 36px; justify-self: end; }.chat-avatar { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: var(--color-ai-gradient); color: white; box-shadow: var(--shadow-sm); }.chat-bubble { position: relative; border: 1px solid var(--color-border-default); border-radius: 4px 16px 16px 16px; background: white; padding: 12px 16px; }.chat-bubble::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; border-radius: 3px 0 0 3px; background: var(--color-ai-gradient); }.chat-msg.user .chat-bubble { border: 0; border-radius: 16px 4px 16px 16px; background: var(--color-primary-600); color: white; }.chat-msg.user .chat-bubble::before { display: none; }.chat-bubble p { margin: 0; line-height: 1.7; }.source-tags { display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--color-border-subtle); margin-top: 10px; padding-top: 10px; }.msg-actions { display: flex; gap: 8px; opacity: 0; transition: opacity 150ms; }.chat-bubble:hover .msg-actions { opacity: 1; }.msg-actions button, .thought-toggle { border: 0; background: transparent; color: var(--color-text-muted); }.thought-toggle svg { transition: transform 180ms var(--ease-out); }.rotate { transform: rotate(180deg); }.thought { overflow: hidden; border-radius: var(--radius-md); background: var(--color-ai-light); color: #6D28D9; margin-bottom: 10px; padding: 8px; font-size: 12px; }
.thinking { display: flex; align-items: center; gap: 5px; color: var(--color-text-muted); }.thinking i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-ai-gradient); animation: thinking 1.2s infinite; }.thinking i:nth-child(2) { animation-delay: .15s; }.thinking i:nth-child(3) { animation-delay: .3s; }
.qa-fixed { position: fixed; left: 50%; bottom: 76px; z-index: var(--z-fixed); width: min(860px, calc(100vw - 48px)); transform: translateX(-50%); border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: rgba(248,250,252,0.96); backdrop-filter: blur(16px); padding: 10px 14px; box-shadow: var(--shadow-lg); }.qa-fixed > div { display: flex; align-items: center; gap: 6px; color: var(--color-primary-700); font-size: 12px; margin-bottom: 6px; }.qa-fixed section { display: grid; grid-template-columns: 1fr auto; gap: 8px; border-radius: var(--radius-lg); background: white; padding: 8px; }.qa-fixed textarea { border: 0; outline: 0; resize: none; }.qa-fixed small { display: block; text-align: center; color: var(--color-text-muted); margin-top: 5px; }
.history-drawer { position: fixed; top: 0; right: 0; bottom: 0; z-index: var(--z-modal); width: 320px; display: grid; align-content: start; gap: 10px; background: white; box-shadow: var(--shadow-xl); padding: 18px; }.drawer-head { display: flex; align-items: center; justify-content: space-between; }.drawer-head button { border: 0; background: transparent; }.history-row { display: grid; grid-template-columns: auto 1fr; gap: 8px; border: 0; border-bottom: 1px solid var(--color-border-subtle); background: white; color: var(--color-text-body); padding: 10px 0; text-align: left; }.history-row small { grid-column: 2; color: var(--color-text-muted); }
.tutoring-grid { grid-template-columns: 55fr 45fr; align-items: start; }.tutor-input, .guide-card { display: grid; gap: 14px; }.problem-text { min-height: 160px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 14px; resize: vertical; }.image-drop { min-height: 200px; display: grid; place-items: center; border: 2px dashed var(--color-border-strong); border-radius: var(--radius-lg); color: var(--color-text-muted); }.image-drop input { display: none; }.knowledge-box { display: flex; flex-wrap: wrap; gap: 8px; border-radius: var(--radius-lg); background: var(--color-ai-light); padding: 12px; }
.empty-guide { display: grid; gap: 12px; justify-items: center; color: var(--color-text-muted); text-align: center; padding: 32px 0; }.guide-step { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); overflow: hidden; }.guide-step > button { width: 100%; display: flex; align-items: center; gap: 10px; border: 0; background: white; color: var(--color-text-primary); padding: 14px; text-align: left; }.guide-step b { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--color-primary-600); color: white; }.guide-body { display: grid; gap: 10px; border-top: 1px solid var(--color-border-subtle); padding: 14px; line-height: 1.7; }.guide-body p { margin: 0; }
.history-strip { display: grid; gap: 10px; }.history-strip div { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }.history-strip button { min-height: 80px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; text-align: left; padding: 12px; }
.knowledge-layout, .wrong-layout { display: grid; grid-template-columns: 280px 1fr; gap: 16px; align-items: start; }.knowledge-tree, .wrong-tree { display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 14px; }.knowledge-tree button, .wrong-tree button { display: flex; align-items: center; gap: 8px; min-height: 36px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); text-align: left; }.knowledge-tree button:hover, .wrong-tree button.active { background: var(--color-primary-50); color: var(--color-primary-700); }.weak-tags { display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--color-border-subtle); padding-top: 10px; }
.knowledge-content { display: grid; gap: 14px; }.knowledge-head h1 { margin: 0; color: var(--color-text-primary); font-size: 22px; }.knowledge-head p { color: var(--color-text-muted); }.knowledge-body { display: grid; gap: 16px; padding: 32px; }.knowledge-block h3 { display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); }.knowledge-block div { border-left: 4px solid var(--color-primary-600); border-radius: 14px; background: var(--color-primary-50); padding: 16px; line-height: 1.75; }.knowledge-block.ai div { border-left-color: #8B5CF6; background: var(--color-ai-light); }.knowledge-block.warning div { border-left-color: var(--color-warning-500); background: var(--color-warning-50); }.practice-cta { display: flex; align-items: center; gap: 10px; border-radius: var(--radius-lg); background: var(--color-ai-light); padding: 14px; }.practice-cta button { border: 0; border-radius: var(--radius-full); background: var(--color-primary-600); color: white; padding: 7px 12px; }
.answer-page { position: fixed; inset: 0; z-index: var(--z-modal); background: var(--color-bg-page); }.answer-shell { min-height: 100vh; display: grid; grid-template-rows: 60px 1fr 64px; }.answer-head, .answer-foot { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: white; padding: 0 24px; }.answer-head span, .answer-stat { display: flex; align-items: center; gap: 8px; color: var(--color-text-muted); }.answer-foot { border-top: 1px solid var(--color-border-default); border-bottom: 0; }.answer-body { display: grid; grid-template-columns: 280px 1fr; gap: 24px; padding: 24px; }.question-nav { background: white; border-right: 1px solid var(--color-border-default); padding: 18px; }.answer-stat { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 14px; }.answer-stat span { border-radius: 8px; background: var(--color-bg-muted); padding: 8px; text-align: center; }.q-grid { display: grid; grid-template-columns: repeat(4, 40px); gap: 8px; }.q-grid button { width: 40px; height: 40px; border-radius: 10px; border: 1px solid var(--color-border-default); background: white; transition: all 160ms var(--ease-out); }.q-grid .answered { background: var(--color-success-50); border-color: var(--color-success-500); }.q-grid .current { box-shadow: 0 0 0 2px var(--color-primary-600); }.q-grid .marked { background: var(--color-warning-50); border-color: var(--color-warning-500); }.question-card { border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 32px; }.question-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }.question-meta .link-btn { margin-left: auto; }.question-card h2 { color: var(--color-text-primary); line-height: 1.75; }.option-list { display: grid; gap: 10px; }.option-btn { width: 100%; min-height: 52px; display: flex; gap: 10px; align-items: center; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; margin-top: 0; padding: 0 14px; text-align: left; transition: transform 160ms var(--ease-out), border-color 160ms, background 160ms; }.option-btn:hover { transform: translateX(3px); border-color: var(--color-primary-300); }.option-btn span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--color-bg-muted); }.option-btn.active { background: var(--color-primary-50); border-color: var(--color-primary-600); color: var(--color-primary-700); }.answer-input { max-width: 360px; }.answer-textarea { min-height: 160px; resize: vertical; }.result-shell { grid-template-rows: 60px 1fr; }.result-main { display: grid; gap: 16px; max-width: 900px; width: 100%; margin: 0 auto; padding: 28px; animation: result-pop 300ms var(--ease-out); }.result-card { display: grid; justify-items: center; gap: 8px; border-radius: 24px; background: linear-gradient(135deg,#4F46E5,#06B6D4); color: white; padding: 40px; }.result-card strong { font-size: 56px; line-height: 1; }.result-card em { border-radius: var(--radius-full); background: rgba(255,255,255,.18); padding: 4px 12px; font-style: normal; }.result-grid { display: grid; grid-template-columns: 200px 1fr; gap: 18px; align-items: center; }.answer-analysis { display: grid; gap: 10px; }.answer-analysis details { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; padding: 12px; }.answer-analysis summary { display: flex; align-items: center; gap: 8px; cursor: pointer; }.answer-analysis summary span { margin-left: auto; }.answer-analysis details[open] { background: var(--color-bg-muted); }.confirm-card p { color: var(--color-text-secondary); }
.quiz-list, .wrong-list { display: grid; gap: 12px; }.quiz-card, .wrong-card { position: relative; display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-left: 4px solid var(--color-success-500); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 16px; }.quiz-card h2, .wrong-card h2 { margin: 0; color: var(--color-text-primary); font-size: 17px; }.quiz-card p, .wrong-card p { color: var(--color-text-muted); }.quiz-card footer, .wrong-card footer { display: flex; gap: 8px; }
.practice-maker { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.chapter-checks { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }.chapter-checks button { border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 7px 12px; }.chapter-checks .active { background: var(--color-primary-600); color: white; }
.wrong-hero, .plan-hero, .profile-hero { display: grid; grid-template-columns: auto repeat(3, 1fr) auto; align-items: center; gap: 20px; background: linear-gradient(135deg,#EF4444,#F59E0B); color: white; }.wrong-hero strong, .plan-hero strong { display: block; font-size: 28px; }.wrong-tools { display: grid; grid-template-columns: 1fr 140px auto; gap: 10px; margin-bottom: 12px; }
.plans-grid { grid-template-columns: 45fr 30fr 25fr; }.calendar-card { display: grid; gap: 10px; }.calendar-head { display: flex; justify-content: space-between; align-items: center; }.calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }.calendar-grid span { display: grid; place-items: center; min-height: 44px; border-radius: 50%; color: var(--color-text-muted); }.calendar-grid .done { background: var(--color-primary-600); color: white; }.calendar-grid .today { border: 1px solid var(--color-primary-600); color: var(--color-primary-700); animation: pulse-ring 1.6s infinite; }
.task-row { display: grid; grid-template-columns: 36px 1fr auto; gap: 10px; align-items: center; min-height: 56px; border-bottom: 1px solid var(--color-border-subtle); }.task-row button:first-child { width: 36px; height: 36px; border-radius: 50%; border: 1px solid var(--color-border-default); background: white; }.task-row.done strong { text-decoration: line-through; color: var(--color-text-muted); }.task-row.done button:first-child { background: var(--color-success-500); color: white; }
.mini-bars { height: 160px; display: flex; align-items: end; gap: 8px; }.mini-bars i { flex: 1; border-radius: 8px 8px 0 0; background: var(--color-primary-600); }.badge-wall, .badges { display: flex; flex-wrap: wrap; gap: 8px; }.badge-wall span, .badges span { display: grid; place-items: center; min-width: 64px; min-height: 64px; border: 1px solid #F59E0B; border-radius: 12px; color: var(--color-warning-700); }.badge-wall .locked, .badges .locked { filter: grayscale(1); opacity: .5; border-color: var(--color-border-default); }
.profile-page { max-width: 800px; margin: 0 auto; display: grid; gap: 16px; }.profile-hero { grid-template-columns: auto 1fr auto; min-height: 160px; background: linear-gradient(135deg,#4338CA,#8B5CF6); color: white; }.big-avatar { width: 80px; height: 80px; border-radius: 50%; border: 4px solid white; font-size: 26px; font-weight: 700; position: relative; }.big-avatar svg { position: absolute; right: 0; bottom: 0; border-radius: 50%; background: var(--color-primary-600); padding: 3px; }.profile-hero h1 { margin: 0; }.profile-hero p { display: flex; align-items: center; gap: 6px; margin: 4px 0; color: rgba(255,255,255,0.78); }.profile-hero aside strong { display: block; font-size: 36px; }
.achievement-row { grid-template-columns: repeat(4, 1fr); }.profile-form { display: grid; gap: 12px; }.profile-form label { display: grid; gap: 6px; color: var(--color-text-secondary); }.toggle-line, .check-line { display: flex; align-items: center; gap: 10px; }.time-input { width: 120px; margin-left: auto; }
.modal-mask { position: fixed; inset: 0; z-index: var(--z-modal-bg); display: grid; place-items: center; background: rgba(15,23,42,0.36); backdrop-filter: blur(8px); }.join-modal { width: 480px; max-width: calc(100vw - 32px); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-xl); padding: 20px; }.modal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }.modal-head h2 { flex: 1; margin: 0; color: var(--color-text-primary); }.code-input { display: grid; grid-template-columns: 1fr auto; align-items: center; height: 56px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 0 12px; }.code-input input { border: 0; outline: 0; text-align: center; letter-spacing: 8px; font: 20px var(--font-family-mono); text-transform: uppercase; }.code-input.ok { border-color: var(--color-success-500); }.code-input.error { border-color: var(--color-danger-500); }.field-error { color: var(--color-danger-700); }.preview-course { display: grid; grid-template-columns: 48px 1fr; gap: 10px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); margin-top: 14px; padding: 12px; }.preview-course span { display: grid; place-items: center; border-radius: 10px; color: white; }.preview-course small { color: var(--color-text-muted); }.hint-line { display: flex; align-items: center; gap: 6px; color: var(--color-warning-700); background: var(--color-warning-50); border-radius: var(--radius-md); margin-top: 12px; padding: 8px; }.join-modal footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.study-room { min-height: 100vh; background: #0A0F1E; color: white; animation: enter-study 500ms var(--ease-out); }.study-head { position: fixed; inset: 0 0 auto; z-index: var(--z-sticky); height: 48px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; background: rgba(10,15,30,0.8); backdrop-filter: blur(12px); padding: 0 16px; }.study-head > div { display: flex; align-items: center; gap: 10px; }.study-head > div:last-child { justify-content: end; }.glass-btn, .icon-glass { display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: var(--radius-full); background: rgba(255,255,255,0.08); color: white; padding: 8px 10px; }.icon-glass { width: 34px; height: 34px; justify-content: center; padding: 0; }
.study-main { display: grid; grid-template-columns: 1fr 380px; min-height: 100vh; transition: grid-template-columns 300ms var(--ease-out); }.study-room.panelClosed .study-main { grid-template-columns: 1fr 0; }.slide-stage { position: relative; display: grid; place-items: center; padding: 72px 32px 120px; overflow: hidden; }.slide-card { position: relative; width: min(960px, 92%); aspect-ratio: 16/9; display: grid; align-content: center; gap: 18px; border-radius: 8px; background: white; color: var(--color-text-primary); box-shadow: 0 0 0 1px rgba(255,255,255,0.1), 0 24px 48px rgba(0,0,0,0.6); padding: 52px; }.slide-card h1 { margin: 0; font-size: 30px; }.slide-card p { font-size: 18px; line-height: 1.8; }.page-badge, .knowledge-dot { position: absolute; border-radius: var(--radius-full); background: rgba(0,0,0,0.42); color: white; padding: 4px 8px; }.page-badge { right: 16px; bottom: 16px; }.knowledge-dot { right: 16px; top: 16px; background: var(--color-ai-gradient); }
.subtitle-line { position: absolute; bottom: 100px; max-width: 80%; border-radius: var(--radius-full); background: rgba(10,15,30,0.82); backdrop-filter: blur(10px); padding: 12px 24px; color: rgba(255,255,255,0.74); }.subtitle-line strong { color: white; font-weight: 600; }
.player-bar { position: absolute; left: 50%; bottom: 20px; width: min(880px, 75%); min-height: 56px; display: grid; grid-template-columns: auto auto auto auto 1fr auto auto auto auto; align-items: center; gap: 10px; transform: translateX(-50%); border-radius: var(--radius-full); background: rgba(255,255,255,0.96); color: var(--color-text-primary); padding: 6px 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }.round-btn { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 50%; }.round-btn.primary { width: 44px; height: 44px; background: var(--color-primary-600); color: white; }.round-btn.ghost { background: transparent; color: var(--color-text-secondary); }.range { width: 100%; accent-color: var(--color-primary-600); }.time { font-family: var(--font-family-mono); color: var(--color-text-muted); font-size: 12px; }
.lesson-ai { min-width: 0; overflow: hidden; background: white; color: var(--color-text-body); border-left: 1px solid var(--color-border-default); display: grid; grid-template-rows: auto 1fr; }.study-room.panelClosed .lesson-ai { border: 0; }.study-tabs { height: 56px; padding: 0 12px; }.script-view, .class-chat, .note-view { overflow: auto; padding: 16px; }.sticky-tools { position: sticky; top: 0; display: flex; justify-content: space-between; background: white; border-bottom: 1px solid var(--color-border-subtle); padding-bottom: 10px; }.sticky-tools button { display: flex; gap: 5px; border: 0; background: transparent; color: var(--color-primary-700); }.reading { border-left: 3px solid var(--color-primary-600); background: var(--color-primary-50); border-radius: 8px; padding: 14px; line-height: 1.75; }.context-bar { display: flex; gap: 6px; border-radius: var(--radius-lg); background: var(--color-primary-50); color: var(--color-primary-700); padding: 8px; font-size: 12px; }.chat-disclaimer { text-align: center; color: var(--color-text-muted); font-size: 11px; margin: 8px 0; }.chat-input.compact { border-radius: var(--radius-lg); }.note-tools { display: flex; gap: 8px; align-items: center; }.note-tools button { border: 1px solid var(--color-border-default); border-radius: 6px; background: white; }.note-tools span { margin-left: auto; color: var(--color-text-muted); }.note-view textarea { width: 100%; min-height: 520px; border: 0; outline: 0; resize: none; font-size: 14px; line-height: 1.75; padding: 16px 0; }.note-view footer { display: flex; align-items: center; gap: 10px; color: var(--color-text-muted); }
.thumb-panel { position: fixed; z-index: var(--z-fixed); left: 0; top: 48px; bottom: 0; width: 200px; background: rgba(10,15,30,0.9); backdrop-filter: blur(12px); padding: 16px; }.thumb-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 14px; }.thumb-grid button { position: relative; height: 48px; border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; background: rgba(255,255,255,0.08); color: white; }.thumb-grid .active { border: 2px solid var(--color-primary-500); }.thumb-grid .learned svg { position: absolute; right: 4px; top: 4px; border-radius: 50%; background: var(--color-success-500); }
.settings-pop { position: fixed; right: 18px; top: 54px; z-index: var(--z-dropdown); display: grid; gap: 4px; border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 8px; }.settings-pop button { border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 8px 12px; }.settings-pop .active { background: var(--color-primary-50); color: var(--color-primary-700); }
.complete-modal { position: relative; overflow: hidden; width: 640px; border-radius: 24px; background: white; color: var(--color-text-body); text-align: center; box-shadow: var(--shadow-xl); padding: 40px; }.complete-modal > svg { color: #8B5CF6; }.complete-modal h2 { margin: 10px 0 0; color: var(--color-text-primary); }.done-stats { display: flex; justify-content: center; gap: 24px; border-top: 1px solid var(--color-border-subtle); border-bottom: 1px solid var(--color-border-subtle); margin: 20px 0; padding: 16px; }.ai-summary { display: flex; gap: 8px; border-radius: var(--radius-lg); background: var(--color-ai-light); color: #6D28D9; padding: 12px; text-align: left; }.complete-modal footer { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }.confetti i { position: absolute; bottom: 120px; width: 8px; height: 12px; animation: confetti 1.5s ease-out both; }
.bottom-tabs { position: fixed; left: 0; right: 0; bottom: 0; z-index: var(--z-fixed); height: 64px; display: grid; grid-template-columns: repeat(5, 1fr); border-top: 1px solid var(--color-border-default); background: rgba(255,255,255,0.9); backdrop-filter: blur(12px); }.bottom-tabs button { position: relative; display: grid; justify-items: center; align-content: center; gap: 2px; border: 0; background: transparent; color: var(--color-text-muted); font-size: 11px; }.bottom-tabs button span { display: grid; place-items: center; transition: transform 120ms var(--ease-spring), color 150ms; }.bottom-tabs button.active span { transform: scale(1.15); color: var(--color-primary-600); }.bottom-tabs button.active { color: var(--color-primary-600); }.bottom-tabs button i { width: 6px; height: 6px; border-radius: 50%; background: transparent; }.bottom-tabs .active i { background: var(--color-primary-600); }.bottom-tabs .ai span { width: 52px; height: 52px; border-radius: 50%; background: var(--color-ai-gradient); color: white; box-shadow: 0 4px 12px rgba(99,102,241,0.4); transform: translateY(-12px); }.bottom-tabs .ai.active span { transform: translateY(-12px) scale(1.06); }.bottom-tabs .ai { color: var(--color-primary-700); }
.tag { display: inline-flex; align-items: center; gap: 4px; min-height: 22px; border-radius: var(--radius-full); background: var(--color-bg-muted); color: var(--color-text-secondary); padding: 0 8px; font-size: 12px; }.tag-primary { background: var(--color-primary-50); color: var(--color-primary-700); }.tag-success { background: var(--color-success-50); color: var(--color-success-700); }.tag-warning { background: var(--color-warning-50); color: var(--color-warning-700); }.tag-danger { background: var(--color-danger-50); color: var(--color-danger-700); }.tag-ai { background: var(--color-ai-light); color: #6D28D9; border: 1px solid var(--color-ai-border); }
.empty { min-height: 120px; display: grid; place-items: center; gap: 8px; color: var(--color-text-muted); text-align: center; }
.ghost-row { width: 100%; min-height: 36px; display: flex; align-items: center; justify-content: center; gap: 6px; border: 0; background: transparent; color: var(--color-primary-700); }
@keyframes pulse-ring { 0%,100% { box-shadow: 0 0 0 0 rgba(79,70,229,0.35); } 50% { box-shadow: 0 0 0 7px rgba(79,70,229,0); } }
@keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }
@keyframes thinking { 0%,100% { opacity: .3; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }
@keyframes bubble-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes enter-study { from { opacity: 0; filter: brightness(1.8); transform: scale(1.02); } to { opacity: 1; filter: brightness(1); transform: scale(1); } }
@keyframes confetti { from { transform: translateY(0) rotate(0); opacity: 1; } to { transform: translateY(-220px) rotate(420deg); opacity: 0; } }
@keyframes result-pop { from { opacity: 0; transform: scale(.96); } to { opacity: 1; transform: scale(1); } }
.segmented { display: inline-flex; width: fit-content; overflow: hidden; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 3px; }.segmented button { min-height: 32px; border: 0; border-radius: var(--radius-full); background: transparent; color: var(--color-text-secondary); padding: 0 14px; }.segmented .active { background: var(--color-primary-600); color: white; }
.page-switch-enter-active, .page-switch-leave-active, .fade-slide-enter-active, .fade-slide-leave-active, .popover-enter-active, .popover-leave-active, .modal-pop-enter-active, .modal-pop-leave-active, .drawer-enter-active, .drawer-leave-active, .study-top-enter-active, .study-top-leave-active, .player-pop-enter-active, .player-pop-leave-active, .subtitle-enter-active, .subtitle-leave-active, .thought-roll-enter-active, .thought-roll-leave-active { transition: all 250ms var(--ease-out); }
.page-switch-enter-from, .page-switch-leave-to, .fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(6px); }
.thought-roll-enter-from, .thought-roll-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.thought-roll-enter-to, .thought-roll-leave-from { opacity: 1; max-height: 160px; }
.popover-enter-from, .popover-leave-to, .modal-pop-enter-from, .modal-pop-leave-to { opacity: 0; transform: translateY(-8px) scale(.98); }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }
.study-top-enter-from, .study-top-leave-to { opacity: 0; transform: translateY(-12px); }
.player-pop-enter-from, .player-pop-leave-to, .subtitle-enter-from, .subtitle-leave-to { opacity: 0; transform: translate(-50%, 8px); }
.slide-next-enter-active, .slide-next-leave-active, .slide-prev-enter-active, .slide-prev-leave-active { transition: all 300ms var(--ease-out); }
.slide-next-enter-from { opacity: 0; transform: translateX(30px); }.slide-next-leave-to { opacity: 0; transform: translateX(-30px); }.slide-prev-enter-from { opacity: 0; transform: translateX(-30px); }.slide-prev-leave-to { opacity: 0; transform: translateX(30px); }
.search-expand-enter-active, .search-expand-leave-active { transition: all 350ms var(--ease-out); }.search-expand-enter-from, .search-expand-leave-to { opacity: 0; transform: scaleX(.94); }
.thumb-panel-enter-active, .thumb-panel-leave-active { transition: transform 300ms var(--ease-out), opacity 300ms; }.thumb-panel-enter-from, .thumb-panel-leave-to { transform: translateX(-100%); opacity: 0; }
@media (max-width: 900px) {
  .home-grid, .course-layout, .tutoring-grid, .plans-grid, .knowledge-layout, .wrong-layout, .student-course-grid, .practice-maker { grid-template-columns: 1fr; }
  .quick-row, .achievement-row { grid-template-columns: repeat(2, 1fr); }
  .study-main { grid-template-columns: 1fr; }
  .lesson-ai { position: fixed; right: 0; top: 48px; bottom: 0; width: min(380px, 92vw); z-index: var(--z-fixed); }
}
</style>
