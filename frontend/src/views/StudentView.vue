<template>
  <PageLoader v-if="studentFullscreenLoading" />

  <section v-else-if="active === 'studentLessonStudy' && lessonStudyError" class="study-room study-route-state">
    <div class="study-route-center">
      <AlertTriangle :size="42" />
      <h1>课时加载失败</h1>
      <p>{{ lessonStudyError }}</p>
      <button class="glass-btn" @click="returnCourse"><ArrowLeft :size="17" />返回课程</button>
    </div>
  </section>

  <section v-else-if="classroomOpen" ref="studyRoomRef" class="study-room" :class="{ panelClosed: !aiPanelOpen, compactLesson: compactLessonLayout, fullscreen: lessonFullscreen, 'slide-fitted': slideViewportFitScale < 0.999 }" :style="slideViewportStyle" @mousemove="revealChrome">
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
          <button v-if="!compactLessonLayout" class="icon-glass" @click="aiPanelOpen = !aiPanelOpen"><PanelRight :size="18" /></button>
          <button class="icon-glass" @click="settingsOpen = !settingsOpen"><Settings :size="18" /></button>
        </div>
      </header>
    </transition>

    <main ref="studyMainRef" class="study-main" :style="studyLayoutStyle">
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

      <section ref="slideStageRef" class="slide-stage" :class="{ 'has-original-preview': !!classroomOriginalMaterial }" @mouseup="scheduleLessonSelectionCheck" @scroll.passive="hideLessonSelectionMenu">
        <transition :name="classroomOriginalMaterial ? 'fade-slide' : (pageDirection === 'next' ? 'slide-next' : 'slide-prev')" mode="out-in">
          <DocumentPreviewSurface
            v-if="classroomOriginalMaterial"
            :key="`material-${classroomOriginalMaterial.id}`"
            class="lesson-original-preview"
            :material="classroomOriginalMaterial"
            :page-number="currentPage"
            bare
          />
          <div v-else :key="activePage?.id || currentPage" class="slide-card-shell" :style="slideCardShellStyle">
            <article class="slide-card" :class="{ 'slide-card--scaled': slideViewportFitScale < 0.999 }">
              <span class="page-badge">P{{ currentPage }}</span>
              <span class="knowledge-dot" aria-label="AI知识点"><Sparkles :size="14" /></span>
              <h1>{{ activePage?.page_title || `第${currentPage}页` }}</h1>
              <div class="slide-content lesson-markdown" v-html="activePageHtml"></div>
            </article>
          </div>
        </transition>
        <transition name="subtitle">
          <div v-if="subtitleMode !== 'hide' && activeSubtitleText" class="subtitle-line">
            <div class="lesson-markdown" v-html="activeSubtitleHtml"></div>
          </div>
        </transition>
        <transition name="player-pop">
          <div v-show="chromeVisible || !audioPlaying" class="player-bar" :class="{ 'no-audio': !hasActiveAudio }">
            <button class="round-btn ghost" title="上一页" @click="prevPage"><ChevronLeft :size="18" /></button>
            <template v-if="hasActiveAudio">
              <button class="round-btn primary" @click="toggleAudio"><component :is="audioPlaying ? Pause : Play" :size="20" /></button>
            </template>
            <button class="round-btn ghost" title="下一页" @click="nextPage"><ChevronRight :size="18" /></button>
            <template v-if="hasActiveAudio">
              <span class="time">{{ audioTime }}</span>
              <AppSlider v-model="audioProgress" class="range" :min="0" :max="100" @input="seekAudio" />
              <span class="time">{{ audioDuration }}</span>
              <PopoverButton :items="speedItems" :label="`${playbackRate}x`" placement="top" @select="setRate" />
            </template>
            <button class="round-btn ghost" @click="thumbOpen = !thumbOpen"><Grid2X2 :size="18" /></button>
            <button class="round-btn ghost" :title="lessonFullscreen ? '退出全屏' : '进入全屏'" @click="toggleLessonFullscreen"><Maximize :size="18" /></button>
            <audio v-if="activePage?.audio_url" ref="audioRef" :src="activePage.audio_url" @timeupdate="updateAudio" @loadedmetadata="updateAudio" @ended="handleAudioEnded" @play="audioPlaying = true" @pause="audioPlaying = false"></audio>
          </div>
        </transition>
      </section>

      <button
        v-show="aiPanelOpen && !compactLessonLayout"
        class="study-resizer"
        type="button"
        aria-label="拖动调整课件和互动区域宽度"
        title="拖动调整宽度"
        @pointerdown="startLessonResize"
      >
        <span></span>
      </button>

      <aside class="lesson-ai">
        <div class="study-tabs">
          <button :class="{ active: classroomTab === 'script' }" @click="classroomTab = 'script'"><FileText :size="16" />文稿</button>
          <button :class="{ active: classroomTab === 'activity' }" @click="classroomTab = 'activity'"><Zap :size="16" />活动</button>
          <button :class="{ active: classroomTab === 'qa' }" @click="classroomTab = 'qa'"><MessageCircle :size="16" />问答</button>
          <button :class="{ active: classroomTab === 'note' }" @click="classroomTab = 'note'"><ListChecks :size="16" />笔记</button>
        </div>
        <transition name="fade-slide" mode="out-in">
          <section v-if="classroomTab === 'script'" key="script" class="script-view">
            <div class="sticky-tools"><span>当前页 {{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</span><button @click="copyText(activeScriptText || activePageText)"><Copy :size="14" />复制</button></div>
            <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
            <div class="reading lesson-markdown" v-html="activeScriptHtml"></div>
          </section>
          <section v-else-if="classroomTab === 'activity'" key="activity" class="activity-view">
            <div class="activity-hero">
              <span><Sparkles :size="16" />页面活动层</span>
              <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
              <p>{{ pageSummaryActivity?.summary || pageSummaryActivity?.content || activePageText.slice(0, 120) || '暂无页面摘要' }}</p>
            </div>
            <div v-if="learningObjectiveItems.length || keyPointItems.length" class="activity-band">
              <section v-if="learningObjectiveItems.length">
                <h3><Layers :size="15" />目标</h3>
                <ul><li v-for="item in learningObjectiveItems" :key="item">{{ item }}</li></ul>
              </section>
              <section v-if="keyPointItems.length">
                <h3><Zap :size="15" />重点</h3>
                <ul><li v-for="item in keyPointItems" :key="item">{{ item }}</li></ul>
              </section>
            </div>
            <div v-if="problemTemplateActivities.length" class="activity-section">
              <h3><Pencil :size="16" />例题模板</h3>
              <article v-for="item in problemTemplateActivities" :key="item.id" class="activity-item example">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <div v-if="misconceptionActivities.length" class="activity-section">
              <h3><Shield :size="16" />易错点</h3>
              <article v-for="item in misconceptionActivities" :key="item.id" class="activity-item mistake">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <div v-if="quickCheckActivities.length" class="activity-section">
              <h3><MessageCircle :size="16" />快问</h3>
              <button v-for="item in quickCheckActivities" :key="item.id" class="activity-question" type="button" @click="sendQuickClass(activityQuestion(item))">{{ activityQuestion(item) }}</button>
            </div>
            <div v-if="discussionDemoActivities.length" class="activity-section">
              <h3><Presentation :size="16" />讨论与演示</h3>
              <article v-for="item in discussionDemoActivities" :key="item.id" class="activity-item">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <EmptyState v-if="!activePageActivities.length" text="本页暂无活动层，重新解析课件后会生成结构化教学对象" />
          </section>
          <section v-else-if="classroomTab === 'qa'" key="qa" class="class-chat">
            <div class="class-chat-scroll">
              <div v-if="classConversationLoading && !classMessages.length" class="chat-local-loading compact"><LoadingMark :label="false" /></div>
              <ChatList :messages="classMessages" :thinking="classThinking" :user-avatar-url="currentAvatarUrl" :user-name="profileForm.nickname || user.nickname" @toggle-thought="toggleThought" @copy="copyText" @feedback="feedbackQaMessage" @jump-source="jumpToSource" />
            </div>
            <div class="class-chat-dock">
              <div v-if="classQaAttachments.length" class="qa-attachment-strip compact">
                <div v-for="(item, index) in classQaAttachments" :key="`${item.url}-${index}`" class="qa-attachment-chip">
                  <img :src="item.url" alt="" />
                  <span>{{ item.filename || '图片' }}</span>
                  <button type="button" @click="removeQaAttachment('class', index)"><X :size="13" /></button>
                </div>
              </div>
              <div v-if="lessonAskContext" class="lesson-qa-selection-context" :title="lessonAskContext">
                <Quote :size="14" />
                <span>{{ lessonAskContextPreview }}</span>
                <button type="button" aria-label="移除选中文本" @click="clearLessonAskContext"><X :size="13" /></button>
              </div>
              <form class="chat-input compact" @submit.prevent="askInClass">
                <input ref="classQaImageInput" class="qa-image-input" type="file" accept="image/*" @change="handleQaImageChange($event, 'class')" />
                <button type="button" class="attach-btn" :data-loading="classQaImageUploading" :disabled="classThinking || (classConversationLoading && !classMessages.length) || classQaImageUploading || classQaAttachments.length >= 3" title="上传图片" @click="classQaImageInput?.click()"><Camera :size="17" /></button>
                <textarea
                  ref="classQuestionInput"
                  v-model="classQuestion"
                  :placeholder="classQuestionPlaceholder"
                  rows="1"
                  @compositionstart="handleQuestionCompositionStart('class')"
                  @compositionend="handleQuestionCompositionEnd('class')"
                  @keydown="handleClassQuestionKeydown"
                ></textarea>
                <button v-if="classThinking" type="button" class="send-btn send-btn-stop" title="停止生成" aria-label="停止生成" @click="stopClassGeneration"><Square :size="16" /></button>
                <button v-else :disabled="(!classQuestion.trim() && !classQaAttachments.length) || (classConversationLoading && !classMessages.length) || classQaImageUploading" class="send-btn"><Send :size="18" /></button>
              </form>
              <div class="quick-tags lesson-quick-tags">
                <button v-for="item in quickPageQuestions" :key="item" :title="item" @click="sendQuickClass(item)">{{ item }}</button>
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

    <transition name="selection-pop">
      <div
        v-if="lessonSelectionMenu.open"
        class="lesson-selection-popover"
        :style="lessonSelectionMenuStyle"
        @pointerdown.stop
        @mousedown.prevent.stop
      >
        <button type="button" @click="explainLessonSelection">解释</button>
        <button type="button" @click="prepareLessonSelectionQuestion">提问</button>
      </div>
    </transition>

    <Teleport to="body">
      <transition name="modal-pop">
        <div v-if="completeOpen" class="modal-mask student-modal-scope">
          <article class="complete-modal">
            <div class="confetti"><i v-for="n in 28" :key="n" :style="confettiStyle(n)"></i></div>
            <CheckCircle :size="56" />
            <h2>恭喜完成</h2>
            <p>{{ classroomLesson?.lesson.title }}</p>
            <div class="done-stats"><span>本次 {{ Math.max(1, Math.round(studySeconds / 60)) }} 分钟</span><span>{{ classroomLesson?.pages.length || 0 }} 页</span><span>{{ classMessages.filter((m) => m.role === 'user').length }} 次提问</span></div>
            <div class="ai-summary"><Info :size="16" />{{ completionSummary }}</div>
            <footer><button class="btn btn-primary" @click="nextLessonAfterComplete">下一课时</button><button class="btn btn-secondary" @click="returnCourse">回课程</button><button class="btn btn-ghost" @click="openQuizSelection('practice')">做练习</button></footer>
          </article>
        </div>
      </transition>
    </Teleport>

    <transition name="fade-slide">
      <div v-if="settingsOpen" class="settings-pop">
        <button :class="{ active: subtitleMode === 'full' }" @click="subtitleMode = 'full'">完整字幕</button>
        <button :class="{ active: subtitleMode === 'keyword' }" @click="subtitleMode = 'keyword'">关键词</button>
        <button :class="{ active: subtitleMode === 'hide' }" @click="subtitleMode = 'hide'">隐藏字幕</button>
      </div>
    </transition>
  </section>

  <section v-else class="student-shell" :class="{ 'route-loading': studentPageLoading }">
    <header class="student-top">
      <button type="button" class="brand" aria-label="返回学生首页" @click="go('studentHome')">
        <BrandLogo class="student-brand-logo" />
        <strong>智学黑板</strong>
      </button>
      <Teleport to="body">
        <transition name="search-expand">
          <div v-if="searchOpen" class="global-search" @click.self="closeSearch">
            <div class="global-search-panel" @click.stop>
              <div class="global-search-bar">
                <Search :size="18" />
                <input
                  ref="searchInput"
                  v-model="globalSearch"
                  placeholder="搜索课程、课时、资料、知识点、问答"
                  @keydown.down.prevent="moveSearchSelection(1)"
                  @keydown.up.prevent="moveSearchSelection(-1)"
                  @keydown.enter.prevent="openActiveSearchResult"
                  @keyup.esc="closeSearch"
                />
                <button type="button" @click="closeSearch"><X :size="18" /></button>
              </div>
              <div class="global-search-results">
                <div v-if="searchLoading" class="global-search-state">
                  <LoadingMark :label="false" class="inline-loading-mark" />
                  <span>正在搜索</span>
                </div>
                <div v-else-if="searchError" class="global-search-state error">
                  <AlertTriangle :size="18" />
                  <span>{{ searchError }}</span>
                </div>
                <div v-else-if="!searchKeyword" class="global-search-state">
                  <Search :size="18" />
                  <span>输入课程、课时、资料、知识点或问答关键词</span>
                </div>
                <div v-else-if="searchResultGroups.length" class="global-search-groups">
                  <section v-for="group in searchResultGroups" :key="group.type" class="global-search-group">
                    <header>
                      <span>{{ group.label }}</span>
                      <small>{{ group.items.length }}</small>
                    </header>
                    <button
                      v-for="item in group.items"
                      :key="item.key"
                      type="button"
                      class="global-search-item"
                      :class="{ active: isSearchResultActive(item), ai: item.type === 'qa' }"
                      @mouseenter="focusSearchResult(item.key)"
                      @click="openSearchResult(item)"
                    >
                      <span class="global-search-item-icon">
                        <component :is="searchTypeMeta(item.type).icon" :size="18" />
                      </span>
                      <span class="global-search-copy">
                        <strong>{{ item.title }}</strong>
                        <small>{{ item.subtitle }}</small>
                        <p v-if="item.excerpt">{{ item.excerpt }}</p>
                      </span>
                      <ChevronRight :size="16" class="global-search-arrow" />
                    </button>
                  </section>
                </div>
                <div v-else class="global-search-state">
                  <Info :size="18" />
                  <span>没有找到相关内容</span>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </Teleport>
      <nav ref="topNavRef" class="student-nav-links" aria-label="学生端主导航">
        <span
          class="student-nav-indicator"
          :class="{ ready: topNavIndicator.ready }"
          :style="{ width: `${topNavIndicator.width}px`, transform: `translateX(${topNavIndicator.left}px)` }"
          aria-hidden="true"
        ></span>
        <button
          v-for="item in topNavTabs"
          :key="item.key"
          type="button"
          class="student-nav-link"
          :class="{ active: isStudentNavActive(item.key), ai: item.key === 'studentQa' }"
          :aria-current="isStudentNavActive(item.key) ? 'page' : undefined"
          @click="handleStudentNav(item.key)"
        >
          <component :is="item.icon" :size="16" />
          {{ item.label }}
        </button>
      </nav>
      <div ref="topActionsRef" class="top-actions">
        <button class="top-icon" title="全局搜索" aria-label="全局搜索" @click="openSearch"><Search :size="19" /></button>
        <button class="top-icon" title="通知中心" aria-label="通知中心" :data-loading="notificationLoading" @click="toggleNotifications"><Bell :size="19" /><em v-if="unreadCount">{{ unreadCount }}</em></button>
        <ThemeToggle class="top-theme-toggle" />
        <button class="avatar-btn" title="个人档案" aria-label="个人档案" @click="userMenuOpen = !userMenuOpen">
          <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" />
          <DefaultUserAvatar v-else />
        </button>
      </div>
      <transition name="top-menu">
        <div v-if="noticeOpen" ref="noticePopRef" class="notice-pop top-menu-panel">
          <header class="notice-head">
            <strong>通知中心</strong>
            <button v-if="unreadCount" type="button" :data-loading="notificationReading" :disabled="notificationReading" @click="markStudentNotificationsRead()">全部已读</button>
          </header>
          <div v-for="item in notifications" :key="item.id || `${item.type}-${item.title}`" class="notice-item" :class="{ unread: item.unread }">
            <Bell :size="15" />
            <div><strong>{{ item.title }}</strong><p v-if="item.message">{{ item.message }}</p><small>{{ item.course_name ? `${item.course_name} · ` : '' }}{{ relativeTime(item.time) }}</small></div>
            <button v-if="item.unread" type="button" class="notice-read-btn" :data-loading="notificationReading" :disabled="notificationReading" @click.stop="markStudentNotificationsRead(item)">已读</button>
            <i v-if="item.unread"></i>
          </div>
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

    <main class="student-main" :class="{ 'student-main-qa': active === 'studentQa' }">
      <div
        ref="pageStageRef"
        class="student-page-stage"
        :class="{ 'is-switching': pageSwitching }"
        :style="pageStageStyle"
      >
        <transition
          :name="pageTransitionName"
          @before-leave="beforeStudentPageLeave"
          @before-enter="beforeStudentPageEnter"
          @after-enter="finishStudentPageTransition"
          @enter-cancelled="finishStudentPageTransition"
          @leave-cancelled="finishStudentPageTransition"
        >
          <section :key="active" class="student-page" :class="{ 'student-page-qa': active === 'studentQa' }">
          <template v-if="active === 'studentHome'">
            <article class="hello-card">
              <div><Sun :size="24" /><section><h1>{{ greeting }}，{{ user.nickname }}</h1><p>{{ todayText }}<template v-if="currentTermLabel"> · {{ currentTermLabel }}</template></p></section></div>
              <div v-if="todayTasks.length" class="circle-stat"><RingProgress :value="todayDoneRate" /><span>{{ doneTasks }}/{{ todayTasks.length }}</span></div>
            </article>
            <article class="today-plan" :class="{ 'is-empty': !todayTasks.length }">
              <CalendarCheck :size="20" />
              <div class="today-plan-copy">
                <strong>今日计划</strong>
                <small>{{ todayTasks.length ? todayPlanSummary : '今天还没有学习安排，点击制定计划后可在首页直接查看和打卡' }}</small>
              </div>
              <span v-if="todayTasks.length" class="today-plan-count">{{ doneTasks }}/{{ todayTasks.length }}</span>
              <AppProgress v-if="todayTasks.length" :value="todayDoneRate" />
              <button @click="go('studentPlans')">{{ todayTasks.length ? '查看' : '制定计划' }}</button>
            </article>
            <article class="continue-card">
              <div class="continue-cover" :style="courseCoverStyle(continueLesson?.course || activeCourse)"><Presentation :size="32" /><span>P{{ continueProgressPage }}</span></div>
              <section v-if="continueLesson">
                <span class="tag tag-ai"><Sparkles :size="12" />接续上次</span>
                <h2>{{ continueLesson.lesson.title }}</h2>
                <p>第 {{ continueProgressPage }} 页 / 共 {{ continueLesson.lesson.page_count || 1 }} 页</p>
                <AppProgress :value="continueProgress" />
                <small>{{ continueTime }}</small>
                <button class="btn btn-primary" :disabled="isLessonOpening" @click="openLesson(continueLesson.lesson.id)"><LoadingMark v-if="isOpeningLesson(continueLesson.lesson.id)" :label="false" class="inline-loading-mark" /><Play v-else :size="16" />{{ isOpeningLesson(continueLesson.lesson.id) ? '正在打开' : '继续学习' }}</button>
              </section>
              <section v-else class="empty-continue"><BookOpen :size="42" /><h2>还没有学习</h2><button class="btn btn-primary" @click="go('studentCourses')">浏览课程</button></section>
            </article>
            <div class="home-grid">
              <article class="panel-card">
                <div class="section-head"><h2><BookOpen :size="18" />我的课程</h2><button @click="go('studentCourses')">查看全部</button></div>
                <div v-if="courses.length" class="home-course-strip" :class="{ 'single-course': courses.length === 1 }">
                  <button v-for="course in courses" :key="course.id" class="home-course" @click="openCourse(course.id)">
                    <span :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)">
                      <strong v-if="!course.cover_url" class="course-cover-mini-text">{{ courseCoverText(course) }}</strong>
                    </span>
                    <div><strong>{{ course.name }}</strong><small>{{ course.teacher?.nickname || '教师' }} · {{ course.term }}</small><AppProgress :value="course.progress_percent || 0" /><em>{{ course.progress_percent || 0 }}%</em></div>
                  </button>
                </div>
                <button class="join-dashed" @click="joinOpen = true"><Plus :size="16" />加入新课程</button>
              </article>
              <article class="panel-card">
                <div class="section-head"><h2><BarChart2 :size="18" />我的学习</h2><button @click="go('studentProfile')">学习报告</button></div>
                <div class="rings"><RingBlock label="累计学习" :value="hourTargetRate" :text="`${stats.study_hours || 0}h`" sub="累计时长" /><RingBlock label="完成率" :value="stats.completion_rate || 0" :text="`${stats.completion_rate || 0}%`" sub="课时" tone="success" /><RingBlock label="正确率" :value="stats.accuracy || 0" :text="`${stats.accuracy || 0}%`" sub="练习" tone="ai" /></div>
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
                  <button class="home-refresh-btn" @click="hasJoinedCourses ? loadDashboard({ refreshRecommendation: true }) : (joinOpen = true)">
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
                <header class="course-art" :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)">
                  <span class="course-term-pill">{{ course.term || '本学期' }}</span>
                  <strong v-if="!course.cover_url" class="course-cover-text">{{ courseCoverText(course) }}</strong>
                  <DropdownMenu :items="courseMenuItems" @select="handleCourseMenu($event, course)" />
                </header>
                <section class="course-card-body">
                  <div class="course-card-title">
                    <h2>{{ course.name }}</h2>
                    <p><User :size="14" />{{ course.teacher?.nickname || '课程教师' }}</p>
                  </div>
                  <div class="course-progress-panel">
                    <div>
                      <span>学习进度</span>
                      <strong>{{ course.progress_percent || 0 }}%</strong>
                    </div>
                    <AppProgress :value="course.progress_percent || 0" />
                  </div>
                  <div class="course-meta">
                    <span><BookOpen :size="14" />已学 {{ course.studied_lessons || 0 }}/{{ course.lesson_total || 0 }} 课时</span>
                    <span><Clock :size="14" />{{ course.last_lesson ? relativeTime(course.last_progress?.updated_at) : '未开始' }}</span>
                  </div>
                  <div class="course-card-stats">
                    <span><MessageCircle :size="14" /><b>{{ course.qa_count || 0 }}</b>问答</span>
                    <span><XCircle :size="14" /><b>{{ course.wrong_count || 0 }}</b>错题</span>
                    <span><Users :size="14" /><b>{{ course.student_count || 0 }}</b>同学</span>
                  </div>
                  <footer class="course-card-actions">
                    <button type="button" class="btn btn-primary" @click="openCourse(course.id)"><Play :size="16" />{{ (course.progress_percent || 0) > 0 ? '继续学习' : '开始学习' }}</button>
                    <button type="button" class="course-card-link" @click="handleCourseMenu('qa', course)"><MessageCircle :size="15" />问答</button>
                  </footer>
                </section>
              </article>
            </div>
            <EmptyState v-if="!filteredCourses.length" text="暂无课程" />
          </template>

          <template v-else-if="active === 'studentCourseHome'">
            <article v-if="courseHomeError" class="course-route-state error">
              <span class="course-route-icon error"><AlertTriangle :size="34" /></span>
              <h1>课程加载失败</h1>
              <p>{{ courseHomeError }}</p>
              <footer>
                <button type="button" class="btn btn-primary" @click="loadCourseHome"><RefreshCw :size="16" />重试</button>
                <button type="button" class="btn btn-secondary" @click="go('studentCourses')"><ArrowLeft :size="16" />返回课程列表</button>
              </footer>
            </article>
            <CourseRequired v-else-if="!courseHome.course" />
            <template v-else>
              <article class="course-hero-student course-hero-compact" :class="{ 'has-image': courseHome.course.cover_url }" :style="courseHeroStyle(courseHome.course)">
                <section>
                  <h1>{{ courseHome.course.name }}</h1>
                  <p><User :size="16" />{{ courseHome.teacher?.nickname || '教师' }} · {{ courseHome.course.term }}</p>
                  <div><Check :size="16" />已完成 {{ courseHome.stats?.completion_rate || 0 }}% <AppProgress :value="courseHome.stats?.completion_rate || 0" class="hero-progress" tone="success" /><Users :size="16" />{{ courseHome.student_count || 0 }}名同学</div>
                </section>
                <aside class="course-hero-action-side">
                  <button class="btn white-fill" :disabled="isLessonOpening || !latestLesson" @click="latestLesson && openLesson(Number(latestLesson.id))"><LoadingMark v-if="latestLesson && isOpeningLesson(Number(latestLesson.id))" :label="false" class="inline-loading-mark" /><Play v-else :size="16" />{{ latestLesson && isOpeningLesson(Number(latestLesson.id)) ? '正在打开' : '进入课时' }}</button>
                </aside>
              </article>
              <div class="quick-row"><QuickTile :icon="Presentation" label="课时学习" :sub="`${courseHome.lessons?.length || 0} 个课时`" @click="scrollToLessons" /><QuickTile :icon="MessageCircle" label="知识问答" sub="AI 解答" @click="go('studentQa')" /><QuickTile :icon="FolderOpen" label="课程资料" :sub="`${courseHome.materials?.length || 0} 份文件`" @click="courseSection = 'materials'" /><QuickTile :icon="ClipboardList" label="章节练习" sub="自选练习" @click="openQuizSelection('practice')" /></div>
              <div class="course-layout course-overview-layout">
                <article id="lesson-list" class="panel-card course-lessons-card">
                  <div class="section-head"><h2><Presentation :size="18" />课时列表</h2><span class="tag">全部 {{ courseHome.lessons?.length || 0 }}</span></div>
                  <div class="course-lessons-scroll">
                    <LessonItem v-for="(lesson, index) in courseHome.lessons || []" :key="lesson.id" :lesson="lesson" :index="Number(index)" :loading="isOpeningLesson(Number(lesson.id))" :disabled="isLessonOpening && !isOpeningLesson(Number(lesson.id))" @open="openLesson(Number(lesson.id))" />
                  </div>
                </article>
                <article class="panel-card course-data-card"><div class="section-head"><h2><BarChart2 :size="18" />我的数据</h2></div><div class="data-grid"><MiniMetric :icon="Clock" label="学习时长" :value="`${courseHome.stats?.study_hours || 0}h`" /><MiniMetric :icon="CheckCircle" label="完成进度" :value="`${courseHome.stats?.completion_rate || 0}%`" tone="success" /><MiniMetric :icon="MessageCircle" label="问答次数" :value="courseHome.stats?.qa_count || 0" tone="ai" /><MiniMetric :icon="XCircle" label="错题数" :value="courseHome.stats?.wrong_count || 0" tone="danger" /><MiniMetric :icon="Star" label="正确率" :value="`${courseHome.stats?.accuracy || 0}%`" tone="warning" /><MiniMetric :icon="Zap" label="连续打卡" :value="`${courseHome.stats?.streak_days || 0}天`" tone="warning" /></div></article>
                <article class="panel-card course-materials-card">
                  <div class="section-head"><h2><FolderOpen :size="18" />课程资料</h2><button @click="materialsExpanded = !materialsExpanded">{{ materialsExpanded ? '收起' : '展开' }}</button></div>
                  <div class="course-material-list">
                    <MaterialRow v-for="item in baseCourseMaterials" :key="item.id" :item="item" />
                    <Transition name="course-materials-expand">
                      <div v-if="materialsExpanded && extraCourseMaterials.length" class="course-material-extra">
                        <div class="course-material-extra-inner">
                          <MaterialRow v-for="item in extraCourseMaterials" :key="item.id" :item="item" />
                        </div>
                      </div>
                    </Transition>
                  </div>
                  <button v-if="extraCourseMaterials.length" class="ghost-row course-material-toggle" :class="{ expanded: materialsExpanded }" @click="materialsExpanded = !materialsExpanded"><ChevronDown :size="16" />{{ materialsExpanded ? '收起' : `展开更多` }}</button>
                </article>
              </div>
              <div class="course-qa-wide">
                <article class="ask-card"><Sparkles :size="20" /><h2>向 AI 提问</h2><form @submit.prevent="askCourseQuick"><input v-model="quickCourseQuestion" placeholder="这节课有什么不懂的..." /><button><Send :size="16" /></button></form><div class="quick-tags"><button v-for="item in courseHome.quick_questions || []" :key="item" @click="sendCourseQuick(item)">{{ item }}</button></div></article>
                <article class="panel-card recent-qa-card"><div class="section-head"><h2><MessageCircle :size="18" />最近提问</h2><button @click="go('studentQa')">全部</button></div><div v-for="item in courseHome.recent_qa || []" :key="item.id" class="qa-mini"><strong>{{ item.question }}</strong><p>{{ item.answer }}</p></div><EmptyState v-if="!(courseHome.recent_qa || []).length" text="暂无提问" /></article>
              </div>
            </template>
          </template>

          <template v-else-if="active === 'studentQa'">
            <section class="qa-modern-page" :class="{ 'is-empty': !globalMessages.length }">
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
                    <button class="qa-new-chat-link" type="button" title="新建对话" aria-label="新建对话" @click="startNewQaConversation"><Plus :size="18" /></button>
                    <button class="action-circle-btn" type="button" :class="{ active: historyOpen }" title="问答历史" aria-label="问答历史" @click="toggleQaHistory"><Clock :size="18" /></button>
                  </div>
                </div>
                <div v-if="globalConversationLoading && !globalMessages.length" class="chat-local-loading"><LoadingMark :label="false" /></div>
                <div v-if="!globalMessages.length && !globalConversationLoading" class="qa-welcome"><Sparkles :size="48" /><h2>{{ courseScopeName }}专属问答</h2></div>
                <ChatList v-else-if="globalMessages.length" :messages="globalMessages" :thinking="globalThinking" :user-avatar-url="currentAvatarUrl" :user-name="profileForm.nickname || user.nickname" large @toggle-thought="toggleThought" @copy="copyText" @favorite="favoriteQaMessage" @feedback="feedbackQaMessage" @jump-source="jumpToSource" />
                <div v-if="!globalMessages.length && !globalConversationLoading" class="prompt-grid"><button v-for="item in promptCards" :key="item.text" @click="sendGlobalQuick(item.text)"><component :is="item.icon" :size="18" />{{ item.text }}</button></div>
                <div class="qa-latest-anchor" aria-hidden="true"></div>
              </div>
            </section>
          </template>

          <template v-else-if="active === 'studentTutoring'">
            <section class="tutoring-page">
              <PageTitle title="题目辅导">
                <CourseSelect />
                <span class="tag tag-ai"><Sparkles :size="12" />分步提示</span>
              </PageTitle>

              <div class="tutoring-stack">
                <section class="panel-card tutor-input">
                  <div class="tutor-card-head">
                    <div>
                      <span class="tutor-eyebrow"><BookOpen :size="14" />题目输入</span>
                      <h2>{{ selectedCourseId ? `《${courseScopeName}》` : '请先选择课程后输入题目' }}</h2>
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

                <section class="panel-card guide-card">
                  <div class="section-head">
                    <h2><Sparkles :size="18" />{{ activeProblem ? '查看解析' : '等待题目输入' }}</h2>
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
                </section>
              </div>

              <HistoryStrip title="历史辅导记录" :items="problemHistory" @pick="selectProblem" />
            </section>
          </template>

          <template v-else-if="active === 'studentKnowledge'">
            <PageTitle title="知识点精讲"><CourseSelect /></PageTitle>
            <div class="knowledge-layout"><aside class="knowledge-tree"><div class="pretty-input"><Search :size="15" /><input v-model="knowledgeKeyword" placeholder="搜索知识点" /></div><button v-for="chapter in courseHome.chapters || []" :key="chapter.id" @click="selectedChapterId = chapter.id; loadKnowledge()"><ChevronRight :size="14" />{{ chapter.title }}</button><div class="weak-tags"><strong><Zap :size="14" />薄弱知识点</strong><span v-for="item in weakPoints.slice(0, 3)" :key="item.knowledge_point" class="tag tag-danger">{{ item.knowledge_point }}</span></div></aside><section class="knowledge-content"><article class="knowledge-head"><h1>{{ selectedKnowledge?.name || '选择知识点' }}</h1><p>所属：{{ chapterName(selectedKnowledge?.chapter_id) }}</p><span class="tag" :class="knowledgeMasteryClass">{{ knowledgeMasteryText }}</span></article><div class="segmented"><button v-for="item in levelItems" :key="item.value" type="button" :class="{ active: knowledgeLevel === item.value }" @click="knowledgeLevel = String(item.value)">{{ item.label }}</button></div><article class="knowledge-body"><KnowledgeBlock icon="Quote" title="定义" :content="knowledgeContent.definition" /><KnowledgeBlock icon="Layers" title="核心原理" :content="knowledgeContent.principle" ai /><KnowledgeBlock icon="Pencil" title="例题解析" :content="knowledgeContent.example" /><KnowledgeBlock icon="AlertTriangle" title="常见易错点" warning :content="knowledgeContent.common_mistake" /><div class="practice-cta"><Sparkles :size="16" />生成练习题<button @click="generateKnowledgeQuiz(5)">练习5题</button><button @click="generateKnowledgeQuiz(10)">练习10题</button></div></article></section></div>
          </template>

          <template v-else-if="active === 'studentQuizzes'">
            <Teleport to="body">
              <div v-if="answeringQuiz" class="exam-answer-page"><QuizAnswerView :quiz="quizDetail" :answers="quizAnswers" :attempt="attempt" :submitting="quizSubmitting" @answer="setQuizAnswer" @submit="submitQuiz" @exit="closeQuizWorkspace" /></div>
            </Teleport>
            <section v-if="!answeringQuiz" class="quiz-modern-page">
              <header class="quiz-modern-header quiz-hero-card">
                <div class="quiz-hero-copy">
                  <div class="quiz-hero-icon"><ClipboardList :size="26" /></div>
                  <div class="quiz-modern-title">
                    <h1>练习与测验</h1>
                    <p>课程配套测验、自定义章节练习与错题重练集中管理</p>
                    <div class="quiz-hero-pills">
                      <span><BookOpen :size="14" />《{{ courseScopeName }}》</span>
                      <span><Sparkles :size="14" />AI 智能组卷</span>
                    </div>
                  </div>
                </div>
                <div class="quiz-hero-side">
                  <CourseSelect />
                  <div class="quiz-hero-stats">
                    <div><strong>{{ courseQuizzes.length }}</strong><span>课程测验</span></div>
                    <div><strong>{{ practiceQuizzes.length }}</strong><span>章节练习</span></div>
                    <div><strong>{{ pendingWrongCount }}</strong><span>待重练错题</span></div>
                  </div>
                </div>
              </header>

              <div class="quiz-modern-tabs">
                <button type="button" :class="{ active: quizTab === 'course' }" @click="quizTab = 'course'"><ClipboardList :size="18" />课程测验</button>
                <button type="button" :class="{ active: quizTab === 'practice' }" @click="quizTab = 'practice'"><Layers :size="18" />章节练习</button>
              </div>

              <section v-if="quizTab === 'course'" class="quiz-list quiz-modern-list">
                <QuizCard v-for="quiz in courseQuizzes" :key="quiz.id" :quiz="quiz" @open="openQuiz(quiz)" @review="viewQuizAttempt" />
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

                  <div class="practice-difficulty-row">
                    <strong>难度</strong>
                    <AppSelect v-model="practiceDifficulty" :options="quizDifficultyOptions" />
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
                    @click="loadWrongPractice()"
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
                    <button v-for="quiz in practiceQuizzes.slice(0, 5)" :key="quiz.id" type="button" class="practice-history-item" @click="openQuiz(quiz)">
                      <div class="practice-history-left">
                        <span class="practice-history-icon"><Layers :size="20" /></span>
                        <div>
                          <strong>{{ quiz.title }}</strong>
                          <small>{{ quizQuestionMeta(quiz) }} · {{ relativeTime(practiceRecordTime(quiz)) }}</small>
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
                  <button class="btn btn-primary" :data-loading="wrongPracticeGenerating" :disabled="wrongPracticeGenerating || !wrongQuestions.length" @click="loadWrongPractice()"><RefreshCw :size="16" />开始重练</button>
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
                    <h2><Flame :size="28" />{{ longestStreakDays === null ? '—' : longestStreakDays }}</h2>
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
                          :class="{ 'cal-empty': cell.empty, checked: cell.checked, today: cell.today }"
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
                      <div class="card-title"><BarChart2 :size="22" />学习时长</div>
                    </div>

                    <template v-if="hasWeeklyChartData">
                      <div class="mini-chart">
                        <div v-for="item in weeklyChart" :key="item.label" class="bar-col">
                          <div class="bar-track"><div class="bar-fill" :style="{ height: `${item.percent}%` }"></div></div>
                          <span class="bar-label">{{ item.label }}</span>
                        </div>
                      </div>
                    </template>
                    <EmptyState v-else text="暂无每日学习时长数据" />
                    <div class="total-hours">累计学习 <span>{{ totalWeeklyHours }}</span> 小时</div>
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
                      <div class="profile-cover-grid" aria-hidden="true"></div>
                      <button type="button" class="big-avatar avatar-upload-control" :data-loading="avatarUploading" :disabled="avatarUploading" title="更换头像" aria-label="更换头像" @click="studentAvatarInput?.click()">
                        <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" />
                        <DefaultUserAvatar v-else />
                        <Camera :size="14" class="camera-badge" />
                      </button>
                      <input ref="studentAvatarInput" class="visually-hidden-file" type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="uploadProfileAvatar" />
                    </div>
                    <div class="profile-header-info">
                      <section class="profile-name-block">
                        <span class="profile-role-pill">学生</span>
                        <h1>{{ profileForm.nickname }}</h1>
                        <div class="profile-contact-list">
                          <p><IdCard :size="15" /><span>学号</span><strong>{{ user.student_no || '-' }}</strong></p>
                          <p><Mail :size="15" /><span>邮箱</span><strong>{{ user.email }}</strong></p>
                        </div>
                      </section>
                      <aside class="profile-points-card">
                        <strong>{{ stats.qa_count || 0 }}</strong>
                        <span><MessageCircle :size="15" />累计提问数</span>
                      </aside>
                    </div>
                  </article>
                  <article class="panel-card badge-card profile-achievement-card">
                    <div class="section-head"><h2><Award :size="18" />我的成就</h2></div>
                    <div class="badges"><span v-for="item in profilePayload.achievements || []" :key="item.key" :class="{ locked: !item.unlocked }"><Award :size="22" />{{ item.unlocked ? item.name : '?' }}</span></div>
                    <EmptyState v-if="!(profilePayload.achievements || []).length" text="暂无成就" />
                  </article>
                </aside>

                <section class="profile-main-card">
                  <div class="profile-main-head">
                    <div>
                      <span>学习概览</span>
                      <h2>我的学习数据</h2>
                    </div>
                    <button type="button" class="btn btn-secondary btn-sm" @click="loadProfile"><RefreshCw :size="14" />刷新</button>
                  </div>
                  <div class="achievement-row">
                    <MiniMetric :icon="Clock" label="总学习时长" :value="`${stats.study_hours || 0}h`" />
                    <MiniMetric :icon="CheckCircle" label="课时完成" :value="`${stats.completion_rate || 0}%`" tone="success" />
                    <MiniMetric :icon="MessageCircle" label="知识问答" :value="stats.qa_count || 0" tone="ai" />
                    <MiniMetric :icon="Star" label="平均得分" :value="`${stats.accuracy || 0}%`" tone="warning" />
                  </div>
                  <div class="profile-tabs">
                    <button :class="{ active: profileTab === 'info' }" @click="profileTab = 'info'"><User :size="15" />我的资料</button>
                    <button :class="{ active: profileTab === 'records' }" @click="profileTab = 'records'"><Clock :size="15" />学习档案</button>
                    <button :class="{ active: profileTab === 'account' }" @click="profileTab = 'account'"><Settings :size="15" />账号设置</button>
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
                        <div v-for="item in noticeSettings" :key="item.key" class="toggle-line"><AppCheckbox v-model="item.enabled" variant="switch" :label="item.label" /></div>
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
      </div>
    </main>

    <nav class="bottom-tabs">
      <button v-for="item in bottomTabs" :key="item.key" :class="{ active: isStudentNavActive(item.key), ai: item.key === 'studentQa' }" @click="handleStudentNav(item.key)">
        <span><component :is="item.icon" :size="item.key === 'studentQa' ? 24 : 22" /></span>{{ item.label }}<i></i>
      </button>
    </nav>

    <Teleport to="body">
      <div v-if="active === 'studentQa'" class="qa-modern-page qa-teleport-layer">
        <form class="input-dock-container" @submit.prevent="askGlobal">
          <transition name="qa-jump-latest-pop">
            <button v-if="showQaLatestButton" class="qa-jump-latest-btn" type="button" title="回到最新消息" aria-label="回到最新消息" @click="scrollQaToLatest()">
              <ChevronDown :size="20" />
            </button>
          </transition>
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
              <button type="button" class="attach-btn" :data-loading="globalQaImageUploading" :disabled="globalThinking || (globalConversationLoading && !globalMessages.length) || globalQaImageUploading || globalQaAttachments.length >= 3" title="上传图片" @click="globalQaImageInput?.click()"><Camera :size="18" /></button>
              <textarea
                ref="globalQuestionInput"
                v-model="globalQuestion"
                placeholder="输入问题"
                rows="1"
                @compositionstart="handleQuestionCompositionStart('global')"
                @compositionend="handleQuestionCompositionEnd('global')"
                @keydown="handleGlobalQuestionKeydown"
              ></textarea>
              <button v-if="globalThinking" type="button" class="send-btn send-btn-stop" title="停止生成" aria-label="停止生成" @click="stopGlobalGeneration"><Square :size="18" /></button>
              <button v-else :disabled="(!globalQuestion.trim() && !globalQaAttachments.length) || (globalConversationLoading && !globalMessages.length) || globalQaImageUploading" class="send-btn"><Send :size="20" /></button>
            </section>
          </div>
        </form>
        <transition name="fade-slide"><button v-if="historyOpen" type="button" class="history-drawer-backdrop" aria-label="关闭问答历史" @click="closeQaHistory"></button></transition>
        <transition name="drawer">
          <aside v-if="historyOpen" class="history-drawer">
            <div class="history-drawer-sticky">
              <div class="drawer-head"><h2>{{ courseScopeName }}问答历史</h2><div class="drawer-head-actions"><button type="button" class="history-favorite-toggle" :class="{ checked: showFavorites }" :aria-pressed="showFavorites" @click="showFavorites = !showFavorites"><span class="favorite-check-box" aria-hidden="true"></span><strong>仅看收藏</strong></button><button class="drawer-close-btn" type="button" @click="closeQaHistory"><X :size="16" /></button></div></div>
              <div class="pretty-input"><Search :size="15" /><input v-model="qaKeyword" placeholder="搜索本课程历史问答" @keyup.enter="loadQaHistory" /></div>
            </div>
            <div class="history-drawer-list">
              <div v-for="item in filteredQaHistory" :key="item.conversation_id" class="history-row-wrap" :class="{ active: routeQaConversationId() === Number(item.conversation_id) }">
                <button class="history-row" type="button" @click="openQaConversation(item)"><MessageCircle :size="13" /><span>{{ item.question }}</span><small>{{ formatTime(item.created_at) }}<template v-if="item.record_count > 1"> · {{ item.record_count }} 条</template></small></button>
                <button class="history-del-btn" type="button" title="删除该问答历史" aria-label="删除该问答历史" @click.stop="requestDeleteQaHistory(item)"><Trash2 :size="14" /></button>
              </div>
              <EmptyState v-if="!filteredQaHistory.length" text="本课程暂无问答记录" />
            </div>
          </aside>
        </transition>
      </div>

      <MaterialPreviewModal :open="!!materialPreviewItem" :item="materialPreviewItem" :detail="materialPreviewDetail" :loading="materialPreviewLoading" @download="downloadMaterial" @close="closeMaterialPreview" />

      <ConfirmDialog
        :open="leaveConfirmOpen"
        title="退出课程"
        :message="`确认退出课程《${leaveTargetCourse?.name || ''}》？退出后学习进度可能丢失。`"
        confirm-text="确认退出"
        cancel-text="再想想"
        tone="danger"
        @confirm="confirmLeaveCourse"
        @cancel="cancelLeaveCourse"
      />

      <ConfirmDialog
        :open="deleteQaHistoryConfirmOpen"
        title="删除问答历史"
        :message="`确认删除这条问答历史？该会话下的全部问答记录将被永久删除，不可恢复。`"
        confirm-text="删除"
        cancel-text="取消"
        tone="danger"
        @confirm="confirmDeleteQaHistory"
        @cancel="deleteQaHistoryConfirmOpen = false"
      />

      <transition name="modal-pop">
        <div v-if="joinOpen" class="modal-mask student-modal-scope">
          <article class="join-modal">
            <div class="modal-head"><PlusCircle :size="22" /><h2>加入新课程</h2><button @click="joinOpen = false"><X :size="16" /></button></div>
            <label>课程码</label>
            <div class="code-input" :class="{ ok: joinPreview && !joinPreview.already_joined, error: joinError }"><input v-model="joinCode" maxlength="12" @input="formatJoinCode" /><LoadingMark v-if="joinChecking" :label="false" class="inline-loading-mark" /><CheckCircle v-if="joinPreview && !joinChecking" :size="18" /><XCircle v-if="joinError" :size="18" /></div>
            <small class="field-error" v-if="joinError">{{ joinError }}</small>
            <article v-if="joinPreview" class="preview-course"><span :class="{ 'has-image': joinPreview.course.cover_url }" :style="courseCoverStyle(joinPreview.course)"><strong v-if="!joinPreview.course.cover_url" class="course-cover-mini-text">{{ courseCoverText(joinPreview.course) }}</strong></span><div><strong>{{ joinPreview.course.name }}</strong><small>{{ joinPreview.teacher?.nickname || '教师' }} · {{ joinPreview.course.term }} · {{ joinPreview.student_count }}人</small></div></article>
            <div class="hint-line"><Info :size="14" />加入后即可学习课程内容</div>
            <footer><button class="btn btn-ghost" @click="joinOpen = false">取消</button><button class="btn btn-primary" :data-loading="joinChecking" :disabled="joinChecking || !joinPreview || joinPreview.already_joined" @click="confirmJoin">确认加入</button></footer>
          </article>
        </div>
      </transition>

      <transition name="modal-pop">
        <div v-if="planModalOpen" class="modal-mask student-modal-scope">
          <article class="join-modal">
            <div class="modal-head"><Sparkles :size="22" /><h2>AI 学习计划</h2><button @click="planModalOpen = false"><X :size="16" /></button></div>
            <textarea v-model="planForm.goal" class="textarea" placeholder="学习目标"></textarea>
            <div class="form-row"><input v-model.number="planForm.daily_minutes" class="input" type="number" /><input v-model.number="planForm.available_days" class="input" type="number" /></div>
            <footer><button class="btn btn-ghost" @click="planModalOpen = false">取消</button><button class="btn btn-primary" @click="createPlan">采用计划</button></footer>
          </article>
        </div>
      </transition>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, Teleport, Transition, watch, type PropType, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Award, BarChart2, Bell, BookMarked, BookOpen, CalendarCheck, Camera, Check,
  CheckCircle, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, Cpu, Download, FileText, Flame, FolderOpen, GitBranch, Grid2X2,
  Eye, History, IdCard, Info, Flag, Layers, ListChecks, LogOut, Mail, Maximize, MessageCircle, PanelRight,
  Pause, Pencil, Play, Plus, PlusCircle, Presentation, Quote, RefreshCw, Search, Send, Settings,
  Shield, Sparkles, Square, Star, Sun, Trash2, Type, User, Users, Wifi, X, XCircle, Zap
} from "../icons";
import { api, setToken } from "../api/client";
import { routeByPage } from "../router";
import type { Lesson, LessonDetail, LessonPage, Material, MaterialDetail, PageActivity, Quiz, User as UserType } from "../types";
import { copyToClipboard } from "../utils/clipboard";
import { extractStructuredText, renderRichText } from "../utils/richText";
import AppCheckbox from "../components/AppCheckbox.vue";
import AppProgress from "../components/AppProgress.vue";
import AppSelect from "../components/AppSelect.vue";
import AppSlider from "../components/AppSlider.vue";
import BrandLogo from "../components/BrandLogo.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import DocumentPreviewSurface from "../components/DocumentPreviewSurface.vue";
import DropdownMenu from "../components/DropdownMenu";
import LoadingMark from "../components/LoadingMark.vue";
import MaterialPreviewModal from "../components/MaterialPreviewModal.vue";
import PageLoader from "../components/PageLoader.vue";
import PasswordField from "../components/PasswordField.vue";
import SelectMenu from "../components/SelectMenu";
import ThemeToggle from "../components/ThemeToggle.vue";
import ChatList from "./student/components/ChatList";
import "../styles/student/base.css";
import "../styles/student/study-room.css";
import "../styles/student/courses.css";
import "../styles/student/qa.css";
import "../styles/student/quiz.css";
import "../styles/student/plan-profile.css";
import "../styles/student/tutoring.css";
import "../styles/student/classagent.css";

