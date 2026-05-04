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
            <div class="slide-content lesson-markdown" v-html="activePageHtml"></div>
          </article>
        </transition>
        <transition name="subtitle">
          <div v-if="subtitleMode !== 'hide' && activeSubtitleText" class="subtitle-line">
            <div class="lesson-markdown" v-html="activeSubtitleHtml"></div>
          </div>
        </transition>
        <transition name="player-pop">
          <div v-show="chromeVisible || !audioPlaying" class="player-bar">
            <button class="round-btn ghost" @click="firstPage"><SkipBack :size="18" /></button>
            <button class="round-btn primary" @click="toggleAudio"><component :is="audioPlaying ? Pause : Play" :size="20" /></button>
            <button class="round-btn ghost" @click="nextPage"><SkipForward :size="18" /></button>
            <span class="time">{{ audioTime }}</span>
            <AppSlider v-model="audioProgress" class="range" :min="0" :max="100" @input="seekAudio" />
            <span class="time">{{ audioDuration }}</span>
            <PopoverButton :items="speedItems" :label="`${playbackRate}x`" placement="top" @select="setRate" />
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
            <div class="sticky-tools"><span>当前页 {{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</span><button @click="copyText(activeScriptText || activePageText)"><Copy :size="14" />复制</button></div>
            <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
            <div class="reading lesson-markdown" v-html="activeScriptHtml"></div>
          </section>
          <section v-else-if="classroomTab === 'qa'" key="qa" class="class-chat">
            <div class="context-bar"><Info :size="14" />第{{ currentPage }}页内容</div>
              <div class="class-chat-scroll">
              <ChatList :messages="classMessages" :thinking="classThinking" @toggle-thought="toggleThought" @copy="copyText" />
            </div>
            <div class="class-chat-dock">
              <div v-if="classQaAttachments.length" class="qa-attachment-strip compact">
                <div v-for="(item, index) in classQaAttachments" :key="`${item.url}-${index}`" class="qa-attachment-chip">
                  <img :src="item.url" alt="" />
                  <span>{{ item.filename || '图片' }}</span>
                  <button type="button" @click="removeQaAttachment('class', index)"><X :size="13" /></button>
                </div>
              </div>
              <form class="chat-input compact" @submit.prevent="askInClass">
                <input ref="classQaImageInput" class="qa-image-input" type="file" accept="image/*" @change="handleQaImageChange($event, 'class')" />
                <button type="button" class="attach-btn" :data-loading="classQaImageUploading" :disabled="classThinking || classQaImageUploading || classQaAttachments.length >= 3" title="上传图片" @click="classQaImageInput?.click()"><Camera :size="17" /></button>
                <textarea v-model="classQuestion" placeholder="问问 AI 这一页..." rows="1"></textarea>
                <button :disabled="(!classQuestion.trim() && !classQaAttachments.length) || classThinking || classQaImageUploading" :data-loading="classThinking" class="send-btn"><Send :size="18" /></button>
              </form>
              <div class="quick-tags">
                <button v-for="item in quickPageQuestions" :key="item" @click="sendQuickClass(item)">{{ item }}</button>
              </div>
            </div>
          </section>
          <section v-else key="note" class="note-view">
            <div class="note-tools" role="toolbar" aria-label="笔记格式工具">
              <button type="button" title="加粗" @click="formatNote('bold')"><strong>B</strong></button>
              <button type="button" title="斜体" @click="formatNote('italic')"><i>I</i></button>
              <button type="button" title="标记重点" @click="formatNote('mark')"><Flag :size="14" />标记</button>
              <span class="note-state" :class="{ dirty: noteState !== '已保存' }">{{ noteState }}</span>
            </div>
            <textarea ref="pageNoteArea" v-model="pageNote" class="note-editor" placeholder="记录你对这一页的理解、疑问或总结..." @input="queueNoteSave"></textarea>
            <footer class="note-footer"><button class="btn btn-primary btn-sm" :data-loading="noteState === '保存中'" :disabled="noteState === '保存中'" @click="saveCurrentNote">保存笔记</button><span>{{ noteSavedAt }}</span></footer>
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
          <footer><button class="btn btn-primary" @click="nextLessonAfterComplete">下一课时</button><button class="btn btn-secondary" @click="returnCourse">回课程</button><button class="btn btn-ghost" @click="go('studentQuizzes')">做练习</button></footer>
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
      <nav class="student-nav-links" aria-label="学生端主导航">
        <button
          v-for="item in topNavTabs"
          :key="item.key"
          type="button"
          class="student-nav-link"
          :class="{ active: isStudentNavActive(item.key), ai: item.key === 'studentQa' }"
          @click="go(item.key)"
        >
          <component :is="item.icon" :size="16" />
          {{ item.label }}
        </button>
      </nav>
      <div ref="topActionsRef" class="top-actions">
        <button class="top-icon" title="全局搜索" aria-label="全局搜索" @click="openSearch"><Search :size="19" /></button>
        <button class="top-icon" title="通知中心" aria-label="通知中心" :data-loading="notificationLoading" @click="toggleNotifications"><Bell :size="19" /><em v-if="unreadCount">{{ unreadCount }}</em></button>
        <button class="avatar-btn" title="个人档案" aria-label="个人档案" @click="userMenuOpen = !userMenuOpen">
          <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" />
          <DefaultUserAvatar v-else />
        </button>
      </div>
      <transition name="top-menu">
        <div v-if="noticeOpen" ref="noticePopRef" class="notice-pop top-menu-panel">
          <div v-for="item in notifications" :key="item.id || `${item.type}-${item.title}`" class="notice-item"><Bell :size="15" /><div><strong>{{ item.title }}</strong><p v-if="item.message">{{ item.message }}</p><small>{{ item.course_name ? `${item.course_name} · ` : '' }}{{ relativeTime(item.time) }}</small></div><i v-if="item.unread"></i></div>
          <EmptyState v-if="!notifications.length" text="暂无通知" />
        </div>
      </transition>
      <transition name="top-menu">
        <div v-if="userMenuOpen" ref="userPopRef" class="user-pop top-menu-panel">
          <div class="user-card"><strong>{{ user.nickname }}</strong><small>{{ user.email }}</small></div>
          <button @click="go('studentProfile')"><User :size="15" />个人中心</button>
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
              <CalendarCheck :size="20" /><div><strong>今日计划</strong><small>查看并打卡今天的学习任务</small></div><span>{{ doneTasks }}/{{ todayTasks.length }}</span><AppProgress :value="todayDoneRate" /><button @click="go('studentPlans')">查看</button>
            </article>
            <article class="continue-card">
              <div class="continue-cover" :style="courseCoverStyle(continueLesson?.course || activeCourse)"><Presentation :size="32" /><span>P{{ continueProgressPage }}</span></div>
              <section v-if="continueLesson">
                <span class="tag tag-ai"><Sparkles :size="12" />接续上次</span>
                <h2>{{ continueLesson.lesson.title }}</h2>
                <p>第 {{ continueProgressPage }} 页 / 共 {{ continueLesson.lesson.page_count || 1 }} 页</p>
                <AppProgress :value="continueProgress" />
                <small>{{ continueTime }}</small>
                <button class="btn btn-primary" @click="openLesson(continueLesson.lesson.id)"><Play :size="16" />继续学习</button>
              </section>
              <section v-else class="empty-continue"><BookOpen :size="42" /><h2>还没有学习</h2><button class="btn btn-primary" @click="go('studentCourses')">浏览课程</button></section>
            </article>
            <div class="home-grid">
              <article class="panel-card">
                <div class="section-head"><h2><BookOpen :size="18" />我的课程</h2><button @click="go('studentCourses')">查看全部</button></div>
                <button v-for="course in courses.slice(0, 3)" :key="course.id" class="home-course" @click="openCourse(course.id)">
                  <span :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)"><BookOpen v-if="!course.cover_url" :size="21" /></span>
                  <div><strong>{{ course.name }}</strong><small>{{ course.teacher?.nickname || '教师' }} · {{ course.term }}</small><AppProgress :value="course.progress_percent || 0" /><em>{{ course.progress_percent || 0 }}%</em></div>
                </button>
                <button class="join-dashed" @click="joinOpen = true"><Plus :size="16" />加入新课程</button>
              </article>
              <article class="panel-card">
                <div class="section-head"><h2><BarChart2 :size="18" />我的学习</h2><button @click="go('studentProfile')">学习报告</button></div>
                <div class="rings"><RingBlock label="本周学习" :value="hourTargetRate" :text="`${stats.study_hours || 0}h`" sub="目标5h" /><RingBlock label="完成率" :value="stats.completion_rate || 0" :text="`${stats.completion_rate || 0}%`" sub="课时" tone="success" /><RingBlock label="正确率" :value="stats.accuracy || 0" :text="`${stats.accuracy || 0}%`" sub="练习" tone="ai" /></div>
                <div class="week-check"><span v-for="item in weekDays" :key="item.label" :class="{ done: item.done, today: item.today }">{{ item.label }}</span></div>
                <div class="streak"><Flame :size="16" />连续 {{ stats.streak_days || 0 }} 天</div>
              </article>
            </div>
            <article class="home-ai-recommend-card" :class="{ 'is-empty': !hasJoinedCourses }">
              <div class="home-ai-rec-left">
                <div class="home-ai-rec-header">
                  <div class="home-ai-icon-wrap">
                    <Sparkles v-if="hasJoinedCourses" :size="24" />
                    <BookOpen v-else :size="24" />
                  </div>
                  <h2>{{ hasJoinedCourses ? 'AI 今日推荐' : '加入课程后生成推荐' }}</h2>
                </div>
                <p class="home-ai-rec-content" v-if="hasJoinedCourses">
                  {{ studentRecommendationText }}
                </p>
                <p class="home-ai-rec-content" v-else>
                  AI 今日推荐会基于你加入的课程、学习进度、今日计划和错题薄弱点生成。当前账号还没有课程数据，所以不会生成课程学习建议。
                </p>
                <div class="home-ai-rec-footer">
                  <div class="home-data-tag">
                    <Sparkles :size="14" />{{ hasJoinedCourses ? '基于你的学习数据生成' : '等待课程数据' }}
                  </div>
                  <button class="home-refresh-btn" @click="hasJoinedCourses ? loadDashboard() : (joinOpen = true)">
                    <RefreshCw v-if="hasJoinedCourses" :size="14" />
                    <Plus v-else :size="14" />
                    {{ hasJoinedCourses ? '刷新建议' : '加入课程' }}
                  </button>
                </div>
              </div>

              <div class="home-ai-rec-actions">
                <button class="home-action-task-card" @click="openHomeRecommendedLesson">
                  <div class="home-task-info">
                    <span class="home-task-type"><BookOpen :size="14" />{{ hasJoinedCourses ? '推荐课时' : '课程入口' }}</span>
                    <span class="home-task-title">{{ homeRecommendedLessonTitle }}</span>
                  </div>
                  <div class="home-task-arrow"><ArrowRight :size="16" /></div>
                </button>
                <button class="home-action-task-card" @click="openHomeRecommendedPractice">
                  <div class="home-task-info">
                    <span class="home-task-type"><Pencil :size="14" />{{ hasJoinedCourses ? '推荐练习' : '练习入口' }}</span>
                    <span class="home-task-title">{{ homeRecommendedPracticeTitle }}</span>
                  </div>
                  <div class="home-task-arrow"><ArrowRight :size="16" /></div>
                </button>
              </div>
            </article>

            <article class="home-activity-card">
              <div class="home-ac-header">
                <div class="home-ac-title">
                  <Clock :size="24" />
                  学习动态
                </div>
                <button class="home-ac-view-all" @click="go('studentProfile')">查看全部记录 <ArrowRight :size="14" /></button>
              </div>
              <div v-if="homeActivityItems.length" class="home-activity-list">
                <div v-for="item in homeActivityItems" :key="item.key" class="home-activity-item">
                  <div class="home-ac-icon-wrapper" :class="item.tone">
                    <component :is="item.icon" :size="20" />
                  </div>
                  <div class="home-ac-content-wrap">
                    <div class="home-ac-meta">
                      <span class="home-ac-action-name">{{ item.action }}</span>
                      <span class="home-ac-time">{{ item.timeText }}</span>
                    </div>
                    <div class="home-ac-detail" :class="{ quote: item.quote }">{{ item.detail }}</div>
                    <div v-if="item.progress !== null" class="home-mini-progress-bar">
                      <div class="home-mp-track">
                        <div class="home-mp-fill" :style="{ width: `${item.progress}%` }"></div>
                      </div>
                      <span class="home-mp-text">{{ item.progress }}%</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="home-activity-empty">
                <BookOpen :size="28" />
                <span>{{ hasJoinedCourses ? '暂无学习动态' : '加入课程后开始记录学习动态' }}</span>
              </div>
            </article>
          </template>

          <template v-else-if="active === 'studentCourses'">
            <PageTitle title="我的课程" :sub="`共 ${courses.length} 门课程`"><button class="btn btn-primary" @click="joinOpen = true"><Plus :size="16" />加入课程</button></PageTitle>
            <div class="course-tools"><div class="pretty-input"><Search :size="16" /><input v-model="courseKeyword" placeholder="搜索课程名称" /></div><SelectMenu v-model="termFilter" :items="termOptions" /></div>
            <div class="underline-tabs"><button :class="{ active: courseTab === 'active' }" @click="courseTab = 'active'"><BookOpen :size="16" />在学中({{ activeCourses.length }})</button><button :class="{ active: courseTab === 'done' }" @click="courseTab = 'done'"><CheckCircle :size="16" />已完成({{ doneCourses.length }})</button></div>
            <div class="student-course-grid">
              <article v-for="course in filteredCourses" :key="course.id" class="student-course-card">
                <div class="course-art" :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)"><BookOpen v-if="!course.cover_url" :size="56" /><span>{{ course.term }}</span><em><Check :size="12" />{{ course.progress_percent || 0 }}%</em><DropdownMenu :items="courseMenuItems" @select="handleCourseMenu($event, course)" /></div>
                <section><h2>{{ course.name }}</h2><p><User :size="14" />{{ course.teacher?.nickname || '教师' }} · {{ course.teacher?.bio || '课程教师' }}</p><AppProgress :value="course.progress_percent || 0" /><div class="course-meta"><span>已学 {{ course.studied_lessons || 0 }}/{{ course.lesson_total || 0 }}</span><span>{{ course.last_lesson ? relativeTime(course.last_progress?.updated_at) : '未开始' }}</span></div><div class="mini-data"><span><MessageCircle :size="14" />{{ course.qa_count || 0 }}</span><span><XCircle :size="14" />{{ course.wrong_count || 0 }}</span><span><Users :size="14" />{{ course.student_count || 0 }}</span></div><button class="btn btn-primary full" @click="openCourse(course.id)"><Play :size="16" />继续学习</button></section>
              </article>
            </div>
            <EmptyState v-if="!filteredCourses.length" text="暂无课程" />
          </template>

          <template v-else-if="active === 'studentCourseHome'">
            <CourseRequired v-if="!courseHome.course" />
            <template v-else>
              <article class="course-hero-student" :class="{ 'has-image': courseHome.course.cover_url }" :style="courseHeroStyle(courseHome.course)">
                <section><h1>{{ courseHome.course.name }}</h1><p><User :size="16" />{{ courseHome.teacher?.nickname || '教师' }} · {{ courseHome.course.term }}</p><div><Check :size="16" />已完成 {{ courseHome.stats?.completion_rate || 0 }}% <AppProgress :value="courseHome.stats?.completion_rate || 0" class="hero-progress" tone="success" /><Users :size="16" />{{ courseHome.student_count || 0 }}名同学</div></section>
                <aside><div class="slide-mini">{{ latestLesson?.title?.slice(0, 8) || '课时' }}</div><button class="btn white-fill" @click="latestLesson && openLesson(Number(latestLesson.id))"><Play :size="16" />进入课时</button></aside>
              </article>
              <div class="quick-row"><QuickTile :icon="Presentation" label="课时学习" :sub="`${courseHome.lessons?.length || 0} 个课时`" @click="scrollToLessons" /><QuickTile :icon="MessageCircle" label="知识问答" sub="AI 解答" @click="go('studentQa')" /><QuickTile :icon="FolderOpen" label="课程资料" :sub="`${courseHome.materials?.length || 0} 份文件`" @click="courseSection = 'materials'" /><QuickTile :icon="ClipboardList" label="章节练习" sub="自选练习" @click="go('studentQuizzes')" /></div>
              <div class="course-layout">
                <section>
                  <article id="lesson-list" class="panel-card"><div class="section-head"><h2><Presentation :size="18" />课时列表</h2><span class="tag">全部 {{ courseHome.lessons?.length || 0 }}</span></div><LessonItem v-for="(lesson, index) in courseHome.lessons || []" :key="lesson.id" :lesson="lesson" :index="Number(index)" @open="openLesson(Number(lesson.id))" /></article>
                  <article class="panel-card"><div class="section-head"><h2><FolderOpen :size="18" />课程资料</h2><button @click="materialsExpanded = !materialsExpanded">{{ materialsExpanded ? '收起' : '展开' }}</button></div><MaterialRow v-for="item in visibleCourseMaterials" :key="item.id" :item="item" /><button v-if="(courseHome.materials || []).length > 5" class="ghost-row" @click="materialsExpanded = !materialsExpanded"><ChevronDown :size="16" />{{ materialsExpanded ? '收起' : `展开更多` }}</button></article>
                </section>
                <aside>
                  <article class="panel-card"><div class="section-head"><h2><BarChart2 :size="18" />我的数据</h2></div><div class="data-grid"><MiniMetric :icon="Clock" label="学习时长" :value="`${courseHome.stats?.study_hours || 0}h`" /><MiniMetric :icon="CheckCircle" label="完成进度" :value="`${courseHome.stats?.completion_rate || 0}%`" tone="success" /><MiniMetric :icon="MessageCircle" label="问答次数" :value="courseHome.stats?.qa_count || 0" tone="ai" /><MiniMetric :icon="XCircle" label="错题数" :value="courseHome.stats?.wrong_count || 0" tone="danger" /><MiniMetric :icon="Star" label="正确率" :value="`${courseHome.stats?.accuracy || 0}%`" tone="warning" /><MiniMetric :icon="Zap" label="连续打卡" :value="`${courseHome.stats?.streak_days || 0}天`" tone="warning" /></div></article>
                  <article class="ask-card"><Sparkles :size="20" /><h2>向 AI 提问</h2><form @submit.prevent="askCourseQuick"><input v-model="quickCourseQuestion" placeholder="这节课有什么不懂的..." /><button><Send :size="16" /></button></form><div class="quick-tags"><button v-for="item in courseHome.quick_questions || []" :key="item" @click="sendCourseQuick(item)">{{ item }}</button></div></article>
                  <article class="panel-card recent-qa-card"><div class="section-head"><h2><MessageCircle :size="18" />最近提问</h2><button @click="go('studentQa')">全部</button></div><div v-for="item in courseHome.recent_qa || []" :key="item.id" class="qa-mini"><strong>{{ item.question }}</strong><p>{{ item.answer }}</p></div><EmptyState v-if="!(courseHome.recent_qa || []).length" text="暂无提问" /></article>
                </aside>
              </div>
            </template>
          </template>

          <template v-else-if="active === 'studentQa'">
            <section class="qa-modern-page" :class="{ empty: !globalMessages.length }">
              <div class="qa-scroll-area">
                <div class="chat-wrapper">
                  <div class="qa-header">
                    <div class="qa-title-group">
                      <div class="qa-title-icon"><Sparkles :size="24" /></div>
                      <section class="qa-title">
                        <h1>《{{ courseScopeName }}》AI 问答</h1>
                      </section>
                    </div>
                    <div class="qa-header-actions">
                      <CourseSelect />
                      <button class="qa-tutoring-link" type="button" @click="go('studentTutoring')"><Pencil :size="13" />题目辅导</button>
                      <button class="action-circle-btn" type="button" :class="{ active: historyOpen }" title="问答历史" aria-label="问答历史" @click="openQaHistory"><Clock :size="18" /></button>
                    </div>
                  </div>
                  <div v-if="!globalMessages.length" class="qa-welcome"><Sparkles :size="48" /><h2>{{ courseScopeName }}专属问答</h2></div>
                  <ChatList v-else :messages="globalMessages" :thinking="globalThinking" large @toggle-thought="toggleThought" @copy="copyText" @favorite="favoriteQaMessage" @feedback="feedbackQaMessage" />
                  <div v-if="!globalMessages.length" class="prompt-grid"><button v-for="item in promptCards" :key="item.text" @click="sendGlobalQuick(item.text)"><component :is="item.icon" :size="18" />{{ item.text }}</button></div>
                </div>
              </div>
              <form class="input-dock-container" @submit.prevent="askGlobal">
                <div class="input-wrapper">
                  <div class="context-badge"><BookOpen :size="14" />当前课程空间：《{{ courseScopeName }}》</div>
                  <div v-if="globalQaAttachments.length" class="qa-attachment-strip">
                    <div v-for="(item, index) in globalQaAttachments" :key="`${item.url}-${index}`" class="qa-attachment-chip">
                      <img :src="item.url" alt="" />
                      <span>{{ item.filename || '图片' }}</span>
                      <button type="button" @click="removeQaAttachment('global', index)"><X :size="13" /></button>
                    </div>
                  </div>
                  <section class="input-box">
                    <input ref="globalQaImageInput" class="qa-image-input" type="file" accept="image/*" @change="handleQaImageChange($event, 'global')" />
                    <button type="button" class="attach-btn" :data-loading="globalQaImageUploading" :disabled="globalThinking || globalQaImageUploading || globalQaAttachments.length >= 3" title="上传图片" @click="globalQaImageInput?.click()"><Camera :size="18" /></button>
                    <textarea v-model="globalQuestion" placeholder="输入问题" rows="1"></textarea>
                    <button :disabled="(!globalQuestion.trim() && !globalQaAttachments.length) || globalThinking || globalQaImageUploading" :data-loading="globalThinking" class="send-btn"><Send :size="20" /></button>
                  </section>
                </div>
              </form>
              <transition name="drawer"><aside v-if="historyOpen" class="history-drawer"><div class="drawer-head"><h2>{{ courseScopeName }}问答历史</h2><button type="button" @click="historyOpen = false"><X :size="16" /></button></div><div class="pretty-input"><Search :size="15" /><input v-model="qaKeyword" placeholder="搜索本课程历史问答" @keyup.enter="loadQaHistory" /></div><button type="button" class="history-favorite-toggle" :class="{ checked: showFavorites }" :aria-pressed="showFavorites" @click="showFavorites = !showFavorites"><span class="favorite-check-box" aria-hidden="true"></span><strong>仅看收藏</strong></button><button v-for="item in filteredQaHistory" :key="item.id" class="history-row" type="button" @click="reuseHistory(item)"><MessageCircle :size="13" /><span>{{ item.question }}</span><small>{{ formatTime(item.created_at) }}</small></button><EmptyState v-if="!filteredQaHistory.length" text="本课程暂无问答记录" /></aside></transition>
            </section>
          </template>

          <template v-else-if="active === 'studentTutoring'">
            <section class="tutoring-page">
              <PageTitle title="题目辅导">
                <CourseSelect />
                <span class="tag tag-ai"><Sparkles :size="12" />分步提示</span>
              </PageTitle>

              <div class="tutoring-grid">
                <section class="panel-card tutor-input">
                  <div class="tutor-card-head">
                    <div>
                      <span class="tutor-eyebrow"><BookOpen :size="14" />当前课程</span>
                      <h2>{{ courseScopeName }}</h2>
                    </div>
                    <span class="tutor-status" :class="{ active: !!activeProblem }">{{ activeProblem ? '辅导中' : '待提交' }}</span>
                  </div>

                  <div class="seg-tabs tutor-mode-tabs">
                    <button type="button" :class="{ active: problemMode === 'text' }" @click="problemMode = 'text'"><Type :size="16" />文字输入</button>
                    <button type="button" :class="{ active: problemMode === 'image' }" @click="problemMode = 'image'"><Camera :size="16" />图片上传</button>
                  </div>

                  <div class="problem-editor-wrap">
                    <textarea
                      v-if="problemMode === 'text'"
                      v-model="problemText"
                      maxlength="500"
                      placeholder="题目内容"
                      class="problem-text"
                    ></textarea>
                    <label v-else class="image-drop" :class="{ 'ocr-scanning': ocrScanning }">
                      <input ref="problemFile" type="file" accept="image/*" @change="createImageProblem" />
                      <span class="upload-icon"><Camera :size="34" /></span>
                      <strong>{{ ocrScanning ? '正在识别题目' : '上传题目截图' }}</strong>
                    </label>
                  </div>

                  <div class="tutor-input-meta">
                    <span>{{ problemMode === 'text' ? `${problemText.length} / 500字` : '图片模式' }}</span>
                    <span>{{ selectedCourseId ? `《${courseScopeName}》` : '请先选择课程' }}</span>
                  </div>

                  <div v-if="activeProblem" class="knowledge-box">
                    <Sparkles :size="14" />
                    <strong>识别知识点</strong>
                    <span v-for="item in activeProblem.knowledge_points || []" :key="item" class="tag tag-primary">{{ item }}</span>
                    <span v-if="!(activeProblem.knowledge_points || []).length" class="tag">待分析</span>
                  </div>

                  <button
                    type="button"
                    class="btn btn-ai full tutor-submit-btn"
                    :data-loading="problemSubmitting || ocrScanning"
                    :disabled="problemMode === 'text' ? (problemSubmitting || !selectedCourseId || !problemText.trim()) : (ocrScanning || !selectedCourseId)"
                    @click="problemMode === 'text' ? createTextProblem() : problemFile?.click()"
                  >
                    <Sparkles :size="16" />{{ problemMode === 'text' ? '开始辅导' : '上传并识别' }}
                  </button>
                </section>

                <aside class="panel-card guide-card">
                  <div class="section-head">
                    <h2><Sparkles :size="18" />{{ activeProblem ? 'AI 辅导进行中' : '等待题目输入' }}</h2>
                    <span v-if="activeProblem" class="tag tag-success">3步引导</span>
                  </div>

                  <article v-if="activeProblem" class="active-problem-card">
                    <span>当前题目</span>
                    <p>{{ activeProblem.corrected_text || activeProblem.ocr_text || activeProblem.raw_text || problemText || '已提交题目' }}</p>
                  </article>

                  <EmptyGuide v-if="!activeProblem" />
                  <div v-else class="guide-step-list">
                    <GuideStep v-for="level in [1,2,3]" :key="level" :level="level" :data="guidance[level]" :open="guideOpen[level]" @toggle="toggleGuide(level)" @load="loadGuidance(level)" />
                  </div>
                </aside>
              </div>

              <HistoryStrip title="历史辅导记录" :items="problemHistory" @pick="selectProblem" />
            </section>
          </template>

          <template v-else-if="active === 'studentKnowledge'">
            <PageTitle title="知识点精讲"><CourseSelect /></PageTitle>
            <div class="knowledge-layout"><aside class="knowledge-tree"><div class="pretty-input"><Search :size="15" /><input v-model="knowledgeKeyword" placeholder="搜索知识点" /></div><button v-for="chapter in courseHome.chapters || []" :key="chapter.id" @click="selectedChapterId = chapter.id; loadKnowledge()"><ChevronRight :size="14" />{{ chapter.title }}</button><div class="weak-tags"><strong><Zap :size="14" />薄弱知识点</strong><span v-for="item in weakPoints.slice(0, 3)" :key="item.knowledge_point" class="tag tag-danger">{{ item.knowledge_point }}</span></div></aside><section class="knowledge-content"><article class="knowledge-head"><h1>{{ selectedKnowledge?.name || '选择知识点' }}</h1><p>所属：{{ chapterName(selectedKnowledge?.chapter_id) }}</p><span class="tag" :class="knowledgeMasteryClass">{{ knowledgeMasteryText }}</span><AppProgress :value="knowledgeMastery" :tone="knowledgeMastery >= 70 ? 'success' : knowledgeMastery >= 35 ? 'warning' : 'danger'" /></article><div class="segmented"><button v-for="item in levelItems" :key="item.value" type="button" :class="{ active: knowledgeLevel === item.value }" @click="knowledgeLevel = String(item.value)">{{ item.label }}</button></div><article class="knowledge-body"><KnowledgeBlock icon="Quote" title="定义" :content="knowledgeContent.definition" /><KnowledgeBlock icon="Layers" title="核心原理" :content="knowledgeContent.principle" ai /><KnowledgeBlock icon="Pencil" title="例题解析" :content="knowledgeContent.example" /><KnowledgeBlock icon="AlertTriangle" title="常见易错点" warning :content="knowledgeContent.common_mistake" /><div class="practice-cta"><Sparkles :size="16" />生成练习题<button @click="generateKnowledgeQuiz(5)">练习5题</button><button @click="generateKnowledgeQuiz(10)">练习10题</button></div></article></section></div>
          </template>

          <template v-else-if="active === 'studentQuizzes'">
            <div v-if="answeringQuiz" class="exam-answer-page"><QuizAnswerView :quiz="quizDetail" :answers="quizAnswers" :attempt="attempt" :submitting="quizSubmitting" @answer="setQuizAnswer" @submit="submitQuiz" @exit="answeringQuiz = false" /></div>
            <section v-else class="quiz-modern-page">
              <div class="quiz-modern-header">
                <div class="quiz-modern-title">
                  <h1>练习与测验</h1>
                  <p>课程配套测验与自定义章节练习</p>
                </div>
                <CourseSelect />
              </div>

              <div class="quiz-modern-tabs">
                <button type="button" :class="{ active: quizTab === 'course' }" @click="quizTab = 'course'"><ClipboardList :size="18" />课程测验</button>
                <button type="button" :class="{ active: quizTab === 'practice' }" @click="quizTab = 'practice'"><Layers :size="18" />章节练习</button>
              </div>

              <section v-if="quizTab === 'course'" class="quiz-list quiz-modern-list">
                <QuizCard v-for="quiz in courseQuizzes" :key="quiz.id" :quiz="quiz" @open="startQuiz(quiz.id)" />
                <EmptyState v-if="!courseQuizzes.length" text="暂无测验" />
              </section>

              <section v-else class="practice-modern-grid">
                <article class="practice-modern-card">
                  <div class="practice-card-header">
                    <div class="practice-card-icon"><Sparkles :size="24" /></div>
                    <h2>自选章节练习</h2>
                  </div>

                  <div class="practice-config-section">
                    <span class="practice-config-label">请选择要练习的章节（可多选）</span>
                    <div class="practice-chapter-chips">
                      <button
                        v-for="chapter in courseHome.chapters || []"
                        :key="chapter.id"
                        type="button"
                        class="practice-chip"
                        :class="{ active: selectedPracticeChapters.includes(chapter.id) }"
                        @click="togglePracticeChapter(chapter.id)"
                      >
                        {{ chapter.title }}
                      </button>
                    </div>
                    <EmptyState v-if="!(courseHome.chapters || []).length" text="暂无章节" />
                  </div>

                  <div class="practice-settings-row">
                    <div class="practice-segmented-control">
                      <button
                        v-for="item in quizCountOptions"
                        :key="item"
                        type="button"
                        :class="{ active: quizQuestionCount === item }"
                        @click="quizQuestionCount = item"
                      >
                        {{ item }}
                      </button>
                    </div>
                    <button type="button" class="practice-switch-wrapper" :class="{ active: smartQuiz }" @click="smartQuiz = !smartQuiz">
                      <span class="practice-switch"></span>
                      <strong>优先薄弱点</strong>
                    </button>
                  </div>

                  <button
                    type="button"
                    class="practice-generate-btn"
                    :data-loading="quizGenerating"
                    :disabled="quizGenerating || !selectedCourseId"
                    @click="generateQuiz"
                  >
                    <Sparkles :size="20" />智能生成练习
                  </button>
                  <p class="practice-generate-hint"></p>
                </article>

                <article class="practice-modern-card">
                  <button
                    type="button"
                    class="practice-feature-card"
                    :data-loading="wrongPracticeGenerating"
                    :disabled="wrongPracticeGenerating || !wrongQuestions.length"
                    @click="loadWrongPractice"
                  >
                    <div>
                      <div class="practice-feature-icon"><BookMarked :size="24" /></div>
                      <h2>错题重练</h2>
                      <p>{{ wrongQuestions.length ? `${wrongQuestions.length} 道错题` : '暂无错题' }}</p>
                    </div>
                    <span><Play :size="16" />{{ wrongQuestions.length ? '开始' : '暂无' }}</span>
                  </button>

                  <div class="practice-history-title"><History :size="18" />最近练习记录</div>
                  <div class="practice-history-list">
                    <button v-for="quiz in practiceQuizzes.slice(0, 5)" :key="quiz.id" type="button" class="practice-history-item" @click="startQuiz(quiz.id)">
                      <div class="practice-history-left">
                        <span class="practice-history-icon"><Layers :size="20" /></span>
                        <div>
                          <strong>{{ quiz.title }}</strong>
                          <small>{{ quizQuestionMeta(quiz) }} · {{ relativeTime(quiz.created_at) }}</small>
                        </div>
                      </div>
                      <em>{{ quizScoreLabel(quiz) }}</em>
                    </button>
                    <EmptyState v-if="!practiceQuizzes.length" text="暂无练习记录" />
                  </div>
                </article>
              </section>
            </section>
          </template>

          <template v-else-if="active === 'studentWrongBook'">
            <section class="wrong-book-page">
              <header class="wrong-dashboard-head">
                <div class="wrong-title-block">
                  <span class="wrong-title-icon"><BookMarked :size="22" /></span>
                  <div>
                    <h1>错题本</h1>
                    <p>《{{ courseScopeName }}》</p>
                  </div>
                </div>
                <div class="wrong-head-actions">
                  <CourseSelect />
                  <button class="btn btn-primary" :data-loading="wrongPracticeGenerating" :disabled="wrongPracticeGenerating || !wrongQuestions.length" @click="loadWrongPractice"><RefreshCw :size="16" />开始重练</button>
                </div>
              </header>

              <article class="wrong-hero">
                <div><strong>{{ wrongQuestions.length }}</strong><span>历史错题</span></div>
                <div><strong>{{ pendingWrongCount }}</strong><span>待重练</span></div>
                <div><strong>{{ repeatedWrongCount }}</strong><span>多次错误</span></div>
                <div><strong>{{ weeklyWrongCount }}</strong><span>本周新增</span></div>
              </article>

              <div class="wrong-layout">
                <aside class="wrong-tree">
                  <strong class="course-scope-label"><BookOpen :size="15" />{{ courseScopeName }}</strong>
                  <button type="button" :class="{ active: !selectedWrongKnowledge }" @click="selectedWrongKnowledge = ''"><Layers :size="16" />全部错题 <em>{{ wrongQuestions.length }}</em></button>
                  <strong>按知识点</strong>
                  <button v-for="item in wrongKnowledgeFilters" :key="item.name" type="button" :class="{ active: selectedWrongKnowledge === item.name }" @click="selectedWrongKnowledge = item.name">
                    <Zap :size="15" />{{ item.name }} <em>{{ item.count }}</em>
                  </button>
                </aside>
                <section class="wrong-list">
                  <div class="wrong-tools">
                    <div class="pretty-input"><Search :size="15" /><input v-model="wrongKeyword" placeholder="搜索题干或解析" /></div>
                    <SelectMenu v-model="wrongStatus" :items="wrongStatusOptions" />
                  </div>
                  <div v-if="selectedWrongKnowledge || wrongStatus || wrongKeyword" class="wrong-filter-state">
                    <span>{{ wrongFilterSummary }}</span>
                    <button type="button" @click="clearWrongFilters"><X :size="14" />清除</button>
                  </div>
                  <WrongCard v-for="item in filteredWrongQuestions" :key="item.wrong_question_id" :item="item" @practice="practiceWrong(item)" />
                  <EmptyState v-if="!filteredWrongQuestions.length" text="本课程暂无错题" />
                </section>
              </div>
            </section>
          </template>

          <template v-else-if="active === 'studentPlans'">
            <section class="student-plan-page">
              <div class="plan-banner">
                <div class="banner-left">
                  <div class="banner-icon"><CalendarCheck :size="32" /></div>
                  <div class="banner-title">学习计划 & 打卡</div>
                </div>

                <div class="banner-stats">
                  <div class="b-stat-item">
                    <h2>{{ stats.streak_days || 0 }}</h2>
                    <span>连续打卡</span>
                  </div>
                  <div class="b-stat-item">
                    <h2>{{ monthlyCheckins }}</h2>
                    <span>本月打卡</span>
                  </div>
                  <div class="b-stat-item">
                    <h2><Flame :size="28" />{{ Math.max(stats.streak_days || 0, 0) }}</h2>
                    <span>最长连续</span>
                  </div>
                </div>
              </div>

              <div class="plan-layout">
                <div class="main-col">
                  <article class="card">
                    <div class="calendar-nav">
                      <div class="cal-month">{{ planMonthLabel }}</div>
                      <div class="cal-arrows">
                        <button type="button" class="cal-arr-btn" @click="shiftPlanMonth(-1)"><ChevronLeft :size="18" /></button>
                        <button type="button" class="cal-arr-btn" @click="shiftPlanMonth(1)"><ChevronRight :size="18" /></button>
                      </div>
                    </div>

                    <div class="cal-weekdays">
                      <div v-for="day in planWeekHeaders" :key="day" class="cal-header-day">{{ day }}</div>
                    </div>

                    <div class="cal-grid">
                      <div v-for="cell in planCalendarCells" :key="cell.key" class="cal-day-wrapper">
                        <button
                          type="button"
                          class="cal-day"
                          :class="{ empty: cell.empty, checked: cell.checked, today: cell.today }"
                          :disabled="cell.empty"
                        >
                          {{ cell.label }}
                        </button>
                      </div>
                    </div>
                  </article>

                  <article class="card">
                    <div class="card-header">
                      <div class="card-title"><ListChecks :size="22" />今日任务</div>
                      <div class="card-subtitle">{{ doneTasks }} / {{ todayTasks.length }} 已完成</div>
                    </div>

                    <div v-if="todayTasks.length" class="plan-task-list">
                      <div v-for="task in todayTasks" :key="task.id" class="plan-task-row" :class="{ done: task.status === 'done' }">
                        <button type="button" class="plan-task-check" @click="checkinTask(task.id)">
                          <Check v-if="task.status === 'done'" :size="16" />
                        </button>
                        <div class="plan-task-body">
                          <strong>{{ task.title }}</strong>
                          <small>{{ task.estimated_minutes || 30 }} 分钟 · {{ task.task_type || '学习' }}</small>
                        </div>
                        <span class="plan-task-tag">{{ task.status === 'done' ? '已完成' : '待完成' }}</span>
                      </div>
                    </div>

                    <div v-else class="empty-task-state">
                      <div class="ai-sparkle-bg">
                        <Sparkles :size="40" />
                      </div>
                      <h3>今天还没有计划</h3>

                      <div class="ai-prompt-bar">
                        <input v-model="planForm.goal" type="text" placeholder="学习目标" @keyup.enter="createPlan" />
                        <button type="button" class="btn-ai-gen" :data-loading="planCreating" :disabled="planCreating || !planForm.goal.trim()" @click="createPlan">
                          <Sparkles :size="18" />AI 生成
                        </button>
                      </div>
                    </div>
                  </article>
                </div>

                <div class="side-col">
                  <article class="card">
                    <div class="card-header compact">
                      <div class="card-title"><BarChart2 :size="22" />本周学习</div>
                    </div>

                    <div class="mini-chart">
                      <div v-for="item in weeklyChart" :key="item.label" class="bar-col">
                        <div class="bar-track"><div class="bar-fill" :style="{ height: `${item.percent}%` }"></div></div>
                        <span class="bar-label">{{ item.label }}</span>
                      </div>
                    </div>
                    <div class="total-hours">共 <span>{{ totalWeeklyHours }}</span> 小时</div>
                  </article>

                  <article class="card">
                    <div class="card-header compact">
                      <div class="card-title achievement-title"><Award :size="22" />我的成就</div>
                    </div>

                    <div class="badges-grid">
                      <div v-for="item in planAchievementSlots" :key="item.key" class="badge-item" :class="{ unlocked: item.unlocked }">
                        <div class="badge-icon"><Award :size="28" /></div>
                        <span class="badge-name">{{ item.unlocked ? item.name : '?' }}</span>
                      </div>
                    </div>
                  </article>
                </div>
              </div>
            </section>
          </template>

          <template v-else-if="active === 'studentProfile'">
            <section class="profile-page">
              <div class="profile-pc-layout">
                <aside class="profile-side">
                  <article class="profile-identity-card">
                    <div class="profile-cover">
                      <span class="big-avatar">
                        <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" />
                        <DefaultUserAvatar v-else />
                        <Camera :size="14" class="camera-badge" />
                      </span>
                    </div>
                    <div class="profile-header-info">
                      <section>
                        <h1>{{ profileForm.nickname }}</h1>
                        <p><IdCard :size="15" />{{ user.student_no || '-' }}</p>
                        <p><Mail :size="15" />{{ user.email }}</p>
                      </section>
                      <aside>
                        <strong>{{ learningPoints }}</strong>
                        <span><Star :size="15" />学习积分</span>
                      </aside>
                    </div>
                  </article>
                  <article class="panel-card badge-card">
                    <div class="section-head"><h2><Award :size="18" />我的成就</h2></div>
                    <div class="badges"><span v-for="item in profilePayload.achievements || []" :key="item.key" :class="{ locked: !item.unlocked }"><Award :size="22" />{{ item.unlocked ? item.name : '?' }}</span></div>
                    <EmptyState v-if="!(profilePayload.achievements || []).length" text="暂无成就" />
                  </article>
                </aside>

                <section class="profile-main-card">
                  <div class="achievement-row">
                    <MiniMetric :icon="Clock" label="总学习时长" :value="`${stats.study_hours || 0}h`" />
                    <MiniMetric :icon="CheckCircle" label="课时完成" :value="`${stats.completion_rate || 0}%`" tone="success" />
                    <MiniMetric :icon="MessageCircle" label="知识问答" :value="stats.qa_count || 0" tone="ai" />
                    <MiniMetric :icon="Star" label="平均得分" :value="`${stats.accuracy || 0}`" tone="warning" />
                  </div>
                  <div class="profile-tabs">
                    <button :class="{ active: profileTab === 'info' }" @click="profileTab = 'info'">我的资料</button>
                    <button :class="{ active: profileTab === 'records' }" @click="profileTab = 'records'">学习档案</button>
                    <button :class="{ active: profileTab === 'account' }" @click="profileTab = 'account'">账号设置</button>
                  </div>
                  <Transition name="fade-slide" mode="out-in">
                    <article v-if="profileTab === 'info'" key="info" class="panel-card profile-form">
                      <div class="profile-form-grid">
                        <label>姓名<input v-model="profileForm.nickname" class="input" /></label>
                        <label>学校<input v-model="profileForm.school" class="input" /></label>
                        <label class="wide">简介<textarea v-model="profileForm.bio" class="textarea"></textarea></label>
                      </div>
                      <footer><button class="btn btn-primary" @click="saveProfile">保存修改</button></footer>
                    </article>
                    <article v-else-if="profileTab === 'records'" key="records" class="panel-card profile-records"><ActivityTimeline :items="profilePayload.activities || []" /></article>
                    <article v-else key="account" class="panel-card profile-form">
                      <h2>账号安全</h2>
                      <div class="profile-form-grid">
                        <PasswordField v-model="passwordForm.old_password" placeholder="当前密码" />
                        <PasswordField v-model="passwordForm.new_password" placeholder="新密码" />
                        <PasswordField v-model="passwordConfirm" placeholder="确认密码" />
                      </div>
                      <footer><button class="btn btn-primary" @click="changePassword">确认修改</button></footer>
                      <h2>通知设置</h2>
                      <div class="notice-settings-grid">
                        <div v-for="item in noticeSettings" :key="item.key" class="toggle-line"><AppCheckbox v-model="item.enabled" variant="switch" :label="item.label" /><input v-if="item.key === 'plan'" v-model="item.time" class="time-input" type="text" placeholder="09:00" /></div>
                      </div>
                      <footer><button class="btn btn-secondary" @click="saveNotices">保存设置</button></footer>
                    </article>
                  </Transition>
                </section>
              </div>
            </section>
          </template>

          <template v-else-if="active === 'studentMaterials'">
            <PageTitle title="课程资料"><CourseSelect /></PageTitle>
            <article class="panel-card"><MaterialRow v-for="item in courseHome.materials || []" :key="item.id" :item="item" /><EmptyState v-if="!(courseHome.materials || []).length" text="暂无资料" /></article>
          </template>
        </section>
      </transition>
    </main>

    <nav class="bottom-tabs">
      <button v-for="item in bottomTabs" :key="item.key" :class="{ active: isStudentNavActive(item.key), ai: item.key === 'studentQa' }" @click="go(item.key)">
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
          <article v-if="joinPreview" class="preview-course"><span :class="{ 'has-image': joinPreview.course.cover_url }" :style="courseCoverStyle(joinPreview.course)"><BookOpen v-if="!joinPreview.course.cover_url" :size="20" /></span><div><strong>{{ joinPreview.course.name }}</strong><small>{{ joinPreview.teacher?.nickname || '教师' }} · {{ joinPreview.course.term }} · {{ joinPreview.student_count }}人</small></div></article>
          <div class="hint-line"><Info :size="14" />加入后即可学习课程内容</div>
          <footer><button class="btn btn-ghost" @click="joinOpen = false">取消</button><button class="btn btn-primary" :data-loading="joinChecking" :disabled="joinChecking || !joinPreview || joinPreview.already_joined" @click="confirmJoin">确认加入</button></footer>
        </article>
      </div>
    </transition>

    <transition name="modal-pop">
      <div v-if="planModalOpen" class="modal-mask">
        <article class="join-modal">
          <div class="modal-head"><Sparkles :size="22" /><h2>AI 学习计划</h2><button @click="planModalOpen = false"><X :size="16" /></button></div>
          <textarea v-model="planForm.goal" class="textarea" placeholder="学习目标"></textarea>
          <div class="form-row"><input v-model.number="planForm.daily_minutes" class="input" type="number" /><input v-model.number="planForm.available_days" class="input" type="number" /></div>
          <footer><button class="btn btn-ghost" @click="planModalOpen = false">取消</button><button class="btn btn-primary" @click="createPlan">采用计划</button></footer>
        </article>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, Transition, watch, type PropType, type Ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownIt from "markdown-it";
