<template>
  <PageLoader v-if="initialPageLoading" />
  <section v-else class="teacher-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'page-loading': pageLoading }">
    <header class="teacher-header">
      <div class="brand">
        <span class="logo-mark"><Sparkles :size="17" /></span>
        <strong>课程学习助手</strong>
        <i></i>
        <div ref="courseSwitchRef" class="course-switch">
          <button type="button" :class="{ active: courseMenuOpen }" aria-haspopup="menu" :aria-expanded="courseMenuOpen" @click.stop="toggleCourseMenu">
            <span>{{ currentCourse?.name || '选择课程' }}</span>
            <ChevronDown :size="16" />
          </button>
          <Transition name="top-menu">
            <div v-if="courseMenuOpen" class="course-popover top-menu-panel" role="menu">
              <button v-for="course in courses.slice(0, 8)" :key="course.id" type="button" role="menuitem" :class="{ active: currentCourseId === course.id }" @click="selectCourse(course.id)">
                <Check v-if="currentCourseId === course.id" :size="15" />{{ course.name }}
              </button>
              <button type="button" role="menuitem" @click="newCourse"><Plus :size="15" />创建课程</button>
            </div>
          </Transition>
        </div>
      </div>
      <div class="header-actions">
        <div ref="teacherNoticeRef" class="teacher-notice-menu">
          <button type="button" class="icon-btn" :class="{ active: teacherNoticeOpen }" aria-label="通知" @click.stop="openNotifications"><Bell :size="20" /><span>通知</span><em v-if="topNoticeCount">{{ topNoticeCount }}</em></button>
          <Transition name="top-menu">
            <div v-if="teacherNoticeOpen" class="teacher-notice-popover top-menu-panel">
              <header class="teacher-notice-head">
                <strong>通知</strong>
                <button v-if="topNoticeCount" type="button" :data-loading="notificationReading" :disabled="notificationReading" @click="markTeacherNotificationsRead()">全部已读</button>
              </header>
              <div v-for="item in teacherNotifications" :key="item.id || `${item.type}-${item.title}`" class="teacher-notice-item" :class="{ unread: item.unread }">
                <button type="button" class="teacher-notice-main" @click="openTeacherNotification(item)">
                  <Bell :size="15" />
                  <span><strong>{{ item.title }}</strong><small v-if="item.message">{{ item.message }}</small><em>{{ item.course_name ? `${item.course_name} · ` : '' }}{{ relativeTime(item.time) }}</em></span>
                </button>
                <button v-if="item.unread" type="button" class="notice-read-btn" :data-loading="notificationReading" :disabled="notificationReading" @click.stop="markTeacherNotificationsRead(item)">已读</button>
                <i v-if="item.unread"></i>
              </div>
              <div v-if="!teacherNotifications.length && todoCount" class="teacher-notice-empty"><Clock :size="16" />有 {{ todoCount }} 条待办事项</div>
              <EmptyState v-if="!teacherNotifications.length && !todoCount" text="暂无通知" />
            </div>
          </Transition>
        </div>
        <ThemeToggle class="header-theme-toggle" />
        <button type="button" class="icon-btn" aria-label="帮助" @click="openHelp"><HelpCircle :size="20" /><span>帮助</span></button>
        <i></i>
        <div ref="userMenuRef" class="user-menu">
          <button type="button" aria-haspopup="menu" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen"><span class="avatar" :class="{ 'has-image': teacherAvatarUrl }"><img v-if="teacherAvatarUrl" :src="teacherAvatarUrl" alt="" /><template v-else>{{ firstChar(teacherName) }}</template></span><b>{{ teacherName }}</b><ChevronDown :size="16" /></button>
          <Transition name="top-menu">
            <div v-if="userMenuOpen" class="user-popover top-menu-panel" role="menu">
              <button type="button" role="menuitem" @click="go('teacherProfile')"><User :size="15" />个人中心</button>
              <button type="button" role="menuitem" @click="go('teacherProfile')"><Settings :size="15" />账号设置</button>
              <button type="button" role="menuitem" @click="$emit('logout')"><LogOut :size="15" />退出登录</button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <aside class="teacher-sidebar">
      <button
        type="button"
        class="teacher-sidebar-toggle"
        :aria-label="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
        :title="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <ChevronRight v-if="sidebarCollapsed" :size="17" />
        <ChevronLeft v-else :size="17" />
        <span>{{ sidebarCollapsed ? '展开' : '收起' }}</span>
      </button>
      <nav>
        <div class="nav-group">
          <span>全局</span>
          <button :class="{ active: active === 'teacherDashboard' }" @click="go('teacherDashboard')"><LayoutDashboard :size="16" />工作台首页</button>
        </div>
        <div class="nav-group">
          <span>我的课程</span>
          <button :class="{ active: active === 'teacherCourses' }" @click="go('teacherCourses')"><BookOpen :size="16" />课程列表</button>
          <button :class="{ active: active === 'teacherCourseForm' }" @click="newCourse"><PlusCircle :size="16" />创建课程</button>
        </div>
        <div class="nav-group">
          <span class="course-title" @click="currentCourseId && go('teacherCourseHome')">{{ currentCourse ? shortName(currentCourse.name) : '请先选择或创建课程' }}<ChevronRight v-if="currentCourse" :size="13" /></span>
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherCourseHome' }" @click="go('teacherCourseHome')"><Home :size="16" />课程主页</button>
          <button :disabled="!currentCourseOperable" :class="{ active: active === 'teacherMaterials' || active === 'teacherPpt' }" @click="go('teacherMaterials')"><FolderOpen :size="16" />资料管理</button>
          <button :disabled="!currentCourseOperable" :class="{ active: active === 'teacherLessons' }" @click="go('teacherLessons')"><Presentation :size="16" />课时管理</button>
          <button :disabled="!currentCourseOperable" :class="{ active: active === 'teacherStudents' }" @click="go('teacherStudents')"><Users :size="16" />学生管理</button>
          <button :disabled="!currentCourseOperable" :class="{ active: active === 'teacherAnalytics' }" @click="go('teacherAnalytics')"><BarChart2 :size="16" />教学分析</button>
          <button :disabled="!currentCourseOperable" :class="{ active: active === 'teacherWeakQuizzes' }" @click="go('teacherWeakQuizzes')"><AlertTriangle :size="16" />薄弱题目</button>
        </div>
        <div class="nav-group">
          <span>个人</span>
          <button :class="{ active: active === 'teacherProfile' }" @click="go('teacherProfile')"><User :size="16" />个人中心</button>
        </div>
      </nav>
    </aside>

    <main class="teacher-main" :class="{ immersive: active === 'teacherPpt' }">
      <div v-if="active !== 'teacherPpt'" class="breadcrumb">
        <div><Home :size="15" /><span>工作台</span><ChevronRight :size="14" /><strong>{{ pageTitle }}</strong></div>
        <section class="page-actions">
          <button v-if="active === 'teacherDashboard'" class="btn btn-secondary" @click="enterRecentCourse"><Presentation :size="16" />最近课程</button>
          <button v-if="active === 'teacherCourses'" class="btn btn-primary" @click="newCourse"><Plus :size="16" />创建课程</button>
          <button v-if="active === 'teacherCourseForm'" class="btn btn-primary" :data-loading="isPending('save-course')" :disabled="isPending('save-course')" @click="saveCourse">{{ courseForm.id ? '保存修改' : '创建课程' }}</button>
          <button v-if="active === 'teacherMaterials'" class="btn btn-primary" :disabled="!currentCourseOperable" @click="openUploadModal"><Upload :size="16" />上传资料</button>
          <button v-if="active === 'teacherLessons'" class="btn btn-primary" :disabled="!currentCourseOperable" @click="go('teacherMaterials')"><Plus :size="16" />从资料创建</button>
          <button v-if="active === 'teacherStudents'" class="btn btn-ghost" :data-loading="isPending('export-teacherStudents')" :disabled="isPending('export-teacherStudents') || !currentCourseOperable" @click="exportCurrent"><Download :size="16" />导出学生</button>
          <div v-if="active === 'teacherAnalytics'" class="segmented-control">
            <button v-for="item in analysisRangeOptions" :key="item" type="button" class="segment-btn" :class="{ active: analysisRange === item }" :data-loading="isPending('analysis-range') && analysisRange === item" :disabled="isPending('analysis-range') || !currentCourseOperable" @click="setAnalysisRange(item)">{{ item }}</button>
          </div>
          <button v-if="active === 'teacherAnalytics'" class="btn btn-ghost" :data-loading="isPending('export-teacherAnalytics')" :disabled="isPending('export-teacherAnalytics') || !currentCourseOperable" @click="exportCurrent"><Download :size="16" />导出报告</button>
        </section>
      </div>
      <TransitionGroup name="page-switch" tag="div" class="teacher-page-stack">
      <section v-if="active === 'teacherDashboard'" key="teacherDashboard" class="teacher-content">
        <article class="welcome">
          <i class="welcome-glow" aria-hidden="true"></i>
          <i class="welcome-scribble" aria-hidden="true"></i>
          <i class="welcome-tray" aria-hidden="true"></i>
          <div><Sparkles :size="24" /><section><h1>{{ greeting }}，{{ teacherName }}老师</h1><p>{{ todayText }} · {{ focusCount }} 门课程</p></section></div>
          <button class="btn white-btn" @click="enterRecentCourse"><Presentation :size="16" />最近课程</button>
        </article>
        <div class="metric-grid four">
          <MetricCard :icon="BookOpen" label="我的课程" :value="`${dashboard.stats?.active_course_total || 0}/${dashboard.stats?.course_total || 0}`" sub="本学期" />
          <MetricCard :icon="Users" label="学生总数" :value="dashboard.stats?.student_total || 0" sub="全部课程" tone="success" />
          <MetricCard :icon="MessageCircle" label="本周提问" :value="dashboard.stats?.weekly_qa || 0" sub="AI 问答" tone="warning" />
          <MetricCard :icon="Clock" label="待处理" :value="dashboard.stats?.pending_scripts || 0" sub="脚本页" :danger="(dashboard.stats?.pending_scripts || 0) > 0" />
        </div>
        <div class="dash-mid">
          <article class="panel-card">
            <div class="panel-head"><h2><BookOpen :size="18" />我的课程</h2><button class="link-btn" @click="go('teacherCourses')">查看全部</button></div>
            <TransitionGroup name="motion-list" tag="div" class="recent-course-list">
              <div v-for="course in dashboard.recent_courses || []" :key="course.id" class="recent-course">
                <span class="cover"><BookOpen :size="20" /></span>
                <div><strong>{{ course.name }}</strong><small>{{ course.term }} · {{ course.student_count || 0 }}人</small><AppProgress :value="course.published_rate || 0" /></div>
                <button class="btn btn-ghost btn-sm" :data-loading="isPending(`select-course-${course.id}`)" :disabled="isPending(`select-course-${course.id}`)" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button>
              </div>
            </TransitionGroup>
            <button class="dashed-btn" @click="newCourse"><Plus :size="16" />创建新课程</button>
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><ClipboardList :size="18" />待办事项</h2><span class="badge">{{ todoCount }}</span></div>
            <TransitionGroup name="motion-list" tag="div" class="todo-list">
              <div v-for="todo in dashboard.todos || []" :key="`${todo.type}-${todo.title}`" class="todo-row">
                <i :class="todo.type"></i><component :is="todoIcon(todo.type)" :size="16" /><div><strong>{{ todo.title }}</strong><small>{{ formatTime(todo.created_at) }}</small></div><button class="link-btn" :data-loading="isPending(`select-course-${todo.course_id}`)" :disabled="isPending(`select-course-${todo.course_id}`)" @click="selectCourse(todo.course_id, 'teacherLessons')">处理</button>
              </div>
            </TransitionGroup>
            <EmptyState v-if="!(dashboard.todos || []).length" text="暂无待办" />
          </article>
        </div>
        <div class="bottom-grid">
          <article class="panel-card">
            <div class="panel-head"><h2><Activity :size="18" />本周学生动态</h2></div>
            <div class="heatmap">
              <div class="heat-head"><span></span><b v-for="day in weekdays" :key="day">{{ day }}</b></div>
              <TransitionGroup name="motion-list" tag="div" class="heat-body">
                <div v-for="row in dashboard.weekly_activity || []" :key="row.course_id" class="heat-row">
                  <span>{{ shortName(row.course_name) }}</span><i v-for="item in row.days" :key="item.day" :style="{ opacity: heatOpacity(item.count) }"></i>
                </div>
              </TransitionGroup>
            </div>
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><FileEdit :size="18" />待审核脚本</h2><span class="tag tag-warning">{{ (dashboard.pending_scripts || []).length }}</span></div>
            <TransitionGroup name="motion-list" tag="div" class="script-list">
              <div v-for="item in dashboard.pending_scripts || []" :key="item.page_id" class="script-row"><Presentation :size="16" /><div><strong>{{ item.lesson_title }}</strong><small>第{{ item.page_number }}页</small></div><button class="link-btn" @click="openPptFromLesson(item.lesson_id)">审核</button></div>
            </TransitionGroup>
            <EmptyState v-if="!(dashboard.pending_scripts || []).length" text="脚本已完成" success />
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><Sparkles :size="18" />AI 任务</h2><small>30秒</small></div>
            <TaskList :items="dashboard.ai_tasks || []" @retry="retryTask" />
          </article>
        </div>
      </section>

      <section v-if="active === 'teacherCourses'" key="teacherCourses" class="teacher-content">
        <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="courseFilter.keyword" placeholder="搜索课程名称" /></div><AppSelect v-model="courseFilter.term" :options="courseTermOptions" /><AppSelect v-model="courseFilter.status" :options="courseStatusOptions" /><span></span><div class="view-toggle"><button type="button" :class="{ active: courseView === 'grid' }" @click="courseView = 'grid'"><Grid2X2 :size="16" />网格</button><button type="button" :class="{ active: courseView === 'list' }" @click="courseView = 'list'"><FileText :size="16" />列表</button></div></article>
        <Transition name="fade-slide" mode="out-in">
          <TransitionGroup v-if="courseView === 'grid'" key="grid" name="card-list" tag="div" class="course-grid">
            <article v-for="course in filteredCourses" :key="course.id" class="course-card" :class="{ inactive: course.status !== 'active' }">
              <div class="course-cover" :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)"><span class="tag">{{ course.term }}</span><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span><strong v-if="!course.cover_url" class="course-cover-title">{{ courseCoverText(course) }}</strong></div>
              <section><h2>{{ course.name }}</h2><code>{{ course.course_code }}</code><div class="course-stats"><span><Users :size="15" />{{ course.student_count || 0 }}</span><span><Presentation :size="15" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</span><span><File :size="15" />{{ course.material_count || 0 }}</span><span><Check :size="15" />{{ course.published_rate || 0 }}%</span></div></section>
              <footer><button class="btn btn-primary btn-sm" :data-loading="isPending(`select-course-${course.id}`)" :disabled="isPending(`select-course-${course.id}`)" @click="selectCourse(course.id, 'teacherCourseHome')">{{ isCourseOperable(course) ? '进入课程' : '查看状态' }}</button><button v-if="isCourseOperable(course)" class="icon-action" :data-loading="isPending(`edit-course-${course.id}`)" :disabled="isPending(`edit-course-${course.id}`)" @click="editCourse(course)"><Pencil :size="15" />编辑</button><button class="icon-action course-status-action" :class="{ danger: isCourseOperable(course) }" :data-loading="isPending(`toggle-course-${course.id}`)" :disabled="isPending(`toggle-course-${course.id}`)" @click="toggleCourseStatus(course)"><Check v-if="!isCourseOperable(course)" :size="15" /><Ban v-else :size="15" />{{ isCourseOperable(course) ? '下架' : '上架' }}</button></footer>
            </article>
          </TransitionGroup>
          <article v-else key="list" class="table-card"><table class="teacher-table"><thead><tr><th>课程名称</th><th>学期</th><th>学生数</th><th>课时数</th><th>资料数</th><th>状态</th><th>最近更新</th><th>操作</th></tr></thead><TransitionGroup name="row-list" tag="tbody"><tr v-for="course in filteredCourses" :key="course.id"><td><span class="mini-cover" :class="{ 'has-image': course.cover_url }" :style="courseCoverStyle(course)">{{ course.cover_url ? '' : courseCoverText(course).slice(0, 2) }}</span><strong>{{ course.name }}</strong><code>{{ course.course_code }}</code></td><td>{{ course.term }}</td><td><Users :size="14" />{{ course.student_count || 0 }}</td><td><Presentation :size="14" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</td><td><File :size="14" />{{ course.material_count || 0 }}</td><td><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span></td><td>{{ relativeTime(course.updated_at) }}</td><td><button class="btn btn-primary btn-sm" :data-loading="isPending(`select-course-${course.id}`)" :disabled="isPending(`select-course-${course.id}`)" @click="selectCourse(course.id, 'teacherCourseHome')">{{ isCourseOperable(course) ? '进入课程' : '查看状态' }}</button><button v-if="isCourseOperable(course)" class="icon-action" :data-loading="isPending(`edit-course-${course.id}`)" :disabled="isPending(`edit-course-${course.id}`)" @click="editCourse(course)"><Pencil :size="15" />编辑</button><button class="icon-action course-status-action" :class="{ danger: isCourseOperable(course) }" :data-loading="isPending(`toggle-course-${course.id}`)" :disabled="isPending(`toggle-course-${course.id}`)" @click="toggleCourseStatus(course)"><Check v-if="!isCourseOperable(course)" :size="15" /><Ban v-else :size="15" />{{ isCourseOperable(course) ? '下架' : '上架' }}</button></td></tr></TransitionGroup></table></article>
        </Transition>
        <EmptyState v-if="!filteredCourses.length" text="还没有课程"><button class="btn btn-primary" @click="newCourse"><Plus :size="16" />创建课程</button></EmptyState>
      </section>

      <section v-if="active === 'teacherCourseForm'" key="teacherCourseForm" class="teacher-content form-content">
        <section class="course-form-layout">
          <article class="panel-card form-panel">
            <div class="form-section"><h2>基本信息</h2><label>课程名称<input v-model="courseForm.name" class="input" maxlength="50" /></label><label>课程简介<textarea v-model="courseForm.description" class="textarea" maxlength="500"></textarea><small>{{ courseForm.description.length }} / 500</small></label><label>学期<input v-model="courseForm.term" class="input" /></label><label>课程封面<div class="cover-upload-field"><div class="cover-upload-preview" :style="courseCoverPreviewStyle()"><strong v-if="!(courseCoverPreview || courseForm.cover_url)" class="course-cover-title">{{ courseCoverText(courseForm) }}</strong></div><div class="cover-upload-actions"><button type="button" class="btn btn-secondary btn-sm" @click="courseCoverInput?.click()"><Upload :size="14" />上传图片</button><button v-if="courseCoverPreview || courseForm.cover_url" type="button" class="btn btn-ghost btn-sm" @click="courseForm.cover_url = ''; resetCourseCoverSelection()">清除</button><small>{{ courseCoverFile?.name || '未上传图片时显示课程名前四字和底色' }}</small><input ref="courseCoverInput" type="file" accept="image/*" hidden @change="pickCourseCover" /></div></div></label><label>封面底色<div class="color-row"><button v-for="color in palette" :key="color" type="button" :style="{ background: color }" :class="{ active: courseForm.cover_color === color }" @click="courseForm.cover_color = color"></button></div></label></div>
            <div class="form-section"><h2>AI 设置</h2><AppCheckbox v-model="courseForm.allow_general_ai_answer" variant="switch" label="允许资料外回答" /><small>开启后，学生在 QA、课件页问答和题目辅导中，即使课程资料未覆盖，AI 也会继续回答，但会明确提示该回答没有课程资料依据。</small></div>
            <div class="form-section"><div class="section-head"><h2><Layers :size="18" />课程章节</h2><button class="btn btn-ghost btn-sm" :disabled="courseForm.chapters.length >= 30" @click="addDraftChapter"><Plus :size="14" />添加章节</button></div><TransitionGroup name="chapter-list" tag="div" class="chapter-edit-list"><div v-for="(chapter, index) in courseForm.chapters" :key="chapter.local_id" class="chapter-edit" :class="{ 'just-added': freshChapterId === chapter.local_id }"><GripVertical :size="15" /><input v-model="chapter.title" class="input" /><input v-model.number="chapter.order_index" class="input order-input" type="number" /><button class="icon-action danger" :disabled="courseForm.chapters.length <= 1" @click="removeDraftChapter(index)"><Trash2 :size="15" />删除</button></div></TransitionGroup></div>
            <div class="advanced" :class="{ open: advancedOpen }"><button type="button" class="advanced-trigger" @click="advancedOpen = !advancedOpen"><Settings :size="16" />高级设置<ChevronDown :size="14" /></button><Transition name="accordion"><div v-if="advancedOpen" class="advanced-body"><AppCheckbox v-model="courseForm.allow_leave" label="学生退出" /><AppCheckbox v-model="courseForm.ai_qa" label="AI 问答" /><AppCheckbox v-model="courseForm.quiz_enabled" label="测验发布" /></div></Transition></div>
          </article>
          <aside class="course-preview-panel">
            <div class="panel-head"><h2><Eye :size="18" />卡片预览</h2><small>学生端展示</small></div>
            <article class="course-preview-frame">
              <div class="course-preview-cover" :class="{ 'has-image': courseCoverPreview || courseForm.cover_url }" :style="courseCoverPreviewStyle()">
                <strong v-if="!(courseCoverPreview || courseForm.cover_url)" class="course-cover-title">{{ courseCoverText(courseForm) }}</strong>
                <span>{{ courseForm.term || '2026春' }}</span>
              </div>
              <section class="course-preview-body">
                <h3>{{ courseForm.name || '课程名称' }}</h3>
                <p>{{ courseForm.description || '课程简介会显示在课程卡片中。' }}</p>
                <div class="course-preview-meta">
                  <code>{{ courseForm.id ? currentCourse?.course_code : 'A8K3Z' }}</code>
                  <span><Layers :size="14" />{{ courseForm.chapters.length }} 章</span>
                  <span><Users :size="14" />0 人</span>
                </div>
              </section>
            </article>
          </aside>
        </section>
        <div class="fixed-actions"><span><Edit2 :size="15" />有未保存的更改</span><div><button class="btn btn-ghost" @click="go('teacherCourses')">取消</button><button v-if="courseForm.id" class="btn btn-danger" :data-loading="isPending('delete-course')" :disabled="isPending('delete-course')" @click="deleteCourse">删除课程</button><button class="btn btn-secondary" :data-loading="isPending('save-course')" :disabled="isPending('save-course')" @click="saveCourse">保存草稿</button><button class="btn btn-primary" :data-loading="isPending('save-course')" :disabled="isPending('save-course')" @click="saveCourse">{{ courseForm.id ? '保存修改' : '创建课程' }}</button></div></div>
      </section>

      <section v-if="active === 'teacherCourseHome'" key="teacherCourseHome" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="course-hero" :class="{ 'has-image': currentCourse.cover_url }" :style="courseHeroStyle(currentCourse)"><span><BookOpen v-if="currentCourse.cover_url" :size="36" /><strong v-else class="course-hero-cover-title">{{ courseCoverText(currentCourse) }}</strong></span><div><h1>{{ courseHome.course?.name || currentCourse.name }}</h1><p>{{ currentCourse.term }} · {{ currentCourse.course_code }} <span class="tag" :class="statusClass(currentCourse.status)">{{ statusText(currentCourse.status) }}</span></p><small><Users :size="15" />{{ courseHome.quick_counts?.student_count || 0 }} 学生 <Presentation :size="15" />{{ courseHome.quick_counts?.lesson_count || 0 }} 课时 <File :size="15" />{{ courseHome.quick_counts?.material_count || 0 }} 资料</small></div><section><button v-if="currentCourseOperable" class="btn ghost-white" @click="editCourse(currentCourse)"><Pencil :size="16" />编辑课程</button><button v-if="currentCourseOperable" class="btn ghost-white" @click="copyText(currentCourse.course_code)"><Share2 :size="16" />分享课程码</button><button class="btn ghost-white" :class="{ danger: currentCourseOperable }" :data-loading="isPending(`toggle-course-${currentCourse.id}`)" :disabled="isPending(`toggle-course-${currentCourse.id}`)" @click="toggleCourseStatus(currentCourse)"><Check v-if="!currentCourseOperable" :size="16" /><Ban v-else :size="16" />{{ currentCourseOperable ? '下架课程' : '上架课程' }}</button></section></article>
          <article v-if="!currentCourseOperable" class="course-inactive-banner"><AlertTriangle :size="20" /><div><strong>课程已下架</strong><span>已加入学生可继续学习，新学生不能加入；教师需上架后才能继续管理课程。</span></div></article>
          <div v-if="currentCourseOperable" class="quick-grid"><QuickAction :icon="Upload" label="上传资料" sub="PPT/PDF/Word/TXT" @click="go('teacherMaterials')" /><QuickAction :icon="Presentation" label="管理课时" sub="课时发布" @click="go('teacherLessons')" /><QuickAction :icon="UserPlus" label="邀请学生" sub="课程码" @click="copyText(currentCourse.course_code)" /><QuickAction :icon="BarChart2" label="教学分析" sub="课程数据" @click="go('teacherAnalytics')" /></div>
          <div class="course-home-grid">
            <article class="panel-card home-lesson-card">
              <div class="panel-head rich-head">
                <div><h2><Presentation :size="18" />课时列表</h2><small>{{ courseHome.quick_counts?.lesson_count || 0 }} 个课时 · 点击可进入脚本工作台</small></div>
                <button class="btn btn-ghost btn-sm" :disabled="!currentCourseOperable" @click="go('teacherLessons')"><Presentation :size="14" />管理课时</button>
              </div>
              <LessonRows :items="courseHome.lessons || []" :student-total="courseHome.quick_counts?.student_count || 0" :chapters="courseHome.chapters || []" :disabled="!currentCourseOperable" @open="openLessonScript" />
              <button class="btn btn-primary btn-sm full home-card-action" :disabled="!currentCourseOperable" @click="go('teacherMaterials')"><Plus :size="14" />从资料生成课时</button>
            </article>
            <article class="panel-card material-overview-card">
              <div class="panel-head rich-head">
                <div><h2><FolderOpen :size="18" />资料状态</h2><small>{{ materialReadyCount }}/{{ materialTotal }} 份资料已完成解析</small></div>
                <button class="btn btn-ghost btn-sm" :disabled="!currentCourseOperable" @click="go('teacherMaterials')"><Upload :size="14" />资料管理</button>
              </div>
              <section class="material-health">
                <div><strong>{{ materialReadyPercent }}%</strong><span>解析完成率</span></div>
                <AppProgress :value="materialReadyPercent" :tone="materialProgressTone" />
              </section>
              <div class="material-status-grid">
                <button v-for="item in materialStatusCards" :key="item.key" :class="['material-status-tile', item.tone]" :disabled="!currentCourseOperable" @click="go('teacherMaterials')">
                  <component :is="item.icon" :size="17" />
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </button>
              </div>
              <MaterialTypeList :stats="courseHome.material_stats?.by_type || {}" />
              <button class="btn btn-secondary btn-sm full home-card-action" :disabled="!currentCourseOperable" @click="go('teacherMaterials')"><Upload :size="14" />上传课程资料</button>
            </article>
            <article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />近期活动</h2></div><ActivityList :items="courseHome.activities || []" /></article>
          </div>
          <div class="course-bottom-grid"><article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生学习进度</h2><button class="link-btn" :disabled="!currentCourseOperable" @click="go('teacherStudents')">查看详情</button></div><ProgressList :items="courseHome.student_progress || []" /></article><article class="panel-card"><div class="panel-head"><h2><Sparkles :size="18" />AI 任务队列</h2><span class="tag">{{ (courseHome.ai_tasks || []).length }}</span></div><TaskList :items="courseHome.ai_tasks || []" @retry="retryTask" /></article></div>
        </template>
      </section>

      <section v-if="active === 'teacherMaterials'" key="teacherMaterials" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid three compact"><MetricCard :icon="File" label="资料总数" :value="materialSummary.total || 0" sub="份" /><MetricCard :icon="Database" label="存储用量" :value="sizeLabel(materialSummary.size_bytes)" sub="课程资料" tone="success" /><MetricCard :icon="Sparkles" label="已解析" :value="`${materialSummary.ready || 0}/${materialSummary.total || 0}`" sub="AI" tone="ai" /></div>
          <div class="materials-layout"><aside class="chapter-tree"><div class="search-box small"><Search :size="15" /><input v-model="chapterKeyword" placeholder="搜索章节" /></div><button class="chapter-tree-main" :class="{ active: selectedChapterId === 0 }" @click="selectedChapterId = 0"><FileText :size="16" /><span class="chapter-tree-title">全部资料</span><span class="chapter-tree-count">{{ materialSummary.total || 0 }}</span></button><TransitionGroup name="motion-list" tag="div" class="chapter-buttons"><div v-for="chapter in filteredChapters" :key="chapter.id" class="chapter-tree-row" :class="{ active: selectedChapterId === chapter.id, 'is-empty': !chapter.count, 'just-added': freshMaterialChapterId === chapter.id }"><button class="chapter-tree-main" @click="selectedChapterId = chapter.id"><Layers :size="16" /><span class="chapter-tree-title">{{ chapter.title }}</span><span class="chapter-tree-count">{{ chapter.count || 0 }}</span></button><button class="chapter-tree-delete" :data-loading="isPending(`delete-chapter-${chapter.id}`)" :disabled="isPending(`delete-chapter-${chapter.id}`)" title="删除章节" @click="deleteChapterFromTree(chapter)"><Trash2 :size="14" /></button></div></TransitionGroup><button :data-loading="isPending('add-tree-chapter')" :disabled="isPending('add-tree-chapter')" @click="openAddChapterModal"><Plus :size="16" /><span class="chapter-tree-title">添加章节</span></button></aside><section class="materials-panel" :class="{ 'panel-loading': isPending('filter-materials') }"><div class="material-filter"><div class="search-box"><Search :size="16" /><input v-model="materialFilter.keyword" placeholder="搜索文件名" @keyup.enter="refreshMaterials" /></div><AppSelect v-model="materialFilter.type" :options="materialTypeOptions" /><AppSelect v-model="materialFilter.status" :options="materialStatusOptions" /><AppSelect v-model="materialSort" :options="materialSortOptions" /><div class="view-toggle"><button type="button" :class="{ active: materialView === 'grid' }" @click="materialView = 'grid'"><Grid2X2 :size="16" />网格</button><button type="button" :class="{ active: materialView === 'list' }" @click="materialView = 'list'"><FileText :size="16" />列表</button></div></div><TransitionGroup name="material-list-motion" tag="div" class="material-list" :class="materialView"><article v-for="item in filteredMaterials" :key="item.id" class="material-row" :class="{ processing: isMaterialProcessing(item) }"><span class="file-badge" :class="item.material_type"><component :is="fileIcon(item.material_type)" :size="18" /></span><div><strong>{{ item.title }}</strong><small>{{ chapterName(item.chapter_id) }} · {{ typeText(item.material_type) }} · {{ sizeLabel(item.size_bytes) }}</small><MaterialStatus :item="item" /></div><span class="tag" :class="statusClass(materialRowStatus(item))">{{ statusText(materialRowStatus(item)) }}</span><section><button class="icon-action" @click="previewMaterial(item)"><Eye :size="15" />预览</button><button class="icon-action" :data-loading="isPending(`reprocess-material-${item.id}`) || isMaterialRetryBlocked(item)" :disabled="isPending(`reprocess-material-${item.id}`) || isMaterialRetryBlocked(item)" @click="reprocessMaterial(item.id)"><RefreshCw :size="15" />{{ materialRetryActionText(item) }}</button><button v-if="materialRowStatus(item) === 'ready'" class="icon-action" :data-loading="isPending(`open-ppt-${item.id}`)" :disabled="isPending(`open-ppt-${item.id}`) || isMaterialProcessing(item)" @click="openPptWorkbench(item.id)"><Wand2 :size="15" />编辑课时</button><button class="icon-action" @click="downloadMaterial(item)"><Download :size="15" />下载</button><button class="icon-action danger" :data-loading="isPending(`delete-material-${item.id}`)" :disabled="isPending(`delete-material-${item.id}`)" @click="deleteMaterial(item.id)"><Trash2 :size="15" />删除</button></section></article><EmptyState v-if="!filteredMaterials.length" key="empty" text="暂无资料" /></TransitionGroup></section></div>
        </template>
      </section>

      <section v-if="active === 'teacherPpt'" key="teacherPpt" class="ppt-workbench" :class="{ 'presentation-mode': presentationMode }">
        <header class="ppt-head"><button class="btn btn-ghost" @click="go(workbenchMode === 'lesson' ? 'teacherLessons' : 'teacherMaterials')"><ArrowLeft :size="16" />{{ workbenchMode === 'lesson' ? '返回课时管理' : '返回资料管理' }}</button><strong>{{ materialDetail?.material?.title || 'PPT 工作台' }}</strong></header>
        <template v-if="pages.length">
          <aside class="thumb-column"><div class="thumb-top"><strong>{{ materialDetail?.material?.title || '-' }}</strong><small>{{ reviewedCount }}/{{ pages.length }} 页已审核</small><AppProgress :value="reviewedCount" :max="Math.max(pages.length, 1)" tone="success" /><AppCheckbox :model-value="false" label="全选审核" @update:model-value="markAllReviewed" /><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent"><RefreshCw :size="14" />批量重新生成</button></div><TransitionGroup name="thumb-list" tag="div" class="thumb-list"><button v-for="page in pages" :key="page.id" class="thumb-card" :class="{ active: currentPageId === page.id }" @click="currentPageId = page.id"><span>{{ page.page_number }}</span><div>{{ page.page_title || `第${page.page_number}页` }}</div><CheckCircle v-if="page.script_status === 'ready'" :size="16" /><Clock v-else :size="16" /><small>{{ page.script_text?.slice(0, 20) }}</small></button></TransitionGroup></aside>
          <main class="ppt-stage" :class="{ focused: stageFocused }"><div class="stage-top"><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" />上一页</button>第 {{ currentPageIndex + 1 }} / {{ pages.length }} 页<button class="icon-action" @click="nextPage"><ChevronRight :size="18" />下一页</button><button class="icon-action" @click="zoomSlide"><ZoomIn :size="18" />放大</button><button class="icon-action" :class="{ active: stageFocused }" @click="toggleStageFocus"><Maximize :size="18" />专注</button></div><div class="slide-preview-wrap" :class="{ focused: stageFocused }" :style="{ '--slide-scale': slideScale }"><Transition name="slide-flip" mode="out-in"><article :key="activePage?.id || 0" class="slide-preview"><h2>{{ activePage?.page_title || `第${currentPageIndex + 1}页` }}</h2><div class="slide-content teacher-markdown markdown-body" v-html="activePageHtml"></div></article></Transition></div><Transition name="fade-slide"><div v-if="slideOverviewOpen" class="slide-overview"><TransitionGroup name="thumb-list" tag="div" class="slide-overview-grid"><button v-for="page in pages" :key="page.id" :class="{ active: currentPageId === page.id }" @click="jumpToPage(page.id)"><span>{{ page.page_number }}</span><strong>{{ page.page_title || `第${page.page_number}页` }}</strong><small>{{ page.script_status === 'ready' ? '已审核' : '待处理' }}</small></button></TransitionGroup></div></Transition><div class="stage-controls"><button class="icon-action" @click="firstPage"><SkipBack :size="18" />首页</button><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" />上一页</button><button class="icon-action" @click="nextPage"><ChevronRight :size="18" />下一页</button><button class="icon-action" @click="lastPage"><SkipForward :size="18" />末页</button><button class="icon-action" :class="{ active: slideOverviewOpen }" @click="toggleSlideOverview"><Grid2X2 :size="18" />缩略图</button><button class="icon-action" :class="{ active: presentationMode }" @click="togglePresentationMode"><Presentation :size="18" />演示</button></div></main>
          <aside class="script-panel"><div class="script-head"><h2><FileEdit :size="18" />第 {{ activePage?.page_number || 1 }} 页</h2><span class="tag" :class="statusClass(activePage?.script_status)">{{ statusText(activePage?.script_status) }}</span></div><div class="ai-strip" :class="{ thinking: activePage && isPending(`regen-page-${activePage.id}`) }"><Sparkles :size="14" />AI 生成<button :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent">重新生成</button></div><div class="editor-toolbar"><button :class="{ active: editorPulse === 'bold' }" @click="formatScript('bold')">B</button><button :class="{ active: editorPulse === 'italic' }" @click="formatScript('italic')">I</button><button :class="{ active: editorPulse === 'paragraph' }" @click="formatScript('paragraph')">段落</button><button :class="{ active: editorPulse === 'undo' }" @click="undoScriptEdit">撤销</button><button :class="{ active: editorPulse === 'redo' }" @click="redoScriptEdit">重做</button></div><textarea ref="scriptEditor" v-model="scriptDraft" class="script-editor"></textarea><small class="word-count">{{ scriptDraft.length }} 字</small><div class="script-actions"><span><Volume2 :size="16" />{{ activePage?.audio_url ? '已合成' : '未合成' }}</span><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent">重新生成</button><button class="btn btn-primary btn-sm" :data-loading="activePage && isPending(`save-script-${activePage.id}`)" :disabled="!!activePage && isPending(`save-script-${activePage.id}`)" @click="saveScript">审核完成</button></div></aside>
          <footer class="ppt-status"><span>{{ materialDetail?.material?.title }} · 已审核 {{ reviewedCount }}/{{ pages.length }} 页 · 已保存</span><div><button class="btn btn-secondary btn-sm" :data-loading="isPending('mark-all-reviewed')" :disabled="isPending('mark-all-reviewed')" @click="markAllReviewed">批量审核</button><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`save-script-${activePage.id}`)" :disabled="!!activePage && isPending(`save-script-${activePage.id}`)" @click="synthesizeCurrent">语音合成</button><button class="btn btn-primary btn-sm" :data-loading="isPending('publish-lesson')" :disabled="isPending('publish-lesson')" @click="publishLessonFromMaterial">发布课时</button></div></footer>
        </template>
        <div v-else class="ppt-empty-state"><FileText :size="42" /><h2>暂无可编辑页面</h2><p>资料解析完成后会在这里显示课时页面和 AI 脚本。</p><button class="btn btn-primary" @click="go(workbenchMode === 'lesson' ? 'teacherLessons' : 'teacherMaterials')"><ArrowLeft :size="16" />返回列表</button></div>
      </section>

      <section v-if="active === 'teacherLessons'" key="teacherLessons" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="lessonFilter.keyword" placeholder="课时名称" /></div><AppSelect v-model="lessonFilter.chapter_id" :options="lessonChapterOptions" /><AppSelect v-model="lessonFilter.status" :options="lessonStatusOptions" /><AppSelect v-model="lessonSort" :options="lessonSortOptions" /></article>
          <TransitionGroup name="card-list" tag="div" class="lesson-card-list"><article v-for="lesson in pagedLessons" :key="lesson.id" class="lesson-card"><div class="lesson-thumb">{{ lesson.page_count || 0 }}</div><section><h2><span class="lesson-card-title">{{ lesson.title }}</span><span class="tag" :class="statusClass(lesson.status)">{{ statusText(lesson.status) }}</span></h2><p>{{ chapterName(lesson.chapter_id) }} · {{ lesson.page_count }}页 · {{ lesson.learned_count || 0 }}/{{ courseHome.quick_counts?.student_count || 0 }}人 · {{ shortDate(lesson.published_at || lesson.created_at) }}</p><AppProgress :value="lesson.average_progress || 0" :tone="Number(lesson.average_progress || 0) >= 70 ? 'success' : Number(lesson.average_progress || 0) >= 30 ? 'warning' : 'danger'" /></section><div class="lesson-actions"><button class="icon-action" :data-loading="isPending(`preview-lesson-${lesson.id}`)" :disabled="isPending(`preview-lesson-${lesson.id}`)" @click="openLessonPreview(lesson.id)"><Presentation :size="16" />预览</button><button class="icon-action" @click="openLessonScript(lesson)"><Wand2 :size="16" />脚本</button><button class="icon-action" :data-loading="isPending(`duplicate-lesson-${lesson.id}`)" :disabled="isPending(`duplicate-lesson-${lesson.id}`)" @click="duplicateLesson(lesson.id)"><Copy :size="16" />复制</button><AppCheckbox variant="switch" :label="lesson.status === 'published' ? '已发布' : '草稿'" :model-value="lesson.status === 'published'" :disabled="isPending(`toggle-lesson-${lesson.id}`)" @update:model-value="toggleLessonPublish(lesson)" /><button class="icon-action danger" :data-loading="isPending(`delete-lesson-${lesson.id}`)" :disabled="isPending(`delete-lesson-${lesson.id}`)" @click="deleteLesson(lesson.id)"><Trash2 :size="16" />删除</button></div></article><EmptyState v-if="!filteredLessons.length" key="empty" text="暂无课时" /></TransitionGroup>
          <nav v-if="lessonPageCount > 1" class="lesson-pager"><button class="btn btn-ghost btn-sm" :disabled="lessonPage <= 1" @click="lessonPage = Math.max(1, lessonPage - 1)"><ChevronLeft :size="14" />上一页</button><span class="lesson-pager-info">{{ lessonPage }} / {{ lessonPageCount }} · 共 {{ filteredLessons.length }} 个课时</span><button class="btn btn-ghost btn-sm" :disabled="lessonPage >= lessonPageCount" @click="lessonPage = Math.min(lessonPageCount, lessonPage + 1)">下一页<ChevronRight :size="14" /></button></nav>
        </template>
      </section>

      <section v-if="active === 'teacherStudents'" key="teacherStudents" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid four compact"><MetricCard :icon="Users" label="学生总数" :value="studentPayload.stats?.total || 0" sub="本周新增" /><MetricCard :icon="Activity" label="活跃学生" :value="studentPayload.stats?.active_7d || 0" sub="近7天" tone="success" /><MetricCard :icon="CheckCircle" label="完成率" :value="`${studentPayload.stats?.average_completion || 0}%`" sub="平均" tone="success" /><MetricCard :icon="UserX" label="长期未活跃" :value="studentPayload.stats?.inactive_14d || 0" sub="14天" :danger="(studentPayload.stats?.inactive_14d || 0) > 0" /></div>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="studentFilter.keyword" placeholder="搜索学生姓名" /></div><AppSelect v-model="studentFilter.progress" :options="studentProgressOptions" /><AppSelect v-model="studentFilter.active" :options="studentActiveOptions" /><button class="btn btn-ghost" @click="clearStudentFilter"><X :size="16" />清除</button><span></span><button class="btn btn-ghost" :disabled="!filteredStudents.length" @click="batchRemind"><Bell :size="16" />批量提醒</button></article>
          <article class="table-card"><table class="teacher-table"><thead><tr><th>学生</th><th>加入时间</th><th>课时进度</th><th>提问次数</th><th>错题数</th><th>最近学习</th><th>操作</th></tr></thead><TransitionGroup name="row-list" tag="tbody"><tr v-for="item in filteredStudents" :key="item.student.id" :class="{ inactive: isLongInactive(item.last_study_at) }"><td><span class="avatar mini">{{ firstChar(item.student.nickname) }}</span><strong>{{ item.student.nickname }}</strong><code>{{ item.student.student_no || '-' }}</code></td><td>{{ shortDate(item.joined_at) }}</td><td><ProgressBar :value="item.progress_percent" />{{ item.studied_lessons }}/{{ item.lesson_total }}</td><td><MessageCircle :size="14" />{{ item.qa_count }}</td><td :class="{ danger: item.wrong_count > 10 }"><XCircle :size="14" />{{ item.wrong_count }}</td><td>{{ relativeTime(item.last_study_at) }}</td><td><button class="icon-action" :data-loading="isPending(`open-student-${item.student.id}`)" :disabled="isPending(`open-student-${item.student.id}`)" @click="openStudent(item.student.id)"><Eye :size="15" />详情</button><button class="icon-action" :data-loading="isPending(`remind-student-${item.student.id}`)" :disabled="isPending(`remind-student-${item.student.id}`)" @click="remindStudent(item.student.id)"><Bell :size="15" />提醒</button></td></tr></TransitionGroup></table></article>
        </template>
      </section>

      <section v-if="active === 'teacherAnalytics'" key="teacherAnalytics" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="ai-suggestion" :class="{ thinking: pageLoading || isPending('refresh-analysis') }"><span><Sparkles :size="20" /></span><div><h2>教学建议</h2><p>{{ analysis.suggestion || '暂无建议' }}</p></div><button class="btn btn-ghost btn-sm" :data-loading="isPending('refresh-analysis')" :disabled="isPending('refresh-analysis')" @click="refreshAnalysis"><RefreshCw :size="14" />刷新</button><span class="tag tag-ai">{{ analysisRange }}</span></article>
          <div class="metric-grid six compact"><MetricCard :icon="Activity" label="活跃率" :value="`${analysis.metrics?.active_rate || 0}%`" sub="近7天" /><MetricCard :icon="Clock" label="学习时长" :value="`${analysis.metrics?.study_hours || 0}h`" sub="期间" /><MetricCard :icon="Presentation" label="完成率" :value="`${analysis.metrics?.completion_rate || 0}%`" sub="课时" /><MetricCard :icon="MessageCircle" label="问答总量" :value="analysis.metrics?.qa_total || 0" sub="期间" /><MetricCard :icon="ClipboardList" label="平均分" :value="analysis.metrics?.average_score || 0" sub="/100" /><MetricCard :icon="AlertTriangle" label="薄弱点" :value="analysis.metrics?.weak_point_count || 0" sub="数量" :danger="(analysis.metrics?.weak_point_count || 0) > 0" /></div>
          <div class="analysis-grid two"><article class="panel-card"><div class="panel-head"><h2><Presentation :size="18" />课时完成率</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="260" /></article><article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />学习时长</h2></div><AdminChart type="line" :labels="analysisTimeLabels" :series="analysisTimeSeries" :height="260" /></article></div>
          <div class="analysis-grid knowledge"><article class="panel-card"><div class="panel-head"><h2><Layers :size="18" />章节掌握</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="260" /></article><article class="panel-card weak-list"><div class="panel-head weak-head"><div><h2><TrendingDown :size="18" />薄弱知识点</h2><small>专项题生成与作答管理已移至薄弱题目页面</small></div><button class="btn btn-secondary btn-sm weak-create-all" @click="go('teacherWeakQuizzes')"><ClipboardList :size="14" />管理题目</button></div><TransitionGroup name="motion-list" tag="div" class="weak-row-list"><div v-for="(item, index) in analysis.weak_points || []" :key="item.knowledge_point" class="weak-row weak-row-readonly"><b>{{ rankNumber(index) }}</b><span>{{ item.knowledge_point }}</span><AppProgress :value="item.wrong_count" :max="weakMax" tone="danger" /><strong>{{ item.wrong_count }}</strong><em>错题数</em></div></TransitionGroup><EmptyState v-if="!(analysis.weak_points || []).length" text="暂无薄弱点" /></article></div>
          <article class="panel-card"><div class="panel-head"><h2><MessageCircle :size="18" />学生高频问题</h2><small>{{ analysisRange }}</small></div><div class="question-layout"><TransitionGroup name="cloud-list" tag="div" class="word-cloud"><span v-for="item in analysis.high_frequency_questions || []" :key="item.question" :style="{ fontSize: cloudSize(item.count) }">{{ item.question.slice(0, 12) }}</span></TransitionGroup><TransitionGroup name="motion-list" tag="div"><div v-for="(item, index) in analysis.high_frequency_questions || []" :key="item.question" class="question-row"><b>{{ rankPlain(index) }}</b><span>{{ item.question }}</span><strong>{{ item.count }}次</strong></div></TransitionGroup></div></article>
          <div class="analysis-grid three"><article class="panel-card"><div class="panel-head"><h2><ClipboardList :size="18" />成绩分布</h2></div><AdminChart type="bar" :labels="scoreLabels" :series="scoreSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><CheckCircle :size="18" />测验完成</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><XCircle :size="18" />错题分布</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="220" /></article></div>
          <article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生活跃度</h2><button class="btn btn-ghost btn-sm" :disabled="!filteredStudents.length" @click="batchRemind"><Bell :size="14" />批量提醒</button></div><div class="activity-layers"><LayerCard label="高度活跃" :value="analysis.student_layers?.high || 0" tone="success" :max="studentPayload.stats?.total || 1" /><LayerCard label="正常活跃" :value="analysis.student_layers?.normal || 0" :max="studentPayload.stats?.total || 1" /><LayerCard label="低活跃" :value="analysis.student_layers?.low || 0" tone="warning" :max="studentPayload.stats?.total || 1" /><LayerCard label="长期未活跃" :value="analysis.student_layers?.inactive || 0" tone="danger" :max="studentPayload.stats?.total || 1" /></div></article>
        </template>
      </section>

      <section v-if="active === 'teacherWeakQuizzes'" key="teacherWeakQuizzes" class="teacher-content weak-quiz-page">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="ai-suggestion weak-quiz-hero" :class="{ thinking: weakQuizGenerating }">
            <span><AlertTriangle :size="20" /></span>
            <div><h2>薄弱题目管理</h2><p>按薄弱知识点生成多套专项测验，审核题目后发布，并追踪学生作答情况。</p></div>
            <button class="btn btn-ai btn-sm" :data-loading="weakQuizGenerating && weakQuizGenerationMode === 'all'" :disabled="weakQuizGenerating || !weakQuizFormValid || !weakQuizPoints.length" @click="generateTeacherWeakQuiz()"><Sparkles :size="14" />生成综合测验</button>
          </article>
          <div class="metric-grid four compact"><MetricCard :icon="AlertTriangle" label="薄弱知识点" :value="weakQuizData.stats?.weak_point_count || 0" sub="当前课程" :danger="(weakQuizData.stats?.weak_point_count || 0) > 0" /><MetricCard :icon="XCircle" label="错题累计" :value="weakQuizData.stats?.wrong_count || 0" sub="学生错题" tone="warning" /><MetricCard :icon="ClipboardList" label="题目套数" :value="weakQuizData.stats?.quiz_set_count || 0" sub="已生成" tone="success" /><MetricCard :icon="CheckCircle" label="题型合计" :value="weakQuizTypeTotal" :sub="weakQuizFormValid ? '配置有效' : '需等于总题量'" :danger="!weakQuizFormValid" /></div>
          <div class="weak-quiz-layout">
            <aside class="panel-card weak-config-card">
              <div class="panel-head rich-head"><div><h2><Settings :size="18" />生成设置</h2><small>一次生成一套测验，可重复生成多套</small></div></div>
              <div class="weak-config-body">
                <label>题目总数<input v-model.number="weakQuizForm.question_count" class="input" type="number" min="1" max="20" /></label>
                <label>难度<AppSelect v-model="weakQuizForm.difficulty" :options="quizDifficultyOptions" /></label>
                <div class="weak-type-grid">
                  <label v-for="item in weakQuestionTypes" :key="item.value">{{ item.label }}<input v-model.number="weakQuizForm.question_type_counts[item.value]" class="input" type="number" min="0" max="20" /></label>
                </div>
                <div class="weak-type-status" :class="{ invalid: !weakQuizFormValid }"><strong>{{ weakQuizTypeTotal }}</strong><span>题型合计 / 总题量 {{ weakQuizForm.question_count }}</span></div>
                <button class="btn btn-primary full" :data-loading="weakQuizGenerating && weakQuizGenerationMode === 'all'" :disabled="weakQuizGenerating || !weakQuizFormValid || !weakQuizPoints.length" @click="generateTeacherWeakQuiz()"><Sparkles :size="15" />按全部薄弱点生成</button>
                <button class="btn btn-ghost full" :data-loading="isPending('load-weak-quizzes')" :disabled="isPending('load-weak-quizzes')" @click="loadWeakQuizzes(true)"><RefreshCw :size="15" />刷新列表</button>
              </div>
            </aside>
            <section class="panel-card weak-selection-card">
              <div class="panel-head rich-head"><div><h2><ClipboardList :size="18" />题目选择</h2><small>选择综合测验或按薄弱知识点选择专项套题</small></div></div>
              <div class="weak-selection-scroll">
                <section v-if="weakQuizAllSets.length" class="weak-set-section">
                  <div class="weak-section-title"><strong>综合测验</strong><small>覆盖全部薄弱知识点的测验套卷</small></div>
                  <div class="weak-set-grid">
                    <button v-for="quiz in weakQuizAllSets" :key="quiz.id" type="button" class="weak-set-card" :class="{ active: weakQuizSelectedSetId === quiz.id }" @click="selectWeakQuizSet(quiz)">
                      <strong>{{ quiz.title }}</strong><span class="tag" :class="statusClass(quiz.status)">{{ statusText(quiz.status) }}</span><small>{{ quiz.question_count }}题 · {{ quiz.attempt_count }}次作答 · 平均 {{ quiz.average_accuracy }}%</small>
                    </button>
                  </div>
                </section>
                <section v-if="selectedWeakQuizPoint" class="weak-point-switcher">
                  <div class="weak-point-switcher-head">
                    <button type="button" class="icon-action" :disabled="weakQuizPointCount <= 1" @click="stepWeakQuizPoint(-1)"><ChevronLeft :size="15" />上一个</button>
                    <div class="weak-point-switcher-title">
                      <small>知识点 {{ weakQuizPointIndex + 1 }} / {{ weakQuizPointCount }}</small>
                      <strong>{{ selectedWeakQuizPoint.knowledge_point }}</strong>
                    </div>
                    <button type="button" class="icon-action" :disabled="weakQuizPointCount <= 1" @click="stepWeakQuizPoint(1)">下一个<ChevronRight :size="15" /></button>
                  </div>
                  <article :key="selectedWeakQuizPoint.knowledge_point_id" class="weak-point-card weak-point-active">
                    <header>
                      <b>{{ rankNumber(weakQuizPointIndex) }}</b>
                      <div><h2>{{ selectedWeakQuizPoint.knowledge_point }}</h2><p>{{ selectedWeakQuizPoint.description || '暂无知识点说明' }}</p></div>
                      <span class="tag tag-danger">{{ selectedWeakQuizPoint.wrong_count }} 错题</span>
                      <button class="btn btn-secondary btn-sm" :data-loading="weakQuizGeneratingTopic === selectedWeakQuizPoint.knowledge_point" :disabled="weakQuizGenerating || !weakQuizFormValid" @click="generateTeacherWeakQuiz(selectedWeakQuizPoint)"><Sparkles :size="14" />生成新套题</button>
                    </header>
                    <div v-if="selectedWeakQuizPoint.quiz_sets?.length" class="weak-set-list">
                      <button v-for="quiz in selectedWeakQuizPoint.quiz_sets" :key="quiz.id" type="button" class="weak-set-card" :class="{ active: weakQuizSelectedSetId === quiz.id }" @click="selectWeakQuizSet(quiz)">
                        <strong>{{ quiz.title }}</strong><span class="tag" :class="statusClass(quiz.status)">{{ statusText(quiz.status) }}</span><small>{{ quiz.question_count }}题 · {{ quiz.attempt_count }}次作答 · 平均 {{ quiz.average_accuracy }}%</small>
                      </button>
                    </div>
                    <div v-else class="weak-empty-line"><span>还没有为这个薄弱点生成题目</span><button class="link-btn" :disabled="weakQuizGenerating || !weakQuizFormValid" @click="generateTeacherWeakQuiz(selectedWeakQuizPoint)">立即生成</button></div>
                  </article>
                </section>
                <EmptyState v-else text="暂无薄弱知识点" />
              </div>
            </section>
            <aside class="panel-card weak-detail-card">
              <div class="panel-head rich-head"><div><h2><Eye :size="18" />题目与作答</h2><small>{{ weakQuizAttemptDetail?.quiz?.title || '选择一套题查看详情' }}</small></div></div>
              <div class="weak-detail-scroll">
                <template v-if="weakQuizAttemptDetail">
                  <div class="weak-detail-actions"><button class="btn btn-secondary btn-sm" @click="openWeakQuizEditor"><Eye :size="14" />查看题目</button><button v-if="weakQuizAttemptDetail.quiz?.status !== 'published'" class="btn btn-primary btn-sm" @click="openWeakQuizEditor"><Check :size="14" />审核发布</button></div>
                  <section class="weak-detail-section">
                    <strong>题目预览</strong>
                    <div class="weak-question-preview"><div v-for="(question, index) in weakQuizAttemptDetail.questions || []" :key="question.id"><b>{{ rankPlain(index) }}</b><span>{{ question.stem }}</span><em>{{ questionTypeText(question.question_type) }}</em></div></div>
                  </section>
                  <section class="weak-detail-section">
                    <strong>作答记录</strong>
                    <div class="weak-attempt-list">
                      <article v-for="attempt in weakQuizAttemptDetail.attempts || []" :key="attempt.id" class="weak-attempt-row">
                        <div class="weak-attempt-summary">
                          <span class="avatar mini">{{ firstChar(attempt.student?.nickname) }}</span>
                          <div class="weak-attempt-student"><strong>{{ attempt.student?.nickname || '学生' }}</strong><small>{{ formatTime(attempt.submitted_at) }}</small></div>
                          <b>{{ attempt.score }}/{{ attempt.total_score }}</b>
                          <em>{{ attempt.correct_count }}/{{ attempt.answer_count }}</em>
                        </div>
                        <div v-if="attempt.answers?.length" class="weak-answer-mini">
                          <span v-for="(answer, index) in attempt.answers" :key="answer.id" :class="{ correct: answer.is_correct }">
                            <b>{{ rankPlain(index) }}</b><strong>{{ answer.is_correct ? '正确' : '错误' }}</strong><small>{{ answer.user_answer ?? '未作答' }}</small>
                          </span>
                        </div>
                      </article>
                      <EmptyState v-if="!(weakQuizAttemptDetail.attempts || []).length" text="暂无学生作答" />
                    </div>
                  </section>
                </template>
                <EmptyState v-else text="请选择一套薄弱题目" />
              </div>
            </aside>
          </div>
        </template>
      </section>

      <section v-if="active === 'teacherProfile'" key="teacherProfile" class="teacher-content profile-content">
        <article class="profile-card"><button type="button" class="avatar large profile-avatar-button" :class="{ 'has-image': teacherAvatarUrl }" :data-loading="isPending('upload-avatar')" :disabled="isPending('upload-avatar')" title="更换头像" aria-label="更换头像" @click="teacherAvatarInput?.click()"><img v-if="teacherAvatarUrl" :src="teacherAvatarUrl" alt="" /><template v-else>{{ firstChar(teacherName) }}</template><Camera :size="18" /></button><input ref="teacherAvatarInput" class="visually-hidden-file" type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="uploadProfileAvatar" /><div><h1>{{ profileForm.nickname }}<span class="tag tag-primary">教师</span></h1><p><Mail :size="15" />{{ user.email }}</p><p><IdCard :size="15" />{{ user.employee_no || '-' }}</p><small><Clock :size="14" />{{ registeredDays }} 天</small></div><button class="btn btn-secondary btn-sm" @click="profileEditing = true"><Pencil :size="14" />编辑信息</button></article>
        <div class="profile-tabs"><button :class="{ active: profileTab === 'base' }" @click="profileTab = 'base'"><User :size="16" />基本信息</button><button :class="{ active: profileTab === 'security' }" @click="profileTab = 'security'"><Lock :size="16" />账号安全</button><button :class="{ active: profileTab === 'notice' }" @click="profileTab = 'notice'"><Bell :size="16" />通知设置</button></div>
        <Transition name="fade-slide" mode="out-in">
          <article v-if="profileTab === 'base'" key="base" class="panel-card profile-form"><label>姓名<input v-model="profileForm.nickname" class="input" :readonly="!profileEditing" /></label><label>邮箱<input :value="user.email" class="input" readonly /></label><label>学校/单位<input v-model="profileForm.organization" class="input" :readonly="!profileEditing" /></label><label>所在院系<input v-model="profileForm.department" class="input" :readonly="!profileEditing" /></label><label>个人简介<textarea v-model="profileForm.bio" class="textarea" :readonly="!profileEditing"></textarea></label><footer><button class="btn btn-ghost" @click="profileEditing = false">取消</button><button class="btn btn-primary" :data-loading="isPending('save-profile')" :disabled="isPending('save-profile')" @click="saveProfile">保存修改</button></footer></article>
          <article v-else-if="profileTab === 'security'" key="security" class="panel-card profile-form">
            <div class="panel-head"><h2><Lock :size="18" />修改密码</h2></div>
            <label>当前密码<PasswordField v-model="passwordForm.old_password" /></label>
            <label>新密码<PasswordField v-model="passwordForm.new_password" /></label>
            <div class="strength"><i :style="{ width: passwordStrength + '%' }"></i></div>
            <label>确认新密码<PasswordField v-model="passwordConfirm" /></label>
            <button class="btn btn-primary btn-sm" :data-loading="isPending('change-password')" :disabled="isPending('change-password')" @click="changePassword">修改密码</button>
          </article>
          <article v-else key="notice" class="panel-card notice-list"><TransitionGroup name="motion-list" tag="div" class="notice-items"><AppCheckbox v-for="item in noticeSettings" :key="item.key" v-model="item.enabled" variant="switch" :label="item.label" /></TransitionGroup><button class="btn btn-primary btn-sm" :data-loading="isPending('save-notice')" :disabled="isPending('save-notice')" @click="saveNotice">保存设置</button></article>
        </Transition>
      </section>
      </TransitionGroup>
    </main>

    <Transition name="modal-pop">
      <div v-if="uploadOpen" class="modal-mask">
        <article class="modal upload-modal">
          <div class="modal-head"><Upload :size="20" /><h2>上传课程资料</h2><button class="icon-action modal-close-action" aria-label="关闭" title="关闭" :disabled="isPending('upload-materials')" @click="closeUploadModal"><X :size="16" />关闭</button></div>
          <label class="upload-drop" :class="{ disabled: isPending('upload-materials') }"><Upload :size="40" /><span>拖拽上传</span><input type="file" multiple accept=".ppt,.pptx,.pdf,.doc,.docx,.txt,.md,.markdown" :disabled="isPending('upload-materials')" @change="pickUploadFiles" /></label>
          <section v-if="uploadQueue.length" class="upload-progress-panel">
            <div class="upload-progress-head">
              <strong>{{ isPending('upload-materials') ? `上传进度 ${uploadOverallPercent}%` : uploadFailedCount ? '可重试失败文件' : '待上传文件' }}</strong>
              <small>{{ uploadProgressText }}</small>
            </div>
            <AppProgress :value="uploadOverallPercent" :tone="uploadProgressTone" />
          </section>
          <TransitionGroup name="motion-list" tag="div" class="upload-list">
            <div v-for="item in uploadQueue" :key="item.id" class="upload-row" :class="`is-${item.status}`">
              <File :size="18" />
              <div class="upload-body">
                <div class="upload-meta">
                  <div class="upload-meta-head"><span>{{ item.file.name }}</span><small>{{ sizeLabel(item.file.size) }}</small></div>
                  <div class="upload-meta-progress"><AppProgress :value="item.progress" :tone="uploadItemTone(item)" compact /><em>{{ uploadItemText(item) }}</em></div>
                  <p v-if="item.error" class="upload-error">{{ item.error }}</p>
                </div>
                <div class="upload-controls">
                  <AppSelect v-model="item.chapter_id" :disabled="isPending('upload-materials')" :options="uploadChapterOptions" />
                  <AppSelect v-model="item.category" :disabled="isPending('upload-materials')" :options="materialCategoryOptions" />
                  <button class="icon-action danger" :disabled="isPending('upload-materials')" @click="removeUpload(item.id)"><Trash2 :size="15" />移除</button>
                </div>
              </div>
            </div>
          </TransitionGroup>
          <footer><button class="btn btn-ghost" :disabled="isPending('upload-materials')" @click="closeUploadModal">取消</button><button class="btn btn-primary" :data-loading="isPending('upload-materials')" :disabled="!uploadQueue.length || isPending('upload-materials')" @click="uploadMaterials">确认上传</button></footer>
        </article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="chapterNameOpen" class="modal-mask">
        <article class="modal chapter-name-modal">
          <div class="modal-head">
            <Layers :size="20" />
            <h2>添加章节</h2>
            <button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="chapterNameOpen = false"><X :size="16" />关闭</button>
          </div>
          <label>章节名称<input ref="chapterNameInput" v-model="chapterNameDraft" class="input" maxlength="80" placeholder="输入章节名称" @keydown.enter.prevent="addChapterFromTree" /></label>
          <footer>
            <button class="btn btn-ghost" @click="chapterNameOpen = false">取消</button>
            <button class="btn btn-primary" :data-loading="isPending('add-tree-chapter')" :disabled="isPending('add-tree-chapter') || !chapterNameDraft.trim()" @click="addChapterFromTree"><Plus :size="16" />添加章节</button>
          </footer>
        </article>
      </div>
    </Transition>

    <Transition name="drawer">
      <aside v-if="studentDrawer" class="drawer">
        <div class="drawer-head"><span class="avatar">{{ firstChar(studentDrawer.student.nickname) }}</span><div><h2>{{ studentDrawer.student.nickname }}</h2><small>{{ studentDrawer.student.student_no || '-' }} · {{ studentDrawer.student.email }}</small></div><button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="studentDrawer = null"><X :size="16" />关闭</button></div>
        <div class="profile-tabs small-tabs"><button :class="{ active: studentTab === 'base' }" @click="studentTab = 'base'">基本信息</button><button :class="{ active: studentTab === 'data' }" @click="studentTab = 'data'">学习数据</button><button :class="{ active: studentTab === 'qa' }" @click="studentTab = 'qa'">问答记录</button></div>
        <Transition name="fade-slide" mode="out-in">
          <section v-if="studentTab === 'base'" key="base" class="drawer-body"><InfoRow label="加入时间" :value="formatTime(studentDrawer.membership.joined_at)" /><InfoRow label="加入方式" value="课程码" /><InfoRow label="邮箱" :value="studentDrawer.student.email" /><InfoRow label="学号" :value="studentDrawer.student.student_no || '-'" /><div class="drawer-actions"><button class="btn btn-secondary" :data-loading="isPending(`remind-student-${studentDrawer.student.id}`)" :disabled="isPending(`remind-student-${studentDrawer.student.id}`)" @click="remindStudent(studentDrawer.student.id)"><Bell :size="16" />发送提醒</button><button class="btn btn-danger" :data-loading="isPending(`remove-student-${studentDrawer.student.id}`)" :disabled="isPending(`remove-student-${studentDrawer.student.id}`)" @click="removeStudent(studentDrawer.student.id)">移出课程</button></div></section>
          <section v-else-if="studentTab === 'data'" key="data" class="drawer-body"><TransitionGroup name="motion-list" tag="div" class="drawer-progress-list"><div v-for="item in studentDrawer.lesson_progress" :key="item.lesson.id" class="drawer-progress"><span>{{ item.lesson.title }}</span><ProgressBar :value="item.progress_percent" /><small>{{ item.current_page }}/{{ item.lesson.page_count }}</small></div></TransitionGroup><div class="drawer-stats">提问 {{ studentDrawer.stats.qa_total }} · 测验 {{ studentDrawer.stats.attempt_total }} · 平均 {{ studentDrawer.stats.average_score }} · 错题 {{ studentDrawer.stats.wrong_total }}</div><TransitionGroup name="motion-list" tag="div" class="tag-list"><span v-for="item in studentDrawer.weak_points" :key="item.name" class="tag tag-warning">{{ item.name }}</span></TransitionGroup></section>
          <section v-else key="qa" class="drawer-body"><TransitionGroup name="motion-list" tag="div" class="qa-record-list"><div v-for="item in studentDrawer.qa_records" :key="item.id" class="qa-record"><MessageCircle :size="16" /><div><strong>{{ item.question }}</strong><p>{{ item.answer }}</p><small>{{ formatTime(item.created_at) }}</small></div></div><EmptyState v-if="!studentDrawer.qa_records.length" key="empty" text="暂无问答" /></TransitionGroup></section>
        </Transition>
      </aside>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="reminderOpen" class="modal-mask">
        <article class="modal reminder-modal">
          <div class="modal-head">
            <Bell :size="20" />
            <h2>发送学习提醒</h2>
            <button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="reminderOpen = false"><X :size="16" />关闭</button>
          </div>
          <div class="reminder-recipients">
            <Users :size="16" />
            <span>发送给 {{ reminderTargetIds.length }} 名学生</span>
            <small>{{ reminderTargetNames }}</small>
          </div>
          <label>提醒标题<input v-model="reminderForm.title" class="input" maxlength="80" /></label>
          <label>提醒内容<textarea v-model="reminderForm.message" class="textarea" maxlength="500" rows="5"></textarea><small>{{ reminderForm.message.length }} / 500</small></label>
          <footer>
            <button class="btn btn-ghost" @click="reminderOpen = false">取消</button>
            <button class="btn btn-primary" :data-loading="isPending('send-reminder')" :disabled="isPending('send-reminder') || !reminderForm.title.trim() || !reminderForm.message.trim()" @click="sendReminder"><Bell :size="16" />发送提醒</button>
          </footer>
        </article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="helpOpen" class="modal-mask" @click.self="helpOpen = false">
        <article class="modal help-modal">
          <div class="modal-head"><HelpCircle :size="20" /><h2>使用帮助</h2><button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="helpOpen = false"><X :size="16" />关闭</button></div>
          <div class="help-body">
            <section class="help-section">
              <h3><BookOpen :size="16" />快速上手</h3>
              <ol>
                <li>在「我的课程」创建课程并填写章节结构。</li>
                <li>进入「资料管理」上传 PPT/PDF/Word/TXT，等待 AI 解析。</li>
                <li>解析完成后在「PPT 工作台」审核脚本并发布课时。</li>
                <li>用课程码邀请学生加入，在「学生管理」跟踪进度。</li>
              </ol>
            </section>
            <section class="help-section">
              <h3><Sparkles :size="16" />AI 任务与重试</h3>
              <p>资料解析、脚本生成和测验生成会进入 AI 任务队列。若任务显示「失败」，可点击任务上的「重试」重新提交处理。</p>
            </section>
            <section class="help-section">
              <h3><Mail :size="16" />联系与反馈</h3>
              <p>遇到问题可联系平台管理员，或通过页面右上角「通知」查看系统提醒。</p>
            </section>
          </div>
          <footer><button class="btn btn-primary" @click="helpOpen = false">我知道了</button></footer>
        </article>
      </div>
    </Transition>

    <MaterialPreviewModal :open="!!previewItem" :item="previewItem" :detail="previewDetail" :loading="previewItem ? isPending(`preview-material-${previewItem.id}`) : false" @download="downloadMaterial" @close="closePreview" />
    <Transition name="modal-pop">
      <div v-if="lessonPreview" class="modal-mask">
        <article class="modal lesson-preview-modal">
          <div class="modal-head"><Presentation :size="20" /><h2>{{ lessonPreview.lesson.title }}</h2><button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="lessonPreview = null"><X :size="16" />关闭</button></div>
          <div class="lesson-preview-layout">
            <aside>
              <button v-for="page in lessonPreview.pages" :key="page.id" :class="{ active: lessonPreviewPageId === page.id }" @click="lessonPreviewPageId = page.id">
                <span>{{ page.page_number }}</span>
                <strong>{{ page.page_title || `第${page.page_number}页` }}</strong>
              </button>
            </aside>
            <section v-if="lessonPreviewActivePage" class="lesson-preview-stage">
              <article><h3>{{ lessonPreviewActivePage.page_title || `第${lessonPreviewActivePage.page_number}页` }}</h3><div class="teacher-markdown markdown-body" v-html="lessonPreviewPageHtml"></div></article>
              <article><h3>AI 讲解脚本</h3><div class="teacher-markdown markdown-body" v-html="lessonPreviewScriptHtml"></div></article>
            </section>
            <EmptyState v-else text="该课时暂无页面" />
          </div>
        </article>
      </div>
    </Transition>
    <Transition name="modal-pop">
      <div v-if="quizEditorOpen" class="modal-mask">
        <article class="modal quiz-editor-modal">
          <div class="modal-head">
            <Sparkles :size="20" />
            <h2>编辑课堂测验</h2>
            <span class="tag" :class="statusClass(quizEditor.status)">{{ statusText(quizEditor.status) }}</span>
            <button class="icon-action modal-close-action" aria-label="关闭" title="关闭" @click="quizEditorOpen = false"><X :size="16" />关闭</button>
          </div>
          <div class="quiz-editor-layout">
            <aside class="quiz-editor-side">
              <label>测验标题<input v-model="quizEditor.title" class="input" maxlength="80" /></label>
              <label>测验说明<textarea v-model="quizEditor.description" class="textarea" maxlength="300"></textarea></label>
              <div class="quiz-editor-stats"><span>{{ quizEditor.questions.length }}</span><small>题目数</small><span>{{ quizEditor.questions.reduce((sum, item) => sum + Number(item.score || 0), 0) }}</span><small>总分</small></div>
              <button class="btn btn-secondary full" type="button" @click="addEditorQuestion"><Plus :size="15" />新增题目</button>
            </aside>
            <section class="quiz-editor-questions">
              <article v-for="(question, qIndex) in quizEditor.questions" :key="question.local_id" class="quiz-edit-card">
                <header>
                  <b>{{ qIndex + 1 }}</b>
                  <select v-model="question.question_type" class="input" @change="changeEditorQuestionType(question)">
                    <option value="single_choice">单选题</option>
                    <option value="multiple_choice">多选题</option>
                    <option value="judge">判断题</option>
                    <option value="short_answer">简答题</option>
                    <option value="blank">填空题</option>
                  </select>
                  <input v-model.number="question.score" class="input score-input" type="number" min="1" max="100" />
                  <button class="icon-action danger" type="button" :disabled="quizEditor.questions.length <= 1" @click="removeEditorQuestion(qIndex)"><Trash2 :size="15" />删除</button>
                </header>
                <div v-if="question.knowledge_point_name || question.difficulty || (quizEditor.generated && question.id)" class="quiz-edit-meta">
                  <span v-if="question.knowledge_point_name" class="tag tag-primary">{{ question.knowledge_point_name }}</span>
                  <span v-if="question.difficulty" class="tag" :class="difficultyTagClass(question.difficulty)">{{ difficultyText(question.difficulty) }}</span>
                  <button v-if="quizEditor.generated && question.id" class="btn btn-secondary btn-sm quiz-regenerate-btn" type="button" :data-loading="isPending(`regen-question-${question.id}`)" :disabled="isPending(`regen-question-${question.id}`) || quizEditorSaving || quizEditorPublishing" @click="regenerateEditorQuestion(question)"><RefreshCw :size="14" />{{ isPending(`regen-question-${question.id}`) ? '生成中…' : '换一题' }}</button>
                </div>
                <label>题干<textarea v-model="question.stem" class="textarea" maxlength="2000"></textarea></label>
                <div v-if="question.question_type === 'single_choice' || question.question_type === 'multiple_choice'" class="option-editor">
                  <div v-for="(option, index) in question.options" :key="index" class="option-edit-row">
                    <span>{{ optionLabel(Number(index)) }}</span>
                    <input v-model="question.options[index]" class="input" />
                    <label v-if="question.question_type === 'single_choice'" class="answer-radio"><input v-model.number="question.reference_answer.value" type="radio" :value="index" />正确</label>
                    <label v-else class="answer-radio"><input type="checkbox" :checked="question.reference_answer.value?.includes(Number(index))" @change="toggleEditorMultiAnswer(question, Number(index))" />正确</label>
                    <button class="icon-action danger" type="button" :disabled="question.options.length <= 2" @click="removeEditorOption(question, Number(index))"><Trash2 :size="14" /></button>
                  </div>
                  <button class="dashed-btn" type="button" @click="addEditorOption(question)"><Plus :size="15" />添加选项</button>
                </div>
                <label v-else-if="question.question_type === 'judge'">正确答案<select v-model="question.reference_answer.value" class="input"><option :value="true">正确</option><option :value="false">错误</option></select></label>
                <label v-else>参考答案关键词<input v-model="question.reference_answer.keywordsText" class="input" placeholder="用逗号分隔" /></label>
                <label>解析<textarea v-model="question.explanation" class="textarea" maxlength="2000"></textarea></label>
              </article>
            </section>
          </div>
          <footer>
            <button class="btn btn-ghost" @click="quizEditorOpen = false">取消</button>
            <button class="btn btn-secondary" :data-loading="quizEditorSaving" :disabled="quizEditorSaving || quizEditorPublishing" @click="saveQuizEditor"><Save :size="15" />保存</button>
            <button class="btn btn-primary" :data-loading="quizEditorPublishing" :disabled="quizEditorSaving || quizEditorPublishing" @click="publishQuizEditor"><Check :size="15" />发布给学生</button>
          </footer>
        </article>
      </div>
    </Transition>
    <ConfirmDialog
      :open="confirmDeleteCourseOpen"
      title="删除课程"
      message="删除后课程、章节和相关课时将不可恢复。"
      confirm-text="删除"
      tone="danger"
      @cancel="confirmDeleteCourseOpen = false"
      @confirm="confirmDeleteCourse"
    />
    <ConfirmDialog
      :open="confirmRemoveStudentOpen"
      title="移出课程"
      :message="`确认将学生 ${confirmRemoveStudent.name} 移出课程？移出后该学生将无法继续学习本课程。`"
      confirm-text="移出"
      tone="danger"
      @cancel="confirmRemoveStudentOpen = false"
      @confirm="confirmRemoveStudentAction"
    />
    <ConfirmDialog
      :open="confirmDeleteLessonOpen"
      title="删除课时"
      message="删除课时将同时不可恢复地删除该课时下所有学生的学习进度与讲解内容，确认删除？"
      confirm-text="删除"
      tone="danger"
      @cancel="confirmDeleteLessonOpen = false"
      @confirm="confirmDeleteLesson"
    />
    <ConfirmDialog
      :open="confirmDeleteMaterialOpen"
      title="删除资料"
      message="删除资料将一并删除其解析内容与向量，不可恢复，确认删除？"
      confirm-text="删除"
      tone="danger"
      @cancel="confirmDeleteMaterialOpen = false"
      @confirm="confirmDeleteMaterial"
    />
  </section>