type QaAttachment = { type: string; url: string; filename?: string; size_bytes?: number; ocr_text?: string };
type ChatMessage = { id: number; role: "user" | "ai"; text: string; sources?: any[]; attachments?: QaAttachment[]; thought?: string; thoughtOpen?: boolean; record_id?: number; favorite?: boolean; feedback?: "positive" | "negative" | null; outOfScope?: boolean; streaming?: boolean; statusText?: string };
type QaHistoryConversation = { id: number; conversation_id: number; course_id: number; user_id: number; title: string; question: string; answer_preview?: string; created_at: string; updated_at?: string; lesson_page_id?: number | null; attachments?: QaAttachment[]; is_favorite?: boolean; record_count: number };
type QaInputScope = "class" | "global";
type StudentSearchResultType = "course" | "lesson" | "material" | "knowledge" | "qa";
type StudentSearchResult = {
  key: string;
  type: StudentSearchResultType;
  title: string;
  subtitle: string;
  excerpt?: string;
  courseId?: number;
  lessonId?: number;
  knowledgeId?: number | null;
  chapterId?: number | null;
  qaItem?: any;
  rank: number;
  order: number;
};

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string]; authed: [user: UserType] }>();
const route = useRoute();
const router = useRouter();

const LESSON_LAYOUT_STORAGE_KEY = "student_lesson_panel_ratio_v2";
const LESSON_LAYOUT_DEFAULT_RATIO = 0.24;
const LESSON_LAYOUT_MIN_RATIO = 0.18;
const LESSON_LAYOUT_MAX_RATIO = 0.62;
const LESSON_RESIZER_WIDTH = 18;
const LESSON_LAYOUT_MIN_RIGHT = 336;