import katex from "katex";
import "katex/dist/katex.min.css";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Award, BarChart2, Bell, BookMarked, BookOpen, CalendarCheck, Camera, Check,
  CheckCircle, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, Cpu, Download, FileText, Flame, FolderOpen, GitBranch, Grid2X2,
  History, IdCard, Info, Flag, Layers, ListChecks, Loader2, LogOut, Mail, Maximize, MessageCircle, MoreHorizontal, PanelRight,
  Pause, Pencil, Play, Plus, PlusCircle, Presentation, Quote, RefreshCw, Search, Send, Settings, SkipBack,
  Shield, SkipForward, Sparkles, Star, Sun, Type, User, Users, Wifi, X, XCircle, Zap
} from "lucide-vue-next";
import { api } from "../api/client";
import { routeByPage } from "../router";
import type { Lesson, LessonPage, Quiz, User as UserType } from "../types";
import AppCheckbox from "../components/AppCheckbox.vue";
import AppProgress from "../components/AppProgress.vue";
import AppSlider from "../components/AppSlider.vue";
import PasswordField from "../components/PasswordField.vue";

type QaAttachment = { type: string; url: string; filename?: string; size_bytes?: number; ocr_text?: string };
type ChatMessage = { id: number; role: "user" | "ai"; text: string; sources?: any[]; attachments?: QaAttachment[]; thought?: string; thoughtOpen?: boolean; record_id?: number; favorite?: boolean; outOfScope?: boolean; streaming?: boolean };
const markdownRenderer = new MarkdownIt({ html: false, linkify: true, breaks: true });
const textPayloadKeys = ["markdownContent", "markdown_content", "page_text", "script_text", "content", "text"] as const;

function renderMath(source: string, displayMode: boolean) {
  try {
    return katex.renderToString(source, {
      displayMode,
      throwOnError: false,
      strict: false,
      output: "html",
    });
  } catch {
    return source;
  }
}

function extractStructuredText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(extractStructuredText).filter(Boolean).join("\n\n");
  if (typeof value === "object") {
    const payload = value as Record<string, unknown>;
    for (const key of textPayloadKeys) {
      const text = extractStructuredText(payload[key]);
      if (text) return text;
    }
    return Object.values(payload)
      .map(extractStructuredText)
      .filter(Boolean)
      .join("\n\n");
  }
  let text = String(value).trim();
  if (!text) return "";
  if (text.startsWith("{") || text.startsWith("[")) {
    try {
      return extractStructuredText(JSON.parse(text));
    } catch {
      text = extractSerializedTextValues(text) || text;
    }
  }
  return text
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\'/g, "'")
    .replace(/\\"/g, "\"")
    .trim();
}

function extractSerializedTextValues(value: string) {
  const keyPattern = new RegExp(String.raw`['"](?:${textPayloadKeys.join("|")})['"]\s*:\s*`, "g");
  const pieces: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = keyPattern.exec(value))) {
    let cursor = match.index + match[0].length;
    while (/\s/.test(value[cursor] || "")) cursor += 1;
    const quote = value[cursor];
    if (quote !== "'" && quote !== "\"") continue;
    cursor += 1;
    let raw = "";
    let escaped = false;
    for (; cursor < value.length; cursor += 1) {
      const char = value[cursor];
      if (escaped) {
        raw += `\\${char}`;
        escaped = false;
        continue;
      }
      if (char === "\\") {
        escaped = true;
        continue;
      }
      if (char === quote) {
        if (raw.trim()) pieces.push(raw);
        keyPattern.lastIndex = cursor + 1;
        break;
      }
      raw += char;
    }
    if (escaped && raw.trim()) pieces.push(`${raw}\\`);
  }
  return pieces.join("\n\n");
}

function normalizeLatexEscapes(value: string) {
  if (!value.includes("\\")) return value;
  return value.replace(/(^|[^\\])\\\\([A-Za-z])/g, (_match, prefix: string, command: string) => `${prefix}\\${command}`);
}

function wrapBareLatexBlocks(value: string) {
  if (!value.includes("\\")) return value;
  const command = String.raw`(?:frac|mathrm|mathbf|mathbb|sqrt|sum|int|lim|left|right|begin|end|cdot|times|leq|geq|neq|approx|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|Delta|Omega|infty)`;
  const commandPattern = new RegExp(String.raw`\\${command}`, "g");
  let inFence = false;
  return value.split("\n").map((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      inFence = !inFence;
      return line;
    }
    if (
      inFence ||
      !trimmed ||
      trimmed.includes("@@MATH_") ||
      trimmed.startsWith("$$") ||
      trimmed.endsWith("$$") ||
      trimmed.startsWith("\\[") ||
      trimmed.startsWith("\\(")
    ) {
      return line;
    }
    const commands = trimmed.match(commandPattern) || [];
    const syntaxWeight = (trimmed.match(/[\\{}_^=&]/g) || []).length / Math.max(trimmed.length, 1);
    const formulaLike = commands.length > 0 && (/\\begin\{|\\left|\\right|\\frac|\\mathbb|\\mathrm|[_^=]/.test(trimmed));
    if (formulaLike && (trimmed.startsWith("\\") || syntaxWeight > 0.12 || trimmed.length > 32)) {
      const leading = line.match(/^\s*/)?.[0] || "";
      return `${leading}$$ ${trimmed} $$`;
    }
    return line;
  }).join("\n");
}

function wrapInlineBareLatex(value: string) {
  if (!value.includes("\\")) return value;
  const command = String.raw`(?:frac|mathrm|mathbf|mathbb|sqrt|sum|int|lim|left|right|cdot|times|div|pm|leq|geq|neq|approx|alpha|beta|gamma|delta|theta|lambda|mu|pi|sigma|Delta|Omega|infty)`;
  const pattern = new RegExp(String.raw`(^|[\s：:，,（(])((?:\\${command}(?:\{[^{}]*\}|\[[^\]]*\]|[^\s。；;!?！？])*)+)`, "g");
  return value.split("\n").map((line) => {
    if (line.includes("@@MATH_") || line.includes("$$") || line.includes("\\[") || line.includes("\\(")) return line;
    return line.replace(pattern, (match, prefix: string, expr: string) => {
      if (!expr) return match;
      return `${prefix}$${expr.trim()}$`;
    });
  }).join("\n");
}

function renderRichText(value?: unknown) {
  if (!value) return "";
  const mathParts: string[] = [];
  const stash = (html: string) => {
    const token = `@@MATH_${mathParts.length}@@`;
    mathParts.push(html);
    return token;
  };
  const renderDelimitedMath = (text: string) => text
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), true)))
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), true)))
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, expr: string) => stash(renderMath(normalizeLatexEscapes(expr.trim()), false)))
    .replace(/(^|[^\\])\$([^$\n]+?)\$/g, (_, prefix: string, expr: string) => `${prefix}${stash(renderMath(normalizeLatexEscapes(expr.trim()), false))}`);
  const extracted = normalizeLatexEscapes(extractStructuredText(value));
  const delimitedRendered = renderDelimitedMath(extracted);
  const inferredMath = wrapInlineBareLatex(wrapBareLatexBlocks(delimitedRendered));
  const textWithDelimitedMath = renderDelimitedMath(inferredMath);
  return markdownRenderer.render(textWithDelimitedMath).replace(/@@MATH_(\d+)@@/g, (_, index: string) => mathParts[Number(index)] || "");
}

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
const notificationLoading = ref(false);
const userMenuOpen = ref(false);
const topActionsRef = ref<HTMLElement | null>(null);
const noticePopRef = ref<HTMLElement | null>(null);
const userPopRef = ref<HTMLElement | null>(null);
const joinOpen = ref(false);
const joinCode = ref("");
const joinPreview = ref<any | null>(null);
const joinChecking = ref(false);
const joinError = ref("");
let joinTimer: number | undefined;
let notificationTimer: number | undefined;

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
const classQaImageInput = ref<HTMLInputElement | null>(null);
const classQaAttachments = ref<QaAttachment[]>([]);
const classQaImageUploading = ref(false);
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
const pageNoteArea = ref<HTMLTextAreaElement | null>(null);
const noteState = ref("已保存");
const noteSavedAt = ref("尚未保存");
let chromeTimer: number | undefined;
let studyTimer: number | undefined;
let noteTimer: number | undefined;

const globalMessages = ref<ChatMessage[]>([]);
const globalQuestion = ref("");
const globalThinking = ref(false);
const globalConversationId = ref<number | null>(null);
const globalQaImageInput = ref<HTMLInputElement | null>(null);
const globalQaAttachments = ref<QaAttachment[]>([]);
const globalQaImageUploading = ref(false);
const qaHistory = ref<any[]>([]);
const qaKeyword = ref("");
const historyOpen = ref(false);
const showFavorites = ref(false);

const problemMode = ref<"text" | "image">("text");
const problemText = ref("");
const problemFile = ref<HTMLInputElement | null>(null);
const problemSubmitting = ref(false);
const ocrScanning = ref(false);
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

const quizTab = ref<"course" | "practice">("practice");
const quizzes = ref<Quiz[]>([]);
const quizDetail = ref<any | null>(null);
const quizAnswers = reactive<Record<number, any>>({});
const attempt = ref<any | null>(null);
const answeringQuiz = ref(false);
const selectedPracticeChapters = ref<number[]>([]);
const quizQuestionCount = ref("10题");
const smartQuiz = ref(true);
const quizGenerating = ref(false);
const wrongPracticeGenerating = ref(false);
const quizSubmitting = ref(false);

const wrongQuestions = ref<any[]>([]);
const wrongKeyword = ref("");
const wrongStatus = ref("");
const selectedWrongKnowledge = ref("");

const plans = ref<any[]>([]);
const tasks = ref<any[]>([]);
const planModalOpen = ref(false);
const planForm = reactive({ title: "今日学习计划", goal: "", available_days: 7, daily_minutes: 60 });
const planCreating = ref(false);
const planCalendarDate = ref(new Date());
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
const topNavTabs = [
  { key: "studentHome", label: "工作台", icon: BookOpen },
  { key: "studentCourses", label: "我的课程", icon: Presentation },
  { key: "studentQa", label: "AI 问答", icon: Sparkles },
  { key: "studentWrongBook", label: "错题本", icon: BookMarked }
];
const speedItems = ["0.5", "0.75", "1", "1.25", "1.5", "2"].map((value) => ({ label: `${value}x`, value }));
const levelItems = [{ label: "入门", value: "beginner" }, { label: "标准", value: "standard" }, { label: "进阶", value: "advanced" }];
const quizCountOptions = ["5题", "10题", "15题", "20题"];
const wrongStatusOptions = [{ label: "全部状态", value: "" }, { label: "待重练", value: "todo" }, { label: "已掌握", value: "resolved" }, { label: "多次错误", value: "repeat" }];
const courseMenuItems = [{ label: "课程详情", value: "detail" }, { label: "问答记录", value: "qa" }, { label: "分享课程码", value: "share" }, { label: "退出课程", value: "leave", danger: true }];

const stats = computed(() => dashboard.value.stats || profilePayload.value.stats || {});
const todayTasks = computed(() => dashboard.value.today_tasks || tasks.value || []);
const doneTasks = computed(() => todayTasks.value.filter((task: any) => task.status === "done").length);
const todayDoneRate = computed(() => todayTasks.value.length ? Math.round(doneTasks.value / todayTasks.value.length * 100) : 0);
const continueLesson = computed(() => dashboard.value.continue_learning || null);
const continueProgress = computed(() => continueLesson.value?.progress?.progress_percent || 0);
const continueProgressPage = computed(() => continueLesson.value?.progress?.current_page || 1);
const continueTime = computed(() => continueLesson.value?.progress?.updated_at ? `上次学习：${relativeTime(continueLesson.value.progress.updated_at)}` : "从第一节开始");
const hasJoinedCourses = computed(() => courses.value.length > 0);
const studentRecommendationText = computed(() => dashboard.value.recommendation?.text || "建议选择一门课程完成一个课时，并用练习检查掌握情况。");
const hourTargetRate = computed(() => Math.min(100, Math.round((stats.value.study_hours || 0) / 5 * 100)));
const unreadCount = computed(() => notifications.value.filter((item) => item.unread).length);
const activities = computed(() => dashboard.value.activities || []);
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" }));
const termLeftDays = computed(() => Math.max(1, Math.ceil((new Date(new Date().getFullYear(), 6, 15).getTime() - Date.now()) / 86400000)));
const activeCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value) || courses.value[0] || null);
const courseScopeName = computed(() => activeCourse.value?.name || "当前课程");
const currentAvatarUrl = computed(() => profileForm.avatar_url || props.user.avatar_url || "");
const homeRecommendedLesson = computed(() => dashboard.value.recommendation?.lesson || continueLesson.value || null);
const homeRecommendedLessonTitle = computed(() => {
  if (!hasJoinedCourses.value) return "输入课程码加入课程";
  return homeRecommendedLesson.value?.lesson?.title || activeCourse.value?.last_lesson?.title || "暂无推荐课时";
});
const homeRecommendedPracticeTitle = computed(() => {
  if (!hasJoinedCourses.value) return "加入后查看推荐练习";
  const weakPoint = dashboard.value.recommendation?.weak_points?.[0]?.name;
  return weakPoint ? `${weakPoint}专项练习 (10题)` : "章节巩固练习 (10题)";
});
const homeActivityItems = computed(() => activities.value.map((item: any, index: number) => {
  const type = item?.type || "activity";
  const rawTitle = item?.title || "学习记录";
  const meta = item?.meta || "";
  const progress = type === "lesson" ? normalizePercent(meta) : null;
  if (type === "qa") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: MessageCircle, tone: "ai", action: "向 AI 发起提问", detail: rawTitle, quote: true, progress: null, timeText: relativeTime(item?.time) };
  }
  if (type === "lesson") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: Play, tone: "learning", action: "学习课时", detail: rawTitle.replace(/^学习\s*/, ""), quote: false, progress, timeText: relativeTime(item?.time) };
  }
  if (type === "quiz") {
    return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: ClipboardList, tone: "learning", action: "提交练习", detail: `${rawTitle.replace(/^提交\s*/, "")}${meta ? ` · ${meta}` : ""}`, quote: false, progress: null, timeText: relativeTime(item?.time) };
  }
  return { key: `${type}-${rawTitle}-${item?.time || index}`, icon: Sparkles, tone: "ai", action: type === "tutoring" ? "AI 题目辅导" : "学习记录", detail: meta ? `${rawTitle} · ${meta}` : rawTitle, quote: false, progress: null, timeText: relativeTime(item?.time) };
}));
const termOptions = computed(() => [{ label: "全部学期", value: "" }, ...Array.from(new Set(courses.value.map((course) => course.term))).filter(Boolean).map((term: any) => ({ label: term, value: term }))]);
const activeCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) < 100));
const doneCourses = computed(() => courses.value.filter((course) => (course.progress_percent || 0) >= 100));
const filteredCourses = computed(() => (courseTab.value === "active" ? activeCourses.value : doneCourses.value).filter((course) => (!courseKeyword.value || course.name.includes(courseKeyword.value)) && (!termFilter.value || course.term === termFilter.value)));
const latestLesson = computed(() => (courseHome.value.lessons || [])[0] || null);
const visibleCourseMaterials = computed(() => materialsExpanded.value ? courseHome.value.materials || [] : (courseHome.value.materials || []).slice(0, 5));
const activePage = computed(() => classroomLesson.value?.pages.find((page) => page.page_number === currentPage.value) || classroomLesson.value?.pages[0] || null);
const activePageText = computed(() => extractStructuredText(activePage.value?.page_text || "") || String(activePage.value?.page_text || "").trim());
const activeScriptText = computed(() => extractStructuredText(activePage.value?.script_text || activePage.value?.page_text || "") || String(activePage.value?.script_text || activePage.value?.page_text || "").trim());
const activeSubtitleText = computed(() => {
  const text = extractStructuredText(activePage.value?.subtitle_text || activePage.value?.script_text || activePage.value?.page_text || "");
  if (subtitleMode.value === "keyword") {
    const firstSentence = text.match(/^[\s\S]*?[。！？!?]/)?.[0]?.trim() || text;
    return firstSentence.slice(0, 140);
  }
  return text;
});
const activePageHtml = computed(() => renderRichText(activePageText.value || "暂无页面内容"));
const activeScriptHtml = computed(() => renderRichText(activeScriptText.value || "暂无文稿"));
const activeSubtitleHtml = computed(() => renderRichText(activeSubtitleText.value));
const promptContext = computed(() => {
  const home = courseHome.value || {};
  const courseName = home.course?.name || activeCourse.value?.name || "";
  const lesson = (home.lessons || []).find((item: any) => item?.title)?.title || "";
  const chapter = (home.chapters || []).find((item: any) => item?.title)?.title || "";
  const material = (home.materials || []).find((item: any) => item?.title)?.title || "";
  const weakPoint = weakPoints.value.find((item: any) => item?.knowledge_point || item?.name);
  const point = knowledge.value.find((item: any) => item?.name)?.name || weakPoint?.knowledge_point || weakPoint?.name || "";
  const base = lesson || chapter || material || courseName || "当前课程";
  return { courseName, lesson, chapter, material, point, base };
});
const promptCards = computed(() => {
  const ctx = promptContext.value;
  const rows = [
    { text: `${ctx.base} 的重点是什么？`, icon: Layers },
    { text: ctx.point ? `请解释 ${ctx.point}` : `${ctx.base} 有哪些核心概念？`, icon: Zap },
    { text: ctx.lesson ? `根据 ${ctx.lesson} 出一道练习题` : `根据 ${ctx.base} 出一道练习题`, icon: Pencil },
    { text: ctx.chapter ? `帮我梳理 ${ctx.chapter} 的知识框架` : `帮我总结 ${ctx.base}`, icon: GitBranch },
    { text: ctx.material ? `${ctx.material} 里容易混淆的点有哪些？` : `${ctx.base} 有哪些易错点？`, icon: Shield },
    { text: ctx.courseName ? `我该如何复习《${ctx.courseName}》？` : "请先选择一门课程后提问", icon: BookOpen }
  ];
  const seen = new Set<string>();
  return rows.filter((item) => {
    if (seen.has(item.text)) return false;
    seen.add(item.text);
    return true;
  });
});
const quickPageQuestions = computed(() => {
  const title = activePage.value?.page_title || classroomLesson.value?.lesson?.title || "当前页面";
  return [`${title} 的重点？`, `用例子解释 ${title}`, `根据 ${title} 出道题`, `总结 ${title}`];
});
const studyClock = computed(() => `${String(Math.floor(studySeconds.value / 60)).padStart(2, "0")}:${String(studySeconds.value % 60).padStart(2, "0")}`);
const audioTime = computed(() => timeLabel(audioRef.value?.currentTime || 0));
const audioDuration = computed(() => timeLabel(audioRef.value?.duration || activePage.value?.audio_duration_seconds || 0));
const completionSummary = computed(() => "本次学习完成度良好，建议继续完成配套练习并整理课时笔记。");
const filteredQaHistory = computed(() => qaHistory.value.filter((item) => (!showFavorites.value || item.is_favorite) && (!qaKeyword.value || item.question.includes(qaKeyword.value))));
const selectedKnowledge = computed(() => knowledge.value.find((item) => item.id === selectedKnowledgeId.value) || knowledge.value[0] || null);
const knowledgeMastery = computed(() => Math.max(35, 90 - (weakPoints.value.find((item) => item.knowledge_point === selectedKnowledge.value?.name)?.wrong_count || 0) * 12));
const knowledgeMasteryText = computed(() => knowledgeMastery.value > 75 ? "已掌握" : knowledgeMastery.value > 55 ? "待加强" : "薄弱");
const knowledgeMasteryClass = computed(() => knowledgeMastery.value > 75 ? "tag-success" : knowledgeMastery.value > 55 ? "tag-warning" : "tag-danger");
const knowledgeContent = computed(() => selectedKnowledge.value?.content_by_level?.[knowledgeLevel.value] || {});
const courseQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type === "course"));
const practiceQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type !== "course"));
const wrongKnowledgeFilters = computed(() => {
  const counter = new Map<string, number>();
  wrongQuestions.value.forEach((item: any) => {
    const name = item.knowledge_point_name || "未标注知识点";
    counter.set(name, (counter.get(name) || 0) + 1);
  });
  return Array.from(counter.entries()).map(([name, count]) => ({ name, count })).sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
});
const pendingWrongCount = computed(() => wrongQuestions.value.filter((item) => !item.is_resolved).length);
const repeatedWrongCount = computed(() => wrongQuestions.value.filter((item) => Number(item.wrong_count || 0) > 1).length);
const filteredWrongQuestions = computed(() => wrongQuestions.value.filter((item) => {
  const keyword = wrongKeyword.value.trim();
  const stem = item.question?.stem || "";
  const explanation = item.question?.explanation || "";
  const knowledgeName = item.knowledge_point_name || "未标注知识点";
  const statusMatched = !wrongStatus.value
    || (wrongStatus.value === "todo" && !item.is_resolved)
    || (wrongStatus.value === "resolved" && item.is_resolved)
    || (wrongStatus.value === "repeat" && Number(item.wrong_count || 0) > 1);
  return (!keyword || stem.includes(keyword) || explanation.includes(keyword))
    && (!selectedWrongKnowledge.value || knowledgeName === selectedWrongKnowledge.value)
    && statusMatched;
}));
const wrongFilterSummary = computed(() => {
  const parts = [];
  if (selectedWrongKnowledge.value) parts.push(selectedWrongKnowledge.value);
  if (wrongStatus.value) parts.push(String(wrongStatusOptions.find((item) => item.value === wrongStatus.value)?.label || ""));
  if (wrongKeyword.value.trim()) parts.push(`关键词：${wrongKeyword.value.trim()}`);
  return parts.filter(Boolean).join(" · ") || "全部错题";
});
const weeklyWrongCount = computed(() => wrongQuestions.value.filter((item) => {
  const time = item.last_wrong_at || item.updated_at || item.created_at;
  return time && Date.now() - new Date(time).getTime() < 7 * 86400000;
}).length);
const monthlyCheckins = computed(() => checkinDays.value.filter((day) => day.slice(0, 7) === new Date().toISOString().slice(0, 7)).length);
const weeklyHours = computed(() => [0.8, 1.2, 1.6, 1.1, 2.2, 0.7, 1.4]);
const totalWeeklyHours = computed(() => Number(weeklyHours.value.reduce((sum, value) => sum + Number(value || 0), 0).toFixed(1)));
const weeklyChart = computed(() => {
  const labels = ["一", "二", "三", "四", "五", "六", "日"];
  const max = Math.max(1, ...weeklyHours.value.map((value) => Number(value || 0)));
  return labels.map((label, index) => {
    const value = Number(weeklyHours.value[index] || 0);
    return { label, value, percent: value <= 0 ? 0 : Math.max(12, Math.round(value / max * 100)) };
  });
});
const learningPoints = computed(() => Math.round((stats.value.study_hours || 0) * 10 + (stats.value.qa_count || 0) * 2 + (stats.value.completion_rate || 0)));
const weekDays = computed(() => ["一", "二", "三", "四", "五", "六", "日"].map((label, index) => ({ label, done: index < Math.min(7, stats.value.streak_days || 0), today: index === new Date().getDay() - 1 })));
const planWeekHeaders = ["一", "二", "三", "四", "五", "六", "日"];
const planMonthLabel = computed(() => `${planCalendarDate.value.getFullYear()}年 ${planCalendarDate.value.getMonth() + 1}月`);
const planCalendarCells = computed(() => {
  const cursor = planCalendarDate.value;
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const leading = (firstDay.getDay() + 6) % 7;
  const days = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const cells: Array<{ key: string; label: string; empty: boolean; checked: boolean; today: boolean }> = [];
  for (let index = 0; index < leading; index += 1) cells.push({ key: `empty-${index}`, label: "", empty: true, checked: false, today: false });
  for (let day = 1; day <= days; day += 1) {
    const iso = localDateKey(new Date(year, month, day));
    cells.push({
      key: iso,
      label: String(day),
      empty: false,
      checked: checkinDays.value.includes(iso),
      today: year === today.getFullYear() && month === today.getMonth() && day === today.getDate()
    });
  }
  return cells;
});
const planAchievementSlots = computed(() => {
  const items = [...(profilePayload.value.achievements || [])].slice(0, 4);
  while (items.length < 4) items.push({ key: `locked-${items.length}`, name: "?", unlocked: false });
  return items;
});

function resetCourseScopedState() {
  courseHome.value = {};
  lessons.value = [];
  globalMessages.value = [];
  globalConversationId.value = null;
  globalQuestion.value = "";
  globalQaAttachments.value = [];
  qaHistory.value = [];
  qaKeyword.value = "";
  historyOpen.value = false;
  wrongQuestions.value = [];
  weakPoints.value = [];
  wrongKeyword.value = "";
  wrongStatus.value = "";
  selectedWrongKnowledge.value = "";
  quizzes.value = [];
  activeProblem.value = null;
  problemText.value = "";
  problemHistory.value = [];
  Object.keys(guidance).forEach((key) => delete guidance[Number(key)]);
  guideOpen[1] = true;
  guideOpen[2] = false;
  guideOpen[3] = false;
}

watch(() => props.pageKey, async (key) => { active.value = key || "studentHome"; await loadActive(); });
watch(selectedCourseId, async (id, previousId) => {
  if (id) localStorage.setItem("student_current_course_id", String(id));
  if (id === previousId) return;
  resetCourseScopedState();
  if (active.value === "studentQa") {
    await loadCourseHome();
    await loadQaHistory();
  }
  if (active.value === "studentWrongBook") await loadWrongBook();
  if (active.value === "studentTutoring") await loadProblemHistory();
  if (active.value === "studentKnowledge") await loadKnowledge();
  if (active.value === "studentQuizzes") await loadQuizPage();
});
watch(activePage, async (page) => { if (page) await loadNote(page.id); }, { immediate: false });

