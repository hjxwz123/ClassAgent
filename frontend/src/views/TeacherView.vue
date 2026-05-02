<template>
  <section class="teacher-shell">
    <header class="teacher-header">
      <div class="brand">
        <span class="logo-mark"><Sparkles :size="17" /></span>
        <strong>课程学习助手</strong>
        <i></i>
        <div ref="courseSwitchRef" class="course-switch">
          <button @click="courseMenuOpen = !courseMenuOpen">{{ currentCourse?.name || '选择课程' }}<ChevronDown :size="16" /></button>
          <Transition name="top-menu">
            <div v-if="courseMenuOpen" class="course-popover top-menu-panel">
              <button v-for="course in courses.slice(0, 8)" :key="course.id" :class="{ active: currentCourseId === course.id }" @click="selectCourse(course.id)">
                <Check v-if="currentCourseId === course.id" :size="15" />{{ course.name }}
              </button>
              <button @click="newCourse"><Plus :size="15" />创建课程</button>
            </div>
          </Transition>
        </div>
      </div>
      <div class="header-actions">
        <button class="icon-btn" @click="openNotifications"><Bell :size="20" /><span>通知</span><em v-if="todoCount">{{ todoCount }}</em></button>
        <button class="icon-btn" @click="openHelp"><HelpCircle :size="20" /><span>帮助</span></button>
        <i></i>
        <div ref="userMenuRef" class="user-menu">
          <button @click="userMenuOpen = !userMenuOpen"><span class="avatar">{{ firstChar(teacherName) }}</span><b>{{ teacherName }}</b><ChevronDown :size="16" /></button>
          <Transition name="top-menu">
            <div v-if="userMenuOpen" class="user-popover top-menu-panel">
              <button @click="go('teacherProfile')"><User :size="15" />个人中心</button>
              <button @click="go('teacherProfile')"><Settings :size="15" />账号设置</button>
              <button @click="$emit('logout')"><LogOut :size="15" />退出登录</button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <aside class="teacher-sidebar">
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
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherMaterials' || active === 'teacherPpt' }" @click="go('teacherMaterials')"><FolderOpen :size="16" />资料管理</button>
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherLessons' }" @click="go('teacherLessons')"><Presentation :size="16" />课时管理</button>
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherStudents' }" @click="go('teacherStudents')"><Users :size="16" />学生管理</button>
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherAnalytics' }" @click="go('teacherAnalytics')"><BarChart2 :size="16" />教学分析</button>
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
          <button v-if="active === 'teacherMaterials'" class="btn btn-primary" @click="uploadOpen = true"><Upload :size="16" />上传资料</button>
          <button v-if="active === 'teacherLessons'" class="btn btn-primary" @click="go('teacherMaterials')"><Plus :size="16" />从资料创建</button>
          <button v-if="active === 'teacherStudents'" class="btn btn-ghost" :data-loading="isPending('export-teacherStudents')" :disabled="isPending('export-teacherStudents')" @click="exportCurrent"><Download :size="16" />导出学生</button>
          <div v-if="active === 'teacherAnalytics'" class="segmented-control">
            <button v-for="item in analysisRangeOptions" :key="item" type="button" class="segment-btn" :class="{ active: analysisRange === item }" :data-loading="isPending('analysis-range') && analysisRange === item" :disabled="isPending('analysis-range')" @click="setAnalysisRange(item)">{{ item }}</button>
          </div>
          <button v-if="active === 'teacherAnalytics'" class="btn btn-ghost" :data-loading="isPending('export-teacherAnalytics')" :disabled="isPending('export-teacherAnalytics')" @click="exportCurrent"><Download :size="16" />导出报告</button>
        </section>
      </div>
      <Transition name="fade-slide">
        <div v-if="pageLoading" class="teacher-page-loading"><span class="spinner"></span></div>
      </Transition>

      <TransitionGroup name="page-switch" tag="div" class="teacher-page-stack">
      <section v-if="active === 'teacherDashboard'" key="teacherDashboard" class="teacher-content">
        <article class="welcome">
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
              <div class="course-cover" :style="{ background: courseColor(course.id) }"><span class="tag">{{ course.term }}</span><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span><BookOpen :size="48" /></div>
              <section><h2>{{ course.name }}</h2><code>{{ course.course_code }}</code><div class="course-stats"><span><Users :size="15" />{{ course.student_count || 0 }}</span><span><Presentation :size="15" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</span><span><File :size="15" />{{ course.material_count || 0 }}</span><span><Check :size="15" />{{ course.published_rate || 0 }}%</span></div></section>
              <footer><button class="btn btn-primary btn-sm" :data-loading="isPending(`select-course-${course.id}`)" :disabled="isPending(`select-course-${course.id}`)" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button><button class="icon-action" :data-loading="isPending(`edit-course-${course.id}`)" :disabled="isPending(`edit-course-${course.id}`)" @click="editCourse(course)"><Pencil :size="15" />编辑</button></footer>
            </article>
          </TransitionGroup>
          <article v-else key="list" class="table-card"><table class="teacher-table"><thead><tr><th>课程名称</th><th>学期</th><th>学生数</th><th>课时数</th><th>资料数</th><th>状态</th><th>最近更新</th><th>操作</th></tr></thead><TransitionGroup name="row-list" tag="tbody"><tr v-for="course in filteredCourses" :key="course.id"><td><span class="mini-cover"></span><strong>{{ course.name }}</strong><code>{{ course.course_code }}</code></td><td>{{ course.term }}</td><td><Users :size="14" />{{ course.student_count || 0 }}</td><td><Presentation :size="14" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</td><td><File :size="14" />{{ course.material_count || 0 }}</td><td><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span></td><td>{{ relativeTime(course.updated_at) }}</td><td><button class="btn btn-primary btn-sm" :data-loading="isPending(`select-course-${course.id}`)" :disabled="isPending(`select-course-${course.id}`)" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button><button class="icon-action" :data-loading="isPending(`edit-course-${course.id}`)" :disabled="isPending(`edit-course-${course.id}`)" @click="editCourse(course)"><Pencil :size="15" />编辑</button></td></tr></TransitionGroup></table></article>
        </Transition>
        <EmptyState v-if="!filteredCourses.length" text="还没有课程"><button class="btn btn-primary" @click="newCourse"><Plus :size="16" />创建课程</button></EmptyState>
      </section>

      <section v-if="active === 'teacherCourseForm'" key="teacherCourseForm" class="teacher-content form-content">
        <section class="course-form-layout">
          <article class="panel-card form-panel">
            <div class="form-section"><h2>基本信息</h2><label>课程名称<input v-model="courseForm.name" class="input" maxlength="50" /></label><label>课程简介<textarea v-model="courseForm.description" class="textarea" maxlength="500"></textarea><small>{{ courseForm.description.length }} / 500</small></label><label>学期<input v-model="courseForm.term" class="input" /></label><label>课程封面色<div class="color-row"><button v-for="color in palette" :key="color" :style="{ background: color }" :class="{ active: courseForm.cover_color === color }" @click="courseForm.cover_color = color"></button></div></label></div>
            <div class="form-section"><div class="section-head"><h2><Layers :size="18" />课程章节</h2><button class="btn btn-ghost btn-sm" :disabled="courseForm.chapters.length >= 30" @click="addDraftChapter"><Plus :size="14" />添加章节</button></div><TransitionGroup name="chapter-list" tag="div" class="chapter-edit-list"><div v-for="(chapter, index) in courseForm.chapters" :key="chapter.local_id" class="chapter-edit" :class="{ 'just-added': freshChapterId === chapter.local_id }"><GripVertical :size="15" /><input v-model="chapter.title" class="input" /><input v-model.number="chapter.order_index" class="input order-input" type="number" /><button class="icon-action danger" :disabled="courseForm.chapters.length <= 1" @click="removeDraftChapter(index)"><Trash2 :size="15" />删除</button></div></TransitionGroup></div>
            <div class="advanced" :class="{ open: advancedOpen }"><button type="button" class="advanced-trigger" @click="advancedOpen = !advancedOpen"><Settings :size="16" />高级设置<ChevronDown :size="14" /></button><Transition name="accordion"><div v-if="advancedOpen" class="advanced-body"><AppCheckbox v-model="courseForm.allow_leave" label="学生退出" /><AppCheckbox v-model="courseForm.ai_qa" label="AI 问答" /><AppCheckbox v-model="courseForm.quiz_enabled" label="测验发布" /></div></Transition></div>
          </article>
          <aside class="panel-card preview-card"><div class="panel-head"><h2><Eye :size="18" />卡片预览</h2></div><article class="course-card preview"><div class="course-cover" :style="{ background: courseForm.cover_color }"><BookOpen :size="44" /></div><section><h2>{{ courseForm.name || '课程名称' }}</h2><code>{{ courseForm.id ? currentCourse?.course_code : 'A8K3Z' }}</code><div class="course-stats"><span><Layers :size="15" />{{ courseForm.chapters.length }}</span><span><Users :size="15" />0</span></div></section></article></aside>
        </section>
        <div class="fixed-actions"><span><Edit2 :size="15" />有未保存的更改</span><div><button class="btn btn-ghost" @click="go('teacherCourses')">取消</button><button v-if="courseForm.id" class="btn btn-danger" :data-loading="isPending('delete-course')" :disabled="isPending('delete-course')" @click="deleteCourse">删除课程</button><button class="btn btn-secondary" :data-loading="isPending('save-course')" :disabled="isPending('save-course')" @click="saveCourse">保存草稿</button><button class="btn btn-primary" :data-loading="isPending('save-course')" :disabled="isPending('save-course')" @click="saveCourse">{{ courseForm.id ? '保存修改' : '创建课程' }}</button></div></div>
      </section>

      <section v-if="active === 'teacherCourseHome'" key="teacherCourseHome" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="course-hero" :style="{ background: courseColor(currentCourse.id) }"><span><BookOpen :size="36" /></span><div><h1>{{ courseHome.course?.name || currentCourse.name }}</h1><p>{{ currentCourse.term }} · {{ currentCourse.course_code }}</p><small><Users :size="15" />{{ courseHome.quick_counts?.student_count || 0 }} 学生 <Presentation :size="15" />{{ courseHome.quick_counts?.lesson_count || 0 }} 课时 <File :size="15" />{{ courseHome.quick_counts?.material_count || 0 }} 资料</small></div><section><button class="btn ghost-white" @click="editCourse(currentCourse)"><Pencil :size="16" />编辑课程</button><button class="btn ghost-white" @click="copyText(currentCourse.course_code)"><Share2 :size="16" />分享课程码</button></section></article>
          <div class="quick-grid"><QuickAction :icon="Upload" label="上传资料" sub="PPT/PDF/Word/TXT" @click="go('teacherMaterials')" /><QuickAction :icon="Presentation" label="管理课时" sub="课时发布" @click="go('teacherLessons')" /><QuickAction :icon="UserPlus" label="邀请学生" sub="课程码" @click="copyText(currentCourse.course_code)" /><QuickAction :icon="BarChart2" label="教学分析" sub="课程数据" @click="go('teacherAnalytics')" /></div>
          <div class="course-home-grid">
            <article class="panel-card home-lesson-card">
              <div class="panel-head rich-head">
                <div><h2><Presentation :size="18" />课时列表</h2><small>{{ courseHome.quick_counts?.lesson_count || 0 }} 个课时 · 点击可进入脚本工作台</small></div>
                <button class="btn btn-ghost btn-sm" @click="go('teacherLessons')"><Presentation :size="14" />管理课时</button>
              </div>
              <LessonRows :items="courseHome.lessons || []" :student-total="courseHome.quick_counts?.student_count || 0" @open="openLessonScript" />
              <button class="btn btn-primary btn-sm full home-card-action" @click="go('teacherMaterials')"><Plus :size="14" />从资料生成课时</button>
            </article>
            <article class="panel-card material-overview-card">
              <div class="panel-head rich-head">
                <div><h2><FolderOpen :size="18" />资料状态</h2><small>{{ materialReadyCount }}/{{ materialTotal }} 份资料已完成解析</small></div>
                <button class="btn btn-ghost btn-sm" @click="go('teacherMaterials')"><Upload :size="14" />资料管理</button>
              </div>
              <section class="material-health">
                <div><strong>{{ materialReadyPercent }}%</strong><span>解析完成率</span></div>
                <AppProgress :value="materialReadyPercent" :tone="materialProgressTone" />
              </section>
              <div class="material-status-grid">
                <button v-for="item in materialStatusCards" :key="item.key" :class="['material-status-tile', item.tone]" @click="go('teacherMaterials')">
                  <component :is="item.icon" :size="17" />
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </button>
              </div>
              <MaterialTypeList :stats="courseHome.material_stats?.by_type || {}" />
              <button class="btn btn-secondary btn-sm full home-card-action" @click="go('teacherMaterials')"><Upload :size="14" />上传课程资料</button>
            </article>
            <article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />近期活动</h2></div><ActivityList :items="courseHome.activities || []" /></article>
          </div>
          <div class="course-bottom-grid"><article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生学习进度</h2><button class="link-btn" @click="go('teacherStudents')">查看详情</button></div><ProgressList :items="courseHome.student_progress || []" /></article><article class="panel-card"><div class="panel-head"><h2><Sparkles :size="18" />AI 任务队列</h2><span class="tag">{{ (courseHome.ai_tasks || []).length }}</span></div><TaskList :items="courseHome.ai_tasks || []" @retry="retryTask" /></article></div>
        </template>
      </section>

      <section v-if="active === 'teacherMaterials'" key="teacherMaterials" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid three compact"><MetricCard :icon="File" label="资料总数" :value="materialSummary.total || 0" sub="份" /><MetricCard :icon="Database" label="存储用量" :value="sizeLabel(materialSummary.size_bytes)" sub="课程资料" tone="success" /><MetricCard :icon="Sparkles" label="已解析" :value="`${materialSummary.ready || 0}/${materialSummary.total || 0}`" sub="AI" tone="ai" /></div>
          <div class="materials-layout"><aside class="chapter-tree"><div class="search-box small"><Search :size="15" /><input v-model="chapterKeyword" placeholder="搜索章节" /></div><button :class="{ active: selectedChapterId === 0 }" @click="selectedChapterId = 0"><FileText :size="16" />全部资料<span>{{ materialSummary.total || 0 }}</span></button><TransitionGroup name="motion-list" tag="div" class="chapter-buttons"><button v-for="chapter in filteredChapters" :key="chapter.id" :class="{ active: selectedChapterId === chapter.id, empty: !chapter.count, 'just-added': freshMaterialChapterId === chapter.id }" @click="selectedChapterId = chapter.id"><Layers :size="16" />{{ chapter.title }}<span>{{ chapter.count }}</span></button></TransitionGroup><button :data-loading="isPending('add-tree-chapter')" :disabled="isPending('add-tree-chapter')" @click="addChapterFromTree"><Plus :size="16" />添加章节</button></aside><section class="materials-panel" :class="{ 'panel-loading': isPending('filter-materials') }"><div class="material-filter"><div class="search-box"><Search :size="16" /><input v-model="materialFilter.keyword" placeholder="搜索文件名" @keyup.enter="refreshMaterials" /></div><AppSelect v-model="materialFilter.type" :options="materialTypeOptions" /><AppSelect v-model="materialFilter.status" :options="materialStatusOptions" /><AppSelect v-model="materialSort" :options="materialSortOptions" /><div class="view-toggle"><button type="button" :class="{ active: materialView === 'grid' }" @click="materialView = 'grid'"><Grid2X2 :size="16" />网格</button><button type="button" :class="{ active: materialView === 'list' }" @click="materialView = 'list'"><FileText :size="16" />列表</button></div></div><TransitionGroup name="material-list-motion" tag="div" class="material-list" :class="materialView"><article v-for="item in filteredMaterials" :key="item.id" class="material-row"><span class="file-badge" :class="item.material_type"><component :is="fileIcon(item.material_type)" :size="18" /></span><div><strong>{{ item.title }}</strong><small>{{ chapterName(item.chapter_id) }} · {{ typeText(item.material_type) }} · {{ sizeLabel(item.size_bytes) }}</small><MaterialStatus :item="item" /></div><span class="tag" :class="statusClass(item.parse_status)">{{ statusText(item.parse_status) }}</span><section><button class="icon-action" @click="previewMaterial(item)"><Eye :size="15" />预览</button><button v-if="item.parse_status === 'ready'" class="icon-action" :data-loading="isPending(`open-ppt-${item.id}`)" :disabled="isPending(`open-ppt-${item.id}`)" @click="openPptWorkbench(item.id)"><Wand2 :size="15" />编辑课时</button><a v-if="item.preview_url" class="icon-action" :href="item.preview_url" target="_blank"><Download :size="15" />下载</a><button class="icon-action danger" :data-loading="isPending(`delete-material-${item.id}`)" :disabled="isPending(`delete-material-${item.id}`)" @click="deleteMaterial(item.id)"><Trash2 :size="15" />删除</button></section></article><EmptyState v-if="!filteredMaterials.length" key="empty" text="暂无资料" /></TransitionGroup></section></div>
        </template>
      </section>

      <section v-if="active === 'teacherPpt'" key="teacherPpt" class="ppt-workbench" :class="{ 'presentation-mode': presentationMode }">
        <header class="ppt-head"><button class="btn btn-ghost" @click="go(workbenchMode === 'lesson' ? 'teacherLessons' : 'teacherMaterials')"><ArrowLeft :size="16" />{{ workbenchMode === 'lesson' ? '返回课时管理' : '返回资料管理' }}</button><strong>{{ materialDetail?.material?.title || 'PPT 工作台' }}</strong></header>
        <template v-if="pages.length">
          <aside class="thumb-column"><div class="thumb-top"><strong>{{ materialDetail?.material?.title || '-' }}</strong><small>{{ reviewedCount }}/{{ pages.length }} 页已审核</small><AppProgress :value="reviewedCount" :max="Math.max(pages.length, 1)" tone="success" /><AppCheckbox :model-value="false" label="全选审核" @update:model-value="markAllReviewed" /><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent"><RefreshCw :size="14" />批量重新生成</button></div><TransitionGroup name="thumb-list" tag="div" class="thumb-list"><button v-for="page in pages" :key="page.id" class="thumb-card" :class="{ active: currentPageId === page.id }" @click="currentPageId = page.id"><span>{{ page.page_number }}</span><div>{{ page.page_title || `第${page.page_number}页` }}</div><CheckCircle v-if="page.script_status === 'ready'" :size="16" /><Clock v-else :size="16" /><small>{{ page.script_text?.slice(0, 20) }}</small></button></TransitionGroup></aside>
          <main class="ppt-stage" :class="{ focused: stageFocused }"><div class="stage-top"><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" />上一页</button>第 {{ currentPageIndex + 1 }} / {{ pages.length }} 页<button class="icon-action" @click="nextPage"><ChevronRight :size="18" />下一页</button><button class="icon-action" @click="zoomSlide"><ZoomIn :size="18" />放大</button><button class="icon-action" :class="{ active: stageFocused }" @click="toggleStageFocus"><Maximize :size="18" />专注</button></div><div class="slide-preview-wrap" :class="{ focused: stageFocused }" :style="{ '--slide-scale': slideScale }"><Transition name="slide-flip" mode="out-in"><article :key="activePage?.id || 0" class="slide-preview"><h2>{{ activePage?.page_title || `第${currentPageIndex + 1}页` }}</h2><p>{{ activePage?.page_text }}</p></article></Transition></div><Transition name="fade-slide"><div v-if="slideOverviewOpen" class="slide-overview"><TransitionGroup name="thumb-list" tag="div" class="slide-overview-grid"><button v-for="page in pages" :key="page.id" :class="{ active: currentPageId === page.id }" @click="jumpToPage(page.id)"><span>{{ page.page_number }}</span><strong>{{ page.page_title || `第${page.page_number}页` }}</strong><small>{{ page.script_status === 'ready' ? '已审核' : '待处理' }}</small></button></TransitionGroup></div></Transition><div class="stage-controls"><button class="icon-action" @click="firstPage"><SkipBack :size="18" />首页</button><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" />上一页</button><button class="icon-action" @click="nextPage"><ChevronRight :size="18" />下一页</button><button class="icon-action" @click="lastPage"><SkipForward :size="18" />末页</button><button class="icon-action" :class="{ active: slideOverviewOpen }" @click="toggleSlideOverview"><Grid2X2 :size="18" />缩略图</button><button class="icon-action" :class="{ active: presentationMode }" @click="togglePresentationMode"><Presentation :size="18" />演示</button></div></main>
          <aside class="script-panel"><div class="script-head"><h2><FileEdit :size="18" />第 {{ activePage?.page_number || 1 }} 页</h2><span class="tag" :class="statusClass(activePage?.script_status)">{{ statusText(activePage?.script_status) }}</span></div><div class="ai-strip" :class="{ thinking: activePage && isPending(`regen-page-${activePage.id}`) }"><Sparkles :size="14" />AI 生成<button :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent">重新生成</button></div><div class="editor-toolbar"><button :class="{ active: editorPulse === 'bold' }" @click="formatScript('bold')">B</button><button :class="{ active: editorPulse === 'italic' }" @click="formatScript('italic')">I</button><button :class="{ active: editorPulse === 'paragraph' }" @click="formatScript('paragraph')">段落</button><button :class="{ active: editorPulse === 'undo' }" @click="undoScriptEdit">撤销</button><button :class="{ active: editorPulse === 'redo' }" @click="redoScriptEdit">重做</button></div><textarea ref="scriptEditor" v-model="scriptDraft" class="script-editor"></textarea><small class="word-count">{{ scriptDraft.length }} 字</small><div class="script-actions"><span><Volume2 :size="16" />{{ activePage?.audio_url ? '已合成' : '未合成' }}</span><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`regen-page-${activePage.id}`)" :disabled="!!activePage && isPending(`regen-page-${activePage.id}`)" @click="regenCurrent">重新生成</button><button class="btn btn-primary btn-sm" :data-loading="activePage && isPending(`save-script-${activePage.id}`)" :disabled="!!activePage && isPending(`save-script-${activePage.id}`)" @click="saveScript">审核完成</button></div></aside>
          <footer class="ppt-status"><span>{{ materialDetail?.material?.title }} · 已审核 {{ reviewedCount }}/{{ pages.length }} 页 · 已保存</span><div><button class="btn btn-secondary btn-sm" :data-loading="isPending('mark-all-reviewed')" :disabled="isPending('mark-all-reviewed')" @click="markAllReviewed">批量审核</button><button class="btn btn-ghost btn-sm" :data-loading="activePage && isPending(`save-script-${activePage.id}`)" :disabled="!!activePage && isPending(`save-script-${activePage.id}`)" @click="synthesizeCurrent">语音合成</button><button class="btn btn-primary btn-sm" :data-loading="isPending('publish-lesson')" :disabled="isPending('publish-lesson')" @click="publishLessonFromMaterial">发布课时</button></div></footer>
        </template>
        <div v-else class="ppt-empty-state"><FileText :size="42" /><h2>暂无可编辑页面</h2><p>资料解析完成后会在这里显示课时页面和 AI 脚本。</p><button class="btn btn-primary" @click="go(workbenchMode === 'lesson' ? 'teacherLessons' : 'teacherMaterials')"><ArrowLeft :size="16" />返回列表</button></div>
      </section>

      <section v-if="active === 'teacherLessons'" key="teacherLessons" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="lessonFilter.keyword" placeholder="课时名称" /></div><AppSelect v-model="lessonFilter.chapter_id" :options="lessonChapterOptions" /><AppSelect v-model="lessonFilter.status" :options="lessonStatusOptions" /><AppSelect v-model="lessonSort" :options="lessonSortOptions" /></article>
          <TransitionGroup name="card-list" tag="div" class="lesson-card-list"><article v-for="lesson in filteredLessons" :key="lesson.id" class="lesson-card"><div class="lesson-thumb">{{ lesson.page_count || 0 }}</div><section><h2>{{ lesson.title }}<span class="tag" :class="statusClass(lesson.status)">{{ statusText(lesson.status) }}</span></h2><p>{{ chapterName(lesson.chapter_id) }} · {{ lesson.page_count }}页 · {{ lesson.learned_count || 0 }}/{{ courseHome.quick_counts?.student_count || 0 }}人 · {{ shortDate(lesson.published_at || lesson.created_at) }}</p><AppProgress :value="lesson.average_progress || 0" :tone="Number(lesson.average_progress || 0) >= 70 ? 'success' : Number(lesson.average_progress || 0) >= 30 ? 'warning' : 'danger'" /></section><div class="lesson-actions"><button class="icon-action" :data-loading="isPending(`preview-lesson-${lesson.id}`)" :disabled="isPending(`preview-lesson-${lesson.id}`)" @click="openLessonPreview(lesson.id)"><Presentation :size="16" />预览</button><button class="icon-action" @click="openLessonScript(lesson)"><Wand2 :size="16" />脚本</button><button class="icon-action" :data-loading="isPending(`duplicate-lesson-${lesson.id}`)" :disabled="isPending(`duplicate-lesson-${lesson.id}`)" @click="duplicateLesson(lesson.id)"><Copy :size="16" />复制</button><AppCheckbox variant="switch" :label="lesson.status === 'published' ? '已发布' : '草稿'" :model-value="lesson.status === 'published'" :disabled="isPending(`toggle-lesson-${lesson.id}`)" @update:model-value="toggleLessonPublish(lesson)" /><button class="icon-action danger" :data-loading="isPending(`delete-lesson-${lesson.id}`)" :disabled="isPending(`delete-lesson-${lesson.id}`)" @click="deleteLesson(lesson.id)"><Trash2 :size="16" />删除</button></div></article><EmptyState v-if="!filteredLessons.length" key="empty" text="暂无课时" /></TransitionGroup>
        </template>
      </section>

      <section v-if="active === 'teacherStudents'" key="teacherStudents" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid four compact"><MetricCard :icon="Users" label="学生总数" :value="studentPayload.stats?.total || 0" sub="本周新增" /><MetricCard :icon="Activity" label="活跃学生" :value="studentPayload.stats?.active_7d || 0" sub="近7天" tone="success" /><MetricCard :icon="CheckCircle" label="完成率" :value="`${studentPayload.stats?.average_completion || 0}%`" sub="平均" tone="success" /><MetricCard :icon="UserX" label="长期未活跃" :value="studentPayload.stats?.inactive_14d || 0" sub="14天" :danger="(studentPayload.stats?.inactive_14d || 0) > 0" /></div>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="studentFilter.keyword" placeholder="搜索学生姓名" /></div><AppSelect v-model="studentFilter.progress" :options="studentProgressOptions" /><AppSelect v-model="studentFilter.active" :options="studentActiveOptions" /><button class="btn btn-ghost" @click="clearStudentFilter"><X :size="16" />清除</button><span></span><button class="btn btn-ghost" :data-loading="isPending('batch-remind')" :disabled="isPending('batch-remind')" @click="batchRemind"><Bell :size="16" />批量提醒</button></article>
          <article class="table-card"><table class="teacher-table"><thead><tr><th>学生</th><th>加入时间</th><th>课时进度</th><th>提问次数</th><th>错题数</th><th>最近学习</th><th>操作</th></tr></thead><TransitionGroup name="row-list" tag="tbody"><tr v-for="item in filteredStudents" :key="item.student.id" :class="{ inactive: isLongInactive(item.last_study_at) }"><td><span class="avatar mini">{{ firstChar(item.student.nickname) }}</span><strong>{{ item.student.nickname }}</strong><code>{{ item.student.student_no || '-' }}</code></td><td>{{ shortDate(item.joined_at) }}</td><td><ProgressBar :value="item.progress_percent" />{{ item.studied_lessons }}/{{ item.lesson_total }}</td><td><MessageCircle :size="14" />{{ item.qa_count }}</td><td :class="{ danger: item.wrong_count > 10 }"><XCircle :size="14" />{{ item.wrong_count }}</td><td>{{ relativeTime(item.last_study_at) }}</td><td><button class="icon-action" :data-loading="isPending(`open-student-${item.student.id}`)" :disabled="isPending(`open-student-${item.student.id}`)" @click="openStudent(item.student.id)"><Eye :size="15" />详情</button><button class="icon-action" :data-loading="isPending(`remind-student-${item.student.id}`)" :disabled="isPending(`remind-student-${item.student.id}`)" @click="remindStudent(item.student.id)"><Bell :size="15" />提醒</button></td></tr></TransitionGroup></table></article>
        </template>
      </section>

      <section v-if="active === 'teacherAnalytics'" key="teacherAnalytics" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="ai-suggestion" :class="{ thinking: pageLoading || isPending('refresh-analysis') }"><span><Sparkles :size="20" /></span><div><h2>AI 教学建议</h2><p>{{ analysis.suggestion || '暂无建议' }}</p></div><button class="btn btn-ghost btn-sm" :data-loading="isPending('refresh-analysis')" :disabled="isPending('refresh-analysis')" @click="refreshAnalysis"><RefreshCw :size="14" />重新生成</button><span class="tag tag-ai">AI</span></article>
          <div class="metric-grid five compact"><MetricCard :icon="Activity" label="活跃率" :value="`${analysis.metrics?.active_rate || 0}%`" sub="近7天" /><MetricCard :icon="Presentation" label="完成率" :value="`${analysis.metrics?.completion_rate || 0}%`" sub="课时" /><MetricCard :icon="MessageCircle" label="问答总量" :value="analysis.metrics?.qa_total || 0" sub="期间" /><MetricCard :icon="ClipboardList" label="平均分" :value="analysis.metrics?.average_score || 0" sub="/100" /><MetricCard :icon="AlertTriangle" label="薄弱点" :value="analysis.metrics?.weak_point_count || 0" sub="数量" :danger="(analysis.metrics?.weak_point_count || 0) > 0" /></div>
          <div class="analysis-grid two"><article class="panel-card"><div class="panel-head"><h2><Presentation :size="18" />课时完成率</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="260" /></article><article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />学习时长</h2></div><AdminChart type="line" :labels="analysisTimeLabels" :series="analysisTimeSeries" :height="260" /></article></div>
          <div class="analysis-grid knowledge"><article class="panel-card"><div class="panel-head"><h2><Layers :size="18" />章节掌握</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="260" /></article><article class="panel-card weak-list"><div class="panel-head"><h2><TrendingDown :size="18" />薄弱知识点</h2></div><TransitionGroup name="motion-list" tag="div" class="weak-row-list"><div v-for="(item, index) in analysis.weak_points || []" :key="item.knowledge_point" class="weak-row"><b>{{ rankNumber(index) }}</b><span>{{ item.knowledge_point }}</span><AppProgress :value="item.wrong_count" :max="weakMax" tone="danger" /><strong>{{ item.wrong_count }}</strong></div></TransitionGroup><button class="btn btn-ai btn-sm full" @click="go('teacherLessons')"><Sparkles :size="14" />生成练习</button></article></div>
          <article class="panel-card"><div class="panel-head"><h2><MessageCircle :size="18" />学生高频问题</h2><small>{{ analysisRange }}</small></div><div class="question-layout"><TransitionGroup name="cloud-list" tag="div" class="word-cloud"><span v-for="item in analysis.high_frequency_questions || []" :key="item.question" :style="{ fontSize: cloudSize(item.count) }">{{ item.question.slice(0, 12) }}</span></TransitionGroup><TransitionGroup name="motion-list" tag="div"><div v-for="(item, index) in analysis.high_frequency_questions || []" :key="item.question" class="question-row"><b>{{ rankPlain(index) }}</b><span>{{ item.question }}</span><strong>{{ item.count }}次</strong></div></TransitionGroup></div></article>
          <div class="analysis-grid three"><article class="panel-card"><div class="panel-head"><h2><ClipboardList :size="18" />成绩分布</h2></div><AdminChart type="bar" :labels="scoreLabels" :series="scoreSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><CheckCircle :size="18" />测验完成</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><XCircle :size="18" />错题分布</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="220" /></article></div>
          <article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生活跃度</h2><button class="btn btn-ghost btn-sm" :data-loading="isPending('batch-remind')" :disabled="isPending('batch-remind')" @click="batchRemind"><Bell :size="14" />批量提醒</button></div><div class="activity-layers"><LayerCard label="高度活跃" :value="analysis.student_layers?.high || 0" tone="success" /><LayerCard label="正常活跃" :value="analysis.student_layers?.normal || 0" /><LayerCard label="低活跃" :value="analysis.student_layers?.low || 0" tone="warning" /><LayerCard label="长期未活跃" :value="analysis.student_layers?.inactive || 0" tone="danger" /></div></article>
        </template>
      </section>

      <section v-if="active === 'teacherProfile'" key="teacherProfile" class="teacher-content profile-content">
        <article class="profile-card"><span class="avatar large">{{ firstChar(teacherName) }}<Camera :size="18" /></span><div><h1>{{ profileForm.nickname }}<span class="tag tag-primary">教师</span></h1><p><Mail :size="15" />{{ user.email }}</p><p><IdCard :size="15" />{{ user.employee_no || '-' }}</p><small><Clock :size="14" />{{ registeredDays }} 天</small></div><button class="btn btn-secondary btn-sm" @click="profileEditing = true"><Pencil :size="14" />编辑信息</button></article>
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
        <article class="modal">
          <div class="modal-head"><Upload :size="20" /><h2>上传课程资料</h2><button class="icon-action" @click="uploadOpen = false"><X :size="16" />关闭</button></div>
          <label class="upload-drop"><Upload :size="40" /><span>拖拽上传</span><input type="file" multiple @change="pickUploadFiles" /></label>
          <TransitionGroup name="motion-list" tag="div" class="upload-list">
            <div v-for="item in uploadQueue" :key="item.id" class="upload-row"><File :size="18" /><span>{{ item.file.name }}</span><small>{{ sizeLabel(item.file.size) }}</small><AppSelect v-model="item.chapter_id" :options="uploadChapterOptions" /><AppSelect v-model="item.category" :options="materialCategoryOptions" /><button class="icon-action danger" @click="removeUpload(item.id)"><Trash2 :size="15" />移除</button></div>
          </TransitionGroup>
          <footer><button class="btn btn-ghost" @click="uploadOpen = false">取消</button><button class="btn btn-primary" :data-loading="isPending('upload-materials')" :disabled="!uploadQueue.length || isPending('upload-materials')" @click="uploadMaterials">确认上传</button></footer>
        </article>
      </div>
    </Transition>

    <Transition name="drawer">
      <aside v-if="studentDrawer" class="drawer">
        <div class="drawer-head"><span class="avatar">{{ firstChar(studentDrawer.student.nickname) }}</span><div><h2>{{ studentDrawer.student.nickname }}</h2><small>{{ studentDrawer.student.student_no || '-' }} · {{ studentDrawer.student.email }}</small></div><button class="icon-action" @click="studentDrawer = null"><X :size="16" />关闭</button></div>
        <div class="profile-tabs small-tabs"><button :class="{ active: studentTab === 'base' }" @click="studentTab = 'base'">基本信息</button><button :class="{ active: studentTab === 'data' }" @click="studentTab = 'data'">学习数据</button><button :class="{ active: studentTab === 'qa' }" @click="studentTab = 'qa'">问答记录</button></div>
        <Transition name="fade-slide" mode="out-in">
          <section v-if="studentTab === 'base'" key="base" class="drawer-body"><InfoRow label="加入时间" :value="formatTime(studentDrawer.membership.joined_at)" /><InfoRow label="加入方式" value="课程码" /><InfoRow label="邮箱" :value="studentDrawer.student.email" /><InfoRow label="学号" :value="studentDrawer.student.student_no || '-'" /><div class="drawer-actions"><button class="btn btn-secondary" :data-loading="isPending(`remind-student-${studentDrawer.student.id}`)" :disabled="isPending(`remind-student-${studentDrawer.student.id}`)" @click="remindStudent(studentDrawer.student.id)"><Bell :size="16" />发送提醒</button><button class="btn btn-danger" :data-loading="isPending(`remove-student-${studentDrawer.student.id}`)" :disabled="isPending(`remove-student-${studentDrawer.student.id}`)" @click="removeStudent(studentDrawer.student.id)">移出课程</button></div></section>
          <section v-else-if="studentTab === 'data'" key="data" class="drawer-body"><TransitionGroup name="motion-list" tag="div" class="drawer-progress-list"><div v-for="item in studentDrawer.lesson_progress" :key="item.lesson.id" class="drawer-progress"><span>{{ item.lesson.title }}</span><ProgressBar :value="item.progress_percent" /><small>{{ item.current_page }}/{{ item.lesson.page_count }}</small></div></TransitionGroup><div class="drawer-stats">提问 {{ studentDrawer.stats.qa_total }} · 测验 {{ studentDrawer.stats.attempt_total }} · 平均 {{ studentDrawer.stats.average_score }} · 错题 {{ studentDrawer.stats.wrong_total }}</div><TransitionGroup name="motion-list" tag="div" class="tag-list"><span v-for="item in studentDrawer.weak_points" :key="item.name" class="tag tag-warning">{{ item.name }}</span></TransitionGroup></section>
          <section v-else key="qa" class="drawer-body"><TransitionGroup name="motion-list" tag="div" class="qa-record-list"><div v-for="item in studentDrawer.qa_records" :key="item.id" class="qa-record"><MessageCircle :size="16" /><div><strong>{{ item.question }}</strong><p>{{ item.answer }}</p><small>{{ formatTime(item.created_at) }}</small></div></div><EmptyState v-if="!studentDrawer.qa_records.length" key="empty" text="暂无问答" /></TransitionGroup></section>
        </Transition>
      </aside>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="previewItem" class="modal-mask"><article class="modal preview-modal"><div class="modal-head"><FileText :size="20" /><h2>{{ previewItem.title }}</h2><button class="icon-action" @click="previewItem = null"><X :size="16" />关闭</button></div><iframe v-if="previewItem.preview_url" :src="previewItem.preview_url"></iframe><EmptyState v-else text="暂无预览" /></article></div>
    </Transition>
    <Transition name="modal-pop">
      <div v-if="lessonPreview" class="modal-mask">
        <article class="modal lesson-preview-modal">
          <div class="modal-head"><Presentation :size="20" /><h2>{{ lessonPreview.lesson.title }}</h2><button class="icon-action" @click="lessonPreview = null"><X :size="16" />关闭</button></div>
          <div class="lesson-preview-layout">
            <aside>
              <button v-for="page in lessonPreview.pages" :key="page.id" :class="{ active: lessonPreviewPageId === page.id }" @click="lessonPreviewPageId = page.id">
                <span>{{ page.page_number }}</span>
                <strong>{{ page.page_title || `第${page.page_number}页` }}</strong>
              </button>
            </aside>
            <section v-if="lessonPreviewActivePage" class="lesson-preview-stage">
              <article><h3>{{ lessonPreviewActivePage.page_title || `第${lessonPreviewActivePage.page_number}页` }}</h3><p>{{ lessonPreviewActivePage.page_text }}</p></article>
              <article><h3>AI 讲解脚本</h3><p>{{ lessonPreviewActivePage.script_text || '暂无脚本' }}</p></article>
            </section>
            <EmptyState v-else text="该课时暂无页面" />
          </div>
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
  </section>
