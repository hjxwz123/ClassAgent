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

  <StudentLessonStudy v-else-if="classroomOpen" />

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
          <div v-for="item in notifications" :key="item.id || `${item.type}-${item.title}`" class="notice-item" :class="{ unread: item.unread, clickable: notificationQuizId(item) > 0 }" :role="notificationQuizId(item) > 0 ? 'button' : undefined" :tabindex="notificationQuizId(item) > 0 ? 0 : undefined" @click="onNotificationClick(item)" @keydown.enter="onNotificationClick(item)">
            <Bell :size="15" />
            <div><strong>{{ item.title }}</strong><p v-if="item.message">{{ item.message }}</p><small>{{ item.course_name ? `${item.course_name} · ` : '' }}{{ relativeTime(item.time) }}<span v-if="notificationQuizId(item) > 0" class="notice-go">· 点击去练习 <ArrowRight :size="12" /></span></small></div>
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
            <StudentHome />
          </template>

          <template v-else-if="active === 'studentCourses'">
            <StudentCourses />
          </template>

          <template v-else-if="active === 'studentCourseHome'">
            <StudentCourseHome />
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
                    <CourseSelect v-model="selectedCourseId" :courses="courses" @reload="loadActive" @join="joinOpen = true" />
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
            <StudentTutoring />
          </template>

          <template v-else-if="active === 'studentKnowledge'">
            <StudentKnowledge />
          </template>

          <template v-else-if="active === 'studentQuizzes'">
            <section class="quiz-modern-page">
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
                  <CourseSelect v-model="selectedCourseId" :courses="courses" @reload="loadActive" @join="joinOpen = true" />
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
                <QuizCard v-for="quiz in courseQuizzes" :key="quiz.id" :quiz="quiz" :has-draft="hasQuizDraft(Number(quiz.id))" :retaking="quizRetaking" @open="openQuiz(quiz)" @review="(attemptId) => reviewAttempt(quiz.id, attemptId)" @retake="retakeQuiz(quiz.id, 'full')" />
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

                  <div class="practice-config-section practice-type-section">
                    <span class="practice-config-label">题型（可多选）</span>
                    <div class="practice-chapter-chips">
                      <button
                        v-for="item in quizTypeOptions"
                        :key="item.value"
                        type="button"
                        class="practice-chip"
                        :class="{ active: selectedQuizTypes.includes(item.value) }"
                        @click="toggleQuizType(item.value)"
                      >
                        {{ item.label }}
                      </button>
                    </div>
                  </div>

                  <div class="practice-difficulty-row">
                    <strong>难度</strong>
                    <AppSelect v-model="practiceDifficulty" :options="quizDifficultyOptions" />
                  </div>

                  <button
                    type="button"
                    class="practice-generate-btn"
                    :data-loading="quizGenerating"
                    :disabled="quizGenerating"
                    @click="generateQuiz"
                  >
                    <Sparkles :size="20" />{{ quizGenerating ? '出卷中…' : '智能生成练习' }}
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
                      <h2>错题重练 · 变式训练</h2>
                      <p>{{ wrongQuestions.length ? `${pendingWrongCount} 道待巩固 · AI 换情境出同考点新题` : '暂无错题' }}</p>
                    </div>
                    <span><Play :size="16" />{{ wrongQuestions.length ? '开始' : '暂无' }}</span>
                  </button>

                  <div class="practice-history-title">
                    <History :size="18" />我的练习
                    <div class="quiz-filter-caps">
                      <button type="button" :class="{ active: quizListFilter === 'all' }" @click="quizListFilter = 'all'">全部</button>
                      <button type="button" :class="{ active: quizListFilter === 'pending' }" @click="quizListFilter = 'pending'">待完成</button>
                      <button type="button" :class="{ active: quizListFilter === 'done' }" @click="quizListFilter = 'done'">已完成</button>
                    </div>
                  </div>
                  <div class="practice-history-list">
                    <div v-for="task in generatingTasks" :key="`gen-${task.task_id || task.id}`" class="practice-history-item quiz-gen-item" :class="{ failed: task.status === 'failed' }">
                      <div class="practice-history-left">
                        <span class="practice-history-icon quiz-gen-icon"><Sparkles :size="20" /></span>
                        <div>
                          <strong>{{ task.title || 'AI 出题' }}</strong>
                          <small>{{ task.status === 'failed' ? '生成失败，可重新发起生成' : 'AI 正在出题，完成后自动出现在列表…' }}</small>
                        </div>
                      </div>
                      <button v-if="task.status === 'failed'" type="button" class="quiz-gen-dismiss" @click="ignoreGenerationTask(Number(task.task_id || task.id))"><X :size="14" />忽略</button>
                      <span v-else class="quiz-gen-spinner" aria-hidden="true"></span>
                    </div>
                    <div v-for="quiz in filteredPracticeQuizzes" :key="quiz.id" class="practice-history-row" :class="`quiz-status-${quizCardStatus(quiz)}`">
                      <button type="button" class="practice-history-item" @click="openQuiz(quiz)">
                        <div class="practice-history-left">
                          <span class="practice-history-icon"><Layers :size="20" /></span>
                          <div>
                            <strong>{{ quiz.title }}</strong>
                            <small>{{ quizQuestionMeta(quiz) }} · {{ relativeTime(practiceRecordTime(quiz)) }}</small>
                          </div>
                        </div>
                        <em v-if="quizCardStatus(quiz) === 'done'">{{ quizScoreLabel(quiz) }}</em>
                        <span v-else-if="quizCardStatus(quiz) === 'doing'" class="quiz-status-pill doing"><Play :size="13" />继续作答</span>
                        <span v-else class="quiz-status-pill todo"><Play :size="13" />开始</span>
                      </button>
                      <button v-if="quizCardStatus(quiz) === 'todo'" type="button" class="practice-history-del" title="删除未开始的练习" @click.stop="requestDeletePractice(quiz)"><Trash2 :size="15" /></button>
                    </div>
                    <EmptyState v-if="!filteredPracticeQuizzes.length && !generatingTasks.length" :text="quizListFilter === 'all' ? '还没有练习，用左侧生成器让 AI 出一份吧' : '该筛选下暂无练习'" />
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
                    <p>《{{ courseScopeName }}》· 纸面复习，按遗忘曲线重练</p>
                  </div>
                  <span class="wrong-review-stamp" aria-hidden="true">REVIEW</span>
                </div>
                <div class="wrong-head-actions">
                  <CourseSelect v-model="selectedCourseId" :courses="courses" @reload="loadActive" @join="joinOpen = true" />
                  <button class="btn btn-secondary" :data-loading="wrongPracticeGenerating" :disabled="wrongPracticeGenerating || !wrongQuestions.length" @click="loadWrongPractice()"><Sparkles :size="16" />变式重练</button>
                </div>
              </header>

              <!-- 艾宾浩斯：今日待复习提醒 + 一键开始复习 -->
              <article v-if="wrongQuestions.length" class="wrong-review-today" :class="{ due: dueWrongCount > 0 }">
                <span class="wrt-icon"><Clock :size="22" /></span>
                <div class="wrt-body">
                  <strong>{{ dueWrongCount > 0 ? `今日待复习 ${dueWrongCount} 道` : '今日已无到期复习' }}</strong>
                  <p v-if="dueWrongCount > 0">按艾宾浩斯遗忘曲线，这些错题到复习时间了 —— 趁记忆还在，巩固一遍。</p>
                  <p v-else>错题都在计划内，答对会自动排到下一档（1 → 2 → 4 → 7 → 15 → 30 天）。</p>
                </div>
                <button class="btn" :class="dueWrongCount > 0 ? 'btn-primary' : 'btn-ghost'" :data-loading="wrongPracticeGenerating" :disabled="wrongPracticeGenerating" @click="loadWrongPractice()"><RefreshCw :size="16" />{{ dueWrongCount > 0 ? '开始复习' : '提前复习' }}</button>
              </article>

              <article class="wrong-hero">
                <div class="mastery-pending"><strong>{{ pendingWrongCount }}</strong><span>未掌握</span></div>
                <div class="mastery-consolidating"><strong>{{ consolidatingWrongCount }}</strong><span>复习巩固中</span></div>
                <div class="mastery-resolved"><strong>{{ resolvedWrongCount }}</strong><span>已掌握</span></div>
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
                  <WrongCard v-for="item in filteredWrongQuestions" :key="item.wrong_question_id" :item="item" :generating="wrongPracticeGenerating" @practice="practiceWrong(item)" />
                  <div v-if="!wrongQuestions.length" class="wrong-empty-chalk">
                    <strong>太棒了，一道错题都没有！</strong>
                    <p>做题时答错的题目会自动收进这里，并按遗忘曲线提醒你按时复习。</p>
                  </div>
                  <EmptyState v-else-if="!filteredWrongQuestions.length" text="没有符合当前筛选的错题" />
                </section>
              </div>
            </section>
          </template>

          <template v-else-if="active === 'studentPlans'">
            <StudentPlans />
          </template>

          <template v-else-if="active === 'studentProfile'">
            <StudentProfile />
          </template>

          <template v-else-if="active === 'studentMaterials'">
            <PageTitle title="课程资料"><CourseSelect v-model="selectedCourseId" :courses="courses" @reload="loadActive" @join="joinOpen = true" /></PageTitle>
            <article class="panel-card"><MaterialRow v-for="item in courseHome.materials || []" :key="item.id" :item="item" @preview="previewMaterial" @download="downloadMaterial" /><EmptyState v-if="!(courseHome.materials || []).length" text="暂无资料" /></article>
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
              <div class="pretty-input"><Search :size="15" /><input v-model="qaKeyword" placeholder="输入即筛选，回车搜索云端历史" @keyup.enter="loadQaHistory" /></div>
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
            <footer><button class="btn btn-ghost" @click="joinOpen = false">取消</button><button class="btn btn-primary" :data-loading="joinSubmitting" :disabled="joinChecking || joinSubmitting || !joinPreview || joinPreview.already_joined" @click="confirmJoin">确认加入</button></footer>
          </article>
        </div>
      </transition>

      <ConfirmDialog
        :open="deletePracticeConfirmOpen"
        title="删除练习"
        :message="`确认删除练习「${deletePracticeTarget?.title || '未命名练习'}」？该练习及其作答草稿将被永久删除，不可恢复。`"
        confirm-text="删除"
        cancel-text="取消"
        tone="danger"
        @confirm="confirmDeletePractice"
        @cancel="deletePracticeConfirmOpen = false"
      />
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, Teleport, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Bell, BookMarked, BookOpen, CalendarCheck, Camera, Check, CheckCircle,
  ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, FileText, GitBranch, Grid2X2, History,
  Info, Flag, Layers, ListChecks, LogOut, Maximize, MessageCircle, PanelRight, Pause, Pencil,
  Play, Plus, PlusCircle, Presentation, Quote, RefreshCw, Search, Send, Settings, Shield,
  Sparkles, Square, Trash2, User, X, XCircle, Zap
} from "../icons";
import { api } from "../api/client";
import { PageTitle, DefaultUserAvatar, EmptyState } from "./student/components/primitives";
import { QuizCard, WrongCard } from "./student/components/cards";
import { CourseSelect, MaterialRow } from "./student/components/course";
import { StudentCtxKey } from "./student/context";
import StudentTutoring from "./student/pages/StudentTutoring.vue";
import StudentKnowledge from "./student/pages/StudentKnowledge.vue";
import StudentHome from "./student/pages/StudentHome.vue";
import StudentLessonStudy from "./student/pages/StudentLessonStudy.vue";
import StudentPlans from "./student/pages/StudentPlans.vue";
import StudentProfile from "./student/pages/StudentProfile.vue";
import StudentCourses from "./student/pages/StudentCourses.vue";
import StudentCourseHome from "./student/pages/StudentCourseHome.vue";
import { routeByPage } from "../router";
import type { LessonDetail, MaterialDetail, User as UserType } from "../types";
import { copyToClipboard } from "../utils/clipboard";
import { timestampMs, relativeTime, formatTime } from "../utils/datetime";
import AppSelect from "../components/AppSelect.vue";
import BrandLogo from "../components/BrandLogo.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import LoadingMark from "../components/LoadingMark.vue";
import MaterialPreviewModal from "../components/MaterialPreviewModal.vue";
import PageLoader from "../components/PageLoader.vue";
import SelectMenu from "../components/SelectMenu";
import ThemeToggle from "../components/ThemeToggle.vue";
import ChatList from "./student/components/ChatList";
import { useQaEngine, type QaAttachment, type ChatMessage } from "./student/useQaEngine";
import { useStudentSearch } from "./student/useStudentSearch";
import { useStudentQuiz } from "./student/useStudentQuiz";
import "../styles/student/base.css";
import "../styles/student/study-room.css";
import "../styles/student/courses.css";
import "../styles/student/qa.css";
import "../styles/student/quiz.css";
import "../styles/student/plan-profile.css";
import "../styles/student/tutoring.css";
import "../styles/student/classagent.css";