async function run<T>(task: () => Promise<T>, ok?: string) { try { const data = await task(); if (ok) emit("notice", "success", ok); return data; } catch (error) { emit("notice", "error", (error as Error).message); return null; } }
async function go(key: string) { await router.push(routeByPage[key] || "/home"); }
async function loadCourses() { courses.value = (await run<any[]>(() => api.get("/student/courses"))) || []; if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id; }
async function loadDashboard() { dashboard.value = (await run(() => api.get("/student/dashboard"))) || {}; notifications.value = dashboard.value.notifications || []; courses.value = dashboard.value.courses || courses.value; if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id; }
async function loadNotifications(silent = false) {
  if (notificationLoading.value) return;
  if (!silent) notificationLoading.value = true;
  try {
    notifications.value = (await api.get<any[]>("/student/notifications")) || [];
  } catch (error) {
    if (!silent) emit("notice", "error", (error as Error).message);
  } finally {
    if (!silent) notificationLoading.value = false;
  }
}
async function toggleNotifications() {
  noticeOpen.value = !noticeOpen.value;
  userMenuOpen.value = false;
  if (noticeOpen.value) await loadNotifications();
}
async function loadCourseHome() { if (!selectedCourseId.value) return; courseHome.value = (await run(() => api.get(`/student/courses/${selectedCourseId.value}/home`))) || {}; lessons.value = courseHome.value.lessons || []; }
async function loadProfile() { profilePayload.value = (await run(() => api.get("/student/profile"))) || {}; Object.assign(profileForm, { nickname: profilePayload.value.user?.nickname || props.user.nickname, avatar_url: profilePayload.value.user?.avatar_url || "", school: profilePayload.value.student_profile?.school || "", bio: profilePayload.value.user?.bio || "" }); noticeSettings.splice(0, noticeSettings.length, ...(profilePayload.value.notification_settings || [])); }
async function loadActive() {
  if (active.value === "studentHome") await loadDashboard();
  if (active.value === "studentCourses") await loadCourses();
  if (["studentQa", "studentWrongBook", "studentTutoring", "studentKnowledge", "studentQuizzes"].includes(active.value) && !courses.value.length) await loadCourses();
  if (["studentCourseHome", "studentMaterials"].includes(active.value)) await loadCourseHome();
  if (active.value === "studentQa") {
    await loadCourseHome();
    await loadQaHistory();
  }
  if (active.value === "studentTutoring") await loadProblemHistory();
  if (active.value === "studentKnowledge") await loadKnowledge();
  if (active.value === "studentQuizzes") await loadQuizPage();
  if (active.value === "studentWrongBook") await loadWrongBook();
  if (active.value === "studentPlans") await loadPlans();
  if (active.value === "studentProfile") await loadProfile();
}
async function openCourse(id: number) { selectedCourseId.value = id; await loadCourseHome(); await go("studentCourseHome"); }
async function openHomeRecommendedLesson() {
  if (!hasJoinedCourses.value) { joinOpen.value = true; return; }
  const lessonId = homeRecommendedLesson.value?.lesson?.id || activeCourse.value?.last_lesson?.id;
  if (lessonId) { await openLesson(Number(lessonId)); return; }
  await go("studentCourses");
}
async function openHomeRecommendedPractice() {
  if (!hasJoinedCourses.value) { joinOpen.value = true; return; }
  await go("studentQuizzes");
}
function scrollToLessons() { document.getElementById("lesson-list")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
async function openSearch() { searchOpen.value = true; await nextTick(); searchInput.value?.focus(); }
function firstChar(value?: string) { return (value || "-").slice(0, 1); }
function localDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function shiftPlanMonth(offset: number) {
  const current = planCalendarDate.value;
  planCalendarDate.value = new Date(current.getFullYear(), current.getMonth() + offset, 1);
}
function isStudentNavActive(key: string) {
  const courseKeys = ["studentCourses", "studentCourseHome", "studentMaterials", "studentKnowledge", "studentQuizzes", "studentTutoring", "studentPlans"];
  if (key === "studentCourses") return courseKeys.includes(active.value);
  return active.value === key;
}
function courseGradient(id = 1) { const items = ["linear-gradient(135deg,#4F46E5,#06B6D4)", "linear-gradient(135deg,#10B981,#3B82F6)", "linear-gradient(135deg,#F59E0B,#EF4444)", "linear-gradient(135deg,#8B5CF6,#EC4899)"]; return items[id % items.length]; }
function courseCoverStyle(course?: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(180deg, rgba(15,23,42,0.06), rgba(15,23,42,0.42)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseGradient(Number(course?.id || 1)) };
}
function courseHeroStyle(course?: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(135deg, rgba(15,23,42,0.72), rgba(79,70,229,0.50)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseGradient(Number(course?.id || 1)) };
}
function normalizePercent(value: unknown) { const percent = Number.parseFloat(String(value ?? "").replace("%", "")); return Number.isFinite(percent) ? Math.max(0, Math.min(100, Math.round(percent))) : null; }
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
function formatNote(kind: "bold" | "italic" | "mark") {
  const textarea = pageNoteArea.value;
  if (!textarea) return;
  const start = textarea.selectionStart ?? 0;
  const end = textarea.selectionEnd ?? start;
  const selected = pageNote.value.slice(start, end) || (kind === "mark" ? "重点" : "文字");
  const [prefix, suffix] = kind === "bold" ? ["**", "**"] : kind === "italic" ? ["*", "*"] : ["==", "=="];
  pageNote.value = `${pageNote.value.slice(0, start)}${prefix}${selected}${suffix}${pageNote.value.slice(end)}`;
  const cursor = start + prefix.length + selected.length + suffix.length;
  nextTick(() => {
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
  });
  queueNoteSave();
}
function confettiStyle(n: number) { return { left: `${(n * 37) % 100}%`, background: ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EF4444"][n % 5], animationDelay: `${(n % 8) * 0.05}s` }; }
function nextLessonAfterComplete() { const index = (courseHome.value.lessons || []).findIndex((item: any) => item.id === classroomLesson.value?.lesson.id); const next = (courseHome.value.lessons || [])[index + 1]; if (next) openLesson(next.id); else returnCourse(); }
function returnCourse() { completeOpen.value = false; closeClassroom(); }

function patchChatMessage(messages: Ref<ChatMessage[]>, id: number, updater: (message: ChatMessage) => ChatMessage) {
  const index = messages.value.findIndex((item) => item.id === id);
  if (index < 0) return;
  messages.value.splice(index, 1, updater({ ...messages.value[index] }));
}

function applyQaStreamEvent(messages: Ref<ChatMessage[]>, messageId: number, event: string, data: any) {
  if (event === "delta") {
    patchChatMessage(messages, messageId, (message) => data?.type === "thought"
      ? { ...message, thought: `${message.thought || ""}${data.text || ""}`, thoughtOpen: true }
      : { ...message, text: `${message.text || ""}${data?.text || ""}` });
    return;
  }
  if (event === "final") {
    patchChatMessage(messages, messageId, (message) => ({
      ...message,
      text: data.answer || message.text,
      thought: data.thinking_process || message.thought || "",
      sources: data.sources || [],
      attachments: data.attachments || message.attachments || [],
      record_id: data.record_id,
      outOfScope: data.is_out_of_scope,
    }));
  }
}

function qaAttachmentsFor(scope: "class" | "global") {
  return scope === "class" ? classQaAttachments.value : globalQaAttachments.value;
}

function removeQaAttachment(scope: "class" | "global", index: number) {
  qaAttachmentsFor(scope).splice(index, 1);
}

async function handleQaImageChange(event: Event, scope: "class" | "global") {
  const input = event.target as HTMLInputElement;
  const file = (input.files || [])[0];
  input.value = "";
  if (!file) return;
  const courseId = scope === "class" ? classroomLesson.value?.lesson.course_id : selectedCourseId.value;
  if (!courseId) {
    emit("notice", "warning", "请先选择课程");
    return;
  }
  if (!file.type.startsWith("image/")) {
    emit("notice", "warning", "请上传图片文件");
    return;
  }
  const target = qaAttachmentsFor(scope);
  if (target.length >= 3) {
    emit("notice", "warning", "最多上传 3 张图片");
    return;
  }
  const form = new FormData();
  form.set("course_id", String(courseId));
  form.set("file", file);
  if (scope === "class") classQaImageUploading.value = true;
  else globalQaImageUploading.value = true;
  try {
    const attachment = await run<QaAttachment>(() => api.post("/qa/attachments/image", form), "图片已上传");
    if (attachment) target.push(attachment);
  } finally {
    if (scope === "class") classQaImageUploading.value = false;
    else globalQaImageUploading.value = false;
  }
}

async function askInClass() {
  if ((!classQuestion.value.trim() && !classQaAttachments.value.length) || !classroomLesson.value || classThinking.value || classQaImageUploading.value) return;
  const question = classQuestion.value.trim() || "请分析这张图片";
  const attachments = classQaAttachments.value.map((item) => ({ ...item }));
  classQuestion.value = "";
  classQaAttachments.value = [];
  classMessages.value.push({ id: Date.now(), role: "user", text: question, attachments });
  const aiMessageId = Date.now() + 1;
  const aiMessage: ChatMessage = { id: aiMessageId, role: "ai", text: "", thought: "", sources: [], streaming: true };
  classMessages.value.push(aiMessage);
  classThinking.value = true;
  try {
    await api.streamPost("/qa/ask/stream", {
      course_id: classroomLesson.value.lesson.course_id,
      conversation_id: classConversationId.value,
      lesson_page_id: activePage.value?.id,
      question,
      attachments
    }, (event, data) => {
      applyQaStreamEvent(classMessages, aiMessageId, event, data);
      if (event === "final") classConversationId.value = data.conversation_id;
    });
  } catch (error) {
    const current = classMessages.value.find((message) => message.id === aiMessageId);
    if (!current?.text) patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
    emit("notice", "error", (error as Error).message);
  } finally {
    patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, streaming: false }));
    classThinking.value = false;
  }
}
function sendQuickClass(text: string) { classQuestion.value = text; askInClass(); }
async function askGlobal() {
  if ((!globalQuestion.value.trim() && !globalQaAttachments.value.length) || !selectedCourseId.value || globalThinking.value || globalQaImageUploading.value) return;
  const question = globalQuestion.value.trim() || "请分析这张图片";
  const attachments = globalQaAttachments.value.map((item) => ({ ...item }));
  globalQuestion.value = "";
  globalQaAttachments.value = [];
  globalMessages.value.push({ id: Date.now(), role: "user", text: question, attachments });
  const aiMessageId = Date.now() + 1;
  const aiMessage: ChatMessage = { id: aiMessageId, role: "ai", text: "", thought: "", sources: [], streaming: true };
  globalMessages.value.push(aiMessage);
  globalThinking.value = true;
  try {
    await api.streamPost("/qa/ask/stream", {
      course_id: selectedCourseId.value,
      conversation_id: globalConversationId.value,
      question,
      attachments
    }, (event, data) => {
      applyQaStreamEvent(globalMessages, aiMessageId, event, data);
      if (event === "final") globalConversationId.value = data.conversation_id;
    });
    await loadQaHistory();
  } catch (error) {
    const current = globalMessages.value.find((message) => message.id === aiMessageId);
    if (!current?.text) patchChatMessage(globalMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
    emit("notice", "error", (error as Error).message);
  } finally {
    patchChatMessage(globalMessages, aiMessageId, (message) => ({ ...message, streaming: false }));
    globalThinking.value = false;
  }
}
function sendGlobalQuick(text: string) { globalQuestion.value = text; askGlobal(); }
async function sendCourseQuick(text: string) { quickCourseQuestion.value = text; await askCourseQuick(); }
async function askCourseQuick() { if (!quickCourseQuestion.value.trim()) return; globalQuestion.value = quickCourseQuestion.value; quickCourseQuestion.value = ""; await go("studentQa"); await askGlobal(); }
async function loadQaHistory() { if (!selectedCourseId.value) return; qaHistory.value = (await run<any[]>(() => api.get("/qa/history", { course_id: selectedCourseId.value, keyword: qaKeyword.value }))) || []; }
async function openQaHistory() { showFavorites.value = false; historyOpen.value = true; await loadQaHistory(); }
function reuseHistory(item: any) { historyOpen.value = false; globalMessages.value = [{ id: item.id * 2, role: "user", text: item.question, attachments: item.attachments || [] }, { id: item.id * 2 + 1, role: "ai", text: item.answer, sources: item.sources || [], attachments: item.attachments || [], thought: item.thinking_process || item.reasoning_content || item.thought || "", record_id: item.id, favorite: item.is_favorite }]; }
function toggleThought(message: ChatMessage) { message.thoughtOpen = !message.thoughtOpen; }
async function favoriteQaMessage(message: ChatMessage) { if (!message.record_id) return; await run(() => api.post(`/qa/${message.record_id}/favorite`, { is_favorite: !message.favorite }), "已收藏"); message.favorite = !message.favorite; }
async function feedbackQaMessage(message: ChatMessage, feedback = "positive") { if (!message.record_id) return; await run(() => api.post(`/qa/${message.record_id}/feedback`, { feedback }), "已评价"); }

async function createTextProblem() {
  if (problemSubmitting.value) return;
  if (!selectedCourseId.value) {
    emit("notice", "warning", "请先选择课程");
    return;
  }
  if (!problemText.value.trim()) {
    emit("notice", "warning", "请先输入题目");
    return;
  }
  problemSubmitting.value = true;
  try {
    activeProblem.value = await run<any>(() => api.post("/tutoring/problems/text", { course_id: selectedCourseId.value, text: problemText.value }), "已提交");
    await loadProblemHistory();
    if (activeProblem.value) await loadGuidance(1);
  } finally {
    problemSubmitting.value = false;
  }
}
async function createImageProblem(event: Event) {
  const file = ((event.target as HTMLInputElement).files || [])[0];
  if (!file) return;
  if (!selectedCourseId.value) {
    emit("notice", "warning", "请先选择课程");
    (event.target as HTMLInputElement).value = "";
    return;
  }
  const form = new FormData();
  form.set("course_id", String(selectedCourseId.value));
  form.set("file", file);
  ocrScanning.value = true;
  try {
    activeProblem.value = await run<any>(() => api.post("/tutoring/problems/image", form), "已识别");
    problemText.value = activeProblem.value?.ocr_text || "";
    await loadProblemHistory();
  } finally {
    ocrScanning.value = false;
    (event.target as HTMLInputElement).value = "";
  }
}
async function loadProblemHistory() { problemHistory.value = (await run<any[]>(() => api.get("/tutoring/history", { course_id: selectedCourseId.value || undefined }))) || []; }
function selectProblem(item: any) { activeProblem.value = item; problemText.value = item.corrected_text || item.ocr_text || item.raw_text || ""; guideOpen[1] = true; }
async function loadGuidance(level: number) { if (!activeProblem.value) return; guidance[level] = await run(() => api.get(`/tutoring/problems/${activeProblem.value.id}/guidance`, { level })); guideOpen[level] = true; }
async function toggleGuide(level: number) { if (!guidance[level]) await loadGuidance(level); else guideOpen[level] = !guideOpen[level]; }

async function loadKnowledge() { if (!selectedCourseId.value) return; knowledge.value = (await run<any[]>(() => api.get("/learning/knowledge-points", { course_id: selectedCourseId.value, chapter_id: selectedChapterId.value || undefined }))) || []; if (!selectedKnowledgeId.value && knowledge.value[0]) selectedKnowledgeId.value = knowledge.value[0].id; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); }
async function generateKnowledgeQuiz(count: number) { if (!selectedCourseId.value) return; await run(() => api.post("/learning/quizzes/generate", { course_id: selectedCourseId.value, chapter_id: selectedKnowledge.value?.chapter_id || undefined, title: `${selectedKnowledge.value?.name || '知识点'}练习`, quiz_type: "practice", question_count: count }), "已生成"); await go("studentQuizzes"); }

async function loadQuizPage() { if (!selectedCourseId.value) return; quizzes.value = (await run<Quiz[]>(() => api.get("/learning/quizzes", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); await loadWrongBook(); }
async function generateQuiz() {
  if (!selectedCourseId.value || quizGenerating.value) return;
  quizGenerating.value = true;
  try {
    const count = Number(quizQuestionCount.value.replace("题", ""));
    const chapterIds = selectedPracticeChapters.value.length ? selectedPracticeChapters.value : (selectedChapterId.value ? [selectedChapterId.value] : []);
    const quiz = await run<Quiz>(() => api.post("/learning/quizzes/generate", {
      course_id: selectedCourseId.value,
      chapter_id: chapterIds.length === 1 ? chapterIds[0] : undefined,
      chapter_ids: chapterIds,
      title: smartQuiz.value ? "薄弱点章节练习" : "章节练习",
      quiz_type: "practice",
      question_count: count,
      prefer_weak_points: smartQuiz.value,
    }), "已生成");
    await loadQuizPage();
    if (quiz) await startQuiz(quiz.id);
  } finally {
    quizGenerating.value = false;
  }
}
async function startQuiz(id: number) { quizDetail.value = await run(() => api.get(`/learning/quizzes/${id}`)); Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]); attempt.value = null; answeringQuiz.value = true; }
function setQuizAnswer(questionId: number, answer: any) { quizAnswers[questionId] = answer; }
async function submitQuiz() {
  if (!quizDetail.value || quizSubmitting.value) return;
  quizSubmitting.value = true;
  try {
    const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer }));
    attempt.value = await run(() => api.post(`/learning/quizzes/${quizDetail.value.quiz.id}/submit`, { answers }), "已提交");
    await loadWrongBook();
  } finally {
    quizSubmitting.value = false;
  }
}
function togglePracticeChapter(id: number) { selectedPracticeChapters.value = selectedPracticeChapters.value.includes(id) ? selectedPracticeChapters.value.filter((item) => item !== id) : [...selectedPracticeChapters.value, id]; }

async function loadWrongBook() { if (!selectedCourseId.value) return; wrongQuestions.value = (await run<any[]>(() => api.get("/learning/wrong-questions", { course_id: selectedCourseId.value }))) || []; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; }
async function loadWrongPractice() {
  if (!selectedCourseId.value || wrongPracticeGenerating.value) return;
  wrongPracticeGenerating.value = true;
  try {
    if (!wrongQuestions.value.length) await loadWrongBook();
    if (!wrongQuestions.value.length) {
      emit("notice", "info", "暂无错题可重练");
      return;
    }
    const quiz = await run<Quiz>(() => api.post("/learning/wrong-questions/practice", undefined, { course_id: selectedCourseId.value }), "已生成");
    if (quiz) { await loadQuizPage(); await startQuiz(quiz.id); await go("studentQuizzes"); }
  } finally {
    wrongPracticeGenerating.value = false;
  }
}
function practiceWrong(_: any) { loadWrongPractice(); }
function clearWrongFilters() { wrongKeyword.value = ""; wrongStatus.value = ""; selectedWrongKnowledge.value = ""; }

async function loadPlans() { plans.value = (await run<any[]>(() => api.get("/learning/plans", { course_id: selectedCourseId.value || undefined }))) || []; if (plans.value[0]) tasks.value = (await run<any[]>(() => api.get(`/learning/plans/${plans.value[0].id}/tasks`))) || []; checkinDays.value = todayTasks.value.filter((task: any) => task.status === "done").map(() => new Date().toISOString().slice(0, 10)); await loadProfile(); }
async function createPlan() {
  if (planCreating.value) return;
  if (!selectedCourseId.value) { emit("notice", "warning", "请先加入或选择课程"); return; }
  if (!planForm.goal.trim()) { emit("notice", "warning", "请先输入学习目标"); return; }
  planCreating.value = true;
  const data = await run<any>(() => api.post("/learning/plans", { ...planForm, course_id: selectedCourseId.value }), "已生成");
  planCreating.value = false;
  if (data) {
    planModalOpen.value = false;
    tasks.value = data.tasks || [];
    await loadDashboard();
  }
}
async function checkinTask(id: number) { await run(() => api.post(`/learning/tasks/${id}/checkin`, { notes: "" }), "已打卡"); await loadDashboard(); await loadPlans(); }

async function saveProfile() { const data = await run<any>(() => api.patch("/student/profile", { nickname: profileForm.nickname, avatar_url: profileForm.avatar_url, bio: profileForm.bio, school: profileForm.school }), "已保存"); if (data) profilePayload.value = data; }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); await run(() => api.post("/auth/me/password", passwordForm), "已保存"); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }
async function saveNotices() { await run(() => api.put("/student/notifications", { settings: noticeSettings }), "已保存"); }