</template>

<script setup lang="ts">
import { TransitionGroup, computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch, type PropType } from "vue";
import { useRouter } from "vue-router";
import {
  Activity, AlertCircle, AlertTriangle, ArrowLeft, BarChart2, Bell, BookOpen, Camera, Check, CheckCircle,
  ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, Database, Download, Edit2, Eye, File,
  FileEdit, FileText, FolderOpen, GripVertical, Grid2X2, HelpCircle, Home, IdCard, Inbox, Layers, LayoutDashboard,
  Lock, LogOut, Mail, Maximize, MessageCircle, Pencil, Plus, PlusCircle, Presentation, RefreshCw,
  Search, Settings, Share2, SkipBack, SkipForward, Sparkles, Trash2, TrendingDown, Upload, User, UserPlus, UserX,
  Users, Volume2, Wand2, X, XCircle, ZoomIn
} from "lucide-vue-next";
import { api } from "../api/client";
import type { Course, CourseDetail, MaterialDetail, User as UserType } from "../types";
import AppCheckbox from "../components/AppCheckbox.vue";
import AppProgress from "../components/AppProgress.vue";
import AppSelect from "../components/AppSelect.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import PasswordField from "../components/PasswordField.vue";
import AdminChart from "./admin/AdminChart.vue";

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();
const router = useRouter();