type QaHistoryConversation = { id: number; conversation_id: number; course_id: number; user_id: number; title: string; question: string; answer_preview?: string; created_at: string; updated_at?: string; lesson_page_id?: number | null; attachments?: QaAttachment[]; is_favorite?: boolean; record_count: number };

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string, action?: { label: string; onClick: () => void }]; authed: [user: UserType] }>();
const route = useRoute();
const router = useRouter();

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
// 记住上次进入的课程主页：从顶部"我的课程"标签返回时回到该课程，而非每次都退回课程选择列表。
const lastCourseHomeId = ref<number>(Number(localStorage.getItem("student_last_course_home_id") || 0));
const notifications = ref<any[]>([]);
const lessons = ref<any[]>([]);
const materialPreviewItem = ref<any | null>(null);
const materialPreviewDetail = ref<MaterialDetail | null>(null);
const materialPreviewLoading = ref(false);

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
const joinSubmitting = ref(false);
const joinError = ref("");
// 删除未开始练习前的二次确认（不可逆破坏性操作）。
const deletePracticeConfirmOpen = ref(false);
const deletePracticeTarget = ref<any | null>(null);
let joinTimer: number | undefined;
let notificationTimer: number | undefined;
let topNavIndicatorFrame = 0;
let pageTransitionTimer: number | undefined;

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
const currentPage = ref(1);
const pendingSourcePageNumber = ref<number | null>(null);
const pendingSourcePageId = ref<number | null>(null);
const pageDirection = ref<"next" | "prev">("next");
let globalAbortController: AbortController | null = null;
const globalQuestionInput = ref<HTMLTextAreaElement | null>(null);
const lessonSelectionMenu = reactive({ open: false, text: "", x: 0, y: 0 });
// QA 流式引擎（全局问答与课堂问答共用）。跟随滚动钩子接全局问答页的滚动函数（课堂问答 follow=false 不触发）。
const {
  patchChatMessage, flushQaDeltas, queueQaDelta, applyQaStreamEvent,
  questionCompositionState, handleQuestionCompositionStart, handleQuestionCompositionEnd,
  submitQuestionOnEnter, resizeQuestionInput,
} = useQaEngine({ isNearLatest: () => isQaNearLatest(320), keepAtLatest: keepQaAtLatestIfNeeded });
function handleGlobalQuestionKeydown(event: KeyboardEvent) { submitQuestionOnEnter(event, "global", askGlobal); }
const thumbOpen = ref(false);
const settingsOpen = ref(false);
const studySeconds = ref(0);
// #35：上报学习时长时使用真实停留秒数的增量，而不是写死的 +30 秒。
// reportedStudySeconds 记录上次已上报到 studySeconds 的位置，每次上报真实差值。
const reportedStudySeconds = ref(0);
const completeOpen = ref(false);
let studyTimer: number | undefined;
let lessonLoadSeq = 0;
let courseHomeLoadSeq = 0;
let suppressCourseScopedReset = false;
let qaScrollFrame = 0;
let qaConversationLoadSeq = 0;

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