type SelectOption = { label: string; value: string | number; danger?: boolean };
function normalizeItems(items: unknown[]): SelectOption[] {
  return items.map((item) => (typeof item === "string" ? { label: item, value: item } : item as SelectOption));
}
function optionText(value: unknown, question?: any) {
  if (value === null || value === undefined || value === "") return "-";
  const options = Array.isArray(question?.options) ? question.options : [];
  const renderOne = (item: unknown) => {
    const index = typeof item === "number"
      ? item
      : (typeof item === "string" && /^\d+$/.test(item) ? Number(item) : (typeof item === "string" && /^[A-Z]$/i.test(item.trim()) ? item.trim().toUpperCase().charCodeAt(0) - 65 : null));
    if (index !== null && options[index] !== undefined) {
      const raw = options[index];
      const text = typeof raw === "object" ? raw.text || raw.label || JSON.stringify(raw) : String(raw);
      return `${String.fromCharCode(65 + index)}. ${text}`;
    }
    return String(item);
  };
  return Array.isArray(value) ? value.map(renderOne).join("；") : renderOne(value);
}
function statusText(value: string) {
  const map: Record<string, string> = { published: "已发布", review: "待审核", draft: "草稿", active: "正常", done: "已完成", pending: "待处理" };
  return map[value] || value || "-";
}
function quizQuestionMeta(quiz: any) {
  const count = quiz.question_count || quiz.questions_count || quiz.questions?.length || 0;
  return count ? `${count}题` : `${quiz.total_score || 0}分`;
}
function quizScoreLabel(quiz: any) {
  const attempt = quiz.latest_attempt || quiz.last_attempt || quiz.best_attempt;
  if (attempt?.correct_count !== undefined && attempt?.total_count) return `${attempt.correct_count}/${attempt.total_count}`;
  if (attempt?.score !== undefined) return `${Math.round(Number(attempt.score))}分`;
  return statusText(quiz.status || "published");
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

const DefaultUserAvatar = defineComponent({
  setup() {
    return () => h("svg", { class: "default-user-avatar", viewBox: "0 0 64 64", role: "img", "aria-label": "默认头像" }, [
      h("rect", { width: 64, height: 64, rx: 32, fill: "#EEF2FF" }),
      h("circle", { cx: 32, cy: 25, r: 11, fill: "#6366F1", opacity: "0.95" }),
      h("path", { d: "M16 53c2.8-10.2 9-15.4 16-15.4S45.2 42.8 48 53", fill: "#4F46E5", opacity: "0.92" }),
      h("path", { d: "M48 12l1.8 4.4L54 18l-4.2 1.6L48 24l-1.8-4.4L42 18l4.2-1.6L48 12Z", fill: "#06B6D4" }),
      h("path", { d: "M18 14l1.1 2.7L22 18l-2.9 1.3L18 22l-1.1-2.7L14 18l2.9-1.3L18 14Z", fill: "#8B5CF6" })
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
    return () => h("article", { class: "profile-activity-card" }, [
      h("div", { class: "section-head" }, [h("h2", [h(Clock, { size: 18 }), "学习动态"])]),
      p.items.length
        ? p.items.map((item) => h("div", { class: "profile-timeline-item", key: `${item.type}-${item.title}-${item.time}` }, [
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
    const root = ref<HTMLElement | null>(null);
    const options = computed(() => normalizeItems(p.items));
    const current = computed(() => options.value.find((item) => item.value === p.modelValue)?.label || options.value[0]?.label || "请选择");
    function close() { open.value = false; }
    function onPointerDown(event: PointerEvent) { if (!root.value?.contains(event.target as Node)) close(); }
    function onKeydown(event: KeyboardEvent) { if (event.key === "Escape") close(); }
    onMounted(() => {
      document.addEventListener("pointerdown", onPointerDown);
      document.addEventListener("keydown", onKeydown);
    });
    onBeforeUnmount(() => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeydown);
    });
    return () => h("div", { ref: root, class: "select-menu" }, [
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
    const root = ref<HTMLElement | null>(null);
    function close() { open.value = false; }
    function onPointerDown(event: PointerEvent) { if (!root.value?.contains(event.target as Node)) close(); }
    function onKeydown(event: KeyboardEvent) { if (event.key === "Escape") close(); }
    onMounted(() => {
      document.addEventListener("pointerdown", onPointerDown);
      document.addEventListener("keydown", onKeydown);
    });
    onBeforeUnmount(() => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeydown);
    });
    return () => h("div", { ref: root, class: "dropdown-menu" }, [
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
      const nextId = Number(value);
      if (nextId === selectedCourseId.value) {
        await loadActive();
        return;
      }
      selectedCourseId.value = nextId;
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
    function attachmentNodes(message: ChatMessage) {
      if (!message.attachments?.length) return null;
      return h("div", { class: "chat-attachments" }, message.attachments.map((item, index) => h("a", { key: `${item.url}-${index}`, href: item.url, target: "_blank", class: "chat-attachment" }, [
        h("img", { src: item.url, alt: item.filename || "图片" }),
        h("span", item.filename || `图片${index + 1}`)
      ])));
    }
    function bubble(message: ChatMessage) {
      if (p.large && message.role === "user") {
        return h("div", { class: "chat-bubble bubble-user" }, [h("p", message.text), attachmentNodes(message)]);
      }
      if (p.large && message.role === "ai") {
        return h("div", { class: "chat-bubble bubble-ai" }, [
          message.thought ? h("button", { type: "button", class: "thought-toggle thinking-process", onClick: () => update("toggle-thought", message) }, [h(Sparkles, { size: 13 }), "思考过程", h(ChevronDown, { size: 13, class: { rotate: message.thoughtOpen } })]) : null,
          h(Transition, { name: "thought-roll" }, { default: () => message.thought && message.thoughtOpen ? h("div", { class: "thought markdown-body", innerHTML: renderRichText(message.thought) }) : null }),
          h("div", { class: "ai-content-card" }, [
            message.outOfScope ? h("span", { class: "tag tag-warning" }, "可能超纲") : null,
            message.text
              ? h("div", { class: "ai-text markdown-body", innerHTML: renderRichText(message.text) })
              : h("div", { class: "ai-text streaming-placeholder" }, message.streaming ? "AI 正在生成..." : ""),
            message.sources?.length ? h("div", { class: "source-tags references-area" }, [
              h("span", { class: "source-label ref-label" }, [h(BookOpen, { size: 14 }), "引用来源："]),
              ...message.sources.slice(0, 3).map((source, index) => h("span", { class: "tag ref-tag", key: index }, source.title || source.material_title || `来源${index + 1}`))
            ]) : null,
            h("div", { class: "msg-actions ai-action-bar" }, [
              h("button", { type: "button", title: "复制", class: "ai-action-btn", disabled: !message.text, onClick: () => update("copy", message.text) }, [h(Copy, { size: 16 }), "复制"]),
              !message.streaming && message.record_id ? h("button", { type: "button", title: message.favorite ? "已收藏" : "收藏", class: "ai-action-btn", onClick: () => update("favorite", message) }, [h(BookMarked, { size: 16 }), message.favorite ? "已收藏" : "收藏"]) : null,
              !message.streaming && message.record_id ? h("button", { type: "button", title: "有用", class: "ai-action-btn success", onClick: () => update("feedback", message, "positive") }, [h(Check, { size: 16 }), "有用"]) : null
            ])
          ])
        ]);
      }
      const body = [
        message.thought ? h("button", { type: "button", class: "thought-toggle", onClick: () => update("toggle-thought", message) }, [h(Sparkles, { size: 13 }), "思考过程", h(ChevronDown, { size: 13, class: { rotate: message.thoughtOpen } })]) : null,
        h(Transition, { name: "thought-roll" }, { default: () => message.thought && message.thoughtOpen ? h("div", { class: "thought markdown-body", innerHTML: renderRichText(message.thought) }) : null }),
        message.outOfScope ? h("span", { class: "tag tag-warning" }, "可能超纲") : null,
        message.role === "ai"
          ? (message.text ? h("div", { class: "ai-text markdown-body", innerHTML: renderRichText(message.text) }) : h("div", { class: "ai-text streaming-placeholder" }, message.streaming ? "AI 正在生成..." : ""))
          : [h("p", message.text), attachmentNodes(message)],
        message.sources?.length ? h("div", { class: "source-tags" }, [
          h("span", { class: "source-label" }, [h(BookOpen, { size: 14 }), "引用来源："]),
          ...message.sources.slice(0, 3).map((source, index) => h("span", { class: "tag", key: index }, source.title || source.material_title || `来源${index + 1}`))
        ]) : null,
        h("div", { class: "msg-actions" }, [
          h("button", { type: "button", title: "复制", disabled: !message.text, onClick: () => update("copy", message.text) }, [h(Copy, { size: 13 }), "复制"]),
          message.role === "ai" && p.large && !message.streaming && message.record_id ? h("button", { type: "button", title: message.favorite ? "已收藏" : "收藏", onClick: () => update("favorite", message) }, [h(BookMarked, { size: 13 }), message.favorite ? "已收藏" : "收藏"]) : null,
          message.role === "ai" && p.large && !message.streaming && message.record_id ? h("button", { type: "button", title: "有用", class: "success", onClick: () => update("feedback", message, "positive") }, [h(Check, { size: 13 }), "有用"]) : null
        ])
      ];
      return h("div", { class: "chat-bubble" }, body);
    }
    function avatar(message: ChatMessage) {
      return h("span", { class: ["chat-avatar", p.large ? (message.role === "user" ? "avatar-user" : "avatar-ai") : ""] }, [message.role === "user" ? h(User, { size: 16 }) : h(Sparkles, { size: 16 })]);
    }
    return () => {
      const hasStreamingMessage = p.messages.some((message) => message.streaming);
      return h("div", { class: ["chat-list", p.large ? "large" : ""] }, [
      ...p.messages.map((message) => h("article", { key: message.id, class: ["chat-msg", p.large ? "message-row" : "", message.role] }, message.role === "user" ? [bubble(message), avatar(message)] : [avatar(message), bubble(message)])),
      p.thinking && !hasStreamingMessage ? h("div", { class: "thinking ai-thinking-border" }, [h("i", { class: "dot-1" }), h("i", { class: "dot-2" }), h("i", { class: "dot-3" }), h("span", "AI 正在思考...")]) : null
    ]);
    };
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
      h(Transition, { name: "accordion" }, {
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
    return () => h("article", { class: "tutoring-history-card" }, [
      h("header", { class: "tutoring-history-head" }, [
        h("h2", [h(Clock, { size: 18 }), p.title]),
        h("span", { class: "tag" }, `${p.items.length} 条`)
      ]),
      p.items.length ? h("div", { class: "tutoring-history-grid" }, p.items.slice(0, 6).map((item) => h("button", { type: "button", key: item.id, class: "tutoring-history-item", onClick: () => update("pick", item) }, [
        h("strong", item.corrected_text || item.ocr_text || item.raw_text || "题目"),
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
    attempt: { type: Object as PropType<any>, default: null },
    submitting: { type: Boolean, default: false }
  },
  emits: ["answer", "submit", "exit"],
  setup(p, { emit: update }) {
    const current = ref(0);
    const marked = ref<number[]>([]);
    const confirming = ref(false);
    const elapsed = ref(0);
    const analysisOpen = ref<Record<string, boolean>>({});
    let timer: number | undefined;
    onMounted(() => { timer = window.setInterval(() => { elapsed.value += 1; }, 1000); });
    onBeforeUnmount(() => { if (timer) window.clearInterval(timer); });
    const questions = computed(() => p.quiz?.questions || []);
    const quizMeta = computed(() => p.quiz?.quiz || {});
    const question = computed(() => questions.value[current.value] || null);
    const answeredCount = computed(() => questions.value.filter((item: any) => hasAnswer(item)).length);
    const attemptData = computed(() => p.attempt?.attempt || p.attempt);
    const attemptAnswers = computed(() => p.attempt?.answers || []);
    const unansweredCount = computed(() => Math.max(0, questions.value.length - answeredCount.value));
    const progressPercent = computed(() => Math.round(((current.value + 1) / Math.max(questions.value.length, 1)) * 100));
    function answerValue(item: any) {
      return p.answers[item.id];
    }
    function hasAnswer(item: any) {
      const value = p.answers[item.id];
      return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== "";
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
    function questionTypeLabel(type?: string) {
      const map: Record<string, string> = {
        single_choice: "单选题",
        multiple_choice: "多选题",
        judge: "判断题",
        blank: "填空题",
        short_answer: "简答题",
      };
      return map[String(type || "")] || "题目";
    }
    function difficultyLabel(value?: string) {
      const map: Record<string, string> = {
        easy: "基础难度",
        standard: "标准难度",
        medium: "标准难度",
        hard: "进阶难度",
      };
      return map[String(value || "")] || String(value || "标准难度");
    }
    function submit() {
      if (p.submitting) return;
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
        return h("div", { class: "exam-options-group" }, options.map((option: any, index: number) => {
          const value = index;
          const selected = item.question_type === "multiple_choice" ? (answerValue(item) || []).includes(value) : answerValue(item) === value;
          return h("label", { class: "exam-opt-label" }, [
            h("input", {
              type: item.question_type === "multiple_choice" ? "checkbox" : "radio",
              name: `question-${item.id}`,
              class: "exam-opt-input",
              checked: selected,
              onChange: () => setAnswer(item, value)
            }),
            h("div", { class: "exam-opt-card" }, [
              h("div", { class: "exam-opt-letter" }, optionLabel(index)),
              h("div", { class: "exam-opt-text" }, typeof option === "object" ? option.text || option.label || JSON.stringify(option) : String(option))
            ])
          ]);
        }));
      }
      if (item.question_type === "blank") {
        return h("input", { class: "exam-answer-input", value: answerValue(item) || "", placeholder: "填写答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLInputElement).value) });
      }
      return h("div", { class: "exam-text-answer" }, [
        h("textarea", { class: "exam-answer-textarea", value: answerValue(item) || "", maxlength: 500, placeholder: "写下你的答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLTextAreaElement).value) }),
        h("small", `${String(answerValue(item) || "").length} / 500`)
      ]);
    }
    function renderResult() {
      const accuracy = Number(attemptData.value?.accuracy || 0);
      const rowOpen = (row: any) => analysisOpen.value[String(row.question_id)] ?? !row.is_correct;
      const toggleRow = (row: any) => {
        const key = String(row.question_id);
        analysisOpen.value = { ...analysisOpen.value, [key]: !rowOpen(row) };
      };
      return h("section", { class: "exam-shell exam-result-shell" }, [
        h("header", { class: "exam-header" }, [
          h("button", { type: "button", class: "exam-exit-btn", onClick: () => update("exit") }, [h(ArrowLeft, { size: 18 }), "返回练习"]),
          h("div", { class: "exam-title" }, quizMeta.value.title || "练习结果"),
          h("div", { class: "timer-widget" }, [h(Clock, { size: 16 }), h("span", { class: "timer-text" }, timeLabel(elapsed.value))])
        ]),
        h("main", { class: "exam-result-main" }, [
          h("article", { class: "exam-result-card" }, [
            accuracy >= 60 ? h(CheckCircle, { size: 48 }) : h(XCircle, { size: 48 }),
            h("strong", String(Math.round(Number(attemptData.value?.score || 0)))),
            h("span", `分 / ${Math.round(Number(attemptData.value?.total_score || quizMeta.value.total_score || 100))} 分`),
            h("em", scoreLevel(accuracy)),
            h("small", `用时 ${timeLabel(elapsed.value)} · 正确率 ${accuracy}%`)
          ]),
          h("article", { class: "exam-result-summary" }, [
            h("div", [h("h2", [h(Sparkles, { size: 18 }), "AI 建议"]), h("p", attemptData.value?.ai_feedback || "复盘错题，并回看对应知识点。")])
          ]),
          h("article", { class: "exam-analysis-card" }, [
            h("div", { class: "exam-analysis-head" }, [h("h2", "题目解析")]),
            attemptAnswers.value.length
              ? attemptAnswers.value.map((row: any, index: number) => {
                const open = rowOpen(row);
                return h("div", { key: row.question_id, class: ["exam-analysis-item", open ? "open" : ""] }, [
                  h("button", { type: "button", class: "exam-analysis-trigger", onClick: () => toggleRow(row) }, [
                    row.is_correct ? h(CheckCircle, { size: 16 }) : h(XCircle, { size: 16 }),
                    `题目 ${index + 1}`,
                    h("span", row.is_correct ? "正确" : "错误"),
                    h(ChevronDown, { size: 15 })
                  ]),
                  h(Transition, { name: "accordion" }, {
                    default: () => open ? h("section", { class: "exam-analysis-body" }, [
                      h("p", row.question?.stem || ""),
                      h("small", `你的答案：${optionText(row.user_answer, row.question)} · 正确答案：${optionText(row.correct_answer, row.question)}`),
                      h("div", row.feedback || row.question?.explanation || "暂无解析")
                    ]) : null
                  })
                ]);
              })
              : h("p", attemptData.value?.ai_feedback || "提交完成")
          ])
        ])
      ]);
    }
    return () => {
      if (p.attempt) return renderResult();
      const item = question.value;
      if (!item) return h("div", { class: "exam-shell exam-empty-shell" }, [h(EmptyState, { text: "暂无题目" })]);
      const unanswered = questions.value.filter((entry: any) => !hasAnswer(entry)).map((entry: any, index: number) => index + 1);
      return h("section", { class: "exam-shell" }, [
        h("header", { class: "exam-header" }, [
          h("button", { type: "button", class: "exam-exit-btn", onClick: () => update("exit") }, [h(ArrowLeft, { size: 18 }), "退出练习"]),
          h("div", { class: "exam-title" }, quizMeta.value.title || "章节练习"),
          h("div", { class: "timer-widget" }, [h(Clock, { size: 16 }), h("span", { class: "timer-text" }, timeLabel(elapsed.value))])
        ]),
        h("main", { class: "exam-container" }, [
          h("aside", { class: "exam-nav-sidebar" }, [
            h("div", { class: "exam-nav-card" }, [
              h("div", { class: "exam-nav-stats" }, [
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(answeredCount.value)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-answered" }), "已答"])]),
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(marked.value.length)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-marked" }), "标记"])]),
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(unansweredCount.value)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-unanswered" }), "未答"])])
              ]),
              h("div", { class: "exam-q-grid" }, questions.value.map((entry: any, index: number) => h("button", {
              type: "button",
                class: ["exam-q-btn", hasAnswer(entry) ? "answered" : "", index === current.value ? "current" : "", marked.value.includes(entry.id) ? "marked" : ""],
              onClick: () => { current.value = index; }
              }, String(index + 1))))
            ])
          ]),
          h("section", { class: "exam-question-area" }, [
            h("article", { class: "exam-q-card" }, [
              h("div", { class: "exam-q-meta-row" }, [
                h("div", { class: "exam-q-tags" }, [
                  h("span", { class: "exam-q-number" }, `题目 ${current.value + 1}`),
                  h("span", { class: "exam-tag exam-tag-type" }, questionTypeLabel(item.question_type)),
                  h("span", { class: "exam-tag exam-tag-diff" }, difficultyLabel(item.difficulty))
                ]),
                h("button", { type: "button", class: ["exam-mark-btn", marked.value.includes(item.id) ? "is-marked" : ""], onClick: () => { marked.value = marked.value.includes(item.id) ? marked.value.filter((id) => id !== item.id) : [...marked.value, item.id]; } }, [
                  h(Flag, { size: 16 }),
                  marked.value.includes(item.id) ? "已标记" : "标记稍后看"
                ])
            ]),
              h("div", { class: "exam-q-stem" }, item.stem),
              renderQuestionBody(item)
            ])
          ])
        ]),
        h("footer", { class: "exam-action-footer" }, [
          h("div", { class: "exam-footer-container" }, [
            h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: current.value <= 0, onClick: () => { current.value = Math.max(0, current.value - 1); } }, [h(ArrowLeft, { size: 18 }), "上一题"]),
            h("div", { class: "exam-footer-progress" }, [
              h("span", { class: "exam-prog-text" }, `第 ${current.value + 1} / ${questions.value.length} 题`),
              h("div", { class: "exam-prog-bar" }, [h("div", { class: "exam-prog-fill", style: { width: `${progressPercent.value}%` } })])
            ]),
            h("div", { class: "exam-footer-actions" }, [
              h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: current.value >= questions.value.length - 1, onClick: () => { current.value = Math.min(questions.value.length - 1, current.value + 1); } }, ["下一题", h(ArrowRight, { size: 18 })]),
              h("button", { type: "button", class: "exam-btn exam-btn-primary", disabled: p.submitting, "data-loading": p.submitting, onClick: () => { confirming.value = true; } }, [h(Check, { size: 16 }), "交卷"])
            ])
          ])
        ]),
        h(Transition, { name: "modal-pop" }, {
          default: () => confirming.value ? h("div", { class: "exam-modal-mask" }, [
            h("article", { class: "exam-confirm-card" }, [
              h("div", { class: "exam-modal-head" }, [h(AlertTriangle, { size: 22 }), h("h2", "确认交卷"), h("button", { type: "button", onClick: () => { confirming.value = false; } }, [h(X, { size: 16 })])]),
              h("p", unanswered.length ? `还有 ${unanswered.length} 道未答` : "所有题目已作答"),
              marked.value.length ? h("p", `已标记 ${marked.value.length} 道`) : null,
              h("footer", [h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: p.submitting, onClick: () => { confirming.value = false; } }, "继续作答"), h("button", { type: "button", class: "exam-btn exam-btn-primary", disabled: p.submitting, "data-loading": p.submitting, onClick: submit }, "确认交卷")])
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
      h("div", { class: "wrong-card-top" }, [
        h("span", { class: ["wrong-state", p.item.is_resolved ? "resolved" : "pending"] }, p.item.is_resolved ? "已掌握" : "待重练"),
        h("span", { class: "wrong-times" }, `错 ${p.item.wrong_count || 1} 次`)
      ]),
      h("h2", p.item.question?.stem || "错题"),
      h("p", p.item.question?.explanation || "建议重新练习"),
      h("div", { class: "wrong-card-tags" }, [
        h("span", { class: "tag tag-warning" }, p.item.knowledge_point_name || "未标注知识点"),
        p.item.last_wrong_at ? h("span", { class: "tag" }, `最近出错 ${relativeTime(p.item.last_wrong_at)}`) : null,
        p.item.resolved_at ? h("span", { class: "tag tag-success" }, `掌握 ${relativeTime(p.item.resolved_at)}`) : null
      ]),
      h("footer", [h("button", { type: "button", class: "btn btn-primary btn-sm", onClick: () => update("practice") }, [h(RefreshCw, { size: 14 }), p.item.is_resolved ? "再练一次" : "重练"])])
    ]);
  }
});

const PopoverButton = defineComponent({
  props: {
    label: { type: String, required: true },
    items: { type: Array as PropType<SelectOption[]>, default: () => [] },
    placement: { type: String as PropType<"top" | "bottom">, default: "bottom" }
  },
  emits: ["select"],
  setup(p, { emit: update }) {
    const open = ref(false);
    const root = ref<HTMLElement | null>(null);
    function close() { open.value = false; }
    function onPointerDown(event: PointerEvent) { if (!root.value?.contains(event.target as Node)) close(); }
    function onKeydown(event: KeyboardEvent) { if (event.key === "Escape") close(); }
    onMounted(() => {
      document.addEventListener("pointerdown", onPointerDown);
      document.addEventListener("keydown", onKeydown);
    });
    onBeforeUnmount(() => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeydown);
    });
    const popStyle = computed(() => p.placement === "top" ? {
      top: "auto",
      right: "0",
      bottom: "calc(100% + 10px)",
      transformOrigin: "bottom center"
    } : undefined);
    return () => h("div", { ref: root, class: ["popover-button select-menu", `placement-${p.placement}`] }, [
      h("button", { type: "button", onClick: () => { open.value = !open.value; } }, [p.label, h(ChevronDown, { size: 14 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop", style: popStyle.value }, p.items.map((item) => h("button", { type: "button", key: item.value, onClick: () => { update("select", String(item.value)); open.value = false; } }, item.label))) : null
      })
    ]);
  }
});

function onStudentDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node;
  if (topActionsRef.value?.contains(target) || noticePopRef.value?.contains(target) || userPopRef.value?.contains(target)) return;
  noticeOpen.value = false;
  userMenuOpen.value = false;
}
function onStudentDocumentKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  noticeOpen.value = false;
  userMenuOpen.value = false;
  settingsOpen.value = false;
}
function onStudentVisibilityChange() {
  if (!document.hidden) void loadNotifications(true);
}
function onStudentWindowFocus() {
  void loadNotifications(true);
}

onMounted(async () => {
  document.addEventListener("pointerdown", onStudentDocumentPointerDown);
  document.addEventListener("keydown", onStudentDocumentKeydown);
  document.addEventListener("visibilitychange", onStudentVisibilityChange);
  window.addEventListener("focus", onStudentWindowFocus);
  await loadCourses();
  await loadActive();
  await loadNotifications(true);
  notificationTimer = window.setInterval(() => {
    if (!document.hidden) void loadNotifications(true);
  }, 15000);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onStudentDocumentPointerDown);
  document.removeEventListener("keydown", onStudentDocumentKeydown);
  document.removeEventListener("visibilitychange", onStudentVisibilityChange);
  window.removeEventListener("focus", onStudentWindowFocus);
  stopStudyClock();
  if (chromeTimer) clearTimeout(chromeTimer);
  if (joinTimer) clearTimeout(joinTimer);
  if (notificationTimer) clearInterval(notificationTimer);
  if (noteTimer) clearTimeout(noteTimer);
});
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
.avatar-btn img, .avatar-btn .default-user-avatar { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
.global-search { position: fixed; inset: 0; z-index: var(--z-modal); height: 64px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; background: white; padding: 0 32px; }
.global-search input { border: 0; outline: 0; font-size: 18px; }
.global-search button { border: 0; background: transparent; color: var(--color-text-muted); }
.notice-pop, .user-pop { position: fixed; top: 58px; right: 24px; z-index: var(--z-popover); width: 360px; border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-lg); padding: 10px; }
.user-pop { width: 220px; display: grid; gap: 4px; }
.user-pop button, .notice-item { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 10px; text-align: left; }
.user-card { border-bottom: 1px solid var(--color-border-subtle); padding: 10px; }
.user-card strong, .notice-item strong { color: var(--color-text-primary); }
.user-card small, .notice-item small { color: var(--color-text-muted); }
.notice-item p { margin: 3px 0; color: var(--color-text-secondary); font-size: 12px; line-height: 1.45; }
.notice-item i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-primary-600); }
.student-main { max-width: 1100px; margin: 0 auto; padding: 24px 24px 16px; }
.student-page { display: grid; gap: 16px; animation: fade-slide-up var(--duration-base) var(--ease-out); }
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
.home-grid, .course-layout, .tutoring-grid { display: grid; grid-template-columns: 55fr 45fr; gap: 16px; }
.panel-card, .course-tools, .student-course-card, .knowledge-head, .knowledge-body, .wrong-hero, .profile-hero, .badge-card { border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 18px; }
.section-head, .page-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-head h2, .page-title-row h1 { display: flex; align-items: center; gap: 8px; margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.page-title-row p { margin: 4px 0 0; color: var(--color-text-muted); }
.page-title-actions { display: flex; align-items: center; gap: 8px; }
.home-course { width: 100%; display: grid; grid-template-columns: 44px 1fr; align-items: center; gap: 12px; border: 0; border-radius: var(--radius-lg); background: white; padding: 12px; text-align: left; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out); }
.home-course:hover, .student-course-card:hover, .quick-tile:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.home-course > span { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 10px; color: white; }
.home-course strong { color: var(--color-text-primary); }.home-course small { display: block; color: var(--color-text-muted); }.home-course em { color: var(--color-text-muted); font-size: 12px; font-style: normal; }
.join-dashed { width: 100%; min-height: 52px; display: flex; align-items: center; justify-content: center; gap: 8px; border: 1px dashed var(--color-border-strong); border-radius: var(--radius-lg); background: white; color: var(--color-primary-700); }
.rings { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 20px 0; }
.ring-block { display: grid; justify-items: center; gap: 6px; text-align: center; }.ring-wrap { position: relative; width: 72px; height: 72px; display: grid; place-items: center; }.ring-wrap svg { transform: rotate(-90deg); }.ring-wrap strong { position: absolute; color: var(--color-text-primary); }
.week-check { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; border-top: 1px solid var(--color-border-subtle); padding-top: 14px; }
.week-check span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; border: 1px dashed var(--color-border-strong); color: var(--color-text-muted); }
.week-check .done { border: 0; background: var(--color-primary-600); color: white; }.week-check .today { animation: pulse-ring var(--duration-slow) var(--ease-in-out) infinite; }
.streak { display: flex; align-items: center; gap: 6px; margin-top: 12px; color: var(--color-warning-700); }
.profile-activity-card { display: grid; gap: 12px; }
.profile-timeline-item { display: grid; grid-template-columns: 18px 1fr auto; gap: 10px; position: relative; }
.profile-timeline-item::before { content: ""; position: absolute; left: 8px; top: 18px; bottom: -14px; width: 1px; background: var(--color-border-default); }
.profile-timeline-item i { width: 9px; height: 9px; border-radius: 50%; background: var(--color-primary-600); margin-top: 6px; }
.profile-timeline-item strong { color: var(--color-text-primary); }
.profile-timeline-item p, .profile-timeline-item time { margin: 0; color: var(--color-text-muted); font-size: 12px; }
.course-tools { display: grid; grid-template-columns: 220px 160px 1fr; align-items: center; gap: 12px; }
.pretty-input { display: flex; align-items: center; gap: 8px; height: 38px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 0 12px; }
.pretty-input input { width: 100%; border: 0; outline: 0; }
.select-menu, .dropdown-menu { position: relative; }
.select-menu > button, .dropdown-trigger { min-height: 38px; display: inline-flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-text-body); padding: 0 12px; }
.select-pop, .dropdown-pop { position: absolute; top: calc(100% + 6px); z-index: var(--z-popover); min-width: 180px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 6px; transform-origin: top center; animation: popover-in var(--duration-fast) var(--ease-out) both; will-change: opacity, transform; }
.select-pop button, .dropdown-pop button { width: 100%; min-height: 34px; display: flex; align-items: center; gap: 8px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 0 10px; text-align: left; }.select-pop button.active, .select-pop button:hover, .dropdown-pop button:hover { background: var(--color-primary-50); color: var(--color-primary-700); }.dropdown-pop .danger { color: var(--color-danger-700); }
.course-select { min-width: 180px; }.select-menu-empty { display: inline-flex; align-items: center; gap: 6px; min-height: 38px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-primary-700); padding: 0 12px; }
.underline-tabs, .seg-tabs, .study-tabs, .profile-tabs { display: flex; gap: 14px; border-bottom: 1px solid var(--color-border-default); }
.underline-tabs button, .seg-tabs button, .study-tabs button, .profile-tabs button { display: inline-flex; align-items: center; gap: 7px; min-height: 42px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-secondary); padding: 0 8px; }
.underline-tabs .active, .seg-tabs .active, .study-tabs .active, .profile-tabs .active { border-bottom-color: var(--color-primary-600); color: var(--color-primary-700); font-weight: 600; }
.student-course-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.student-course-card { overflow: hidden; padding: 0; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out); }
.course-art { position: relative; aspect-ratio: 16/9; display: grid; place-items: center; color: white; }.course-art svg { transition: transform var(--duration-base) var(--ease-out); }.student-course-card:hover .course-art > svg { transform: scale(1.05); }
.course-art span, .course-art em { position: absolute; bottom: 12px; border-radius: var(--radius-full); background: rgba(255,255,255,0.22); backdrop-filter: blur(8px); color: white; padding: 4px 8px; font-style: normal; }.course-art span { left: 12px; }.course-art em { right: 12px; display: flex; align-items: center; gap: 4px; }
.course-art .dropdown-menu { position: absolute; top: 12px; right: 12px; width: auto; }.course-art .dropdown-trigger { width: 38px; height: 38px; min-height: 38px; justify-content: center; padding: 0; border: 1px solid rgba(255,255,255,0.56); border-radius: 50%; background: rgba(255,255,255,0.22); color: white; }
.student-course-card section { padding: 18px; }.student-course-card h2 { margin: 0; color: var(--color-text-primary); font-size: 16px; }.student-course-card p, .course-meta { display: flex; align-items: center; gap: 6px; color: var(--color-text-muted); font-size: 13px; }.course-meta { justify-content: space-between; }
.mini-data { display: flex; gap: 16px; color: var(--color-text-secondary); font-size: 13px; margin: 12px 0; }.mini-data span { display: flex; align-items: center; gap: 5px; }
.full { width: 100%; }
.course-hero-student { min-height: 180px; display: grid; grid-template-columns: 1fr 180px; align-items: center; gap: 24px; border-radius: 24px; color: white; padding: 32px; overflow: hidden; }.course-hero-student h1 { margin: 0; font-size: 26px; }.course-hero-student p, .course-hero-student div { display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.78); }.course-hero-student .hero-progress { width: 100px; background: rgba(255,255,255,0.28); }.slide-mini { width: 120px; height: 90px; display: grid; place-items: center; border-radius: 12px; background: white; color: var(--color-text-primary); box-shadow: 0 8px 32px rgba(0,0,0,0.35); transform: rotate(-3deg); transition: transform var(--duration-base) var(--ease-out); }.slide-mini:hover { transform: rotate(0) scale(1.03); }
.quick-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }.quick-tile { min-height: 80px; display: grid; justify-items: start; gap: 4px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 14px; text-align: left; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out); }.quick-tile span { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--color-primary-50); color: var(--color-primary-700); }.quick-tile strong { color: var(--color-text-primary); }
.course-layout { grid-template-columns: 60fr 40fr; align-items: start; }.course-layout > section, .course-layout > aside { display: grid; gap: 16px; }
.lesson-item { position: relative; display: grid; grid-template-columns: 40px 1fr auto; align-items: center; gap: 12px; width: 100%; min-height: 72px; border: 0; border-bottom: 1px solid var(--color-border-subtle); background: white; text-align: left; padding: 8px; }.lesson-item.current { background: var(--color-primary-50); box-shadow: inset 3px 0 0 var(--color-primary-600); }.lesson-item b { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 8px; background: var(--color-primary-50); color: var(--color-primary-700); }.lesson-item strong { color: var(--color-text-primary); }.lesson-item small { color: var(--color-text-muted); }
.material-row { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 10px; min-height: 56px; border-bottom: 1px solid var(--color-border-subtle); }.file-badge { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 8px; background: var(--color-primary-600); color: white; }.material-row strong { color: var(--color-text-primary); }.material-row small { display: block; color: var(--color-text-muted); }
.data-grid, .achievement-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }.mini-metric { min-height: 68px; display: grid; grid-template-columns: auto 1fr; gap: 6px; border-radius: 8px; background: var(--color-bg-muted); padding: 12px; }.mini-metric strong { color: var(--color-text-primary); font-size: 22px; }.mini-metric span { color: var(--color-text-muted); font-size: 11px; }.mini-metric.success svg { color: var(--color-success-500); }.mini-metric.ai svg { color: #8B5CF6; }.mini-metric.danger svg { color: var(--color-danger-500); }.mini-metric.warning svg { color: var(--color-warning-500); }
.ask-card { display: grid; gap: 10px; border-radius: var(--radius-xl); background: linear-gradient(135deg, rgba(6,182,212,0.1), rgba(139,92,246,0.1)); border-left: 4px solid #8B5CF6; padding: 18px; }.ask-card h2 { margin: 0; color: var(--color-text-primary); }.ask-card form, .chat-input { display: grid; grid-template-columns: 1fr auto; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 6px; }.ask-card input, .chat-input textarea { border: 0; outline: 0; resize: none; padding: 6px 10px; }.ask-card button:not(.quick-tags button), .send-btn { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 50%; background: var(--color-primary-600); color: white; }
.quick-tags { display: flex; gap: 8px; overflow-x: auto; }.quick-tags button { border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; color: var(--color-text-secondary); padding: 5px 10px; white-space: nowrap; transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out); }.quick-tags button:hover { background: var(--color-primary-50); color: var(--color-primary-700); transform: translateY(-1px); }
.class-chat .chat-list { display: grid; gap: 18px; padding: 20px 0; }
.class-chat .chat-msg { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 10px; align-items: start; max-width: 86%; animation: bubble-in var(--duration-base) var(--ease-out); }
.class-chat .chat-msg.user { grid-template-columns: minmax(0, 1fr) 36px; justify-self: end; }
.class-chat .chat-avatar { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: var(--color-ai-gradient); color: white; box-shadow: var(--shadow-sm); }
.class-chat .chat-bubble { position: relative; border: 1px solid var(--color-border-default); border-radius: 4px 16px 16px 16px; background: white; padding: 12px 16px; }
.class-chat .chat-bubble::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; border-radius: 3px 0 0 3px; background: var(--color-ai-gradient); }
.class-chat .chat-msg.user .chat-bubble { border: 0; border-radius: 16px 4px 16px 16px; background: var(--color-primary-600); color: white; }
.class-chat .chat-msg.user .chat-bubble::before { display: none; }
.class-chat .chat-bubble p { margin: 0; line-height: 1.7; }
.class-chat .source-tags { display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--color-border-subtle); margin-top: 10px; padding-top: 10px; }
.class-chat .msg-actions { display: flex; gap: 8px; opacity: 0; transition: opacity var(--duration-fast) var(--ease-out); }
.class-chat .chat-bubble:hover .msg-actions { opacity: 1; }
.class-chat .msg-actions button,
.class-chat .thought-toggle { border: 0; background: transparent; color: var(--color-text-muted); }
.class-chat .thought-toggle svg { transition: transform var(--duration-fast) var(--ease-out); }
.class-chat .rotate { transform: rotate(180deg); }
.class-chat .thought { overflow: hidden; border-radius: var(--radius-md); background: var(--color-ai-light); color: #6D28D9; margin-bottom: 10px; padding: 8px; font-size: 12px; }
.class-chat .thinking { display: inline-flex; align-items: center; gap: 7px; width: fit-content; border-radius: 16px; background: white; color: var(--color-text-muted); padding: 10px 14px; box-shadow: var(--shadow-sm); }
.class-chat .thinking i { width: 7px; height: 7px; border-radius: 50%; background: var(--color-ai-gradient); }
.tutoring-grid { grid-template-columns: 55fr 45fr; align-items: start; }.tutor-input, .guide-card { display: grid; gap: 14px; }.problem-text { min-height: 160px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 14px; resize: vertical; }.image-drop { min-height: 200px; display: grid; place-items: center; border: 2px dashed var(--color-border-strong); border-radius: var(--radius-lg); color: var(--color-text-muted); }.image-drop input { display: none; }.knowledge-box { display: flex; flex-wrap: wrap; gap: 8px; border-radius: var(--radius-lg); background: var(--color-ai-light); padding: 12px; }
.empty-guide { display: grid; gap: 12px; justify-items: center; color: var(--color-text-muted); text-align: center; padding: 32px 0; }.guide-step { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); overflow: hidden; }.guide-step > button { width: 100%; display: flex; align-items: center; gap: 10px; border: 0; background: white; color: var(--color-text-primary); padding: 14px; text-align: left; }.guide-step b { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--color-primary-600); color: white; }.guide-body { display: grid; gap: 10px; border-top: 1px solid var(--color-border-subtle); padding: 14px; line-height: 1.7; }.guide-body p { margin: 0; }
.history-strip { display: grid; gap: 10px; }.history-strip div { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }.history-strip button { min-height: 80px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; text-align: left; padding: 12px; }
.knowledge-layout, .wrong-layout { display: grid; grid-template-columns: 280px 1fr; gap: 16px; align-items: start; }.knowledge-tree, .wrong-tree { display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 14px; }.knowledge-tree button, .wrong-tree button { display: flex; align-items: center; gap: 8px; min-height: 36px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); text-align: left; }.knowledge-tree button:hover, .wrong-tree button.active { background: var(--color-primary-50); color: var(--color-primary-700); }.weak-tags { display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--color-border-subtle); padding-top: 10px; }
.course-scope-label { display: inline-flex; align-items: center; gap: 6px; border-radius: var(--radius-md); background: var(--color-primary-50); color: var(--color-primary-700); padding: 10px 12px; font-size: 13px; }
.knowledge-content { display: grid; gap: 14px; }.knowledge-head h1 { margin: 0; color: var(--color-text-primary); font-size: 22px; }.knowledge-head p { color: var(--color-text-muted); }.knowledge-body { display: grid; gap: 16px; padding: 32px; }.knowledge-block h3 { display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); }.knowledge-block div { border-left: 4px solid var(--color-primary-600); border-radius: 14px; background: var(--color-primary-50); padding: 16px; line-height: 1.75; }.knowledge-block.ai div { border-left-color: #8B5CF6; background: var(--color-ai-light); }.knowledge-block.warning div { border-left-color: var(--color-warning-500); background: var(--color-warning-50); }.practice-cta { display: flex; align-items: center; gap: 10px; border-radius: var(--radius-lg); background: var(--color-ai-light); padding: 14px; }.practice-cta button { border: 0; border-radius: var(--radius-full); background: var(--color-primary-600); color: white; padding: 7px 12px; }
.quiz-list, .wrong-list { display: grid; gap: 12px; }.quiz-card, .wrong-card { position: relative; display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-left: 4px solid var(--color-success-500); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-sm); padding: 16px; }.quiz-card h2, .wrong-card h2 { margin: 0; color: var(--color-text-primary); font-size: 17px; }.quiz-card p, .wrong-card p { color: var(--color-text-muted); }.quiz-card footer, .wrong-card footer { display: flex; gap: 8px; }
.wrong-hero, .profile-hero { display: grid; grid-template-columns: auto repeat(3, 1fr) auto; align-items: center; gap: 20px; background: linear-gradient(135deg,#EF4444,#F59E0B); color: white; }.wrong-hero strong { display: block; font-size: 28px; }.wrong-tools { display: grid; grid-template-columns: 1fr 140px auto; gap: 10px; margin-bottom: 12px; }
.badges { display: flex; flex-wrap: wrap; gap: 8px; }.badges span { display: grid; place-items: center; min-width: 64px; min-height: 64px; border: 1px solid #F59E0B; border-radius: 12px; color: var(--color-warning-700); }.badges .locked { filter: grayscale(1); opacity: .5; border-color: var(--color-border-default); }
.profile-page { max-width: 800px; margin: 0 auto; display: grid; gap: 16px; }.profile-hero { grid-template-columns: auto 1fr auto; min-height: 160px; background: linear-gradient(135deg,#4338CA,#8B5CF6); color: white; }.big-avatar { width: 80px; height: 80px; border-radius: 50%; border: 4px solid white; font-size: 26px; font-weight: 700; position: relative; }.big-avatar svg { position: absolute; right: 0; bottom: 0; border-radius: 50%; background: var(--color-primary-600); padding: 3px; }.profile-hero h1 { margin: 0; }.profile-hero p { display: flex; align-items: center; gap: 6px; margin: 4px 0; color: rgba(255,255,255,0.78); }.profile-hero aside strong { display: block; font-size: 36px; }
.achievement-row { grid-template-columns: repeat(4, 1fr); }.profile-form { display: grid; gap: 12px; }.profile-form label { display: grid; gap: 6px; color: var(--color-text-secondary); }.toggle-line, .check-line { display: flex; align-items: center; gap: 10px; }.time-input { width: 120px; margin-left: auto; }
.modal-mask { position: fixed; inset: 0; z-index: var(--z-modal-bg); display: grid; place-items: center; background: rgba(15,23,42,0.36); backdrop-filter: blur(8px); }.join-modal { width: 480px; max-width: calc(100vw - 32px); border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-xl); padding: 20px; }.modal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }.modal-head h2 { flex: 1; margin: 0; color: var(--color-text-primary); }.code-input { display: grid; grid-template-columns: 1fr auto; align-items: center; height: 56px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 0 12px; }.code-input input { border: 0; outline: 0; text-align: center; letter-spacing: 8px; font: 20px var(--font-family-mono); text-transform: uppercase; }.code-input.ok { border-color: var(--color-success-500); }.code-input.error { border-color: var(--color-danger-500); }.field-error { color: var(--color-danger-700); }.preview-course { display: grid; grid-template-columns: 48px 1fr; gap: 10px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); margin-top: 14px; padding: 12px; }.preview-course span { display: grid; place-items: center; border-radius: 10px; color: white; }.preview-course small { color: var(--color-text-muted); }.hint-line { display: flex; align-items: center; gap: 6px; color: var(--color-warning-700); background: var(--color-warning-50); border-radius: var(--radius-md); margin-top: 12px; padding: 8px; }.join-modal footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.study-room { min-height: 100vh; background: #0A0F1E; color: white; animation: enter-study var(--duration-slower) var(--ease-out); }.study-head { position: fixed; inset: 0 0 auto; z-index: var(--z-sticky); height: 48px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; background: rgba(10,15,30,0.8); backdrop-filter: blur(12px); padding: 0 16px; }.study-head > div { display: flex; align-items: center; gap: 10px; }.study-head > div:last-child { justify-content: end; }.glass-btn, .icon-glass { display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: var(--radius-full); background: rgba(255,255,255,0.08); color: white; padding: 8px 10px; }.icon-glass { width: 34px; height: 34px; justify-content: center; padding: 0; }
.study-main { display: grid; grid-template-columns: 1fr 380px; min-height: 100vh; transition: grid-template-columns var(--duration-slow) var(--ease-out); }.study-room.panelClosed .study-main { grid-template-columns: 1fr 0; }.slide-stage { position: relative; display: grid; place-items: center; padding: 72px 32px 120px; overflow: hidden; }.slide-card { position: relative; width: min(960px, 92%); aspect-ratio: 16/9; display: grid; align-content: center; gap: 18px; border-radius: 8px; background: white; color: var(--color-text-primary); box-shadow: 0 0 0 1px rgba(255,255,255,0.1), 0 24px 48px rgba(0,0,0,0.6); padding: 52px; }.slide-card h1 { margin: 0; font-size: 30px; }.slide-card p { font-size: 18px; line-height: 1.8; }.page-badge, .knowledge-dot { position: absolute; border-radius: var(--radius-full); background: rgba(0,0,0,0.42); color: white; padding: 4px 8px; }.page-badge { right: 16px; bottom: 16px; }.knowledge-dot { right: 16px; top: 16px; background: var(--color-ai-gradient); }
.subtitle-line { position: absolute; bottom: 100px; max-width: 80%; border-radius: var(--radius-full); background: rgba(10,15,30,0.82); backdrop-filter: blur(10px); padding: 12px 24px; color: rgba(255,255,255,0.74); }.subtitle-line strong { color: white; font-weight: 600; }
.player-bar { position: absolute; left: 50%; bottom: 20px; width: min(880px, 75%); min-height: 56px; display: grid; grid-template-columns: auto auto auto auto 1fr auto auto auto auto; align-items: center; gap: 10px; transform: translateX(-50%); border-radius: var(--radius-full); background: rgba(255,255,255,0.96); color: var(--color-text-primary); padding: 6px 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }.round-btn { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 50%; }.round-btn.primary { width: 44px; height: 44px; background: var(--color-primary-600); color: white; }.round-btn.ghost { background: transparent; color: var(--color-text-secondary); }.range { width: 100%; accent-color: var(--color-primary-600); }.time { font-family: var(--font-family-mono); color: var(--color-text-muted); font-size: 12px; }
.lesson-ai { min-width: 0; overflow: hidden; background: white; color: var(--color-text-body); border-left: 1px solid var(--color-border-default); display: grid; grid-template-rows: auto 1fr; }.study-room.panelClosed .lesson-ai { border: 0; }.study-tabs { height: 56px; padding: 0 12px; }.script-view, .class-chat, .note-view { overflow: auto; padding: 16px; }.sticky-tools { position: sticky; top: 0; display: flex; justify-content: space-between; background: white; border-bottom: 1px solid var(--color-border-subtle); padding-bottom: 10px; }.sticky-tools button { display: flex; gap: 5px; border: 0; background: transparent; color: var(--color-primary-700); }.reading { border-left: 3px solid var(--color-primary-600); background: var(--color-primary-50); border-radius: 8px; padding: 14px; line-height: 1.75; }.context-bar { display: flex; gap: 6px; border-radius: var(--radius-lg); background: var(--color-primary-50); color: var(--color-primary-700); padding: 8px; font-size: 12px; }.chat-disclaimer { text-align: center; color: var(--color-text-muted); font-size: 11px; margin: 8px 0; }.chat-input.compact { border-radius: var(--radius-lg); }.note-tools { display: flex; gap: 8px; align-items: center; }.note-tools button { border: 1px solid var(--color-border-default); border-radius: 6px; background: white; }.note-tools span { margin-left: auto; color: var(--color-text-muted); }.note-view textarea { width: 100%; min-height: 520px; border: 0; outline: 0; resize: none; font-size: 14px; line-height: 1.75; padding: 16px 0; }.note-view footer { display: flex; align-items: center; gap: 10px; color: var(--color-text-muted); }
.thumb-panel { position: fixed; z-index: var(--z-fixed); left: 0; top: 48px; bottom: 0; width: 200px; background: rgba(10,15,30,0.9); backdrop-filter: blur(12px); padding: 16px; }.thumb-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 14px; }.thumb-grid button { position: relative; height: 48px; border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; background: rgba(255,255,255,0.08); color: white; }.thumb-grid .active { border: 2px solid var(--color-primary-500); }.thumb-grid .learned svg { position: absolute; right: 4px; top: 4px; border-radius: 50%; background: var(--color-success-500); }
.settings-pop { position: fixed; right: 18px; top: 54px; z-index: var(--z-popover); display: grid; gap: 4px; border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 8px; }.settings-pop button { border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); padding: 8px 12px; }.settings-pop .active { background: var(--color-primary-50); color: var(--color-primary-700); }
.complete-modal { position: relative; overflow: hidden; width: 640px; border-radius: 24px; background: white; color: var(--color-text-body); text-align: center; box-shadow: var(--shadow-xl); padding: 40px; }.complete-modal > svg { color: #8B5CF6; }.complete-modal h2 { margin: 10px 0 0; color: var(--color-text-primary); }.done-stats { display: flex; justify-content: center; gap: 24px; border-top: 1px solid var(--color-border-subtle); border-bottom: 1px solid var(--color-border-subtle); margin: 20px 0; padding: 16px; }.ai-summary { display: flex; gap: 8px; border-radius: var(--radius-lg); background: var(--color-ai-light); color: #6D28D9; padding: 12px; text-align: left; }.complete-modal footer { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }.confetti i { position: absolute; bottom: 120px; width: 8px; height: 12px; animation: confetti var(--duration-confetti) var(--ease-out) both; }
.bottom-tabs { position: fixed; left: 0; right: 0; bottom: 0; z-index: var(--z-fixed); height: 64px; display: grid; grid-template-columns: repeat(5, 1fr); border-top: 1px solid var(--color-border-default); background: rgba(255,255,255,0.9); backdrop-filter: blur(12px); }.bottom-tabs button { position: relative; display: grid; justify-items: center; align-content: center; gap: 2px; border: 0; background: transparent; color: var(--color-text-muted); font-size: 11px; }.bottom-tabs button span { display: grid; place-items: center; transition: transform var(--duration-fast) var(--ease-spring), color var(--duration-fast) var(--ease-out); }.bottom-tabs button.active span { transform: scale(1.15); color: var(--color-primary-600); }.bottom-tabs button.active { color: var(--color-primary-600); }.bottom-tabs button i { width: 6px; height: 6px; border-radius: 50%; background: transparent; }.bottom-tabs .active i { background: var(--color-primary-600); }.bottom-tabs .ai span { width: 52px; height: 52px; border-radius: 50%; background: var(--color-ai-gradient); color: white; box-shadow: 0 4px 12px rgba(99,102,241,0.4); transform: translateY(-12px); }.bottom-tabs .ai.active span { transform: translateY(-12px) scale(1.06); }.bottom-tabs .ai { color: var(--color-primary-700); }
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
@keyframes check-bounce { 0% { transform: scale(1); } 45% { transform: scale(1.3); } 100% { transform: scale(1); } }
.segmented { display: inline-flex; width: fit-content; overflow: hidden; border: 1px solid var(--color-border-default); border-radius: var(--radius-full); background: white; padding: 3px; }.segmented button { min-height: 32px; border: 0; border-radius: var(--radius-full); background: transparent; color: var(--color-text-secondary); padding: 0 14px; }.segmented .active { background: var(--color-primary-600); color: white; }
.page-switch-enter-active, .page-switch-leave-active, .fade-slide-enter-active, .fade-slide-leave-active, .popover-enter-active, .popover-leave-active, .modal-pop-enter-active, .modal-pop-leave-active, .drawer-enter-active, .drawer-leave-active, .study-top-enter-active, .study-top-leave-active, .player-pop-enter-active, .player-pop-leave-active, .subtitle-enter-active, .subtitle-leave-active, .thought-roll-enter-active, .thought-roll-leave-active { transition: all var(--duration-base) var(--ease-out); }
.page-switch-enter-from, .page-switch-leave-to, .fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(6px); }
.thought-roll-enter-from, .thought-roll-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.thought-roll-enter-to, .thought-roll-leave-from { opacity: 1; max-height: 160px; }
.popover-enter-from, .popover-leave-to, .modal-pop-enter-from, .modal-pop-leave-to { opacity: 0; transform: translateY(-8px) scale(.98); }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }
.study-top-enter-from, .study-top-leave-to { opacity: 0; transform: translateY(-12px); }
.player-pop-enter-from, .player-pop-leave-to, .subtitle-enter-from, .subtitle-leave-to { opacity: 0; transform: translate(-50%, 8px); }
.slide-next-enter-active, .slide-next-leave-active, .slide-prev-enter-active, .slide-prev-leave-active { transition: all var(--duration-base) var(--ease-out); }
.slide-next-enter-from { opacity: 0; transform: translateX(30px); }.slide-next-leave-to { opacity: 0; transform: translateX(-30px); }.slide-prev-enter-from { opacity: 0; transform: translateX(-30px); }.slide-prev-leave-to { opacity: 0; transform: translateX(30px); }
.search-expand-enter-active, .search-expand-leave-active { transition: all var(--duration-slow) var(--ease-out); }.search-expand-enter-from, .search-expand-leave-to { opacity: 0; transform: scaleX(.94); }
.thumb-panel-enter-active, .thumb-panel-leave-active { transition: transform var(--duration-base) var(--ease-out), opacity var(--duration-base) var(--ease-out); }.thumb-panel-enter-from, .thumb-panel-leave-to { transform: translateX(-100%); opacity: 0; }

/* Course detail study room: keep content, subtitles and controls in separate layers. */
.study-main {
  grid-template-columns: minmax(0, 1fr) 380px;
  height: 100vh;
  min-height: 100vh;
  padding-top: 48px;
}

.slide-stage {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 16px;
  overflow: auto;
  padding: 24px 32px 28px;
}

.slide-card {
  width: min(960px, 100%);
  min-height: 420px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
  border-radius: 18px;
  padding: 44px 52px 48px;
}

.slide-card h1 {
  font-size: clamp(22px, 2.2vw, 30px);
  line-height: 1.35;
  padding-right: 56px;
}

.slide-content {
  flex: 1;
  min-height: 0;
  max-height: calc(100vh - 360px);
  overflow: auto;
  padding-right: 8px;
  color: var(--color-text-body);
  font-size: 17px;
  line-height: 1.75;
}

.subtitle-line {
  position: static;
  z-index: 8;
  width: min(760px, 100%);
  max-width: min(760px, calc(100vw - 96px));
  max-height: 118px;
  overflow: auto;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background: rgba(10, 15, 30, 0.82);
  color: rgba(255, 255, 255, 0.86);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28);
  padding: 12px 18px;
  backdrop-filter: blur(12px);
}

.subtitle-line strong {
  color: #fff;
}

.player-bar {
  position: sticky;
  left: auto;
  bottom: 0;
  z-index: 12;
  justify-self: center;
  width: min(880px, 100%);
  transform: none;
  border-radius: 18px;
}

.lesson-ai {
  height: 100%;
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
}

.script-view,
.class-chat,
.note-view {
  min-height: 0;
  padding: 18px 18px 96px;
}

.class-chat {
  height: 100%;
  overflow: hidden;
  padding-bottom: 18px;
}

.sticky-tools {
  z-index: 2;
  align-items: center;
  margin-bottom: 18px;
  padding: 0 0 12px;
}

.reading {
  overflow: auto;
  border-radius: 14px;
  padding: 18px 20px;
}

.lesson-markdown {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.lesson-markdown :deep(p),
.lesson-markdown :deep(ul),
.lesson-markdown :deep(ol),
.lesson-markdown :deep(blockquote),
.lesson-markdown :deep(pre),
.lesson-markdown :deep(table) {
  margin: 0 0 12px;
}

.lesson-markdown :deep(p:last-child),
.lesson-markdown :deep(ul:last-child),
.lesson-markdown :deep(ol:last-child),
.lesson-markdown :deep(blockquote:last-child),
.lesson-markdown :deep(pre:last-child) {
  margin-bottom: 0;
}

.lesson-markdown :deep(ul),
.lesson-markdown :deep(ol) {
  padding-left: 1.4em;
}

.lesson-markdown :deep(li + li) {
  margin-top: 6px;
}

.lesson-markdown :deep(code) {
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.08);
  padding: 2px 5px;
  font-family: var(--font-family-mono);
  font-size: 0.92em;
}

.lesson-markdown :deep(pre) {
  overflow: auto;
  border-radius: 12px;
  background: #0F172A;
  color: #E2E8F0;
  padding: 14px 16px;
}

.lesson-markdown :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}

.lesson-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.lesson-markdown :deep(th),
.lesson-markdown :deep(td) {
  border: 1px solid var(--color-border-default);
  padding: 8px 10px;
  vertical-align: top;
}

.lesson-markdown :deep(th) {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

.lesson-markdown :deep(.katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 6px 0;
}

.subtitle-line .lesson-markdown :deep(p) {
  margin-bottom: 6px;
}

.subtitle-line .lesson-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.player-pop-enter-from,
.player-pop-leave-to,
.subtitle-enter-from,
.subtitle-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 900px) {
  .home-grid, .course-layout, .tutoring-grid, .knowledge-layout, .wrong-layout, .student-course-grid { grid-template-columns: 1fr; }
  .quick-row, .achievement-row { grid-template-columns: repeat(2, 1fr); }
  .study-main { grid-template-columns: 1fr; }
  .lesson-ai { position: fixed; right: 0; top: 48px; bottom: 0; width: min(380px, 92vw); z-index: var(--z-fixed); }
}

/* Student visual refresh: soft glass, poster cards and immersive learning hub. */
.student-shell {
  --s-primary-50: #EEF2FF;
  --s-primary-100: #E0E7FF;
  --s-primary-400: #818CF8;
  --s-primary-500: #6366F1;
  --s-primary-600: #5A67D8;
  --s-ai-light: linear-gradient(135deg, #E0F2FE 0%, #EDE9FE 100%);
  --s-ai-main: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --s-bg: #F4F6F9;
  --s-card: #FFFFFF;
  --s-glass: rgba(255, 255, 255, 0.76);
  --s-text: #1E293B;
  --s-muted: #64748B;
  --s-hint: #94A3B8;
  --s-border: rgba(226, 232, 240, 0.82);
  --s-radius-sm: 8px;
  --s-radius-md: 16px;
  --s-radius-lg: 24px;
  --s-radius-xl: 32px;
  --s-pill: 999px;
  --s-shadow-card: 0 10px 30px -5px rgba(15, 23, 42, 0.04);
  --s-shadow-float: 0 20px 40px -10px rgba(15, 23, 42, 0.08);
  --s-shadow-glass: 0 8px 32px rgba(30, 41, 59, 0.08);
  min-height: 100vh;
  padding-bottom: 40px;
  background-color: var(--s-bg);
  background-image:
    radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.045) 0%, transparent 44%),
    radial-gradient(circle at 86% 28%, rgba(6, 182, 212, 0.04) 0%, transparent 46%);
  background-attachment: fixed;
  color: var(--s-text);
  font-size: 15px;
  line-height: 1.6;
}

.student-shell button,
.student-shell a,
.student-shell .student-course-card,
.student-shell .panel-card,
.student-shell .quick-tile,
.student-shell .quiz-card,
.student-shell .wrong-card,
.student-shell .home-course,
.student-shell .material-row,
.student-shell .lesson-item {
  transition:
    transform var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    opacity var(--duration-fast) var(--ease-out);
}

.student-shell input[type="number"] {
  appearance: textfield;
}

.student-shell input[type="number"]::-webkit-outer-spin-button,
.student-shell input[type="number"]::-webkit-inner-spin-button {
  margin: 0;
  appearance: none;
}

.student-top {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: grid;
  grid-template-columns: minmax(190px, 1fr) auto minmax(190px, 1fr);
  align-items: center;
  height: 72px;
  padding: 0 40px;
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.62);
  background: var(--s-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: none;
}

.brand {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: var(--s-text);
  font-weight: 800;
  letter-spacing: 0.2px;
}

.brand span {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--s-ai-main);
  color: white;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.28);
}

.brand strong {
  font-size: 18px;
}

.brand:hover {
  transform: translateY(-1px);
}

.student-nav-links {
  justify-self: center;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px;
  border-radius: var(--s-pill);
  background: rgba(241, 245, 249, 0.68);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.72);
}

.student-nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 20px;
  border-radius: var(--s-pill);
  color: var(--s-muted);
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
}

.student-nav-link:hover {
  color: var(--s-text);
  background: rgba(255, 255, 255, 0.58);
}

.student-nav-link.active {
  background: white;
  color: var(--s-primary-600);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

.student-nav-link.ai.active {
  color: #6D28D9;
}

.top-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 16px;
}

.top-icon,
.avatar-btn,
.modal-head button {
  width: 44px;
  height: 44px;
  min-width: 44px;
  padding: 0;
  border-radius: 50%;
  background: white;
  color: var(--s-muted);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.035);
}

.top-icon:hover,
.avatar-btn:hover,
.modal-head button:hover {
  background: var(--s-primary-50);
  color: var(--s-primary-600);
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(99, 102, 241, 0.12);
}

.avatar-btn {
  overflow: hidden;
  flex: 0 0 44px;
}

.avatar-btn img,
.avatar-btn .default-user-avatar {
  position: static;
  display: block;
  width: 100%;
  height: 100%;
  border: 2px solid white;
  border-radius: 50%;
  object-fit: cover;
  background: var(--s-ai-light);
  padding: 0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.top-icon em {
  top: 1px;
  right: 1px;
  min-width: 18px;
  height: 18px;
  border: 2px solid white;
  border-radius: 10px;
  background: #EF4444;
  font-size: 10px;
  line-height: 14px;
}

.global-search {
  height: 72px;
  padding: 0 max(32px, calc((100vw - 1140px) / 2));
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--s-shadow-glass);
}

.global-search input {
  color: var(--s-text);
}

.notice-pop,
.user-pop,
.select-pop,
.dropdown-pop,
.settings-pop {
  z-index: var(--z-popover);
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: var(--s-radius-lg);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--s-shadow-glass);
  backdrop-filter: blur(18px);
}

.user-pop button,
.notice-item {
  border-radius: var(--s-radius-md);
}

.user-pop button:hover,
.notice-item:hover {
  background: var(--s-primary-50);
  color: var(--s-primary-600);
  transform: translateX(2px);
}

.student-main {
  width: min(1140px, 100%);
  max-width: 1140px;
  padding: 40px 32px 80px;
}

.student-page {
  display: grid;
  gap: 32px;
  animation: student-scale-fade 0.5s var(--ease-out);
}

.page-title-row {
  align-items: flex-end;
  margin-bottom: 8px;
}

.page-title-row h1 {
  color: var(--s-text);
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0;
}

.page-title-row p {
  margin-top: 8px;
  color: var(--s-muted);
  font-size: 16px;
}