</template>

<script setup lang="ts">
import { TransitionGroup, computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  Activity, AlertCircle, AlertTriangle, ArrowLeft, Ban, BarChart2, Bell, BookOpen, Camera, Check, CheckCircle,
  ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, Database, Download, Edit2, Eye, File,
  FileEdit, FileText, FolderOpen, GripVertical, Grid2X2, HelpCircle, Home, IdCard, Layers, LayoutDashboard,
  Lock, LogOut, Mail, Maximize, MessageCircle, Pencil, Plus, PlusCircle, Presentation, RefreshCw,
  Save, Search, Settings, Share2, SkipBack, SkipForward, Sparkles, Trash2, TrendingDown, Upload, User, UserPlus, UserX,
  Users, Volume2, Wand2, X, XCircle, ZoomIn
} from "../icons";
import { api, setToken } from "../api/client";
import { routeByPage } from "../router";
import type { Course, CourseDetail, MaterialDetail, User as UserType } from "../types";
import { copyToClipboard } from "../utils/clipboard";
import { extractStructuredText, renderRichText } from "../utils/richText";
import AppCheckbox from "../components/AppCheckbox.vue";
import AppProgress from "../components/AppProgress.vue";
import AppSelect from "../components/AppSelect.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import LoadingMark from "../components/LoadingMark.vue";
import MaterialPreviewModal from "../components/MaterialPreviewModal.vue";
import PageLoader from "../components/PageLoader.vue";
import PasswordField from "../components/PasswordField.vue";
import ThemeToggle from "../components/ThemeToggle.vue";
import AdminChart from "./admin/AdminChart.vue";
import { firstChar, fileIcon, relativeTime, statusClass, statusText, typeText } from "./teacher/components/helpers";
import { MetricCard, EmptyState, CourseRequired, QuickAction, TaskList, LessonRows, MaterialTypeList, ActivityList, ProgressList, ProgressBar, MaterialStatus, LayerCard, InfoRow } from "./teacher/components/primitives";

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string]; authed: [user: UserType] }>();
const router = useRouter();