const selectedChapterId = ref<number | null>(null);
const selectedKnowledgeId = ref<number | null>(null);
const weakPoints = ref<any[]>([]);
// 全局搜索（跨课程/课时/资料/知识点/问答）：状态与检索逻辑内聚在 composable，命中跳转由此处导航动作驱动。
const {
  searchOpen, globalSearch, searchInput, searchLoading, searchError, searchActiveIndex,
  searchResultGroups, flatSearchResults, searchTypeMeta,
  pruneSearchCache, closeSearch, openSearch, moveSearchSelection, focusSearchResult, isSearchResultActive,
  openSearchResult, openActiveSearchResult,
} = useStudentSearch({ courses, selectedCourseId, selectedChapterId, selectedKnowledgeId, openCourse, openLesson, loadCourseHome, go, loadQaHistory, reuseHistory });

// 出题/生成任务/错题本/练习 子系统整体抽入 useStudentQuiz 组合式（脚本级抽离，模板保持不变）。
// 返回的 ref/函数在此解构，模板与外壳的调用点一字不改；共享的 openQuizSelection、generateKnowledgeQuiz 仍向 ctx provide。
const {
  quizTab, quizzes, selectedPracticeChapters, quizQuestionCount, practiceDifficulty, smartQuiz,
  quizGenerating, wrongPracticeGenerating, quizRetaking, generatingTasks, quizListFilter, quizDraftVersion,
  wrongQuestions, wrongKeyword, wrongStatus, selectedWrongKnowledge, selectedQuizTypes,
  quizCountOptions, quizTypeOptions, quizDifficultyOptions, wrongStatusOptions,
  courseQuizzes, practiceQuizzes, filteredPracticeQuizzes, wrongKnowledgeFilters,
  pendingWrongCount, consolidatingWrongCount, resolvedWrongCount, repeatedWrongCount, dueWrongCount,
  filteredWrongQuestions, wrongFilterSummary, weeklyWrongCount,
  toggleQuizType, quizTypeCounts, wrongMastery, queuedQuizMessage, maybeOpenQuizFromQuery, notificationQuizId,
  openQuizSelection, generateKnowledgeQuiz, loadQuizPage,
  quizDraftKey, readQuizDraft, clearQuizDraft, hasQuizDraft, quizCardStatus,
  refreshGenerationTasks, upsertGeneratingTask, removeGeneratingTask, ignoreGenerationTask,
  trackGenerationTask, handleGenerateResult, pollGenerationTask, openQuizById,
  practiceQuizTitle, generateQuiz, latestQuizAttempt, practiceRecordTime,
  openQuiz, startQuiz, reviewAttempt, retakeQuiz, deletePractice, togglePracticeChapter,
  loadWrongBook, loadWrongPractice, practiceWrong, clearWrongFilters,
  quizQuestionMeta, quizScoreLabel,
} = useStudentQuiz({
  run, emit, router, route, active, go,
  selectedCourseId, weakPoints, courseHome, selectedChapterId,
  loadCourseHome, loadNotifications, user: props.user,
});