function savedLessonPanelRatio() {
  const value = Number(localStorage.getItem(LESSON_LAYOUT_STORAGE_KEY));
  return Number.isFinite(value) && value > 0 ? Math.min(LESSON_LAYOUT_MAX_RATIO, Math.max(LESSON_LAYOUT_MIN_RATIO, value)) : LESSON_LAYOUT_DEFAULT_RATIO;
}

function currentRoutePageKey() {
  return String(route.meta.pageKey || props.pageKey || "studentHome");
}

const active = ref(currentRoutePageKey());
const dashboard = ref<any>({});
const profilePayload = ref<any>({});
const courses = ref<any[]>([]);
const studentPageLoading = ref(true);
const initialStudentLoading = ref(true);
const courseHome = ref<any>({});
const courseHomeLoading = ref(false);
const courseHomeError = ref("");
const selectedCourseId = ref<number>(Number(localStorage.getItem("student_current_course_id") || 0));
const notifications = ref<any[]>([]);
const lessons = ref<any[]>([]);
const materialsExpanded = ref(false);
const courseSection = ref("lessons");
const materialPreviewItem = ref<any | null>(null);
const materialPreviewDetail = ref<MaterialDetail | null>(null);
const materialPreviewLoading = ref(false);

const searchOpen = ref(false);
const globalSearch = ref("");
const searchInput = ref<HTMLInputElement | null>(null);
const searchLoading = ref(false);
const searchError = ref("");
const searchResults = ref<StudentSearchResult[]>([]);
const searchActiveIndex = ref(-1);
const searchCourseHomeCache = reactive<Record<number, any>>({});
const searchKnowledgeCache = reactive<Record<number, any[]>>({});
const searchQaCache = reactive<Record<string, any[]>>({});
const searchCourseHomePending = new Map<number, Promise<any>>();
const searchKnowledgePending = new Map<number, Promise<any[]>>();
const searchQaPending = new Map<string, Promise<any[]>>();
let searchTimer: number | undefined;
let searchRequestSeq = 0;
const noticeOpen = ref(false);
const notificationLoading = ref(false);
const notificationReading = ref(false);
const userMenuOpen = ref(false);
const topNavRef = ref<HTMLElement | null>(null);
const topNavIndicator = reactive({ left: 0, width: 0, ready: false });
const pageTransitionName = ref("student-page-forward");
const pageStageRef = ref<HTMLElement | null>(null);
const pageSwitching = ref(false);
const pageStageHeight = ref(0);
const topActionsRef = ref<HTMLElement | null>(null);
const noticePopRef = ref<HTMLElement | null>(null);
const userPopRef = ref<HTMLElement | null>(null);
const joinOpen = ref(false);
const leaveConfirmOpen = ref(false);
const leaveTargetCourse = ref<any | null>(null);
const deleteQaHistoryConfirmOpen = ref(false);
const deleteQaHistoryTarget = ref<any | null>(null);
const joinCode = ref("");
const joinPreview = ref<any | null>(null);
const joinChecking = ref(false);
const joinError = ref("");
let joinTimer: number | undefined;
let notificationTimer: number | undefined;
let topNavIndicatorFrame = 0;
let pageTransitionTimer: number | undefined;

const courseKeyword = ref("");
const termFilter = ref("");
const courseTab = ref<"active" | "done">("active");
const quickCourseQuestion = ref("");
const pageStageStyle = computed(() => (
  pageSwitching.value && pageStageHeight.value > 0
    ? { height: `${pageStageHeight.value}px` }
    : undefined
));

const classroomOpen = ref(false);
const classroomLesson = ref<LessonDetail | null>(null);
const lessonStudyLoading = ref(active.value === "studentLessonStudy");
const lessonStudyError = ref("");
const studentFullscreenLoading = computed(() => initialStudentLoading.value || (
  active.value === "studentCourseHome" && courseHomeLoading.value
) || (
  active.value === "studentLessonStudy" && !lessonStudyError.value && (!classroomOpen.value || lessonStudyLoading.value)
));
const openingLessonId = ref<number | null>(null);
const studyRoomRef = ref<HTMLElement | null>(null);
const studyMainRef = ref<HTMLElement | null>(null);
const slideStageRef = ref<HTMLElement | null>(null);
const slideCardMeasureRef = ref({ width: 0, height: 0 });
const lessonPanelRatio = ref(savedLessonPanelRatio());
const lessonPanelRatioCustomized = ref(false);
const lessonResizeActive = ref(false);
const compactLessonLayout = ref(false);
const lessonFullscreen = ref(false);
const lessonLayoutWidth = ref(typeof window === "undefined" ? 0 : window.innerWidth || 0);
const slideViewportFitScale = ref(1);
const currentPage = ref(1);
const pendingSourcePageNumber = ref<number | null>(null);
const pendingSourcePageId = ref<number | null>(null);
const pageDirection = ref<"next" | "prev">("next");
const classroomTab = ref<"script" | "activity" | "qa" | "note">("script");
const classMessages = ref<ChatMessage[]>([]);
const classQuestion = ref("");
const classThinking = ref(false);
let classAbortController: AbortController | null = null;
let globalAbortController: AbortController | null = null;
const classConversationLoading = ref(false);
const classConversationId = ref<number | null>(null);
const classQaImageInput = ref<HTMLInputElement | null>(null);
const classQuestionInput = ref<HTMLTextAreaElement | null>(null);
const globalQuestionInput = ref<HTMLTextAreaElement | null>(null);
const classQaAttachments = ref<QaAttachment[]>([]);
const classQaImageUploading = ref(false);
const lessonSelectionMenu = reactive({ open: false, text: "", x: 0, y: 0 });
const lessonAskContext = ref("");
const questionCompositionState = reactive<Record<QaInputScope, { active: boolean; endedAt: number }>>({
  class: { active: false, endedAt: 0 },
  global: { active: false, endedAt: 0 }
});
const aiPanelOpen = ref(true);
const chromeVisible = ref(true);
const thumbOpen = ref(false);
const settingsOpen = ref(false);
const subtitleMode = ref<"full" | "keyword" | "hide">("hide");
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlaying = ref(false);
const playbackRate = ref(1);
const audioProgress = ref(0);
const studySeconds = ref(0);
// #35：上报学习时长时使用真实停留秒数的增量，而不是写死的 +30 秒。
// reportedStudySeconds 记录上次已上报到 studySeconds 的位置，每次上报真实差值。
const reportedStudySeconds = ref(0);
const completeOpen = ref(false);
const pageNote = ref("");
const pageNoteArea = ref<HTMLTextAreaElement | null>(null);
const noteState = ref("已保存");
const noteSavedAt = ref("尚未保存");
let chromeTimer: number | undefined;
let studyTimer: number | undefined;
let noteTimer: number | undefined;
let lessonLoadSeq = 0;
let courseHomeLoadSeq = 0;
let suppressCourseScopedReset = false;
let qaScrollFrame = 0;
let lessonSelectionTimer: number | undefined;
let qaConversationLoadSeq = 0;
let classConversationLoadSeq = 0;
let slideStageResizeObserver: ResizeObserver | undefined;

const globalMessages = ref<ChatMessage[]>([]);
const globalQuestion = ref("");
const globalThinking = ref(false);
const globalConversationLoading = ref(false);
const globalConversationId = ref<number | null>(null);
const globalQaImageInput = ref<HTMLInputElement | null>(null);
const globalQaAttachments = ref<QaAttachment[]>([]);
const globalQaImageUploading = ref(false);
const qaHistory = ref<QaHistoryConversation[]>([]);
const qaKeyword = ref("");
const historyOpen = ref(false);
const showFavorites = ref(false);
const showQaLatestButton = ref(false);

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
const practiceDifficulty = ref("mixed");
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
const studentAvatarInput = ref<HTMLInputElement | null>(null);
const avatarUploading = ref(false);
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
const studentCourseNavKeys = ["studentCourses", "studentCourseHome", "studentMaterials", "studentKnowledge", "studentQuizzes", "studentTutoring", "studentPlans"];
const topNavTabs = [
  { key: "studentHome", label: "工作台", icon: BookOpen },
  { key: "studentCourses", label: "我的课程", icon: Presentation },
  { key: "studentQa", label: "AI 问答", icon: Sparkles },
  { key: "studentWrongBook", label: "错题本", icon: BookMarked }
];
const speedItems = ["0.5", "0.75", "1", "1.25", "1.5", "2"].map((value) => ({ label: `${value}x`, value }));
const levelItems = [{ label: "入门", value: "beginner" }, { label: "标准", value: "standard" }, { label: "进阶", value: "advanced" }];
const quizCountOptions = ["5题", "10题", "15题", "20题"];
const quizDifficultyOptions = [
  { label: "混合（易中难梯度）", value: "mixed" },
  { label: "基础", value: "easy" },
  { label: "标准", value: "standard" },
  { label: "较难", value: "hard" },
];
const wrongStatusOptions = [{ label: "全部状态", value: "" }, { label: "待重练", value: "todo" }, { label: "已掌握", value: "resolved" }, { label: "多次错误", value: "repeat" }];
const courseMenuItems = [{ label: "课程详情", value: "detail" }, { label: "问答记录", value: "qa" }, { label: "分享课程码", value: "share" }, { label: "退出课程", value: "leave", danger: true }];
const studentSearchTypeMeta: Record<StudentSearchResultType, { label: string; icon: any }> = {
  course: { label: "课程", icon: Presentation },
  lesson: { label: "课时", icon: Play },
  material: { label: "资料", icon: FolderOpen },
  knowledge: { label: "知识点", icon: Layers },
  qa: { label: "问答", icon: MessageCircle },
};

function studentTopNavGroupKey(key: string) {
  return studentCourseNavKeys.includes(key) ? "studentCourses" : key;
}

function studentTopNavIndex(key: string) {
  const groupKey = studentTopNavGroupKey(key);
  return topNavTabs.findIndex((item) => item.key === groupKey);
}

function setStudentPageTransition(nextKey: string, fromKey = active.value) {
  const fromIndex = studentTopNavIndex(fromKey);
  const nextIndex = studentTopNavIndex(nextKey);
  if (fromIndex < 0 || nextIndex < 0 || fromIndex === nextIndex) {
    pageTransitionName.value = "student-page-forward";
    return;
  }
  pageTransitionName.value = nextIndex < fromIndex ? "student-page-back" : "student-page-forward";
}

function studentPageElementHeight(el?: Element | null) {
  if (!(el instanceof HTMLElement)) return 0;
  return Math.ceil(Math.max(el.scrollHeight, el.offsetHeight, el.getBoundingClientRect().height));
}

function lockStudentPageStage(height = 0) {
  if (pageTransitionTimer) {
    window.clearTimeout(pageTransitionTimer);
    pageTransitionTimer = undefined;
  }
  const stageHeight = pageStageRef.value?.getBoundingClientRect().height || 0;
  const nextHeight = Math.ceil(Math.max(height, stageHeight, pageStageHeight.value));
  if (nextHeight > 0) pageStageHeight.value = nextHeight;
  pageSwitching.value = true;
}