.page-title-actions {
  gap: 10px;
}

.btn,
.white-pill,
.white-fill,
.link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 24px;
  border-radius: var(--s-pill);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.btn-primary {
  border: 0;
  background: var(--s-primary-600);
  color: white;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.24);
}

.btn-primary:hover {
  background: var(--s-primary-500);
  box-shadow: 0 8px 22px rgba(79, 70, 229, 0.30);
  transform: translateY(-1px);
}

.btn-ai {
  border: 0;
  background: var(--s-ai-main);
  color: white;
  box-shadow: 0 4px 16px rgba(139, 92, 246, 0.26);
}

.btn-ai:hover {
  filter: brightness(1.04);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.34);
  transform: translateY(-1px);
}

.btn-secondary,
.btn-ghost {
  background: var(--s-bg);
  color: var(--s-text);
  border: 1px solid transparent;
}

.btn-secondary:hover,
.btn-ghost:hover {
  background: #E2E8F0;
  box-shadow: none;
}

.btn-sm {
  min-height: 34px;
  padding: 0 14px;
  border-radius: var(--s-pill);
}

.input,
.textarea,
.time-input,
.problem-text,
.answer-input,
.answer-textarea,
.pretty-input,
.code-input,
.select-menu > button,
.dropdown-trigger,
.ask-card form,
.chat-input {
  border: 1px solid transparent;
  border-radius: var(--s-radius-md);
  background: white;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
}

.input,
.time-input {
  height: 48px;
  padding: 0 16px;
}

.textarea,
.problem-text,
.answer-textarea {
  padding: 14px 16px;
}

.pretty-input,
.select-menu > button,
.dropdown-trigger {
  min-height: 44px;
  padding: 0 16px;
}

.input:hover,
.textarea:hover,
.time-input:hover,
.problem-text:hover,
.answer-textarea:hover,
.pretty-input:hover,
.select-menu > button:hover,
.dropdown-trigger:hover {
  border-color: rgba(99, 102, 241, 0.24);
}

.input:focus,
.textarea:focus,
.time-input:focus,
.problem-text:focus,
.answer-textarea:focus,
.pretty-input:focus-within,
.code-input:focus-within,
.ask-card form:focus-within,
.chat-input:focus-within {
  border-color: var(--s-primary-500);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.14);
}

.hello-card {
  min-height: 184px;
  padding: 48px;
  border-radius: var(--s-radius-xl);
  background:
    radial-gradient(circle at 12% 15%, rgba(255, 255, 255, 0.18), transparent 34%),
    radial-gradient(circle at 94% 90%, rgba(139, 92, 246, 0.34), transparent 42%),
    var(--s-primary-600);
  color: white;
  box-shadow: 0 20px 40px -10px rgba(79, 70, 229, 0.30);
}

.hello-card::before,
.hello-card::after {
  display: none;
}

.hello-card > div:first-child {
  gap: 16px;
}

.hello-card > div:first-child > svg {
  width: 42px;
  height: 42px;
  padding: 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(10px);
}

.hello-card h1 {
  font-size: 36px;
  line-height: 1.18;
  font-weight: 800;
  letter-spacing: 0;
}

.hello-card p {
  margin-top: 12px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 16px;
}

.white-pill,
.white-fill {
  border: 1px solid rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.20);
  color: white;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
  backdrop-filter: blur(10px);
}

.white-pill:hover,
.white-fill:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: translateY(-1px);
}

.today-plan {
  min-height: 78px;
  grid-template-columns: auto 1fr auto minmax(120px, 180px) auto;
  border: 0;
  border-radius: var(--s-radius-lg);
  background: white;
  box-shadow: var(--s-shadow-card);
  padding: 18px 22px;
}

.today-plan > svg {
  width: 42px;
  height: 42px;
  padding: 10px;
  border-radius: 16px;
  background: var(--s-primary-50);
  color: var(--s-primary-600);
}

.continue-card {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 24px;
  min-height: 188px;
  padding: 24px;
  border-radius: var(--s-radius-xl);
  background: white;
  box-shadow: var(--s-shadow-card);
}

.continue-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--s-shadow-float);
}

.continue-cover {
  min-height: 140px;
  border-radius: var(--s-radius-md);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
}

.continue-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.08);
  transition: opacity var(--duration-base) var(--ease-out);
}

.continue-card:hover .continue-cover::after {
  opacity: 0;
}

.continue-cover svg {
  width: 48px;
  height: 48px;
  z-index: 1;
  filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.18));
}

.continue-cover span {
  z-index: 1;
  right: 16px;
  bottom: 16px;
  color: var(--s-primary-600);
}

.continue-card section {
  padding: 0;
  align-content: center;
  gap: 12px;
}

.continue-card h2 {
  color: var(--s-text);
  font-size: 22px;
  font-weight: 800;
}

.empty-continue {
  justify-items: start;
}

.home-grid {
  grid-template-columns: 2fr 1fr;
  gap: 32px;
}

.panel-card,
.course-tools,
.student-course-card,
.knowledge-head,
.knowledge-body,
.wrong-hero,
.profile-hero,
.badge-card {
  border: 0;
  border-radius: var(--s-radius-lg);
  background: white;
  box-shadow: var(--s-shadow-card);
  padding: 28px;
}

.panel-card:hover,
.student-course-card:hover,
.quick-tile:hover,
.quiz-card:hover,
.wrong-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--s-shadow-float);
}

.section-head {
  margin-bottom: 22px;
}

.section-head h2 {
  color: var(--s-text);
  font-size: 20px;
  font-weight: 800;
}

.section-head button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--s-pill);
  background: var(--s-primary-50);
  color: var(--s-primary-600);
  padding: 0 14px;
  font-weight: 700;
}

.section-head button:hover {
  background: var(--s-primary-100);
  transform: translateY(-1px);
}

.home-course {
  min-height: 76px;
  border-radius: var(--s-radius-md);
  background: #FBFCFF;
  padding: 14px;
}

.home-course:hover {
  background: white;
  transform: translateX(3px);
}

.home-course > span {
  width: 50px;
  height: 50px;
  border-radius: 16px;
}

.join-dashed,
.image-drop {
  min-height: 72px;
  border: 2px dashed rgba(148, 163, 184, 0.46);
  border-radius: var(--s-radius-lg);
  background: rgba(255, 255, 255, 0.65);
  color: var(--s-primary-600);
  font-weight: 700;
}

.join-dashed:hover,
.image-drop:hover {
  border-color: var(--s-primary-400);
  background: white;
  transform: translateY(-2px);
  box-shadow: var(--s-shadow-card);
}

.rings {
  gap: 18px;
  padding: 20px 0 26px;
}

.ring-wrap {
  width: 82px;
  height: 82px;
}

.ring-block span:not(.ring-wrap) {
  color: var(--s-muted);
  font-weight: 700;
}

.week-check {
  border-top-color: rgba(226, 232, 240, 0.72);
}

.week-check span {
  width: 32px;
  height: 32px;
  border-color: rgba(148, 163, 184, 0.42);
}

.streak {
  width: fit-content;
  border-radius: var(--s-pill);
  background: #FFFBEB;
  padding: 10px 14px;
  color: #B45309;
  font-weight: 800;
}

.home-ai-recommend-card {
  background: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  padding: 32px 40px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
  display: flex;
  gap: 48px;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.home-ai-recommend-card::before {
  content: "";
  position: absolute;
  top: -50%;
  left: -10%;
  width: 50%;
  height: 150%;
  background: radial-gradient(circle, rgba(255,255,255,0.8) 0%, transparent 70%);
  pointer-events: none;
}

.home-ai-rec-left {
  flex: 1;
  position: relative;
  z-index: 1;
}

.home-ai-rec-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.home-ai-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 16px rgba(139, 92, 246, 0.15);
  color: #8B5CF6;
}

.home-ai-recommend-card.is-empty .home-ai-icon-wrap {
  color: #4F46E5;
}

.home-ai-rec-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: #1E293B;
  letter-spacing: 0;
}

.home-ai-rec-content {
  margin: 0 0 24px;
  font-size: 16px;
  color: #64748B;
  line-height: 1.7;
}

.home-ai-rec-content strong {
  color: #1E293B;
  font-weight: 600;
}

.home-ai-rec-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.home-data-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 600;
  color: #6D28D9;
}

.home-refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 0;
  border-radius: 9999px;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #64748B;
}

.home-refresh-btn:hover {
  background: rgba(255, 255, 255, 0.5);
  color: #4F46E5;
}

.home-ai-rec-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 320px;
  position: relative;
  z-index: 1;
}

.home-action-task-card {
  width: 100%;
  background: white;
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 16px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: left;
}

.home-action-task-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(79, 70, 229, 0.1);
  border-color: #E0E7FF;
}

.home-task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.home-task-type {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #94A3B8;
  font-weight: 500;
}

.home-task-title {
  font-size: 16px;
  font-weight: 700;
  color: #1E293B;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-task-arrow {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #EEF2FF;
  color: #4F46E5;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.home-action-task-card:hover .home-task-arrow {
  background: #4F46E5;
  color: white;
  transform: translateX(4px);
}

.home-activity-card {
  background: white;
  border-radius: 24px;
  padding: 32px 40px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
  border: 1px solid #E2E8F0;
}

.home-ac-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
}

.home-ac-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 800;
  color: #1E293B;
}

.home-ac-title svg {
  color: #4F46E5;
}

.home-ac-view-all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: #4F46E5;
  text-decoration: none;
  transition: opacity 0.2s;
}

.home-ac-view-all:hover {
  opacity: 0.8;
}

.home-activity-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
}

.home-activity-list::before {
  content: "";
  position: absolute;
  left: 24px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: #E2E8F0;
  border-radius: 2px;
  z-index: 0;
}

.home-activity-item {
  display: flex;
  gap: 24px;
  position: relative;
  z-index: 1;
}

.home-ac-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 4px solid white;
  box-shadow: 0 4px 8px rgba(0,0,0,0.05);
  flex-shrink: 0;
}

.home-ac-icon-wrapper.ai {
  background: #F5F3FF;
  color: #8B5CF6;
}

.home-ac-icon-wrapper.learning {
  background: #EEF2FF;
  color: #4F46E5;
}

.home-ac-content-wrap {
  flex: 1;
  background: #F4F6F9;
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #E2E8F0;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
  min-width: 0;
}

.home-ac-content-wrap:hover {
  border-color: #E0E7FF;
  background: white;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.home-ac-meta {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 8px;
}

.home-ac-action-name {
  font-size: 15px;
  font-weight: 700;
  color: #1E293B;
}

.home-ac-time {
  font-size: 13px;
  color: #94A3B8;
  font-weight: 500;
  white-space: nowrap;
}

.home-ac-detail {
  font-size: 14px;
  color: #64748B;
  word-break: break-word;
}

.home-ac-detail.quote {
  position: relative;
  padding-left: 12px;
  font-style: italic;
  border-left: 3px solid #E2E8F0;
}

.home-mini-progress-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.home-mp-track {
  flex: 1;
  height: 6px;
  background: #E2E8F0;
  border-radius: 9999px;
  overflow: hidden;
}

.home-mp-fill {
  height: 100%;
  background: #10B981;
  border-radius: 9999px;
}

.home-mp-text {
  font-size: 13px;
  font-weight: 600;
  color: #1E293B;
  width: 44px;
  text-align: right;
}

.home-activity-empty {
  min-height: 120px;
  display: grid;
  place-items: center;
  gap: 8px;
  color: #94A3B8;
  text-align: center;
}

.profile-activity-card {
  gap: 16px;
}

.profile-timeline-item {
  grid-template-columns: 22px minmax(0, 1fr) auto;
  padding: 6px 0;
}

.profile-timeline-item i {
  width: 11px;
  height: 11px;
  background: var(--s-ai-main);
}

.course-tools {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 0;
  background: transparent;
  box-shadow: none;
}

.course-tools .pretty-input {
  width: min(320px, 100%);
}

.course-tools .select-menu {
  width: 180px;
}

.underline-tabs,
.seg-tabs,
.profile-tabs,
.study-tabs {
  width: fit-content;
  display: inline-flex;
  gap: 6px;
  border: 0;
  border-radius: var(--s-pill);
  background: rgba(255, 255, 255, 0.70);
  padding: 6px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.60);
}

.underline-tabs button,
.seg-tabs button,
.profile-tabs button,
.study-tabs button,
.segmented button {
  min-height: 38px;
  border: 0;
  border-radius: var(--s-pill);
  padding: 0 18px;
  color: var(--s-muted);
  font-weight: 700;
}

.underline-tabs .active,
.seg-tabs .active,
.profile-tabs .active,
.study-tabs .active,
.segmented .active {
  background: white;
  color: var(--s-primary-600);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}

.student-course-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
}

.student-course-card {
  overflow: visible;
  padding: 0;
  border-radius: var(--s-radius-xl);
}

.course-art {
  overflow: visible;
  height: 160px;
  aspect-ratio: auto;
  padding: 24px;
  border-radius: var(--s-radius-xl) var(--s-radius-xl) 0 0;
}

.course-art::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 24% 20%, rgba(255, 255, 255, 0.22), transparent 34%);
}

.course-art > svg {
  z-index: 1;
  width: 64px;
  height: 64px;
  padding: 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.20);
  backdrop-filter: blur(10px);
}

.student-course-card:hover .course-art > svg {
  transform: scale(1.08) rotate(-2deg);
}

.course-art span,
.course-art em {
  z-index: 1;
  bottom: auto;
  top: 16px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--s-primary-600);
  font-weight: 800;
}

.course-art span {
  left: 16px;
}

.course-art em {
  right: 64px;
}

.course-art .dropdown-menu {
  z-index: var(--z-popover);
  top: 16px;
  right: 16px;
  bottom: auto;
  width: auto;
}

.course-art .dropdown-pop {
  top: calc(100% + 8px);
  right: 0;
  left: auto;
  z-index: var(--z-popover);
  min-width: 168px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16);
  padding: 8px;
}

.course-art .dropdown-trigger {
  width: 38px;
  height: 38px;
  min-height: 38px;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.56);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(8px);
  color: white;
  padding: 0;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
}

.course-art .dropdown-trigger:hover {
  background: white;
  color: var(--s-primary-600);
  transform: translateY(-1px);
}

.student-course-card section {
  display: grid;
  gap: 12px;
  padding: 24px;
}

.student-course-card h2 {
  font-size: 19px;
  font-weight: 800;
}

.mini-data {
  justify-content: space-between;
  gap: 10px;
  margin: 4px 0 8px;
}

.mini-data span {
  min-height: 30px;
  border-radius: var(--s-pill);
  background: var(--s-bg);
  padding: 0 10px;
}

.course-hero-student {
  min-height: 240px;
  border-radius: var(--s-radius-xl);
  padding: 42px 48px;
  box-shadow: 0 20px 40px -10px rgba(79, 70, 229, 0.24);
}

.course-hero-student h1 {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0;
}

.slide-mini {
  width: 150px;
  height: 110px;
  border-radius: var(--s-radius-md);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.22);
}

.quick-row {
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.quick-tile {
  min-height: 104px;
  border: 0;
  border-radius: var(--s-radius-lg);
  background: white;
  box-shadow: var(--s-shadow-card);
  padding: 20px;
}

.quick-tile span {
  width: 42px;
  height: 42px;
  border-radius: 16px;
  background: var(--s-primary-50);
}

.quick-tile:hover span {
  background: var(--s-primary-600);
  color: white;
}

.course-layout {
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.9fr);
  gap: 32px;
}

.course-layout > section,
.course-layout > aside {
  gap: 24px;
}

.lesson-item {
  min-height: 82px;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  border: 0;
  border-radius: var(--s-radius-md);
  background: #FBFCFF;
  margin-bottom: 10px;
  padding: 12px 14px;
}

.lesson-item b {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: var(--s-primary-50);
}

.lesson-item:hover {
  background: white;
  transform: translateX(4px);
  box-shadow: var(--s-shadow-card);
}

.lesson-item.current {
  background: var(--s-primary-50);
  box-shadow: inset 4px 0 0 var(--s-primary-600);
}

.lesson-item svg:last-child {
  color: var(--s-primary-600);
}

.material-row {
  min-height: 70px;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  border: 0;
  border-radius: var(--s-radius-md);
  background: #FBFCFF;
  margin-bottom: 10px;
  padding: 12px 14px;
}

.material-row:hover {
  background: white;
  transform: translateX(4px);
  box-shadow: var(--s-shadow-card);
}

.file-badge {
  width: 42px;
  height: 42px;
  border-radius: 16px;
  background: var(--s-ai-main);
}

.data-grid,
.achievement-row {
  gap: 14px;
}

.mini-metric {
  min-height: 86px;
  border-radius: var(--s-radius-md);
  background: var(--s-bg);
  padding: 16px;
}

.mini-metric strong {
  font-size: 26px;
  font-weight: 800;
}

.ask-card {
  border: 0;
  border-radius: var(--s-radius-lg);
  background: var(--s-ai-light);
  box-shadow: var(--s-shadow-card);
  padding: 28px;
}

.ask-card > svg {
  width: 44px;
  height: 44px;
  padding: 10px;
  border-radius: 16px;
  background: white;
  color: #8B5CF6;
}

.ask-card button:not(.quick-tags button),
.send-btn {
  width: 42px;
  height: 42px;
  background: var(--s-primary-600);
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.22);
}

.send-btn:hover:not(:disabled) {
  background: var(--s-primary-500);
  transform: scale(1.05);
}

.quick-tags {
  gap: 12px;
}

.quick-tags button,
.practice-cta button {
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: var(--s-pill);
  background: rgba(255, 255, 255, 0.78);
  color: var(--s-muted);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.035);
  font-weight: 700;
}

.quick-tags button:hover,
.practice-cta button:hover {
  background: white;
  color: var(--s-primary-600);
  transform: translateY(-2px);
  box-shadow: var(--s-shadow-card);
}

.tutoring-grid {
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 32px;
}

.tutor-input,
.guide-card,
.history-strip {
  gap: 18px;
}

.image-drop {
  min-height: 240px;
}

.knowledge-box {
  border-radius: var(--s-radius-md);
  background: var(--s-ai-light);
}

.guide-step {
  border: 0;
  border-radius: var(--s-radius-md);
  background: #FBFCFF;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.72);
}

.guide-step > button {
  border-radius: var(--s-radius-md);
  background: transparent;
  padding: 16px;
}

.guide-step:hover {
  box-shadow: var(--s-shadow-card);
}

.history-strip div {
  gap: 14px;
}

.history-strip button {
  min-height: 92px;
  border: 0;
  border-radius: var(--s-radius-md);
  background: #FBFCFF;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.72);
}

.history-strip button:hover {
  background: white;
  transform: translateY(-2px);
  box-shadow: var(--s-shadow-card);
}

.knowledge-layout,
.wrong-layout {
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 32px;
}

.knowledge-tree,
.wrong-tree {
  gap: 10px;
  border: 0;
  border-radius: var(--s-radius-lg);
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.knowledge-tree .pretty-input {
  margin-bottom: 10px;
}

.knowledge-tree button,
.wrong-tree button {
  min-height: 44px;
  border-radius: var(--s-pill);
  color: var(--s-muted);
  font-weight: 700;
  padding: 0 16px;
}

.knowledge-tree button:hover,
.wrong-tree button:hover,
.wrong-tree button.active {
  background: white;
  color: var(--s-primary-600);
  box-shadow: var(--s-shadow-card);
  transform: translateX(2px);
}

.wrong-tree strong {
  margin: 22px 16px 4px;
  color: var(--s-hint);
  font-size: 12px;
  letter-spacing: 1px;
}

.knowledge-head {
  display: grid;
  gap: 14px;
}

.knowledge-head h1 {
  font-size: 30px;
  font-weight: 800;
}

.knowledge-body {
  gap: 22px;
}

.knowledge-block h3 {
  font-size: 18px;
  font-weight: 800;
}

.knowledge-block div {
  border-left: 0;
  border-radius: var(--s-radius-md);
  background: var(--s-primary-50);
}

.practice-cta {
  border-radius: var(--s-radius-md);
  background: var(--s-ai-light);
}

.quiz-list,
.wrong-list {
  gap: 16px;
}

.quiz-card,
.wrong-card {
  border: 0;
  border-radius: var(--s-radius-lg);
  background: white;
  box-shadow: var(--s-shadow-card);
  padding: 22px;
}

.quiz-card::before,
.wrong-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 5px;
  border-radius: 0 6px 6px 0;
  background: var(--s-ai-main);
}

.quiz-card h2,
.wrong-card h2 {
  font-size: 19px;
  font-weight: 800;
}

.quiz-modern-page {
  --quiz-primary-50: #EEF2FF;
  --quiz-primary-100: #E0E7FF;
  --quiz-primary-500: #6366F1;
  --quiz-primary-600: #5A67D8;
  --quiz-ai-main: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --quiz-ai-light: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  --quiz-bg: #F4F6F9;
  --quiz-surface: #FFFFFF;
  --quiz-muted: #F8FAFC;
  --quiz-border: #E2E8F0;
  --quiz-text: #1E293B;
  --quiz-secondary: #64748B;
  --quiz-hint: #94A3B8;
  --quiz-radius-md: 12px;
  --quiz-radius-lg: 16px;
  --quiz-radius-xl: 24px;
  --quiz-pill: 9999px;
  --quiz-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --quiz-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.04);
  --quiz-shadow-float: 0 20px 40px -10px rgba(79, 70, 229, 0.15);
  --quiz-shadow-focus: 0 0 0 4px rgba(99, 102, 241, 0.15);
  display: grid;
  gap: 32px;
}

.quiz-modern-page button {
  font-family: inherit;
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out),
    filter var(--duration-fast) var(--ease-out);
}

.quiz-modern-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.quiz-modern-title h1 {
  margin: 0 0 8px;
  color: var(--quiz-text);
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0;
}

.quiz-modern-title p {
  margin: 0;
  color: var(--quiz-secondary);
  font-size: 15px;
}

.quiz-modern-page .course-select .select-menu > button,
.quiz-modern-page .select-menu-empty {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--quiz-border);
  border-radius: var(--quiz-pill);
  background: white;
  color: var(--quiz-text);
  box-shadow: var(--quiz-shadow-sm);
  padding: 0 20px;
  font-size: 15px;
  font-weight: 700;
}

.quiz-modern-page .course-select .select-menu > button:hover,
.quiz-modern-page .select-menu-empty:hover {
  border-color: var(--quiz-primary-500);
  box-shadow: var(--quiz-shadow-focus);
}

.quiz-modern-tabs {
  display: flex;
  gap: 12px;
}

.quiz-modern-tabs button {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: transparent;
  color: var(--quiz-secondary);
  padding: 0 24px;
  font-size: 15px;
  font-weight: 700;
}

.quiz-modern-tabs button:hover {
  background: rgba(255, 255, 255, 0.5);
}

.quiz-modern-tabs button.active {
  background: white;
  color: var(--quiz-primary-600);
  box-shadow: var(--quiz-shadow-sm);
}

.quiz-modern-list {
  gap: 16px;
}

.practice-modern-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 32px;
}

.practice-modern-card {
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--quiz-radius-xl);
  background: white;
  box-shadow: var(--quiz-shadow-card);
  padding: 32px;
}

.practice-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.practice-card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--quiz-ai-light);
  color: #8B5CF6;
}

.practice-card-header h2 {
  margin: 0;
  color: var(--quiz-text);
  font-size: 20px;
  font-weight: 800;
}

.practice-config-section {
  margin-bottom: 32px;
}

.practice-config-label {
  display: block;
  margin-bottom: 16px;
  color: var(--quiz-text);
  font-size: 14px;
  font-weight: 700;
}

.practice-chapter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.practice-chip {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  border: 1px solid transparent;
  border-radius: var(--quiz-pill);
  background: var(--quiz-muted);
  color: var(--quiz-secondary);
  padding: 0 20px;
  font-size: 14px;
  font-weight: 600;
}

.practice-chip:hover {
  background: #E2E8F0;
}

.practice-chip.active {
  border-color: var(--quiz-primary-500);
  background: var(--quiz-primary-50);
  color: var(--quiz-primary-600);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.10);
}

.practice-settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: var(--quiz-pill);
  background: var(--quiz-muted);
  padding: 8px 16px 8px 8px;
}

.practice-segmented-control {
  display: flex;
  gap: 4px;
}

.practice-segmented-control button {
  min-height: 36px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: transparent;
  color: var(--quiz-secondary);
  padding: 0 24px;
  font-size: 14px;
  font-weight: 600;
}

.practice-segmented-control button.active {
  background: white;
  color: var(--quiz-primary-600);
  box-shadow: var(--quiz-shadow-sm);
}

.practice-switch-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  color: var(--quiz-text);
}

.practice-switch-wrapper strong {
  font-size: 14px;
  font-weight: 700;
}

.practice-switch {
  position: relative;
  width: 44px;
  height: 24px;
  flex: 0 0 auto;
  border-radius: var(--quiz-pill);
  background: var(--quiz-border);
  transition: background var(--duration-base) var(--ease-out);
}

.practice-switch::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  box-shadow: var(--quiz-shadow-sm);
  transition: transform var(--duration-base) var(--ease-out);
}

.practice-switch-wrapper.active .practice-switch {
  background: var(--quiz-primary-600);
}

.practice-switch-wrapper.active .practice-switch::after {
  transform: translateX(20px);
}

.practice-generate-btn {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 40px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: var(--quiz-ai-main);
  color: white;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.30);
  font-size: 16px;
  font-weight: 800;
}

.practice-generate-btn:hover {
  filter: brightness(1.05);
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(139, 92, 246, 0.40);
}

.practice-generate-hint {
  margin: 12px 0 0;
  color: var(--quiz-hint);
  text-align: center;
  font-size: 13px;
}

.practice-feature-card {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 32px;
  border: 1px solid #FEF08A;
  border-radius: var(--quiz-radius-lg);
  background: linear-gradient(to right, #FFF7ED, #FEFCE8);
  padding: 24px;
  text-align: left;
}

.practice-feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(245, 158, 11, 0.14);
}

.practice-feature-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  border-radius: 12px;
  background: white;
  color: #F59E0B;
  box-shadow: var(--quiz-shadow-sm);
}

.practice-feature-card h2 {
  margin: 0 0 4px;
  color: #B45309;
  font-size: 18px;
  font-weight: 800;
}

.practice-feature-card p {
  margin: 0;
  color: #A16207;
  font-size: 13px;
}

.practice-feature-card > span {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--quiz-pill);
  background: #F59E0B;
  color: white;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.20);
  padding: 0 24px;
  font-weight: 700;
}

.practice-history-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--quiz-text);
  font-size: 15px;
  font-weight: 800;
}

.practice-history-title svg {
  color: var(--quiz-primary-500);
}

.practice-history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.practice-history-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--quiz-border);
  border-radius: var(--quiz-radius-lg);
  background: white;
  padding: 16px;
  text-align: left;
}

.practice-history-item:hover {
  border-color: #CBD5E1;
  background: var(--quiz-muted);
  transform: translateY(-1px);
}

.practice-history-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 16px;
}

.practice-history-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 10px;
  background: var(--quiz-primary-50);
  color: var(--quiz-primary-600);
}

.practice-history-left strong {
  display: block;
  max-width: 260px;
  overflow: hidden;
  color: var(--quiz-text);
  font-size: 15px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.practice-history-left small {
  color: var(--quiz-hint);
  font-size: 12px;
}

.practice-history-item em {
  flex: 0 0 auto;
  color: #10B981;
  font-size: 16px;
  font-style: normal;
  font-weight: 900;
}

.wrong-hero {
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  background: transparent;
  box-shadow: none;
  padding: 0;
  color: var(--s-text);
}

.wrong-hero > svg {
  display: none;
}

.wrong-hero div {
  position: relative;
  min-height: 132px;
  overflow: hidden;
  border-radius: var(--s-radius-lg);
  background: white;
  box-shadow: var(--s-shadow-card);
  padding: 30px 32px;
}

.wrong-hero div::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  background: #EF4444;
}

.wrong-hero div:nth-of-type(2)::before {
  background: #F59E0B;
}

.wrong-hero div:nth-of-type(3)::before {
  background: #10B981;
}

.wrong-hero strong {
  color: var(--s-text);
  font-size: 48px;
  line-height: 1;
  font-weight: 800;
}

.wrong-hero span {
  color: var(--s-muted);
  font-weight: 700;
}

.wrong-tools {
  grid-template-columns: minmax(0, 1fr) 160px;
  gap: 12px;
  margin-bottom: 18px;
}

.student-plan-page {
  --plan-primary-50: #EEF2FF;
  --plan-primary-100: #E0E7FF;
  --plan-primary-500: #6366F1;
  --plan-primary-600: #5A67D8;
  --plan-ai-main: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --plan-ai-light: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  --plan-success-50: #ECFDF5;
  --plan-success-500: #10B981;
  --plan-warning-500: #F59E0B;
  --plan-bg: #F4F6F9;
  --plan-card: #FFFFFF;
  --plan-muted-bg: #F8FAFC;
  --plan-border-light: #F1F5F9;
  --plan-border: #E2E8F0;
  --plan-text: #1E293B;
  --plan-secondary: #64748B;
  --plan-hint: #94A3B8;
  --plan-radius-sm: 8px;
  --plan-radius-md: 12px;
  --plan-radius-lg: 16px;
  --plan-radius-xl: 24px;
  --plan-pill: 9999px;
  --plan-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --plan-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.04);
  --plan-shadow-focus: 0 0 0 4px rgba(79, 70, 229, 0.15);
  width: 100%;
  color: var(--plan-text);
}

.student-plan-page button,
.student-plan-page input {
  font-family: inherit;
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.student-plan-page .plan-banner {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  min-height: 164px;
  margin-bottom: 32px;
  border-radius: var(--plan-radius-xl);
  background: linear-gradient(135deg, #4F46E5 0%, #8B5CF6 100%);
  color: white;
  box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.3);
  padding: 40px 48px;
}

.student-plan-page .plan-banner::after {
  content: "";
  position: absolute;
  right: -50px;
  top: -100px;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
  pointer-events: none;
}

.student-plan-page .banner-left {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 20px;
}

.student-plan-page .banner-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  background: rgba(255,255,255,0.2);
  backdrop-filter: blur(10px);
}

.student-plan-page .banner-title {
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0;
}

.student-plan-page .banner-stats {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 48px;
}

.student-plan-page .b-stat-item {
  text-align: center;
}

.student-plan-page .b-stat-item h2 {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin: 0 0 4px;
  font-size: 36px;
  line-height: 1;
  font-weight: 800;
}

.student-plan-page .b-stat-item h2 svg {
  color: #FDE047;
  fill: #FDE047;
}

.student-plan-page .b-stat-item span {
  font-size: 14px;
  font-weight: 500;
  opacity: 0.9;
}

.student-plan-page .plan-layout {
  display: grid;
  grid-template-columns: 1.8fr 1fr;
  gap: 32px;
  align-items: start;
}

.student-plan-page .main-col,
.student-plan-page .side-col {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.student-plan-page .card {
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: var(--plan-radius-xl);
  background: var(--plan-card);
  box-shadow: var(--plan-shadow-card);
  padding: 36px;
}

.student-plan-page .card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
}

.student-plan-page .card-header.compact {
  margin-bottom: 24px;
}

.student-plan-page .card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--plan-text);
  font-size: 20px;
  font-weight: 800;
}

.student-plan-page .card-title svg {
  color: var(--plan-primary-600);
}

.student-plan-page .achievement-title svg {
  color: var(--plan-warning-500);
}

.student-plan-page .card-subtitle {
  color: var(--plan-secondary);
  font-size: 14px;
  font-weight: 600;
}

.student-plan-page .calendar-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.student-plan-page .cal-month {
  color: var(--plan-text);
  font-size: 18px;
  font-weight: 800;
}

.student-plan-page .cal-arrows {
  display: flex;
  gap: 8px;
}

.student-plan-page .cal-arr-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--plan-muted-bg);
  color: var(--plan-secondary);
}

.student-plan-page .cal-arr-btn:hover {
  background: var(--plan-border);
  color: var(--plan-text);
}

.student-plan-page .cal-weekdays,
.student-plan-page .cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
}

.student-plan-page .cal-weekdays {
  gap: 8px;
  margin-bottom: 12px;
}

.student-plan-page .cal-grid {
  grid-auto-rows: 44px;
  gap: 12px 8px;
}

.student-plan-page .cal-header-day {
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--plan-hint);
  font-size: 14px;
  font-weight: 600;
}

.student-plan-page .cal-day-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
}

.student-plan-page .cal-day {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--plan-secondary);
  font-size: 16px;
  font-weight: 500;
}

.student-plan-page .cal-day:hover:not(:disabled) {
  background: var(--plan-muted-bg);
}

.student-plan-page .cal-day.empty {
  color: transparent;
  pointer-events: none;
}

.student-plan-page .cal-day.checked {
  background: var(--plan-success-50);
  color: var(--plan-success-500);
  font-weight: 700;
}

.student-plan-page .cal-day.today {
  border: 2px solid var(--plan-primary-500);
  color: var(--plan-primary-600);
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
}

.student-plan-page .cal-day.today.checked {
  border-color: var(--plan-primary-500);
  background: var(--plan-primary-500);
  color: white;
}

.student-plan-page .empty-task-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0 16px;
  text-align: center;
}

.student-plan-page .ai-sparkle-bg {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  background: var(--plan-ai-light);
  color: #8B5CF6;
  box-shadow: 0 12px 24px rgba(139, 92, 246, 0.15);
  margin-bottom: 24px;
}

.student-plan-page .empty-task-state h3 {
  margin: 0 0 8px;
  color: var(--plan-text);
  font-size: 22px;
  font-weight: 800;
}

.student-plan-page .empty-task-state p {
  max-width: 520px;
  margin: 0 0 32px;
  color: var(--plan-secondary);
  font-size: 15px;
}

.student-plan-page .ai-prompt-bar {
  width: 100%;
  max-width: 540px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--plan-border);
  border-radius: var(--plan-pill);
  background: var(--plan-card);
  box-shadow: var(--plan-shadow-sm);
  padding: 6px 6px 6px 20px;
}

.student-plan-page .ai-prompt-bar:focus-within {
  border-color: var(--plan-primary-500);
  box-shadow: 0 12px 32px rgba(79, 70, 229, 0.1), var(--plan-shadow-focus);
  transform: translateY(-2px);
}

.student-plan-page .ai-prompt-bar input {
  flex: 1;
  min-width: 0;
  height: 44px;
  border: 0;
  background: transparent;
  color: var(--plan-text);
  box-shadow: none;
  padding: 0;
  font-size: 15px;
}

.student-plan-page .ai-prompt-bar input::placeholder {
  color: var(--plan-hint);
}

.student-plan-page .btn-ai-gen {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--plan-pill);
  background: var(--plan-ai-main);
  color: white;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
  padding: 0 24px;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
}

.student-plan-page .btn-ai-gen:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: scale(1.02);
}

.student-plan-page .plan-task-list {
  display: grid;
  gap: 14px;
}

.student-plan-page .plan-task-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-height: 68px;
  border: 1px solid var(--plan-border-light);
  border-radius: var(--plan-radius-lg);
  background: var(--plan-muted-bg);
  padding: 12px 14px;
}

.student-plan-page .plan-task-row:hover {
  border-color: var(--plan-primary-100);
  background: white;
  box-shadow: var(--plan-shadow-sm);
  transform: translateY(-1px);
}

.student-plan-page .plan-task-check {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: 1px solid var(--plan-border);
  border-radius: 50%;
  background: white;
  color: var(--plan-success-500);
}

.student-plan-page .plan-task-row.done .plan-task-check {
  border-color: var(--plan-success-500);
  background: var(--plan-success-500);
  color: white;
}

.student-plan-page .plan-task-body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.student-plan-page .plan-task-body strong {
  overflow: hidden;
  color: var(--plan-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.student-plan-page .plan-task-body small {
  color: var(--plan-hint);
}

.student-plan-page .plan-task-row.done .plan-task-body strong {
  color: var(--plan-hint);
  text-decoration: line-through;
}

.student-plan-page .plan-task-tag {
  border-radius: var(--plan-pill);
  background: white;
  color: var(--plan-secondary);
  padding: 5px 12px;
  font-size: 13px;
  font-weight: 700;
}

.student-plan-page .plan-task-row.done .plan-task-tag {
  background: var(--plan-success-50);
  color: var(--plan-success-500);
}

.student-plan-page .mini-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 140px;
  border-bottom: 1px solid var(--plan-border);
  margin-bottom: 20px;
  padding-bottom: 12px;
}

.student-plan-page .bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.student-plan-page .bar-track {
  width: 100%;
  max-width: 20px;
  height: 100%;
  display: flex;
  align-items: flex-end;
  border-radius: 6px;
  background: var(--plan-muted-bg);
}

.student-plan-page .bar-fill {
  width: 100%;
  border-radius: 6px;
  background: linear-gradient(to top, #818CF8, #4F46E5);
  transition: height 0.5s ease;
}

.student-plan-page .bar-label {
  color: var(--plan-hint);
  font-size: 13px;
  font-weight: 500;
}

.student-plan-page .total-hours {
  display: flex;
  align-items: baseline;
  gap: 4px;
  color: var(--plan-text);
  font-size: 16px;
  font-weight: 700;
}

.student-plan-page .total-hours span {
  color: var(--plan-primary-600);
  font-size: 24px;
  line-height: 1;
}

.student-plan-page .badges-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.student-plan-page .badge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border: 2px dashed var(--plan-border);
  border-radius: var(--plan-radius-lg);
  background: var(--plan-muted-bg);
  color: var(--plan-hint);
  padding: 24px 0;
}

.student-plan-page .badge-item.unlocked {
  border: 1px solid #FDE68A;
  border-style: solid;
  background: linear-gradient(to bottom right, #FFFBEB, #FEF3C7);
  color: #D97706;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.1);
}

.student-plan-page .badge-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.student-plan-page .badge-name {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
}

.profile-page {
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
}

.profile-pc-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}

.profile-side,
.profile-main-card {
  display: grid;
  gap: 24px;
}

.profile-identity-card,
.profile-main-card {
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: var(--s-radius-xl);
  background: white;
  box-shadow: var(--s-shadow-card);
}

.profile-main-card {
  padding: 28px;
}

.profile-cover {
  position: relative;
  height: 180px;
  margin-bottom: 82px;
  border-radius: var(--s-radius-xl) var(--s-radius-xl) 0 0;
  background:
    radial-gradient(circle at 18% 12%, rgba(255, 255, 255, 0.28), transparent 30%),
    linear-gradient(135deg, #EEF2FF 0%, #E0F2FE 46%, #EDE9FE 100%);
  box-shadow: none;
}

.profile-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.08), rgba(99, 102, 241, 0));
}

.big-avatar {
  position: absolute;
  left: 50%;
  bottom: -68px;
  z-index: 1;
  width: 136px;
  height: 136px;
  transform: translateX(-50%);
  overflow: visible;
  border: 6px solid white;
  border-radius: 50%;
  background: white;
  color: var(--s-primary-600);
  box-shadow: var(--s-shadow-float);
}

.big-avatar > img,
.big-avatar > .default-user-avatar {
  position: static;
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  background: transparent;
  padding: 0;
}