const routeByKey: Record<string, string> = {
  teacherDashboard: "/teacher",
  teacherCourses: "/teacher/courses",
  teacherCourseForm: "/teacher/courses/new",
  teacherCourseHome: "/teacher/course",
  teacherMaterials: "/teacher/materials",
  teacherPpt: "/teacher/materials/workbench",
  teacherLessons: "/teacher/lessons",
  teacherStudents: "/teacher/students",
  teacherAnalytics: "/teacher/analytics",
  teacherProfile: "/teacher/profile"
};

const active = ref(props.pageKey || "teacherDashboard");
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
const pageLoading = ref(false);
const currentCourseId = ref<number>(Number(localStorage.getItem("teacher_current_course_id") || 0));
const courseMenuOpen = ref(false);
const userMenuOpen = ref(false);
const courseSwitchRef = ref<HTMLElement | null>(null);
const userMenuRef = ref<HTMLElement | null>(null);
const courseView = ref<"grid" | "list">("grid");
const materialView = ref<"grid" | "list">("list");
const selectedChapterId = ref(0);
const advancedOpen = ref(false);
const chapterKeyword = ref("");
const materialSort = ref("time");
const lessonSort = ref("created");
const uploadOpen = ref(false);
const uploadQueue = ref<Array<{ id: number; file: File; chapter_id: number; category: string }>>([]);
const removedChapterIds = ref<number[]>([]);
const previewItem = ref<any | null>(null);
const currentPageId = ref<number | null>(null);
const scriptDraft = ref("");
const analysisRange = ref("本月");
const analysisRangeOptions = ["本周", "本月", "本学期"];
const profileTab = ref<"base" | "security" | "notice">("base");
const profileEditing = ref(false);
const passwordConfirm = ref("");
const studentTab = ref<"base" | "data" | "qa">("base");
const pendingActions = reactive(new Set<string>());
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
let freshChapterTimer = 0;
let freshMaterialChapterTimer = 0;
let editorPulseTimer = 0;