const plans = ref<any[]>([]);
const tasks = ref<any[]>([]);
const planForm = reactive({ title: "今日学习计划", goal: "", available_days: 7, daily_minutes: 60 });
const planCreating = ref(false);
const checkinDays = ref<string[]>([]);

const profileForm = reactive({ nickname: props.user.nickname, avatar_url: props.user.avatar_url || "", school: "", bio: props.user.bio || "" });
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
// 把所选题型均分到总题量（余数给靠前的题型），转成后端 question_type_counts。

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
const planTodayTasks = computed(() => tasks.value.filter((task: any) => taskDateKey(task) === todayTaskKey()));
const todayTasks = computed(() => {
  if (active.value === "studentPlans") return planTodayTasks.value;
  const dashboardTasks = Array.isArray(dashboard.value.today_tasks) ? dashboard.value.today_tasks : [];
  return dashboardTasks.length ? dashboardTasks : planTodayTasks.value;
});
const doneTasks = computed(() => todayTasks.value.filter((task: any) => task.status === "done").length);
const hasJoinedCourses = computed(() => courses.value.length > 0);
const unreadCount = computed(() => notifications.value.filter((item) => item.unread).length);
// 学期信息来源于后端课程的 term 字段，没有真实学期起止日期时只展示学期名，不再编造“距结束 X 天”的假倒计时。
const activeCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value) || courses.value[0] || null);
const courseScopeName = computed(() => activeCourse.value?.name || "当前课程");