.big-avatar .camera-badge {
  position: absolute;
  right: 4px;
  bottom: 8px;
  width: 36px;
  height: 36px;
  border: 3px solid white;
  border-radius: 50%;
  background: var(--s-primary-600);
  color: white;
  padding: 8px;
}

.profile-header-info {
  display: grid;
  gap: 18px;
  padding: 0 28px 28px;
  text-align: center;
}

.profile-header-info h1 {
  margin: 0 0 8px;
  color: var(--s-text);
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
}

.profile-header-info p {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 4px 6px 0;
  color: var(--s-muted);
  word-break: normal;
  overflow-wrap: anywhere;
}

.profile-header-info aside {
  display: grid;
  justify-items: center;
  gap: 4px;
  border-radius: 18px;
  background: var(--s-bg);
  padding: 18px;
  text-align: center;
}

.profile-header-info aside strong {
  display: block;
  color: var(--s-primary-600);
  font-size: 36px;
  line-height: 1;
  font-weight: 800;
}

.profile-header-info aside span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  color: var(--s-muted);
  font-weight: 800;
}

.profile-tabs {
  width: fit-content;
  align-self: center;
  justify-self: center;
  margin: 4px 0 2px;
  border: 0;
  border-radius: var(--s-pill);
  background: var(--s-bg);
  padding: 6px;
}

.profile-tabs button {
  min-height: 38px;
  border: 0;
  border-radius: var(--s-pill);
  padding: 0 18px;
}

.profile-tabs .active {
  background: white;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

.badge-card {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.badge-card .badges {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.badges span {
  min-width: 0;
  min-height: 92px;
  border: 0;
  border-radius: 18px;
  background: #FFFBEB;
  color: #B45309;
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.20);
  font-weight: 800;
}

.badges .locked {
  background: var(--s-bg);
}

.profile-form {
  display: grid;
  gap: 20px;
  border-color: rgba(226, 232, 240, 0.82);
  box-shadow: none;
  padding: 24px;
}

.profile-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.profile-form-grid .wide {
  grid-column: 1 / -1;
}

.profile-form footer {
  display: flex;
  justify-content: flex-end;
}

.profile-form .password-field {
  min-height: 48px;
  border-radius: var(--s-radius-md);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
}

.profile-form label {
  gap: 8px;
  color: var(--s-text);
  font-weight: 800;
}

.profile-form .textarea {
  min-height: 160px;
}

.profile-records {
  box-shadow: none;
}

.notice-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.notice-settings-grid .toggle-line {
  min-height: 52px;
  border: 1px solid var(--s-border);
  border-radius: 14px;
  background: var(--s-bg);
  padding: 0 14px;
}

.modal-mask {
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(8px);
}

.join-modal,
.complete-modal {
  border-radius: var(--s-radius-lg);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.22);
  padding: 28px;
}

.modal-head {
  margin-bottom: 20px;
}

.code-input {
  height: 58px;
}

.preview-course {
  border: 0;
  border-radius: var(--s-radius-md);
  background: var(--s-bg);
}

.hint-line {
  border-radius: var(--s-radius-md);
}

.bottom-tabs {
  display: none;
}

.practice-chip:focus-visible,
.practice-segmented-control button:focus-visible,
.practice-switch-wrapper:focus-visible,
.practice-generate-btn:focus-visible,
.practice-feature-card:focus-visible,
.practice-history-item:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

.practice-segmented-control button:hover:not(.active):not(:disabled),
.practice-switch-wrapper:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.72);
  color: var(--quiz-primary-600);
}

.practice-generate-btn:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(139, 92, 246, 0.40);
}

.practice-generate-btn:active:not(:disabled),
.practice-feature-card:active:not(:disabled),
.practice-history-item:active:not(:disabled) {
  transform: scale(0.98);
}

.practice-generate-btn:disabled,
.practice-feature-card:disabled,
.practice-chip:disabled,
.practice-segmented-control button:disabled,
.practice-switch-wrapper:disabled,
.practice-history-item:disabled {
  cursor: not-allowed;
  transform: none;
  filter: none;
  box-shadow: none;
}

.practice-generate-btn:disabled,
.practice-feature-card:disabled {
  opacity: 0.64;
}

.practice-feature-card:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(245, 158, 11, 0.14);
}

.practice-feature-card:disabled > span {
  background: #CBD5E1;
  color: white;
  box-shadow: none;
}

.practice-history-item:hover:not(:disabled) {
  border-color: #CBD5E1;
  background: var(--quiz-muted);
  transform: translateY(-1px);
}

.exam-answer-page {
  --exam-primary-50: #EEF2FF;
  --exam-primary-100: #E0E7FF;
  --exam-primary-400: #818CF8;
  --exam-primary-500: #6366F1;
  --exam-primary-600: #4F46E5;
  --exam-success-50: #ECFDF5;
  --exam-success-500: #10B981;
  --exam-warning-50: #FFFBEB;
  --exam-warning-500: #F59E0B;
  --exam-warning-700: #B45309;
  --exam-bg-page: #F4F6F9;
  --exam-bg-card: #FFFFFF;
  --exam-border-light: #F1F5F9;
  --exam-border-default: #E2E8F0;
  --exam-border-strong: #CBD5E1;
  --exam-text-main: #1E293B;
  --exam-text-sec: #64748B;
  --exam-text-hint: #94A3B8;
  --exam-radius-sm: 8px;
  --exam-radius-md: 12px;
  --exam-radius-lg: 16px;
  --exam-radius-xl: 24px;
  --exam-radius-pill: 9999px;
  --exam-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --exam-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.05);
  --exam-shadow-focus: 0 0 0 4px rgba(79, 70, 229, 0.15);
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  background: var(--exam-bg-page);
  color: var(--exam-text-main);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

.exam-answer-page *,
.exam-answer-page *::before,
.exam-answer-page *::after {
  box-sizing: border-box;
}

.exam-answer-page svg {
  display: block;
  flex-shrink: 0;
}

.exam-answer-page button {
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  outline: 0;
  transition: all 0.2s ease;
}

.exam-answer-page button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

.exam-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--exam-bg-page);
}

.exam-header {
  position: relative;
  z-index: 10;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  border-bottom: 1px solid var(--exam-border-default);
  background: var(--exam-bg-card);
  box-shadow: var(--exam-shadow-sm);
  padding: 0 32px;
}

.exam-exit-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--exam-radius-pill);
  color: var(--exam-text-sec);
  padding: 8px 16px 8px 8px;
  font-size: 14px;
  font-weight: 700;
}

.exam-exit-btn:hover {
  background: var(--exam-bg-page);
  color: var(--exam-text-main);
}

.exam-title {
  position: absolute;
  left: 50%;
  max-width: min(560px, calc(100vw - 360px));
  overflow: hidden;
  transform: translateX(-50%);
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exam-answer-page .timer-widget {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--exam-primary-100);
  border-radius: var(--exam-radius-pill);
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
  padding: 6px 16px;
}

.exam-answer-page .timer-text {
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--exam-primary-600);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1px;
}

.exam-container {
  flex: 1;
  display: flex;
  gap: 24px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  overflow-y: auto;
  padding: 24px 32px 96px;
}

.exam-nav-sidebar {
  width: 280px;
  flex: 0 0 280px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-nav-card {
  border: 1px solid white;
  border-radius: var(--exam-radius-xl);
  background: var(--exam-bg-card);
  box-shadow: var(--exam-shadow-card);
  padding: 24px;
}

.exam-nav-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--exam-border-light);
  padding-bottom: 16px;
}

.exam-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.exam-stat-val {
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 800;
  line-height: 1;
}

.exam-stat-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--exam-text-hint);
  font-size: 12px;
}

.exam-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.exam-dot-answered {
  background: var(--exam-primary-500);
}

.exam-dot-marked {
  background: var(--exam-warning-500);
}

.exam-dot-unanswered {
  border: 2px solid var(--exam-border-strong);
}

.exam-q-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.exam-q-btn {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-sm);
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 700;
}

.exam-q-btn:hover {
  border-color: var(--exam-primary-400);
  color: var(--exam-primary-600);
}

.exam-q-btn.answered {
  border-color: var(--exam-primary-100);
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
}

.exam-q-btn.current {
  border: 2px solid var(--exam-primary-600);
  background: white;
  color: var(--exam-primary-600);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.20);
}

.exam-q-btn.marked::after {
  content: "";
  position: absolute;
  top: -4px;
  right: -4px;
  width: 10px;
  height: 10px;
  border: 2px solid white;
  border-radius: 50%;
  background: var(--exam-warning-500);
}

.exam-question-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.exam-q-card {
  flex: 1;
  border: 1px solid white;
  border-radius: var(--exam-radius-xl);
  background: var(--exam-bg-card);
  box-shadow: var(--exam-shadow-card);
  padding: 40px;
}

.exam-q-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.exam-q-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.exam-q-number {
  margin-right: 8px;
  color: var(--exam-text-main);
  font-size: 16px;
  font-weight: 900;
}

.exam-tag {
  border-radius: var(--exam-radius-pill);
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 700;
}

.exam-tag-type {
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
}

.exam-tag-diff {
  border: 1px solid var(--exam-border-default);
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
}

.exam-mark-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-pill);
  background: white;
  color: var(--exam-text-sec);
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 700;
}

.exam-mark-btn:hover,
.exam-mark-btn.is-marked {
  border-color: #FDE68A;
  background: var(--exam-warning-50);
  color: var(--exam-warning-700);
}

.exam-mark-btn.is-marked svg {
  fill: var(--exam-warning-500);
  color: var(--exam-warning-500);
}

.exam-q-stem {
  margin-bottom: 32px;
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 700;
  line-height: 1.6;
  letter-spacing: 0.3px;
}

.exam-options-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-opt-label {
  position: relative;
  display: block;
  cursor: pointer;
}

.exam-opt-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}

.exam-opt-card {
  display: flex;
  align-items: center;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: var(--exam-bg-card);
  padding: 16px 20px;
  transition: all 0.2s ease;
}

.exam-opt-label:hover .exam-opt-card {
  border-color: var(--exam-primary-400);
  background: var(--exam-bg-page);
}

.exam-opt-letter {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 32px;
  margin-right: 16px;
  border: 1px solid var(--exam-border-default);
  border-radius: 50%;
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 800;
  transition: all 0.2s;
}

.exam-opt-text {
  flex: 1;
  color: var(--exam-text-main);
  font-size: 15px;
  line-height: 1.5;
}

.exam-opt-input:focus-visible + .exam-opt-card,
.exam-q-btn:focus-visible,
.exam-mark-btn:focus-visible,
.exam-btn:focus-visible,
.exam-exit-btn:focus-visible,
.exam-analysis-trigger:focus-visible {
  outline: 0;
  box-shadow: var(--exam-shadow-focus);
}

.exam-opt-input:checked + .exam-opt-card {
  border-color: var(--exam-primary-500);
  background: var(--exam-primary-50);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.10);
}

.exam-opt-input:checked + .exam-opt-card .exam-opt-letter {
  border-color: var(--exam-primary-600);
  background: var(--exam-primary-600);
  color: white;
}

.exam-opt-input:checked + .exam-opt-card .exam-opt-text {
  color: var(--exam-primary-600);
  font-weight: 600;
}

.exam-answer-input,
.exam-answer-textarea {
  width: 100%;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: white;
  color: var(--exam-text-main);
  padding: 14px 16px;
  font: inherit;
  outline: 0;
  transition: all 0.2s ease;
}

.exam-answer-input {
  max-width: 420px;
  height: 48px;
}

.exam-answer-textarea {
  min-height: 180px;
  resize: vertical;
}

.exam-answer-input:focus,
.exam-answer-textarea:focus {
  border-color: var(--exam-primary-500);
  box-shadow: var(--exam-shadow-focus);
}

.exam-text-answer {
  display: grid;
  gap: 8px;
}

.exam-text-answer small {
  justify-self: end;
  color: var(--exam-text-hint);
  font-size: 12px;
}

.exam-action-footer {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 100;
  height: 72px;
  display: flex;
  justify-content: center;
  border-top: 1px solid var(--exam-border-default);
  background: rgba(255, 255, 255, 0.90);
  backdrop-filter: blur(12px);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.03);
}

.exam-footer-container {
  width: 100%;
  max-width: 1200px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 32px;
}

.exam-footer-actions,
.exam-footer-progress {
  display: flex;
  align-items: center;
}

.exam-footer-actions {
  gap: 16px;
}

.exam-footer-progress {
  gap: 16px;
}

.exam-btn {
  min-width: 112px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--exam-radius-pill);
  padding: 0 24px;
  font-size: 14px;
  font-weight: 800;
}

.exam-btn-outline {
  border: 1px solid var(--exam-border-strong) !important;
  background: white !important;
  color: var(--exam-text-main) !important;
}

.exam-btn-outline:hover:not(:disabled) {
  border-color: var(--exam-primary-500) !important;
  background: var(--exam-bg-page) !important;
  color: var(--exam-primary-600) !important;
}

.exam-btn-primary {
  background: var(--exam-primary-600) !important;
  color: white !important;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.30);
}

.exam-btn-primary:hover:not(:disabled) {
  background: var(--exam-primary-500) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.40);
}

.exam-prog-text {
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 800;
}

.exam-prog-bar {
  width: 120px;
  height: 6px;
  overflow: hidden;
  border-radius: 4px;
  background: var(--exam-border-default);
}

.exam-prog-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--exam-primary-500);
  transition: width 0.25s ease;
}

.exam-modal-mask {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-bg);
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(8px);
}

.exam-confirm-card {
  width: 440px;
  max-width: calc(100vw - 32px);
  border-radius: var(--exam-radius-xl);
  background: white;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
  padding: 22px;
}

.exam-modal-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.exam-modal-head h2 {
  flex: 1;
  margin: 0;
  color: var(--exam-text-main);
  font-size: 20px;
}

.exam-modal-head svg {
  color: var(--exam-warning-500);
}

.exam-confirm-card p {
  margin: 8px 0;
  color: var(--exam-text-sec);
}

.exam-confirm-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.exam-result-main {
  flex: 1;
  display: grid;
  gap: 20px;
  width: min(900px, calc(100% - 48px));
  margin: 0 auto;
  overflow-y: auto;
  padding: 32px 0 48px;
}

.exam-result-card,
.exam-result-summary,
.exam-analysis-card {
  border: 1px solid white;
  border-radius: var(--exam-radius-xl);
  background: white;
  box-shadow: var(--exam-shadow-card);
  padding: 28px;
}

.exam-result-card {
  display: grid;
  justify-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #4F46E5, #06B6D4);
  color: white;
  padding: 40px;
}

.exam-result-card strong {
  font-size: 56px;
  line-height: 1;
}

.exam-result-card em {
  border-radius: var(--exam-radius-pill);
  background: rgba(255, 255, 255, 0.18);
  padding: 4px 12px;
  font-style: normal;
  font-weight: 800;
}

.exam-result-summary h2,
.exam-analysis-head h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--exam-text-main);
  font-size: 20px;
}

.exam-result-summary p {
  margin: 12px 0 0;
  color: var(--exam-text-sec);
}

.exam-analysis-card {
  display: grid;
  gap: 12px;
}

.exam-analysis-item {
  overflow: hidden;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: white;
}

.exam-analysis-item.open {
  background: var(--exam-bg-page);
}

.exam-analysis-trigger {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--exam-text-main);
  padding: 0 14px;
  text-align: left;
}

.exam-analysis-trigger span {
  margin-left: auto;
}

.exam-analysis-item.open .exam-analysis-trigger svg:last-child {
  transform: rotate(180deg);
}

.exam-analysis-body {
  display: grid;
  gap: 8px;
  border-top: 1px solid var(--exam-border-default);
  padding: 14px;
}

.exam-analysis-body p,
.exam-analysis-body small {
  margin: 0;
  color: var(--exam-text-sec);
}

@media (max-width: 900px) {
  .exam-header {
    height: auto;
    min-height: 64px;
    gap: 12px;
    padding: 12px 16px;
  }

  .exam-title {
    position: static;
    max-width: none;
    transform: none;
    font-size: 16px;
  }

  .exam-answer-page .timer-widget {
    padding: 5px 12px;
  }

  .exam-container {
    flex-direction: column;
    gap: 16px;
    padding: 16px 16px 104px;
  }

  .exam-nav-sidebar {
    width: 100%;
    flex-basis: auto;
  }

  .exam-nav-card {
    padding: 18px;
  }

  .exam-q-grid {
    grid-template-columns: repeat(8, minmax(34px, 1fr));
    gap: 8px;
  }

  .exam-q-card {
    padding: 24px;
  }

  .exam-q-meta-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 16px;
  }

  .exam-mark-btn {
    align-self: flex-start;
  }

  .exam-footer-container {
    gap: 10px;
    padding: 0 12px;
  }

  .exam-footer-progress {
    display: none;
  }

  .exam-footer-actions {
    gap: 8px;
  }

  .exam-btn {
    min-width: 0;
    padding: 0 14px;
  }
}

@media (max-width: 560px) {
  .exam-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .exam-title {
    order: -1;
    width: 100%;
  }

  .exam-q-grid {
    grid-template-columns: repeat(5, 1fr);
  }

  .exam-opt-card {
    align-items: flex-start;
    padding: 14px;
  }

  .exam-action-footer {
    height: 88px;
  }

  .exam-footer-container {
    align-items: stretch;
  }

  .exam-footer-actions {
    flex: 1;
  }

  .exam-footer-actions .exam-btn {
    flex: 1;
  }
}

@media (max-width: 640px) {
  .student-plan-page .plan-banner {
    padding: 24px;
  }

  .student-plan-page .banner-left {
    align-items: flex-start;
  }

  .student-plan-page .banner-icon {
    width: 52px;
    height: 52px;
    border-radius: 16px;
  }

  .student-plan-page .banner-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }

  .student-plan-page .b-stat-item h2 {
    font-size: 26px;
  }

  .student-plan-page .card {
    padding: 22px;
  }

  .student-plan-page .cal-grid {
    grid-auto-rows: 36px;
    gap: 10px 4px;
  }

  .student-plan-page .cal-day {
    width: 36px;
    height: 36px;
    font-size: 14px;
  }

  .student-plan-page .ai-prompt-bar {
    align-items: stretch;
    flex-direction: column;
    border-radius: var(--plan-radius-lg);
    padding: 12px;
  }

  .student-plan-page .btn-ai-gen {
    width: 100%;
    justify-content: center;
  }

  .student-plan-page .badges-grid {
    gap: 12px;
  }
}

@keyframes student-scale-fade {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes float-orb {
  0%, 100% { transform: translateY(0); box-shadow: 0 16px 40px rgba(139, 92, 246, 0.36); }
  50% { transform: translateY(-12px); box-shadow: 0 24px 48px rgba(139, 92, 246, 0.46); }
}

@media (max-width: 1080px) {
  .student-top {
    grid-template-columns: 1fr auto;
    padding: 0 24px;
  }

  .student-nav-links {
    display: none;
  }

  .student-course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .course-layout,
  .tutoring-grid,
  .student-plan-page .plan-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .student-shell {
    padding-bottom: 88px;
  }

  .student-top {
    height: 64px;
  }

  .brand strong {
    font-size: 16px;
  }

  .top-actions {
    gap: 10px;
  }

  .top-icon,
  .avatar-btn {
    width: 40px;
    height: 40px;
    min-width: 40px;
  }

  .student-main {
    padding: 24px 16px 96px;
  }

  .student-page {
    gap: 24px;
  }

  .hello-card {
    min-height: auto;
    flex-direction: column;
    align-items: flex-start;
    gap: 24px;
    padding: 30px;
  }

  .hello-card h1 {
    font-size: 28px;
  }

  .continue-card {
    grid-template-columns: 1fr;
  }

  .continue-cover {
    min-height: 180px;
  }

  .home-grid,
  .student-course-grid,
  .quick-row,
  .knowledge-layout,
  .wrong-layout,
  .achievement-row {
    grid-template-columns: 1fr;
  }

  .panel-card,
  .knowledge-head,
  .knowledge-body,
  .badge-card {
    padding: 22px;
  }

  .home-ai-recommend-card,
  .home-activity-card {
    padding: 24px;
  }

  .home-ai-recommend-card {
    flex-direction: column;
    align-items: stretch;
    gap: 24px;
  }

  .home-ai-rec-actions {
    width: 100%;
  }

  .home-ac-header {
    align-items: flex-start;
    gap: 12px;
  }

  .home-activity-item {
    gap: 16px;
  }

  .course-tools {
    display: grid;
    grid-template-columns: 1fr;
  }

  .course-tools .pretty-input,
  .course-tools .select-menu {
    width: 100%;
  }

  .page-title-row {
    display: grid;
    gap: 16px;
  }

  .page-title-row h1,
  .course-hero-student h1,
  .student-plan-page .banner-title,
  .profile-header-info h1 {
    font-size: 28px;
  }

  .course-hero-student {
    grid-template-columns: 1fr;
    padding: 30px;
  }

  .student-plan-page .plan-banner {
    align-items: flex-start;
    flex-direction: column;
    padding: 30px;
  }

  .student-plan-page .banner-stats {
    width: 100%;
    justify-content: space-between;
    gap: 18px;
  }

  .student-plan-page .card {
    padding: 28px;
  }

  .student-plan-page .ai-prompt-bar {
    max-width: none;
  }

  .student-plan-page .plan-task-row {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .student-plan-page .plan-task-tag {
    grid-column: 2;
    width: fit-content;
  }

  .wrong-hero {
    grid-template-columns: 1fr;
  }

  .wrong-tools {
    grid-template-columns: 1fr;
  }

  .quiz-modern-header {
    display: grid;
    gap: 16px;
  }

  .quiz-modern-title h1 {
    font-size: 28px;
  }

  .quiz-modern-page .course-select,
  .quiz-modern-page .select-menu {
    width: 100%;
  }

  .quiz-modern-tabs {
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .practice-modern-grid {
    grid-template-columns: 1fr;
  }

  .practice-modern-card {
    padding: 24px;
  }

  .practice-settings-row {
    align-items: stretch;
    flex-direction: column;
    border-radius: var(--quiz-radius-lg);
    padding: 8px;
  }

  .practice-segmented-control {
    flex-wrap: wrap;
  }

  .practice-segmented-control button {
    flex: 1 1 72px;
  }

  .practice-feature-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .profile-pc-layout,
  .profile-form-grid,
  .notice-settings-grid {
    grid-template-columns: 1fr;
  }

  .profile-main-card {
    padding: 22px;
  }

  .profile-cover {
    height: 210px;
    margin-bottom: 70px;
  }

  .big-avatar {
    left: 50%;
    transform: translateX(-50%);
  }

  .profile-header-info {
    display: grid;
    justify-items: center;
    padding: 0 8px;
    text-align: center;
  }

  .profile-header-info p {
    justify-content: center;
  }

  .profile-header-info aside {
    text-align: center;
  }

  .bottom-tabs {
    display: grid;
    border-top: 1px solid rgba(226, 232, 240, 0.72);
    background: rgba(255, 255, 255, 0.86);
    backdrop-filter: blur(16px);
  }
}

/* Student AI Q&A page: single source of truth, rewritten from the provided reference. */
.student-main:has(.qa-modern-page) {
  width: 100%;
  max-width: none;
  background: var(--s-bg, #F4F6F9);
  padding: 0 0 96px;
}

.student-page:has(.qa-modern-page) {
  display: block;
  min-height: calc(100vh - 72px);
  background: var(--s-bg, #F4F6F9);
}

.qa-modern-page {
  --qa-primary-50: #EEF2FF;
  --qa-primary-100: #E0E7FF;
  --qa-primary-400: #818CF8;
  --qa-primary-500: #6366F1;
  --qa-primary-600: #4F46E5;
  --qa-ai-gradient: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --qa-ai-light: #F5F3FF;
  --qa-bg: #F4F6F9;
  --qa-surface: #FFFFFF;
  --qa-muted-bg: #F8FAFC;
  --qa-border: #E2E8F0;
  --qa-text: #1E293B;
  --qa-secondary: #64748B;
  --qa-hint: #94A3B8;
  --qa-radius-md: 12px;
  --qa-radius-lg: 16px;
  --qa-radius-xl: 24px;
  --qa-pill: 9999px;
  --qa-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --qa-shadow-float: 0 12px 32px rgba(15, 23, 42, 0.08);
  --qa-shadow-focus: 0 0 0 4px rgba(79, 70, 229, 0.15);
  position: relative;
  width: 100%;
  max-width: none;
  min-height: calc(100vh - 152px);
  margin: 0;
  background: var(--s-bg, var(--qa-bg));
  padding: 0 0 160px;
  color: var(--qa-text);
}

.qa-modern-page,
.qa-modern-page * {
  box-sizing: border-box;
}

.qa-modern-page button {
  font-family: inherit;
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out),
    opacity var(--duration-fast) var(--ease-out);
}

.qa-modern-page textarea {
  font-family: inherit;
}

.qa-modern-page.empty {
  display: block;
  place-items: initial;
  gap: 0;
  color: var(--qa-text);
  text-align: initial;
}

.qa-modern-page .qa-scroll-area {
  width: 100%;
}

.qa-modern-page .chat-wrapper {
  width: 100%;
  max-width: 860px;
  display: flex;
  flex-direction: column;
  gap: 32px;
  margin: 0 auto;
  padding: 40px 24px;
}

.qa-modern-page .qa-header {
  position: static;
  inset: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin: 0 0 16px;
  padding-bottom: 32px;
  border-bottom: 1px dashed var(--qa-border);
}

.qa-modern-page .qa-title-group {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.qa-modern-page.empty .qa-header > .qa-title-group {
  display: flex;
}

.qa-modern-page .qa-title-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 16px;
  background: var(--qa-ai-light);
  color: #8B5CF6;
  box-shadow: 0 8px 16px rgba(139, 92, 246, 0.10);
}

.qa-modern-page .qa-title h1 {
  margin: 0 0 4px;
  color: var(--qa-text);
  font-size: 24px;
  line-height: 1.25;
  font-weight: 800;
  letter-spacing: 0;
}

.qa-modern-page .qa-title p {
  margin: 0;
  color: var(--qa-hint);
  font-size: 14px;
  font-weight: 600;
}

.qa-modern-page .qa-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.qa-modern-page .course-select {
  min-width: 0;
}

.qa-modern-page .course-select .select-menu > button,
.qa-modern-page .select-menu-empty {
  min-height: 40px;
  border: 1px solid var(--qa-border);
  border-radius: var(--qa-pill);
  background: var(--qa-surface);
  color: var(--qa-text);
  box-shadow: var(--qa-shadow-sm);
  padding: 0 16px;
  font-size: 14px;
  font-weight: 700;
}

.qa-modern-page .course-select .select-menu > button:hover,
.qa-modern-page .select-menu-empty:hover {
  border-color: var(--qa-primary-500);
  color: var(--qa-primary-600);
  transform: translateY(-2px);
}

.qa-modern-page .action-circle-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--qa-border);
  border-radius: 50%;
  background: var(--qa-surface);
  color: var(--qa-secondary);
  box-shadow: var(--qa-shadow-sm);
}

.qa-modern-page .action-circle-btn:hover {
  background: var(--qa-muted-bg);
  color: var(--qa-primary-600);
  transform: translateY(-2px);
}

.qa-modern-page .qa-tutoring-link {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: var(--qa-pill);
  background: var(--qa-ai-gradient);
  color: white;
  box-shadow: 0 8px 18px rgba(139, 92, 246, 0.22);
  padding: 0 16px;
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
}

.qa-modern-page .qa-tutoring-link:hover {
  filter: brightness(1.04);
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(139, 92, 246, 0.30);
}

.qa-modern-page .qa-tutoring-link:active {
  transform: translateY(0);
}

.qa-modern-page .history-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-modal);
  width: 360px;
  display: grid;
  align-content: start;
  gap: 14px;
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: 24px 0 0 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(18px);
  padding: 24px;
}

.qa-modern-page .drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.qa-modern-page .drawer-head h2 {
  margin: 0;
  color: var(--qa-text);
  font-size: 18px;
  font-weight: 800;
}

.qa-modern-page .drawer-head button {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  background: var(--qa-muted-bg);
  color: var(--qa-secondary);
}

.qa-modern-page .drawer-head button:hover {
  background: var(--qa-primary-50);
  color: var(--qa-primary-600);
  transform: translateY(-1px);
}

.qa-modern-page .history-favorite-toggle {
  width: fit-content;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 9px;
  border: 1px solid var(--qa-border);
  border-radius: var(--qa-pill);
  background: var(--qa-surface);
  color: var(--qa-secondary);
  box-shadow: var(--qa-shadow-sm);
  padding: 0 13px 0 10px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.qa-modern-page .history-favorite-toggle .favorite-check-box {
  width: 18px;
  height: 18px;
  min-width: 18px;
  max-width: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 18px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--qa-border);
  border-radius: 6px;
  background: #FFFFFF;
  color: transparent;
  line-height: 0;
  overflow-wrap: normal;
  transition: all 0.2s ease;
}

.qa-modern-page .history-favorite-toggle .favorite-check-box::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 48%;
  width: 8px;
  height: 4px;
  border-left: 2px solid #FFFFFF;
  border-bottom: 2px solid #FFFFFF;
  opacity: 0;
  transform: translate(-50%, -50%) rotate(-45deg);
  transform-origin: center;
}

.qa-modern-page .history-favorite-toggle strong {
  display: inline-block;
  font-size: inherit;
  font-weight: inherit;
  line-height: 1;
}

.qa-modern-page .history-favorite-toggle:hover {
  border-color: var(--qa-primary-500);
  color: var(--qa-primary-600);
  transform: translateY(-1px);
}

.qa-modern-page .history-favorite-toggle:active {
  transform: translateY(0);
}

.qa-modern-page .history-favorite-toggle.checked {
  border-color: var(--qa-primary-100);
  background: var(--qa-primary-50);
  color: var(--qa-primary-600);
}

.qa-modern-page .history-favorite-toggle.checked .favorite-check-box {
  border-color: var(--qa-primary-600);
  background: var(--qa-primary-600);
  color: #FFFFFF;
}

.qa-modern-page .history-favorite-toggle.checked .favorite-check-box::after {
  opacity: 1;
}

.qa-modern-page .history-row {
  min-height: 56px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 4px 8px;
  border: 0;
  border-radius: var(--qa-radius-md);
  background: transparent;
  color: var(--qa-text);
  padding: 10px;
  text-align: left;
}

.qa-modern-page .history-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qa-modern-page .history-row small {
  grid-column: 2;
  color: var(--qa-hint);
}

.qa-modern-page .history-row:hover {
  background: var(--qa-primary-50);
  color: var(--qa-primary-600);
  transform: translateX(2px);
}

.qa-modern-page .qa-welcome {
  min-height: 280px;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 32px 0 8px;
  text-align: center;
}

.qa-modern-page .qa-welcome > svg {
  width: 84px;
  height: 84px;
  padding: 20px;
  border: 4px solid white;
  border-radius: 50%;
  background: var(--qa-ai-gradient);
  color: white;
  box-shadow: 0 16px 40px rgba(139, 92, 246, 0.36);
}

.qa-modern-page .qa-welcome h2 {
  margin: 12px 0 0;
  color: var(--qa-text);
  font-size: 30px;
  line-height: 1.25;
  font-weight: 800;
  letter-spacing: 0;
}

.qa-modern-page .qa-welcome p {
  margin: 0;
  color: var(--qa-secondary);
  font-size: 16px;
}

.qa-modern-page .prompt-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin: 0;
}

.qa-modern-page .prompt-grid button {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: var(--qa-pill);
  background: rgba(255, 255, 255, 0.78);
  color: var(--qa-secondary);
  box-shadow: var(--qa-shadow-sm);
  padding: 0 18px;
  font-weight: 700;
}

.qa-modern-page .prompt-grid button:hover {
  background: white;
  color: var(--qa-primary-600);
  transform: translateY(-2px);
  box-shadow: var(--qa-shadow-float);
}

/* AI Q&A chat bubbles: rebuilt from the provided reference. */
.qa-modern-page :deep(.chat-list.large) {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 0;
}

.qa-modern-page :deep(.message-row) {
  width: 100%;
  display: flex;
  gap: 16px;
  animation: qa-message-in 300ms ease-out both;
}

.qa-modern-page :deep(.message-row.user) {
  flex-direction: row-reverse;
}

.qa-modern-page :deep(.message-row.ai) {
  align-items: flex-start;
}

.qa-modern-page :deep(.avatar-user) {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid var(--qa-border);
  border-radius: 50%;
  background: var(--qa-muted-bg);
  color: var(--qa-secondary);
  box-shadow: none;
}

.qa-modern-page :deep(.avatar-ai) {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  margin-top: 4px;
  border: 2px solid white;
  border-radius: 50%;
  background: var(--qa-ai-gradient);
  color: white;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.30);
}

.qa-modern-page :deep(.chat-bubble) {
  position: relative;
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.qa-modern-page :deep(.chat-bubble::before) {
  display: none;
}

.qa-modern-page :deep(.bubble-user) {
  max-width: 75%;
  border-radius: 20px 20px 4px 20px;
  background: var(--qa-primary-600);
  color: white;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.20);
  padding: 14px 20px;
  font-size: 15px;
  font-weight: 600;
}

.qa-modern-page :deep(.bubble-user p) {
  margin: 0;
  line-height: 1.6;
}

.qa-modern-page :deep(.chat-attachments),
.class-chat :deep(.chat-attachments) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.qa-modern-page :deep(.chat-attachment),
.class-chat :deep(.chat-attachment) {
  max-width: 220px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  color: inherit;
  padding: 6px 9px 6px 6px;
  text-decoration: none;
  font-size: 12px;
  font-weight: 700;
}

.class-chat :deep(.chat-msg:not(.user) .chat-attachment),
.qa-modern-page :deep(.bubble-ai .chat-attachment) {
  border: 1px solid var(--qa-border, var(--color-border-default));
  background: var(--qa-muted-bg, var(--color-bg-muted));
  color: var(--qa-secondary, var(--color-text-secondary));
}

.qa-modern-page :deep(.chat-attachment img),
.class-chat :deep(.chat-attachment img) {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border-radius: 10px;
  object-fit: cover;
}

.qa-modern-page :deep(.chat-attachment span),
.class-chat :deep(.chat-attachment span) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qa-modern-page :deep(.bubble-ai) {
  flex: 1;
  max-width: 85%;
}

.qa-modern-page :deep(.thinking-process),
.qa-modern-page :deep(.thought-toggle) {
  width: fit-content;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  border: 1px solid var(--qa-border);
  border-radius: var(--qa-pill);
  background: white;
  color: var(--qa-secondary);
  box-shadow: var(--qa-shadow-sm);
  padding: 0 12px;
  font-size: 13px;
  font-weight: 700;
}

.qa-modern-page :deep(.thinking-process:hover),
.qa-modern-page :deep(.thought-toggle:hover) {
  background: var(--qa-muted-bg);
  color: var(--qa-text);
  transform: translateY(-1px);
}

.qa-modern-page :deep(.thought-toggle svg) {
  color: var(--qa-hint);
}

.qa-modern-page :deep(.thought-toggle svg:last-child) {
  transition: transform 250ms cubic-bezier(0.16, 1, 0.3, 1);
}

.qa-modern-page :deep(.thought-toggle .rotate) {
  transform: rotate(180deg);
}

.qa-modern-page :deep(.thought) {
  overflow: hidden;
  max-width: 100%;
  border: 1px solid rgba(221, 214, 254, 0.86);
  border-radius: 18px;
  background: var(--qa-ai-light);
  color: #6D28D9;
  box-shadow: var(--qa-shadow-sm);
  margin: -4px 0 16px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
}

.qa-modern-page :deep(.ai-content-card) {
  border: 1px solid rgba(226, 232, 240, 0.60);
  border-radius: 8px 24px 24px 24px;
  background: white;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  padding: 20px 24px;
}

.qa-modern-page :deep(.ai-text) {
  margin: 0 0 24px;
  color: var(--qa-text);
  font-size: 15px;
  line-height: 1.7;
}

.qa-modern-page :deep(.markdown-body p),
.class-chat :deep(.markdown-body p) {
  margin: 0 0 12px;
}

.qa-modern-page :deep(.markdown-body p:last-child),
.class-chat :deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}

.qa-modern-page :deep(.markdown-body ul),
.qa-modern-page :deep(.markdown-body ol),
.class-chat :deep(.markdown-body ul),
.class-chat :deep(.markdown-body ol) {
  margin: 8px 0 12px;
  padding-left: 22px;
}

.qa-modern-page :deep(.markdown-body li + li),
.class-chat :deep(.markdown-body li + li) {
  margin-top: 4px;
}

.qa-modern-page :deep(.markdown-body code),
.class-chat :deep(.markdown-body code) {
  border-radius: 6px;
  background: var(--qa-primary-50, var(--color-primary-50));
  color: #6D28D9;
  padding: 2px 6px;
  font-family: var(--font-family-mono);
  font-size: 0.92em;
}

.qa-modern-page :deep(.markdown-body pre),
.class-chat :deep(.markdown-body pre) {
  overflow: auto;
  border-radius: 12px;
  background: #0F172A;
  color: #E2E8F0;
  margin: 12px 0;
  padding: 14px;
}

.qa-modern-page :deep(.markdown-body pre code),
.class-chat :deep(.markdown-body pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}

.qa-modern-page :deep(.markdown-body blockquote),
.class-chat :deep(.markdown-body blockquote) {
  border-left: 3px solid #8B5CF6;
  background: var(--qa-ai-light, var(--color-ai-light));
  margin: 12px 0;
  padding: 10px 12px;
}

.qa-modern-page :deep(.markdown-body table),
.class-chat :deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 14px;
}

.qa-modern-page :deep(.markdown-body th),
.qa-modern-page :deep(.markdown-body td),
.class-chat :deep(.markdown-body th),
.class-chat :deep(.markdown-body td) {
  border: 1px solid var(--qa-border, var(--color-border-default));
  padding: 8px 10px;
}

.qa-modern-page :deep(.markdown-body th),
.class-chat :deep(.markdown-body th) {
  background: var(--qa-muted-bg, var(--color-bg-muted));
  font-weight: 800;
}

.qa-modern-page :deep(.markdown-body .katex-display),
.class-chat :deep(.markdown-body .katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 0;
}

.qa-modern-page :deep(.references-area),
.qa-modern-page :deep(.source-tags) {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--qa-border);
}

.qa-modern-page :deep(.ref-label),
.qa-modern-page :deep(.source-label) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--qa-hint);
  font-size: 13px;
  font-weight: 600;
}