function beforeStudentPageLeave(el: Element) {
  lockStudentPageStage(studentPageElementHeight(el));
}

function beforeStudentPageEnter(el: Element) {
  pageSwitching.value = true;
  void nextTick(() => {
    window.requestAnimationFrame(() => {
      lockStudentPageStage(studentPageElementHeight(el));
    });
  });
}

function finishStudentPageTransition() {
  if (pageTransitionTimer) window.clearTimeout(pageTransitionTimer);
  pageTransitionTimer = window.setTimeout(() => {
    pageSwitching.value = false;
    pageStageHeight.value = 0;
    pageTransitionTimer = undefined;
  }, 60);
}

function updateTopNavIndicator() {
  void nextTick(() => {
    if (topNavIndicatorFrame) window.cancelAnimationFrame(topNavIndicatorFrame);
    topNavIndicatorFrame = window.requestAnimationFrame(() => {
      topNavIndicatorFrame = 0;
      const nav = topNavRef.value;
      const activeButton = nav?.querySelector<HTMLElement>(".student-nav-link.active");
      if (!nav || !activeButton || activeButton.offsetWidth <= 0) {
        topNavIndicator.ready = false;
        return;
      }
      topNavIndicator.left = activeButton.offsetLeft;
      topNavIndicator.width = activeButton.offsetWidth;
      topNavIndicator.ready = true;
    });
  });
}

const stats = computed(() => dashboard.value.stats || profilePayload.value.stats || {});
// #33：后端 stats 目前只返回当前连续天数(streak_days)，没有“历史最长连续”字段。
// 仅当后端补上 longest_streak 才显示真实值，否则返回 null 由模板渲染占位符，不再把当前连续天数冒充成最长。
const longestStreakDays = computed<number | null>(() => {
  const raw = (stats.value as any).longest_streak ?? (stats.value as any).longest_streak_days;
  return raw === undefined || raw === null ? null : Number(raw);
});
const planTodayTasks = computed(() => tasks.value.filter((task: any) => taskDateKey(task) === todayTaskKey()));
const todayTasks = computed(() => {
  if (active.value === "studentPlans") return planTodayTasks.value;
  const dashboardTasks = Array.isArray(dashboard.value.today_tasks) ? dashboard.value.today_tasks : [];
  return dashboardTasks.length ? dashboardTasks : planTodayTasks.value;
});
const doneTasks = computed(() => todayTasks.value.filter((task: any) => task.status === "done").length);
const todayDoneRate = computed(() => todayTasks.value.length ? Math.round(doneTasks.value / todayTasks.value.length * 100) : 0);
const nextTodayTask = computed(() => todayTasks.value.find((task: any) => task.status !== "done") || todayTasks.value[0] || null);
const todayPlanSummary = computed(() => {
  const task = nextTodayTask.value;
  if (!task) return "";
  const title = String(task.title || "学习任务").trim();
  const minutes = Number(task.estimated_minutes || 0);
  const timeText = Number.isFinite(minutes) && minutes > 0 ? `${minutes}分钟` : (task.task_type || "学习");
  return `${task.status === "done" ? "已完成" : "待完成"}：${title} · ${timeText}`;
});
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
// 学期信息来源于后端课程的 term 字段，没有真实学期起止日期时只展示学期名，不再编造“距结束 X 天”的假倒计时。
const currentTermLabel = computed(() => {
  const terms = Array.from(new Set(courses.value.map((course) => String(course.term || "").trim()).filter(Boolean)));
  return terms.length === 1 ? terms[0] : "";
});
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
const isLessonOpening = computed(() => openingLessonId.value !== null);
const baseCourseMaterials = computed(() => (courseHome.value.materials || []).slice(0, 5));
const extraCourseMaterials = computed(() => (courseHome.value.materials || []).slice(5));
const searchKeyword = computed(() => globalSearch.value.trim());
const searchResultGroups = computed(() => (["course", "lesson", "material", "knowledge", "qa"] as StudentSearchResultType[])
  .map((type) => ({
    type,
    label: studentSearchTypeMeta[type].label,
    items: searchResults.value.filter((item) => item.type === type),
  }))
  .filter((group) => group.items.length));
const flatSearchResults = computed(() => searchResultGroups.value.flatMap((group) => group.items));
const activePage = computed(() => classroomLesson.value?.pages.find((page) => page.page_number === currentPage.value) || classroomLesson.value?.pages[0] || null);
const classroomOriginalMaterial = computed<Material | null>(() => {
  const material = classroomLesson.value?.material || null;
  if (!material?.id) return null;
  const type = String(material.material_type || "").toLowerCase();
  return ["pdf", "ppt", "pptx", "doc", "docx", "txt", "md", "markdown"].includes(type) ? material : null;
});
const hasActiveAudio = computed(() => Boolean(activePage.value?.audio_url));
const lessonSelectionMenuStyle = computed(() => ({
  left: `${lessonSelectionMenu.x}px`,
  top: `${lessonSelectionMenu.y}px`,
}));
const lessonAskContextPreview = computed(() => selectionPreviewText(lessonAskContext.value));
const classQuestionPlaceholder = computed(() => lessonAskContext.value ? "需要问点什么？" : "问问 AI 这一页...");
const studyLayoutStyle = computed(() => {
  if (compactLessonLayout.value || !aiPanelOpen.value) return undefined;
  const totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0;
  const bounds = lessonPanelBounds(totalWidth);
  const ratio = clampLessonPanelRatio(lessonPanelRatio.value, totalWidth);
  const rightWidth = Math.round(Math.min(bounds.maxRight, Math.max(bounds.minRight, ratio * bounds.availableWidth)));
  return {
    gridTemplateColumns: `minmax(min(${bounds.minLeft}px,72vw),1fr) ${LESSON_RESIZER_WIDTH}px minmax(${bounds.minRight}px,${rightWidth}px)`,
  };
});
const activePageActivities = computed<PageActivity[]>(() => activePage.value?.pedagogy || []);
const pageSummaryActivity = computed(() => activePageActivities.value.find((item) => item.type === "page_summary") || null);
const conceptActivities = computed(() => activePageActivities.value.filter((item) => item.type === "concept_card"));
const problemTemplateActivities = computed(() => activePageActivities.value.filter((item) => item.type === "problem_template"));
const misconceptionActivities = computed(() => activePageActivities.value.filter((item) => item.type === "misconception_card"));
const quickCheckActivities = computed(() => activePageActivities.value.filter((item) => item.type === "quick_check"));
const discussionActivities = computed(() => activePageActivities.value.filter((item) => item.type === "discussion_prompt"));
const demoActivities = computed(() => activePageActivities.value.filter((item) => item.type === "demo"));
const discussionDemoActivities = computed(() => [...discussionActivities.value, ...demoActivities.value]);
const learningObjectiveItems = computed(() => payloadList(pageSummaryActivity.value, "learning_objectives"));
const keyPointItems = computed(() => {
  const items = payloadList(pageSummaryActivity.value, "key_points");
  if (items.length) return items;
  return conceptActivities.value.map((item) => item.payload?.knowledge_point || item.title.replace("：知识点", "")).filter(Boolean).slice(0, 6);
});
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
const slideViewportStyle = computed(() => ({
  "--lesson-slide-fit-scale": String(slideViewportFitScale.value),
}));
const slideCardShellStyle = computed(() => {
  const scale = slideViewportFitScale.value;
  const baseWidth = Math.max(slideCardMeasureRef.value.width, 1160);
  const baseHeight = Math.max(slideCardMeasureRef.value.height, 620);
  return {
    "--lesson-slide-base-width": `${baseWidth}px`,
    "--lesson-slide-base-height": `${baseHeight}px`,
    "--lesson-slide-shell-width": `${Math.max(1, Math.round(baseWidth * scale))}px`,
    "--lesson-slide-shell-height": `${Math.max(1, Math.round(baseHeight * scale))}px`,
  };
});
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
  const structured = [...quickCheckActivities.value, ...discussionActivities.value].map(activityQuestion).filter(Boolean);
  if (structured.length) return Array.from(new Set(structured)).slice(0, 4);
  const title = activePage.value?.page_title || classroomLesson.value?.lesson?.title || "当前页面";
  return [`${title} 的重点？`, `用例子解释 ${title}`, `根据 ${title} 出道题`, `总结 ${title}`];
});
const studyClock = computed(() => `${String(Math.floor(studySeconds.value / 60)).padStart(2, "0")}:${String(studySeconds.value % 60).padStart(2, "0")}`);
const audioTime = computed(() => timeLabel(audioRef.value?.currentTime || 0));
const audioDuration = computed(() => timeLabel(audioRef.value?.duration || activePage.value?.audio_duration_seconds || 0));
// #66：此前是写死的“假 AI 总结”。后端没有按课时生成 AI 学情总结的接口，
// 因此这里改为基于本次会话真实数据(学习时长/页数/提问数)的事实性小结，且不再冒充 AI 生成。
const completionSummary = computed(() => {
  const minutes = Math.max(1, Math.round(studySeconds.value / 60));
  const pages = classroomLesson.value?.pages.length || 0;
  const questions = classMessages.value.filter((m) => m.role === "user").length;
  const parts = [`本次学习约 ${minutes} 分钟`];
  if (pages) parts.push(`共 ${pages} 页`);
  parts.push(questions ? `提问 ${questions} 次` : "本次没有提问");
  return `${parts.join("，")}。建议继续完成配套练习并整理课时笔记。`;
});
const filteredQaHistory = computed<QaHistoryConversation[]>(() => {
  const keyword = qaKeyword.value.trim();
  return qaHistory.value
    .filter((item) => {
      if (showFavorites.value && !item.is_favorite) return false;
      if (!keyword) return true;
      return [item.title, item.question, item.answer_preview].some((value) => String(value || "").includes(keyword));
    })
    .sort((left, right) => timestampMs(right.created_at) - timestampMs(left.created_at));
});
const selectedKnowledge = computed(() => knowledge.value.find((item) => item.id === selectedKnowledgeId.value) || knowledge.value[0] || null);
// #34：后端没有“掌握度百分比”，此前用 `Math.max(35, 90 - impact*12)` 拍脑袋编了个数。
// 改为只依据后端真实的薄弱点信号(weak_score / wrong_count)给出定性评估；
// 知识点不在薄弱点列表中即代表暂无评估数据，不再编造百分比进度条。
const selectedKnowledgeWeak = computed(() => weakPoints.value.find((item) => item.knowledge_point === selectedKnowledge.value?.name) || null);
const knowledgeMasteryAssessed = computed(() => !!selectedKnowledgeWeak.value);
const knowledgeMasteryText = computed(() => {
  if (!knowledgeMasteryAssessed.value) return "暂无评估";
  const impact = Number(selectedKnowledgeWeak.value?.weak_score ?? selectedKnowledgeWeak.value?.wrong_count ?? 0);
  return impact >= 3 ? "薄弱" : "待加强";
});
const knowledgeMasteryClass = computed(() => {
  if (!knowledgeMasteryAssessed.value) return "tag";
  const impact = Number(selectedKnowledgeWeak.value?.weak_score ?? selectedKnowledgeWeak.value?.wrong_count ?? 0);
  return impact >= 3 ? "tag-danger" : "tag-warning";
});
const knowledgeContent = computed(() => selectedKnowledge.value?.content_by_level?.[knowledgeLevel.value] || {});
const courseQuizzes = computed(() => quizzes.value.filter((quiz) => quiz.quiz_type === "course"));
const practiceQuizzes = computed(() => quizzes.value
  .filter((quiz) => quiz.quiz_type !== "course")
  .sort((left, right) => timestampMs(practiceRecordTime(right)) - timestampMs(practiceRecordTime(left))));
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
  const timeMs = timestampMs(time);
  return timeMs > 0 && Date.now() - timeMs < 7 * 86400000;
}).length);
const monthlyCheckins = computed(() => checkinDays.value.filter((day) => day.slice(0, 7) === new Date().toISOString().slice(0, 7)).length);
// #32：后端暂无“每日学习时长”时间序列接口，不再用写死的假数组糊弄。
// 仅展示真实存在的整体学习总时长，按天的柱状分布需后端补 daily 接口后再接入。
const weeklyHours = computed<number[]>(() => []);
const totalWeeklyHours = computed(() => Number((stats.value.study_hours || 0).toFixed(1)));
const hasWeeklyChartData = computed(() => weeklyHours.value.some((value) => Number(value || 0) > 0));
const weeklyChart = computed(() => {
  const labels = ["一", "二", "三", "四", "五", "六", "日"];
  const max = Math.max(1, ...weeklyHours.value.map((value) => Number(value || 0)));
  return labels.map((label, index) => {
    const value = Number(weeklyHours.value[index] || 0);
    return { label, value, percent: value <= 0 ? 0 : Math.max(12, Math.round(value / max * 100)) };
  });
});
const weekDays = computed(() => {
  const now = new Date();
  // Monday(0) .. Sunday(6) index of today; getDay() => 0=Sun..6=Sat
  const todayIndex = (now.getDay() + 6) % 7;
  // Date of this week's Monday at local midnight
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - todayIndex);
  return ["一", "二", "三", "四", "五", "六", "日"].map((label, index) => {
    const dayDate = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + index);
    const iso = localDateKey(dayDate);
    return { label, done: checkinDays.value.includes(iso), today: index === todayIndex };
  });
});
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

watch(() => [props.pageKey, route.fullPath], async () => { await syncRouteState(); });
watch(active, () => updateTopNavIndicator(), { flush: "post" });
watch(selectedCourseId, async (id, previousId) => {
  if (id) localStorage.setItem("student_current_course_id", String(id));
  if (id === previousId) return;
  if (suppressCourseScopedReset) return;
  resetCourseScopedState();
  if (active.value === "studentQa") {
    await loadCourseHome();
    await loadQaHistory();
  }
  if (active.value === "studentWrongBook") await loadWrongBook();
  if (active.value === "studentTutoring") await loadProblemHistory();
  if (active.value === "studentKnowledge") await loadKnowledge();
  if (active.value === "studentQuizzes") await loadQuizPage();
  if (active.value === "studentPlans") await loadPlans();
});
watch(activePage, async (page) => {
  if (audioRef.value) {
    audioRef.value.pause();
    audioRef.value.currentTime = 0;
  }
  audioPlaying.value = false;
  audioProgress.value = 0;
  if (page) await loadNote(page.id);
}, { immediate: false });
watch(globalSearch, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer);
  if (!searchOpen.value) return;
  const keyword = value.trim();
  const requestSeq = ++searchRequestSeq;
  if (!keyword) {
    searchLoading.value = false;
    searchError.value = "";
    searchResults.value = [];
    searchActiveIndex.value = -1;
    return;
  }
  searchLoading.value = true;
  searchError.value = "";
  searchTimer = window.setTimeout(() => { void performGlobalSearch(keyword, requestSeq); }, 220);
});
watch(flatSearchResults, (items) => {
  if (!items.length) {
    searchActiveIndex.value = -1;
    return;
  }
  if (searchActiveIndex.value < 0 || searchActiveIndex.value >= items.length) searchActiveIndex.value = 0;
});
watch(active, async (page) => {
  if (page !== "studentQa") {
    showQaLatestButton.value = false;
    return;
  }
  await nextTick();
  updateQaLatestButton();
}, { flush: "post" });
watch(() => globalMessages.value.length, async (length, previousLength) => {
  if (active.value !== "studentQa") return;
  const shouldFollow = previousLength === 0 || isQaNearLatest(360);
  await nextTick();
  if (length && shouldFollow) scrollQaToLatest(false);
  else updateQaLatestButton();
}, { flush: "post" });