const courseFilter = reactive({ keyword: "", term: "", status: "" });
const materialFilter = reactive({ keyword: "", type: "", status: "" });
const lessonFilter = reactive({ keyword: "", chapter_id: 0, status: "" });
const studentFilter = reactive({ keyword: "", progress: "", active: "" });
const courseForm = reactive({ id: 0, name: "", description: "", term: "2026春", cover_color: "#4F46E5", allow_leave: true, ai_qa: true, quiz_enabled: true, chapters: [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] as any[] });
const profileForm = reactive({ nickname: props.user.nickname, organization: "", department: "", bio: props.user.bio || "" });
const passwordForm = reactive({ old_password: "", new_password: "" });
const noticeSettings = reactive([{ key: "join", label: "学生加入课程", enabled: true }, { key: "ppt", label: "PPT 解析完成", enabled: true }, { key: "script", label: "脚本生成完成", enabled: false }, { key: "tts", label: "TTS 合成失败", enabled: true }, { key: "qa", label: "学生问答汇总", enabled: true }, { key: "ai", label: "AI 任务状态", enabled: true }, { key: "peak", label: "提问高峰", enabled: true }, { key: "system", label: "系统公告", enabled: true }]);

const palette = ["#4F46E5", "#10B981", "#F59E0B", "#06B6D4", "#8B5CF6", "#EF4444"];
const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const pageTitleMap: Record<string, string> = { teacherDashboard: "工作台首页", teacherCourses: "我的课程", teacherCourseForm: "创建课程", teacherCourseHome: "课程主页", teacherMaterials: "资料管理", teacherPpt: "PPT 工作台", teacherLessons: "课时管理", teacherStudents: "学生管理", teacherAnalytics: "教学分析", teacherProfile: "个人中心" };
const courseStatusOptions = [{ label: "全部", value: "" }, { label: "进行中", value: "active" }, { label: "已停用", value: "inactive" }];
const materialTypeOptions = [{ label: "全部", value: "" }, { label: "PPT", value: "pptx" }, { label: "PDF", value: "pdf" }, { label: "Word", value: "docx" }, { label: "TXT", value: "txt" }];
const materialStatusOptions = [{ label: "全部", value: "" }, { label: "已解析", value: "ready" }, { label: "解析中", value: "processing" }, { label: "解析失败", value: "failed" }];
const materialSortOptions = [{ label: "上传时间", value: "time" }, { label: "文件名", value: "name" }, { label: "文件大小", value: "size" }];
const materialCategoryOptions = [{ label: "课件", value: "courseware" }, { label: "讲义", value: "handout" }, { label: "习题", value: "exercise" }, { label: "参考资料", value: "reference" }];
const lessonStatusOptions = [{ label: "全部", value: "" }, { label: "已发布", value: "published" }, { label: "草稿", value: "ready" }];
const lessonSortOptions = [{ label: "创建时间", value: "created" }, { label: "发布时间", value: "published" }, { label: "学习人数", value: "students" }];
const studentProgressOptions = [{ label: "全部进度", value: "" }, { label: "未开始", value: "none" }, { label: "学习中", value: "learning" }, { label: "已完成", value: "done" }];
const studentActiveOptions = [{ label: "全部状态", value: "" }, { label: "活跃", value: "active" }, { label: "近期不活跃", value: "inactive" }, { label: "长期未活跃", value: "long" }];

const currentCourse = computed(() => courses.value.find((course) => course.id === currentCourseId.value) || courses.value[0] || null);
const pageTitle = computed(() => pageTitleMap[active.value] || "教师端");
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }));
const focusCount = computed(() => (dashboard.value.todos || []).length || courses.value.length);
const todoCount = computed(() => (dashboard.value.todos || []).length);
const courseTerms = computed(() => [...new Set(courses.value.map((course) => course.term).filter(Boolean))]);
const courseTermOptions = computed(() => [{ label: "全部学期", value: "" }, ...courseTerms.value.map((term) => ({ label: String(term), value: String(term) }))]);
const lessonChapterOptions = computed(() => [{ label: "全部章节", value: 0 }, ...(courseHome.value.chapters || []).map((chapter: any) => ({ label: chapter.title, value: chapter.id }))]);
const uploadChapterOptions = computed(() => [{ label: "章节", value: 0 }, ...(courseHome.value.chapters || []).map((chapter: any) => ({ label: chapter.title, value: chapter.id }))]);
const filteredCourses = computed(() => courses.value.filter((course) => (!courseFilter.keyword || course.name.includes(courseFilter.keyword)) && (!courseFilter.term || course.term === courseFilter.term) && (!courseFilter.status || course.status === courseFilter.status)));
const filteredChapters = computed(() => (materialSummary.value.chapters || []).filter((chapter: any) => !chapterKeyword.value || chapter.title.includes(chapterKeyword.value)));
const filteredMaterials = computed(() => {
  let rows = materials.value.filter((item) => (!selectedChapterId.value || item.chapter_id === selectedChapterId.value) && (!materialFilter.keyword || item.title.includes(materialFilter.keyword)) && (!materialFilter.type || item.material_type === materialFilter.type) && (!materialFilter.status || item.parse_status === materialFilter.status));
  if (materialSort.value === "name") rows = [...rows].sort((a, b) => a.title.localeCompare(b.title));
  if (materialSort.value === "size") rows = [...rows].sort((a, b) => b.size_bytes - a.size_bytes);
  return rows;
});
const filteredLessons = computed(() => {
  const rows = (courseHome.value.lessons || lessons.value).filter((lesson: any) => (!lessonFilter.keyword || lesson.title.includes(lessonFilter.keyword)) && (!lessonFilter.chapter_id || lesson.chapter_id === lessonFilter.chapter_id) && (!lessonFilter.status || lesson.status === lessonFilter.status));
  if (lessonSort.value === "published") return [...rows].sort((a: any, b: any) => new Date(b.published_at || b.created_at || 0).getTime() - new Date(a.published_at || a.created_at || 0).getTime());
  if (lessonSort.value === "students") return [...rows].sort((a: any, b: any) => Number(b.learned_count || 0) - Number(a.learned_count || 0));
  return [...rows].sort((a: any, b: any) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
});
const filteredStudents = computed(() => (studentPayload.value.items || []).filter((item: any) => {
  const nameMatch = !studentFilter.keyword || item.student.nickname.includes(studentFilter.keyword);
  const progressMatch = !studentFilter.progress || (studentFilter.progress === "none" ? item.progress_percent < 5 : studentFilter.progress === "done" ? item.progress_percent > 80 : item.progress_percent >= 5 && item.progress_percent <= 80);
  const activeMatch = !studentFilter.active || (studentFilter.active === "long" ? isLongInactive(item.last_study_at) : studentFilter.active === "active" ? !isLongInactive(item.last_study_at) : true);
  return nameMatch && progressMatch && activeMatch;
}));
const pages = computed<any[]>(() => materialDetail.value?.pages || []);
const currentPageIndex = computed(() => Math.max(0, pages.value.findIndex((page: any) => page.id === currentPageId.value)));
const activePage = computed(() => pages.value[currentPageIndex.value] || null);
const lessonPreviewActivePage = computed(() => lessonPreview.value?.pages?.find((page: any) => page.id === lessonPreviewPageId.value) || lessonPreview.value?.pages?.[0] || null);
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
const lessonAnalysisSeries = computed(() => [{ name: "完成率", data: (analysis.value.lesson_completion || []).map((item: any) => item.completion_rate || item.average_progress || 0), color: "#10B981" }]);
const analysisTimeLabels = computed(() => ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]);
const analysisTimeSeries = computed(() => [{ name: "分钟", data: [12, 18, 32, 28, 22, 14, 10], color: "#4F46E5" }]);
const weakLabels = computed(() => (analysis.value.weak_points || []).map((item: any) => item.knowledge_point));
const weakSeries = computed(() => [{ name: "错题", data: (analysis.value.weak_points || []).map((item: any) => item.wrong_count), color: "#EF4444" }]);
const weakMax = computed(() => Math.max(1, ...(analysis.value.weak_points || []).map((item: any) => item.wrong_count || 0)));
const scoreLabels = computed(() => (analysis.value.score_distribution || []).map((item: any) => item.range));
const scoreSeries = computed(() => [{ name: "人数", data: (analysis.value.score_distribution || []).map((item: any) => item.count), color: "#06B6D4" }]);
const registeredDays = computed(() => props.user.created_at ? Math.max(1, Math.floor((Date.now() - new Date(props.user.created_at).getTime()) / 86400000)) : 1);
const passwordStrength = computed(() => Math.min(100, Math.max(20, passwordForm.new_password.length * 10)));
const teacherName = computed(() => profileForm.nickname || props.user.nickname);