type UploadQueueItem = {
  id: number;
  file: File;
  chapter_id: number;
  category: string;
  progress: number;
  status: "pending" | "uploading" | "uploaded" | "failed";
  error: string;
};

const active = ref(props.pageKey || "teacherDashboard");
const sidebarCollapsed = ref(localStorage.getItem("teacher_sidebar_collapsed") !== "0");
const courses = ref<any[]>([]);
const dashboard = ref<any>({});
const courseHome = ref<any>({});
const materialSummary = ref<any>({});
const materials = ref<any[]>([]);
const materialDetail = ref<MaterialDetail | any | null>(null);
const lessonPreview = ref<any | null>(null);
const lessonPreviewPageId = ref<number | null>(null);
const workbenchMode = ref<"material" | "lesson">("material");
const lessons = ref<any[]>([]);
const studentPayload = ref<any>({ stats: {}, items: [] });
const studentDrawer = ref<any | null>(null);
const analysis = ref<any>({});
const analysisCache = reactive<Record<string, { fetchedAt: number; data: any }>>({});
const initialPageLoading = ref(true);
const pageLoading = ref(false);
const currentCourseId = ref<number>(Number(localStorage.getItem("teacher_current_course_id") || 0));
const courseMenuOpen = ref(false);
const userMenuOpen = ref(false);
const teacherNoticeOpen = ref(false);
const notificationReading = ref(false);
const courseSwitchRef = ref<HTMLElement | null>(null);
const userMenuRef = ref<HTMLElement | null>(null);
const teacherNoticeRef = ref<HTMLElement | null>(null);
const courseView = ref<"grid" | "list">("grid");
const materialView = ref<"grid" | "list">("list");
const selectedChapterId = ref(0);
const advancedOpen = ref(false);
const chapterKeyword = ref("");
const materialSort = ref("time");
const lessonSort = ref("created");
const uploadOpen = ref(false);
const uploadQueue = ref<UploadQueueItem[]>([]);
const chapterNameOpen = ref(false);
const chapterNameDraft = ref("");
const chapterNameInput = ref<HTMLInputElement | null>(null);
const removedChapterIds = ref<number[]>([]);
const previewItem = ref<any | null>(null);
const previewDetail = ref<MaterialDetail | any | null>(null);
const currentPageId = ref<number | null>(null);
const scriptDraft = ref("");
const analysisRange = ref("本月");
const analysisRangeOptions = ["本周", "本月", "本学期"];
const profileTab = ref<"base" | "security" | "notice">("base");
const profileEditing = ref(false);
const passwordConfirm = ref("");
const studentTab = ref<"base" | "data" | "qa">("base");
const pendingActions = reactive(new Set<string>());
const materialProcessingOverrides = reactive<Record<number, { startedAt: number; seenProcessing: boolean }>>({});
const freshChapterId = ref<number | null>(null);
const freshMaterialChapterId = ref<number | null>(null);
const slideScale = ref(1);
const stageFocused = ref(false);
const slideOverviewOpen = ref(false);
const presentationMode = ref(false);
const scriptEditor = ref<HTMLTextAreaElement | null>(null);
const scriptUndoStack = ref<string[]>([]);
const scriptRedoStack = ref<string[]>([]);
const editorPulse = ref("");
const confirmDeleteCourseOpen = ref(false);
const confirmRemoveStudentOpen = ref(false);
const confirmRemoveStudent = reactive<{ id: number; name: string }>({ id: 0, name: "" });
const confirmDeleteLessonOpen = ref(false);
const confirmDeleteLessonId = ref(0);
const confirmDeleteMaterialOpen = ref(false);
const confirmDeleteMaterialId = ref(0);
const helpOpen = ref(false);
const reminderOpen = ref(false);
const reminderTargetIds = ref<number[]>([]);
const courseCoverFile = ref<File | null>(null);
const courseCoverPreview = ref("");
const courseCoverInput = ref<HTMLInputElement | null>(null);
const quizEditorOpen = ref(false);
const quizEditorSaving = ref(false);
const quizEditorPublishing = ref(false);
const weakQuizGenerating = ref(false);
const weakQuizGeneratingTopic = ref("");
const weakQuizGenerationMode = ref<"all" | "single" | "">("");
const weakQuizStatus = ref("");
const weakQuizData = ref<any>({ stats: {}, weak_points: [], all_sets: [] });
const weakQuizSelectedSetId = ref(0);
const weakQuizPointIndex = ref(0);
const weakQuizAttemptDetail = ref<any | null>(null);
const quizEditor = reactive({ id: 0, status: "", title: "", description: "", generated: false, questions: [] as any[] });
let freshChapterTimer = 0;
let freshMaterialChapterTimer = 0;
let editorPulseTimer = 0;
let materialRefreshTimers: number[] = [];
const weakQuizTaskPollIntervalMs = 2500;
const weakQuizTaskMaxPolls = 240;