.qa-modern-page :deep(.ref-tag),
.qa-modern-page :deep(.source-tags .tag) {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  border: 0;
  border-radius: var(--qa-pill);
  background: var(--qa-primary-50);
  color: var(--qa-primary-600);
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.qa-modern-page :deep(.ref-tag:hover),
.qa-modern-page :deep(.source-tags .tag:hover) {
  background: var(--qa-primary-100);
}

.qa-modern-page :deep(.ai-action-bar),
.qa-modern-page :deep(.msg-actions) {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  opacity: 1;
}

.qa-modern-page :deep(.ai-action-btn),
.qa-modern-page :deep(.msg-actions button) {
  width: auto;
  min-width: 0;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  overflow: visible;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--qa-hint);
  padding: 0 10px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.qa-modern-page :deep(.ai-action-btn:disabled),
.qa-modern-page :deep(.msg-actions button:disabled) {
  cursor: not-allowed;
  opacity: 0.45;
}

.qa-modern-page :deep(.ai-action-btn svg),
.qa-modern-page :deep(.msg-actions button svg) {
  width: 16px;
  height: 16px;
}

.qa-modern-page :deep(.ai-action-btn:hover),
.qa-modern-page :deep(.msg-actions button:hover) {
  background: var(--qa-muted-bg);
  color: var(--qa-text);
  transform: translateY(-1px);
}

.qa-modern-page :deep(.ai-action-btn.success:hover),
.qa-modern-page :deep(.msg-actions button.success:hover) {
  background: #ECFDF5;
  color: #10B981;
}

.qa-modern-page :deep(.streaming-placeholder) {
  color: var(--qa-hint);
  font-weight: 600;
}

.qa-modern-page :deep(.thinking) {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(221, 214, 254, 0.90);
  border-radius: var(--qa-pill);
  background: white;
  color: var(--qa-secondary);
  box-shadow: var(--qa-shadow-sm);
  padding: 10px 14px;
}

.qa-modern-page :deep(.thinking i) {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--qa-ai-gradient);
  animation: thinking var(--duration-slow) var(--ease-in-out) infinite;
}

.qa-modern-page :deep(.thinking .dot-2) {
  animation-delay: 120ms;
}

.qa-modern-page :deep(.thinking .dot-3) {
  animation-delay: 240ms;
}

.class-chat {
  --class-chat-primary: #4F46E5;
  --class-chat-primary-50: #EEF2FF;
  --class-chat-border: #E2E8F0;
  --class-chat-text: #1E293B;
  --class-chat-muted: #64748B;
  --class-chat-ai: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #FFFFFF;
}

.class-chat .context-bar {
  flex: 0 0 auto;
}

.class-chat-scroll {
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 4px 4px 0;
  scrollbar-gutter: stable;
}

.class-chat-dock {
  position: relative;
  z-index: 4;
  flex: 0 0 auto;
  display: grid;
  gap: 10px;
  border-top: 1px solid var(--class-chat-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.86), #FFFFFF 34%);
  box-shadow: 0 -12px 24px rgba(15, 23, 42, 0.04);
  margin: 0 -2px;
  padding: 12px 2px 0;
}

.class-chat-dock .qa-attachment-strip.compact {
  max-height: 88px;
  overflow-y: auto;
}

.class-chat-dock .quick-tags {
  width: 100%;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.class-chat-dock .quick-tags button {
  flex: 0 0 auto;
  border-color: var(--class-chat-border);
  background: #FFFFFF;
  color: var(--class-chat-muted);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.035);
}

.class-chat-dock .quick-tags button:hover {
  background: var(--class-chat-primary-50);
  color: var(--class-chat-primary);
  transform: translateY(-1px);
}

.class-chat :deep(.chat-list) {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 180px;
  padding: 14px 0 8px;
}

.class-chat :deep(.chat-msg) {
  width: 100%;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  animation: bubble-in 220ms ease-out both;
}

.class-chat :deep(.chat-msg.user) {
  flex-direction: row-reverse;
}

.class-chat :deep(.chat-avatar) {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--class-chat-ai);
  color: #FFFFFF;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.20);
}

.class-chat :deep(.chat-msg.user .chat-avatar) {
  border: 1px solid var(--class-chat-border);
  background: #F8FAFC;
  color: var(--class-chat-muted);
  box-shadow: none;
}

.class-chat :deep(.chat-bubble) {
  position: relative;
  max-width: calc(100% - 46px);
  min-width: 0;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 8px 18px 18px 18px;
  background: #FFFFFF;
  color: var(--class-chat-text);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  padding: 12px 14px;
}

.class-chat :deep(.chat-bubble::before) {
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 3px;
  background: var(--class-chat-ai);
}

.class-chat :deep(.chat-msg.user .chat-bubble) {
  border: 0;
  border-radius: 18px 8px 18px 18px;
  background: var(--class-chat-primary);
  color: #FFFFFF;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.20);
}

.class-chat :deep(.chat-msg.user .chat-bubble::before) {
  display: none;
}

.class-chat :deep(.chat-bubble p) {
  margin: 0;
  line-height: 1.7;
}

.class-chat :deep(.ai-text) {
  color: var(--class-chat-text);
  font-size: 14px;
  line-height: 1.75;
}

.class-chat :deep(.thought-toggle) {
  width: fit-content;
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
  border: 1px solid rgba(221, 214, 254, 0.9);
  border-radius: 9999px;
  background: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  color: #6D28D9;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
}

.class-chat :deep(.thought) {
  overflow: hidden;
  border: 1px solid rgba(221, 214, 254, 0.85);
  border-radius: 12px;
  background: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  color: #6D28D9;
  margin-bottom: 10px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
}

.class-chat :deep(.source-tags) {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  border-top: 1px dashed var(--class-chat-border);
  margin-top: 10px;
  padding-top: 10px;
}

.class-chat :deep(.source-label) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--class-chat-muted);
  font-size: 12px;
  font-weight: 700;
}

.class-chat :deep(.source-tags .tag) {
  min-height: 22px;
  border-radius: 9999px;
  background: var(--class-chat-primary-50);
  color: var(--class-chat-primary);
  padding: 0 9px;
  font-size: 12px;
  font-weight: 700;
}

.class-chat :deep(.msg-actions) {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  opacity: 1;
}

.class-chat :deep(.msg-actions button) {
  width: auto;
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--class-chat-muted);
  padding: 0 8px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.class-chat :deep(.msg-actions button:hover:not(:disabled)) {
  background: #F8FAFC;
  color: var(--class-chat-text);
}

.class-chat :deep(.msg-actions button:disabled) {
  cursor: not-allowed;
  opacity: 0.45;
}

.class-chat :deep(.thinking) {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(221, 214, 254, 0.9);
  border-radius: 9999px;
  background: #FFFFFF;
  color: var(--class-chat-muted);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  padding: 10px 14px;
}

.class-chat :deep(.thinking i) {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--class-chat-ai);
  animation: thinking var(--duration-slow) var(--ease-in-out) infinite;
}

.qa-modern-page .input-dock-container {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-fixed);
  width: auto;
  display: flex;
  justify-content: center;
  transform: none;
  border: 0;
  border-radius: 0;
  background: linear-gradient(to bottom, rgba(244, 246, 249, 0), rgba(244, 246, 249, 1) 40%);
  box-shadow: none;
  padding: 40px 24px 32px;
  pointer-events: none;
}

.qa-modern-page .input-wrapper {
  width: 100%;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: auto;
}

.qa-modern-page .context-badge {
  align-self: flex-start;
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 24px;
  border: 1px solid var(--qa-primary-100);
  border-radius: var(--qa-pill);
  background: var(--qa-surface);
  color: var(--qa-primary-600);
  box-shadow: var(--qa-shadow-sm);
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
  animation: qa-float-up 500ms var(--ease-out);
}

.qa-modern-page .input-box {
  min-height: 70px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(226, 232, 240, 0.84);
  border-radius: var(--qa-radius-xl);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: var(--qa-shadow-float);
  padding: 12px 16px 12px 24px;
}

.qa-modern-page .input-box:focus-within {
  border-color: var(--qa-primary-400);
  box-shadow: 0 20px 40px rgba(79, 70, 229, 0.10), var(--qa-shadow-focus);
}

.qa-image-input {
  display: none;
}

.qa-attachment-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 18px -2px;
}

.qa-attachment-strip.compact {
  margin: 0 0 8px;
}

.qa-attachment-chip {
  min-width: 0;
  max-width: 220px;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--qa-border, var(--color-border-default));
  border-radius: 12px;
  background: white;
  box-shadow: var(--qa-shadow-sm, var(--shadow-sm));
  padding: 5px 7px 5px 5px;
  color: var(--qa-secondary, var(--color-text-secondary));
  font-size: 12px;
  font-weight: 700;
}

.qa-attachment-chip img {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: 8px;
  object-fit: cover;
}

.qa-attachment-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qa-attachment-chip button {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border: 0;
  border-radius: 50%;
  background: var(--qa-muted-bg, var(--color-bg-muted));
  color: var(--qa-hint, var(--color-text-muted));
}

.qa-attachment-chip button:hover {
  background: #FEE2E2;
  color: #EF4444;
}

.qa-modern-page .input-box textarea {
  flex: 1;
  align-self: center;
  min-height: 40px;
  max-height: 120px;
  border: 0;
  background: transparent;
  color: var(--qa-text);
  resize: none;
  outline: none;
  overflow: auto;
  padding: 8px 0;
  font-size: 16px;
  line-height: 1.5;
}

.qa-modern-page .input-box textarea::placeholder {
  color: var(--qa-hint);
}

.qa-modern-page .attach-btn,
.class-chat .attach-btn {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border: 1px solid var(--qa-border, var(--color-border-default));
  border-radius: 14px;
  background: var(--qa-muted-bg, var(--color-bg-muted));
  color: var(--qa-secondary, var(--color-text-secondary));
  margin-bottom: 0;
}

.qa-modern-page .attach-btn:hover:not(:disabled),
.class-chat .attach-btn:hover:not(:disabled) {
  border-color: var(--qa-primary-100, var(--color-primary-100));
  background: var(--qa-primary-50, var(--color-primary-50));
  color: var(--qa-primary-600, var(--color-primary-600));
  transform: translateY(-1px);
}

.qa-modern-page .attach-btn:disabled,
.class-chat .attach-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.class-chat .chat-input.compact {
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: end;
  border-radius: var(--radius-lg);
}

.class-chat .chat-input.compact textarea {
  align-self: center;
  min-height: 40px;
}

.qa-modern-page .send-btn {
  width: 44px;
  height: 44px;
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 14px;
  background: var(--qa-primary-600);
  color: white;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.30);
  margin-bottom: 0;
}

.qa-modern-page .send-btn:hover:not(:disabled) {
  background: var(--qa-primary-500);
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.40);
}

.qa-modern-page .send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.qa-modern-page .disclaimer {
  display: block;
  margin-top: 8px;
  color: var(--qa-hint);
  text-align: center;
  font-size: 12px;
}

.qa-modern-page .thought-roll-enter-active,
.qa-modern-page .thought-roll-leave-active {
  overflow: hidden;
  transition:
    max-height var(--duration-slow) var(--ease-out),
    opacity var(--duration-base) var(--ease-out),
    padding-top var(--duration-base) var(--ease-out),
    padding-bottom var(--duration-base) var(--ease-out),
    margin var(--duration-base) var(--ease-out);
}

.qa-modern-page .thought-roll-enter-from,
.qa-modern-page .thought-roll-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
  margin-top: 0;
  margin-bottom: 0;
}

.qa-modern-page .thought-roll-enter-to,
.qa-modern-page .thought-roll-leave-from {
  max-height: 320px;
  opacity: 1;
}

@keyframes qa-message-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes qa-float-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .qa-modern-page {
    padding-bottom: 178px;
  }

  .qa-modern-page .chat-wrapper {
    padding: 0 0 32px;
  }

  .qa-modern-page .qa-header {
    display: grid;
    gap: 18px;
    padding-bottom: 24px;
  }

  .qa-modern-page .qa-header-actions {
    flex-wrap: wrap;
  }

  .qa-modern-page .course-select {
    flex: 1;
  }

  .qa-modern-page .chat-msg.user .chat-bubble,
  .qa-modern-page .bubble-ai {
    max-width: calc(100% - 48px);
  }

  .qa-modern-page .input-dock-container {
    padding: 34px 12px 76px;
  }

  .qa-modern-page .history-drawer {
    width: min(360px, 92vw);
  }
}

/* Student UI audit overrides: final scoped layer for alignment, readability and feedback. */
.student-shell,
.student-shell *,
.study-room,
.study-room * {
  box-sizing: border-box;
  writing-mode: horizontal-tb;
  text-orientation: mixed;
}

.student-shell {
  --student-audit-focus: 0 0 0 4px rgba(99, 102, 241, 0.18);
  --student-audit-error: #DC2626;
  --student-audit-success: #059669;
}

.student-main {
  width: min(1280px, 100%);
  max-width: 1280px;
  margin-inline: auto;
  padding: 40px 32px 92px;
}

.student-page {
  width: 100%;
  min-width: 0;
  align-items: stretch;
  gap: 32px;
}

.student-page > *,
.student-shell section,
.student-shell article,
.student-shell aside,
.student-shell form,
.student-shell div {
  min-width: 0;
}

.student-shell h1,
.student-shell h2,
.student-shell h3,
.student-shell p,
.student-shell strong,
.student-shell span,
.student-shell small,
.student-shell em,
.student-shell label,
.student-shell button,
.student-shell a,
.student-shell input,
.student-shell textarea,
.student-shell .markdown-body,
.student-shell .lesson-markdown {
  letter-spacing: 0;
  word-break: normal;
  overflow-wrap: anywhere;
}

.student-shell button,
.student-shell a,
.student-shell input,
.student-shell textarea,
.student-shell .select-menu > button,
.student-shell .dropdown-trigger,
.student-shell .quick-tile,
.student-shell .lesson-item,
.student-shell .material-row,
.student-shell .history-row,
.student-shell .practice-feature-card,
.student-shell .practice-history-item,
.student-shell .home-action-task-card {
  -webkit-tap-highlight-color: transparent;
}

.student-shell button:focus-visible,
.student-shell a:focus-visible,
.student-shell input:focus-visible,
.student-shell textarea:focus-visible,
.student-shell select:focus-visible,
.student-shell .select-menu > button:focus-visible,
.student-shell .dropdown-trigger:focus-visible,
.student-shell .quick-tile:focus-visible,
.student-shell .lesson-item:focus-visible,
.student-shell .material-row:focus-visible,
.student-shell .home-action-task-card:focus-visible,
.student-shell .history-row:focus-visible,
.student-shell .practice-feature-card:focus-visible,
.student-shell .practice-history-item:focus-visible,
.student-shell .cal-day:focus-visible,
.student-shell .plan-task-check:focus-visible {
  outline: 0;
  border-color: var(--s-primary-500, #6366F1) !important;
  box-shadow: var(--student-audit-focus) !important;
}

.student-shell button:not(:disabled):active,
.student-shell a:not([aria-disabled="true"]):active,
.student-shell .quick-tile:active,
.student-shell .lesson-item:active,
.student-shell .material-row:active,
.student-shell .home-action-task-card:active,
.student-shell .practice-history-item:active,
.student-shell .history-row:active {
  transform: translateY(0) scale(0.985);
}

.student-shell button:disabled,
.student-shell input:disabled,
.student-shell textarea:disabled,
.student-shell [aria-disabled="true"] {
  cursor: not-allowed !important;
  opacity: 0.56 !important;
  transform: none !important;
  box-shadow: none !important;
  filter: grayscale(0.08);
}

.student-shell button[data-loading="true"],
.student-shell .btn[data-loading="true"],
.student-shell .practice-generate-btn[data-loading="true"],
.student-shell .btn-ai-gen[data-loading="true"] {
  position: relative;
  pointer-events: none;
  color: transparent !important;
}

.student-shell button[data-loading="true"]::before,
.student-shell .btn[data-loading="true"]::before,
.student-shell .practice-generate-btn[data-loading="true"]::before,
.student-shell .btn-ai-gen[data-loading="true"]::before {
  content: none !important;
  display: none !important;
}

.student-shell button[data-loading="true"] > *,
.student-shell .btn[data-loading="true"] > *,
.student-shell .practice-generate-btn[data-loading="true"] > *,
.student-shell .btn-ai-gen[data-loading="true"] > * {
  opacity: 0 !important;
  visibility: hidden;
}

.student-shell button[data-loading="true"]::after,
.student-shell .btn[data-loading="true"]::after,
.student-shell .practice-generate-btn[data-loading="true"]::after,
.student-shell .btn-ai-gen[data-loading="true"]::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  margin: -9px 0 0 -9px;
  border: 2px solid rgba(255, 255, 255, 0.55);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: student-audit-spin 0.8s linear infinite;
}

.student-shell .btn-secondary[data-loading="true"]::after,
.student-shell .btn-ghost[data-loading="true"]::after,
.student-shell .btn-outline[data-loading="true"]::after {
  border-color: rgba(99, 102, 241, 0.22);
  border-top-color: var(--s-primary-600, #4F46E5);
}

.student-shell input[aria-invalid="true"],
.student-shell textarea[aria-invalid="true"],
.student-shell .input.error,
.student-shell .textarea.error,
.student-shell .code-input.error,
.student-shell .is-error {
  border-color: var(--student-audit-error) !important;
  box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.12) !important;
}

.student-shell .code-input.ok,
.student-shell .is-success {
  border-color: var(--student-audit-success) !important;
  box-shadow: 0 0 0 4px rgba(5, 150, 105, 0.12) !important;
}

.student-top {
  grid-template-columns: minmax(180px, 0.8fr) minmax(0, auto) minmax(160px, 0.8fr);
}

.student-nav-links {
  max-width: 100%;
  overflow-x: auto;
  scrollbar-width: none;
}

.student-nav-links::-webkit-scrollbar,
.quick-tags::-webkit-scrollbar,
.quiz-modern-tabs::-webkit-scrollbar,
.class-chat-dock .quick-tags::-webkit-scrollbar {
  display: none;
}

.student-nav-link,
.top-icon,
.avatar-btn,
.bottom-tabs button,
.tag,
.home-data-tag,
.home-refresh-btn,
.home-task-type,
.home-ac-view-all,
.course-meta span,
.mini-data span,
.student-plan-page .plan-task-tag,
.student-plan-page .badge-name,
.qa-modern-page .qa-tutoring-link,
.qa-modern-page .action-circle-btn {
  white-space: nowrap;
}

.home-grid {
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
  align-items: start;
}

.student-course-grid {
  grid-template-columns: repeat(auto-fill, minmax(300px, 360px));
  justify-content: start;
  align-items: stretch;
}

.course-layout {
  grid-template-columns: minmax(0, 1.35fr) minmax(420px, 0.95fr);
  align-items: start;
}

.course-layout > aside {
  min-width: 420px;
}

.quick-row {
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.tutoring-grid,
.practice-modern-grid {
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.85fr);
  align-items: start;
}

.knowledge-layout,
.wrong-layout {
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
  align-items: start;
}

.profile-pc-layout {
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
}

.student-plan-page .plan-layout {
  grid-template-columns: minmax(0, 1.75fr) minmax(300px, 1fr);
}

.course-tools,
.wrong-tools {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(180px, 240px);
  align-items: center;
  gap: 14px;
}

.course-tools .pretty-input,
.course-tools .select-menu,
.wrong-tools .pretty-input,
.wrong-tools .select-menu {
  width: 100%;
}

.panel-card,
.student-course-card,
.course-tools,
.knowledge-head,
.knowledge-body,
.wrong-hero div,
.profile-identity-card,
.profile-main-card,
.student-plan-page .card,
.practice-modern-card,
.qa-modern-page :deep(.ai-content-card),
.empty {
  border: 1px solid rgba(226, 232, 240, 0.72);
}

.page-title-row,
.section-head,
.home-ac-header,
.student-plan-page .card-header,
.quiz-modern-header,
.profile-tabs,
.modal-head,
.drawer-head {
  min-width: 0;
}

.page-title-row {
  flex-wrap: wrap;
}

.page-title-actions,
.home-ai-rec-footer,
.home-ac-meta,
.course-meta,
.mini-data,
.quick-tags,
.practice-chapter-chips,
.quiz-modern-tabs,
.profile-tabs,
.notice-settings-grid .toggle-line,
.join-modal footer,
.complete-modal footer {
  flex-wrap: wrap;
}

.home-task-title,
.home-course strong,
.continue-card h2,
.student-course-card h2,
.student-course-card p,
.lesson-item strong,
.lesson-item small,
.material-row strong,
.material-row small,
.qa-mini strong,
.qa-mini p,
.practice-history-left strong,
.practice-history-left small,
.student-plan-page .plan-task-body strong,
.student-plan-page .plan-task-body small,
.profile-header-info p,
.notice-item strong,
.notice-item p,
.user-card small,
.history-row span,
.qa-attachment-chip span {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
}

.home-task-info,
.home-ac-content-wrap,
.student-course-card section,
.lesson-item > div,
.material-row > div,
.practice-history-left > div,
.profile-header-info section,
.notice-item > div,
.qa-mini,
.wrong-card,
.quiz-card {
  min-width: 0;
}

.student-course-card p,
.course-hero-student p,
.course-hero-student div,
.home-ac-meta,
.student-plan-page .card-header,
.profile-header-info p {
  align-items: flex-start;
}

.course-hero-student p,
.course-hero-student div {
  flex-wrap: wrap;
  color: rgba(255, 255, 255, 0.92);
}

.course-art {
  isolation: isolate;
}

.course-art .dropdown-menu {
  z-index: calc(var(--z-popover, 1000) + 5);
}

.course-art .dropdown-pop,
.select-pop,
.dropdown-pop,
.notice-pop,
.user-pop,
.settings-pop,
.qa-modern-page .history-drawer {
  z-index: calc(var(--z-popover, 1000) + 20);
  overflow: visible;
}

.select-pop button,
.dropdown-pop button,
.user-pop button,
.settings-pop button {
  justify-content: flex-start;
  min-height: 38px;
  line-height: 1.35;
}

.select-pop button:hover,
.select-pop button.active,
.dropdown-pop button:hover,
.dropdown-pop button.active,
.user-pop button:hover,
.settings-pop button:hover,
.settings-pop button.active {
  background: var(--s-primary-50, #EEF2FF);
  color: var(--s-primary-600, #4F46E5);
}

.top-icon:hover,
.avatar-btn:hover,
.student-nav-link:hover,
.underline-tabs button:hover:not(.active),
.seg-tabs button:hover:not(.active),
.profile-tabs button:hover:not(.active),
.study-tabs button:hover:not(.active),
.segmented button:hover:not(.active),
.home-refresh-btn:hover,
.home-ac-view-all:hover,
.quick-tile:hover,
.lesson-item:hover,
.material-row:hover,
.knowledge-tree button:hover,
.wrong-tree button:hover,
.student-plan-page .cal-day:hover:not(:disabled),
.student-plan-page .plan-task-check:hover:not(:disabled),
.practice-chip:hover:not(.active):not(:disabled),
.practice-segmented-control button:hover:not(.active):not(:disabled) {
  filter: none;
}

.bottom-tabs {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.bottom-tabs button {
  min-width: 0;
  line-height: 1.2;
}

.bottom-tabs .ai span {
  flex: 0 0 auto;
}

.empty,
.home-activity-empty,
.quiz-modern-page .empty,
.exam-empty-shell .empty {
  color: var(--s-muted, #64748B);
  line-height: 1.55;
}

.qa-modern-page {
  padding-bottom: 196px;
}

.qa-modern-page .qa-title p,
.qa-modern-page .qa-welcome p {
  color: var(--qa-secondary);
}

.qa-modern-page .qa-tutoring-link {
  background: var(--qa-ai-gradient);
}

.qa-modern-page .history-row {
  grid-template-columns: auto minmax(0, 1fr);
  border: 1px solid transparent;
}

.qa-modern-page .history-row:hover {
  border-color: var(--qa-primary-100);
}

.qa-modern-page .history-row span {
  white-space: normal;
}

.qa-modern-page .prompt-grid button {
  justify-content: center;
  min-width: min(240px, 100%);
  max-width: 100%;
  white-space: normal;
  line-height: 1.45;
  padding-block: 10px;
}

.qa-modern-page :deep(.message-row),
.class-chat :deep(.chat-msg) {
  min-width: 0;
}

.qa-modern-page :deep(.bubble-user),
.qa-modern-page :deep(.bubble-ai),
.class-chat :deep(.chat-bubble) {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: normal;
}

.qa-modern-page :deep(.ai-content-card) {
  min-width: 0;
  overflow: visible;
}

.qa-modern-page :deep(.markdown-body),
.class-chat :deep(.markdown-body),
.lesson-markdown {
  color: inherit;
  line-height: 1.75;
}

.qa-modern-page :deep(.markdown-body table),
.class-chat :deep(.markdown-body table),
.lesson-markdown :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
}

.qa-modern-page :deep(.ai-action-bar),
.qa-modern-page :deep(.msg-actions),
.class-chat :deep(.msg-actions) {
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.qa-modern-page :deep(.ai-action-btn),
.qa-modern-page :deep(.msg-actions button),
.class-chat :deep(.msg-actions button) {
  width: auto;
  min-width: 72px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: #F8FAFC;
  color: #475569;
  line-height: 1.2;
  white-space: nowrap;
}

.qa-modern-page :deep(.ai-action-btn:hover:not(:disabled)),
.qa-modern-page :deep(.msg-actions button:hover:not(:disabled)),
.class-chat :deep(.msg-actions button:hover:not(:disabled)) {
  border-color: #E0E7FF;
  background: #EEF2FF;
  color: #4F46E5;
}

.qa-modern-page .input-box {
  min-width: 0;
}

.qa-modern-page .input-box textarea {
  min-width: 0;
}

.qa-attachment-strip {
  max-width: 100%;
}

.qa-attachment-chip {
  max-width: min(260px, 100%);
}

.qa-attachment-chip button {
  min-width: 22px;
}

.class-chat {
  min-height: 0;
}

.class-chat-scroll {
  min-height: 180px;
}

.class-chat-dock .quick-tags button {
  white-space: nowrap;
}

.student-plan-page .cal-weekdays,
.student-plan-page .cal-grid {
  align-items: center;
}

.student-plan-page .cal-grid {
  grid-auto-rows: 48px;
}

.student-plan-page .cal-day-wrapper {
  min-height: 48px;
}

.student-plan-page .plan-task-row {
  grid-template-columns: 42px minmax(0, 1fr) auto;
}

.student-plan-page .plan-task-body strong {
  white-space: normal;
}

.profile-page {
  max-width: none;
}

.profile-header-info p {
  word-break: normal;
  overflow-wrap: anywhere;
}

.profile-form-grid label,
.profile-form-grid .password-field,
.notice-settings-grid .toggle-line {
  min-width: 0;
}

.study-room button:focus-visible,
.study-room input:focus-visible,
.study-room textarea:focus-visible,
.study-room .glass-btn:focus-visible,
.study-room .icon-glass:focus-visible,
.study-room .round-btn:focus-visible,
.study-room .thumb-grid button:focus-visible,
.study-room .study-tabs button:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 4px rgba(129, 140, 248, 0.35);
}

.study-head {
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
}

.study-head > div,
.study-head span,
.study-head strong {
  min-width: 0;
}

.study-head strong,
.study-head span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slide-card {
  max-height: calc(100vh - 204px);
}

.slide-content {
  max-height: none;
  overflow-y: auto;
  overflow-x: hidden;
}

.subtitle-line {
  flex: 0 0 auto;
  border-radius: 14px;
}

.player-bar {
  flex: 0 0 auto;
  margin-top: 0;
}

.player-bar button:hover:not(:disabled),
.glass-btn:hover:not(:disabled),
.icon-glass:hover:not(:disabled),
.thumb-grid button:hover:not(:disabled),
.settings-pop button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.lesson-ai {
  min-width: 0;
}

.study-tabs {
  overflow-x: auto;
  scrollbar-width: none;
}

.study-tabs::-webkit-scrollbar {
  display: none;
}

.study-tabs button {
  white-space: nowrap;
}

.script-view,
.class-chat,
.note-view {
  scrollbar-gutter: stable;
}

.study-room .player-bar {
  overflow: visible;
}

.study-room .player-bar .popover-button.select-menu {
  width: 78px;
  overflow: visible;
}

.study-room .player-bar .popover-button.select-menu > button {
  min-height: 38px;
  justify-content: center;
  border-color: rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  background: #fff;
  color: var(--color-text-primary);
  font-weight: 700;
  padding: 0 10px;
}

.study-room .player-bar .popover-button.select-menu > button:hover {
  border-color: var(--color-primary-200);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.study-room .player-bar .popover-button.select-menu .select-pop {
  top: auto;
  right: 0;
  bottom: calc(100% + 10px);
  min-width: 96px;
  transform-origin: bottom center;
  border-radius: 14px;
  padding: 8px;
}

.study-room .player-bar .popover-button.select-menu .select-pop::after {
  content: "";
  position: absolute;
  right: 28px;
  bottom: -6px;
  width: 12px;
  height: 12px;
  border-right: 1px solid rgba(226, 232, 240, 0.9);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
  transform: rotate(45deg);
}

.study-room .study-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: auto;
  gap: 6px;
  border: 0;
  border-bottom: 1px solid var(--color-border-default);
  border-radius: 0;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: none;
  padding: 10px 12px;
}

.study-room .study-tabs button {
  min-width: 0;
  min-height: 38px;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 12px;
  color: var(--color-text-secondary);
  font-weight: 700;
  padding: 0 10px;
}

.study-room .study-tabs button:hover:not(.active) {
  border-color: var(--color-border-default);
  background: white;
  color: var(--color-text-primary);
}

.study-room .study-tabs button.active {
  border-color: var(--color-primary-100);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.08);
}

.study-room .note-view {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 14px;
  height: 100%;
  overflow: hidden;
  background: #F8FAFC;
  padding: 18px;
}

.study-room .note-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--color-border-default);
  border-radius: 16px;
  background: white;
  box-shadow: var(--shadow-xs);
  padding: 8px;
}

.study-room .note-tools button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-weight: 700;
  padding: 0 12px;
}

.study-room .note-tools button:hover {
  border-color: var(--color-primary-200);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.study-room .note-tools button:active {
  transform: scale(0.96);
}

.study-room .note-state {
  margin-left: auto;
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  border-radius: var(--radius-full);
  background: var(--color-success-50);
  color: var(--color-success-700);
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
}

.study-room .note-state.dirty {
  background: var(--color-warning-50);
  color: var(--color-warning-700);
}

.study-room .note-editor {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--color-border-default);
  border-radius: 18px;
  outline: none;
  resize: none;
  background: white;
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
  font-size: 15px;
  line-height: 1.8;
  padding: 18px;
}

.study-room .note-editor:focus {
  border-color: var(--color-primary-300);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.14), var(--shadow-sm);
}

.study-room .note-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text-muted);
}

.study-room .note-footer .btn-primary {
  min-width: 104px;
  border: 1px solid var(--color-primary-600) !important;
  background: var(--color-primary-600) !important;
  color: #fff !important;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.24);
}

.study-room .note-footer .btn-primary:hover:not(:disabled) {
  border-color: var(--color-primary-500) !important;
  background: var(--color-primary-500) !important;
  color: #fff !important;
  transform: translateY(-1px);
}

.study-room .note-footer .btn-primary:disabled,
.study-room .note-footer .btn-primary[data-loading="true"] {
  border-color: var(--color-primary-300) !important;
  background: var(--color-primary-300) !important;
  color: #fff !important;
  cursor: wait;
  opacity: 0.9;
}

.study-room .note-footer > span {
  color: var(--color-text-secondary);
  font-size: 12px;
}

@media (max-width: 1180px) {
  .student-top {
    grid-template-columns: minmax(160px, 1fr) auto;
  }

  .student-nav-links {
    display: none;
  }

  .home-grid,
  .course-layout,
  .tutoring-grid,
  .knowledge-layout,
  .wrong-layout,
  .practice-modern-grid,
  .profile-pc-layout,
  .student-plan-page .plan-layout {
    grid-template-columns: 1fr;
  }

  .course-layout > aside {
    min-width: 0;
  }

  .knowledge-tree,
  .wrong-tree {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }
}

@media (max-width: 760px) {
  .student-main {
    padding: 24px 16px 96px;
  }

  .student-course-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .student-page {
    gap: 24px;
  }

  .hello-card,
  .home-ai-recommend-card,
  .home-activity-card,
  .student-plan-page .plan-banner,
  .student-plan-page .card,
  .panel-card,
  .profile-main-card,
  .practice-modern-card {
    padding: 22px;
  }

  .course-tools,
  .wrong-tools {
    grid-template-columns: 1fr;
  }

  .today-plan,
  .student-plan-page .plan-task-row {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .today-plan > .app-progress,
  .today-plan > button,
  .student-plan-page .plan-task-tag {
    grid-column: 2;
  }

  .profile-tabs,
  .underline-tabs,
  .seg-tabs,
  .quiz-modern-tabs {
    width: 100%;
    overflow-x: auto;
  }

  .profile-tabs button,
  .underline-tabs button,
  .seg-tabs button,
  .quiz-modern-tabs button {
    flex: 1 0 auto;
  }

  .qa-modern-page .input-box {
    gap: 10px;
    padding: 12px;
  }

  .qa-modern-page .qa-header-actions {
    width: 100%;
  }

  .qa-modern-page .qa-header-actions > * {
    flex: 1 1 auto;
  }

  .qa-modern-page .action-circle-btn {
    flex: 0 0 40px;
  }

  .student-plan-page .ai-prompt-bar {
    border-radius: var(--plan-radius-lg);
  }
}

/* Tutoring page rebuild: clear hierarchy for problem input, OCR upload, guided hints and history. */
.tutoring-page {
  --tutor-primary-50: #EEF2FF;
  --tutor-primary-100: #E0E7FF;
  --tutor-primary-500: #6366F1;
  --tutor-primary-600: #4F46E5;
  --tutor-ai-main: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --tutor-ai-light: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  --tutor-success-50: #ECFDF5;
  --tutor-success-600: #059669;
  --tutor-warning-50: #FFFBEB;
  --tutor-warning-600: #D97706;
  --tutor-card: #FFFFFF;
  --tutor-muted: #F8FAFC;
  --tutor-border: #E2E8F0;
  --tutor-text: #1E293B;
  --tutor-secondary: #64748B;
  --tutor-hint: #94A3B8;
  --tutor-radius-lg: 16px;
  --tutor-radius-xl: 24px;
  --tutor-pill: 9999px;
  --tutor-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.05);
  --tutor-shadow-focus: 0 0 0 4px rgba(79, 70, 229, 0.15);
  display: grid;
  gap: 28px;
  width: 100%;
  color: var(--tutor-text);
}

.tutoring-page .page-title-row {
  margin-bottom: 0;
}

.tutoring-page .page-title-actions {
  align-items: center;
}

.tutoring-page .course-select .select-menu > button,
.tutoring-page .select-menu-empty {
  min-height: 42px;
  border: 1px solid var(--tutor-border);
  border-radius: var(--tutor-pill);
  background: white;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.035);
  padding: 0 16px;
}

.tutoring-page .tutoring-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(420px, 0.88fr);
  gap: 28px;
  align-items: start;
}

.tutoring-page .tutor-input,
.tutoring-page .guide-card {
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: var(--tutor-radius-xl);
  background: var(--tutor-card);
  box-shadow: var(--tutor-shadow-card);
  padding: 30px;
}

.tutoring-page .tutor-input {
  display: grid;
  gap: 20px;
}

.tutor-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.tutor-card-head h2 {
  margin: 4px 0 0;
  color: var(--tutor-text);
  font-size: 24px;
  line-height: 1.25;
  font-weight: 800;
}

.tutor-eyebrow,
.tutor-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--tutor-hint);
  font-size: 13px;
  font-weight: 800;
}

.tutor-status {
  flex: 0 0 auto;
  border-radius: var(--tutor-pill);
  background: var(--tutor-muted);
  color: var(--tutor-secondary);
  padding: 6px 12px;
}

.tutor-status.active {
  background: var(--tutor-success-50);
  color: var(--tutor-success-600);
}

.tutoring-page .tutor-mode-tabs {
  width: fit-content;
  display: inline-flex;
  gap: 6px;
  border: 0;
  border-radius: var(--tutor-pill);
  background: var(--tutor-muted);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.8);
  padding: 6px;
}

.tutoring-page .tutor-mode-tabs button {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: var(--tutor-pill);
  background: transparent;
  color: var(--tutor-secondary);
  padding: 0 18px;
  font-weight: 800;
}

.tutoring-page .tutor-mode-tabs button:hover:not(.active) {
  background: rgba(255, 255, 255, 0.72);
  color: var(--tutor-primary-600);
}

.tutoring-page .tutor-mode-tabs button.active {
  background: white;
  color: var(--tutor-primary-600);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}

.problem-editor-wrap {
  display: grid;
  min-height: 260px;
}

.tutoring-page .problem-text {
  width: 100%;
  min-height: 260px;
  border: 1px solid var(--tutor-border);
  border-radius: var(--tutor-radius-lg);
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(255, 255, 255, 1)),
    white;
  color: var(--tutor-text);
  box-shadow: none;
  padding: 18px 20px;
  resize: vertical;
  font-size: 16px;
  line-height: 1.75;
}

.tutoring-page .problem-text::placeholder {
  color: var(--tutor-hint);
}

.tutoring-page .problem-text:hover {
  border-color: var(--tutor-primary-100);
}

.tutoring-page .problem-text:focus {
  border-color: var(--tutor-primary-500);
  box-shadow: var(--tutor-shadow-focus);
}

.tutoring-page .image-drop {
  position: relative;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  border: 2px dashed #CBD5E1;
  border-radius: var(--tutor-radius-lg);
  background:
    radial-gradient(circle at 18% 18%, rgba(99, 102, 241, 0.08), transparent 32%),
    linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  color: var(--tutor-secondary);
  cursor: pointer;
  text-align: center;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.tutoring-page .image-drop:hover {
  border-color: var(--tutor-primary-500);
  background: #FFFFFF;
  box-shadow: 0 12px 32px rgba(79, 70, 229, 0.10);
  transform: translateY(-1px);
}

.tutoring-page .image-drop input {
  display: none;
}

.tutoring-page .image-drop .upload-icon {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border-radius: 22px;
  background: var(--tutor-ai-light);
  color: #8B5CF6;
  box-shadow: 0 12px 24px rgba(139, 92, 246, 0.15);
}

.tutoring-page .image-drop strong {
  color: var(--tutor-text);
  font-size: 20px;
  font-weight: 800;
}

.tutoring-page .image-drop small {
  max-width: 320px;
  color: var(--tutor-secondary);
  line-height: 1.6;
}

.tutoring-page .image-drop.ocr-scanning {
  pointer-events: none;
  border-color: var(--tutor-primary-500);
  background: var(--tutor-primary-50);
}

.tutoring-page .image-drop.ocr-scanning .upload-icon {
  animation: tutor-pulse 1.2s ease-in-out infinite;
}

.tutor-input-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--tutor-hint);
  font-size: 13px;
  font-weight: 700;
}

.tutoring-page .knowledge-box {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid rgba(221, 214, 254, 0.82);
  border-radius: var(--tutor-radius-lg);
  background: var(--tutor-ai-light);
  color: #6D28D9;
  padding: 12px 14px;
}

.tutoring-page .knowledge-box strong {
  margin-right: 2px;
  font-size: 13px;
}

.tutoring-page .tutor-submit-btn {
  min-height: 52px;
  border-radius: var(--tutor-pill);
  background: var(--tutor-ai-main);
  color: white;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.28);
  font-size: 15px;
  font-weight: 900;
}

.tutoring-page .tutor-submit-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(139, 92, 246, 0.34);
}