watch(activePage, (page) => {
  scriptDraft.value = page?.script_text || "";
  scriptUndoStack.value = [];
  scriptRedoStack.value = [];
}, { immediate: true });
watch(() => props.pageKey, (key) => { active.value = key || "teacherDashboard"; loadActive(); });
watch(currentCourseId, (id) => { if (id) localStorage.setItem("teacher_current_course_id", String(id)); });

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
  if (key !== "teacherPpt") {
    presentationMode.value = false;
    slideOverviewOpen.value = false;
    stageFocused.value = false;
  }
  await router.push(routeByKey[key] || "/teacher");
}
function openNotifications() {
  if (todoCount.value) {
    emit("notice", "info", `有 ${todoCount.value} 条待办事项`);
    go("teacherDashboard");
    return;
  }
  emit("notice", "info", "暂无新通知");
}
function openHelp() { emit("notice", "info", "教师端帮助已准备，可以从当前页面继续操作"); }
async function loadCourses() { courses.value = (await run(() => api.get<any[]>("/teacher/courses"))) || []; if ((!currentCourseId.value || !courses.value.some((course) => course.id === currentCourseId.value)) && courses.value[0]) currentCourseId.value = courses.value[0].id; }
async function loadDashboard() { dashboard.value = (await run(() => api.get("/teacher/dashboard"))) || {}; }
async function loadCourseHome() { if (!currentCourse.value) return; courseHome.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/home`))) || {}; lessons.value = courseHome.value.lessons || []; }
async function loadMaterials() { if (!currentCourse.value) return; materialSummary.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/materials/summary`))) || {}; materials.value = (await run(() => api.get<any[]>("/materials", { course_id: currentCourse.value.id, keyword: materialFilter.keyword, category: "" }))) || []; }
async function loadLessons() { await loadCourseHome(); }
async function loadStudents() { if (!currentCourse.value) return; studentPayload.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/students`))) || { stats: {}, items: [] }; }
async function loadAnalysis() { if (!currentCourse.value) return; const days = analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; analysis.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/analysis`, { days }))) || {}; }
async function refreshAnalysis() { await withAction("refresh-analysis", loadAnalysis); }
async function setAnalysisRange(value: string) {
  if (analysisRange.value === value) return;
  analysisRange.value = value;
  await withAction("analysis-range", loadAnalysis);
}
async function loadTeacherProfile() { const data = await run<any>(() => api.get("/teacher/profile")); if (!data) return; Object.assign(profileForm, { nickname: data.user?.nickname || profileForm.nickname, bio: data.user?.bio || "", organization: data.teacher_profile?.organization || "", department: data.teacher_profile?.department || "" }); if (Array.isArray(data.notification_settings)) noticeSettings.splice(0, noticeSettings.length, ...data.notification_settings); }
async function loadActive() {
  pageLoading.value = true;
  try {
    if (active.value === "teacherDashboard") await loadDashboard();
    if (active.value === "teacherCourses") await loadCourses();
    if (active.value === "teacherCourseHome") await loadCourseHome();
    if (active.value === "teacherMaterials") await loadMaterials();
    if (active.value === "teacherLessons") await loadLessons();
    if (active.value === "teacherStudents") await loadStudents();
    if (active.value === "teacherAnalytics") await loadAnalysis();
    if (active.value === "teacherProfile") await loadTeacherProfile();
  } finally {
    pageLoading.value = false;
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
function newCourse() { removedChapterIds.value = []; Object.assign(courseForm, { id: 0, name: "", description: "", term: "2026春", cover_color: "#4F46E5", allow_leave: true, ai_qa: true, quiz_enabled: true, chapters: [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] }); go("teacherCourseForm"); }
async function editCourse(course: any) {
  const detail = await withAction<CourseDetail>(`edit-course-${course.id}`, () => api.get(`/courses/${course.id}`));
  removedChapterIds.value = [];
  Object.assign(courseForm, { id: course.id, name: course.name, description: course.description || "", term: course.term, cover_color: course.cover_color || "#4F46E5", chapters: (detail?.chapters || []).length ? detail!.chapters.map((chapter: any) => ({ ...chapter, local_id: chapter.id })) : [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] });
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
async function saveCourse() {
  if (!courseForm.name.trim() || !courseForm.term.trim()) return emit("notice", "warning", "课程必填");
  await withAction("save-course", async () => {
    const payload = { name: courseForm.name, description: courseForm.description, term: courseForm.term };
    const course = courseForm.id ? await run<Course>(() => api.patch(`/courses/${courseForm.id}`, payload), "已保存") : await run<Course>(() => api.post("/courses", payload), "已创建");
    if (!course) return;
    currentCourseId.value = course.id;
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
async function deleteCourse() {
  if (!courseForm.id) return;
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
async function addChapterFromTree() {
  const title = `第${(courseHome.value.chapters || []).length + 1}章`;
  if (!currentCourse.value) return;
  await withAction("add-tree-chapter", async () => {
    const chapter = await run<any>(() => api.post(`/courses/${currentCourse.value!.id}/chapters`, { title, description: "", order_index: (courseHome.value.chapters || []).length + 1 }), "已添加");
    await loadMaterials();
    await loadCourseHome();
    markFreshMaterialChapter(chapter?.id || (materialSummary.value.chapters || []).find((item: any) => item.title === title)?.id);
  });
}
async function refreshMaterials() { await withAction("filter-materials", loadMaterials); }
function scheduleMaterialRefreshes() {
  [3500, 12000, 30000].forEach((delay) => {
    window.setTimeout(async () => {
      if (!currentCourse.value) return;
      await loadMaterials();
      await loadCourseHome();
    }, delay);
  });
}
function pickUploadFiles(event: Event) { const files = Array.from((event.target as HTMLInputElement).files || []); uploadQueue.value = files.map((file, index) => ({ id: Date.now() + index, file, chapter_id: selectedChapterId.value, category: "courseware" })); }
function removeUpload(id: number) { uploadQueue.value = uploadQueue.value.filter((item) => item.id !== id); }
async function uploadMaterials() {
  if (!currentCourse.value) return;
  await withAction("upload-materials", async () => {
    let successCount = 0;
    for (const item of uploadQueue.value) {
      const form = new FormData();
      form.set("course_id", String(currentCourse.value!.id));
      form.set("title", item.file.name.replace(/\.[^.]+$/, ""));
      form.set("category", item.category);
      if (item.chapter_id) form.set("chapter_id", String(item.chapter_id));
      form.set("file", item.file);
      const uploaded = await run(() => api.post("/materials", form));
      if (uploaded) successCount += 1;
    }
    if (!successCount) return;
    emit("notice", "success", successCount === uploadQueue.value.length ? "已上传" : `已上传 ${successCount}/${uploadQueue.value.length} 个文件`);
    uploadOpen.value = false;
    uploadQueue.value = [];
    await loadMaterials();
    await loadCourseHome();
    scheduleMaterialRefreshes();
  });
}
async function deleteMaterial(id: number) { await withAction(`delete-material-${id}`, async () => { await run(() => api.delete(`/materials/${id}`), "已删除"); await loadMaterials(); }); }
function previewMaterial(item: any) { previewItem.value = item; }
async function openPptWorkbench(materialId: number) {
  const detail = await withAction<MaterialDetail>(`open-ppt-${materialId}`, () => api.get(`/materials/${materialId}`));
  if (!detail) return;
  if (!(detail.pages || []).length) return emit("notice", "warning", "资料还没有可编辑页面，请等待解析完成或重新处理");
  workbenchMode.value = "material";
  materialDetail.value = detail;
  currentPageId.value = materialDetail.value?.pages[0]?.id || null;
  await go("teacherPpt");
}
async function openLessonWorkbench(lessonId: number) {
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
  if (!activePage.value) return;
  const pageId = activePage.value.id;
  const page = await withAction<any>(`save-script-${pageId}`, () => api.patch(`/materials/pages/${pageId}/script`, { script_text: scriptDraft.value }), ok);
  if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item: any) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; }
}
async function saveScript() { await saveCurrentScript("已审核"); }
async function synthesizeCurrent() { await saveCurrentScript("已合成"); }
async function regenCurrent() {
  if (!activePage.value) return;
  const pageId = activePage.value.id;
  const page = await withAction<any>(`regen-page-${pageId}`, () => api.post(`/materials/pages/${pageId}/script/regenerate`), "已生成");
  if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item: any) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; scriptDraft.value = page.script_text || ""; }
}
async function markAllReviewed() {
  await withAction("mark-all-reviewed", async () => {
    for (const page of pages.value) await run(() => api.patch(`/materials/pages/${page.id}/script`, { script_text: page.script_text || page.page_text }));
    emit("notice", "success", "已审核");
    if (workbenchMode.value === "material" && materialDetail.value?.material?.id) await openPptWorkbench(materialDetail.value.material.id);
    else if (materialDetail.value?.lesson_id) await openLessonWorkbench(materialDetail.value.lesson_id);
  });
}
async function publishLessonFromMaterial() { if (!materialDetail.value?.lesson_id) return emit("notice", "warning", "暂无可发布的课时"); await withAction("publish-lesson", () => api.post(`/lessons/${materialDetail.value!.lesson_id}/publish`), "已发布"); }
async function toggleLessonPublish(lesson: any) { await withAction(`toggle-lesson-${lesson.id}`, async () => { await run(() => api.post(`/lessons/${lesson.id}/${lesson.status === 'published' ? 'unpublish' : 'publish'}`), "已更新"); await loadLessons(); }); }
async function duplicateLesson(id: number) { await withAction(`duplicate-lesson-${id}`, async () => { await run(() => api.post(`/teacher/lessons/${id}/duplicate`), "已复制"); await loadLessons(); }); }
async function deleteLesson(id: number) { await withAction(`delete-lesson-${id}`, async () => { await run(() => api.delete(`/teacher/lessons/${id}`), "已删除"); await loadLessons(); }); }
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
async function remindStudent(id: number) { if (!currentCourse.value) return; await withAction(`remind-student-${id}`, () => api.post(`/teacher/courses/${currentCourse.value!.id}/students/${id}/remind`), "已提醒"); }
async function removeStudent(id: number) { if (!currentCourse.value) return; await withAction(`remove-student-${id}`, async () => { await run(() => api.delete(`/teacher/courses/${currentCourse.value!.id}/students/${id}`), "已移出"); studentDrawer.value = null; await loadStudents(); }); }
async function batchRemind() { await withAction("batch-remind", async () => { for (const item of filteredStudents.value) await run(() => api.post(`/teacher/courses/${currentCourse.value!.id}/students/${item.student.id}/remind`)); emit("notice", "success", "已提醒"); }); }
function clearStudentFilter() { Object.assign(studentFilter, { keyword: "", progress: "", active: "" }); }
async function exportCurrent() { if (!currentCourse.value) return; await withAction(`export-${active.value}`, async () => { if (active.value === "teacherStudents") await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/students/export`, `students-${currentCourse.value!.course_code}.csv`), "已导出"); if (active.value === "teacherAnalytics") { const days = analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/analysis/export`, `analysis-${currentCourse.value!.course_code}.csv`, { days }), "已导出"); } }); }
function retryTask() { emit("notice", "info", "已重试"); }
function copyText(text: string) { navigator.clipboard?.writeText(text); emit("notice", "success", "已复制"); }
async function saveProfile() { const data = await withAction<any>("save-profile", () => api.patch("/teacher/profile", { nickname: profileForm.nickname, bio: profileForm.bio, organization: profileForm.organization, department: profileForm.department }), "已保存"); if (data) Object.assign(profileForm, { nickname: data.user?.nickname || profileForm.nickname, bio: data.user?.bio || "", organization: data.teacher_profile?.organization || "", department: data.teacher_profile?.department || "" }); profileEditing.value = false; }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); await withAction("change-password", async () => { await run(() => api.post("/auth/me/password", passwordForm), "已保存"); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }); }
async function saveNotice() { const data = await withAction<any[]>("save-notice", () => api.put("/teacher/profile/notifications", { settings: noticeSettings.map((item) => ({ key: item.key, enabled: item.enabled })) }), "已保存"); if (data) noticeSettings.splice(0, noticeSettings.length, ...data); }