const courseFilter = reactive({ keyword: "", term: "", status: "" });
const materialFilter = reactive({ keyword: "", type: "", status: "" });
const lessonFilter = reactive({ keyword: "", chapter_id: 0, status: "" });
const lessonPage = ref(1);
const lessonPageSize = 12;
const studentFilter = reactive({ keyword: "", progress: "", active: "" });
const courseForm = reactive({ id: 0, name: "", description: "", term: "2026春", cover_url: "", cover_color: "#121614", allow_leave: true, ai_qa: true, quiz_enabled: true, allow_general_ai_answer: false, chapters: [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] as any[] });
const weakQuizForm = reactive({
  question_count: 5,
  difficulty: "mixed",
  question_type_counts: {
    single_choice: 2,
    multiple_choice: 1,
    judge: 1,
    blank: 0,
    short_answer: 1,
  } as Record<string, number>,
});
const reminderForm = reactive({ title: "", message: "" });
const profileForm = reactive({ nickname: props.user.nickname, avatar_url: props.user.avatar_url || "", organization: "", department: "", bio: props.user.bio || "" });
const teacherAvatarInput = ref<HTMLInputElement | null>(null);
const passwordForm = reactive({ old_password: "", new_password: "" });
const noticeSettings = reactive([{ key: "join", label: "学生加入课程", enabled: true }, { key: "ppt", label: "PPT 解析完成", enabled: true }, { key: "script", label: "脚本生成完成", enabled: false }, { key: "tts", label: "TTS 合成失败", enabled: true }, { key: "qa", label: "学生问答汇总", enabled: true }, { key: "ai", label: "AI 任务状态", enabled: true }, { key: "peak", label: "提问高峰", enabled: true }, { key: "system", label: "系统公告", enabled: true }]);