// 向抽出的页面子组件提供共享上下文（provide/inject），避免逐层 prop 传递跨页状态。
function openJoin() { joinOpen.value = true; }
function noticeFromCtx(type: "success" | "warning" | "error" | "info", text: string, action?: { label: string; onClick: () => void }) { emit("notice", type, text, action); }
const currentAvatarUrl = computed(() => profileForm.avatar_url || props.user.avatar_url || "");
const isLessonOpening = computed(() => openingLessonId.value !== null);
const searchKeyword = computed(() => globalSearch.value.trim());
const promptContext = computed(() => {
  const home = courseHome.value || {};
  const courseName = home.course?.name || activeCourse.value?.name || "";
  const lesson = (home.lessons || []).find((item: any) => item?.title)?.title || "";
  const chapter = (home.chapters || []).find((item: any) => item?.title)?.title || "";
  const material = (home.materials || []).find((item: any) => item?.title)?.title || "";
  const weakPoint = weakPoints.value.find((item: any) => item?.knowledge_point || item?.name);
  const point = weakPoint?.knowledge_point || weakPoint?.name || "";
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
// #66：此前是写死的“假 AI 总结”。后端没有按课时生成 AI 学情总结的接口，
// 因此这里改为基于本次会话真实数据(学习时长/页数/提问数)的事实性小结，且不再冒充 AI 生成。
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
// 排序原则：先看"该做的事"——进行中(有草稿) > 未开始 > 已完成，段内按时间倒序。
// #32：后端暂无“每日学习时长”时间序列接口，不再用写死的假数组糊弄。
// 仅展示真实存在的整体学习总时长，按天的柱状分布需后端补 daily 接口后再接入。

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
  // 换课必须清掉章节选择与生成任务，否则生成请求会带上一门课的 chapter_ids。
  selectedPracticeChapters.value = [];
  selectedChapterId.value = null;
  generatingTasks.value = [];
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
  if (active.value === "studentQuizzes") await loadQuizPage();
  if (active.value === "studentPlans") await loadPlans();
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
  // 落在某个课程主页（点进课程、深链或刷新）即记住它，作为"我的课程"标签的恢复目标。
  if (nextPageKey === "studentCourseHome" && routeCourseId()) {
    lastCourseHomeId.value = routeCourseId();
    localStorage.setItem("student_last_course_home_id", String(routeCourseId()));
  }
  if (leavingLessonStudy || (classroomOpen.value && nextPageKey !== "studentLessonStudy")) {
    lessonLoadSeq += 1;
    await leaveClassroom(true);
  }
  await loadActive();
  await maybeOpenQuizFromQuery();
}
// 出卷成功消息点击 / 直达链接带 ?open=<quizId> 落到测验页：直接跳到该卷的独立做题路由。
async function handleStudentNav(key: string) {
  if (key === "studentQuizzes") {
    await openQuizSelection("practice");
    return;
  }
  // "我的课程"标签：从课程工作区之外点回来时，恢复到上次进入的课程主页（而不是每次都退回选择列表）；
  // 若当前已在课程工作区内，或没有可恢复的课程，则进入课程列表（此处可切换/加入课程）。
  if (key === "studentCourses") {
    const inCourseGroup = studentCourseNavKeys.includes(active.value);
    const resumeId = lastCourseHomeId.value;
    if (!inCourseGroup && resumeId && courses.value.some((course) => Number(course.id) === resumeId)) {
      setStudentPageTransition("studentCourseHome");
      await router.push(courseRoute(resumeId));
      return;
    }
  }
  setStudentPageTransition(key);
  await go(key);
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
// 出题/错题重练完成的通知(quiz_generated)携带 resource_id，可点击直达答题页；
// 失败通知(resource_id 为空)与公告/教师提醒/新课时等暂不导航，返回 0 表示不可点击。
async function onNotificationClick(item: any) {
  const quizId = notificationQuizId(item);
  if (!quizId) return;
  noticeOpen.value = false;
  if (item?.unread) void markStudentNotificationsRead(item);
  await openQuizById(quizId);
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
function firstChar(value?: string) { return (value || "-").slice(0, 1); }
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
async function copyText(text: unknown) {
  const copied = await copyToClipboard(text);
  emit("notice", copied ? "success" : "warning", copied ? "已复制" : "复制失败，请手动复制");
}
function chapterName(id?: number | null) { return (courseHome.value.chapters || []).find((item: any) => item.id === id)?.title || "课程章节"; }
function isOpeningLesson(id?: number | null) { return openingLessonId.value === Number(id || 0); }

function formatJoinCode() { joinCode.value = joinCode.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12); joinPreview.value = null; joinError.value = ""; if (joinTimer) window.clearTimeout(joinTimer); if (joinCode.value.length >= 5) joinTimer = window.setTimeout(validateJoinCode, 350); }
async function validateJoinCode() {
  // 边输边校验：用原始 api（不经 run 的全局 error toast），失败只给内联提示，避免重复弹 toast 且区分错误类型。
  joinChecking.value = true; joinError.value = "";
  try {
    const data = await api.get<any>("/student/courses/preview", { course_code: joinCode.value });
    joinPreview.value = data;
    if (data?.already_joined) joinError.value = "你已加入该课程";
  } catch (error) {
    joinPreview.value = null;
    joinError.value = (error as any)?.status === 404 ? "课程码不存在或已停用" : ((error as Error).message || "校验失败，请稍后重试");
  } finally {
    joinChecking.value = false;
  }
}
async function confirmJoin() {
  if (!joinPreview.value || joinSubmitting.value) return;
  joinSubmitting.value = true;
  try {
    // 加入请求单独的提交中态（此前借用校验态 joinChecking，提交期间按钮不转圈、可重复点）。
    const result = await run(() => api.post("/courses/join", { course_code: joinCode.value }), "已加入");
    if (result === null) return; // 失败：保留弹窗与已输入课程码，不关闭、不刷新，避免"像部分成功"。
    joinOpen.value = false; joinCode.value = ""; joinPreview.value = null;
    await loadDashboard();
  } finally {
    joinSubmitting.value = false;
  }
}
function requestDeletePractice(quiz: any) {
  deletePracticeTarget.value = quiz;
  deletePracticeConfirmOpen.value = true;
}
async function confirmDeletePractice() {
  const quiz = deletePracticeTarget.value;
  deletePracticeConfirmOpen.value = false;
  deletePracticeTarget.value = null;
  if (quiz) await deletePractice(quiz);
}
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
  // 课堂本地态（音频/问答/笔记/划词）已随 StudentLessonStudy 组件卸载自动销毁；
  // 外壳只重置自己仍持有、且与路由/翻页共享的那部分。
  stopStudyClock();
  classroomOpen.value = false;
  completeOpen.value = false;
  settingsOpen.value = false;
  thumbOpen.value = false;
  hideLessonSelectionMenu();
  classroomLesson.value = null;
  currentPage.value = 1;
  studySeconds.value = 0;
  reportedStudySeconds.value = 0;
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
    // 笔记与课堂问答历史改由 StudentLessonStudy 组件 onMounted 拉取（组件挂载后即触发）。
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

function hideLessonSelectionMenu() {
  lessonSelectionMenu.open = false;
}

function startStudyClock() { stopStudyClock(); studyTimer = window.setInterval(() => { studySeconds.value += 1; }, 1000); }
function stopStudyClock() { if (studyTimer) window.clearInterval(studyTimer); studyTimer = undefined; }

// 幻灯面板比例/自适配缩放的三个 watcher（换课重置、面板尺寸变化重新测量）已随
// StudentLessonStudy 组件迁移，在组件内部按其生命周期运行。
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

// 全局问答的图片附件（课堂问答的附件由 StudentLessonStudy 组件自持）。模板仅以 'global' 调用。
function qaAttachmentsFor(_scope: "class" | "global") {
  return globalQaAttachments.value;
}

function removeQaAttachment(scope: "class" | "global", index: number) {
  qaAttachmentsFor(scope).splice(index, 1);
}

async function handleQaImageChange(event: Event, scope: "class" | "global") {
  const input = event.target as HTMLInputElement;
  const file = (input.files || [])[0];
  input.value = "";
  if (!file) return;
  const courseId = selectedCourseId.value;
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
  globalQaImageUploading.value = true;
  try {
    const attachment = await run<QaAttachment>(() => api.post("/qa/attachments/image", form), "图片已上传");
    if (attachment) target.push(attachment);
  } finally {
    globalQaImageUploading.value = false;
  }
}

// 全局问答输入框随内容自适应高度（课堂问答输入框由 StudentLessonStudy 组件自持）。
watch(globalQuestion, () => nextTick(() => resizeQuestionInput(globalQuestionInput.value)));
async function askGlobal() {
  if (globalThinking.value || (globalConversationLoading.value && !globalMessages.value.length) || globalQaImageUploading.value) return;
  if (!globalQuestion.value.trim() && !globalQaAttachments.value.length) return;
  // 零课程/未选课程时不再静默失败：给出明确提示，引导先加入或选择课程。
  if (!selectedCourseId.value) { emit("notice", "warning", "请先加入或选择课程后再提问"); return; }
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
      // delta 只进缓冲(每帧统一提交+滚动跟随一次)；其余事件先冲刷缓冲保证顺序，再按原逻辑处理
      if (event === "delta") {
        queueQaDelta(globalMessages, aiMessageId, data, true);
        return;
      }
      flushQaDeltas();
      const shouldFollowLatest = isQaNearLatest(320);
      applyQaStreamEvent(globalMessages, aiMessageId, event, data);
      keepQaAtLatestIfNeeded(shouldFollowLatest);
      if (event === "created" || event === "final") globalConversationId.value = data.conversation_id ?? globalConversationId.value;
    }, undefined, controller.signal);
  } catch (error) {
    // 用户主动停止：保留已生成内容，不提示错误
    flushQaDeltas();
    if (!controller.signal.aborted) {
      const current = globalMessages.value.find((message) => message.id === aiMessageId);
      if (!current?.text) patchChatMessage(globalMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
      emit("notice", "error", (error as Error).message);
    }
  } finally {
    flushQaDeltas();
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
async function loadQaHistory() {
  if (!selectedCourseId.value) return;
  qaHistory.value = (await run<QaHistoryConversation[]>(() => api.get("/qa/history", { course_id: selectedCourseId.value, keyword: qaKeyword.value }))) || [];
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
async function favoriteQaMessage(message: ChatMessage) { if (!message.record_id) return; const nextFavorite = !message.favorite; const ok = await run(() => api.post(`/qa/${message.record_id}/favorite`, { is_favorite: nextFavorite }), nextFavorite ? "已收藏" : "已取消收藏"); if (ok !== null) message.favorite = nextFavorite; }
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
      // classroomTab 已随组件移出；全局问答场景 classroomOpen 为 false，不会进入本分支。
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
  if (fallbackPage && classroomOpen.value) { await jumpPage(fallbackPage); return; }
  // 全局问答里点了只含页码、无课时信息的来源时，之前三个分支全落空、看似可点却无反应：给出明确提示。
  emit("notice", "info", "该来源暂不支持跳转");
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
    tasks.value = data.tasks || [];
    checkinDays.value = completedTaskDateKeys(tasks.value);
    await loadDashboard();
  }
}

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
    if (searchOpen.value || historyOpen.value || joinOpen.value || completeOpen.value) return;
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
  completeOpen.value = false;
}
function onStudentVisibilityChange() {
  if (!document.hidden) void loadNotifications(true);
}
function onStudentWindowFocus() {
  void loadNotifications(true);
}