async function run<T>(task: () => Promise<T>, ok?: string) { try { const data = await task(); if (ok) emit("notice", "success", ok); return data; } catch (error) { emit("notice", "error", (error as Error).message); return null; } }
function queuedQuizMessage(result: any, fallback = "题目已加入生成队列，生成成功后会通知你") {
  if (result?.id) return "";
  return result?.status === "failed" ? "题目生成失败，请稍后重试" : fallback;
}
function courseRoute(id: number) { return `/courses/${id}`; }
function qaConversationRoute(id: number) { return `/qa/${id}`; }
function pageRoute(key: string) {
  if (key === "studentCourseHome") {
    const id = routeCourseId() || selectedCourseId.value;
    return id ? courseRoute(id) : "/courses";
  }
  return routeByPage[key] || "/home";
}
async function go(key: string) { await router.push(pageRoute(key)); }
async function syncRouteState() {
  const nextPageKey = currentRoutePageKey();
  const leavingLessonStudy = active.value === "studentLessonStudy" && nextPageKey !== "studentLessonStudy";
  setStudentPageTransition(nextPageKey);
  active.value = nextPageKey;
  if (leavingLessonStudy || (classroomOpen.value && nextPageKey !== "studentLessonStudy")) {
    lessonLoadSeq += 1;
    await leaveClassroom(true);
  }
  await loadActive();
}
async function handleStudentNav(key: string) {
  if (key === "studentQuizzes") {
    await openQuizSelection("practice");
    return;
  }
  setStudentPageTransition(key);
  await go(key);
}
function pruneSearchCache() {
  const validIds = new Set(courses.value.map((course) => Number(course.id)));
  Object.keys(searchCourseHomeCache).forEach((key) => {
    if (!validIds.has(Number(key))) delete searchCourseHomeCache[Number(key)];
  });
  Object.keys(searchKnowledgeCache).forEach((key) => {
    if (!validIds.has(Number(key))) delete searchKnowledgeCache[Number(key)];
  });
  Object.keys(searchQaCache).forEach((key) => {
    const [courseId] = key.split(":");
    if (!validIds.has(Number(courseId))) delete searchQaCache[key];
  });
}
async function loadCourses() {
  courses.value = (await run<any[]>(() => api.get("/student/courses"))) || [];
  pruneSearchCache();
  if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id;
}
async function loadDashboard(options: { refreshRecommendation?: boolean } = {}) {
  dashboard.value = (await run(() => api.get("/student/dashboard", options.refreshRecommendation ? { refresh_recommendation: true } : undefined))) || {};
  notifications.value = dashboard.value.notifications || [];
  courses.value = dashboard.value.courses || courses.value;
  pruneSearchCache();
  if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = courses.value[0].id;
}
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
async function markStudentNotificationsRead(item?: any) {
  const ids = item
    ? [String(item.id || "").trim()].filter(Boolean)
    : notifications.value.filter((notice) => notice.unread).map((notice) => String(notice.id || "").trim()).filter(Boolean);
  if (!ids.length || notificationReading.value) return;
  notificationReading.value = true;
  try {
    const updated = await api.post<any[]>("/student/notifications/read", { ids });
    notifications.value = updated || notifications.value.map((notice) => (ids.includes(String(notice.id || "")) ? { ...notice, unread: false } : notice));
    if (dashboard.value?.notifications) dashboard.value = { ...dashboard.value, notifications: notifications.value };
  } catch (error) {
    emit("notice", "error", (error as Error).message);
  } finally {
    notificationReading.value = false;
  }
}
async function loadCourseHome() {
  const routeId = routeCourseId();
  const isCourseRoute = active.value === "studentCourseHome";
  if (isCourseRoute && hasCourseRouteParam() && !routeId) {
    courseHome.value = {};
    lessons.value = [];
    courseHomeLoading.value = false;
    courseHomeError.value = "课程地址无效，请从课程列表重新进入。";
    return;
  }
  const courseId = isCourseRoute ? (routeId || selectedCourseId.value) : selectedCourseId.value;
  if (!courseId) {
    if (isCourseRoute) {
      courseHome.value = {};
      lessons.value = [];
      courseHomeLoading.value = false;
      courseHomeError.value = "";
    }
    return;
  }
  if (selectedCourseId.value !== courseId) selectedCourseId.value = courseId;
  const loadSeq = ++courseHomeLoadSeq;
  if (isCourseRoute) {
    courseHomeLoading.value = true;
    courseHomeError.value = "";
  }
  try {
    const home = (await api.get(`/student/courses/${courseId}/home`)) || {};
    if (loadSeq !== courseHomeLoadSeq) return;
    if (isCourseRoute && routeCourseId() && routeCourseId() !== courseId) return;
    courseHome.value = home;
    lessons.value = courseHome.value.lessons || [];
    courseHomeError.value = "";
  } catch (error) {
    if (loadSeq !== courseHomeLoadSeq) return;
    courseHome.value = {};
    lessons.value = [];
    const message = (error as Error).message || "课程加载失败，请稍后重试。";
    if (isCourseRoute) courseHomeError.value = message;
    else emit("notice", "error", message);
  } finally {
    if (loadSeq === courseHomeLoadSeq && isCourseRoute) courseHomeLoading.value = false;
  }
}
function applyStudentProfile(data: any) {
  if (!data) return;
  profilePayload.value = data;
  Object.assign(profileForm, {
    nickname: data.user?.nickname || props.user.nickname,
    avatar_url: data.user?.avatar_url || "",
    school: data.student_profile?.school || "",
    bio: data.user?.bio || "",
  });
  if (data.user) emit("authed", {
    ...props.user,
    nickname: data.user.nickname || props.user.nickname,
    avatar_url: data.user.avatar_url || null,
    bio: data.user.bio || null,
    updated_at: data.user.updated_at || props.user.updated_at,
  });
}
function normalizeNoticeSettings(settings: any) {
  return (Array.isArray(settings) ? settings : [])
    .filter((item: any) => item?.key && item.key !== "plan")
    .map((item: any) => ({ key: item.key, label: item.label, enabled: Boolean(item.enabled) }));
}
async function loadProfile() {
  const data: any = (await run<any>(() => api.get("/student/profile"))) || {};
  applyStudentProfile(data);
  noticeSettings.splice(0, noticeSettings.length, ...normalizeNoticeSettings(data.notification_settings));
}
async function loadActive() {
  studentPageLoading.value = true;
  try {
    if (active.value === "studentLessonStudy") {
      await loadLessonStudyRoute();
      return;
    }
    if (active.value === "studentHome") {
      await loadDashboard();
      const dashboardTasks = Array.isArray(dashboard.value.today_tasks) ? dashboard.value.today_tasks : [];
      if (!dashboardTasks.length) await loadPlans();
    }
    if (active.value === "studentCourses") await loadCourses();
    if (["studentQa", "studentWrongBook", "studentTutoring", "studentKnowledge", "studentQuizzes"].includes(active.value) && !courses.value.length) await loadCourses();
    if (["studentCourseHome", "studentMaterials"].includes(active.value)) await loadCourseHome();
    if (active.value === "studentQa") {
      if (routeQaConversationId()) await loadQaRouteConversation();
      else {
        if (globalConversationId.value) {
          globalConversationId.value = null;
          globalMessages.value = [];
          globalQaAttachments.value = [];
        }
        await loadCourseHome();
        await loadQaHistory();
      }
    }
    if (active.value === "studentTutoring") await loadProblemHistory();
    if (active.value === "studentKnowledge") await loadKnowledge();
    if (active.value === "studentQuizzes") await loadQuizPage();
    if (active.value === "studentWrongBook") await loadWrongBook();
    if (active.value === "studentPlans") await loadPlans();
    if (active.value === "studentProfile") await loadProfile();
  } finally {
    studentPageLoading.value = false;
    initialStudentLoading.value = false;
  }
}
async function openCourse(id: number) {
  const courseId = Number(id);
  if (!courseId) return;
  selectedCourseId.value = courseId;
  courseHomeError.value = "";
  courseHomeLoading.value = true;
  if (active.value === "studentCourseHome" && routeCourseId() === courseId) {
    await loadCourseHome();
    return;
  }
  try {
    await router.push(courseRoute(courseId));
  } catch (error) {
    courseHomeLoading.value = false;
    emit("notice", "error", (error as Error).message || "打开课程失败");
  }
}
async function openHomeRecommendedLesson() {
  if (!hasJoinedCourses.value) { joinOpen.value = true; return; }
  const lessonId = homeRecommendedLesson.value?.lesson?.id || activeCourse.value?.last_lesson?.id;
  if (lessonId) { await openLesson(Number(lessonId)); return; }
  await go("studentCourses");
}
async function openHomeRecommendedPractice() {
  if (!hasJoinedCourses.value) { joinOpen.value = true; return; }
  await openQuizSelection("practice");
}
function resetQuizWorkspace() {
  Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]);
  quizDetail.value = null;
  attempt.value = null;
  answeringQuiz.value = false;
}
function closeQuizWorkspace() {
  resetQuizWorkspace();
}
async function openQuizSelection(tab: "course" | "practice" = "practice") {
  quizTab.value = tab;
  resetQuizWorkspace();
  if (active.value === "studentQuizzes") {
    await loadQuizPage();
    return;
  }
  await go("studentQuizzes");
}
function scrollToLessons() { document.getElementById("lesson-list")?.scrollIntoView({ behavior: "smooth", block: "start" }); }
function qaScrollRoot() {
  return document.scrollingElement || document.documentElement;
}
function qaDistanceFromLatest() {
  const root = qaScrollRoot();
  const scrollTop = root.scrollTop || window.scrollY || 0;
  return Math.max(0, root.scrollHeight - root.clientHeight - scrollTop);
}
function isQaNearLatest(threshold = 220) {
  return qaDistanceFromLatest() <= threshold;
}
function updateQaLatestButton() {
  if (active.value !== "studentQa" || !globalMessages.value.length) {
    showQaLatestButton.value = false;
    return;
  }
  const root = qaScrollRoot();
  const hasLongConversation = root.scrollHeight - root.clientHeight > 260;
  showQaLatestButton.value = hasLongConversation && qaDistanceFromLatest() > 260;
}
function scheduleQaLatestButtonCheck() {
  if (qaScrollFrame) return;
  qaScrollFrame = window.requestAnimationFrame(() => {
    qaScrollFrame = 0;
    updateQaLatestButton();
  });
}
function scrollQaToLatest(smooth = true) {
  void nextTick(() => {
    const root = qaScrollRoot();
    const top = Math.max(0, root.scrollHeight - root.clientHeight);
    window.scrollTo({ top, behavior: smooth ? "smooth" : "auto" });
    showQaLatestButton.value = false;
    window.setTimeout(scheduleQaLatestButtonCheck, smooth ? 360 : 0);
  });
}
function keepQaAtLatestIfNeeded(wasNearLatest: boolean) {
  if (wasNearLatest) scrollQaToLatest(false);
  else scheduleQaLatestButtonCheck();
}
function searchTypeMeta(type: StudentSearchResultType) { return studentSearchTypeMeta[type]; }
function searchTeacherName(course: any) { return course?.teacher_name || course?.teacher?.nickname || course?.teacher?.name || ""; }
function normalizeSearchText(value?: unknown) { return String(value ?? "").replace(/\s+/g, " ").trim().toLowerCase(); }
function splitSearchTokens(value: string) {
  const tokens = normalizeSearchText(value).split(/[\s,，。；;、/|]+/).filter(Boolean);
  return tokens.length ? Array.from(new Set(tokens)) : [];
}
function searchScore(query: string, ...fields: unknown[]) {
  const haystack = normalizeSearchText(fields.filter(Boolean).map((field) => String(field)).join(" "));
  const keyword = normalizeSearchText(query);
  if (!haystack || !keyword) return -1;
  let score = 0;
  if (haystack === keyword) score += 120;
  if (haystack.startsWith(keyword)) score += 75;
  else if (haystack.includes(keyword)) score += 50;
  const tokens = splitSearchTokens(keyword);
  let matched = 0;
  tokens.forEach((token) => {
    if (haystack.includes(token)) {
      matched += 1;
      score += token.length > 1 ? 16 : 8;
    }
  });
  if (!haystack.includes(keyword) && tokens.length > 1 && matched < tokens.length) return -1;
  if (!haystack.includes(keyword) && matched === 0) return -1;
  return score;
}
function searchExcerpt(value?: unknown, max = 72) {
  const text = extractStructuredText(String(value ?? "")).replace(/\s+/g, " ").trim();
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}
function knowledgeExcerpt(item: any) {
  const preferred = item?.content_by_level?.standard || item?.content_by_level?.beginner || item?.content_by_level?.advanced || {};
  return searchExcerpt([preferred.definition, preferred.principle, preferred.example, preferred.common_mistake, item?.content, item?.description].filter(Boolean).join(" "));
}
function resetSearchState(clearKeyword = false) {
  if (searchTimer) window.clearTimeout(searchTimer);
  searchTimer = undefined;
  searchRequestSeq += 1;
  searchLoading.value = false;
  searchError.value = "";
  searchResults.value = [];
  searchActiveIndex.value = -1;
  if (clearKeyword) globalSearch.value = "";
}
function closeSearch() {
  searchOpen.value = false;
  resetSearchState(true);
}
async function openSearch() {
  searchOpen.value = true;
  if (!courses.value.length) void ensureSearchCoursesLoaded();
  await nextTick();
  searchInput.value?.focus();
}
async function ensureSearchCoursesLoaded() {
  if (courses.value.length) return courses.value;
  const data = await api.get<any[]>("/student/courses");
  courses.value = Array.isArray(data) ? data : [];
  pruneSearchCache();
  if ((!selectedCourseId.value || !courses.value.some((course) => course.id === selectedCourseId.value)) && courses.value[0]) selectedCourseId.value = Number(courses.value[0].id);
  return courses.value;
}
async function ensureSearchCourseHome(courseId: number) {
  if (searchCourseHomeCache[courseId]) return searchCourseHomeCache[courseId];
  const pending = searchCourseHomePending.get(courseId);
  if (pending) return pending;
  const task = api.get(`/student/courses/${courseId}/home`)
    .then((data) => {
      searchCourseHomeCache[courseId] = data || {};
      return searchCourseHomeCache[courseId];
    })
    .catch(() => null)
    .finally(() => { searchCourseHomePending.delete(courseId); });
  searchCourseHomePending.set(courseId, task);
  return task;
}
async function ensureSearchKnowledge(courseId: number) {
  if (searchKnowledgeCache[courseId]) return searchKnowledgeCache[courseId];
  const pending = searchKnowledgePending.get(courseId);
  if (pending) return pending;
  const task = api.get<any[]>("/learning/knowledge-points", { course_id: courseId })
    .then((data) => {
      searchKnowledgeCache[courseId] = Array.isArray(data) ? data : [];
      return searchKnowledgeCache[courseId];
    })
    .catch(() => [])
    .finally(() => { searchKnowledgePending.delete(courseId); });
  searchKnowledgePending.set(courseId, task);
  return task;
}
async function ensureSearchQa(courseId: number, keyword: string) {
  const cacheKey = `${courseId}:${normalizeSearchText(keyword)}`;
  if (searchQaCache[cacheKey]) return searchQaCache[cacheKey];
  const pending = searchQaPending.get(cacheKey);
  if (pending) return pending;
  const task = api.get<any[]>("/qa/history", { course_id: courseId, keyword })
    .then((data) => {
      searchQaCache[cacheKey] = Array.isArray(data) ? data : [];
      return searchQaCache[cacheKey];
    })
    .catch(() => [])
    .finally(() => { searchQaPending.delete(cacheKey); });
  searchQaPending.set(cacheKey, task);
  return task;
}
async function performGlobalSearch(keyword: string, currentSearchSeq: number) {
  searchLoading.value = true;
  searchError.value = "";
  try {
    const courseList = await ensureSearchCoursesLoaded();
    const results: StudentSearchResult[] = [];
    let order = 0;
    courseList.forEach((course: any) => {
      const score = searchScore(keyword, course?.name, course?.term, searchTeacherName(course), course?.description, course?.intro);
      if (score < 0) return;
      results.push({
        key: `course-${course.id}`,
        type: "course",
        title: course?.name || "未命名课程",
        subtitle: [course?.term, searchTeacherName(course)].filter(Boolean).join(" · ") || "课程",
        excerpt: searchExcerpt(course?.description || course?.intro),
        courseId: Number(course.id),
        rank: score + 80,
        order: order += 1,
      });
    });
    const shouldSearchQa = normalizeSearchText(keyword).length >= 2;
    const scopedData = await Promise.all(courseList.map(async (course: any) => {
      const courseId = Number(course.id);
      const [home, points, qa] = await Promise.all([
        ensureSearchCourseHome(courseId),
        ensureSearchKnowledge(courseId),
        shouldSearchQa ? ensureSearchQa(courseId, keyword) : Promise.resolve([]),
      ]);
      return { course, home: home || {}, points: Array.isArray(points) ? points : [], qa: Array.isArray(qa) ? qa : [] };
    }));
    if (currentSearchSeq !== searchRequestSeq) return;
    scopedData.forEach(({ course, home, points, qa }) => {
      const courseId = Number(course.id);
      const courseName = course?.name || home?.course?.name || "课程";
      const chapters = Array.isArray(home?.chapters) ? home.chapters : [];
      (Array.isArray(home?.lessons) ? home.lessons : []).forEach((lesson: any) => {
        const score = searchScore(keyword, lesson?.title, lesson?.summary, lesson?.description, courseName);
        if (score < 0) return;
        results.push({
          key: `lesson-${lesson.id}`,
          type: "lesson",
          title: lesson?.title || `课时 ${lesson.id}`,
          subtitle: `${courseName} · 课时`,
          excerpt: searchExcerpt(lesson?.summary || lesson?.description),
          courseId,
          lessonId: Number(lesson.id),
          rank: score + 70,
          order: order += 1,
        });
      });
      (Array.isArray(home?.materials) ? home.materials : []).forEach((material: any) => {
        const title = material?.title || material?.name || material?.filename || material?.original_name || "课程资料";
        const score = searchScore(keyword, title, material?.description, material?.filename, courseName);
        if (score < 0) return;
        results.push({
          key: `material-${material.id || `${courseId}-${title}`}`,
          type: "material",
          title,
          subtitle: `${courseName} · 课程资料`,
          excerpt: searchExcerpt(material?.description || material?.filename || material?.original_name),
          courseId,
          rank: score + 60,
          order: order += 1,
        });
      });
      points.forEach((item: any) => {
        const chapterTitle = chapters.find((chapter: any) => Number(chapter.id) === Number(item?.chapter_id))?.title || item?.chapter_title || "知识点";
        const excerpt = knowledgeExcerpt(item);
        const score = searchScore(keyword, item?.name, chapterTitle, excerpt, courseName);
        if (score < 0) return;
        results.push({
          key: `knowledge-${item.id}`,
          type: "knowledge",
          title: item?.name || `知识点 ${item.id}`,
          subtitle: `${courseName} · ${chapterTitle}`,
          excerpt,
          courseId,
          knowledgeId: Number(item.id),
          chapterId: item?.chapter_id ? Number(item.chapter_id) : null,
          rank: score + 65,
          order: order += 1,
        });
      });
      qa.forEach((item: any) => {
        const answerPreview = item?.answer_preview || item?.answer || "";
        const score = searchScore(keyword, item?.title, item?.question, answerPreview, courseName);
        if (score < 0) return;
        results.push({
          key: `qa-${item.conversation_id || item.id}`,
          type: "qa",
          title: item?.title || item?.question || "历史问答",
          subtitle: `${courseName} · ${formatTime(item?.created_at)}`,
          excerpt: searchExcerpt(answerPreview),
          courseId,
          qaItem: item,
          rank: score + 55,
          order: order += 1,
        });
      });
    });
    const seen = new Set<string>();
    searchResults.value = results
      .sort((left, right) => right.rank - left.rank || left.order - right.order)
      .filter((item) => {
        if (seen.has(item.key)) return false;
        seen.add(item.key);
        return true;
      })
      .slice(0, 24);
    searchActiveIndex.value = searchResults.value.length ? 0 : -1;
  } catch (error) {
    if (currentSearchSeq !== searchRequestSeq) return;
    searchError.value = (error as Error).message || "搜索失败，请稍后重试";
    searchResults.value = [];
    searchActiveIndex.value = -1;
  } finally {
    if (currentSearchSeq === searchRequestSeq) searchLoading.value = false;
  }
}
function moveSearchSelection(step: number) {
  const items = flatSearchResults.value;
  if (!items.length) return;
  if (searchActiveIndex.value < 0) {
    searchActiveIndex.value = 0;
    return;
  }
  const next = (searchActiveIndex.value + step + items.length) % items.length;
  searchActiveIndex.value = next;
}
function focusSearchResult(key: string) {
  const index = flatSearchResults.value.findIndex((item) => item.key === key);
  if (index >= 0) searchActiveIndex.value = index;
}
function isSearchResultActive(item: StudentSearchResult) { return flatSearchResults.value[searchActiveIndex.value]?.key === item.key; }
async function openSearchResult(item: StudentSearchResult) {
  const courseId = Number(item.courseId || 0);
  closeSearch();
  if (item.type === "course" && courseId) {
    await openCourse(courseId);
    return;
  }
  if (item.type === "lesson" && item.lessonId) {
    await openLesson(Number(item.lessonId));
    return;
  }
  if (item.type === "material" && courseId) {
    selectedCourseId.value = courseId;
    courseSection.value = "materials";
    await loadCourseHome();
    await go("studentMaterials");
    return;
  }
  if (item.type === "knowledge" && courseId) {
    selectedCourseId.value = courseId;
    selectedChapterId.value = item.chapterId || null;
    selectedKnowledgeId.value = item.knowledgeId || null;
    await go("studentKnowledge");
    await loadCourseHome();
    await loadKnowledge();
    if (item.knowledgeId) selectedKnowledgeId.value = Number(item.knowledgeId);
    return;
  }
  if (item.type === "qa" && courseId && item.qaItem) {
    selectedCourseId.value = courseId;
    await go("studentQa");
    await loadCourseHome();
    await loadQaHistory();
    reuseHistory(item.qaItem);
  }
}
async function openActiveSearchResult() {
  const item = flatSearchResults.value[searchActiveIndex.value];
  if (!item) return;
  await openSearchResult(item);
}
function firstChar(value?: string) { return (value || "-").slice(0, 1); }
function localDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function todayTaskKey() {
  return new Date().toISOString().slice(0, 10);
}
function taskDateKey(task: any) {
  const raw = task?.task_date || task?.date || task?.due_date || task?.scheduled_date;
  if (!raw) return "";
  if (typeof raw === "string") {
    const match = raw.match(/^\d{4}-\d{2}-\d{2}/);
    if (match) return match[0];
  }
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString().slice(0, 10);
}
function completedTaskDateKeys(items: any[]) {
  return Array.from(new Set(items.filter((task: any) => task.status === "done").map(taskDateKey).filter(Boolean)));
}
function shiftPlanMonth(offset: number) {
  const current = planCalendarDate.value;
  planCalendarDate.value = new Date(current.getFullYear(), current.getMonth() + offset, 1);
}
function isStudentNavActive(key: string) {
  if (key === "studentCourses") return studentCourseNavKeys.includes(active.value);
  return active.value === key;
}
function courseGradient(id = 1) { const items = ["linear-gradient(135deg,#121614,#00B8D4)", "linear-gradient(135deg,#121614,#2E7D32)", "linear-gradient(135deg,#121614,#D9A05B)", "linear-gradient(135deg,#121614,#D94925)"]; return items[id % items.length]; }
function courseCoverText(course?: any) {
  const chars = Array.from(String(course?.name || "课程").replace(/\s+/g, "") || "课程");
  if (chars.length <= 3) return chars.join("");
  const coverChars = chars.slice(0, 4);
  return `${coverChars.slice(0, 2).join("")}\n${coverChars.slice(2, 4).join("")}`;
}
function courseCoverStyle(course?: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(180deg, rgba(18,22,20,0.06), rgba(18,22,20,0.42)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseGradient(Number(course?.id || 1)) };
}
function courseHeroStyle(course?: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(135deg, rgba(18,22,20,0.82), rgba(0,184,212,0.34)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseGradient(Number(course?.id || 1)) };
}
function normalizePercent(value: unknown) { const percent = Number.parseFloat(String(value ?? "").replace("%", "")); return Number.isFinite(percent) ? Math.max(0, Math.min(100, Math.round(percent))) : null; }
const BEIJING_TIME_ZONE = "Asia/Shanghai";
const TIMEZONE_SUFFIX_RE = /(Z|[+-]\d{2}:?\d{2})$/i;
function parseAppDate(value?: string | Date | null) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const text = String(value).trim();
  if (!text) return null;
  const hasTime = /\d{2}:\d{2}/.test(text);
  const normalized = hasTime && !TIMEZONE_SUFFIX_RE.test(text) ? `${text.replace(" ", "T")}Z` : text;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}