const palette = ["#121614", "#D94925", "#00B8D4", "#2E7D32", "#D9A05B", "#C62828"];
const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const pageTitleMap: Record<string, string> = { teacherDashboard: "工作台首页", teacherCourses: "我的课程", teacherCourseForm: "创建课程", teacherCourseHome: "课程主页", teacherMaterials: "资料管理", teacherPpt: "PPT 工作台", teacherLessons: "课时管理", teacherStudents: "学生管理", teacherAnalytics: "教学分析", teacherWeakQuizzes: "薄弱题目", teacherProfile: "个人中心" };
const courseStatusOptions = [{ label: "全部", value: "" }, { label: "进行中", value: "active" }, { label: "已下架", value: "inactive" }];
const materialTypeOptions = [{ label: "全部", value: "" }, { label: "PPT", value: "pptx" }, { label: "PDF", value: "pdf" }, { label: "Word", value: "docx" }, { label: "TXT/Markdown", value: "txt" }];
const materialStatusOptions = [{ label: "全部", value: "" }, { label: "已解析", value: "ready" }, { label: "解析中", value: "processing" }, { label: "解析失败", value: "failed" }];
const materialSortOptions = [{ label: "上传时间", value: "time" }, { label: "文件名", value: "name" }, { label: "文件大小", value: "size" }];
const materialCategoryOptions = [{ label: "课件", value: "courseware" }, { label: "讲义", value: "handout" }, { label: "习题", value: "exercise" }, { label: "参考资料", value: "reference" }];
const lessonStatusOptions = [{ label: "全部", value: "" }, { label: "已发布", value: "published" }, { label: "草稿", value: "ready" }];
const lessonSortOptions = [{ label: "创建时间", value: "created" }, { label: "发布时间", value: "published" }, { label: "学习人数", value: "students" }];
const studentProgressOptions = [{ label: "全部进度", value: "" }, { label: "未开始", value: "none" }, { label: "学习中", value: "learning" }, { label: "已完成", value: "done" }];
const studentActiveOptions = [{ label: "全部状态", value: "" }, { label: "活跃", value: "active" }, { label: "近期不活跃", value: "inactive" }, { label: "长期未活跃", value: "long" }];
const weakQuestionTypes = [
  { label: "单选题", value: "single_choice" },
  { label: "多选题", value: "multiple_choice" },
  { label: "判断题", value: "judge" },
  { label: "填空题", value: "blank" },
  { label: "简答题", value: "short_answer" },
];
const quizDifficultyOptions = [
  { label: "混合（易中难梯度）", value: "mixed" },
  { label: "基础", value: "easy" },
  { label: "标准", value: "standard" },
  { label: "较难", value: "hard" },
];
const questionDifficultyTextMap: Record<string, string> = { easy: "基础", standard: "标准", hard: "较难" };
const courseOperationPages = new Set(["teacherMaterials", "teacherPpt", "teacherLessons", "teacherStudents", "teacherAnalytics", "teacherWeakQuizzes"]);