.tutoring-page .guide-card {
  display: grid;
  gap: 18px;
}

.tutoring-page .guide-card .section-head {
  margin: 0;
}

.tutoring-page .active-problem-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--tutor-border);
  border-radius: var(--tutor-radius-lg);
  background: var(--tutor-muted);
  padding: 16px;
}

.tutoring-page .active-problem-card span {
  color: var(--tutor-hint);
  font-size: 12px;
  font-weight: 900;
}

.tutoring-page .active-problem-card p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  margin: 0;
  color: var(--tutor-text);
  line-height: 1.7;
}

.guide-step-list {
  display: grid;
  gap: 14px;
}

.tutoring-page .guide-step {
  overflow: hidden;
  border: 1px solid var(--tutor-border);
  border-radius: var(--tutor-radius-lg);
  background: white;
  box-shadow: none;
}

.tutoring-page .guide-step:hover {
  border-color: var(--tutor-primary-100);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.tutoring-page .guide-step > button {
  width: 100%;
  min-height: 58px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 0;
  border-radius: 0;
  background: #FFFFFF;
  color: var(--tutor-text);
  padding: 0 16px;
  text-align: left;
}

.tutoring-page .guide-step > button:hover {
  background: var(--tutor-primary-50);
}

.tutoring-page .guide-step b {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--tutor-primary-600);
  color: white;
  font-size: 14px;
  font-weight: 900;
}

.tutoring-page .guide-step strong {
  flex: 1;
  min-width: 0;
  color: var(--tutor-text);
  font-size: 15px;
}

.tutoring-page .guide-step svg:last-child {
  color: var(--tutor-hint);
  transition: transform var(--duration-fast) var(--ease-out);
}

.tutoring-page .guide-step .rotate {
  transform: rotate(180deg);
}

.tutoring-page .guide-body {
  display: grid;
  gap: 12px;
  border-top: 1px solid var(--tutor-border);
  background: var(--tutor-muted);
  color: var(--tutor-secondary);
  padding: 16px 18px;
  line-height: 1.75;
}

.tutoring-page .guide-body p {
  margin: 0;
}

.tutoring-page .guide-body ol {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}

.tutoring-page .guide-body strong {
  display: block;
  border-radius: 12px;
  background: var(--tutor-success-50);
  color: var(--tutor-success-600);
  padding: 10px 12px;
}

.tutoring-page .empty-guide {
  min-height: 330px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
  border: 1px dashed #CBD5E1;
  border-radius: var(--tutor-radius-lg);
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  color: var(--tutor-secondary);
  text-align: center;
  padding: 32px;
}

.tutoring-page .empty-guide svg {
  width: 68px;
  height: 68px;
  border-radius: 22px;
  background: var(--tutor-ai-light);
  color: #8B5CF6;
  padding: 16px;
}

.tutoring-page .empty-guide strong {
  color: var(--tutor-text);
  font-size: 22px;
  font-weight: 900;
}

.tutoring-page .empty-guide span {
  color: var(--tutor-secondary);
}

/* Targeted fixes for QA, courses, course detail, and rebuilt tutoring history. */
.qa-modern-page .qa-header-actions {
  position: relative;
  z-index: 6;
}

.qa-modern-page .qa-tutoring-link svg {
  width: 13px !important;
  height: 13px !important;
  flex: 0 0 13px;
  background: transparent !important;
  color: currentColor;
  box-shadow: none !important;
  padding: 0 !important;
}

.qa-modern-page .action-circle-btn {
  pointer-events: auto;
}

.qa-modern-page .action-circle-btn.active {
  border-color: var(--qa-primary-100);
  background: var(--qa-primary-50);
  color: var(--qa-primary-600);
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.14);
}

.qa-modern-page .history-drawer {
  z-index: calc(var(--z-modal, 1200) + 10);
}

.course-art em {
  top: 16px;
  right: 16px;
  bottom: auto;
}

.course-art .dropdown-menu {
  top: auto;
  right: 16px;
  bottom: 16px;
}

.course-art .dropdown-pop {
  top: auto;
  right: 0;
  bottom: calc(100% + 8px);
}

.course-layout > aside {
  display: grid;
  gap: 22px;
}

.course-layout > aside .ask-card,
.course-layout > aside .recent-qa-card {
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-left: 0;
  border-radius: var(--s-radius-lg);
  background: #FFFFFF;
  box-shadow: var(--s-shadow-card);
  padding: 24px;
}

.course-layout > aside .ask-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.course-layout > aside .ask-card > svg {
  display: none;
}

.course-layout > aside .ask-card h2 {
  margin: 0;
  color: var(--s-text);
  font-size: 19px;
  line-height: 1.3;
  font-weight: 900;
}

.course-layout > aside .ask-card form {
  min-height: 48px;
  border-radius: 16px;
}

.course-layout > aside .ask-card .quick-tags {
  margin: 0;
}

.course-layout > aside .recent-qa-card {
  display: grid;
  gap: 12px;
}

.course-layout > aside .recent-qa-card .section-head {
  margin: 0 0 4px;
}

.course-layout > aside .qa-mini {
  display: grid;
  gap: 6px;
  border: 1px solid var(--s-border);
  border-radius: 14px;
  background: var(--s-bg);
  padding: 12px 14px;
}

.course-layout > aside .qa-mini strong,
.course-layout > aside .qa-mini p {
  margin: 0;
  line-height: 1.55;
}

.course-layout > aside .qa-mini p {
  color: var(--s-muted);
}

.tutoring-page .tutor-card-head,
.tutoring-page .guide-card .section-head {
  min-height: 64px;
}

.tutoring-page .guide-card .section-head {
  align-items: flex-start;
  padding-top: 2px;
}

.tutoring-history-card {
  display: grid;
  gap: 18px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: var(--tutor-radius-xl, 24px);
  background: #FFFFFF;
  box-shadow: var(--tutor-shadow-card, 0 12px 32px rgba(15, 23, 42, 0.05));
  padding: 26px;
}

.tutoring-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.tutoring-history-head h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  color: var(--tutor-text, #1E293B);
  font-size: 20px;
  line-height: 1.3;
  font-weight: 900;
}

.tutoring-history-head svg {
  color: var(--tutor-primary-600, #4F46E5);
}

.tutoring-history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}

.tutoring-history-item {
  min-height: 112px;
  display: grid;
  align-content: space-between;
  gap: 12px;
  border: 1px solid var(--tutor-border, #E2E8F0);
  border-radius: var(--tutor-radius-lg, 16px);
  background: var(--tutor-muted, #F8FAFC);
  color: var(--tutor-text, #1E293B);
  padding: 16px;
  text-align: left;
  transition:
    transform var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}

.tutoring-history-item:hover {
  border-color: var(--tutor-primary-100, #E0E7FF);
  background: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  transform: translateY(-2px);
}

.tutoring-history-item:active {
  transform: translateY(0) scale(0.985);
}

.tutoring-history-item strong {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  color: var(--tutor-text, #1E293B);
  line-height: 1.55;
}

.tutoring-history-item small {
  color: var(--tutor-hint, #94A3B8);
  font-weight: 800;
}

.practice-generate-hint:empty {
  display: none;
}

@media (max-width: 1180px) {
  .tutoring-page .tutoring-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .tutoring-page {
    gap: 22px;
  }

  .tutoring-page .tutor-input,
  .tutoring-page .guide-card {
    padding: 22px;
  }

  .tutor-card-head,
  .tutoring-page .guide-card .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .tutoring-page .tutor-mode-tabs {
    width: 100%;
  }

  .tutoring-page .tutor-mode-tabs button {
    flex: 1;
    padding: 0 10px;
  }

  .problem-editor-wrap,
  .tutoring-page .problem-text,
  .tutoring-page .image-drop {
    min-height: 220px;
  }

  .tutoring-history-grid {
    grid-template-columns: 1fr;
  }
}

@keyframes tutor-pulse {
  0%, 100% { transform: scale(1); box-shadow: 0 12px 24px rgba(139, 92, 246, 0.15); }
  50% { transform: scale(1.04); box-shadow: 0 18px 32px rgba(139, 92, 246, 0.24); }
}

@keyframes student-audit-spin {
  to { transform: rotate(360deg); }
}
</style>

<style>
/* /quizzes must be global because QuizAnswerView and quiz cards are render-function child components. */
.empty {
  min-height: 132px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  border: 1px dashed #CBD5E1;
  border-radius: 16px;
  background: #FFFFFF;
  color: #94A3B8;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
  padding: 28px;
  text-align: center;
}

.empty svg {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: #F8FAFC;
  color: #94A3B8;
  padding: 8px;
}

.empty span {
  color: #64748B;
  font-size: 14px;
  font-weight: 700;
}

.quiz-modern-page .empty {
  min-height: 180px;
  border-color: rgba(99, 102, 241, 0.18);
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
}

.quiz-modern-page {
  --quiz-primary-50: #EEF2FF;
  --quiz-primary-100: #E0E7FF;
  --quiz-primary-500: #6366F1;
  --quiz-primary-600: #5A67D8;
  --quiz-ai-main: linear-gradient(135deg, #06B6D4 0%, #8B5CF6 100%);
  --quiz-ai-light: linear-gradient(135deg, #F0F9FF 0%, #F5F3FF 100%);
  --quiz-bg: #F4F6F9;
  --quiz-surface: #FFFFFF;
  --quiz-muted: #F8FAFC;
  --quiz-border: #E2E8F0;
  --quiz-text: #1E293B;
  --quiz-secondary: #64748B;
  --quiz-hint: #94A3B8;
  --quiz-radius-lg: 16px;
  --quiz-radius-xl: 24px;
  --quiz-pill: 9999px;
  --quiz-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --quiz-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.04);
  display: grid;
  gap: 32px;
}

.quiz-modern-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.quiz-modern-title h1 {
  margin: 0 0 8px;
  color: var(--quiz-text);
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0;
}

.quiz-modern-title p {
  margin: 0;
  color: var(--quiz-secondary);
  font-size: 15px;
}

.quiz-modern-tabs {
  display: flex;
  gap: 12px;
}

.quiz-modern-tabs button,
.practice-segmented-control button,
.practice-chip,
.practice-switch-wrapper,
.practice-generate-btn,
.practice-feature-card,
.practice-history-item,
.quiz-card {
  font-family: inherit;
  transition: all 0.2s ease;
}

.quiz-modern-tabs button {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: transparent;
  color: var(--quiz-secondary);
  padding: 0 24px;
  font-size: 15px;
  font-weight: 700;
}

.quiz-modern-tabs button:hover {
  background: rgba(255, 255, 255, 0.5);
}

.quiz-modern-tabs button.active {
  background: white;
  color: var(--quiz-primary-600);
  box-shadow: var(--quiz-shadow-sm);
}

.practice-modern-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 32px;
}

.practice-modern-card {
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--quiz-radius-xl);
  background: white;
  box-shadow: var(--quiz-shadow-card);
  padding: 32px;
}

.practice-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.practice-card-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--quiz-ai-light);
  color: #8B5CF6;
}

.practice-card-header h2,
.practice-history-title {
  margin: 0;
  color: var(--quiz-text);
  font-size: 20px;
  font-weight: 800;
}

.practice-config-section {
  margin-bottom: 32px;
}

.practice-config-label {
  display: block;
  margin-bottom: 16px;
  color: var(--quiz-text);
  font-size: 14px;
  font-weight: 700;
}

.practice-chapter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.practice-chip {
  min-height: 40px;
  border: 1px solid transparent;
  border-radius: var(--quiz-pill);
  background: var(--quiz-muted);
  color: var(--quiz-secondary);
  padding: 0 20px;
  font-size: 14px;
  font-weight: 700;
}

.practice-chip:hover {
  background: #E2E8F0;
}

.practice-chip.active {
  border-color: var(--quiz-primary-500);
  background: var(--quiz-primary-50);
  color: var(--quiz-primary-600);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.10);
}

.practice-settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: var(--quiz-pill);
  background: var(--quiz-muted);
  padding: 8px 16px 8px 8px;
}

.practice-segmented-control {
  display: flex;
  gap: 4px;
}

.practice-segmented-control button {
  min-height: 36px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: transparent;
  color: var(--quiz-secondary);
  padding: 0 24px;
  font-size: 14px;
  font-weight: 700;
}

.practice-segmented-control button.active {
  background: white;
  color: var(--quiz-primary-600);
  box-shadow: var(--quiz-shadow-sm);
}

.practice-switch-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: transparent;
  color: var(--quiz-text);
  font-weight: 700;
}

.practice-switch {
  position: relative;
  width: 44px;
  height: 24px;
  flex: 0 0 auto;
  border-radius: var(--quiz-pill);
  background: var(--quiz-border);
}

.practice-switch::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  box-shadow: var(--quiz-shadow-sm);
  transition: transform 0.2s ease;
}

.practice-switch-wrapper.active .practice-switch {
  background: var(--quiz-primary-600);
}

.practice-switch-wrapper.active .practice-switch::after {
  transform: translateX(20px);
}

.practice-generate-btn {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 40px;
  border: 0;
  border-radius: var(--quiz-pill);
  background: var(--quiz-ai-main);
  color: white;
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.30);
  font-size: 16px;
  font-weight: 800;
}

.practice-generate-btn:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(139, 92, 246, 0.40);
}

.practice-generate-hint {
  margin: 12px 0 0;
  color: var(--quiz-hint);
  text-align: center;
  font-size: 13px;
}

.practice-feature-card {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 32px;
  border: 1px solid #FEF08A;
  border-radius: var(--quiz-radius-lg);
  background: linear-gradient(to right, #FFF7ED, #FEFCE8);
  padding: 24px;
  text-align: left;
}

.practice-feature-card:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(245, 158, 11, 0.14);
}

.practice-feature-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  margin-bottom: 12px;
  border-radius: 12px;
  background: white;
  color: #F59E0B;
  box-shadow: var(--quiz-shadow-sm);
}

.practice-feature-card h2 {
  margin: 0 0 4px;
  color: #B45309;
  font-size: 18px;
  font-weight: 800;
}

.practice-feature-card p {
  margin: 0;
  color: #A16207;
  font-size: 13px;
}

.practice-feature-card > span {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--quiz-pill);
  background: #F59E0B;
  color: white;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.20);
  padding: 0 24px;
  font-weight: 800;
}

.practice-history-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 15px;
}

.practice-history-title svg {
  color: var(--quiz-primary-500);
}

.practice-history-list,
.quiz-modern-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.practice-history-item,
.quiz-card {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--quiz-border);
  border-radius: var(--quiz-radius-lg);
  background: white;
  box-shadow: var(--quiz-shadow-sm);
  padding: 16px;
  text-align: left;
}

.practice-history-item:hover,
.quiz-card:hover {
  border-color: #CBD5E1;
  background: var(--quiz-muted);
  transform: translateY(-1px);
}

.practice-history-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 16px;
}

.practice-history-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 10px;
  background: var(--quiz-primary-50);
  color: var(--quiz-primary-600);
}

.practice-history-left strong,
.quiz-card h2 {
  display: block;
  margin: 0;
  overflow: hidden;
  color: var(--quiz-text);
  font-size: 15px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.practice-history-left small,
.quiz-card p {
  margin: 0;
  color: var(--quiz-hint);
  font-size: 12px;
}

.practice-history-item em {
  flex: 0 0 auto;
  color: var(--quiz-primary-600);
  font-style: normal;
  font-weight: 900;
}

.exam-answer-page {
  --exam-primary-50: #EEF2FF;
  --exam-primary-100: #E0E7FF;
  --exam-primary-400: #818CF8;
  --exam-primary-500: #6366F1;
  --exam-primary-600: #4F46E5;
  --exam-bg-page: #F4F6F9;
  --exam-bg-card: #FFFFFF;
  --exam-border-light: #F1F5F9;
  --exam-border-default: #E2E8F0;
  --exam-border-strong: #CBD5E1;
  --exam-text-main: #1E293B;
  --exam-text-sec: #64748B;
  --exam-text-hint: #94A3B8;
  --exam-radius-sm: 8px;
  --exam-radius-lg: 16px;
  --exam-radius-xl: 24px;
  --exam-radius-pill: 9999px;
  --exam-shadow-sm: 0 2px 8px rgba(15, 23, 42, 0.04);
  --exam-shadow-card: 0 12px 32px rgba(15, 23, 42, 0.05);
  --exam-shadow-focus: 0 0 0 4px rgba(79, 70, 229, 0.15);
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  background: var(--exam-bg-page);
  color: var(--exam-text-main);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
}

.exam-answer-page *,
.exam-answer-page *::before,
.exam-answer-page *::after {
  box-sizing: border-box;
}

.exam-answer-page button {
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  outline: 0;
  transition: all 0.2s ease;
}

.exam-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--exam-bg-page);
}

.exam-empty-shell {
  display: grid;
  place-items: center;
  padding: 32px;
}

.exam-empty-shell .empty {
  width: min(420px, calc(100vw - 48px));
  min-height: 260px;
  border: 1px solid white;
  border-radius: var(--exam-radius-xl);
  background: white;
  box-shadow: var(--exam-shadow-card);
}

.exam-empty-shell .empty svg {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
  padding: 12px;
}

.exam-empty-shell .empty span {
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 800;
}

.exam-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  border-bottom: 1px solid var(--exam-border-default);
  background: var(--exam-bg-card);
  box-shadow: var(--exam-shadow-sm);
  padding: 0 32px;
}

.exam-exit-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--exam-radius-pill);
  color: var(--exam-text-sec);
  padding: 8px 16px 8px 8px;
  font-size: 14px;
  font-weight: 700;
}

.exam-exit-btn:hover {
  background: var(--exam-bg-page);
  color: var(--exam-text-main);
}

.exam-title {
  position: absolute;
  left: 50%;
  max-width: min(560px, calc(100vw - 360px));
  overflow: hidden;
  transform: translateX(-50%);
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exam-answer-page .timer-widget {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--exam-primary-100);
  border-radius: var(--exam-radius-pill);
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
  padding: 6px 16px;
}

.exam-answer-page .timer-text {
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--exam-primary-600);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 1px;
}

.exam-container {
  flex: 1;
  display: flex;
  gap: 24px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  overflow-y: auto;
  padding: 24px 32px 96px;
}

.exam-nav-sidebar {
  width: 280px;
  flex: 0 0 280px;
}

.exam-nav-card,
.exam-q-card,
.exam-result-card,
.exam-result-summary,
.exam-analysis-card {
  border: 1px solid white;
  border-radius: var(--exam-radius-xl);
  background: var(--exam-bg-card);
  box-shadow: var(--exam-shadow-card);
  padding: 24px;
}

.exam-q-card {
  flex: 1;
  padding: 40px;
}

.exam-nav-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--exam-border-light);
  padding-bottom: 16px;
}

.exam-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.exam-stat-val {
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 800;
}

.exam-stat-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--exam-text-hint);
  font-size: 12px;
}

.exam-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.exam-dot-answered {
  background: var(--exam-primary-500);
}

.exam-dot-marked {
  background: #F59E0B;
}

.exam-dot-unanswered {
  border: 2px solid var(--exam-border-strong);
}

.exam-q-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.exam-q-btn {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-sm);
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 700;
}

.exam-q-btn:hover {
  border-color: var(--exam-primary-400);
  color: var(--exam-primary-600);
}

.exam-q-btn.answered {
  border-color: var(--exam-primary-100);
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
}

.exam-q-btn.current {
  border: 2px solid var(--exam-primary-600);
  background: white;
  color: var(--exam-primary-600);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.20);
}

.exam-q-btn.marked::after {
  content: "";
  position: absolute;
  top: -4px;
  right: -4px;
  width: 10px;
  height: 10px;
  border: 2px solid white;
  border-radius: 50%;
  background: #F59E0B;
}

.exam-question-area {
  flex: 1;
  display: flex;
  min-width: 0;
}

.exam-q-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.exam-q-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.exam-q-number {
  margin-right: 8px;
  color: var(--exam-text-main);
  font-size: 16px;
  font-weight: 900;
}

.exam-tag {
  border-radius: var(--exam-radius-pill);
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 700;
}

.exam-tag-type {
  background: var(--exam-primary-50);
  color: var(--exam-primary-600);
}

.exam-tag-diff {
  border: 1px solid var(--exam-border-default);
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
}

.exam-mark-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-pill);
  background: white;
  color: var(--exam-text-sec);
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 700;
}

.exam-mark-btn:hover,
.exam-mark-btn.is-marked {
  border-color: #FDE68A;
  background: #FFFBEB;
  color: #B45309;
}

.exam-mark-btn.is-marked svg {
  fill: #F59E0B;
  color: #F59E0B;
}

.exam-q-stem {
  margin-bottom: 32px;
  color: var(--exam-text-main);
  font-size: 18px;
  font-weight: 700;
  line-height: 1.6;
}

.exam-options-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-opt-label {
  position: relative;
  display: block;
  cursor: pointer;
}

.exam-opt-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}

.exam-opt-card {
  display: flex;
  align-items: center;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: var(--exam-bg-card);
  padding: 16px 20px;
  transition: all 0.2s ease;
}

.exam-opt-label:hover .exam-opt-card {
  border-color: var(--exam-primary-400);
  background: var(--exam-bg-page);
}

.exam-opt-letter {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 32px;
  margin-right: 16px;
  border: 1px solid var(--exam-border-default);
  border-radius: 50%;
  background: var(--exam-bg-page);
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 800;
}

.exam-opt-text {
  flex: 1;
  color: var(--exam-text-main);
  font-size: 15px;
  line-height: 1.5;
}

.exam-opt-input:checked + .exam-opt-card {
  border-color: var(--exam-primary-500);
  background: var(--exam-primary-50);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.10);
}

.exam-opt-input:checked + .exam-opt-card .exam-opt-letter {
  border-color: var(--exam-primary-600);
  background: var(--exam-primary-600);
  color: white;
}

.exam-opt-input:checked + .exam-opt-card .exam-opt-text {
  color: var(--exam-primary-600);
  font-weight: 600;
}

.exam-answer-input,
.exam-answer-textarea {
  width: 100%;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: white;
  color: var(--exam-text-main);
  padding: 14px 16px;
  font: inherit;
  outline: 0;
}

.exam-answer-input:focus,
.exam-answer-textarea:focus,
.exam-opt-input:focus-visible + .exam-opt-card,
.exam-q-btn:focus-visible,
.exam-mark-btn:focus-visible,
.exam-btn:focus-visible,
.exam-exit-btn:focus-visible,
.exam-analysis-trigger:focus-visible {
  outline: 0;
  border-color: var(--exam-primary-500);
  box-shadow: var(--exam-shadow-focus);
}

.exam-answer-textarea {
  min-height: 180px;
  resize: vertical;
}

.exam-text-answer {
  display: grid;
  gap: 8px;
}

.exam-text-answer small {
  justify-self: end;
  color: var(--exam-text-hint);
  font-size: 12px;
}

.exam-action-footer {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 100;
  height: 72px;
  display: flex;
  justify-content: center;
  border-top: 1px solid var(--exam-border-default);
  background: rgba(255, 255, 255, 0.90);
  backdrop-filter: blur(12px);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.03);
}

.exam-footer-container {
  width: 100%;
  max-width: 1200px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 32px;
}

.exam-footer-actions,
.exam-footer-progress {
  display: flex;
  align-items: center;
  gap: 16px;
}

.exam-btn {
  min-width: 112px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--exam-radius-pill);
  padding: 0 24px;
  font-size: 14px;
  font-weight: 800;
}

.exam-btn-outline {
  border: 1px solid var(--exam-border-strong) !important;
  background: white !important;
  color: var(--exam-text-main) !important;
}

.exam-btn-outline:hover:not(:disabled) {
  border-color: var(--exam-primary-500) !important;
  background: var(--exam-bg-page) !important;
  color: var(--exam-primary-600) !important;
}

.exam-btn-primary {
  background: var(--exam-primary-600) !important;
  color: white !important;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.30);
}

.exam-btn-primary:hover:not(:disabled) {
  background: var(--exam-primary-500) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.40);
}

.exam-prog-text {
  color: var(--exam-text-sec);
  font-size: 14px;
  font-weight: 800;
}

.exam-prog-bar {
  width: 120px;
  height: 6px;
  overflow: hidden;
  border-radius: 4px;
  background: var(--exam-border-default);
}

.exam-prog-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--exam-primary-500);
  transition: width 0.25s ease;
}

.exam-modal-mask {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-bg);
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(8px);
}

.exam-confirm-card {
  width: 440px;
  max-width: calc(100vw - 32px);
  border-radius: var(--exam-radius-xl);
  background: white;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
  padding: 22px;
}

.exam-modal-head,
.exam-analysis-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
}

.exam-modal-head h2 {
  flex: 1;
  margin: 0;
}

.exam-confirm-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.exam-result-main {
  flex: 1;
  display: grid;
  gap: 20px;
  width: min(900px, calc(100% - 48px));
  margin: 0 auto;
  overflow-y: auto;
  padding: 32px 0 48px;
}

.exam-result-card {
  display: grid;
  justify-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #4F46E5, #06B6D4);
  color: white;
  padding: 40px;
}

.exam-result-card strong {
  font-size: 56px;
  line-height: 1;
}

.exam-result-card em {
  border-radius: var(--exam-radius-pill);
  background: rgba(255, 255, 255, 0.18);
  padding: 4px 12px;
  font-style: normal;
  font-weight: 800;
}

.exam-result-summary h2,
.exam-analysis-head h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--exam-text-main);
  font-size: 20px;
}

.exam-result-summary p {
  margin: 12px 0 0;
  color: var(--exam-text-sec);
}

.exam-analysis-card {
  display: grid;
  gap: 12px;
}

.exam-analysis-item {
  overflow: hidden;
  border: 1px solid var(--exam-border-default);
  border-radius: var(--exam-radius-lg);
  background: white;
}

.exam-analysis-item.open {
  background: var(--exam-bg-page);
}

.exam-analysis-trigger {
  width: 100%;
  min-height: 48px;
  color: var(--exam-text-main);
  padding: 0 14px;
  text-align: left;
}

.exam-analysis-trigger span {
  margin-left: auto;
}

.exam-analysis-item.open .exam-analysis-trigger svg:last-child {
  transform: rotate(180deg);
}

.exam-analysis-body {
  display: grid;
  gap: 8px;
  border-top: 1px solid var(--exam-border-default);
  padding: 14px;
}

.exam-analysis-body p,
.exam-analysis-body small {
  margin: 0;
  color: var(--exam-text-sec);
}

@media (max-width: 900px) {
  .quiz-modern-header {
    display: grid;
    gap: 16px;
  }

  .practice-modern-grid {
    grid-template-columns: 1fr;
  }

  .practice-settings-row,
  .practice-feature-card {
    align-items: stretch;
    flex-direction: column;
    border-radius: var(--quiz-radius-lg);
  }

  .exam-header {
    height: auto;
    min-height: 64px;
    gap: 12px;
    padding: 12px 16px;
  }

  .exam-title {
    position: static;
    max-width: none;
    transform: none;
    font-size: 16px;
  }

  .exam-container {
    flex-direction: column;
    gap: 16px;
    padding: 16px 16px 104px;
  }

  .exam-nav-sidebar {
    width: 100%;
    flex-basis: auto;
  }

  .exam-q-grid {
    grid-template-columns: repeat(8, minmax(34px, 1fr));
    gap: 8px;
  }

  .exam-q-card {
    padding: 24px;
  }

  .exam-q-meta-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 16px;
  }

  .exam-footer-progress {
    display: none;
  }

  .exam-footer-container {
    gap: 10px;
    padding: 0 12px;
  }

  .exam-btn {
    min-width: 0;
    padding: 0 14px;
  }
}

/* Render-function UI audit overrides: QuizCard, WrongCard and QuizAnswerView. */
.quiz-modern-page,
.quiz-modern-page *,
.exam-answer-page,
.exam-answer-page * {
  box-sizing: border-box;
  writing-mode: horizontal-tb;
  text-orientation: mixed;
}

.quiz-modern-page h1,
.quiz-modern-page h2,
.quiz-modern-page p,
.quiz-modern-page strong,
.quiz-modern-page span,
.quiz-modern-page small,
.quiz-modern-page em,
.quiz-modern-page button,
.exam-answer-page h1,
.exam-answer-page h2,
.exam-answer-page p,
.exam-answer-page strong,
.exam-answer-page span,
.exam-answer-page small,
.exam-answer-page em,
.exam-answer-page button,
.exam-answer-page input,
.exam-answer-page textarea {
  letter-spacing: 0;
  word-break: normal;
  overflow-wrap: anywhere;
}

.quiz-modern-page {
  width: 100%;
  min-width: 0;
  align-items: stretch;
}

.quiz-modern-page > *,
.quiz-modern-list,
.practice-modern-grid,
.practice-modern-card,
.practice-history-list {
  min-width: 0;
}

.quiz-modern-header {
  min-width: 0;
  flex-wrap: wrap;
}

.quiz-modern-tabs {
  flex-wrap: wrap;
}

.quiz-modern-tabs button,
.practice-chip,
.practice-segmented-control button,
.practice-switch-wrapper,
.practice-generate-btn,
.practice-feature-card,
.practice-history-item,
.quiz-card,
.wrong-card {
  -webkit-tap-highlight-color: transparent;
}

.quiz-modern-tabs button:focus-visible,
.practice-chip:focus-visible,
.practice-segmented-control button:focus-visible,
.practice-switch-wrapper:focus-visible,
.practice-generate-btn:focus-visible,
.practice-feature-card:focus-visible,
.practice-history-item:focus-visible,
.quiz-card:focus-visible,
.wrong-card:focus-visible,
.exam-answer-page button:focus-visible,
.exam-answer-page input:focus-visible,
.exam-answer-page textarea:focus-visible,
.exam-opt-input:focus-visible + .exam-opt-card {
  outline: 0;
  border-color: var(--quiz-primary-500, var(--exam-primary-500, #6366F1)) !important;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.16) !important;
}

.quiz-modern-page button:not(:disabled):active,
.quiz-card:active,
.wrong-card:active,
.practice-history-item:active,
.practice-feature-card:active,
.exam-answer-page button:not(:disabled):active,
.exam-opt-label:active .exam-opt-card {
  transform: translateY(0) scale(0.985);
}

.quiz-modern-page button:disabled,
.exam-answer-page button:disabled,
.exam-answer-page input:disabled,
.exam-answer-page textarea:disabled {
  cursor: not-allowed !important;
  opacity: 0.56 !important;
  transform: none !important;
  box-shadow: none !important;
}

.quiz-modern-page button[data-loading="true"],
.exam-answer-page button[data-loading="true"] {
  position: relative;
  pointer-events: none;
  color: transparent !important;
}

.quiz-modern-page button[data-loading="true"] > *,
.exam-answer-page button[data-loading="true"] > * {
  opacity: 0;
}

.quiz-modern-page button[data-loading="true"]::after,
.exam-answer-page button[data-loading="true"]::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 18px;
  height: 18px;
  margin: -9px 0 0 -9px;
  border: 2px solid rgba(255, 255, 255, 0.55);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: render-audit-spin 0.8s linear infinite;
}

.exam-btn-outline[data-loading="true"]::after {
  border-color: rgba(79, 70, 229, 0.22);
  border-top-color: var(--exam-primary-600, #4F46E5);
}

.practice-modern-grid {
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.85fr);
  align-items: start;
}

.practice-modern-card,
.quiz-card,
.wrong-card,
.exam-nav-card,
.exam-q-card,
.exam-result-card,
.exam-result-summary,
.exam-analysis-card,
.exam-confirm-card,
.empty {
  border: 1px solid rgba(226, 232, 240, 0.72);
}

.quiz-modern-list,
.practice-history-list {
  display: grid;
  gap: 14px;
}

.quiz-card,
.wrong-card,
.practice-history-item {
  min-width: 0;
  align-items: flex-start;
}

.quiz-card,
.wrong-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px 18px;
  overflow: visible;
}

.quiz-card h2,
.wrong-card h2,
.quiz-card p,
.wrong-card p,
.practice-history-left strong,
.practice-history-left small {
  max-width: none;
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
}

.quiz-card h2,
.wrong-card h2 {
  line-height: 1.35;
}

.quiz-card p,
.wrong-card p {
  line-height: 1.55;
}

.quiz-card footer,
.wrong-card footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.practice-history-left {
  flex: 1 1 auto;
  min-width: 0;
  align-items: flex-start;
}

.practice-history-item em {
  align-self: center;
  white-space: nowrap;
}

.practice-feature-card {
  min-width: 0;
}

.practice-feature-card > div {
  min-width: 0;
}

.practice-feature-card > span {
  flex: 0 0 auto;
  white-space: nowrap;
}

.practice-settings-row,
.practice-segmented-control,
.practice-chapter-chips {
  flex-wrap: wrap;
}

.practice-switch-wrapper {
  min-height: 40px;
  border-radius: var(--quiz-pill, 9999px);
  padding: 0 8px;
}

.empty {
  width: 100%;
  color: #64748B;
  line-height: 1.55;
}

.empty span {
  max-width: 100%;
  color: #475569;
  overflow-wrap: anywhere;
}

.exam-answer-page {
  overflow: hidden;
}

.exam-shell {
  min-width: 0;
}

.exam-header {
  gap: 16px;
}

.exam-title {
  line-height: 1.35;
}

.exam-container {
  min-width: 0;
}

.exam-nav-sidebar,
.exam-question-area,
.exam-q-card,
.exam-result-main,
.exam-analysis-card {
  min-width: 0;
}

.exam-q-card {
  overflow: visible;
}

.exam-q-meta-row,
.exam-footer-container,
.exam-footer-actions,
.exam-confirm-card footer {
  flex-wrap: wrap;
}

.exam-q-stem,
.exam-opt-text,
.exam-analysis-trigger span,
.exam-analysis-body,
.exam-result-summary p {
  overflow-wrap: anywhere;
  word-break: normal;
}

.exam-opt-card {
  align-items: flex-start;
}

.exam-opt-text {
  min-width: 0;
  line-height: 1.6;
}

.exam-answer-input,
.exam-answer-textarea {
  min-width: 0;
}

.exam-analysis-trigger {
  gap: 10px;
  min-width: 0;
}

.exam-analysis-trigger span {
  min-width: 0;
  text-align: right;
}

.exam-modal-mask {
  padding: 24px;
}

.exam-confirm-card p {
  line-height: 1.65;
}

.wrong-book-page {
  display: grid;
  gap: 24px;
}

.wrong-dashboard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 20px;
  background: #FFFFFF;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
  padding: 24px 28px;
}

.wrong-title-block {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 16px;
}

.wrong-title-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 16px;
  background: linear-gradient(135deg, #FEE2E2 0%, #FFF7ED 100%);
  color: #DC2626;
}

.wrong-title-block h1 {
  margin: 0;
  color: #1E293B;
  font-size: 26px;
  font-weight: 900;
  line-height: 1.2;
}

.wrong-title-block p {
  margin: 4px 0 0;
  overflow: hidden;
  color: #64748B;
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wrong-head-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.wrong-book-page .wrong-hero {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  color: #1E293B;
}

.wrong-book-page .wrong-hero div {
  min-height: 118px;
  display: grid;
  align-content: center;
  gap: 8px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 18px;
  background: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
  padding: 22px 24px;
}

.wrong-book-page .wrong-hero div::before {
  content: none;
}

.wrong-book-page .wrong-hero strong {
  color: #1E293B;
  font-size: 34px;
  font-weight: 900;
  line-height: 1;
}

.wrong-book-page .wrong-hero span {
  color: #64748B;
  font-size: 14px;
  font-weight: 800;
}

.wrong-book-page .wrong-layout {
  display: grid;
  grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.wrong-book-page .wrong-tree {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 8px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 20px;
  background: #FFFFFF;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
  padding: 16px;
}

.wrong-book-page .wrong-tree strong {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 8px 4px;
  color: #94A3B8;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.wrong-book-page .wrong-tree button {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: #64748B;
  padding: 0 12px;
  font-weight: 800;
  text-align: left;
}

.wrong-book-page .wrong-tree button em {
  min-width: 28px;
  margin-left: auto;
  border-radius: 999px;
  background: #F1F5F9;
  color: #64748B;
  font-size: 12px;
  font-style: normal;
  line-height: 22px;
  text-align: center;
}

.wrong-book-page .wrong-tree button:hover,
.wrong-book-page .wrong-tree button.active {
  border-color: #E0E7FF;
  background: #EEF2FF;
  color: #4F46E5;
  box-shadow: none;
  transform: translateX(2px);
}

.wrong-book-page .wrong-tree button.active em {
  background: #4F46E5;
  color: #FFFFFF;
}

.wrong-book-page .wrong-list {
  display: grid;
  gap: 14px;
}

.wrong-book-page .wrong-tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  gap: 12px;
  margin: 0;
}

.wrong-filter-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #E2E8F0;
  border-radius: 14px;
  background: #F8FAFC;
  padding: 10px 12px;
  color: #64748B;
  font-size: 13px;
  font-weight: 800;
}

.wrong-filter-state button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: 999px;
  background: #FFFFFF;
  color: #4F46E5;
  padding: 7px 12px;
  font-weight: 800;
}

.wrong-filter-state button:hover {
  background: #EEF2FF;
}

.wrong-card-top,
.wrong-card-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.wrong-card-top {
  justify-content: space-between;
}

.wrong-state,
.wrong-times {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 900;
}

.wrong-state.pending {
  background: #FEF2F2;
  color: #DC2626;
}

.wrong-state.resolved {
  background: #ECFDF5;
  color: #059669;
}

.wrong-times {
  background: #F8FAFC;
  color: #64748B;
}

.wrong-book-page .wrong-card {
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 18px;
  background: #FFFFFF;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
  padding: 20px 22px;
}

.wrong-book-page .wrong-card::before {
  background: linear-gradient(180deg, #EF4444, #F59E0B);
}

.top-icon[data-loading="true"] {
  color: var(--s-muted) !important;
}

.top-icon[data-loading="true"] > * {
  opacity: 1 !important;
  visibility: visible !important;
}

.top-icon[data-loading="true"]::after {
  content: none !important;
  display: none !important;
}

@media (max-width: 1180px) {
  .practice-modern-grid {
    grid-template-columns: 1fr;
  }

  .wrong-book-page .wrong-hero {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .wrong-book-page .wrong-layout {
    grid-template-columns: 1fr;
  }

  .wrong-book-page .wrong-tree {
    position: static;
  }
}

@media (max-width: 760px) {
  .wrong-dashboard-head,
  .wrong-head-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .wrong-book-page .wrong-hero,
  .wrong-book-page .wrong-tools {
    grid-template-columns: 1fr;
  }

  .quiz-modern-header {
    align-items: stretch;
  }

  .quiz-modern-tabs {
    width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
  }

  .quiz-modern-tabs button {
    flex: 1 0 auto;
  }

  .quiz-card,
  .wrong-card,
  .practice-history-item,
  .practice-feature-card {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .quiz-card footer,
  .wrong-card footer {
    justify-content: flex-start;
  }

  .exam-header {
    align-items: stretch;
  }

  .exam-title {
    white-space: normal;
  }

  .exam-footer-container {
    align-items: center;
  }
}

@keyframes render-audit-spin {
  to { transform: rotate(360deg); }
}
</style>