function timestampMs(value?: string | Date | null) { return parseAppDate(value)?.getTime() || 0; }
function relativeTime(value?: string | Date | null) { const date = parseAppDate(value); if (!date) return "刚刚"; const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000)); if (seconds < 60) return "刚刚"; if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`; if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`; return `${Math.floor(seconds / 86400)}天前`; }
function formatTime(value?: string | Date | null) { const date = parseAppDate(value); return date ? date.toLocaleString("zh-CN", { hour12: false, timeZone: BEIJING_TIME_ZONE }) : "-"; }
function timeLabel(value: number) { if (!Number.isFinite(value)) return "00:00"; return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(Math.floor(value % 60)).padStart(2, "0")}`; }
function payloadList(activity: PageActivity | null | undefined, key: string) {
  const value = activity?.payload?.[key];
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 8);
  if (typeof value === "string" && value.trim()) return value.split(/[\n；;]+/).map((item) => item.trim()).filter(Boolean).slice(0, 8);
  return [];
}
function activityQuestion(activity: PageActivity) {
  return String(activity.payload?.question || activity.payload?.prompt || activity.summary || activity.title || "").trim();
}
function activityHtml(activity: PageActivity) {
  return renderRichText(activity.content || activity.summary || "");
}
async function copyText(text: unknown) {
  const copied = await copyToClipboard(text);
  emit("notice", copied ? "success" : "warning", copied ? "已复制" : "复制失败，请手动复制");
}
function chapterName(id?: number | null) { return (courseHome.value.chapters || []).find((item: any) => item.id === id)?.title || "课程章节"; }
function isOpeningLesson(id?: number | null) { return openingLessonId.value === Number(id || 0); }

function formatJoinCode() { joinCode.value = joinCode.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12); joinPreview.value = null; joinError.value = ""; if (joinTimer) window.clearTimeout(joinTimer); if (joinCode.value.length >= 5) joinTimer = window.setTimeout(validateJoinCode, 350); }
async function validateJoinCode() { joinChecking.value = true; joinError.value = ""; const data = await run<any>(() => api.get("/student/courses/preview", { course_code: joinCode.value })); joinChecking.value = false; if (!data) { joinError.value = "课程码不存在或已停用"; return; } joinPreview.value = data; if (data.already_joined) joinError.value = "你已加入该课程"; }
async function confirmJoin() { if (!joinPreview.value) return; await run(() => api.post("/courses/join", { course_code: joinCode.value }), "已加入"); joinOpen.value = false; joinCode.value = ""; joinPreview.value = null; await loadDashboard(); }
async function handleCourseMenu(action: string, course: any) {
  if (action === "detail") { await openCourse(course.id); return; }
  if (action === "qa") { selectedCourseId.value = course.id; await go("studentQa"); return; }
  if (action === "share") { await copyText(course.course_code); return; }
  // #12/#37：退课为不可逆操作，先弹二次确认，确认后才真正调用退课接口。
  if (action === "leave") { leaveTargetCourse.value = course; leaveConfirmOpen.value = true; }
}
async function confirmLeaveCourse() {
  const course = leaveTargetCourse.value;
  leaveConfirmOpen.value = false;
  if (!course) return;
  const result = await run(() => api.post(`/courses/${course.id}/leave`), "已退出课程");
  leaveTargetCourse.value = null;
  if (result !== null) await loadCourses();
}
function cancelLeaveCourse() { leaveConfirmOpen.value = false; leaveTargetCourse.value = null; }
function requestDeleteQaHistory(item: any) {
  deleteQaHistoryTarget.value = item;
  deleteQaHistoryConfirmOpen.value = true;
}
async function confirmDeleteQaHistory() {
  const item = deleteQaHistoryTarget.value;
  deleteQaHistoryConfirmOpen.value = false;
  if (!item) return;
  const convId = Number(item.conversation_id || 0);
  if (!convId) return;
  const result = await run(() => api.delete(`/qa/conversations/${convId}`), "已删除");
  deleteQaHistoryTarget.value = null;
  if (result !== null) {
    qaHistory.value = qaHistory.value.filter((c) => Number(c.conversation_id) !== convId);
    // 若删除的是当前正在查看的会话，清空消息并回到 QA 主页，避免加载已删除会话
    if (routeQaConversationId() === convId) {
      globalMessages.value = [];
      if (route.path !== "/qa") await router.push("/qa");
    }
  }
}
function closeMaterialPreview() {
  materialPreviewItem.value = null;
  materialPreviewDetail.value = null;
  materialPreviewLoading.value = false;
}
async function previewMaterial(item: any) {
  materialPreviewItem.value = item;
  materialPreviewDetail.value = null;
  materialPreviewLoading.value = true;
  try {
    const detail = await run<MaterialDetail>(() => api.get(`/materials/${item.id}`));
    if (detail) materialPreviewDetail.value = detail;
  } finally {
    materialPreviewLoading.value = false;
  }
}
async function downloadMaterial(item: any) {
  if (!item?.id) return;
  await run(() => api.download(`/materials/${item.id}/content`, item.original_filename || item.title || `material-${item.id}`), "已下载");
}

function hasCourseRouteParam() {
  return route.params.courseId !== undefined;
}
function routeCourseId() {
  const raw = Array.isArray(route.params.courseId) ? route.params.courseId[0] : route.params.courseId;
  const id = Number(raw);
  return Number.isFinite(id) && id > 0 ? id : 0;
}
function routeLessonId() {
  const raw = Array.isArray(route.params.lessonId) ? route.params.lessonId[0] : route.params.lessonId;
  const id = Number(raw);
  return Number.isFinite(id) && id > 0 ? id : 0;
}
function routeQaConversationId() {
  const raw = Array.isArray(route.params.conversationId) ? route.params.conversationId[0] : route.params.conversationId;
  const id = Number(raw);
  return Number.isFinite(id) && id > 0 ? id : 0;
}
function resetClassroomState() {
  stopStudyClock();
  classroomOpen.value = false;
  audioPlaying.value = false;
  audioProgress.value = 0;
  classroomLesson.value = null;
  classMessages.value = [];
  classConversationId.value = null;
  classQuestion.value = "";
  classThinking.value = false;
  classConversationLoading.value = false;
  classConversationLoadSeq += 1;
  classQaAttachments.value = [];
  classQaImageUploading.value = false;
  clearLessonAskContext();
  hideLessonSelectionMenu();
  completeOpen.value = false;
  settingsOpen.value = false;
  thumbOpen.value = false;
  currentPage.value = 1;
  studySeconds.value = 0;
  reportedStudySeconds.value = 0;
  pageNote.value = "";
  noteState.value = "已保存";
  noteSavedAt.value = "尚未保存";
}
async function leaveClassroom(saveProgressBeforeClose = false) {
  if (saveProgressBeforeClose && classroomLesson.value) await saveProgress(false, true);
  resetClassroomState();
}
async function loadLessonStudyRoute() {
  const lessonId = routeLessonId();
  if (!lessonId) {
    lessonStudyLoading.value = false;
    lessonStudyError.value = "课时地址无效，请从课程列表重新进入。";
    openingLessonId.value = null;
    resetClassroomState();
    return;
  }
  if (classroomOpen.value && classroomLesson.value?.lesson.id === lessonId) {
    lessonStudyLoading.value = false;
    lessonStudyError.value = "";
    openingLessonId.value = null;
    return;
  }
  const loadSeq = ++lessonLoadSeq;
  lessonStudyLoading.value = true;
  lessonStudyError.value = "";
  resetClassroomState();
  try {
    const detail = await api.get<LessonDetail>(`/lessons/${lessonId}`);
    if (loadSeq !== lessonLoadSeq || routeLessonId() !== lessonId) return;
    if (!detail?.lesson) throw new Error("课时不存在或暂无访问权限");
    if (detail.lesson.course_id) selectedCourseId.value = Number(detail.lesson.course_id);
    classroomLesson.value = detail;
    classroomOpen.value = true;
    completeOpen.value = false;
    studySeconds.value = 0;
    reportedStudySeconds.value = 0;
    startStudyClock();
    try {
      const progress = await api.get<any>(`/lessons/${lessonId}/progress`);
      if (loadSeq === lessonLoadSeq && routeLessonId() === lessonId && progress?.current_page) currentPage.value = progress.current_page;
    } catch (error) {
      emit("notice", "warning", `学习进度加载失败：${(error as Error).message}`);
    }
    if (loadSeq === lessonLoadSeq && routeLessonId() === lessonId) applyPendingSourcePage();
    if (loadSeq === lessonLoadSeq && routeLessonId() === lessonId) await loadNote(activePage.value?.id || 0);
    if (loadSeq === lessonLoadSeq && routeLessonId() === lessonId) void loadClassQaHistory();
  } catch (error) {
    if (loadSeq !== lessonLoadSeq) return;
    resetClassroomState();
    lessonStudyError.value = (error as Error).message || "课时加载失败，请稍后重试。";
  } finally {
    if (loadSeq === lessonLoadSeq) {
      lessonStudyLoading.value = false;
      openingLessonId.value = null;
    }
  }
}
async function openLesson(id: number) {
  if (!id || openingLessonId.value) return;
  openingLessonId.value = id;
  if (active.value === "studentLessonStudy" && routeLessonId() === id) {
    openingLessonId.value = null;
    await loadLessonStudyRoute();
    return;
  }
  try {
    await router.push(`/lessons/${id}`);
  } catch (error) {
    openingLessonId.value = null;
    emit("notice", "error", (error as Error).message || "打开课时失败");
  }
}
async function closeClassroom() {
  const shouldReturnToCourse = active.value === "studentLessonStudy";
  const returnCourseId = Number(classroomLesson.value?.lesson.course_id || selectedCourseId.value || 0);
  await leaveClassroom(true);
  if (shouldReturnToCourse) {
    if (returnCourseId) await openCourse(returnCourseId);
    else await go("studentCourses");
  }
  else await loadDashboard();
}

function normalizeLessonSelectionText(text: string) {
  return text
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\s*\n\s*/g, "\n")
    .trim()
    .slice(0, 1200);
}

function selectionPreviewText(text: string) {
  const raw = text.trim();
  const oneLine = raw.replace(/\s+/g, " ");
  if (!oneLine) return "";
  const hasLineBreak = raw.includes("\n");
  const maxLength = 54;
  if (oneLine.length > maxLength) return `${oneLine.slice(0, maxLength)}...`;
  return hasLineBreak ? `${oneLine}...` : oneLine;
}

function readSlideViewportFitScale() {
  const stage = slideStageRef.value;
  if (!stage || classroomOriginalMaterial.value || compactLessonLayout.value) {
    slideViewportFitScale.value = 1;
    return;
  }
  const stageRect = stage.getBoundingClientRect();
  const style = window.getComputedStyle(stage);
  const paddingX = Number.parseFloat(style.paddingLeft || "0") + Number.parseFloat(style.paddingRight || "0");
  const paddingY = Number.parseFloat(style.paddingTop || "0") + Number.parseFloat(style.paddingBottom || "0");
  const gap = Number.parseFloat(style.rowGap || style.gap || "0") * 2;
  const availableWidth = Math.max(stageRect.width - paddingX, 1);
  const availableHeight = Math.max(stageRect.height - paddingY - gap, 1);

  const baseWidth = Math.max(slideCardMeasureRef.value.width, 1160);
  const baseHeight = Math.max(slideCardMeasureRef.value.height, 620);
  const widthScale = availableWidth / baseWidth;
  const heightScale = availableHeight / baseHeight;
  slideViewportFitScale.value = Math.min(1, widthScale, heightScale);
}

function measureSlideCardSize() {
  if (classroomOriginalMaterial.value) {
    slideViewportFitScale.value = 1;
    return;
  }
  const card = slideStageRef.value?.querySelector<HTMLElement>(".slide-card");
  if (card) {
    const cardStyle = window.getComputedStyle(card);
    const paddingY = Number.parseFloat(cardStyle.paddingTop || "0") + Number.parseFloat(cardStyle.paddingBottom || "0");
    const paddingX = Number.parseFloat(cardStyle.paddingLeft || "0") + Number.parseFloat(cardStyle.paddingRight || "0");
    const rowGap = Number.parseFloat(cardStyle.rowGap || cardStyle.gap || "0");
    const title = card.querySelector<HTMLElement>("h1");
    const content = card.querySelector<HTMLElement>(".slide-content");
    const fullContentHeight = content
      ? paddingY + (title?.scrollHeight || title?.offsetHeight || 0) + rowGap + content.scrollHeight
      : card.scrollHeight;
    const fullContentWidth = content ? paddingX + Math.max(content.scrollWidth, title?.scrollWidth || 0) : card.scrollWidth;
    slideCardMeasureRef.value = {
      width: Math.max(fullContentWidth, card.scrollWidth, card.offsetWidth, card.clientWidth),
      height: Math.max(fullContentHeight, card.scrollHeight, card.offsetHeight, card.clientHeight),
    };
  }
  readSlideViewportFitScale();
}

function syncSlideStageResizeObserver() {
  slideStageResizeObserver?.disconnect();
  slideStageResizeObserver = undefined;
  const stage = slideStageRef.value;
  if (!stage || typeof ResizeObserver === "undefined") return;
  slideStageResizeObserver = new ResizeObserver(() => measureSlideCardSize());
  slideStageResizeObserver.observe(stage);
}

function hideLessonSelectionMenu() {
  lessonSelectionMenu.open = false;
}

function clearLessonAskContext() {
  lessonAskContext.value = "";
}

function clearBrowserSelection() {
  window.getSelection()?.removeAllRanges();
}

function lessonSelectionNodeInStage(node: Node | null) {
  const stage = slideStageRef.value;
  if (!stage || !node) return false;
  return stage.contains(node);
}

function clampSelectionPopoverX(x: number) {
  return Math.min(Math.max(x, 76), Math.max(76, window.innerWidth - 76));
}

function updateLessonSelectionMenu() {
  if (!classroomOpen.value || lessonResizeActive.value) {
    hideLessonSelectionMenu();
    return;
  }
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) {
    hideLessonSelectionMenu();
    return;
  }
  const selectedText = normalizeLessonSelectionText(selection.toString());
  if (selectedText.length < 2) {
    hideLessonSelectionMenu();
    return;
  }
  const range = selection.getRangeAt(0);
  if (!lessonSelectionNodeInStage(range.commonAncestorContainer) && !lessonSelectionNodeInStage(selection.anchorNode) && !lessonSelectionNodeInStage(selection.focusNode)) {
    hideLessonSelectionMenu();
    return;
  }
  const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);
  const rect = rects[0] || range.getBoundingClientRect();
  if (!rect || (!rect.width && !rect.height)) {
    hideLessonSelectionMenu();
    return;
  }
  lessonSelectionMenu.text = selectedText;
  lessonSelectionMenu.x = clampSelectionPopoverX(rect.left + rect.width / 2);
  lessonSelectionMenu.y = Math.max(56, rect.top - 12);
  lessonSelectionMenu.open = true;
}

function scheduleLessonSelectionCheck() {
  if (lessonSelectionTimer) window.clearTimeout(lessonSelectionTimer);
  lessonSelectionTimer = window.setTimeout(updateLessonSelectionMenu, 80);
}

async function openClassQaFromSelection() {
  if (!compactLessonLayout.value) aiPanelOpen.value = true;
  classroomTab.value = "qa";
  await nextTick();
}

async function explainLessonSelection() {
  const text = lessonSelectionMenu.text;
  if (!text || classThinking.value) return;
  hideLessonSelectionMenu();
  clearLessonAskContext();
  clearBrowserSelection();
  await openClassQaFromSelection();
  classQuestion.value = `请为我解释“${text}”`;
  await askInClass();
}

async function prepareLessonSelectionQuestion() {
  const text = lessonSelectionMenu.text;
  if (!text) return;
  hideLessonSelectionMenu();
  clearBrowserSelection();
  lessonAskContext.value = text;
  classQuestion.value = "";
  await openClassQaFromSelection();
  classQuestionInput.value?.focus();
}

function lessonPanelBounds(totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0) {
  const availableWidth = Math.max(totalWidth - LESSON_RESIZER_WIDTH, 1);
  const minLeft = classroomOriginalMaterial.value ? 760 : 700;
  const minRight = LESSON_LAYOUT_MIN_RIGHT;
  const preferredMaxRight = classroomOriginalMaterial.value ? availableWidth * 0.38 : availableWidth * 0.42;
  const hardMaxRight = classroomOriginalMaterial.value ? 640 : 680;
  const maxRight = Math.min(hardMaxRight, Math.max(420, preferredMaxRight), Math.max(minRight, availableWidth - minLeft));
  return { availableWidth, minLeft, minRight, maxRight };
}

function clampLessonPanelRatio(value: number, totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0) {
  if (totalWidth > 900) {
    const { availableWidth, minLeft, minRight, maxRight } = lessonPanelBounds(totalWidth);
    const minRatio = minRight / availableWidth;
    const maxRatio = Math.min(maxRight / availableWidth, (availableWidth - minLeft) / availableWidth, LESSON_LAYOUT_MAX_RATIO);
    if (maxRatio > minRatio) return Math.min(maxRatio, Math.max(minRatio, value));
  }
  return Math.min(LESSON_LAYOUT_MAX_RATIO, Math.max(LESSON_LAYOUT_MIN_RATIO, value));
}
function updateLessonPanelRatio(clientX: number) {
  if (compactLessonLayout.value) return;
  const element = studyMainRef.value;
  if (!element) return;
  const rect = element.getBoundingClientRect();
  const width = Math.max(rect.width, 1);
  lessonPanelRatio.value = clampLessonPanelRatio((rect.right - clientX) / width, width);
}
function onLessonResizePointerMove(event: PointerEvent) {
  if (!lessonResizeActive.value) return;
  updateLessonPanelRatio(event.clientX);
}
function stopLessonResize() {
  if (!lessonResizeActive.value) return;
  lessonResizeActive.value = false;
  lessonPanelRatioCustomized.value = true;
  document.body.classList.remove("lesson-resizing");
  window.removeEventListener("pointermove", onLessonResizePointerMove);
  window.removeEventListener("pointerup", stopLessonResize);
  window.removeEventListener("pointercancel", stopLessonResize);
  localStorage.setItem(LESSON_LAYOUT_STORAGE_KEY, String(lessonPanelRatio.value));
}
function startLessonResize(event: PointerEvent) {
  if (!aiPanelOpen.value || compactLessonLayout.value) return;
  event.preventDefault();
  lessonResizeActive.value = true;
  (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
  updateLessonPanelRatio(event.clientX);
  document.body.classList.add("lesson-resizing");
  window.addEventListener("pointermove", onLessonResizePointerMove);
  window.addEventListener("pointerup", stopLessonResize);
  window.addEventListener("pointercancel", stopLessonResize);
}
function revealChrome() { chromeVisible.value = true; if (chromeTimer) window.clearTimeout(chromeTimer); chromeTimer = window.setTimeout(() => { if (audioPlaying.value) chromeVisible.value = false; }, 3000); }
function startStudyClock() { stopStudyClock(); studyTimer = window.setInterval(() => { studySeconds.value += 1; }, 1000); }
function stopStudyClock() { if (studyTimer) window.clearInterval(studyTimer); studyTimer = undefined; }
function updateCompactLessonLayout() {
  const width = window.innerWidth || document.documentElement.clientWidth || 0;
  lessonLayoutWidth.value = width;
  const nextCompact = width > 0 && width < 1180;
  const wasCompact = compactLessonLayout.value;
  compactLessonLayout.value = nextCompact;
  if (nextCompact) {
    aiPanelOpen.value = false;
    thumbOpen.value = false;
    settingsOpen.value = false;
  } else if (wasCompact) {
    aiPanelOpen.value = true;
  }
  requestAnimationFrame(() => measureSlideCardSize());
}
async function toggleLessonFullscreen() {
  const element = studyRoomRef.value;
  if (!element) return;
  try {
    if (document.fullscreenElement === element) {
      await document.exitFullscreen();
      return;
    }
    if (!document.fullscreenElement) {
      await element.requestFullscreen();
      return;
    }
    await document.exitFullscreen();
    await element.requestFullscreen();
  } catch (error) {
    emit("notice", "warning", (error as Error)?.message || "当前环境不支持全屏");
  }
}
function onLessonFullscreenChange() {
  lessonFullscreen.value = document.fullscreenElement === studyRoomRef.value;
}

watch(
  () => classroomLesson.value?.lesson.id,
  () => {
    lessonPanelRatio.value = savedLessonPanelRatio();
    lessonPanelRatioCustomized.value = false;
    slideViewportFitScale.value = 1;
    slideCardMeasureRef.value = { width: 0, height: 0 };
  }
);
watch(
  () => [aiPanelOpen.value, lessonFullscreen.value],
  () => {
    void nextTick(() => {
      syncSlideStageResizeObserver();
      measureSlideCardSize();
      requestAnimationFrame(() => measureSlideCardSize());
    });
  }
);
watch(
  () => [currentPage.value, classroomOriginalMaterial.value?.id, activePageHtml.value, activeSubtitleHtml.value],
  () => {
    void nextTick(() => {
      syncSlideStageResizeObserver();
      measureSlideCardSize();
      requestAnimationFrame(() => measureSlideCardSize());
    });
  },
  { immediate: true }
);
// 翻页进度上报防抖：快速连续翻页只在停下来后上报一次，避免每翻一页发一次请求触发限流。
let progressSaveTimer: ReturnType<typeof setTimeout> | undefined;
function queueSaveProgress() {
  if (progressSaveTimer) clearTimeout(progressSaveTimer);
  progressSaveTimer = setTimeout(() => { progressSaveTimer = undefined; void saveProgress(false, true); }, 900);
}
async function jumpPage(page: number) { pageDirection.value = page >= currentPage.value ? "next" : "prev"; currentPage.value = page; thumbOpen.value = false; queueSaveProgress(); }
async function prevPage() { await jumpPage(Math.max(1, currentPage.value - 1)); }
async function nextPage() { await jumpPage(Math.min(classroomLesson.value?.pages.length || 1, currentPage.value + 1)); }
async function saveProgress(completed: boolean, silent = false) {
  // 立即上报（关闭/完成/切音频结束等）时取消待发的防抖上报，避免重复请求。
  if (progressSaveTimer) { clearTimeout(progressSaveTimer); progressSaveTimer = undefined; }
  if (!classroomLesson.value) return;
  // 真实新增学习秒数 = 自上次上报以来计时器累计的差值（最小为 0，避免负数）。
  const addedSeconds = Math.max(0, studySeconds.value - reportedStudySeconds.value);
  const result = await run(() => api.post(`/lessons/${classroomLesson.value!.lesson.id}/progress`, { current_page: currentPage.value, added_seconds: addedSeconds, completed }), silent ? undefined : "已保存");
  if (result !== null) reportedStudySeconds.value = studySeconds.value;
}
async function toggleAudio() { if (!audioRef.value) return; audioRef.value.playbackRate = playbackRate.value; if (audioRef.value.paused) { try { await audioRef.value.play(); } catch (error) { audioPlaying.value = false; emit("notice", "error", "音频无法播放，请检查音频文件或浏览器自动播放设置"); return; } } else audioRef.value.pause(); revealChrome(); }
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
function confettiStyle(n: number) { return { left: `${(n * 37) % 100}%`, background: ["#00B8D4", "#00E5FF", "#2E7D32", "#D9A05B", "#D94925"][n % 5], animationDelay: `${(n % 8) * 0.05}s` }; }
async function nextLessonAfterComplete() {
  // #36：直接从课程的真实已发布课时列表里取下一课时。直接进入 /lessons/:id 时
  // courseHome 可能为空或属于别的课程，因此按当前课时的 course_id 拉一次真实列表再定位。
  const currentLesson = classroomLesson.value?.lesson;
  if (!currentLesson) { await returnCourse(); return; }
  const courseId = Number(currentLesson.course_id || selectedCourseId.value || 0);
  let lessonList = (courseHome.value.lessons || []) as any[];
  const loadedCourseId = Number(courseHome.value.course?.id || 0);
  if (courseId && (loadedCourseId !== courseId || !lessonList.some((item: any) => item.id === currentLesson.id))) {
    const home = await run<any>(() => api.get(`/student/courses/${courseId}/home`));
    lessonList = (home?.lessons || []) as any[];
  }
  const index = lessonList.findIndex((item: any) => item.id === currentLesson.id);
  const next = index >= 0 ? lessonList[index + 1] : null;
  if (next?.id) { completeOpen.value = false; await openLesson(Number(next.id)); }
  else await returnCourse();
}
async function returnCourse() { completeOpen.value = false; await closeClassroom(); }

function patchChatMessage(messages: Ref<ChatMessage[]>, id: number, updater: (message: ChatMessage) => ChatMessage) {
  const index = messages.value.findIndex((item) => item.id === id);
  if (index < 0) return;
  messages.value.splice(index, 1, updater({ ...messages.value[index] }));
}

function applyQaStreamEvent(messages: Ref<ChatMessage[]>, messageId: number, event: string, data: any) {
  if (event === "stage") {
    // 首 token 前的进度提示（检索中→生成中），让用户不再面对空白干等
    patchChatMessage(messages, messageId, (message) => ({ ...message, statusText: data?.text || "" }));
    return;
  }
  if (event === "created") {
    // 会话/记录已在后端建好，提前挂上 record_id：即使中途停止，该消息也能收藏/反馈
    patchChatMessage(messages, messageId, (message) => ({ ...message, record_id: data?.record_id ?? message.record_id }));
    return;
  }
  if (event === "delta") {
    patchChatMessage(messages, messageId, (message) => data?.type === "thought"
      ? { ...message, thought: `${message.thought || ""}${data.text || ""}`, thoughtOpen: true, statusText: "" }
      : { ...message, text: `${message.text || ""}${data?.text || ""}`, statusText: "" });
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
  if ((!classQuestion.value.trim() && !classQaAttachments.value.length) || !classroomLesson.value || classThinking.value || (classConversationLoading.value && !classMessages.value.length) || classQaImageUploading.value) return;
  const lessonPageId = Number(activePage.value?.id || 0);
  if (!lessonPageId) {
    emit("notice", "warning", "当前课件页还未加载完成，请稍后再提问。");
    return;
  }
  const rawQuestion = classQuestion.value.trim();
  const selectedContext = lessonAskContext.value.trim();
  const question = rawQuestion || "请分析这张图片";
  const requestQuestion = selectedContext
    ? `请基于以下选中的课件内容回答：\n“${selectedContext}”\n\n我的问题：${question}`
    : question;
  const attachments = classQaAttachments.value.map((item) => ({ ...item }));
  classQuestion.value = "";
  clearLessonAskContext();
  classQaAttachments.value = [];
  classMessages.value.push({ id: Date.now(), role: "user", text: question, attachments });
  const aiMessageId = Date.now() + 1;
  const aiMessage: ChatMessage = { id: aiMessageId, role: "ai", text: "", thought: "", sources: [], streaming: true };
  classMessages.value.push(aiMessage);
  const controller = new AbortController();
  classAbortController = controller;
  classThinking.value = true;
  try {
    await api.streamPost("/qa/ask/stream", {
      course_id: classroomLesson.value.lesson.course_id,
      conversation_id: classConversationId.value,
      lesson_page_id: lessonPageId,
      question: requestQuestion,
      attachments
    }, (event, data) => {
      applyQaStreamEvent(classMessages, aiMessageId, event, data);
      if (event === "created" || event === "final") classConversationId.value = data.conversation_id ?? classConversationId.value;
    }, undefined, controller.signal);
  } catch (error) {
    // 用户主动停止：保留已生成内容，不提示错误
    if (!controller.signal.aborted) {
      const current = classMessages.value.find((message) => message.id === aiMessageId);
      if (!current?.text) patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
      emit("notice", "error", (error as Error).message);
    }
  } finally {
    patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, streaming: false }));
    classThinking.value = false;
    if (classAbortController === controller) classAbortController = null;
  }
}
function stopClassGeneration() { classAbortController?.abort(); }
function sendQuickClass(text: string) { classQuestion.value = text; askInClass(); }
function handleQuestionCompositionStart(scope: QaInputScope) {
  questionCompositionState[scope].active = true;
}
function handleQuestionCompositionEnd(scope: QaInputScope) {
  questionCompositionState[scope].active = false;
  questionCompositionState[scope].endedAt = Date.now();
}
function isImeConfirming(event: KeyboardEvent, scope: QaInputScope) {
  const legacyCode = event.keyCode || event.which;
  return questionCompositionState[scope].active || event.isComposing || legacyCode === 229;
}
function submitQuestionOnEnter(event: KeyboardEvent, scope: QaInputScope, submit: () => Promise<void>) {
  if (event.key !== "Enter" || event.shiftKey) return;
  if (isImeConfirming(event, scope)) return;
  if (Date.now() - questionCompositionState[scope].endedAt < 120) {
    event.preventDefault();
    return;
  }
  event.preventDefault();
  void submit();
}
function handleClassQuestionKeydown(event: KeyboardEvent) { submitQuestionOnEnter(event, "class", askInClass); }
function handleGlobalQuestionKeydown(event: KeyboardEvent) { submitQuestionOnEnter(event, "global", askGlobal); }
// 输入框随内容自适应高度，上限交由 CSS 的 max-height 控制（超出后内部滚动）
function resizeQuestionInput(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}
// 用 watch 覆盖所有改值路径：键入、快捷追问写入、发送后清空
watch(classQuestion, () => nextTick(() => resizeQuestionInput(classQuestionInput.value)));
watch(globalQuestion, () => nextTick(() => resizeQuestionInput(globalQuestionInput.value)));
async function askGlobal() {
  if ((!globalQuestion.value.trim() && !globalQaAttachments.value.length) || !selectedCourseId.value || globalThinking.value || (globalConversationLoading.value && !globalMessages.value.length) || globalQaImageUploading.value) return;
  const question = globalQuestion.value.trim() || "请分析这张图片";
  const attachments = globalQaAttachments.value.map((item) => ({ ...item }));
  globalQuestion.value = "";
  globalQaAttachments.value = [];
  globalMessages.value.push({ id: Date.now(), role: "user", text: question, attachments });
  const aiMessageId = Date.now() + 1;
  const aiMessage: ChatMessage = { id: aiMessageId, role: "ai", text: "", thought: "", sources: [], streaming: true };
  globalMessages.value.push(aiMessage);
  scrollQaToLatest(false);
  const controller = new AbortController();
  globalAbortController = controller;
  globalThinking.value = true;
  try {
    await api.streamPost("/qa/ask/stream", {
      course_id: selectedCourseId.value,
      conversation_id: globalConversationId.value,
      question,
      attachments
    }, (event, data) => {
      const shouldFollowLatest = isQaNearLatest(320);
      applyQaStreamEvent(globalMessages, aiMessageId, event, data);
      keepQaAtLatestIfNeeded(shouldFollowLatest);
      if (event === "created" || event === "final") globalConversationId.value = data.conversation_id ?? globalConversationId.value;
    }, undefined, controller.signal);
  } catch (error) {
    // 用户主动停止：保留已生成内容，不提示错误
    if (!controller.signal.aborted) {
      const current = globalMessages.value.find((message) => message.id === aiMessageId);
      if (!current?.text) patchChatMessage(globalMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
      emit("notice", "error", (error as Error).message);
    }
  } finally {
    patchChatMessage(globalMessages, aiMessageId, (message) => ({ ...message, streaming: false }));
    globalThinking.value = false;
    if (globalAbortController === controller) globalAbortController = null;
  }
  // 停止或正常完成后都刷新历史并续接路由会话，保证停止的对话也进历史、刷新后可见
  if (globalConversationId.value && routeQaConversationId() !== globalConversationId.value) await router.replace(qaConversationRoute(globalConversationId.value));
  await loadQaHistory();
}
function stopGlobalGeneration() { globalAbortController?.abort(); }
function sendGlobalQuick(text: string) { globalQuestion.value = text; askGlobal(); }
async function sendCourseQuick(text: string) { quickCourseQuestion.value = text; await askCourseQuick(); }
async function askCourseQuick() { if (!quickCourseQuestion.value.trim()) return; globalQuestion.value = quickCourseQuestion.value; quickCourseQuestion.value = ""; await go("studentQa"); await askGlobal(); }
async function loadQaHistory() {
  if (!selectedCourseId.value) return;
  qaHistory.value = (await run<QaHistoryConversation[]>(() => api.get("/qa/history", { course_id: selectedCourseId.value, keyword: qaKeyword.value }))) || [];
}
async function loadClassQaHistory() {
  if (!classroomLesson.value) return;
  const lessonId = classroomLesson.value.lesson.id;
  const courseId = classroomLesson.value.lesson.course_id;
  const summaries = (await run<QaHistoryConversation[]>(() => api.get("/qa/history", { course_id: courseId, lesson_id: lessonId }))) || [];
  const latest = [...summaries].sort((left, right) => timestampMs(right.created_at) - timestampMs(left.created_at) || Number(right.id || 0) - Number(left.id || 0))[0];
  const conversationId = Number(latest?.conversation_id || 0);
  if (!conversationId) {
    classMessages.value = [];
    classConversationId.value = null;
    return;
  }
  const loadSeq = ++classConversationLoadSeq;
  classConversationLoading.value = true;
  classMessages.value = [];
  try {
    const records = await api.get<any[]>(`/qa/conversations/${conversationId}`);
    if (loadSeq !== classConversationLoadSeq || classroomLesson.value?.lesson.id !== lessonId) return;
    const ordered = [...(records || [])].sort((left, right) => timestampMs(left.created_at) - timestampMs(right.created_at) || Number(left.id || 0) - Number(right.id || 0));
    classMessages.value = qaRecordsToMessages(ordered);
    classConversationId.value = conversationId;
  } catch (error) {
    if (loadSeq === classConversationLoadSeq) emit("notice", "error", (error as Error).message);
  } finally {
    if (loadSeq === classConversationLoadSeq) classConversationLoading.value = false;
  }
}
function closeQaHistory() { historyOpen.value = false; }
async function toggleQaHistory() {
  if (historyOpen.value) {
    closeQaHistory();
    return;
  }
  showFavorites.value = false;
  historyOpen.value = true;
  await loadQaHistory();
}
function qaRecordsToMessages(records: any[]) {
  return records.flatMap((item) => [
    { id: item.id * 2, role: "user" as const, text: item.question, attachments: item.attachments || [] },
    {
      id: item.id * 2 + 1,
      role: "ai" as const,
      text: item.answer,
      sources: item.sources || [],
      attachments: item.attachments || [],
      thought: item.thinking_process || item.reasoning_content || item.thought || "",
      record_id: item.id,
      favorite: item.is_favorite,
      feedback: item.feedback === "positive" || item.feedback === "negative" ? item.feedback : null,
      outOfScope: item.is_out_of_scope,
    }
  ]);
}
async function loadQaRouteConversation() {
  const conversationId = routeQaConversationId();
  if (!conversationId) return;
  if (conversationId === globalConversationId.value && globalMessages.value.length) {
    globalConversationLoading.value = false;
    await loadQaHistory();
    return;
  }
  const loadSeq = ++qaConversationLoadSeq;
  globalConversationLoading.value = true;
  globalMessages.value = [];
  globalQaAttachments.value = [];
  try {
    const records = await api.get<any[]>(`/qa/conversations/${conversationId}`);
    if (loadSeq !== qaConversationLoadSeq) return;
    if (!records?.length) return;
    if (records.some((record) => record?.lesson_page_id)) {
      globalConversationId.value = null;
      globalMessages.value = [];
      globalQaAttachments.value = [];
      historyOpen.value = false;
      if (route.path !== "/qa") await router.replace("/qa");
      await loadQaHistory();
      return;
    }
    const courseId = Number(records[0]?.course_id || 0);
    if (courseId && selectedCourseId.value !== courseId) {
      suppressCourseScopedReset = true;
      selectedCourseId.value = courseId;
      if (courseId) localStorage.setItem("student_current_course_id", String(courseId));
      await nextTick();
      suppressCourseScopedReset = false;
    }
    globalConversationId.value = conversationId;
    globalMessages.value = qaRecordsToMessages(records);
    await loadCourseHome();
    await loadQaHistory();
    scrollQaToLatest(false);
  } catch (error) {
    if (loadSeq === qaConversationLoadSeq) emit("notice", "error", (error as Error).message);
  } finally {
    if (loadSeq === qaConversationLoadSeq) globalConversationLoading.value = false;
  }
}
async function startNewQaConversation() {
  historyOpen.value = false;
  qaConversationLoadSeq += 1;
  globalConversationLoading.value = false;
  globalConversationId.value = null;
  globalMessages.value = [];
  globalQuestion.value = "";
  globalQaAttachments.value = [];
  showQaLatestButton.value = false;
  if (route.path !== "/qa") await router.push("/qa");
}
async function openQaConversation(item: any) {
  const conversationId = Number(item?.conversation_id || 0);
  if (!conversationId) return;
  historyOpen.value = false;
  globalConversationLoading.value = true;
  globalMessages.value = [];
  globalQaAttachments.value = [];
  if (routeQaConversationId() === conversationId) {
    await loadQaRouteConversation();
    return;
  }
  await router.push(qaConversationRoute(conversationId));
}
function reuseHistory(item: any) { void openQaConversation(item); }
function toggleThought(message: ChatMessage) { message.thoughtOpen = !message.thoughtOpen; }
async function favoriteQaMessage(message: ChatMessage) { if (!message.record_id) return; const ok = await run(() => api.post(`/qa/${message.record_id}/favorite`, { is_favorite: !message.favorite }), "已收藏"); if (ok !== null) message.favorite = !message.favorite; }
async function feedbackQaMessage(message: ChatMessage, feedback: "positive" | "negative" = "positive") {
  if (!message.record_id) return;
  const ok = await run(() => api.post(`/qa/${message.record_id}/feedback`, { feedback }), feedback === "positive" ? "感谢反馈" : "已记录，会持续改进");
  if (ok !== null) message.feedback = feedback;
}
async function jumpToSource(source: any) {
  if (!source) return;
  const lessonId = Number(source.lesson_id || 0);
  const lessonPageId = Number(source.lesson_page_id || 0);
  const rawPageNumber = Number(source.page_number || 0);
  // 课堂内问答：来源属于当前打开的课时，直接定位到对应页面
  if (classroomOpen.value && classroomLesson.value && (!lessonId || classroomLesson.value.lesson.id === lessonId)) {
    const targetPage = resolveSourcePageNumber(source);
    if (targetPage) {
      if (classroomTab.value === "qa") classroomTab.value = "script";
      await jumpPage(targetPage);
    }
    return;
  }
  // 全局问答或来源属于其它课时：打开来源所属课时，再定位到对应页面
  if (lessonId) {
    pendingSourcePageNumber.value = rawPageNumber || null;
    pendingSourcePageId.value = lessonPageId || null;
    await openLesson(lessonId);
    return;
  }
  // 没有课时信息但能解析出当前课时的页码时也尝试跳转
  const fallbackPage = resolveSourcePageNumber(source);
  if (fallbackPage && classroomOpen.value) await jumpPage(fallbackPage);
}
function applyPendingSourcePage() {
  const lesson = classroomLesson.value;
  if (!lesson) { pendingSourcePageNumber.value = null; pendingSourcePageId.value = null; return; }
  let targetPage = 0;
  if (pendingSourcePageId.value) {
    const byId = lesson.pages.find((page) => page.id === pendingSourcePageId.value);
    if (byId) targetPage = byId.page_number;
  }
  if (!targetPage && pendingSourcePageNumber.value) {
    const byNumber = lesson.pages.find((page) => page.page_number === pendingSourcePageNumber.value);
    targetPage = byNumber?.page_number || pendingSourcePageNumber.value;
  }
  pendingSourcePageNumber.value = null;
  pendingSourcePageId.value = null;
  if (targetPage && targetPage !== currentPage.value) {
    pageDirection.value = targetPage >= currentPage.value ? "next" : "prev";
    currentPage.value = targetPage;
  }
}
function resolveSourcePageNumber(source: any) {
  const lesson = classroomLesson.value;
  if (!lesson) return Number(source?.page_number || 0) || 0;
  const lessonPageId = Number(source?.lesson_page_id || 0);
  if (lessonPageId) {
    const byId = lesson.pages.find((page) => page.id === lessonPageId);
    if (byId) return byId.page_number;
  }
  const pageNumber = Number(source?.page_number || 0);
  if (pageNumber) {
    const byNumber = lesson.pages.find((page) => page.page_number === pageNumber);
    if (byNumber) return byNumber.page_number;
  }
  return pageNumber || 0;
}

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
    resetGuidanceState();
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
    resetGuidanceState();
    await loadProblemHistory();
  } finally {
    ocrScanning.value = false;
    (event.target as HTMLInputElement).value = "";
  }
}
async function loadProblemHistory() { problemHistory.value = (await run<any[]>(() => api.get("/tutoring/history", { course_id: selectedCourseId.value || undefined }))) || []; }
function resetGuidanceState() {
  Object.keys(guidance).forEach((key) => delete guidance[Number(key)]);
  guideOpen[1] = true;
  guideOpen[2] = false;
  guideOpen[3] = false;
}
function selectProblem(item: any) { activeProblem.value = item; problemText.value = item.corrected_text || item.ocr_text || item.raw_text || ""; resetGuidanceState(); }
async function loadGuidance(level: number) { if (!activeProblem.value) return; guidance[level] = await run(() => api.get(`/tutoring/problems/${activeProblem.value.id}/guidance`, { level })); guideOpen[level] = true; }
async function toggleGuide(level: number) { if (!guidance[level]) await loadGuidance(level); else guideOpen[level] = !guideOpen[level]; }

async function loadKnowledge() { if (!selectedCourseId.value) return; knowledge.value = (await run<any[]>(() => api.get("/learning/knowledge-points", { course_id: selectedCourseId.value, chapter_id: selectedChapterId.value || undefined }))) || []; if (!selectedKnowledgeId.value && knowledge.value[0]) selectedKnowledgeId.value = knowledge.value[0].id; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); }
async function generateKnowledgeQuiz(count: number) {
  if (!selectedCourseId.value) return;
  const result = await run<any>(() => api.post("/learning/quizzes/generate", { course_id: selectedCourseId.value, chapter_id: selectedKnowledge.value?.chapter_id || undefined, title: `${selectedKnowledge.value?.name || '知识点'}练习`, quiz_type: "practice", question_count: count }));
  if (!result) return;
  const queuedMessage = queuedQuizMessage(result);
  emit("notice", result.id ? "success" : "info", queuedMessage || "已生成");
  await openQuizSelection("practice");
  if (!result.id) await loadNotifications(true);
}

async function loadQuizPage() { if (!selectedCourseId.value) return; quizzes.value = (await run<Quiz[]>(() => api.get("/learning/quizzes", { course_id: selectedCourseId.value }))) || []; if (!courseHome.value.course) await loadCourseHome(); await loadWrongBook(); }
async function generateQuiz() {
  if (!selectedCourseId.value || quizGenerating.value) return;
  quizGenerating.value = true;
  try {
    const count = Number(quizQuestionCount.value.replace("题", ""));
    const chapterIds = selectedPracticeChapters.value.length ? selectedPracticeChapters.value : (selectedChapterId.value ? [selectedChapterId.value] : []);
    const quiz = await run<any>(() => api.post("/learning/quizzes/generate", {
      course_id: selectedCourseId.value,
      chapter_id: chapterIds.length === 1 ? chapterIds[0] : undefined,
      chapter_ids: chapterIds,
      title: smartQuiz.value ? "薄弱点章节练习" : "章节练习",
      quiz_type: "practice",
      question_count: count,
      prefer_weak_points: smartQuiz.value,
      difficulty: practiceDifficulty.value || "mixed",
    }));
    if (quiz) emit("notice", quiz.id ? "success" : "info", queuedQuizMessage(quiz) || "已生成");
    await loadQuizPage();
    if (quiz?.id) await startQuiz(quiz.id);
    if (quiz && !quiz.id) await loadNotifications(true);
  } finally {
    quizGenerating.value = false;
  }
}
function latestQuizAttempt(quiz: any) {
  return quiz?.latest_attempt || quiz?.last_attempt || quiz?.best_attempt || (Array.isArray(quiz?.attempts) ? quiz.attempts[0] : null);
}
function practiceRecordTime(quiz: any) {
  const attempt = latestQuizAttempt(quiz);
  return attempt?.submitted_at || attempt?.created_at || quiz?.updated_at || quiz?.created_at || null;
}
async function openQuiz(quiz: any) {
  const latest = latestQuizAttempt(quiz);
  if (latest?.id) {
    await viewQuizAttempt(latest.id);
    return;
  }
  await startQuiz(quiz.id);
}
async function startQuiz(id: number) {
  const attempts = await run<any[]>(() => api.get(`/learning/quizzes/${id}/attempts`));
  if (attempts?.length) {
    await viewQuizAttempt(attempts[0].id);
    return;
  }
  quizDetail.value = await run(() => api.get(`/learning/quizzes/${id}`));
  if (!quizDetail.value) return;
  Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]);
  attempt.value = null;
  answeringQuiz.value = true;
}
async function viewQuizAttempt(attemptId: number) {
  const detail = await run<any>(() => api.get(`/learning/attempts/${attemptId}`));
  if (!detail) return;
  Object.keys(quizAnswers).forEach((key) => delete quizAnswers[Number(key)]);
  quizDetail.value = {
    quiz: detail.quiz || detail.attempt?.quiz || {},
    questions: (detail.answers || []).map((row: any) => row.question).filter(Boolean),
  };
  attempt.value = detail;
  answeringQuiz.value = true;
}
function setQuizAnswer(questionId: number, answer: any) { quizAnswers[questionId] = answer; }
async function submitQuiz() {
  if (!quizDetail.value || quizSubmitting.value) return;
  quizSubmitting.value = true;
  try {
    const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer }));
    attempt.value = await run(() => api.post(`/learning/quizzes/${quizDetail.value.quiz.id}/submit`, { answers }), "已提交");
    await loadQuizPage();
    await loadWrongBook();
  } finally {
    quizSubmitting.value = false;
  }
}
function togglePracticeChapter(id: number) { selectedPracticeChapters.value = selectedPracticeChapters.value.includes(id) ? selectedPracticeChapters.value.filter((item) => item !== id) : [...selectedPracticeChapters.value, id]; }

async function loadWrongBook() { if (!selectedCourseId.value) return; wrongQuestions.value = (await run<any[]>(() => api.get("/learning/wrong-questions", { course_id: selectedCourseId.value }))) || []; weakPoints.value = (await run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || []; }
async function loadWrongPractice(wrongQuestionId?: number) {
  if (!selectedCourseId.value || wrongPracticeGenerating.value) return;
  wrongPracticeGenerating.value = true;
  try {
    if (!wrongQuestions.value.length) await loadWrongBook();
    if (!wrongQuestions.value.length) {
      emit("notice", "info", "暂无错题可重练");
      return;
    }
    const quiz = await run<any>(() => api.post("/learning/wrong-questions/practice", undefined, { course_id: selectedCourseId.value, ...(wrongQuestionId ? { wrong_question_id: wrongQuestionId } : {}) }));
    if (quiz) emit("notice", quiz.id ? "success" : "info", queuedQuizMessage(quiz, "错题重练已加入生成队列，生成成功后会通知你") || "已生成");
    if (quiz) { await go("studentQuizzes"); await loadQuizPage(); if (quiz.id) await startQuiz(quiz.id); }
    if (quiz && !quiz.id) await loadNotifications(true);
  } finally {
    wrongPracticeGenerating.value = false;
  }
}
function practiceWrong(item: any) { loadWrongPractice(item?.wrong_question_id); }
function clearWrongFilters() { wrongKeyword.value = ""; wrongStatus.value = ""; selectedWrongKnowledge.value = ""; }

async function loadPlans() {
  plans.value = (await run<any[]>(() => api.get("/learning/plans", { course_id: selectedCourseId.value || undefined }))) || [];
  tasks.value = plans.value[0] ? ((await run<any[]>(() => api.get(`/learning/plans/${plans.value[0].id}/tasks`))) || []) : [];
  checkinDays.value = completedTaskDateKeys(tasks.value);
  await loadProfile();
}
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
    checkinDays.value = completedTaskDateKeys(tasks.value);
    await loadDashboard();
  }
}
async function checkinTask(id: number) { await run(() => api.post(`/learning/tasks/${id}/checkin`, { notes: "" }), "已打卡"); await loadDashboard(); await loadPlans(); }

function validAvatarFile(file: File) {
  const nameOk = /\.(jpe?g|png|webp|gif)$/i.test(file.name || "");
  const typeOk = !file.type || file.type.startsWith("image/");
  if (!nameOk || !typeOk) {
    emit("notice", "warning", "请上传 JPG、PNG、WEBP 或 GIF 图片");
    return false;
  }
  if (file.size > 5 * 1024 * 1024) {
    emit("notice", "warning", "头像不能超过 5MB");
    return false;
  }
  return true;
}
async function uploadProfileAvatar(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || !validAvatarFile(file)) return;
  avatarUploading.value = true;
  try {
    const form = new FormData();
    form.set("file", file);
    const data = await api.post<any>("/student/profile/avatar", form);
    applyStudentProfile(data);
    emit("notice", "success", "头像已更新");
  } catch (error) {
    emit("notice", "error", (error as Error).message);
  } finally {
    avatarUploading.value = false;
  }
}
async function saveProfile() { const data = await run<any>(() => api.patch("/student/profile", { nickname: profileForm.nickname, avatar_url: profileForm.avatar_url, bio: profileForm.bio, school: profileForm.school }), "已保存"); if (data) applyStudentProfile(data); }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); const res = await run(() => api.post<{ access_token: string }>("/auth/me/password", passwordForm), "已保存"); if (res?.access_token) setToken(res.access_token); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }
async function saveNotices() {
  const settings = noticeSettings.map((item) => ({ key: item.key, enabled: Boolean(item.enabled) }));
  const data = await run<any[]>(() => api.put("/student/notifications", { settings }), "已保存");
  if (data) noticeSettings.splice(0, noticeSettings.length, ...normalizeNoticeSettings(data));
}

type SelectOption = { label: string; value: string | number; danger?: boolean };
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
      h("rect", { width: 64, height: 64, rx: 32, fill: "#F9F8F6" }),
      h("circle", { cx: 32, cy: 25, r: 11, fill: "#00B8D4", opacity: "0.95" }),
      h("path", { d: "M16 53c2.8-10.2 9-15.4 16-15.4S45.2 42.8 48 53", fill: "#121614", opacity: "0.92" }),
      h("path", { d: "M48 12l1.8 4.4L54 18l-4.2 1.6L48 24l-1.8-4.4L42 18l4.2-1.6L48 12Z", fill: "#06B6D4" }),
      h("path", { d: "M18 14l1.1 2.7L22 18l-2.9 1.3L18 22l-1.1-2.7L14 18l2.9-1.3L18 14Z", fill: "#00E5FF" })
    ]);
  }
});

const RingProgress = defineComponent({
  props: { value: { type: Number, default: 0 }, tone: { type: String, default: "primary" } },
  setup(p) {
    return () => {
      const value = Math.max(0, Math.min(100, Number(p.value || 0)));
      const stroke = p.tone === "success" ? "#2E7D32" : p.tone === "ai" ? "#00B8D4" : "#00B8D4";
      const radius = 28;
      const circumference = 2 * Math.PI * radius;
      return h("svg", { width: 72, height: 72, viewBox: "0 0 72 72", style: { transform: "rotate(-90deg)" } }, [
        h("circle", { cx: 36, cy: 36, r: radius, fill: "none", stroke: "rgba(140,148,143,.22)", "stroke-width": 8 }),
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
          h("div", { class: "profile-timeline-content" }, [
            h("div", { class: "profile-timeline-head" }, [
              h("strong", item.title || "学习记录"),
              h("time", relativeTime(item.time))
            ]),
            item.meta ? h("p", item.meta) : null
          ])
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
  props: {
    lesson: { type: Object as PropType<any>, required: true },
    index: { type: Number, required: true },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false }
  },
  emits: ["open"],
  setup(p, { emit: update }) {
    return () => h("button", { type: "button", class: ["lesson-item", p.lesson.progress_percent > 0 && p.lesson.progress_percent < 100 ? "current" : "", p.loading ? "loading" : ""], disabled: p.disabled || p.loading, onClick: () => update("open") }, [
      h("b", String(p.index + 1).padStart(2, "0")),
      h("div", [h("strong", p.lesson.title), h("small", p.loading ? "正在打开课时..." : `第 ${p.lesson.current_page || 1} 页 · ${p.lesson.progress_percent || 0}%`)]),
      p.loading ? h(LoadingMark, { label: false, class: "inline-loading-mark" }) : p.lesson.progress_percent >= 100 ? h(CheckCircle, { size: 18 }) : h(Play, { size: 18 })
    ]);
  }
});

const MaterialRow = defineComponent({
  props: { item: { type: Object as PropType<any>, required: true } },
  setup(p) {
    return () => h("div", { class: "material-row" }, [
      h("span", { class: "file-badge" }, [h(FileText, { size: 16 })]),
      h("div", [h("strong", p.item.title || p.item.original_filename || "课程资料"), h("small", `${p.item.material_type || "file"} · ${p.item.size_label || optionText(p.item.size_bytes || 0)}`)]),
      h("div", { class: "material-row-actions" }, [
        h("button", { type: "button", class: "material-row-action primary", onClick: () => previewMaterial(p.item) }, [h(Eye, { size: 14 }), "预览"]),
        h("button", { type: "button", class: "material-row-action", onClick: () => downloadMaterial(p.item) }, [h(Download, { size: 14 }), "下载"])
      ])
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
    return () => h("div", { class: ["mini-metric", p.tone] }, [
      h("span", { class: "mini-metric-icon" }, [h(p.icon as any, { size: 18 })]),
      h("div", { class: "mini-metric-copy" }, [h("strong", String(p.value)), h("span", p.label)])
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
    const bodyHtml = computed(() => renderRichText(p.data?.content || p.data?.hint || p.data?.answer || "暂无内容"));
    return () => h("section", { class: "guide-step" }, [
      h("button", { type: "button", onClick: () => update(p.data ? "toggle" : "load") }, [h("b", String(p.level)), h("strong", `第 ${p.level} 步 · ${title.value}`), h(ChevronDown, { size: 16, class: { rotate: p.open } })]),
      h(Transition, { name: "accordion" }, {
        default: () => p.open && p.data ? h("div", { class: "guide-body" }, [
          h("div", { class: "guide-content markdown-body", innerHTML: bodyHtml.value }),
          p.data.steps?.length ? h("ol", { class: "guide-points" }, p.data.steps.map((step: string, index: number) => h("li", { key: index }, [
            h("div", { class: "markdown-body", innerHTML: renderRichText(step) })
          ]))) : null,
          p.data.final_answer ? h("div", { class: "guide-answer markdown-body", innerHTML: renderRichText(`**答案**\n\n${p.data.final_answer}`) }) : null
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
    const exitConfirming = ref(false);
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
          h("button", { type: "button", class: "exam-exit-btn", onClick: () => { exitConfirming.value = true; } }, [h(ArrowLeft, { size: 18 }), "退出练习"]),
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
        h(Teleport, { to: "body" }, [
          h(Transition, { name: "modal-pop" }, {
            default: () => confirming.value ? h("div", { class: "exam-modal-mask exam-modal-scope" }, [
              h("article", { class: "exam-confirm-card" }, [
                h("div", { class: "exam-modal-head" }, [h(AlertTriangle, { size: 22 }), h("h2", "确认交卷"), h("button", { type: "button", onClick: () => { confirming.value = false; } }, [h(X, { size: 16 })])]),
                h("p", unanswered.length ? `还有 ${unanswered.length} 道未答` : "所有题目已作答"),
                marked.value.length ? h("p", `已标记 ${marked.value.length} 道`) : null,
                h("footer", [h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: p.submitting, onClick: () => { confirming.value = false; } }, "继续作答"), h("button", { type: "button", class: "exam-btn exam-btn-primary", disabled: p.submitting, "data-loading": p.submitting, onClick: submit }, "确认交卷")])
              ])
            ]) : null
          }),
          h(Transition, { name: "modal-pop" }, {
            default: () => exitConfirming.value ? h("div", { class: "exam-modal-mask exam-modal-scope" }, [
              h("article", { class: "exam-confirm-card" }, [
                h("div", { class: "exam-modal-head" }, [h(AlertTriangle, { size: 22 }), h("h2", "退出练习？"), h("button", { type: "button", onClick: () => { exitConfirming.value = false; } }, [h(X, { size: 16 })])]),
                h("p", "当前作答不会自动保存，确认退出后会回到习题选择页。"),
                h("footer", [
                  h("button", { type: "button", class: "exam-btn exam-btn-outline", onClick: () => { exitConfirming.value = false; } }, "继续作答"),
                  h("button", { type: "button", class: "exam-btn exam-btn-primary", onClick: () => update("exit") }, "退出到选择页")
                ])
              ])
            ]) : null
          })
        ])
      ]);
    };
  }
});

const QuizCard = defineComponent({
  props: { quiz: { type: Object as PropType<any>, required: true } },
  emits: ["open", "review"],
  setup(p, { emit: update }) {
    const attempts = computed(() => Array.isArray(p.quiz.attempts) ? p.quiz.attempts : []);
    const latestAttempt = computed(() => p.quiz.latest_attempt || p.quiz.last_attempt || p.quiz.best_attempt || attempts.value[0] || null);
    const attempted = computed(() => Boolean(latestAttempt.value?.id));
    const attemptLabel = (item: any, index: number) => {
      const order = attempts.value.length - index;
      const score = item?.score !== undefined ? `${Math.round(Number(item.score))}分` : "解析";
      return attempts.value.length > 1 ? `第${order}次 ${score}` : `查看解析 ${score}`;
    };
    return () => h("article", { class: "quiz-card" }, [
      h("h2", p.quiz.title),
      h("p", p.quiz.description || `${p.quiz.total_score || 0} 分 · ${statusText(p.quiz.status || "published")}`),
      h("footer", [
        h("span", { class: "tag" }, attempted.value ? "已完成" : (p.quiz.quiz_type || "practice")),
        attempts.value.slice(0, 3).map((item: any, index: number) => h("button", {
          type: "button",
          class: "btn btn-secondary btn-sm",
          onClick: () => update("review", item.id),
        }, [h(Eye, { size: 14 }), attemptLabel(item, index)])),
        h("button", { type: "button", class: ["btn", attempted.value ? "btn-secondary" : "btn-primary", "btn-sm"], onClick: () => update("open") }, [attempted.value ? h(Eye, { size: 14 }) : h(Play, { size: 14 }), attempted.value ? "查看最近解析" : "开始"])
      ])
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
      h("button", {
        type: "button",
        "aria-haspopup": "listbox",
        "aria-expanded": open.value,
        onClick: () => { open.value = !open.value; },
        onKeydown: (event: KeyboardEvent) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            open.value = !open.value;
          }
        }
      }, [p.label, h(ChevronDown, { size: 14 })]),
      h(Transition, { name: "popover" }, {
        default: () => open.value ? h("div", { class: "select-pop", role: "listbox", style: popStyle.value }, p.items.map((item) => h("button", { type: "button", role: "option", key: item.value, onClick: () => { update("select", String(item.value)); open.value = false; } }, item.label))) : null
      })
    ]);
  }
});

function onStudentDocumentPointerDown(event: PointerEvent) {
  const elementTarget = event.target as Element | null;
  if (!elementTarget?.closest?.(".lesson-selection-popover")) hideLessonSelectionMenu();
  const target = event.target as Node;
  if (topActionsRef.value?.contains(target) || noticePopRef.value?.contains(target) || userPopRef.value?.contains(target)) return;
  noticeOpen.value = false;
  userMenuOpen.value = false;
}
function onStudentDocumentKeydown(event: KeyboardEvent) {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    if (!classroomOpen.value) return;
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    if (searchOpen.value || historyOpen.value || joinOpen.value || planModalOpen.value || completeOpen.value) return;
    const target = event.target as HTMLElement | null;
    if (target) {
      const tag = target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable) return;
    }
    event.preventDefault();
    if (event.key === "ArrowLeft") void prevPage();
    else void nextPage();
    return;
  }
  if (event.key !== "Escape") return;
  if (searchOpen.value) closeSearch();
  hideLessonSelectionMenu();
  closeMaterialPreview();
  noticeOpen.value = false;
  userMenuOpen.value = false;
  settingsOpen.value = false;
  historyOpen.value = false;
  joinOpen.value = false;
  planModalOpen.value = false;
  completeOpen.value = false;
}
function onStudentVisibilityChange() {
  if (!document.hidden) void loadNotifications(true);
}
function onStudentWindowFocus() {
  void loadNotifications(true);
}

onMounted(async () => {
  document.addEventListener("pointerdown", onStudentDocumentPointerDown);
  window.addEventListener("keydown", onStudentDocumentKeydown, { capture: true });
  document.addEventListener("selectionchange", scheduleLessonSelectionCheck);
  document.addEventListener("visibilitychange", onStudentVisibilityChange);
  document.addEventListener("fullscreenchange", onLessonFullscreenChange);
  window.addEventListener("focus", onStudentWindowFocus);
  window.addEventListener("resize", updateTopNavIndicator);
  window.addEventListener("resize", scheduleQaLatestButtonCheck);
  window.addEventListener("resize", updateCompactLessonLayout);
  window.addEventListener("scroll", scheduleQaLatestButtonCheck, { passive: true });
  updateCompactLessonLayout();
  syncSlideStageResizeObserver();
  if (active.value === "studentLessonStudy") {
    await loadActive();
    await loadCourses();
  } else {
    await loadCourses();
    await loadActive();
  }
  updateTopNavIndicator();
  await loadNotifications(true);
  notificationTimer = window.setInterval(() => {
    if (!document.hidden) void loadNotifications(true);
  }, 15000);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onStudentDocumentPointerDown);
  window.removeEventListener("keydown", onStudentDocumentKeydown, { capture: true } as EventListenerOptions);
  document.removeEventListener("selectionchange", scheduleLessonSelectionCheck);
  document.removeEventListener("visibilitychange", onStudentVisibilityChange);
  document.removeEventListener("fullscreenchange", onLessonFullscreenChange);
  window.removeEventListener("focus", onStudentWindowFocus);
  window.removeEventListener("resize", updateTopNavIndicator);
  window.removeEventListener("resize", scheduleQaLatestButtonCheck);
  window.removeEventListener("resize", updateCompactLessonLayout);
  window.removeEventListener("scroll", scheduleQaLatestButtonCheck);
  slideStageResizeObserver?.disconnect();
  slideStageResizeObserver = undefined;
  if (topNavIndicatorFrame) window.cancelAnimationFrame(topNavIndicatorFrame);
  if (qaScrollFrame) window.cancelAnimationFrame(qaScrollFrame);
  if (lessonSelectionTimer) window.clearTimeout(lessonSelectionTimer);
  stopLessonResize();
  stopStudyClock();
  if (chromeTimer) clearTimeout(chromeTimer);
  if (joinTimer) clearTimeout(joinTimer);
  if (searchTimer) clearTimeout(searchTimer);
  if (notificationTimer) clearInterval(notificationTimer);
  if (pageTransitionTimer) clearTimeout(pageTransitionTimer);
  if (noteTimer) clearTimeout(noteTimer);
});
</script>