const currentCourse = computed(() => courses.value.find((course) => course.id === currentCourseId.value) || courses.value[0] || null);
const currentCourseOperable = computed(() => isCourseOperable(currentCourse.value));
const pageTitle = computed(() => pageTitleMap[active.value] || "教师端");
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }));
const focusCount = computed(() => (dashboard.value.todos || []).length || courses.value.length);
const todoCount = computed(() => (dashboard.value.todos || []).length);
const teacherNotifications = computed(() => dashboard.value.notifications || []);
const topNoticeCount = computed(() => teacherNotifications.value.filter((item: any) => item.unread).length);
const courseTerms = computed(() => [...new Set(courses.value.map((course) => course.term).filter(Boolean))]);
const courseTermOptions = computed(() => [{ label: "全部学期", value: "" }, ...courseTerms.value.map((term) => ({ label: String(term), value: String(term) }))]);
const lessonChapterOptions = computed(() => [{ label: "全部章节", value: 0 }, ...(courseHome.value.chapters || []).map((chapter: any) => ({ label: chapter.title, value: chapter.id }))]);
const uploadChapterRows = computed(() => {
  const summaryChapters = Array.isArray(materialSummary.value.chapters) ? materialSummary.value.chapters : [];
  const homeChapters = Array.isArray(courseHome.value.chapters) ? courseHome.value.chapters : [];
  const rows = summaryChapters.length ? summaryChapters : homeChapters;
  const seen = new Set<number>();
  return rows.filter((chapter: any) => {
    const id = Number(chapter?.id || 0);
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
});
const uploadChapterOptions = computed(() => [{ label: "未分章节", value: 0 }, ...uploadChapterRows.value.map((chapter: any) => ({ label: chapter.title || "未命名章节", value: chapter.id }))]);
const uploadCompletedCount = computed(() => uploadQueue.value.filter((item) => item.status === "uploaded").length);
const uploadActiveCount = computed(() => uploadQueue.value.filter((item) => item.status === "uploading").length);
const uploadFailedCount = computed(() => uploadQueue.value.filter((item) => item.status === "failed").length);
const uploadOverallPercent = computed(() => {
  if (!uploadQueue.value.length) return 0;
  const total = uploadQueue.value.reduce((sum, item) => sum + Math.max(0, Math.min(100, Number(item.progress) || 0)), 0);
  return Math.round(total / uploadQueue.value.length);
});
const uploadProgressTone = computed<"primary" | "success" | "warning" | "danger">(() => {
  if (!uploadQueue.value.length) return "primary";
  if (uploadFailedCount.value && !uploadCompletedCount.value && !uploadActiveCount.value) return "danger";
  if (uploadFailedCount.value) return "warning";
  if (uploadCompletedCount.value === uploadQueue.value.length) return "success";
  return "primary";
});
const uploadProgressText = computed(() => {
  if (!uploadQueue.value.length) return "";
  const total = uploadQueue.value.length;
  const parts = [`已提交 ${uploadCompletedCount.value}/${total}`];
  if (uploadActiveCount.value) parts.push(`上传中 ${uploadActiveCount.value}`);
  if (uploadFailedCount.value) parts.push(`失败 ${uploadFailedCount.value}`);
  return parts.join(" · ");
});
const filteredCourses = computed(() => courses.value.filter((course) => (!courseFilter.keyword || course.name.includes(courseFilter.keyword)) && (!courseFilter.term || course.term === courseFilter.term) && (!courseFilter.status || course.status === courseFilter.status)));
const filteredChapters = computed(() => (materialSummary.value.chapters || []).filter((chapter: any) => !chapterKeyword.value || chapter.title.includes(chapterKeyword.value)));
const filteredMaterials = computed(() => {
  let rows = materials.value.filter((item) => (!selectedChapterId.value || item.chapter_id === selectedChapterId.value) && (!materialFilter.keyword || item.title.includes(materialFilter.keyword)) && (!materialFilter.type || item.material_type === materialFilter.type) && (!materialFilter.status || materialRowStatus(item) === materialFilter.status));
  if (materialSort.value === "name") rows = [...rows].sort((a, b) => a.title.localeCompare(b.title));
  if (materialSort.value === "size") rows = [...rows].sort((a, b) => b.size_bytes - a.size_bytes);
  return rows;
});
const filteredLessons = computed(() => {
  const source = lessons.value.length ? lessons.value : (courseHome.value.lessons || []);
  const rows = source.filter((lesson: any) => (!lessonFilter.keyword || lesson.title.includes(lessonFilter.keyword)) && (!lessonFilter.chapter_id || lesson.chapter_id === lessonFilter.chapter_id) && (!lessonFilter.status || lesson.status === lessonFilter.status));
  if (lessonSort.value === "published") return [...rows].sort((a: any, b: any) => new Date(b.published_at || b.created_at || 0).getTime() - new Date(a.published_at || a.created_at || 0).getTime());
  if (lessonSort.value === "students") return [...rows].sort((a: any, b: any) => Number(b.learned_count || 0) - Number(a.learned_count || 0));
  return [...rows].sort((a: any, b: any) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
});
const lessonPageCount = computed(() => Math.max(1, Math.ceil(filteredLessons.value.length / lessonPageSize)));
const pagedLessons = computed(() => {
  const start = (lessonPage.value - 1) * lessonPageSize;
  return filteredLessons.value.slice(start, start + lessonPageSize);
});
watch(filteredLessons, (rows) => {
  const maxPage = Math.max(1, Math.ceil(rows.length / lessonPageSize));
  if (lessonPage.value > maxPage) lessonPage.value = maxPage;
});
watch([() => lessonFilter.keyword, () => lessonFilter.chapter_id, () => lessonFilter.status, lessonSort], () => { lessonPage.value = 1; });
const filteredStudents = computed(() => (studentPayload.value.items || []).filter((item: any) => {
  const nameMatch = !studentFilter.keyword || item.student.nickname.includes(studentFilter.keyword);
  const progressMatch = !studentFilter.progress || (studentFilter.progress === "none" ? item.progress_percent < 5 : studentFilter.progress === "done" ? item.progress_percent > 80 : item.progress_percent >= 5 && item.progress_percent <= 80);
  const activeMatch = !studentFilter.active || (studentFilter.active === "long" ? isLongInactive(item.last_study_at) : studentFilter.active === "active" ? !isLongInactive(item.last_study_at) : true);
  return nameMatch && progressMatch && activeMatch;
}));
const reminderTargetNames = computed(() => {
  const rows = studentPayload.value.items || [];
  const names = reminderTargetIds.value.map((id) => rows.find((item: any) => item.student.id === id)?.student.nickname || (studentDrawer.value?.student?.id === id ? studentDrawer.value.student.nickname : `学生${id}`));
  if (names.length <= 3) return names.join("、") || "未选择学生";
  return `${names.slice(0, 3).join("、")} 等 ${names.length} 人`;
});
const pages = computed<any[]>(() => materialDetail.value?.pages || []);
const currentPageIndex = computed(() => Math.max(0, pages.value.findIndex((page: any) => page.id === currentPageId.value)));
const activePage = computed(() => pages.value[currentPageIndex.value] || null);
const lessonPreviewActivePage = computed(() => lessonPreview.value?.pages?.find((page: any) => page.id === lessonPreviewPageId.value) || lessonPreview.value?.pages?.[0] || null);
const activePageText = computed(() => extractStructuredText(activePage.value?.page_text || "") || String(activePage.value?.page_text || "").trim());
const activePageHtml = computed(() => renderRichText(activePageText.value || "暂无页面内容"));
const lessonPreviewPageText = computed(() => extractStructuredText(lessonPreviewActivePage.value?.page_text || "") || String(lessonPreviewActivePage.value?.page_text || "").trim());
const lessonPreviewScriptText = computed(() => extractStructuredText(lessonPreviewActivePage.value?.script_text || lessonPreviewActivePage.value?.page_text || "") || String(lessonPreviewActivePage.value?.script_text || lessonPreviewActivePage.value?.page_text || "").trim());
const lessonPreviewPageHtml = computed(() => renderRichText(lessonPreviewPageText.value || "暂无页面内容"));
const lessonPreviewScriptHtml = computed(() => renderRichText(lessonPreviewScriptText.value || "暂无脚本"));
const reviewedCount = computed(() => pages.value.filter((page: any) => page.script_status === "ready").length);
const materialStatusCounts = computed<Record<string, number>>(() => courseHome.value.material_stats?.by_status || {});
const materialTotal = computed(() => {
  const statusTotal = Object.values(materialStatusCounts.value).reduce((sum, value) => sum + Number(value || 0), 0);
  return Number(courseHome.value.quick_counts?.material_count || statusTotal || 0);
});
const materialReadyCount = computed(() => Number(materialStatusCounts.value.ready || materialStatusCounts.value.success || 0));
const materialReadyPercent = computed(() => materialTotal.value ? Math.round((materialReadyCount.value / materialTotal.value) * 100) : 0);
const materialProgressTone = computed<"primary" | "success" | "warning" | "danger">(() => {
  if (!materialTotal.value) return "primary";
  if (materialReadyPercent.value >= 80) return "success";
  if (Number(materialStatusCounts.value.failed || 0) > 0) return "danger";
  return "warning";
});
const materialStatusCards = computed(() => [
  { key: "ready", label: "已解析", value: materialReadyCount.value, tone: "success", icon: CheckCircle },
  { key: "processing", label: "处理中", value: Number(materialStatusCounts.value.processing || 0), tone: "warning", icon: Clock },
  { key: "pending", label: "待处理", value: Number(materialStatusCounts.value.pending || materialStatusCounts.value.review || 0), tone: "primary", icon: FileText },
  { key: "failed", label: "失败", value: Number(materialStatusCounts.value.failed || 0), tone: "danger", icon: XCircle }
]);
const lessonAnalysisLabels = computed(() => (analysis.value.lesson_completion || []).map((item: any) => item.title));
const lessonAnalysisSeries = computed(() => [{ name: "完成率", data: (analysis.value.lesson_completion || []).map((item: any) => item.completion_rate || item.average_progress || 0), color: "#2E7D32" }]);
const analysisTimeLabels = computed(() => (analysis.value.study_time_series || []).map((item: any) => item.label));
const analysisTimeSeries = computed(() => [{ name: "分钟", data: (analysis.value.study_time_series || []).map((item: any) => item.minutes || 0), color: "#D94925" }]);
const weakLabels = computed(() => (analysis.value.weak_points || []).map((item: any) => item.knowledge_point));
const weakSeries = computed(() => [{ name: "错题", data: (analysis.value.weak_points || []).map((item: any) => item.wrong_count), color: "#C62828" }]);
const weakMax = computed(() => Math.max(1, ...(analysis.value.weak_points || []).map((item: any) => item.wrong_count || 0)));
const weakQuizPoints = computed(() => weakQuizData.value.weak_points || []);
const weakQuizAllSets = computed(() => weakQuizData.value.all_sets || []);
const weakQuizPointCount = computed(() => weakQuizPoints.value.length);
const selectedWeakQuizPoint = computed(() => weakQuizPoints.value[Math.min(weakQuizPointIndex.value, Math.max(weakQuizPoints.value.length - 1, 0))] || null);
const weakQuizTypeTotal = computed(() => weakQuestionTypes.reduce((sum, item) => sum + Number(weakQuizForm.question_type_counts[item.value] || 0), 0));
const weakQuizFormValid = computed(() => Number(weakQuizForm.question_count || 0) > 0 && weakQuizTypeTotal.value === Number(weakQuizForm.question_count || 0));
const scoreLabels = computed(() => (analysis.value.score_distribution || []).map((item: any) => item.range));
const scoreSeries = computed(() => [{ name: "人数", data: (analysis.value.score_distribution || []).map((item: any) => item.count), color: "#0277BD" }]);
const registeredDays = computed(() => props.user.created_at ? Math.max(1, Math.floor((Date.now() - new Date(props.user.created_at).getTime()) / 86400000)) : 1);
const passwordStrength = computed(() => Math.min(100, Math.max(20, passwordForm.new_password.length * 10)));
const teacherName = computed(() => profileForm.nickname || props.user.nickname);
const teacherAvatarUrl = computed(() => profileForm.avatar_url || props.user.avatar_url || "");

watch(activePage, (page) => {
  scriptDraft.value = page?.script_text || "";
  scriptUndoStack.value = [];
  scriptRedoStack.value = [];
}, { immediate: true });
watch(weakQuizPoints, (points) => {
  if (!points.length) {
    weakQuizPointIndex.value = 0;
    return;
  }
  if (weakQuizPointIndex.value >= points.length) weakQuizPointIndex.value = points.length - 1;
});
watch(() => props.pageKey, (key) => { active.value = key || "teacherDashboard"; loadActive(); });
watch(currentCourseId, (id) => { if (id) localStorage.setItem("teacher_current_course_id", String(id)); });
watch(sidebarCollapsed, (value) => { localStorage.setItem("teacher_sidebar_collapsed", value ? "1" : "0"); });

async function run<T>(task: () => Promise<T>, ok?: string) { try { const data = await task(); if (ok) emit("notice", "success", ok); return data; } catch (error) { emit("notice", "error", (error as Error).message); return null; } }
function isPending(key: string) { return pendingActions.has(key); }
async function withAction<T>(key: string, task: () => Promise<T>, ok?: string) {
  if (pendingActions.has(key)) return null;
  pendingActions.add(key);
  try {
    return await run(task, ok);
  } finally {
    pendingActions.delete(key);
  }
}
async function go(key: string) {
  courseMenuOpen.value = false;
  userMenuOpen.value = false;
  teacherNoticeOpen.value = false;
  if (courseOperationPages.has(key) && currentCourse.value && !isCourseOperable(currentCourse.value)) {
    emit("notice", "warning", "课程已下架，请先上架后再操作");
    key = "teacherCourseHome";
  }
  if (key !== "teacherPpt") {
    presentationMode.value = false;
    slideOverviewOpen.value = false;
    stageFocused.value = false;
  }
  await router.push(routeByPage[key] || "/teacher");
}
function toggleCourseMenu() {
  userMenuOpen.value = false;
  teacherNoticeOpen.value = false;
  courseMenuOpen.value = !courseMenuOpen.value;
}
function openNotifications() {
  courseMenuOpen.value = false;
  userMenuOpen.value = false;
  teacherNoticeOpen.value = !teacherNoticeOpen.value;
}
async function openTeacherNotification(item: any) {
  emit("notice", item.type?.includes("failed") ? "warning" : "success", item.message ? `${item.title}：${item.message}` : item.title);
  if (item.resource_type === "quiz") {
    teacherNoticeOpen.value = false;
    const courseId = Number(item.course_id || 0);
    if (courseId && currentCourseId.value !== courseId) currentCourseId.value = courseId;
    await go("teacherWeakQuizzes");
    const quizId = Number(item.resource_id || 0);
    if (quizId) await openGeneratedWeakQuiz(quizId);
  }
}
async function markTeacherNotificationsRead(item?: any) {
  const ids = item
    ? [String(item.id || "").trim()].filter(Boolean)
    : teacherNotifications.value.filter((notice: any) => notice.unread).map((notice: any) => String(notice.id || "").trim()).filter(Boolean);
  if (!ids.length || notificationReading.value) return;
  notificationReading.value = true;
  try {
    const updated = await api.post<any[]>("/teacher/notifications/read", { ids });
    dashboard.value = { ...dashboard.value, notifications: updated || teacherNotifications.value.map((notice: any) => (ids.includes(String(notice.id || "")) ? { ...notice, unread: false } : notice)) };
  } catch (error) {
    emit("notice", "error", (error as Error).message);
  } finally {
    notificationReading.value = false;
  }
}
function openHelp() {
  courseMenuOpen.value = false;
  userMenuOpen.value = false;
  teacherNoticeOpen.value = false;
  helpOpen.value = true;
}
async function loadCourses() { courses.value = (await run(() => api.get<any[]>("/teacher/courses"))) || []; if ((!currentCourseId.value || !courses.value.some((course) => course.id === currentCourseId.value)) && courses.value[0]) currentCourseId.value = courses.value[0].id; }
async function loadDashboard() { dashboard.value = (await run(() => api.get("/teacher/dashboard"))) || {}; }
async function loadCourseHome() { if (!currentCourse.value) return; courseHome.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/home`))) || {}; lessons.value = courseHome.value.lessons || []; }
async function loadMaterials() {
  if (!currentCourse.value) return;
  materialSummary.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/materials/summary`))) || {};
  const rows = (await run(() => api.get<any[]>("/materials", { course_id: currentCourse.value!.id, keyword: materialFilter.keyword, category: "" }))) || [];
  materials.value = applyMaterialProcessingOverrides(rows);
}
async function loadLessons() {
  if (!currentCourse.value) return;
  const result = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/lessons`))) as { items?: any[] } | undefined;
  lessons.value = result?.items || [];
}
async function loadStudents() { if (!currentCourse.value) return; studentPayload.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/students`))) || { stats: {}, items: [] }; }
function analysisDays() { return analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; }
function analysisCacheKey() { return currentCourse.value ? `${currentCourse.value.id}:${analysisDays()}` : ""; }
async function loadAnalysis(force = false) {
  if (!currentCourse.value) return;
  const key = analysisCacheKey();
  const cached = analysisCache[key];
  if (!force && cached && Date.now() - cached.fetchedAt < 5 * 60 * 1000) {
    analysis.value = cached.data;
    return;
  }
  const data = await run(() => api.get(`/teacher/courses/${currentCourse.value!.id}/analysis`, { days: analysisDays() }));
  analysis.value = data || {};
  if (data) analysisCache[key] = { fetchedAt: Date.now(), data };
}
async function refreshAnalysis() { await withAction("refresh-analysis", () => loadAnalysis(true)); }
async function setAnalysisRange(value: string) {
  if (analysisRange.value === value) return;
  analysisRange.value = value;
  await withAction("analysis-range", () => loadAnalysis());
}
function applyTeacherProfile(data: any) {
  if (!data) return;
  Object.assign(profileForm, {
    nickname: data.user?.nickname || profileForm.nickname,
    avatar_url: data.user?.avatar_url || "",
    bio: data.user?.bio || "",
    organization: data.teacher_profile?.organization || "",
    department: data.teacher_profile?.department || "",
  });
  if (data.user) emit("authed", {
    ...props.user,
    nickname: data.user.nickname || props.user.nickname,
    avatar_url: data.user.avatar_url || null,
    bio: data.user.bio || null,
    updated_at: data.user.updated_at || props.user.updated_at,
  });
}
async function loadTeacherProfile() { const data = await run<any>(() => api.get("/teacher/profile")); if (!data) return; applyTeacherProfile(data); if (Array.isArray(data.notification_settings)) noticeSettings.splice(0, noticeSettings.length, ...data.notification_settings); }
async function loadActive() {
  pageLoading.value = !initialPageLoading.value;
  try {
    if (courseOperationPages.has(active.value) && currentCourse.value && !currentCourseOperable.value) {
      emit("notice", "warning", "课程已下架，请先上架后再操作");
      active.value = "teacherCourseHome";
      await go("teacherCourseHome");
      return;
    }
    if (active.value === "teacherDashboard") await loadDashboard();
    if (active.value === "teacherCourses") await loadCourses();
    if (active.value === "teacherCourseHome") await loadCourseHome();
    if (active.value === "teacherMaterials") await loadMaterials();
    if (active.value === "teacherLessons") await loadLessons();
    if (active.value === "teacherStudents") await loadStudents();
    if (active.value === "teacherAnalytics") await loadAnalysis();
    if (active.value === "teacherWeakQuizzes") await loadWeakQuizzes();
    if (active.value === "teacherProfile") await loadTeacherProfile();
  } finally {
    pageLoading.value = false;
    initialPageLoading.value = false;
  }
}
async function selectCourse(id: number, target = active.value) {
  await withAction(`select-course-${id}`, async () => {
    currentCourseId.value = id;
    courseMenuOpen.value = false;
    await loadCourseHome();
    await go(target);
  });
}
async function enterRecentCourse() { if (currentCourse.value) await selectCourse(currentCourse.value.id, "teacherCourseHome"); else await go("teacherCourses"); }
function resetCourseCoverSelection() {
  if (courseCoverPreview.value && courseCoverPreview.value.startsWith("blob:")) URL.revokeObjectURL(courseCoverPreview.value);
  courseCoverFile.value = null;
  courseCoverPreview.value = "";
  if (courseCoverInput.value) courseCoverInput.value.value = "";
}
function newCourse() { removedChapterIds.value = []; resetCourseCoverSelection(); Object.assign(courseForm, { id: 0, name: "", description: "", term: "2026春", cover_url: "", cover_color: "#121614", allow_leave: true, ai_qa: true, quiz_enabled: true, allow_general_ai_answer: false, chapters: [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] }); go("teacherCourseForm"); }
async function editCourse(course: any) {
  if (!isCourseOperable(course)) return emit("notice", "warning", "课程已下架，请先上架后再编辑");
  const detail = await withAction<CourseDetail>(`edit-course-${course.id}`, () => api.get(`/courses/${course.id}`));
  removedChapterIds.value = [];
  resetCourseCoverSelection();
  Object.assign(courseForm, { id: course.id, name: course.name, description: course.description || "", term: course.term, cover_url: course.cover_url || "", cover_color: course.cover_color || "#121614", allow_general_ai_answer: !!(detail?.course?.allow_general_ai_answer ?? course.allow_general_ai_answer), chapters: (detail?.chapters || []).length ? detail!.chapters.map((chapter: any) => ({ ...chapter, local_id: chapter.id })) : [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] });
  go("teacherCourseForm");
}
function markFreshChapter(localId: number) {
  freshChapterId.value = localId;
  window.clearTimeout(freshChapterTimer);
  freshChapterTimer = window.setTimeout(() => { freshChapterId.value = null; }, 900);
}
function markFreshMaterialChapter(id?: number | null) {
  if (!id) return;
  freshMaterialChapterId.value = id;
  selectedChapterId.value = id;
  window.clearTimeout(freshMaterialChapterTimer);
  freshMaterialChapterTimer = window.setTimeout(() => { freshMaterialChapterId.value = null; }, 1100);
}
function addDraftChapter() {
  const localId = Date.now() + Math.floor(Math.random() * 1000);
  courseForm.chapters.push({ local_id: localId, id: 0, title: `第${courseForm.chapters.length + 1}章`, order_index: courseForm.chapters.length + 1 });
  markFreshChapter(localId);
}
function removeDraftChapter(index: number) { const [chapter] = courseForm.chapters.splice(index, 1); if (chapter?.id) removedChapterIds.value.push(chapter.id); }
function pickCourseCover(event: Event) {
  const file = ((event.target as HTMLInputElement).files || [])[0];
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    emit("notice", "warning", "请上传图片文件");
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    emit("notice", "warning", "课程封面不能超过 8MB");
    return;
  }
  resetCourseCoverSelection();
  courseCoverFile.value = file;
  courseCoverPreview.value = URL.createObjectURL(file);
}
async function uploadCourseCover(courseId: number) {
  if (!courseCoverFile.value) return null;
  const form = new FormData();
  form.set("file", courseCoverFile.value);
  return await run<Course>(() => api.post(`/courses/${courseId}/cover`, form), "封面已上传");
}
async function saveCourse() {
  if (!courseForm.name.trim() || !courseForm.term.trim()) return emit("notice", "warning", "课程必填");
  const originalCourse = courses.value.find((course) => Number(course.id) === Number(courseForm.id));
  if (courseForm.id && originalCourse && !isCourseOperable(originalCourse)) return emit("notice", "warning", "课程已下架，请先上架后再编辑");
  await withAction("save-course", async () => {
    const payload = { name: courseForm.name, description: courseForm.description, term: courseForm.term, cover_url: courseForm.cover_url, cover_color: courseForm.cover_color, allow_general_ai_answer: courseForm.allow_general_ai_answer };
    const course = courseForm.id ? await run<Course>(() => api.patch(`/courses/${courseForm.id}`, payload), "已保存") : await run<Course>(() => api.post("/courses", payload), "已创建");
    if (!course) return;
    currentCourseId.value = course.id;
    const coverCourse = await uploadCourseCover(course.id);
    if (coverCourse?.cover_url) courseForm.cover_url = coverCourse.cover_url;
    resetCourseCoverSelection();
    for (const chapterId of removedChapterIds.value) await run(() => api.delete(`/teacher/courses/${course.id}/chapters/${chapterId}`));
    removedChapterIds.value = [];
    for (const chapter of courseForm.chapters) {
      if (!chapter.title.trim()) continue;
      if (chapter.id) await run(() => api.patch(`/teacher/courses/${course.id}/chapters/${chapter.id}`, { title: chapter.title, order_index: chapter.order_index }));
      else await run(() => api.post(`/courses/${course.id}/chapters`, { title: chapter.title, description: "", order_index: chapter.order_index }));
    }
    await loadCourses();
    await selectCourse(course.id, "teacherCourseHome");
  });
}
async function toggleCourseStatus(course: any) {
  if (!course?.id) return;
  const activating = !isCourseOperable(course);
  if (!activating && !window.confirm(`确定下架“${course.name}”？下架后教师需重新上架才能继续管理，新学生也不能加入。`)) return;
  await withAction(`toggle-course-${course.id}`, async () => {
    const updated = await run<Course>(() => api.post(`/courses/${course.id}/${activating ? "activate" : "deactivate"}`), activating ? "课程已上架" : "课程已下架");
    if (!updated) return;
    courses.value = courses.value.map((item) => Number(item.id) === Number(updated.id) ? { ...item, ...updated } : item);
    if (currentCourseId.value === updated.id) {
      if (courseHome.value.course) courseHome.value = { ...courseHome.value, course: { ...courseHome.value.course, ...updated } };
      await loadCourseHome();
      if (!activating && courseOperationPages.has(active.value)) await go("teacherCourseHome");
    }
    await loadCourses();
    await loadDashboard();
  });
}
async function deleteCourse() {
  if (!courseForm.id) return;
  const originalCourse = courses.value.find((course) => Number(course.id) === Number(courseForm.id));
  if (originalCourse && !isCourseOperable(originalCourse)) return emit("notice", "warning", "课程已下架，请先上架后再删除");
  confirmDeleteCourseOpen.value = true;
}
async function confirmDeleteCourse() {
  if (!courseForm.id) return;
  confirmDeleteCourseOpen.value = false;
  await withAction("delete-course", async () => {
    await run(() => api.delete(`/teacher/courses/${courseForm.id}`), "已删除");
    currentCourseId.value = 0;
    await loadCourses();
    await go("teacherCourses");
  });
}
function materialChapterRows() {
  const rows = [...(materialSummary.value.chapters || []), ...(courseHome.value.chapters || [])];
  const seen = new Set<number>();
  return rows.filter((chapter: any) => {
    const id = Number(chapter?.id || 0);
    if (!id || seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}
function nextChapterOrderIndex() {
  return Math.max(0, ...materialChapterRows().map((chapter: any) => Number(chapter.order_index || 0))) + 1;
}
function openAddChapterModal() {
  if (!ensureCurrentCourseOperable()) return;
  chapterNameDraft.value = `第${nextChapterOrderIndex()}章`;
  chapterNameOpen.value = true;
  nextTick(() => {
    chapterNameInput.value?.focus();
    chapterNameInput.value?.select();
  });
}
async function addChapterFromTree() {
  if (!ensureCurrentCourseOperable()) return;
  const title = chapterNameDraft.value.trim();
  if (!title) return emit("notice", "warning", "请输入章节名称");
  const existing = [...(materialSummary.value.chapters || []), ...(courseHome.value.chapters || [])];
  if (existing.some((chapter: any) => String(chapter.title || "").trim() === title)) return emit("notice", "warning", "章节名称已存在");
  await withAction("add-tree-chapter", async () => {
    const chapter = await run<any>(() => api.post(`/courses/${currentCourse.value!.id}/chapters`, { title, description: "", order_index: nextChapterOrderIndex() }), "已添加");
    chapterNameOpen.value = false;
    chapterNameDraft.value = "";
    await loadMaterials();
    await loadCourseHome();
    markFreshMaterialChapter(chapter?.id || (materialSummary.value.chapters || []).find((item: any) => item.title === title)?.id);
  });
}
async function deleteChapterFromTree(chapter: any) {
  if (!ensureCurrentCourseOperable() || !chapter?.id) return;
  const linkedCount = Number(chapter.count || 0);
  const message = linkedCount > 0
    ? `确定删除“${chapter.title}”？该章节下 ${linkedCount} 份资料会保留并改为未分章。`
    : `确定删除“${chapter.title}”？`;
  if (!window.confirm(message)) return;
  await withAction(`delete-chapter-${chapter.id}`, async () => {
    await run(() => api.delete(`/teacher/courses/${currentCourse.value!.id}/chapters/${chapter.id}`), "已删除章节");
    if (selectedChapterId.value === chapter.id) selectedChapterId.value = 0;
    uploadQueue.value = uploadQueue.value.map((item) => item.chapter_id === chapter.id ? { ...item, chapter_id: 0 } : item);
    await loadMaterials();
    await loadCourseHome();
  });
}
function optionLabel(index: number) { return String.fromCharCode(65 + index); }
function normalizeAnswerPayload(questionType: string, referenceAnswer: any) {
  const value = referenceAnswer && typeof referenceAnswer === "object" && !Array.isArray(referenceAnswer)
    ? referenceAnswer.value ?? referenceAnswer.answer ?? referenceAnswer.correct_answer ?? referenceAnswer.correct ?? referenceAnswer.option_index ?? referenceAnswer.index ?? referenceAnswer.key ?? referenceAnswer.text ?? referenceAnswer.choice ?? referenceAnswer.correct_option ?? referenceAnswer.judge
    : referenceAnswer;
  if (questionType === "judge") return { value: value === true || value === "true" || value === "正确" || value === "对" || value === 0 || value === "0" };
  if (questionType === "multiple_choice") {
    const values = Array.isArray(value) ? value : String(value ?? "").split(/[，,；;、\s]/).filter(Boolean);
    return { value: values.map((item: any) => Number.isNaN(Number(item)) ? item : Number(item)) };
  }
  if (questionType === "single_choice") return { value: value ?? 0 };
  const keywords = Array.isArray(referenceAnswer?.keywords) ? referenceAnswer.keywords : Array.isArray(value) ? value : String(value || "").split(/[，,；;、]/).map((item) => item.trim()).filter(Boolean);
  return { keywordsText: keywords.join("，") };
}
function normalizeEditorQuestion(item: any = {}) {
  const type = item.question_type || "single_choice";
  const options = Array.isArray(item.options) && item.options.length ? [...item.options] : type === "judge" ? ["正确", "错误"] : ["", "", "", ""];
  return {
    local_id: item.id || Date.now() + Math.floor(Math.random() * 1000),
    id: item.id || 0,
    chapter_id: item.chapter_id || null,
    knowledge_point_id: item.knowledge_point_id || null,
    knowledge_point_name: item.knowledge_point_name || null,
    question_type: type,
    stem: item.stem || "",
    options,
    reference_answer: normalizeAnswerPayload(type, item.reference_answer),
    explanation: item.explanation || "",
    score: Number(item.score || 10),
    difficulty: item.difficulty || "standard",
  };
}
function openQuizEditor(detail: any) {
  if (!detail?.quiz) return;
  quizEditor.id = detail.quiz.id;
  quizEditor.status = detail.quiz.status;
  quizEditor.title = detail.quiz.title || "";
  quizEditor.description = detail.quiz.description || "";
  quizEditor.generated = Boolean(detail.quiz.metadata_json?.generated);
  quizEditor.questions = (detail.questions || []).map((item: any) => normalizeEditorQuestion(item));
  quizEditorOpen.value = true;
}
function difficultyText(value?: string) {
  const key = String(value || "").toLowerCase();
  return questionDifficultyTextMap[key] || String(value || "");
}
function difficultyTagClass(value?: string) {
  const key = String(value || "").toLowerCase();
  if (key === "easy") return "tag-success";
  if (key === "hard") return "tag-warning";
  return "";
}
async function regenerateEditorQuestion(question: any) {
  if (!quizEditor.id || !question?.id) return;
  await withAction(`regen-question-${question.id}`, async () => {
    const data = await api.post<any>(`/learning/quizzes/${quizEditor.id}/questions/${question.id}/regenerate`);
    if (!data) return;
    // 用 indexOf 而非渲染时下标：请求期间题目可能被删除/移动，避免替换错位。
    const index = quizEditor.questions.indexOf(question);
    if (index < 0) return;
    quizEditor.questions.splice(index, 1, normalizeEditorQuestion(data));
  }, "已为该题生成新题目");
}
function addEditorQuestion() { quizEditor.questions.push(normalizeEditorQuestion()); }
function removeEditorQuestion(index: number) {
  if (quizEditor.questions.length <= 1) return emit("notice", "warning", "至少保留一道题");
  quizEditor.questions.splice(index, 1);
}
function addEditorOption(question: any) { question.options.push(""); }
function removeEditorOption(question: any, index: number) {
  if (question.options.length <= 2) return;
  question.options.splice(index, 1);
  if (Array.isArray(question.reference_answer.value)) {
    question.reference_answer.value = question.reference_answer.value.filter((i: number) => i !== index).map((i: number) => (i > index ? i - 1 : i));
  } else {
    const cur = Number(question.reference_answer.value || 0);
    if (index < cur) question.reference_answer.value = cur - 1;
    else if (index === cur) question.reference_answer.value = 0;
    if (Number(question.reference_answer.value) >= question.options.length) question.reference_answer.value = 0;
  }
}
function toggleEditorMultiAnswer(question: any, index: number) {
  const values = Array.isArray(question.reference_answer.value) ? question.reference_answer.value : [];
  question.reference_answer.value = values.includes(index) ? values.filter((item: number) => item !== index) : [...values, index];
}
function changeEditorQuestionType(question: any) {
  question.reference_answer = normalizeAnswerPayload(question.question_type, question.reference_answer);
  if (question.question_type === "judge") question.options = ["正确", "错误"];
  if ((question.question_type === "single_choice" || question.question_type === "multiple_choice") && (!Array.isArray(question.options) || question.options.length < 2)) question.options = ["", "", "", ""];
}
function serializeEditorQuestion(question: any) {
  let reference_answer: any = question.reference_answer;
  let options: any[] | null = null;
  if (question.question_type === "single_choice") {
    options = question.options.map((item: string) => item.trim()).filter(Boolean);
    reference_answer = { value: Number(question.reference_answer.value || 0) };
  } else if (question.question_type === "multiple_choice") {
    options = question.options.map((item: string) => item.trim()).filter(Boolean);
    const values = Array.isArray(question.reference_answer.value) ? question.reference_answer.value : [question.reference_answer.value];
    reference_answer = { values };
  } else if (question.question_type === "judge") {
    options = ["正确", "错误"];
    reference_answer = { value: question.reference_answer.value === true || question.reference_answer.value === "true" };
  } else {
    const keywords = String(question.reference_answer.keywordsText || "").split(/[，,；;、]/).map((item) => item.trim()).filter(Boolean);
    reference_answer = { keywords };
  }
  return {
    id: question.id || undefined,
    chapter_id: question.chapter_id || undefined,
    knowledge_point_id: question.knowledge_point_id || undefined,
    question_type: question.question_type,
    stem: question.stem,
    options,
    reference_answer,
    explanation: question.explanation,
    score: Number(question.score || 10),
    difficulty: question.difficulty || "standard",
  };
}
async function saveQuizEditor() {
  if (!ensureCurrentCourseOperable()) return null;
  if (!quizEditor.id || quizEditorSaving.value) return null;
  quizEditorSaving.value = true;
  try {
    const detail = await run<any>(() => api.put(`/learning/quizzes/${quizEditor.id}`, {
      title: quizEditor.title,
      description: quizEditor.description,
      questions: quizEditor.questions.map(serializeEditorQuestion),
    }), "测验已保存");
    if (detail) openQuizEditor(detail);
    return detail;
  } finally {
    quizEditorSaving.value = false;
  }
}
async function publishQuizEditor() {
  if (!ensureCurrentCourseOperable()) return;
  if (!quizEditor.id || quizEditorPublishing.value) return;
  quizEditorPublishing.value = true;
  try {
    const detail = await saveQuizEditor();
    if (!detail) return;
    const quiz = await run<any>(() => api.post(`/learning/quizzes/${quizEditor.id}/publish`), "已发布给学生");
    if (quiz) {
      quizEditor.status = quiz.status;
      quizEditorOpen.value = false;
      if (active.value === "teacherWeakQuizzes") await loadWeakQuizzes(true);
      else await loadAnalysis(true);
    }
  } finally {
    quizEditorPublishing.value = false;
  }
}
async function loadWeakQuizzes(force = false) {
  if (!currentCourse.value) return;
  if (!force && weakQuizData.value.course_id === currentCourse.value.id && weakQuizData.value.loaded) return;
  await withAction("load-weak-quizzes", async () => {
    const data = await run<any>(() => api.get("/learning/teacher/weak-quizzes", { course_id: currentCourse.value!.id }));
    weakQuizData.value = { ...(data || { stats: {}, weak_points: [], all_sets: [] }), course_id: currentCourse.value!.id, loaded: true };
    if (weakQuizSelectedSetId.value) {
      const exists = [...weakQuizAllSets.value, ...weakQuizPoints.value.flatMap((point: any) => point.quiz_sets || [])].some((quiz: any) => quiz.id === weakQuizSelectedSetId.value);
      if (!exists) {
        weakQuizSelectedSetId.value = 0;
        weakQuizAttemptDetail.value = null;
      }
    }
  });
}
function weakQuizTypeCountsPayload() {
  const counts: Record<string, number> = {};
  for (const item of weakQuestionTypes) {
    const count = Number(weakQuizForm.question_type_counts[item.value] || 0);
    if (count > 0) counts[item.value] = count;
  }
  return counts;
}
function setWeakQuizPointIndex(index: number) {
  const total = weakQuizPoints.value.length;
  weakQuizPointIndex.value = total ? (index + total) % total : 0;
}
function stepWeakQuizPoint(offset: number) {
  setWeakQuizPointIndex(weakQuizPointIndex.value + offset);
}
function syncWeakQuizPointIndexForQuiz(quizId: number) {
  const index = weakQuizPoints.value.findIndex((point: any) => (point.quiz_sets || []).some((quiz: any) => Number(quiz.id) === Number(quizId)));
  if (index >= 0) weakQuizPointIndex.value = index;
}
function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
function generationTaskId(payload: any) {
  return Number(payload?.task_id || payload?.generation_task?.id || 0);
}
function generatedQuizId(payload: any) {
  return Number(payload?.id || payload?.target_id || payload?.detail?.quiz_id || payload?.generation_task?.target_id || 0);
}
function generationTaskStatus(payload: any) {
  return String(payload?.task_status || payload?.status || payload?.generation_task?.status || "");
}
async function waitForGeneratedQuiz(initial: any) {
  if (initial?.id) return initial;
  const taskId = generationTaskId(initial);
  if (!taskId) return null;
  emit("notice", "info", "薄弱题目已进入生成队列，完成后将自动打开审核弹窗");
  for (let attempt = 0; attempt < weakQuizTaskMaxPolls; attempt += 1) {
    const task = await api.get<any>(`/learning/generation-tasks/${taskId}`);
    if (task?.id) return task;
    const status = generationTaskStatus(task);
    if (status === "failed") {
      const message = String(task?.detail?.error || task?.detail?.notification?.message || "薄弱题目生成失败");
      throw new Error(message);
    }
    const quizId = generatedQuizId(task);
    if (status === "ready" && quizId) return { id: quizId };
    await wait(weakQuizTaskPollIntervalMs);
  }
  emit("notice", "info", "薄弱题目仍在生成中，完成后可从通知或刷新列表查看");
  return null;
}
async function openGeneratedWeakQuiz(quizOrId: any) {
  const quizId = Number(typeof quizOrId === "number" ? quizOrId : quizOrId?.id || generatedQuizId(quizOrId));
  if (!quizId) return;
  await loadWeakQuizzes(true);
  await selectWeakQuizSet({ id: quizId });
  const detail = await run<any>(() => api.get(`/learning/quizzes/${quizId}`));
  if (detail) openQuizEditor(detail);
}
async function generateTeacherWeakQuiz(point?: any) {
  if (!ensureCurrentCourseOperable()) return;
  if (!weakQuizFormValid.value) return emit("notice", "warning", "题型数量合计必须等于总题量");
  if (weakQuizGenerating.value) return emit("notice", "info", "正在生成测验，请稍候");
  const mode: "all" | "single" = point ? "single" : "all";
  const title = point ? `${point.knowledge_point}薄弱点专项测验` : "薄弱知识点综合测验";
  weakQuizGenerating.value = true;
  weakQuizGeneratingTopic.value = point?.knowledge_point || "";
  weakQuizGenerationMode.value = mode;
  weakQuizStatus.value = point ? `正在生成“${point.knowledge_point}”专项题...` : "正在生成全部薄弱知识点综合测验...";
  emit("notice", "info", weakQuizStatus.value);
  try {
    const quiz = await run<any>(() => api.post("/learning/teacher/weak-quizzes/generate", {
      course_id: currentCourse.value!.id,
      weak_point_id: point?.knowledge_point_id || undefined,
      all_weak_points: !point,
      title,
      question_count: Number(weakQuizForm.question_count || 0),
      question_type_counts: weakQuizTypeCountsPayload(),
      difficulty: weakQuizForm.difficulty || "mixed",
    }));
    if (!quiz) return;
    const generatedQuiz = await waitForGeneratedQuiz(quiz);
    if (!generatedQuiz) {
      await loadDashboard();
      return;
    }
    await openGeneratedWeakQuiz(generatedQuiz);
    await loadDashboard();
    emit("notice", "success", "薄弱题目已生成，请审核后发布");
  } catch (error) {
    emit("notice", "error", (error as Error).message);
  } finally {
    weakQuizGenerating.value = false;
    weakQuizGeneratingTopic.value = "";
    weakQuizGenerationMode.value = "";
    weakQuizStatus.value = "";
  }
}
async function selectWeakQuizSet(quiz: any) {
  if (!quiz?.id) return;
  weakQuizSelectedSetId.value = quiz.id;
  syncWeakQuizPointIndexForQuiz(quiz.id);
  weakQuizAttemptDetail.value = await run<any>(() => api.get(`/learning/teacher/weak-quizzes/${quiz.id}/attempts`));
}
async function openWeakQuizEditor() {
  const quizId = weakQuizAttemptDetail.value?.quiz?.id || weakQuizSelectedSetId.value;
  if (!quizId) return;
  const detail = await run<any>(() => api.get(`/learning/quizzes/${quizId}`));
  if (detail) openQuizEditor(detail);
}
function questionTypeText(type?: string) {
  return weakQuestionTypes.find((item) => item.value === type)?.label || String(type || "-");
}
async function refreshMaterials() { await withAction("filter-materials", loadMaterials); }
async function openUploadModal() {
  if (!ensureCurrentCourseOperable()) return;
  uploadOpen.value = true;
  if (!currentCourse.value) return;
  await withAction("load-upload-chapters", async () => {
    await Promise.all([loadMaterials(), loadCourseHome()]);
  });
}
function materialRowStatus(item: any) {
  if (isMaterialProcessing(item)) return "processing";
  if (isMaterialPending(item)) return "pending";
  return String(item?.parse_status || "");
}
function isMaterialPending(item: any) {
  return String(item?.parse_status || "") === "pending" || String(item?.vector_status || "") === "pending";
}
function isMaterialProcessing(item: any) {
  return String(item?.parse_status || "") === "processing" || String(item?.vector_status || "") === "processing";
}
function isMaterialRetryBlocked(item: any) {
  return isMaterialPending(item) || isMaterialProcessing(item);
}
function materialRetryActionText(item: any) {
  if (isMaterialProcessing(item)) return "解析中";
  if (isMaterialPending(item)) return "待处理";
  return "重新解析";
}
function markMaterialReprocessing(id: number) {
  materialProcessingOverrides[id] = { startedAt: Date.now(), seenProcessing: false };
  materials.value = materials.value.map((item) => Number(item.id) === id ? { ...item, parse_status: "processing", vector_status: "processing" } : item);
}
function applyMaterialProcessingOverrides(rows: any[]) {
  const now = Date.now();
  const activeIds = new Set(rows.map((item) => Number(item.id)));
  Object.keys(materialProcessingOverrides).forEach((key) => {
    if (!activeIds.has(Number(key))) delete materialProcessingOverrides[Number(key)];
  });
  return rows.map((item) => {
    const id = Number(item.id);
    const override = materialProcessingOverrides[id];
    if (!override) return item;
    const remoteProcessing = item.parse_status === "processing" || item.vector_status === "processing";
    const remoteTerminal = ["ready", "failed"].includes(String(item.parse_status)) && ["ready", "failed"].includes(String(item.vector_status || item.parse_status));
    if (remoteProcessing) {
      override.seenProcessing = true;
      return { ...item, parse_status: "processing", vector_status: "processing" };
    }
    if (remoteTerminal && (override.seenProcessing || now - override.startedAt > 6000)) {
      delete materialProcessingOverrides[id];
      return item;
    }
    return { ...item, parse_status: "processing", vector_status: "processing" };
  });
}
function clearMaterialRefreshTimers() {
  materialRefreshTimers.forEach((timer) => window.clearTimeout(timer));
  materialRefreshTimers = [];
}
function scheduleMaterialRefreshes() {
  clearMaterialRefreshTimers();
  // 持续退避轮询直到没有 processing/pending 的资料（或 15 分钟上限）。
  // 原来只固定刷 3 次（3.5s/12s/30s），而完整流水线（解析→讲稿→TTS→向量→教学产物）常见 2-5 分钟，
  // 第三次刷新后状态就永远停在 processing，除非用户手动刷新页面。
  const startedAt = Date.now();
  const maxDurationMs = 15 * 60 * 1000;
  const nextDelay = (elapsedMs: number) => (elapsedMs < 30000 ? 3500 : elapsedMs < 120000 ? 8000 : 15000);
  const poll = async () => {
    if (!currentCourse.value) return;
    await loadMaterials();
    await loadCourseHome();
    const stillProcessing = materials.value.some(
      (item) => ["processing", "pending"].includes(String(item.parse_status)) || String(item.vector_status) === "processing",
    );
    const elapsed = Date.now() - startedAt;
    if (stillProcessing && elapsed < maxDurationMs) {
      const timer = window.setTimeout(poll, nextDelay(elapsed));
      materialRefreshTimers.push(timer);
    }
  };
  const timer = window.setTimeout(poll, 3500);
  materialRefreshTimers.push(timer);
}
function closeUploadModal() {
  if (isPending("upload-materials")) return;
  uploadOpen.value = false;
}
function uploadItemTone(item: UploadQueueItem) {
  if (item.status === "failed") return "danger";
  if (item.status === "uploaded") return "success";
  return "primary";
}
function uploadItemText(item: UploadQueueItem) {
  if (item.status === "uploaded") return "已提交解析";
  if (item.status === "uploading") return item.progress > 0 ? `上传中 ${item.progress}%` : "上传中";
  if (item.status === "failed") return item.error || "上传失败";
  return "待上传";
}
function pickUploadFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!files.length) return;
  const start = Date.now() + uploadQueue.value.length;
  uploadQueue.value = [
    ...uploadQueue.value,
    ...files.map((file, index) => ({
      id: start + index,
      file,
      chapter_id: selectedChapterId.value,
      category: "courseware",
      progress: 0,
      status: "pending" as const,
      error: "",
    })),
  ];
  input.value = "";
}
function removeUpload(id: number) { uploadQueue.value = uploadQueue.value.filter((item) => item.id !== id); }
async function uploadMaterials() {
  if (!ensureCurrentCourseOperable()) return;
  await withAction("upload-materials", async () => {
    if (!currentCourse.value) return;
    let successCount = 0;
    let failureCount = 0;
    for (const item of uploadQueue.value) {
      item.progress = 0;
      item.status = "uploading";
      item.error = "";
      const form = new FormData();
      form.set("course_id", String(currentCourse.value.id));
      form.set("title", item.file.name.replace(/\.[^.]+$/, ""));
      form.set("category", item.category);
      if (item.chapter_id) form.set("chapter_id", String(item.chapter_id));
      form.set("file", item.file);
      try {
        await api.upload("/materials", form, {
          onProgress: ({ percent }) => {
            item.progress = percent;
          },
        });
        item.progress = 100;
        item.status = "uploaded";
        successCount += 1;
      } catch (error) {
        item.status = "failed";
        item.error = (error as Error).message;
        failureCount += 1;
      }
    }
    if (successCount) {
      await loadMaterials();
      await loadCourseHome();
      scheduleMaterialRefreshes();
    }
    if (!failureCount) {
      emit("notice", "success", successCount === 1 ? "资料已上传，正在解析" : `已上传 ${successCount} 个文件，正在解析`);
      uploadOpen.value = false;
      uploadQueue.value = [];
      return;
    }
    uploadQueue.value = uploadQueue.value.filter((item) => item.status !== "uploaded");
    emit("notice", successCount ? "warning" : "error", successCount ? `已上传 ${successCount} 个文件，${failureCount} 个失败` : `上传失败，${failureCount} 个文件未提交`);
  });
}
function deleteMaterial(id: number) { if (!ensureCurrentCourseOperable()) return; confirmDeleteMaterialId.value = id; confirmDeleteMaterialOpen.value = true; }
async function confirmDeleteMaterial() { const id = confirmDeleteMaterialId.value; confirmDeleteMaterialOpen.value = false; if (!id || !ensureCurrentCourseOperable()) return; await withAction(`delete-material-${id}`, async () => { await run(() => api.delete(`/materials/${id}`), "已删除"); await loadMaterials(); }); }
async function reprocessMaterial(id: number) {
  if (!ensureCurrentCourseOperable()) return;
  await withAction(`reprocess-material-${id}`, async () => {
    const material = await run<any>(() => api.post(`/materials/${id}/reprocess`), "已重新提交解析，正在解析中");
    if (!material) return;
    markMaterialReprocessing(id);
    await loadMaterials();
    scheduleMaterialRefreshes();
  });
}
function closePreview() {
  previewItem.value = null;
  previewDetail.value = null;
}
async function previewMaterial(item: any) {
  previewItem.value = item;
  previewDetail.value = null;
  const detail = await withAction<MaterialDetail>(`preview-material-${item.id}`, () => api.get(`/materials/${item.id}`));
  if (detail) previewDetail.value = detail;
}
async function downloadMaterial(item: any) {
  if (!item?.id) return;
  await run(() => api.download(`/materials/${item.id}/content`, item.original_filename || item.title || `material-${item.id}`), "已下载");
}
async function openPptWorkbench(materialId: number) {
  if (!ensureCurrentCourseOperable()) return;
  const row = materials.value.find((item) => Number(item.id) === Number(materialId));
  if (row && isMaterialProcessing(row)) {
    emit("notice", "info", "资料正在解析中，完成后可编辑课时");
    return;
  }
  const detail = await withAction<MaterialDetail>(`open-ppt-${materialId}`, () => api.get(`/materials/${materialId}`));
  if (!detail) return;
  if (!(detail.pages || []).length) return emit("notice", "warning", "资料还没有可编辑页面，请等待解析完成或重新处理");
  workbenchMode.value = "material";
  materialDetail.value = detail;
  currentPageId.value = materialDetail.value?.pages[0]?.id || null;
  await go("teacherPpt");
}
async function openLessonWorkbench(lessonId: number) {
  if (!ensureCurrentCourseOperable()) return;
  const detail = await withAction<any>(`open-lesson-${lessonId}`, () => api.get(`/lessons/${lessonId}`));
  if (!detail) return;
  if (!(detail.pages || []).length) return emit("notice", "warning", "该课时暂无页面内容");
  workbenchMode.value = "lesson";
  materialDetail.value = {
    material: {
      id: detail.lesson.material_id || 0,
      title: detail.lesson.title,
      material_type: "lesson",
      parse_status: detail.lesson.status,
    },
    lesson_id: detail.lesson.id,
    lesson_status: detail.lesson.status,
    lesson_page_count: detail.pages.length,
    pages: detail.pages,
  };
  currentPageId.value = materialDetail.value.pages[0]?.id || null;
  await go("teacherPpt");
}
async function openPptFromLesson(lessonId: number) { await openLessonWorkbench(lessonId); }
async function openLessonScript(lesson: any) { await openLessonWorkbench(lesson.id); }
function jumpToPage(id: number) { currentPageId.value = id; slideOverviewOpen.value = false; }
function prevPage() { const index = Math.max(0, currentPageIndex.value - 1); currentPageId.value = pages.value[index]?.id || null; }
function nextPage() { const index = Math.min(pages.value.length - 1, currentPageIndex.value + 1); currentPageId.value = pages.value[index]?.id || null; }
function firstPage() { currentPageId.value = pages.value[0]?.id || null; }
function lastPage() { currentPageId.value = pages.value[pages.value.length - 1]?.id || null; }
function zoomSlide() {
  const steps = [1, 1.12, 1.24];
  slideScale.value = steps[(steps.findIndex((item) => item === slideScale.value) + 1) % steps.length];
  emit("notice", "info", `缩放 ${Math.round(slideScale.value * 100)}%`);
}
function toggleStageFocus() {
  stageFocused.value = !stageFocused.value;
  if (stageFocused.value) slideOverviewOpen.value = false;
  emit("notice", "info", stageFocused.value ? "已放大预览区" : "已恢复预览区");
}
function toggleSlideOverview() {
  slideOverviewOpen.value = !slideOverviewOpen.value;
  if (slideOverviewOpen.value) stageFocused.value = false;
}
function togglePresentationMode() {
  presentationMode.value = !presentationMode.value;
  slideOverviewOpen.value = false;
  emit("notice", "info", presentationMode.value ? "已进入演示视图" : "已退出演示视图");
}
function pulseEditor(name: string) {
  editorPulse.value = name;
  window.clearTimeout(editorPulseTimer);
  editorPulseTimer = window.setTimeout(() => { editorPulse.value = ""; }, 550);
}
function commitScriptDraft(next: string, selectStart?: number, selectEnd?: number) {
  if (next === scriptDraft.value) return;
  scriptUndoStack.value.push(scriptDraft.value);
  scriptRedoStack.value = [];
  scriptDraft.value = next;
  if (selectStart !== undefined && selectEnd !== undefined) {
    nextTick(() => {
      scriptEditor.value?.focus();
      scriptEditor.value?.setSelectionRange(selectStart, selectEnd);
    });
  }
}
function formatScript(type: "bold" | "italic" | "paragraph") {
  const editor = scriptEditor.value;
  const start = editor?.selectionStart ?? scriptDraft.value.length;
  const end = editor?.selectionEnd ?? scriptDraft.value.length;
  const selected = scriptDraft.value.slice(start, end);
  if (type === "paragraph") {
    const insert = selected ? `\n\n${selected}\n\n` : "\n\n";
    commitScriptDraft(`${scriptDraft.value.slice(0, start)}${insert}${scriptDraft.value.slice(end)}`, start + insert.length, start + insert.length);
    pulseEditor("paragraph");
    return;
  }
  const mark = type === "bold" ? "**" : "*";
  const fallback = type === "bold" ? "重点文字" : "强调文字";
  const content = selected || fallback;
  const next = `${scriptDraft.value.slice(0, start)}${mark}${content}${mark}${scriptDraft.value.slice(end)}`;
  const offset = start + mark.length;
  commitScriptDraft(next, offset, offset + content.length);
  pulseEditor(type);
}
function undoScriptEdit() {
  const previous = scriptUndoStack.value.pop();
  if (previous === undefined) return emit("notice", "info", "没有可撤销的编辑");
  scriptRedoStack.value.push(scriptDraft.value);
  scriptDraft.value = previous;
  pulseEditor("undo");
}
function redoScriptEdit() {
  const next = scriptRedoStack.value.pop();
  if (next === undefined) return emit("notice", "info", "没有可重做的编辑");
  scriptUndoStack.value.push(scriptDraft.value);
  scriptDraft.value = next;
  pulseEditor("redo");
}
async function saveCurrentScript(ok: string) {
  if (!ensureCurrentCourseOperable()) return;
  if (!activePage.value) return;
  const pageId = activePage.value.id;
  const page = await withAction<any>(`save-script-${pageId}`, () => api.patch(`/materials/pages/${pageId}/script`, { script_text: scriptDraft.value }), ok);
  if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item: any) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; }
}
async function saveScript() { await saveCurrentScript("已审核"); }
async function synthesizeCurrent() { await saveCurrentScript("已合成"); }
async function regenCurrent() {
  if (!ensureCurrentCourseOperable()) return;
  if (!activePage.value) return;
  const pageId = activePage.value.id;
  const page = await withAction<any>(`regen-page-${pageId}`, () => api.post(`/materials/pages/${pageId}/script/regenerate`), "已生成");
  if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item: any) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; scriptDraft.value = page.script_text || ""; }
}
async function markAllReviewed() {
  if (!ensureCurrentCourseOperable()) return;
  await withAction("mark-all-reviewed", async () => {
    for (const page of pages.value) await run(() => api.patch(`/materials/pages/${page.id}/script`, { script_text: page.script_text || page.page_text }));
    emit("notice", "success", "已审核");
    if (workbenchMode.value === "material" && materialDetail.value?.material?.id) await openPptWorkbench(materialDetail.value.material.id);
    else if (materialDetail.value?.lesson_id) await openLessonWorkbench(materialDetail.value.lesson_id);
  });
}
async function publishLessonFromMaterial() { if (!ensureCurrentCourseOperable()) return; if (!materialDetail.value?.lesson_id) return emit("notice", "warning", "暂无可发布的课时"); await withAction("publish-lesson", async () => { await run(() => api.post(`/lessons/${materialDetail.value!.lesson_id}/publish`)); await Promise.all([loadCourseHome(), loadLessons()]); }, "已发布"); }
async function toggleLessonPublish(lesson: any) { if (!ensureCurrentCourseOperable()) return; await withAction(`toggle-lesson-${lesson.id}`, async () => { await run(() => api.post(`/lessons/${lesson.id}/${lesson.status === 'published' ? 'unpublish' : 'publish'}`), "已更新"); await loadLessons(); }); }
async function duplicateLesson(id: number) { if (!ensureCurrentCourseOperable()) return; await withAction(`duplicate-lesson-${id}`, async () => { await run(() => api.post(`/teacher/lessons/${id}/duplicate`), "已复制"); await loadLessons(); }); }
function deleteLesson(id: number) { if (!ensureCurrentCourseOperable()) return; confirmDeleteLessonId.value = id; confirmDeleteLessonOpen.value = true; }
async function confirmDeleteLesson() { const id = confirmDeleteLessonId.value; confirmDeleteLessonOpen.value = false; if (!id || !ensureCurrentCourseOperable()) return; await withAction(`delete-lesson-${id}`, async () => { await run(() => api.delete(`/teacher/lessons/${id}`), "已删除"); await loadLessons(); }); }
async function openLessonPreview(id: number) {
  const detail = await withAction<any>(`preview-lesson-${id}`, () => api.get(`/lessons/${id}`));
  if (!detail) return;
  lessonPreview.value = detail;
  lessonPreviewPageId.value = detail.pages?.[0]?.id || null;
}
async function openStudent(id: number) {
  if (!currentCourse.value) return;
  const data = await withAction(`open-student-${id}`, () => api.get(`/teacher/courses/${currentCourse.value!.id}/students/${id}`));
  if (!data) return;
  studentDrawer.value = data;
  studentTab.value = "base";
}
function defaultReminderTitle() { return currentCourse.value ? `${currentCourse.value.name}学习提醒` : "学习提醒"; }
function defaultReminderMessage() { return `请及时查看《${currentCourse.value?.name || "课程"}》的学习进度，完成未学课时、练习或待办任务。`; }
function openReminderModal(ids: number[]) {
  if (!ensureCurrentCourseOperable()) return;
  const uniqueIds = Array.from(new Set(ids.map(Number).filter(Boolean)));
  if (!uniqueIds.length) return emit("notice", "warning", "请先选择学生");
  reminderTargetIds.value = uniqueIds;
  reminderForm.title = defaultReminderTitle();
  reminderForm.message = defaultReminderMessage();
  reminderOpen.value = true;
}
function remindStudent(id: number) { openReminderModal([id]); }
function removeStudent(id: number) {
  if (!ensureCurrentCourseOperable()) return;
  const target = studentDrawer.value?.student?.id === id
    ? studentDrawer.value?.student
    : filteredStudents.value.find((item: any) => Number(item.student?.id) === Number(id))?.student;
  confirmRemoveStudent.id = id;
  confirmRemoveStudent.name = target?.nickname || "该学生";
  confirmRemoveStudentOpen.value = true;
}
async function confirmRemoveStudentAction() {
  const id = confirmRemoveStudent.id;
  confirmRemoveStudentOpen.value = false;
  if (!id || !ensureCurrentCourseOperable()) return;
  await withAction(`remove-student-${id}`, async () => { await run(() => api.delete(`/teacher/courses/${currentCourse.value!.id}/students/${id}`), "已移出"); studentDrawer.value = null; await loadStudents(); });
}
function batchRemind() { openReminderModal(filteredStudents.value.map((item: any) => item.student.id)); }
async function sendReminder() {
  if (!ensureCurrentCourseOperable() || !reminderTargetIds.value.length) return;
  const title = reminderForm.title.trim();
  const message = reminderForm.message.trim();
  if (!title || !message) return emit("notice", "warning", "提醒标题和内容不能为空");
  const targetIds = [...reminderTargetIds.value];
  await withAction("send-reminder", async () => {
    if (targetIds.length === 1) {
      const data = await run<any>(() => api.post(`/teacher/courses/${currentCourse.value!.id}/students/${targetIds[0]}/remind`, { title, message }));
      if (!data?.sent) return;
      emit("notice", "success", "已发送提醒");
    } else {
      const data = await run<any>(() => api.post(`/teacher/courses/${currentCourse.value!.id}/reminders/batch`, { student_ids: targetIds, message }));
      if (!data) return;
      const sent = Number(data?.sent || 0);
      const skipped = Array.isArray(data?.skipped) ? data.skipped : [];
      if (!sent && !skipped.length) return;
      if (!skipped.length) {
        emit("notice", "success", `已提醒 ${sent} 人`);
      } else {
        const reasons = Array.from(new Set(skipped.map((item: any) => item?.reason).filter(Boolean)));
        const reasonText = reasons.length ? `（${reasons.join("、")}）` : "";
        emit("notice", sent ? "success" : "warning", `已提醒 ${sent} 人，${skipped.length} 人跳过${reasonText}`);
      }
    }
    reminderOpen.value = false;
    reminderTargetIds.value = [];
    await loadStudents();
  });
}
function clearStudentFilter() { Object.assign(studentFilter, { keyword: "", progress: "", active: "" }); }
async function exportCurrent() { if (!currentCourse.value) return; await withAction(`export-${active.value}`, async () => { if (active.value === "teacherStudents") await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/students/export`, `students-${currentCourse.value!.course_code}.csv`), "已导出"); if (active.value === "teacherAnalytics") { const days = analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/analysis/export`, `analysis-${currentCourse.value!.course_code}.csv`, { days }), "已导出"); } }); }
async function retryTask(task: any) {
  const targetId = Number(task?.target_id || 0);
  if (task?.target_type === "material" && targetId) {
    // Reprocess is authorized per-material on the backend (course must be active),
    // so retry directly instead of relying on the currently selected course.
    await withAction(`reprocess-material-${targetId}`, async () => {
      const material = await run<any>(() => api.post(`/materials/${targetId}/reprocess`), "已重新提交解析，正在解析中");
      if (!material) return;
      if (currentCourse.value && Number(material.course_id) === Number(currentCourse.value.id)) {
        markMaterialReprocessing(targetId);
        await loadMaterials();
        scheduleMaterialRefreshes();
      }
      await Promise.all([loadDashboard(), currentCourse.value ? loadCourseHome() : Promise.resolve()]);
    });
    return;
  }
  if (task?.target_type === "quiz") {
    const courseId = Number(task?.detail?.course_id || 0);
    if (courseId && currentCourseId.value !== courseId) currentCourseId.value = courseId;
    emit("notice", "info", "请在薄弱题目页面重新生成该测验");
    await go("teacherWeakQuizzes");
    return;
  }
  emit("notice", "warning", "该任务暂不支持重试");
}
async function copyText(text: unknown) {
  const copied = await copyToClipboard(text);
  emit("notice", copied ? "success" : "warning", copied ? "已复制" : "复制失败，请手动复制");
}
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
  await withAction("upload-avatar", async () => {
    const form = new FormData();
    form.set("file", file);
    const data = await api.post<any>("/teacher/profile/avatar", form);
    applyTeacherProfile(data);
    return data;
  }, "头像已更新");
}
async function saveProfile() { const data = await withAction<any>("save-profile", () => api.patch("/teacher/profile", { nickname: profileForm.nickname, avatar_url: profileForm.avatar_url, bio: profileForm.bio, organization: profileForm.organization, department: profileForm.department }), "已保存"); if (data) applyTeacherProfile(data); profileEditing.value = false; }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); await withAction("change-password", async () => { const res = await run(() => api.post<{ access_token: string }>("/auth/me/password", passwordForm), "已保存"); if (res?.access_token) setToken(res.access_token); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }); }
async function saveNotice() { const data = await withAction<any[]>("save-notice", () => api.put("/teacher/profile/notifications", { settings: noticeSettings.map((item) => ({ key: item.key, enabled: item.enabled })) }), "已保存"); if (data) noticeSettings.splice(0, noticeSettings.length, ...data); }