// provide 放在所有共享 ref/computed/函数声明之后，确保引用均已初始化（函数声明已提升）。
provide(StudentCtxKey, {
  user: props.user,
  selectedCourseId, courses, courseScopeName, hasJoinedCourses,
  courseHome, selectedChapterId, selectedKnowledgeId, weakPoints,
  run, notice: noticeFromCtx, loadActive, loadCourseHome, openJoin, go, chapterName, generateKnowledgeQuiz,
  dashboard, stats, todayTasks, doneTasks, checkinDays, profilePayload, planForm, planCreating, createPlan, loadPlans, loadDashboard,
  profileForm, currentAvatarUrl, noticeSettings, loadProfile, applyStudentProfile, normalizeNoticeSettings,
  openCourse, courseCoverStyle, courseCoverText, handleCourseMenu, courseHomeError, isLessonOpening, openLesson, isOpeningLesson,
  openQuizSelection, previewMaterial, downloadMaterial, globalQuestion, askGlobal,
  classroomOpen, classroomLesson, currentPage, pageDirection, studySeconds, completeOpen, settingsOpen, thumbOpen,
  lessonSelectionMenu, pendingSourcePageNumber, pendingSourcePageId, jumpPage, prevPage, nextPage, saveProgress,
  hideLessonSelectionMenu, closeClassroom, returnCourse, nextLessonAfterComplete, resolveSourcePageNumber,
  copyText, feedbackQaMessage, toggleThought, qaRecordsToMessages,
});