function firstChar(value?: string) { return (value || "-").slice(0, 1); }
function shortName(value?: string) { return (value || "-").length > 12 ? `${(value || "").slice(0, 12)}...` : value || "-"; }
function rankPlain(index: string | number) { return Number(index) + 1; }
function rankNumber(index: string | number) { return String(rankPlain(index)).padStart(2, "0"); }
function cloudSize(count: string | number) { return `${14 + Math.min(Number(count) || 0, 20)}px`; }
function formatTime(value?: string | null) { return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-"; }
function shortDate(value?: string | null) { return value ? new Date(value).toLocaleDateString("zh-CN") : "-"; }
function relativeTime(value?: string | null) { if (!value) return "从未"; const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000)); if (seconds < 60) return "刚刚"; if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`; if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`; return `${Math.floor(seconds / 86400)}天前`; }
function statusClass(status?: string) { if (["ready", "published", "active", "success"].includes(String(status))) return "tag-success"; if (["pending", "processing", "review"].includes(String(status))) return "tag-warning"; if (["failed", "inactive", "disabled"].includes(String(status))) return "tag-danger"; return ""; }
function statusText(status?: string) { return { ready: "已解析", published: "已发布", active: "进行中", inactive: "已停用", pending: "待处理", processing: "处理中", failed: "失败", draft: "草稿" }[String(status)] || String(status || "-"); }
function courseColor(id: number) { return `linear-gradient(135deg, ${palette[id % palette.length]}, #0F172A)`; }
function heatOpacity(count: number) { return String(Math.min(1, 0.15 + count / 20)); }
function todoIcon(type: string) { return type === "error" ? AlertCircle : type === "lesson" ? Presentation : FileText; }
function fileIcon(type: string) { if (type === "pptx") return Presentation; if (type === "pdf") return FileText; if (type === "docx") return FileEdit; return File; }
function typeText(type: string) { return { pptx: "PPT", pdf: "PDF", docx: "Word", txt: "TXT" }[type] || type; }
function sizeLabel(size?: number) { const value = Number(size || 0); if (value < 1024) return `${value} B`; if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`; if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`; return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`; }
function chapterName(id?: number | null) { return (courseHome.value.chapters || []).find((chapter: any) => chapter.id === id)?.title || "未分章"; }
function isLongInactive(value?: string | null) { return !value || Date.now() - new Date(value).getTime() > 14 * 86400000; }

function onTeacherDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node;
  if (!courseSwitchRef.value?.contains(target)) courseMenuOpen.value = false;
  if (!userMenuRef.value?.contains(target)) userMenuOpen.value = false;
}
function onTeacherDocumentKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  courseMenuOpen.value = false;
  userMenuOpen.value = false;
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
});

const MetricCard = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, value: { type: [String, Number], required: true }, sub: { type: String, default: "" }, tone: { type: String, default: "primary" }, danger: { type: Boolean, default: false } }, setup(p) { return () => h("article", { class: ["metric-card", p.tone, p.danger ? "danger" : ""] }, [h("div", [h("span", { class: "metric-icon" }, [h(p.icon as any, { size: 20 })]), h("span", p.label)]), h("strong", String(p.value)), h("small", p.sub)]); } });
const EmptyState = defineComponent({ props: { text: { type: String, required: true }, success: { type: Boolean, default: false } }, setup(p, { slots }) { return () => h("div", { class: "empty" }, [p.success ? h(CheckCircle, { size: 30 }) : h(Inbox, { size: 30 }), h("span", p.text), slots.default?.()]); } });
const CourseRequired = defineComponent(() => () => h("div", { class: "empty page-empty" }, [h(BookOpen, { size: 48 }), h("span", "请选择课程")]));
const QuickAction = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, sub: { type: String, required: true } }, emits: ["click"], setup(p, { emit: update }) { return () => h("button", { class: "quick-action", onClick: () => update("click") }, [h(p.icon as any, { size: 22 }), h("strong", p.label), h("small", p.sub)]); } });
const TaskList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, emits: ["retry"], setup(p, { emit: update }) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "task-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.id || item.title, class: "task-item" }, [h(item.status === "ready" ? CheckCircle : item.status === "failed" ? XCircle : item.status === "processing" ? RefreshCw : Clock, { size: 16, class: item.status }), h("span", item.title), h("small", statusText(item.status)), item.status === "failed" ? h("button", { class: "link-btn", onClick: () => update("retry", item) }, "重试") : null])) : [h(EmptyState, { key: "empty", text: "暂无任务" })] }); } });
const LessonRows = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true }, studentTotal: { type: Number, required: true } }, emits: ["open"], setup(p, { emit: update }) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "lesson-rows" }, { default: () => p.items.length ? p.items.slice(0, 6).map((item, index) => {
  const progress = Math.round(Number(item.average_progress || 0));
  const progressTone: "success" | "warning" | "danger" = progress >= 70 ? "success" : progress >= 30 ? "warning" : "danger";
  return h("button", { key: item.id, class: "lesson-row", onClick: () => update("open", item) }, [
    h("span", { class: "lesson-index" }, [h("b", String(index + 1).padStart(2, "0")), h("i")]),
    h("span", { class: "lesson-body" }, [
      h("span", { class: "lesson-title-line" }, [h("strong", item.title), h("span", { class: ["tag", statusClass(item.status)] }, statusText(item.status))]),
      h("small", `${chapterName(item.chapter_id)} · ${item.page_count || 0} 页 · ${item.learned_count || 0}/${p.studentTotal} 人`),
      h("span", { class: "lesson-progress-line" }, [h(AppProgress, { value: progress, compact: true, tone: progressTone }), h("em", `${progress}%`)])
    ]),
    h("span", { class: "lesson-open-label" }, [h(Wand2, { size: 14 }), h("span", "脚本")])
  ]);
}) : [h(EmptyState, { key: "empty", text: "暂无课时" })] }); } });
const MaterialTypeList = defineComponent({ props: { stats: { type: Object as PropType<Record<string, number>>, required: true } }, setup(p) { return () => {
  const rows = ["pptx", "pdf", "docx", "txt"].map((type) => ({ type, count: Number(p.stats[type] || 0) }));
  const max = Math.max(1, ...rows.map((item) => item.count));
  return h(TransitionGroup, { name: "motion-list", tag: "div", class: "type-list" }, { default: () => rows.map((item) => h("div", { key: item.type, class: ["type-row", item.type] }, [
    h("span", { class: "type-icon" }, [h(fileIcon(item.type), { size: 16 })]),
    h("span", { class: "type-body" }, [h("strong", typeText(item.type)), h(AppProgress, { value: item.count, max, compact: true, tone: item.count ? "primary" : "danger" })]),
    h("b", `${item.count}份`)
  ])) });
}; } });
const ActivityList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "activity-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.id || `${item.tone}-${item.time}-${item.text}`, class: "activity-item" }, [h("i", { class: item.tone }), h("span", item.text), h("small", relativeTime(item.time))])) : [h(EmptyState, { key: "empty", text: "暂无活动" })] }); } });
const ProgressList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "progress-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.student.id, class: "student-progress-row" }, [h("span", { class: "avatar mini" }, firstChar(item.student.nickname)), h("strong", item.student.nickname), h(ProgressBar, { value: item.progress_percent }), h("small", `${item.progress_percent}%`)])) : [h(EmptyState, { key: "empty", text: "暂无学生" })] }); } });
const ProgressBar = defineComponent({ props: { value: { type: Number, required: true } }, setup(p) { return () => h(AppProgress, { class: "progress-bar", value: p.value, tone: p.value < 30 ? "danger" : p.value < 70 ? "warning" : "success" }); } });
const MaterialStatus = defineComponent({ props: { item: { type: Object, required: true } }, setup(p) { return () => h("small", { class: "material-status" }, p.item.parse_status === "ready" ? "脚本已生成 · 语音已合成" : p.item.parse_status === "processing" ? "正在生成脚本" : p.item.parse_status === "failed" ? "解析失败" : "待处理"); } });
const LayerCard = defineComponent({ props: { label: { type: String, required: true }, value: { type: Number, required: true }, tone: { type: String, default: "primary" } }, setup(p) { return () => h("article", { class: ["layer-card", p.tone] }, [h("strong", p.label), h("span", `${p.value} 人`), h(AppProgress, { value: p.value, max: Math.max(1, studentPayload.value.stats?.total || 1), tone: p.tone as any })]); } });
const InfoRow = defineComponent({ props: { label: { type: String, required: true }, value: { type: String, required: true } }, setup(p) { return () => h("div", { class: "info-row" }, [h("span", p.label), h("strong", p.value)]); } });
</script>

<style scoped>
.teacher-shell { min-width: 1280px; min-height: 100vh; background: var(--color-bg-page); color: var(--color-text-body); }
.teacher-header { position: fixed; inset: 0 0 auto; z-index: var(--z-sticky); height: 60px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: var(--color-bg-surface); padding: 0 24px; }
.brand, .header-actions, .user-menu > button, .course-switch > button, .breadcrumb > div, .page-actions, .panel-head h2, .todo-row, .script-row, .quick-action, .drawer-head { display: flex; align-items: center; gap: var(--space-2); }
.brand strong { color: var(--color-text-primary); font-size: 17px; font-weight: 600; }
.brand > i, .header-actions > i { width: 1px; height: 16px; background: var(--color-border-default); }
.logo-mark { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-ai-gradient); color: white; }
.course-switch, .user-menu { position: relative; }
.course-switch > button, .user-menu > button { border: 0; background: transparent; color: var(--color-text-body); }
.teacher-shell button,
.teacher-shell a.icon-action {
  transition: background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), opacity var(--duration-fast) var(--ease-out);
  will-change: transform;
}
.teacher-shell button:active:not(:disabled),
.teacher-shell a.icon-action:active {
  transform: scale(0.96);
  transition: transform var(--duration-fast) var(--ease-spring);
}
.teacher-shell button[data-loading="true"] { cursor: wait; }
.teacher-shell button[data-loading="true"] svg { opacity: 0.55; }
.icon-action[data-loading="true"]::before { position: absolute; }
.icon-action[data-loading="true"] > svg { opacity: 0; }
.course-popover, .user-popover { position: absolute; top: 38px; min-width: 220px; z-index: var(--z-popover); border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 8px; }
.course-popover button, .user-popover button { display: flex; width: 100%; align-items: center; gap: 8px; min-height: 34px; border: 0; border-radius: 8px; background: transparent; color: var(--color-text-body); padding: 0 10px; text-align: left; }
.course-popover button.active, .course-popover button:hover, .user-popover button:hover { background: var(--color-primary-50); color: var(--color-primary-700); }
.user-popover { right: 0; min-width: 160px; }
.icon-btn, .icon-action { position: relative; display: inline-flex; min-height: 34px; align-items: center; justify-content: center; gap: 6px; border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; color: var(--color-text-secondary); padding: 0 10px; font-size: var(--text-caption); font-weight: 500; line-height: 1; white-space: nowrap; }
.icon-btn:hover, .icon-action:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.icon-action.active { background: var(--color-primary-50); color: var(--color-primary-700); box-shadow: var(--shadow-focus); }
.icon-btn em { position: absolute; top: -5px; right: -5px; min-width: 16px; height: 16px; border-radius: 8px; background: var(--color-danger-500); color: white; font-size: 10px; font-style: normal; line-height: 16px; text-align: center; }
.avatar { display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-ai-gradient); color: white; font-weight: 700; }
.avatar.mini { width: 24px; height: 24px; font-size: 12px; }
.avatar.large { position: relative; width: 80px; height: 80px; font-size: 26px; }
.avatar.large svg { position: absolute; right: 0; bottom: 0; border-radius: 50%; background: var(--color-primary-600); padding: 4px; }
.teacher-sidebar { position: fixed; top: 60px; left: 0; bottom: 0; width: 240px; min-height: 0; overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain; border-right: 1px solid var(--color-border-default); background: white; padding: 18px 12px; }
.nav-group { display: grid; gap: 2px; padding: 12px 0; border-bottom: 1px solid var(--color-border-subtle); }
.nav-group > span { padding: 0 12px 8px; color: var(--color-text-muted); font-size: var(--text-overline); font-weight: 600; }
.course-title { display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-style: normal; border-radius: var(--radius-md); transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out); }
.course-title:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.course-title:active { transform: scale(0.98); }
.nav-group button { position: relative; display: flex; height: 40px; align-items: center; gap: 8px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-secondary); padding: 0 12px; text-align: left; }
.nav-group button:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.nav-group button.active { background: var(--color-primary-50); color: var(--color-primary-700); font-weight: 500; }
.nav-group button.active::before { content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: var(--color-primary-600); }
.nav-group button:disabled { opacity: 0.45; }
.teacher-main { margin-left: 240px; padding-top: 60px; }
.teacher-main.immersive { padding-top: 60px; }
.teacher-page-stack { display: contents; }
.teacher-page-loading {
  position: fixed;
  top: 72px;
  right: 32px;
  z-index: var(--z-fixed);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-full);
  background: rgba(255,255,255,0.92);
  box-shadow: var(--shadow-md);
  padding: 0 14px;
  backdrop-filter: blur(8px);
}
.teacher-page-loading::after { content: "加载中"; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.breadcrumb { height: 56px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: white; padding: 0 32px; }
.breadcrumb span { color: var(--color-text-secondary); }
.breadcrumb strong { color: var(--color-text-primary); }
.teacher-content { display: grid; gap: 16px; padding: 32px 32px 64px; animation: fade-slide-up var(--duration-base) var(--ease-out); }
.welcome { height: 88px; display: flex; align-items: center; justify-content: space-between; border-radius: var(--radius-xl); color: white; background: var(--color-ai-gradient); padding: 0 32px; }
.welcome > div { display: flex; align-items: center; gap: 14px; }
.welcome h1 { margin: 0; font-size: var(--text-h2); }
.welcome p { margin: 3px 0 0; color: rgba(255,255,255,0.82); }
.white-btn { border-color: rgba(255,255,255,0.5); color: white; background: rgba(255,255,255,0.12); }
.metric-grid { display: grid; gap: 16px; }
.metric-grid.four { grid-template-columns: repeat(4, 1fr); }
.metric-grid.three { grid-template-columns: repeat(3, 1fr); }
.metric-grid.five { grid-template-columns: repeat(5, 1fr); }
.metric-card { min-height: 100px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 18px; }
.metric-card > div { display: flex; align-items: center; gap: 10px; color: var(--color-text-secondary); }
.metric-icon { display: inline-flex; width: 40px; height: 40px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-primary-50); color: var(--color-primary-600); }
.metric-card.success .metric-icon { background: var(--color-success-50); color: var(--color-success-700); }
.metric-card.warning .metric-icon { background: var(--color-warning-50); color: var(--color-warning-700); }
.metric-card.ai .metric-icon { background: var(--color-ai-light); color: #6D28D9; }
.metric-card.danger { background: var(--color-warning-50); border-color: var(--color-warning-100); }
.metric-card strong { display: block; margin-top: 12px; color: var(--color-text-primary); font-size: var(--text-display); line-height: 40px; }
.metric-card small { color: var(--color-text-muted); font-size: var(--text-body-sm); }
.compact .metric-card { min-height: 82px; }
.compact .metric-card strong { font-size: 24px; line-height: 30px; }
.dash-mid { display: grid; grid-template-columns: 60fr 40fr; gap: 16px; }
.bottom-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.panel-card, .filter-card, .table-card, .profile-card, .ai-suggestion { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 20px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.panel-head h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h4); }
.panel-head small { color: var(--color-text-muted); }
.link-btn { border: 0; background: transparent; color: var(--color-primary-700); font-weight: 500; }
.badge { min-width: 20px; height: 20px; border-radius: 10px; background: var(--color-danger-500); color: white; font-size: 12px; text-align: center; line-height: 20px; }
.recent-course-list, .todo-list, .script-list, .heat-body, .chapter-buttons, .upload-list, .weak-row-list, .notice-items, .drawer-progress-list, .qa-record-list { display: grid; gap: 8px; }
.recent-course { display: grid; grid-template-columns: 48px 1fr auto; align-items: center; gap: 12px; border-bottom: 1px solid var(--color-border-subtle); padding: 12px 0; }
.cover { display: inline-flex; width: 48px; height: 48px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-ai-gradient); color: white; }
.recent-course div { display: grid; gap: 4px; }
.recent-course strong { color: var(--color-text-primary); }
.recent-course small { color: var(--color-text-muted); }
.dashed-btn, .upload-drop { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; min-height: 48px; border: 1px dashed var(--color-border-strong); border-radius: var(--radius-lg); background: white; color: var(--color-primary-700); }
.todo-row { min-height: 52px; border-bottom: 1px solid var(--color-border-subtle); }
.todo-row i { width: 8px; height: 8px; border-radius: 50%; background: var(--color-info-500); }
.todo-row i.error { background: var(--color-danger-500); }
.todo-row i.lesson { background: var(--color-warning-500); }
.todo-row div { flex: 1; display: grid; }
.todo-row strong, .script-row strong { color: var(--color-text-primary); }
.todo-row small, .script-row small { color: var(--color-text-muted); }
.heatmap { display: grid; gap: 8px; }
.heat-head, .heat-row { display: grid; grid-template-columns: 90px repeat(7, 1fr); gap: 6px; align-items: center; }
.heat-head b { color: var(--color-text-muted); font-size: 11px; text-align: center; }
.heat-row span { color: var(--color-text-secondary); font-size: 12px; }
.heat-row i { height: 22px; border-radius: 5px; background: var(--color-primary-600); transition: opacity var(--duration-base) var(--ease-in-out), transform var(--duration-fast) var(--ease-out); }
.heat-row i:hover { transform: scale(1.08); }
.script-row { min-height: 48px; border-bottom: 1px solid var(--color-border-subtle); }
.script-row div { flex: 1; display: grid; }
.task-list { display: grid; gap: 8px; }
.task-item { display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: 8px; min-height: 34px; }
.task-item span { color: var(--color-text-body); }
.task-item small { color: var(--color-text-muted); }
.task-item .processing { color: var(--color-primary-600); animation: spin var(--duration-slower) linear infinite; }
.task-item .failed { color: var(--color-danger-500); }
.task-item .ready { color: var(--color-success-500); }
.filter-card { min-height: 56px; display: grid; grid-template-columns: 240px 140px 120px 1fr auto; align-items: center; gap: 10px; padding: 10px 14px; }
.search-box { display: flex; align-items: center; gap: 8px; height: 36px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: white; padding: 0 10px; }
.search-box input { width: 100%; border: 0; outline: 0; }
.search-box:focus-within { border-color: var(--color-primary-600); box-shadow: var(--shadow-focus); }
.search-box.small { height: 32px; }
.segmented-control { display: flex; background: var(--color-bg-muted); border-radius: var(--radius-md); padding: 4px; }
.segment-btn { min-height: 30px; border: 0; border-radius: 6px; background: transparent; color: var(--color-text-muted); padding: 6px 16px; font-size: 13px; font-weight: 500; transition: all var(--duration-fast) var(--ease-out); }
.segment-btn.active { background: white; color: var(--color-text-primary); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.view-toggle { display: inline-flex; overflow: hidden; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.view-toggle button { display: inline-flex; min-height: 32px; align-items: center; gap: 6px; border: 0; background: white; color: var(--color-text-secondary); padding: 0 12px; font-size: var(--text-caption); font-weight: 500; }
.view-toggle .active { background: var(--color-primary-600); color: white; }
.course-grid { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.course-card { overflow: hidden; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); }
.course-card.inactive .course-cover { filter: grayscale(1); opacity: 0.55; }
.course-cover { position: relative; aspect-ratio: 16 / 9; display: grid; place-items: center; color: white; }
.course-cover .tag:first-child { position: absolute; top: 12px; left: 12px; }
.course-cover .tag:nth-child(2) { position: absolute; top: 12px; right: 12px; }
.course-card section { padding: 16px; }
.course-card h2 { min-height: 42px; margin: 0 0 6px; color: var(--color-text-primary); font-size: 15px; }
code { font-family: var(--font-family-mono); color: var(--color-text-muted); }
.course-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 14px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.course-stats span { display: inline-flex; align-items: center; gap: 5px; }
.course-card footer { display: flex; justify-content: space-between; border-top: 1px solid var(--color-border-subtle); padding: 12px 16px; }
.table-card { overflow: auto; padding: 0; }
.teacher-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-sm); }
.teacher-table th, .teacher-table td { border-bottom: 1px solid var(--color-border-subtle); padding: 12px 14px; text-align: left; vertical-align: middle; }
.teacher-table th { background: var(--color-bg-muted); color: var(--color-text-secondary); font-weight: 600; }
.teacher-table tbody tr:nth-child(even):not(.inactive) { background: rgba(248, 250, 252, 0.72); }
.teacher-table tbody tr:hover { background: var(--color-primary-50); }
.teacher-table td svg { display: inline-block; vertical-align: middle; }
.teacher-table tr.inactive { background: var(--color-danger-50); }
.mini-cover { display: inline-block; width: 32px; height: 32px; border-radius: 8px; background: var(--color-ai-gradient); margin-right: 8px; vertical-align: middle; }
.form-content { padding-bottom: 90px; }
.course-form-layout { max-width: 960px; display: grid; grid-template-columns: 620px 280px; gap: 20px; margin: 0 auto; }
.form-panel { display: grid; gap: 22px; }
.form-section { display: grid; gap: 14px; }
.form-section h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h4); }
.form-section label, .advanced label, .profile-form label, .policy-form label { display: grid; gap: 6px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.color-row { display: flex; gap: 8px; }
.color-row button { width: 28px; height: 28px; border: 2px solid transparent; border-radius: 50%; }
.color-row button.active { border-color: var(--color-text-primary); }
.section-head { display: flex; align-items: center; justify-content: space-between; }
.chapter-edit-list { position: relative; display: grid; gap: 8px; }
.chapter-edit { display: grid; grid-template-columns: auto 1fr 76px auto; gap: 8px; align-items: center; border-radius: var(--radius-md); padding: 2px; transition: background var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out); }
.chapter-edit.just-added { animation: item-confirm 900ms var(--ease-out) both; }
.order-input { text-align: center; }
.advanced { overflow: hidden; border-top: 1px solid var(--color-border-subtle); padding-top: 12px; transition: border-color var(--duration-base) var(--ease-out), background var(--duration-base) var(--ease-out); }
.advanced.open { border-color: var(--color-primary-100); background: linear-gradient(180deg, var(--color-primary-50), transparent 58%); }
.advanced-trigger { display: flex; width: 100%; align-items: center; gap: 8px; color: var(--color-text-primary); font-weight: 600; text-align: left; }
.advanced-trigger svg:last-child { margin-left: auto; transition: transform var(--duration-fast) var(--ease-out); }
.advanced.open .advanced-trigger svg:last-child { transform: rotate(180deg); }
.advanced-body { display: grid; gap: 10px; padding-top: 12px; }
.advanced.open label { animation: fade-slide-up var(--duration-base) var(--ease-out) both; }
.preview-card .course-card { transform-origin: top left; width: 260px; box-shadow: none; }
.fixed-actions { position: fixed; left: 240px; right: 0; bottom: 0; z-index: var(--z-fixed); height: 64px; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--color-border-default); background: white; padding: 0 32px; }
.fixed-actions span { display: flex; align-items: center; gap: 6px; color: var(--color-warning-700); }
.fixed-actions div { display: flex; gap: 10px; }
.course-hero { min-height: 120px; display: grid; grid-template-columns: 80px 1fr auto; align-items: center; gap: 20px; border-radius: var(--radius-xl); color: white; padding: 20px 24px; }
.course-hero > span { display: inline-flex; width: 80px; height: 80px; align-items: center; justify-content: center; border-radius: var(--radius-xl); background: rgba(255,255,255,0.2); backdrop-filter: blur(8px); }
.course-hero h1 { margin: 0; font-size: 22px; }
.course-hero p, .course-hero small { display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.82); }
.course-hero section { display: flex; gap: 8px; }
.ghost-white { color: white; border-color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.1); }
.quick-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.quick-action { min-height: 72px; justify-content: flex-start; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 0 16px; text-align: left; }
.quick-action:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.quick-action strong { color: var(--color-text-primary); }
.quick-action small { color: var(--color-text-muted); }
.course-home-grid { display: grid; grid-template-columns: 45fr 32fr 23fr; align-items: stretch; gap: 16px; }
.course-bottom-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.home-lesson-card, .material-overview-card { position: relative; display: flex; min-height: 360px; flex-direction: column; gap: 14px; overflow: hidden; background: linear-gradient(180deg, #fff 0%, #F8FAFC 100%); }
.home-lesson-card::before, .material-overview-card::before { content: ""; position: absolute; inset: 0 0 auto; height: 3px; background: var(--color-ai-gradient); }
.rich-head { align-items: flex-start; margin-bottom: 0; }
.rich-head > div { display: grid; gap: 4px; min-width: 0; }
.rich-head h2 { display: flex; align-items: center; gap: 8px; }
.rich-head small { color: var(--color-text-muted); font-size: var(--text-caption); }
.home-card-action { margin-top: auto; }
.lesson-rows { position: relative; display: grid; gap: 11px; }
.lesson-row {
  position: relative;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: rgba(255,255,255,0.92);
  box-shadow: 0 1px 2px rgba(15,23,42,0.03);
  padding: 10px 12px;
  text-align: left;
}
.lesson-row:hover, .lesson-card:hover, .material-row:hover, .thumb-card:hover { border-color: var(--color-primary-200); box-shadow: var(--shadow-md); transform: translateY(-2px); }
.lesson-row:hover .lesson-open-label { background: var(--color-primary-600); color: white; }
.lesson-index { position: relative; display: grid; place-items: center; align-self: stretch; }
.lesson-index b { display: inline-flex; width: 34px; height: 34px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-primary-50); color: var(--color-primary-700); font-size: 12px; font-weight: 700; }
.lesson-index i { position: absolute; top: 46px; bottom: 0; width: 2px; border-radius: var(--radius-full); background: var(--color-primary-100); }
.lesson-body { display: grid; min-width: 0; gap: 7px; }
.lesson-title-line { display: flex; min-width: 0; align-items: center; gap: 8px; }
.lesson-title-line strong { overflow: hidden; color: var(--color-text-primary); font-size: 14px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.lesson-body small { color: var(--color-text-muted); font-size: 12px; }
.lesson-progress-line { display: grid; grid-template-columns: minmax(0, 1fr) 38px; align-items: center; gap: 8px; }
.lesson-progress-line em { color: var(--color-text-secondary); font-size: 12px; font-style: normal; font-weight: 600; text-align: right; }
.lesson-open-label { display: inline-flex; min-height: 30px; align-items: center; gap: 5px; border-radius: var(--radius-full); background: var(--color-bg-muted); color: var(--color-text-secondary); padding: 0 10px; font-size: 12px; font-weight: 600; transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out); }
.full { width: 100%; }
.material-health { display: grid; gap: 10px; border: 1px solid var(--color-primary-100); border-radius: var(--radius-lg); background: linear-gradient(135deg, var(--color-primary-50), white 70%); padding: 14px; }
.material-health div { display: flex; align-items: end; justify-content: space-between; gap: 10px; }
.material-health strong { color: var(--color-text-primary); font-size: 34px; line-height: 1; }
.material-health span { color: var(--color-text-secondary); font-size: var(--text-body-sm); font-weight: 600; }
.material-status-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.material-status-tile { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; min-height: 44px; border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); background: white; color: var(--color-text-secondary); padding: 0 10px; text-align: left; }
.material-status-tile:hover { border-color: var(--color-primary-200); box-shadow: var(--shadow-sm); transform: translateY(-1px); }
.material-status-tile strong { color: var(--color-text-primary); font-size: 18px; }
.material-status-tile.success svg { color: var(--color-success-500); }
.material-status-tile.warning svg { color: var(--color-warning-500); }
.material-status-tile.danger svg { color: var(--color-danger-500); }
.material-status-tile.primary svg { color: var(--color-primary-600); }
.type-list { display: grid; gap: 9px; border: 1px solid var(--color-border-subtle); border-radius: var(--radius-lg); background: rgba(255,255,255,0.9); padding: 10px; }
.type-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 9px; min-height: 38px; }
.type-icon { display: inline-flex; width: 30px; height: 30px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-bg-muted); color: var(--color-text-secondary); }
.type-row.pptx .type-icon { background: rgba(249,115,22,0.12); color: #EA580C; }
.type-row.pdf .type-icon { background: var(--color-danger-50); color: var(--color-danger-500); }
.type-row.docx .type-icon { background: rgba(14,165,233,0.12); color: var(--color-info-500); }
.type-body { display: grid; gap: 5px; min-width: 0; }
.type-body strong { color: var(--color-text-primary); font-size: 13px; }
.type-row b { color: var(--color-text-secondary); font-size: 12px; white-space: nowrap; }
.activity-list { display: grid; gap: 12px; }
.activity-item { display: grid; grid-template-columns: 10px 1fr auto; gap: 8px; align-items: center; }
.activity-item i { width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary-600); }
.activity-item i.success { background: var(--color-success-500); }
.activity-item span { color: var(--color-text-body); font-size: var(--text-body-sm); }
.activity-item small { color: var(--color-text-muted); font-size: 11px; }
.progress-list { display: grid; gap: 10px; }
.student-progress-row { display: grid; grid-template-columns: auto 90px 1fr 52px; align-items: center; gap: 8px; }
.materials-layout { min-height: 640px; display: grid; grid-template-columns: 220px 1fr; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); overflow: visible; }
.chapter-tree { display: grid; align-content: start; gap: 6px; border-right: 1px solid var(--color-border-default); padding: 12px; }
.chapter-tree button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; min-height: 40px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); text-align: left; padding: 0 10px; }
.chapter-tree button:hover { background: var(--color-bg-muted); }
.chapter-tree button.active { background: var(--color-primary-50); color: var(--color-primary-700); box-shadow: inset 3px 0 0 var(--color-primary-600); }
.chapter-tree button.empty { color: var(--color-text-muted); }
.chapter-tree button.just-added { animation: item-confirm 1100ms var(--ease-out) both; }
.materials-panel { position: relative; min-width: 0; overflow: visible; }
.materials-panel.panel-loading::after {
  content: "";
  position: absolute;
  top: 66px;
  right: 18px;
  z-index: 3;
  width: 18px;
  height: 18px;
  border: 2px solid var(--color-primary-100);
  border-top-color: var(--color-primary-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.material-filter { height: 52px; display: grid; grid-template-columns: 1fr 120px 130px 130px auto; align-items: center; gap: 10px; border-bottom: 1px solid var(--color-border-default); padding: 8px 12px; }
.material-list { position: relative; display: grid; align-content: start; }
.material-list.grid { grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 12px; }
.material-row { display: grid; grid-template-columns: 42px 1fr auto auto; align-items: center; gap: 12px; min-height: 64px; border-bottom: 1px solid var(--color-border-subtle); background: white; padding: 10px 14px; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out), background var(--duration-fast) var(--ease-out); }
.material-list.grid .material-row { border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.file-badge { display: inline-flex; width: 32px; height: 32px; align-items: center; justify-content: center; border-radius: var(--radius-md); color: white; background: var(--color-text-muted); }
.file-badge.pptx { background: #F97316; }.file-badge.pdf { background: var(--color-danger-500); }.file-badge.docx { background: var(--color-info-500); }
.material-row strong { color: var(--color-text-primary); }
.material-row small { display: block; color: var(--color-text-muted); }
.material-status { margin-top: 2px; }
.material-row section { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
.ppt-workbench { position: relative; height: calc(100vh - 60px); display: grid; grid-template-columns: 260px minmax(520px, 1fr) 420px; grid-template-rows: minmax(0, 1fr) 48px; overflow: hidden; background: #0F172A; transition: grid-template-columns var(--duration-slow) var(--ease-out), grid-template-rows var(--duration-slow) var(--ease-out); }
.ppt-workbench.presentation-mode { grid-template-columns: 0 minmax(0, 1fr) 0; grid-template-rows: 1fr 0; }
.ppt-workbench.presentation-mode .thumb-column,
.ppt-workbench.presentation-mode .script-panel {
  opacity: 0;
  pointer-events: none;
  transform: scale(0.96);
  border-color: transparent;
}
.ppt-workbench.presentation-mode .ppt-status {
  opacity: 0;
  pointer-events: none;
  transform: translateY(48px);
}
.ppt-head { position: fixed; top: 0; left: 0; right: 0; z-index: var(--z-fixed); height: 60px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid var(--color-border-default); background: white; padding: 0 18px; }
.ppt-empty-state { grid-column: 1 / -1; grid-row: 1 / -1; align-self: stretch; display: grid; place-items: center; align-content: center; gap: 12px; background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(248,250,252,0.94)); color: var(--color-text-secondary); text-align: center; padding: 32px; }
.ppt-empty-state svg { color: var(--color-primary-600); }
.ppt-empty-state h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.ppt-empty-state p { margin: 0 0 6px; }
.thumb-column, .script-panel { min-width: 0; min-height: 0; background: white; overflow: auto; transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out), border-color var(--duration-base) var(--ease-out); }
.thumb-column { border-right: 1px solid var(--color-border-default); padding: 12px; }
.thumb-top { display: grid; gap: 8px; margin-bottom: 12px; }
.thumb-list { position: relative; display: grid; gap: 8px; }
.thumb-card { position: relative; width: 100%; min-height: 108px; display: grid; grid-template-rows: 58px auto; gap: 7px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: white; padding: 8px; text-align: left; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out); }
.thumb-card.active { border-color: var(--color-primary-600); box-shadow: var(--shadow-focus); }
.thumb-card span { position: absolute; top: 6px; left: 6px; width: 30px; border-radius: 8px; background: var(--color-primary-600); color: white; padding: 0 6px; font-size: 11px; line-height: 18px; text-align: center; }
.thumb-card svg { position: absolute; top: 6px; right: 6px; color: var(--color-success-500); }
.thumb-card div { height: 58px; display: grid; place-items: center; overflow: hidden; border-radius: 6px; background: linear-gradient(135deg, var(--color-primary-50), var(--color-bg-muted)); color: var(--color-text-secondary); padding: 8px 10px; text-align: center; }
.thumb-card small { color: var(--color-text-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.ppt-stage { position: relative; min-width: 0; display: grid; place-items: center; overflow: hidden; padding: 64px 28px; transition: background var(--duration-base) var(--ease-out); }
.ppt-stage.focused { background: radial-gradient(circle at center, rgba(79,70,229,0.18), transparent 60%); }
.stage-top, .stage-controls { position: absolute; left: 50%; transform: translateX(-50%); z-index: 5; display: flex; align-items: center; gap: 8px; border-radius: var(--radius-full); background: rgba(255,255,255,0.15); color: white; white-space: nowrap; backdrop-filter: blur(10px); padding: 8px 12px; }
.stage-top { top: 16px; }
.stage-controls { bottom: 16px; }
.stage-top .icon-action, .stage-controls .icon-action { min-height: 32px; border-color: rgba(255,255,255,0.22); background: rgba(255,255,255,0.08); color: white; padding: 0 10px; }
.stage-top .icon-action.active, .stage-controls .icon-action.active { background: rgba(255,255,255,0.9); color: var(--color-primary-700); }
.slide-preview-wrap {
  width: 100%;
  display: grid;
  place-items: center;
  transform: scale(var(--slide-scale, 1));
  transform-origin: center;
  transition: transform var(--duration-base) var(--ease-spring), filter var(--duration-base) var(--ease-out);
}
.slide-preview-wrap.focused { filter: drop-shadow(0 26px 54px rgba(79,70,229,0.32)); }
.slide-preview { width: min(860px, 90%); aspect-ratio: 16 / 9; display: grid; align-content: center; gap: 16px; border: 4px solid white; border-radius: 8px; background: white; box-shadow: 0 20px 50px rgba(0,0,0,0.35); padding: 48px; }
.slide-preview h2 { margin: 0; color: var(--color-text-primary); font-size: 28px; }
.slide-preview p { max-height: 48vh; overflow: auto; color: var(--color-text-body); font-size: 18px; line-height: 1.8; }
.slide-overview {
  position: absolute;
  inset: 64px 40px 72px;
  z-index: 4;
  overflow: auto;
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: var(--radius-lg);
  background: rgba(15,23,42,0.86);
  box-shadow: 0 22px 58px rgba(0,0,0,0.36);
  padding: 16px;
  backdrop-filter: blur(12px);
}
.slide-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 12px;
}
.slide-overview button {
  min-height: 92px;
  display: grid;
  align-content: start;
  gap: 8px;
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.1);
  color: white;
  padding: 12px;
  text-align: left;
}
.slide-overview button:hover,
.slide-overview button.active { border-color: rgba(255,255,255,0.72); background: rgba(255,255,255,0.18); transform: translateY(-2px); }
.slide-overview span { width: max-content; border-radius: 999px; background: var(--color-primary-600); padding: 1px 8px; font-size: 11px; }
.slide-overview strong { font-size: 13px; }
.slide-overview small { color: rgba(255,255,255,0.7); }
.script-panel { border-left: 1px solid var(--color-border-default); display: grid; grid-template-rows: auto auto auto minmax(0, 1fr) auto auto; overflow: hidden; }
.script-head { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--color-border-default); }
.script-head h2 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: var(--text-h4); }
.ai-strip { display: flex; align-items: center; gap: 8px; background: var(--color-ai-light); color: #6D28D9; padding: 10px 16px; font-size: var(--text-caption); }
.ai-strip button { margin-left: auto; border: 0; background: transparent; color: #6D28D9; }
.editor-toolbar { display: flex; gap: 6px; border-bottom: 1px solid var(--color-border-default); padding: 8px 12px; }
.editor-toolbar button { border: 1px solid var(--color-border-default); border-radius: 6px; background: white; padding: 4px 8px; }
.editor-toolbar button:hover { border-color: var(--color-primary-200); color: var(--color-primary-700); }
.editor-toolbar button.active { border-color: var(--color-primary-300); background: var(--color-primary-50); color: var(--color-primary-700); animation: item-confirm 550ms var(--ease-out) both; }
.script-editor { width: 100%; height: 100%; min-height: 0; overflow: auto; border: 0; outline: 0; background: #FAFAF7; color: var(--color-text-body); font-size: 15px; line-height: 1.75; resize: none; padding: 18px; transition: background var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out); }
.script-editor:focus { background: white; box-shadow: inset 0 0 0 2px var(--color-primary-100); }
.word-count { justify-self: end; color: var(--color-text-muted); padding: 4px 12px; }
.script-actions { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--color-border-default); padding: 10px 12px; }
.script-actions span { display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.ppt-status { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--color-border-default); background: white; padding: 0 16px; transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out); }
.ppt-status span { color: var(--color-text-secondary); }
.ppt-status div { display: flex; gap: 8px; }
.lesson-card-list { position: relative; display: grid; gap: 12px; }
.lesson-card { min-height: 108px; display: grid; grid-template-columns: 96px 1fr auto; align-items: center; gap: 16px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 16px; transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out); }
.lesson-thumb { width: 96px; height: 72px; display: grid; place-items: center; border-radius: 8px; background: #0F172A; color: white; font-size: 24px; font-weight: 700; }
.lesson-card h2 { margin: 0; display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); font-size: 15px; }
.lesson-card p { color: var(--color-text-secondary); margin: 6px 0 10px; }
.lesson-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px; max-width: 360px; }
.switch input { display: none; }
.switch span { position: relative; display: inline-block; width: 36px; height: 20px; border-radius: 10px; background: var(--color-border-strong); transition: background var(--duration-base) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-out); }
.switch span::after { content: ""; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: white; box-shadow: var(--shadow-xs); transition: transform var(--duration-base) var(--ease-spring); }
.switch input:checked + span { background: var(--color-success-500); }
.switch input:checked + span::after { transform: translateX(16px); }
.switch.loading span { box-shadow: var(--shadow-focus); }
.teacher-table .danger { color: var(--color-danger-700); }
.ai-suggestion { display: grid; grid-template-columns: auto 1fr auto auto; align-items: start; gap: 14px; border-left: 4px solid var(--color-ai-cyan); }
.ai-suggestion > span { color: #6D28D9; }
.ai-suggestion h2 { margin: 0 0 8px; color: var(--color-text-primary); font-size: var(--text-h4); }
.ai-suggestion p { margin: 0; color: var(--color-text-body); line-height: 1.7; }
.analysis-grid { display: grid; gap: 16px; }
.analysis-grid.two { grid-template-columns: repeat(2, 1fr); }
.analysis-grid.three { grid-template-columns: repeat(3, 1fr); }
.analysis-grid.knowledge { grid-template-columns: 40fr 60fr; }
.weak-row { display: grid; grid-template-columns: 34px 1fr 180px 50px; align-items: center; gap: 10px; min-height: 42px; }
.weak-row b { font-family: var(--font-family-mono); color: var(--color-text-muted); }
.question-layout { display: grid; grid-template-columns: 55fr 45fr; gap: 16px; }
.word-cloud { min-height: 320px; display: flex; flex-wrap: wrap; align-content: center; justify-content: center; gap: 12px; border-radius: var(--radius-lg); background: var(--color-bg-muted); padding: 18px; color: var(--color-primary-700); }
.word-cloud span { transition: transform var(--duration-base) var(--ease-out), color var(--duration-fast) var(--ease-out); }
.word-cloud span:hover { transform: translateY(-2px) scale(1.04); color: var(--color-primary-900); }
.question-row { display: grid; grid-template-columns: 28px 1fr 60px; align-items: center; gap: 8px; min-height: 44px; border-bottom: 1px solid var(--color-border-subtle); }
.question-row b { display: inline-flex; width: 24px; height: 24px; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-primary-600); color: white; }
.activity-layers { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.layer-card { display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 14px; }
.profile-content { max-width: 720px; margin: 0 auto; width: 100%; }
.profile-card { height: 140px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; border-radius: var(--radius-xl); }
.profile-card h1 { margin: 0; display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); font-size: 22px; }
.profile-card p, .profile-card small { display: flex; align-items: center; gap: 6px; margin: 4px 0; color: var(--color-text-muted); }
.profile-tabs { display: flex; border-bottom: 1px solid var(--color-border-default); }
.profile-tabs button { display: inline-flex; align-items: center; gap: 8px; min-height: 42px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-secondary); padding: 0 14px; }
.profile-tabs button.active { border-bottom-color: var(--color-primary-600); color: var(--color-primary-700); font-weight: 600; }
.profile-form, .notice-list { display: grid; gap: 14px; }
.profile-form footer { display: flex; justify-content: flex-end; gap: 10px; }
.strength { height: 6px; border-radius: 3px; background: var(--color-bg-muted); overflow: hidden; }
.strength i { display: block; height: 100%; background: var(--color-success-500); transition: width var(--duration-base) var(--ease-in-out), background var(--duration-fast) var(--ease-out); }
.notice-list label { display: flex; align-items: center; gap: 10px; min-height: 36px; }
.modal-mask { position: fixed; inset: 0; z-index: var(--z-modal-bg); display: grid; place-items: center; background: rgba(15,23,42,0.38); backdrop-filter: blur(6px); }
.modal { width: 640px; max-height: 90vh; overflow: auto; border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-xl); padding: 20px; }
.modal.preview-modal { width: 800px; height: 90vh; display: grid; grid-template-rows: auto 1fr; }
.preview-modal iframe { width: 100%; height: 100%; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.lesson-preview-modal { width: min(1040px, 92vw); height: min(760px, 90vh); display: grid; grid-template-rows: auto minmax(0, 1fr); }
.lesson-preview-layout { min-height: 0; display: grid; grid-template-columns: 230px minmax(0, 1fr); gap: 14px; }
.lesson-preview-layout aside { min-height: 0; overflow: auto; display: grid; align-content: start; gap: 8px; border-right: 1px solid var(--color-border-default); padding-right: 12px; }
.lesson-preview-layout aside button { display: grid; grid-template-columns: 30px 1fr; align-items: center; gap: 8px; min-height: 44px; border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); background: white; color: var(--color-text-secondary); padding: 0 10px; text-align: left; }
.lesson-preview-layout aside button:hover,
.lesson-preview-layout aside button.active { border-color: var(--color-primary-200); background: var(--color-primary-50); color: var(--color-primary-700); transform: translateY(-1px); }
.lesson-preview-layout aside span { display: inline-flex; height: 24px; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-bg-muted); font-size: 12px; font-weight: 700; }
.lesson-preview-layout aside strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lesson-preview-stage { min-height: 0; overflow: auto; display: grid; gap: 14px; padding-right: 4px; }
.lesson-preview-stage article { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: var(--color-bg-muted); padding: 16px; }
.lesson-preview-stage h3 { margin: 0 0 10px; color: var(--color-text-primary); font-size: var(--text-h4); }
.lesson-preview-stage p { margin: 0; white-space: pre-wrap; color: var(--color-text-body); line-height: 1.75; }
.modal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.modal-head h2 { flex: 1; margin: 0; font-size: var(--text-h3); color: var(--color-text-primary); }
.upload-drop { position: relative; height: 160px; flex-direction: column; color: var(--color-text-muted); margin-bottom: 14px; }
.upload-drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.upload-row { display: grid; grid-template-columns: auto 1fr 80px 140px 120px auto; align-items: center; gap: 8px; border-bottom: 1px solid var(--color-border-subtle); padding: 8px 0; }
.modal footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.drawer { position: fixed; top: 60px; right: 0; bottom: 0; z-index: var(--z-fixed); width: 520px; display: grid; grid-template-rows: auto auto 1fr; border-left: 1px solid var(--color-border-default); background: white; box-shadow: var(--shadow-xl); }
.drawer-head { padding: 16px; border-bottom: 1px solid var(--color-border-default); }
.drawer-head div { flex: 1; }
.drawer-head h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.drawer-head small { color: var(--color-text-muted); }
.small-tabs { padding: 0 12px; }
.drawer-body { overflow: auto; display: grid; align-content: start; gap: 14px; padding: 16px; }
.info-row, .drawer-progress { display: grid; grid-template-columns: 110px 1fr; gap: 10px; border-bottom: 1px solid var(--color-border-subtle); padding-bottom: 10px; }
.info-row span { color: var(--color-text-muted); }
.info-row strong { color: var(--color-text-primary); }
.drawer-actions { display: flex; gap: 10px; }
.drawer-progress { grid-template-columns: 150px 1fr 70px; align-items: center; }
.drawer-stats { border-radius: var(--radius-md); background: var(--color-bg-muted); padding: 12px; color: var(--color-text-secondary); }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.qa-record { display: grid; grid-template-columns: auto 1fr; gap: 10px; border-bottom: 1px solid var(--color-border-subtle); padding: 10px 0; }
.qa-record strong { color: var(--color-text-primary); }
.qa-record p { margin: 4px 0; color: var(--color-text-secondary); }
.qa-record small { color: var(--color-text-muted); }
.empty { min-height: 120px; display: grid; place-items: center; gap: 8px; color: var(--color-text-muted); text-align: center; }
.page-empty { border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; }
.tag { display: inline-flex; align-items: center; min-height: 22px; border-radius: var(--radius-full); background: var(--color-bg-muted); color: var(--color-text-secondary); padding: 0 8px; font-size: var(--text-caption); }
.tag-primary { background: var(--color-primary-50); color: var(--color-primary-700); }
.tag-success { background: var(--color-success-50); color: var(--color-success-700); }
.tag-warning { background: var(--color-warning-50); color: var(--color-warning-700); }
.tag-danger { background: var(--color-danger-50); color: var(--color-danger-700); }
.tag-ai { background: var(--color-ai-light); color: #6D28D9; border: 1px solid var(--color-ai-border); }
.motion-list-enter-active,
.motion-list-leave-active,
.chapter-list-enter-active,
.chapter-list-leave-active,
.material-list-motion-enter-active,
.material-list-motion-leave-active,
.thumb-list-enter-active,
.thumb-list-leave-active,
.cloud-list-enter-active,
.cloud-list-leave-active {
  transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out), filter var(--duration-base) var(--ease-out);
}
.motion-list-enter-from,
.motion-list-leave-to,
.chapter-list-enter-from,
.chapter-list-leave-to,
.material-list-motion-enter-from,
.material-list-motion-leave-to,
.thumb-list-enter-from,
.thumb-list-leave-to,
.cloud-list-enter-from,
.cloud-list-leave-to {
  opacity: 0;
  filter: blur(2px);
  transform: translateY(8px) scale(0.98);
}
.motion-list-move,
.chapter-list-move,
.material-list-motion-move,
.thumb-list-move,
.cloud-list-move,
.card-list-move,
.row-list-move {
  transition: transform var(--duration-base) var(--ease-out);
}
.card-list-enter-active,
.card-list-leave-active {
  transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out), filter var(--duration-base) var(--ease-out);
}
.card-list-enter-from,
.card-list-leave-to {
  opacity: 0;
  filter: blur(2px);
  transform: translateY(12px) scale(0.97);
}
.row-list-enter-active,
.row-list-leave-active {
  transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out), background var(--duration-base) var(--ease-out);
}
.row-list-enter-from,
.row-list-leave-to {
  opacity: 0;
  transform: translateX(10px);
}
.slide-flip-enter-active {
  transition: opacity var(--duration-base) var(--ease-out), transform var(--duration-base) var(--ease-out), filter var(--duration-base) var(--ease-out);
}
.slide-flip-leave-active {
  transition: opacity var(--duration-fast) var(--ease-in), transform var(--duration-fast) var(--ease-in), filter var(--duration-fast) var(--ease-in);
}
.slide-flip-enter-from {
  opacity: 0;
  filter: blur(3px);
  transform: translateY(16px) scale(0.98);
}
.slide-flip-leave-to {
  opacity: 0;
  filter: blur(2px);
  transform: translateY(-10px) scale(0.98);
}
@keyframes item-confirm {
  0% { background: var(--color-primary-50); box-shadow: 0 0 0 0 rgba(79,70,229,0.24); transform: translateY(-6px) scale(0.98); }
  55% { background: var(--color-primary-50); box-shadow: 0 0 0 6px rgba(79,70,229,0.08); transform: translateY(0) scale(1.01); }
  100% { background: transparent; box-shadow: 0 0 0 0 rgba(79,70,229,0); transform: translateY(0) scale(1); }
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