function shortName(value?: string) { return (value || "-").length > 12 ? `${(value || "").slice(0, 12)}...` : value || "-"; }
function rankPlain(index: string | number) { return Number(index) + 1; }
function rankNumber(index: string | number) { return String(rankPlain(index)).padStart(2, "0"); }
function cloudSize(count: string | number) { return `${14 + Math.min(Number(count) || 0, 20)}px`; }
function formatTime(value?: string | null) { return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"; }
function shortDate(value?: string | null) { return value ? new Date(value).toLocaleDateString("zh-CN") : "-"; }
function isCourseOperable(course?: any | null) { return !!course && String(course.status || "active") === "active"; }
function ensureCurrentCourseOperable() {
  if (!currentCourse.value) {
    emit("notice", "warning", "请先选择课程");
    return false;
  }
  if (!currentCourseOperable.value) {
    emit("notice", "warning", "课程已下架，请先上架后再操作");
    return false;
  }
  return true;
}
function courseColor(id: number) { return `linear-gradient(135deg, ${palette[id % palette.length]}, #121614)`; }
function courseCoverText(course?: any) {
  const text = String(course?.name || "课程名称").replace(/\s+/g, "");
  return text.slice(0, 4) || "课程";
}
function courseCoverStyle(course: any) {
  if (course?.cover_url) return { backgroundImage: `linear-gradient(180deg, rgba(18,22,20,0.08), rgba(18,22,20,0.38)), url(${course.cover_url})` };
  return { background: course?.cover_color || courseColor(Number(course?.id || 1)) };
}
function courseHeroStyle(course: any) {
  if (course?.cover_url) {
    return {
      backgroundImage: `linear-gradient(135deg, rgba(18,22,20,0.82), rgba(217,73,37,0.36)), url(${course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: course?.cover_color || courseColor(Number(course?.id || 1)) };
}
function courseCoverPreviewStyle() {
  const preview = courseCoverPreview.value || courseForm.cover_url;
  if (preview) return { backgroundImage: `linear-gradient(180deg, rgba(18,22,20,0.08), rgba(18,22,20,0.38)), url(${preview})` };
  return { background: courseForm.cover_color };
}
function heatOpacity(count: number) { return String(Math.min(1, 0.15 + count / 20)); }
function todoIcon(type: string) { return type === "error" ? AlertCircle : type === "lesson" ? Presentation : FileText; }
function sizeLabel(size?: number) { const value = Number(size || 0); if (value < 1024) return `${value} B`; if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`; if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`; return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`; }
function chapterName(id?: number | null) { return (courseHome.value.chapters || []).find((chapter: any) => chapter.id === id)?.title || "未分章"; }
function isLongInactive(value?: string | null) { return !value || Date.now() - new Date(value).getTime() > 14 * 86400000; }

function onTeacherDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node;
  if (!courseSwitchRef.value?.contains(target)) courseMenuOpen.value = false;
  if (!userMenuRef.value?.contains(target)) userMenuOpen.value = false;
  if (!teacherNoticeRef.value?.contains(target)) teacherNoticeOpen.value = false;
}
function onTeacherDocumentKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  courseMenuOpen.value = false;
  userMenuOpen.value = false;
  teacherNoticeOpen.value = false;
  uploadOpen.value = false;
  chapterNameOpen.value = false;
  reminderOpen.value = false;
  closePreview();
  lessonPreview.value = null;
  quizEditorOpen.value = false;
  studentDrawer.value = null;
}

onMounted(async () => {
  document.addEventListener("pointerdown", onTeacherDocumentPointerDown);
  document.addEventListener("keydown", onTeacherDocumentKeydown);
  await loadCourses();
  await loadActive();
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onTeacherDocumentPointerDown);
  document.removeEventListener("keydown", onTeacherDocumentKeydown);
  clearMaterialRefreshTimers();
  resetCourseCoverSelection();
});

</script>

<style scoped src="../styles/teacher-scoped.css"></style>
<style scoped src="../styles/teacher-classagent.css"></style>
<style scoped>
.help-modal { width: min(560px, 94vw); display: grid; gap: 16px; }
.help-body { display: grid; gap: 18px; }
.help-section { display: grid; gap: 8px; }
.help-section h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: var(--text-body); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.help-section p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-body-sm); line-height: 1.65; }
.help-section ol { margin: 0; padding-left: 20px; display: grid; gap: 6px; color: var(--color-text-secondary); font-size: var(--text-body-sm); line-height: 1.6; }
.help-section li { padding-left: 2px; }
</style>