onMounted(async () => {
  document.addEventListener("pointerdown", onStudentDocumentPointerDown);
  window.addEventListener("keydown", onStudentDocumentKeydown, { capture: true });
  document.addEventListener("visibilitychange", onStudentVisibilityChange);
  window.addEventListener("focus", onStudentWindowFocus);
  window.addEventListener("resize", updateTopNavIndicator);
  window.addEventListener("resize", scheduleQaLatestButtonCheck);
  window.addEventListener("scroll", scheduleQaLatestButtonCheck, { passive: true });
  // 课堂划词/全屏/幻灯尺寸监听（selectionchange、fullscreenchange、resize→compact、ResizeObserver）
  // 已移入 StudentLessonStudy 组件，仅课堂挂载时存在。
  if (active.value === "studentLessonStudy") {
    await loadActive();
    await loadCourses();
  } else {
    await loadCourses();
    await loadActive();
    await maybeOpenQuizFromQuery();
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
  document.removeEventListener("visibilitychange", onStudentVisibilityChange);
  window.removeEventListener("focus", onStudentWindowFocus);
  window.removeEventListener("resize", updateTopNavIndicator);
  window.removeEventListener("resize", scheduleQaLatestButtonCheck);
  window.removeEventListener("scroll", scheduleQaLatestButtonCheck);
  if (topNavIndicatorFrame) window.cancelAnimationFrame(topNavIndicatorFrame);
  if (qaScrollFrame) window.cancelAnimationFrame(qaScrollFrame);
  stopStudyClock();
  if (joinTimer) clearTimeout(joinTimer);
  if (notificationTimer) clearInterval(notificationTimer);
  if (pageTransitionTimer) clearTimeout(pageTransitionTimer);
});
</script>