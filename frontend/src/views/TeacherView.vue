<template>
  <section class="teacher-shell">
    <header class="teacher-header">
      <div class="brand">
        <span class="logo-mark"><Sparkles :size="17" /></span>
        <strong>课程学习助手</strong>
        <i></i>
        <div class="course-switch">
          <button @click="courseMenuOpen = !courseMenuOpen">{{ currentCourse?.name || '选择课程' }}<ChevronDown :size="16" /></button>
          <Transition name="popover">
            <div v-if="courseMenuOpen" class="course-popover">
              <button v-for="course in courses.slice(0, 8)" :key="course.id" :class="{ active: currentCourseId === course.id }" @click="selectCourse(course.id)">
                <Check v-if="currentCourseId === course.id" :size="15" />{{ course.name }}
              </button>
              <button @click="go('teacherCourseForm')"><Plus :size="15" />创建课程</button>
            </div>
          </Transition>
        </div>
      </div>
      <div class="header-actions">
        <button class="icon-btn" aria-label="通知"><Bell :size="20" /><em v-if="todoCount">{{ todoCount }}</em></button>
        <button class="icon-btn" aria-label="帮助"><HelpCircle :size="20" /></button>
        <i></i>
        <div class="user-menu">
          <button @click="userMenuOpen = !userMenuOpen"><span class="avatar">{{ firstChar(teacherName) }}</span><b>{{ teacherName }}</b><ChevronDown :size="16" /></button>
          <Transition name="popover">
            <div v-if="userMenuOpen" class="user-popover">
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
          <button :disabled="!currentCourse" :class="{ active: active === 'teacherLessons' }" @click="go('teacherLessons')"><Presentation :size="16" />课堂管理</button>
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
          <button v-if="active === 'teacherCourseForm'" class="btn btn-primary" @click="saveCourse">{{ courseForm.id ? '保存修改' : '创建课程' }}</button>
          <button v-if="active === 'teacherMaterials'" class="btn btn-primary" @click="uploadOpen = true"><Upload :size="16" />上传资料</button>
          <button v-if="active === 'teacherLessons'" class="btn btn-primary" @click="go('teacherMaterials')"><Plus :size="16" />从资料创建</button>
          <button v-if="active === 'teacherStudents'" class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出学生</button>
          <div v-if="active === 'teacherAnalytics'" class="segmented-control">
            <button v-for="item in analysisRangeOptions" :key="item" type="button" class="segment-btn" :class="{ active: analysisRange === item }" @click="setAnalysisRange(item)">{{ item }}</button>
          </div>
          <button v-if="active === 'teacherAnalytics'" class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出报告</button>
        </section>
      </div>

      <section v-if="active === 'teacherDashboard'" class="teacher-content">
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
            <div v-for="course in dashboard.recent_courses || []" :key="course.id" class="recent-course">
              <span class="cover"><BookOpen :size="20" /></span>
              <div><strong>{{ course.name }}</strong><small>{{ course.term }} · {{ course.student_count || 0 }}人</small><progress :value="course.published_rate || 0" max="100"></progress></div>
              <button class="btn btn-ghost btn-sm" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button>
            </div>
            <button class="dashed-btn" @click="newCourse"><Plus :size="16" />创建新课程</button>
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><ClipboardList :size="18" />待办事项</h2><span class="badge">{{ todoCount }}</span></div>
            <div v-for="todo in dashboard.todos || []" :key="`${todo.type}-${todo.title}`" class="todo-row">
              <i :class="todo.type"></i><component :is="todoIcon(todo.type)" :size="16" /><div><strong>{{ todo.title }}</strong><small>{{ formatTime(todo.created_at) }}</small></div><button class="link-btn" @click="selectCourse(todo.course_id, 'teacherLessons')">处理</button>
            </div>
            <EmptyState v-if="!(dashboard.todos || []).length" text="暂无待办" />
          </article>
        </div>
        <div class="bottom-grid">
          <article class="panel-card">
            <div class="panel-head"><h2><Activity :size="18" />本周学生动态</h2></div>
            <div class="heatmap">
              <div class="heat-head"><span></span><b v-for="day in weekdays" :key="day">{{ day }}</b></div>
              <div v-for="row in dashboard.weekly_activity || []" :key="row.course_id" class="heat-row">
                <span>{{ shortName(row.course_name) }}</span><i v-for="item in row.days" :key="item.day" :style="{ opacity: heatOpacity(item.count) }"></i>
              </div>
            </div>
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><FileEdit :size="18" />待审核脚本</h2><span class="tag tag-warning">{{ (dashboard.pending_scripts || []).length }}</span></div>
            <div v-for="item in dashboard.pending_scripts || []" :key="item.page_id" class="script-row"><Presentation :size="16" /><div><strong>{{ item.lesson_title }}</strong><small>第{{ item.page_number }}页</small></div><button class="link-btn" @click="openPptFromLesson(item.lesson_id)">审核</button></div>
            <EmptyState v-if="!(dashboard.pending_scripts || []).length" text="脚本已完成" success />
          </article>
          <article class="panel-card">
            <div class="panel-head"><h2><Sparkles :size="18" />AI 任务</h2><small>30秒</small></div>
            <TaskList :items="dashboard.ai_tasks || []" @retry="retryTask" />
          </article>
        </div>
      </section>

      <section v-if="active === 'teacherCourses'" class="teacher-content">
        <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="courseFilter.keyword" placeholder="搜索课程名称" /></div><select v-model="courseFilter.term" class="select"><option value="">全部学期</option><option v-for="term in courseTerms" :key="term" :value="term">{{ term }}</option></select><select v-model="courseFilter.status" class="select"><option value="">全部</option><option value="active">进行中</option><option value="inactive">已停用</option></select><span></span><div class="view-toggle"><button type="button" :class="{ active: courseView === 'grid' }" @click="courseView = 'grid'" aria-label="网格"><Grid2X2 :size="16" /></button><button type="button" :class="{ active: courseView === 'list' }" @click="courseView = 'list'" aria-label="列表"><FileText :size="16" /></button></div></article>
        <div v-if="courseView === 'grid'" class="course-grid">
          <article v-for="course in filteredCourses" :key="course.id" class="course-card" :class="{ inactive: course.status !== 'active' }">
            <div class="course-cover" :style="{ background: courseColor(course.id) }"><span class="tag">{{ course.term }}</span><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span><BookOpen :size="48" /></div>
            <section><h2>{{ course.name }}</h2><code>{{ course.course_code }}</code><div class="course-stats"><span><Users :size="15" />{{ course.student_count || 0 }}</span><span><Presentation :size="15" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</span><span><File :size="15" />{{ course.material_count || 0 }}</span><span><Check :size="15" />{{ course.published_rate || 0 }}%</span></div></section>
            <footer><button class="btn btn-primary btn-sm" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button><button class="icon-action" @click="editCourse(course)"><MoreHorizontal :size="16" /></button></footer>
          </article>
        </div>
        <article v-else class="table-card"><table class="teacher-table"><thead><tr><th>课程名称</th><th>学期</th><th>学生数</th><th>课堂数</th><th>资料数</th><th>状态</th><th>最近更新</th><th>操作</th></tr></thead><tbody><tr v-for="course in filteredCourses" :key="course.id"><td><span class="mini-cover"></span><strong>{{ course.name }}</strong><code>{{ course.course_code }}</code></td><td>{{ course.term }}</td><td><Users :size="14" />{{ course.student_count || 0 }}</td><td><Presentation :size="14" />{{ course.published_lesson_count || 0 }}/{{ course.lesson_count || 0 }}</td><td><File :size="14" />{{ course.material_count || 0 }}</td><td><span class="tag" :class="statusClass(course.status)">{{ statusText(course.status) }}</span></td><td>{{ relativeTime(course.updated_at) }}</td><td><button class="btn btn-primary btn-sm" @click="selectCourse(course.id, 'teacherCourseHome')">进入课程</button><button class="icon-action" @click="editCourse(course)"><Pencil :size="15" /></button></td></tr></tbody></table></article>
        <EmptyState v-if="!filteredCourses.length" text="还没有课程"><button class="btn btn-primary" @click="newCourse"><Plus :size="16" />创建课程</button></EmptyState>
      </section>

      <section v-if="active === 'teacherCourseForm'" class="teacher-content form-content">
        <section class="course-form-layout">
          <article class="panel-card form-panel">
            <div class="form-section"><h2>基本信息</h2><label>课程名称<input v-model="courseForm.name" class="input" maxlength="50" /></label><label>课程简介<textarea v-model="courseForm.description" class="textarea" maxlength="500"></textarea><small>{{ courseForm.description.length }} / 500</small></label><label>学期<input v-model="courseForm.term" class="input" /></label><label>课程封面色<div class="color-row"><button v-for="color in palette" :key="color" :style="{ background: color }" :class="{ active: courseForm.cover_color === color }" @click="courseForm.cover_color = color"></button></div></label></div>
            <div class="form-section"><div class="section-head"><h2><Layers :size="18" />课程章节</h2><button class="btn btn-ghost btn-sm" :disabled="courseForm.chapters.length >= 30" @click="addDraftChapter"><Plus :size="14" />添加章节</button></div><div v-for="(chapter, index) in courseForm.chapters" :key="chapter.local_id" class="chapter-edit"><GripVertical :size="15" /><input v-model="chapter.title" class="input" /><input v-model.number="chapter.order_index" class="input order-input" type="number" /><button class="icon-action danger" :disabled="courseForm.chapters.length <= 1" @click="removeDraftChapter(index)"><Trash2 :size="15" /></button></div></div>
            <details class="advanced"><summary><Settings :size="16" />高级设置</summary><label><input v-model="courseForm.allow_leave" type="checkbox" />学生退出</label><label><input v-model="courseForm.ai_qa" type="checkbox" />AI 问答</label><label><input v-model="courseForm.quiz_enabled" type="checkbox" />测验发布</label></details>
          </article>
          <aside class="panel-card preview-card"><div class="panel-head"><h2><Eye :size="18" />卡片预览</h2></div><article class="course-card preview"><div class="course-cover" :style="{ background: courseForm.cover_color }"><BookOpen :size="44" /></div><section><h2>{{ courseForm.name || '课程名称' }}</h2><code>{{ courseForm.id ? currentCourse?.course_code : 'A8K3Z' }}</code><div class="course-stats"><span><Layers :size="15" />{{ courseForm.chapters.length }}</span><span><Users :size="15" />0</span></div></section></article></aside>
        </section>
        <div class="fixed-actions"><span><Edit2 :size="15" />有未保存的更改</span><div><button class="btn btn-ghost" @click="go('teacherCourses')">取消</button><button v-if="courseForm.id" class="btn btn-danger" @click="deleteCourse">删除课程</button><button class="btn btn-secondary" @click="saveCourse">保存草稿</button><button class="btn btn-primary" @click="saveCourse">{{ courseForm.id ? '保存修改' : '创建课程' }}</button></div></div>
      </section>

      <section v-if="active === 'teacherCourseHome'" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="course-hero" :style="{ background: courseColor(currentCourse.id) }"><span><BookOpen :size="36" /></span><div><h1>{{ courseHome.course?.name || currentCourse.name }}</h1><p>{{ currentCourse.term }} · {{ currentCourse.course_code }}</p><small><Users :size="15" />{{ courseHome.quick_counts?.student_count || 0 }} 学生 <Presentation :size="15" />{{ courseHome.quick_counts?.lesson_count || 0 }} 课堂 <File :size="15" />{{ courseHome.quick_counts?.material_count || 0 }} 资料</small></div><section><button class="btn ghost-white" @click="editCourse(currentCourse)"><Pencil :size="16" />编辑课程</button><button class="btn ghost-white" @click="copyText(currentCourse.course_code)"><Share2 :size="16" />分享课程码</button></section></article>
          <div class="quick-grid"><QuickAction :icon="Upload" label="上传资料" sub="PPT/PDF/Word/TXT" @click="go('teacherMaterials')" /><QuickAction :icon="Presentation" label="管理课堂" sub="课堂发布" @click="go('teacherLessons')" /><QuickAction :icon="UserPlus" label="邀请学生" sub="课程码" @click="copyText(currentCourse.course_code)" /><QuickAction :icon="BarChart2" label="教学分析" sub="课程数据" @click="go('teacherAnalytics')" /></div>
          <div class="course-home-grid"><article class="panel-card lesson-list"><div class="panel-head"><h2><Presentation :size="18" />课堂列表</h2><button class="link-btn" @click="go('teacherLessons')">管理课堂</button></div><LessonRows :items="courseHome.lessons || []" :student-total="courseHome.quick_counts?.student_count || 0" @open="openLessonScript" /><button class="btn btn-primary btn-sm full" @click="go('teacherMaterials')"><Plus :size="14" />新建课堂</button></article><article class="panel-card"><div class="panel-head"><h2><FolderOpen :size="18" />资料状态</h2></div><AdminChart type="bar" :labels="materialStatusLabels" :series="materialStatusSeries" :height="190" /><MaterialTypeList :stats="courseHome.material_stats?.by_type || {}" /><button class="btn btn-secondary btn-sm full" @click="go('teacherMaterials')"><Upload :size="14" />上传资料</button></article><article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />近期活动</h2></div><ActivityList :items="courseHome.activities || []" /></article></div>
          <div class="course-bottom-grid"><article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生学习进度</h2><button class="link-btn" @click="go('teacherStudents')">查看详情</button></div><ProgressList :items="courseHome.student_progress || []" /></article><article class="panel-card"><div class="panel-head"><h2><Sparkles :size="18" />AI 任务队列</h2><span class="tag">{{ (courseHome.ai_tasks || []).length }}</span></div><TaskList :items="courseHome.ai_tasks || []" @retry="retryTask" /></article></div>
        </template>
      </section>

      <section v-if="active === 'teacherMaterials'" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid three compact"><MetricCard :icon="File" label="资料总数" :value="materialSummary.total || 0" sub="份" /><MetricCard :icon="Database" label="存储用量" :value="sizeLabel(materialSummary.size_bytes)" sub="课程资料" tone="success" /><MetricCard :icon="Sparkles" label="已解析" :value="`${materialSummary.ready || 0}/${materialSummary.total || 0}`" sub="AI" tone="ai" /></div>
          <div class="materials-layout"><aside class="chapter-tree"><div class="search-box small"><Search :size="15" /><input v-model="chapterKeyword" placeholder="搜索章节" /></div><button :class="{ active: selectedChapterId === 0 }" @click="selectedChapterId = 0"><FileText :size="16" />全部资料<span>{{ materialSummary.total || 0 }}</span></button><button v-for="chapter in filteredChapters" :key="chapter.id" :class="{ active: selectedChapterId === chapter.id, empty: !chapter.count }" @click="selectedChapterId = chapter.id"><Layers :size="16" />{{ chapter.title }}<span>{{ chapter.count }}</span></button><button @click="addChapterFromTree"><Plus :size="16" />添加章节</button></aside><section class="materials-panel"><div class="material-filter"><div class="search-box"><Search :size="16" /><input v-model="materialFilter.keyword" placeholder="搜索文件名" @keyup.enter="loadMaterials" /></div><select v-model="materialFilter.type" class="select"><option value="">全部</option><option value="pptx">PPT</option><option value="pdf">PDF</option><option value="docx">Word</option><option value="txt">TXT</option></select><select v-model="materialFilter.status" class="select"><option value="">全部</option><option value="ready">已解析</option><option value="processing">解析中</option><option value="failed">解析失败</option></select><select v-model="materialSort" class="select"><option value="time">上传时间</option><option value="name">文件名</option><option value="size">文件大小</option></select><div class="view-toggle"><button type="button" :class="{ active: materialView === 'grid' }" @click="materialView = 'grid'" aria-label="网格"><Grid2X2 :size="16" /></button><button type="button" :class="{ active: materialView === 'list' }" @click="materialView = 'list'" aria-label="列表"><FileText :size="16" /></button></div></div><div class="material-list" :class="materialView"><article v-for="item in filteredMaterials" :key="item.id" class="material-row"><span class="file-badge" :class="item.material_type"><component :is="fileIcon(item.material_type)" :size="18" /></span><div><strong>{{ item.title }}</strong><small>{{ chapterName(item.chapter_id) }} · {{ typeText(item.material_type) }} · {{ sizeLabel(item.size_bytes) }}</small><MaterialStatus :item="item" /></div><span class="tag" :class="statusClass(item.parse_status)">{{ statusText(item.parse_status) }}</span><section><button class="icon-action" @click="previewMaterial(item)"><Eye :size="15" /></button><button v-if="item.material_type === 'pptx'" class="icon-action" @click="openPptWorkbench(item.id)"><Wand2 :size="15" /></button><a v-if="item.preview_url" class="icon-action" :href="item.preview_url" target="_blank"><Download :size="15" /></a><button class="icon-action danger" @click="deleteMaterial(item.id)"><Trash2 :size="15" /></button></section></article><EmptyState v-if="!filteredMaterials.length" text="暂无资料" /></div></section></div>
        </template>
      </section>

      <section v-if="active === 'teacherPpt'" class="ppt-workbench">
        <header class="ppt-head"><button class="btn btn-ghost" @click="go('teacherMaterials')"><ArrowLeft :size="16" />返回资料管理</button><strong>{{ materialDetail?.material?.title || 'PPT 工作台' }}</strong></header>
        <aside class="thumb-column"><div class="thumb-top"><strong>{{ materialDetail?.material?.title || '-' }}</strong><small>{{ reviewedCount }}/{{ pages.length }} 页已审核</small><progress :value="reviewedCount" :max="Math.max(pages.length, 1)"></progress><label><input type="checkbox" @change="markAllReviewed" />全选审核</label><button class="btn btn-ghost btn-sm" @click="regenCurrent"><RefreshCw :size="14" />批量重新生成</button></div><button v-for="page in pages" :key="page.id" class="thumb-card" :class="{ active: currentPageId === page.id }" @click="currentPageId = page.id"><span>{{ page.page_number }}</span><div>{{ page.page_title || `第${page.page_number}页` }}</div><CheckCircle v-if="page.script_status === 'ready'" :size="16" /><Clock v-else :size="16" /><small>{{ page.script_text?.slice(0, 20) }}</small></button></aside>
        <main class="ppt-stage"><div class="stage-top"><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" /></button>第 {{ currentPageIndex + 1 }} / {{ pages.length }} 页<button class="icon-action" @click="nextPage"><ChevronRight :size="18" /></button><button class="icon-action"><ZoomIn :size="18" /></button><button class="icon-action"><Maximize :size="18" /></button></div><article class="slide-preview"><h2>{{ activePage?.page_title || `第${currentPageIndex + 1}页` }}</h2><p>{{ activePage?.page_text }}</p></article><div class="stage-controls"><button class="icon-action" @click="firstPage"><SkipBack :size="18" /></button><button class="icon-action" @click="prevPage"><ChevronLeft :size="18" /></button><button class="icon-action" @click="nextPage"><ChevronRight :size="18" /></button><button class="icon-action" @click="lastPage"><SkipForward :size="18" /></button><button class="icon-action"><Grid2X2 :size="18" /></button><button class="icon-action"><Presentation :size="18" /></button></div></main>
        <aside class="script-panel"><div class="script-head"><h2><FileEdit :size="18" />第 {{ activePage?.page_number || 1 }} 页</h2><span class="tag" :class="statusClass(activePage?.script_status)">{{ statusText(activePage?.script_status) }}</span></div><div class="ai-strip"><Sparkles :size="14" />AI 生成<button @click="regenCurrent">重新生成</button></div><div class="editor-toolbar"><button>B</button><button>I</button><button>段落</button><button>撤销</button><button>重做</button></div><textarea v-model="scriptDraft" class="script-editor"></textarea><small class="word-count">{{ scriptDraft.length }} 字</small><div class="script-actions"><span><Volume2 :size="16" />{{ activePage?.audio_url ? '已合成' : '未合成' }}</span><button class="btn btn-ghost btn-sm" @click="regenCurrent">重新生成</button><button class="btn btn-primary btn-sm" @click="saveScript">审核完成</button></div></aside>
        <footer class="ppt-status"><span>{{ materialDetail?.material?.title }} · 已审核 {{ reviewedCount }}/{{ pages.length }} 页 · 已保存</span><div><button class="btn btn-secondary btn-sm" @click="markAllReviewed">批量审核</button><button class="btn btn-ghost btn-sm" @click="regenCurrent">语音合成</button><button class="btn btn-primary btn-sm" @click="publishLessonFromMaterial">发布课堂</button></div></footer>
      </section>

      <section v-if="active === 'teacherLessons'" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="lessonFilter.keyword" placeholder="课堂名称" /></div><select v-model.number="lessonFilter.chapter_id" class="select"><option :value="0">全部章节</option><option v-for="chapter in courseHome.chapters || []" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option></select><select v-model="lessonFilter.status" class="select"><option value="">全部</option><option value="published">已发布</option><option value="ready">草稿</option></select><select v-model="lessonSort" class="select"><option value="created">创建时间</option><option value="published">发布时间</option><option value="students">学习人数</option></select></article>
          <div class="lesson-card-list"><article v-for="lesson in filteredLessons" :key="lesson.id" class="lesson-card"><div class="lesson-thumb">{{ lesson.page_count || 0 }}</div><section><h2>{{ lesson.title }}<span class="tag" :class="statusClass(lesson.status)">{{ statusText(lesson.status) }}</span></h2><p>{{ chapterName(lesson.chapter_id) }} · {{ lesson.page_count }}页 · {{ lesson.learned_count || 0 }}/{{ courseHome.quick_counts?.student_count || 0 }}人 · {{ shortDate(lesson.published_at || lesson.created_at) }}</p><progress :value="lesson.average_progress || 0" max="100"></progress></section><div class="lesson-actions"><button class="icon-action" @click="openLessonPreview(lesson.id)"><Presentation :size="16" /></button><button class="icon-action" @click="openLessonScript(lesson)"><Wand2 :size="16" /></button><button class="icon-action" @click="duplicateLesson(lesson.id)"><Copy :size="16" /></button><label class="switch"><input type="checkbox" :checked="lesson.status === 'published'" @change="toggleLessonPublish(lesson)" /><span></span></label><button class="icon-action danger" @click="deleteLesson(lesson.id)"><Trash2 :size="16" /></button></div></article><EmptyState v-if="!filteredLessons.length" text="暂无课堂" /></div>
        </template>
      </section>

      <section v-if="active === 'teacherStudents'" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <div class="metric-grid four compact"><MetricCard :icon="Users" label="学生总数" :value="studentPayload.stats?.total || 0" sub="本周新增" /><MetricCard :icon="Activity" label="活跃学生" :value="studentPayload.stats?.active_7d || 0" sub="近7天" tone="success" /><MetricCard :icon="CheckCircle" label="完成率" :value="`${studentPayload.stats?.average_completion || 0}%`" sub="平均" tone="success" /><MetricCard :icon="UserX" label="长期未活跃" :value="studentPayload.stats?.inactive_14d || 0" sub="14天" :danger="(studentPayload.stats?.inactive_14d || 0) > 0" /></div>
          <article class="filter-card"><div class="search-box"><Search :size="16" /><input v-model="studentFilter.keyword" placeholder="搜索学生姓名" /></div><select v-model="studentFilter.progress" class="select"><option value="">全部进度</option><option value="none">未开始</option><option value="learning">学习中</option><option value="done">已完成</option></select><select v-model="studentFilter.active" class="select"><option value="">全部状态</option><option value="active">活跃</option><option value="inactive">近期不活跃</option><option value="long">长期未活跃</option></select><button class="btn btn-ghost" @click="clearStudentFilter"><X :size="16" />清除</button><span></span><button class="btn btn-ghost" @click="batchRemind"><Bell :size="16" />批量提醒</button></article>
          <article class="table-card"><table class="teacher-table"><thead><tr><th>学生</th><th>加入时间</th><th>课堂进度</th><th>提问次数</th><th>错题数</th><th>最近学习</th><th>操作</th></tr></thead><tbody><tr v-for="item in filteredStudents" :key="item.student.id" :class="{ inactive: isLongInactive(item.last_study_at) }"><td><span class="avatar mini">{{ firstChar(item.student.nickname) }}</span><strong>{{ item.student.nickname }}</strong><code>{{ item.student.student_no || '-' }}</code></td><td>{{ shortDate(item.joined_at) }}</td><td><ProgressBar :value="item.progress_percent" />{{ item.studied_lessons }}/{{ item.lesson_total }}</td><td><MessageCircle :size="14" />{{ item.qa_count }}</td><td :class="{ danger: item.wrong_count > 10 }"><XCircle :size="14" />{{ item.wrong_count }}</td><td>{{ relativeTime(item.last_study_at) }}</td><td><button class="icon-action" @click="openStudent(item.student.id)"><Eye :size="15" /></button><button class="icon-action" @click="remindStudent(item.student.id)"><Bell :size="15" /></button></td></tr></tbody></table></article>
        </template>
      </section>

      <section v-if="active === 'teacherAnalytics'" class="teacher-content">
        <CourseRequired v-if="!currentCourse" />
        <template v-else>
          <article class="ai-suggestion"><span><Sparkles :size="20" /></span><div><h2>AI 教学建议</h2><p>{{ analysis.suggestion || '暂无建议' }}</p></div><button class="btn btn-ghost btn-sm" @click="loadAnalysis"><RefreshCw :size="14" />重新生成</button><span class="tag tag-ai">AI</span></article>
          <div class="metric-grid five compact"><MetricCard :icon="Activity" label="活跃率" :value="`${analysis.metrics?.active_rate || 0}%`" sub="近7天" /><MetricCard :icon="Presentation" label="完成率" :value="`${analysis.metrics?.completion_rate || 0}%`" sub="课堂" /><MetricCard :icon="MessageCircle" label="问答总量" :value="analysis.metrics?.qa_total || 0" sub="期间" /><MetricCard :icon="ClipboardList" label="平均分" :value="analysis.metrics?.average_score || 0" sub="/100" /><MetricCard :icon="AlertTriangle" label="薄弱点" :value="analysis.metrics?.weak_point_count || 0" sub="数量" :danger="(analysis.metrics?.weak_point_count || 0) > 0" /></div>
          <div class="analysis-grid two"><article class="panel-card"><div class="panel-head"><h2><Presentation :size="18" />课堂完成率</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="260" /></article><article class="panel-card"><div class="panel-head"><h2><Clock :size="18" />学习时长</h2></div><AdminChart type="line" :labels="analysisTimeLabels" :series="analysisTimeSeries" :height="260" /></article></div>
          <div class="analysis-grid knowledge"><article class="panel-card"><div class="panel-head"><h2><Layers :size="18" />章节掌握</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="260" /></article><article class="panel-card weak-list"><div class="panel-head"><h2><TrendingDown :size="18" />薄弱知识点</h2></div><div v-for="(item, index) in analysis.weak_points || []" :key="item.knowledge_point" class="weak-row"><b>{{ rankNumber(index) }}</b><span>{{ item.knowledge_point }}</span><progress :value="item.wrong_count" :max="weakMax"></progress><strong>{{ item.wrong_count }}</strong></div><button class="btn btn-ai btn-sm full" @click="go('teacherLessons')"><Sparkles :size="14" />生成练习</button></article></div>
          <article class="panel-card"><div class="panel-head"><h2><MessageCircle :size="18" />学生高频问题</h2><small>{{ analysisRange }}</small></div><div class="question-layout"><div class="word-cloud"><span v-for="item in analysis.high_frequency_questions || []" :key="item.question" :style="{ fontSize: cloudSize(item.count) }">{{ item.question.slice(0, 12) }}</span></div><div><div v-for="(item, index) in analysis.high_frequency_questions || []" :key="item.question" class="question-row"><b>{{ rankPlain(index) }}</b><span>{{ item.question }}</span><strong>{{ item.count }}次</strong></div></div></div></article>
          <div class="analysis-grid three"><article class="panel-card"><div class="panel-head"><h2><ClipboardList :size="18" />成绩分布</h2></div><AdminChart type="bar" :labels="scoreLabels" :series="scoreSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><CheckCircle :size="18" />测验完成</h2></div><AdminChart type="hbar" :labels="lessonAnalysisLabels" :series="lessonAnalysisSeries" :height="220" /></article><article class="panel-card"><div class="panel-head"><h2><XCircle :size="18" />错题分布</h2></div><AdminChart type="bar" :labels="weakLabels" :series="weakSeries" :height="220" /></article></div>
          <article class="panel-card"><div class="panel-head"><h2><Users :size="18" />学生活跃度</h2><button class="btn btn-ghost btn-sm" @click="batchRemind"><Bell :size="14" />批量提醒</button></div><div class="activity-layers"><LayerCard label="高度活跃" :value="analysis.student_layers?.high || 0" tone="success" /><LayerCard label="正常活跃" :value="analysis.student_layers?.normal || 0" /><LayerCard label="低活跃" :value="analysis.student_layers?.low || 0" tone="warning" /><LayerCard label="长期未活跃" :value="analysis.student_layers?.inactive || 0" tone="danger" /></div></article>
        </template>
      </section>

      <section v-if="active === 'teacherProfile'" class="teacher-content profile-content">
        <article class="profile-card"><span class="avatar large">{{ firstChar(teacherName) }}<Camera :size="18" /></span><div><h1>{{ profileForm.nickname }}<span class="tag tag-primary">教师</span></h1><p><Mail :size="15" />{{ user.email }}</p><p><IdCard :size="15" />{{ user.employee_no || '-' }}</p><small><Clock :size="14" />{{ registeredDays }} 天</small></div><button class="btn btn-secondary btn-sm" @click="profileEditing = true"><Pencil :size="14" />编辑信息</button></article>
        <div class="profile-tabs"><button :class="{ active: profileTab === 'base' }" @click="profileTab = 'base'"><User :size="16" />基本信息</button><button :class="{ active: profileTab === 'security' }" @click="profileTab = 'security'"><Lock :size="16" />账号安全</button><button :class="{ active: profileTab === 'notice' }" @click="profileTab = 'notice'"><Bell :size="16" />通知设置</button></div>
        <article v-if="profileTab === 'base'" class="panel-card profile-form"><label>姓名<input v-model="profileForm.nickname" class="input" :readonly="!profileEditing" /></label><label>邮箱<input :value="user.email" class="input" readonly /></label><label>学校/单位<input v-model="profileForm.organization" class="input" :readonly="!profileEditing" /></label><label>所在院系<input v-model="profileForm.department" class="input" :readonly="!profileEditing" /></label><label>个人简介<textarea v-model="profileForm.bio" class="textarea" :readonly="!profileEditing"></textarea></label><footer><button class="btn btn-ghost" @click="profileEditing = false">取消</button><button class="btn btn-primary" @click="saveProfile">保存修改</button></footer></article>
        <article v-if="profileTab === 'security'" class="panel-card profile-form"><div class="panel-head"><h2><Lock :size="18" />修改密码</h2></div><label>当前密码<input v-model="passwordForm.old_password" class="input" type="password" /></label><label>新密码<input v-model="passwordForm.new_password" class="input" type="password" /></label><div class="strength"><i :style="{ width: passwordStrength + '%' }"></i></div><label>确认新密码<input v-model="passwordConfirm" class="input" type="password" /></label><button class="btn btn-primary btn-sm" @click="changePassword">修改密码</button></article>
        <article v-if="profileTab === 'notice'" class="panel-card notice-list"><label v-for="item in noticeSettings" :key="item.key"><input v-model="item.enabled" type="checkbox" />{{ item.label }}</label><button class="btn btn-primary btn-sm" @click="saveNotice">保存设置</button></article>
      </section>
    </main>

    <div v-if="uploadOpen" class="modal-mask">
      <article class="modal">
        <div class="modal-head"><Upload :size="20" /><h2>上传课程资料</h2><button class="icon-action" @click="uploadOpen = false"><X :size="16" /></button></div>
        <label class="upload-drop"><Upload :size="40" /><span>拖拽上传</span><input type="file" multiple @change="pickUploadFiles" /></label>
        <div v-for="item in uploadQueue" :key="item.id" class="upload-row"><File :size="18" /><span>{{ item.file.name }}</span><small>{{ sizeLabel(item.file.size) }}</small><select v-model.number="item.chapter_id" class="select"><option :value="0">章节</option><option v-for="chapter in courseHome.chapters || []" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option></select><select v-model="item.category" class="select"><option value="courseware">课件</option><option value="handout">讲义</option><option value="exercise">习题</option><option value="reference">参考资料</option></select><button class="icon-action danger" @click="removeUpload(item.id)"><Trash2 :size="15" /></button></div>
        <footer><button class="btn btn-ghost" @click="uploadOpen = false">取消</button><button class="btn btn-primary" :disabled="!uploadQueue.length" @click="uploadMaterials">确认上传</button></footer>
      </article>
    </div>

    <aside v-if="studentDrawer" class="drawer">
      <div class="drawer-head"><span class="avatar">{{ firstChar(studentDrawer.student.nickname) }}</span><div><h2>{{ studentDrawer.student.nickname }}</h2><small>{{ studentDrawer.student.student_no || '-' }} · {{ studentDrawer.student.email }}</small></div><button class="icon-action" @click="studentDrawer = null"><X :size="16" /></button></div>
      <div class="profile-tabs small-tabs"><button :class="{ active: studentTab === 'base' }" @click="studentTab = 'base'">基本信息</button><button :class="{ active: studentTab === 'data' }" @click="studentTab = 'data'">学习数据</button><button :class="{ active: studentTab === 'qa' }" @click="studentTab = 'qa'">问答记录</button></div>
      <section v-if="studentTab === 'base'" class="drawer-body"><InfoRow label="加入时间" :value="formatTime(studentDrawer.membership.joined_at)" /><InfoRow label="加入方式" value="课程码" /><InfoRow label="邮箱" :value="studentDrawer.student.email" /><InfoRow label="学号" :value="studentDrawer.student.student_no || '-'" /><div class="drawer-actions"><button class="btn btn-secondary" @click="remindStudent(studentDrawer.student.id)"><Bell :size="16" />发送提醒</button><button class="btn btn-danger" @click="removeStudent(studentDrawer.student.id)">移出课程</button></div></section>
      <section v-if="studentTab === 'data'" class="drawer-body"><div v-for="item in studentDrawer.lesson_progress" :key="item.lesson.id" class="drawer-progress"><span>{{ item.lesson.title }}</span><ProgressBar :value="item.progress_percent" /><small>{{ item.current_page }}/{{ item.lesson.page_count }}</small></div><div class="drawer-stats">提问 {{ studentDrawer.stats.qa_total }} · 测验 {{ studentDrawer.stats.attempt_total }} · 平均 {{ studentDrawer.stats.average_score }} · 错题 {{ studentDrawer.stats.wrong_total }}</div><div class="tag-list"><span v-for="item in studentDrawer.weak_points" :key="item.name" class="tag tag-warning">{{ item.name }}</span></div></section>
      <section v-if="studentTab === 'qa'" class="drawer-body"><div v-for="item in studentDrawer.qa_records" :key="item.id" class="qa-record"><MessageCircle :size="16" /><div><strong>{{ item.question }}</strong><p>{{ item.answer }}</p><small>{{ formatTime(item.created_at) }}</small></div></div><EmptyState v-if="!studentDrawer.qa_records.length" text="暂无问答" /></section>
    </aside>

    <div v-if="previewItem" class="modal-mask"><article class="modal preview-modal"><div class="modal-head"><FileText :size="20" /><h2>{{ previewItem.title }}</h2><button class="icon-action" @click="previewItem = null"><X :size="16" /></button></div><iframe v-if="previewItem.preview_url" :src="previewItem.preview_url"></iframe><EmptyState v-else text="暂无预览" /></article></div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref, watch, type PropType } from "vue";
import { useRouter } from "vue-router";
import {
  Activity, AlertCircle, AlertTriangle, ArrowLeft, BarChart2, Bell, BookOpen, Camera, Check, CheckCircle,
  ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Clock, Copy, Database, Download, Edit2, Eye, File,
  FileEdit, FileText, FolderOpen, GripVertical, Grid2X2, HelpCircle, Home, IdCard, Inbox, Layers, LayoutDashboard,
  Lock, LogOut, Mail, Maximize, MessageCircle, MoreHorizontal, Pencil, Plus, PlusCircle, Presentation, RefreshCw,
  Search, Settings, Share2, SkipBack, SkipForward, Sparkles, Trash2, TrendingDown, Upload, User, UserPlus, UserX,
  Users, Volume2, Wand2, X, XCircle, ZoomIn
} from "lucide-vue-next";
import { api } from "../api/client";
import type { Course, CourseDetail, MaterialDetail, User as UserType } from "../types";
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
const materialDetail = ref<MaterialDetail | null>(null);
const lessons = ref<any[]>([]);
const studentPayload = ref<any>({ stats: {}, items: [] });
const studentDrawer = ref<any | null>(null);
const analysis = ref<any>({});
const currentCourseId = ref<number>(Number(localStorage.getItem("teacher_current_course_id") || 0));
const courseMenuOpen = ref(false);
const userMenuOpen = ref(false);
const courseView = ref<"grid" | "list">("grid");
const materialView = ref<"grid" | "list">("list");
const selectedChapterId = ref(0);
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
const pageTitleMap: Record<string, string> = { teacherDashboard: "工作台首页", teacherCourses: "我的课程", teacherCourseForm: "创建课程", teacherCourseHome: "课程主页", teacherMaterials: "资料管理", teacherPpt: "PPT 工作台", teacherLessons: "课堂管理", teacherStudents: "学生管理", teacherAnalytics: "教学分析", teacherProfile: "个人中心" };

const currentCourse = computed(() => courses.value.find((course) => course.id === currentCourseId.value) || courses.value[0] || null);
const pageTitle = computed(() => pageTitleMap[active.value] || "教师端");
const greeting = computed(() => { const hour = new Date().getHours(); if (hour < 12) return "早上好"; if (hour < 18) return "下午好"; return "晚上好"; });
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }));
const focusCount = computed(() => (dashboard.value.todos || []).length || courses.value.length);
const todoCount = computed(() => (dashboard.value.todos || []).length);
const courseTerms = computed(() => [...new Set(courses.value.map((course) => course.term).filter(Boolean))]);
const filteredCourses = computed(() => courses.value.filter((course) => (!courseFilter.keyword || course.name.includes(courseFilter.keyword)) && (!courseFilter.term || course.term === courseFilter.term) && (!courseFilter.status || course.status === courseFilter.status)));
const filteredChapters = computed(() => (materialSummary.value.chapters || []).filter((chapter: any) => !chapterKeyword.value || chapter.title.includes(chapterKeyword.value)));
const filteredMaterials = computed(() => {
  let rows = materials.value.filter((item) => (!selectedChapterId.value || item.chapter_id === selectedChapterId.value) && (!materialFilter.keyword || item.title.includes(materialFilter.keyword)) && (!materialFilter.type || item.material_type === materialFilter.type) && (!materialFilter.status || item.parse_status === materialFilter.status));
  if (materialSort.value === "name") rows = [...rows].sort((a, b) => a.title.localeCompare(b.title));
  if (materialSort.value === "size") rows = [...rows].sort((a, b) => b.size_bytes - a.size_bytes);
  return rows;
});
const filteredLessons = computed(() => (courseHome.value.lessons || lessons.value).filter((lesson: any) => (!lessonFilter.keyword || lesson.title.includes(lessonFilter.keyword)) && (!lessonFilter.chapter_id || lesson.chapter_id === lessonFilter.chapter_id) && (!lessonFilter.status || lesson.status === lessonFilter.status)));
const filteredStudents = computed(() => (studentPayload.value.items || []).filter((item: any) => {
  const nameMatch = !studentFilter.keyword || item.student.nickname.includes(studentFilter.keyword);
  const progressMatch = !studentFilter.progress || (studentFilter.progress === "none" ? item.progress_percent < 5 : studentFilter.progress === "done" ? item.progress_percent > 80 : item.progress_percent >= 5 && item.progress_percent <= 80);
  const activeMatch = !studentFilter.active || (studentFilter.active === "long" ? isLongInactive(item.last_study_at) : studentFilter.active === "active" ? !isLongInactive(item.last_study_at) : true);
  return nameMatch && progressMatch && activeMatch;
}));
const pages = computed(() => materialDetail.value?.pages || []);
const currentPageIndex = computed(() => Math.max(0, pages.value.findIndex((page) => page.id === currentPageId.value)));
const activePage = computed(() => pages.value[currentPageIndex.value] || null);
const reviewedCount = computed(() => pages.value.filter((page) => page.script_status === "ready").length);
const materialStatusLabels = computed(() => Object.keys(courseHome.value.material_stats?.by_status || {}));
const materialStatusSeries = computed(() => [{ name: "资料", data: Object.values(courseHome.value.material_stats?.by_status || {}).map(Number), color: "#4F46E5" }]);
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

watch(activePage, (page) => { scriptDraft.value = page?.script_text || ""; }, { immediate: true });
watch(() => props.pageKey, (key) => { active.value = key || "teacherDashboard"; loadActive(); });
watch(currentCourseId, (id) => { if (id) localStorage.setItem("teacher_current_course_id", String(id)); });

async function run<T>(task: () => Promise<T>, ok?: string) { try { const data = await task(); if (ok) emit("notice", "success", ok); return data; } catch (error) { emit("notice", "error", (error as Error).message); return null; } }
async function go(key: string) { await router.push(routeByKey[key] || "/teacher"); }
async function loadCourses() { courses.value = (await run(() => api.get<any[]>("/teacher/courses"))) || []; if ((!currentCourseId.value || !courses.value.some((course) => course.id === currentCourseId.value)) && courses.value[0]) currentCourseId.value = courses.value[0].id; }
async function loadDashboard() { dashboard.value = (await run(() => api.get("/teacher/dashboard"))) || {}; }
async function loadCourseHome() { if (!currentCourse.value) return; courseHome.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/home`))) || {}; lessons.value = courseHome.value.lessons || []; }
async function loadMaterials() { if (!currentCourse.value) return; materialSummary.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/materials/summary`))) || {}; materials.value = (await run(() => api.get<any[]>("/materials", { course_id: currentCourse.value.id, keyword: materialFilter.keyword, category: "" }))) || []; }
async function loadLessons() { await loadCourseHome(); }
async function loadStudents() { if (!currentCourse.value) return; studentPayload.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/students`))) || { stats: {}, items: [] }; }
async function loadAnalysis() { if (!currentCourse.value) return; const days = analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; analysis.value = (await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/analysis`, { days }))) || {}; }
async function setAnalysisRange(value: string) {
  if (analysisRange.value === value) return;
  analysisRange.value = value;
  await loadAnalysis();
}
async function loadTeacherProfile() { const data = await run<any>(() => api.get("/teacher/profile")); if (!data) return; Object.assign(profileForm, { nickname: data.user?.nickname || profileForm.nickname, bio: data.user?.bio || "", organization: data.teacher_profile?.organization || "", department: data.teacher_profile?.department || "" }); if (Array.isArray(data.notification_settings)) noticeSettings.splice(0, noticeSettings.length, ...data.notification_settings); }
async function loadActive() { if (active.value === "teacherDashboard") await loadDashboard(); if (active.value === "teacherCourses") await loadCourses(); if (active.value === "teacherCourseHome") await loadCourseHome(); if (active.value === "teacherMaterials") await loadMaterials(); if (active.value === "teacherLessons") await loadLessons(); if (active.value === "teacherStudents") await loadStudents(); if (active.value === "teacherAnalytics") await loadAnalysis(); if (active.value === "teacherProfile") await loadTeacherProfile(); }
async function selectCourse(id: number, target = active.value) { currentCourseId.value = id; courseMenuOpen.value = false; await loadCourseHome(); await go(target); }
async function enterRecentCourse() { if (currentCourse.value) await selectCourse(currentCourse.value.id, "teacherCourseHome"); else await go("teacherCourses"); }
function newCourse() { removedChapterIds.value = []; Object.assign(courseForm, { id: 0, name: "", description: "", term: "2026春", cover_color: "#4F46E5", allow_leave: true, ai_qa: true, quiz_enabled: true, chapters: [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] }); go("teacherCourseForm"); }
async function editCourse(course: any) { const detail = await run<CourseDetail>(() => api.get(`/courses/${course.id}`)); removedChapterIds.value = []; Object.assign(courseForm, { id: course.id, name: course.name, description: course.description || "", term: course.term, cover_color: course.cover_color || "#4F46E5", chapters: (detail?.chapters || []).length ? detail!.chapters.map((chapter: any) => ({ ...chapter, local_id: chapter.id })) : [{ local_id: Date.now(), id: 0, title: "第一章", order_index: 1 }] }); go("teacherCourseForm"); }
function addDraftChapter() { courseForm.chapters.push({ local_id: Date.now() + Math.random(), id: 0, title: `第${courseForm.chapters.length + 1}章`, order_index: courseForm.chapters.length + 1 }); }
function removeDraftChapter(index: number) { const [chapter] = courseForm.chapters.splice(index, 1); if (chapter?.id) removedChapterIds.value.push(chapter.id); }
async function saveCourse() { if (!courseForm.name.trim() || !courseForm.term.trim()) return emit("notice", "warning", "课程必填"); const payload = { name: courseForm.name, description: courseForm.description, term: courseForm.term }; const course = courseForm.id ? await run<Course>(() => api.patch(`/courses/${courseForm.id}`, payload), "已保存") : await run<Course>(() => api.post("/courses", payload), "已创建"); if (!course) return; currentCourseId.value = course.id; for (const chapterId of removedChapterIds.value) await run(() => api.delete(`/teacher/courses/${course.id}/chapters/${chapterId}`)); removedChapterIds.value = []; for (const chapter of courseForm.chapters) { if (!chapter.title.trim()) continue; if (chapter.id) await run(() => api.patch(`/teacher/courses/${course.id}/chapters/${chapter.id}`, { title: chapter.title, order_index: chapter.order_index })); else await run(() => api.post(`/courses/${course.id}/chapters`, { title: chapter.title, description: "", order_index: chapter.order_index })); } await loadCourses(); await selectCourse(course.id, "teacherCourseHome"); }
async function deleteCourse() { if (!courseForm.id || !window.confirm("确认删除？")) return; await run(() => api.delete(`/teacher/courses/${courseForm.id}`), "已删除"); currentCourseId.value = 0; await loadCourses(); await go("teacherCourses"); }
async function addChapterFromTree() { const title = `第${(courseHome.value.chapters || []).length + 1}章`; if (!currentCourse.value) return; await run(() => api.post(`/courses/${currentCourse.value.id}/chapters`, { title, description: "", order_index: (courseHome.value.chapters || []).length + 1 }), "已添加"); await loadMaterials(); await loadCourseHome(); }
function pickUploadFiles(event: Event) { const files = Array.from((event.target as HTMLInputElement).files || []); uploadQueue.value = files.map((file, index) => ({ id: Date.now() + index, file, chapter_id: selectedChapterId.value, category: "courseware" })); }
function removeUpload(id: number) { uploadQueue.value = uploadQueue.value.filter((item) => item.id !== id); }
async function uploadMaterials() { if (!currentCourse.value) return; for (const item of uploadQueue.value) { const form = new FormData(); form.set("course_id", String(currentCourse.value.id)); form.set("title", item.file.name.replace(/\.[^.]+$/, "")); form.set("category", item.category); if (item.chapter_id) form.set("chapter_id", String(item.chapter_id)); form.set("file", item.file); await run(() => api.post("/materials", form)); } emit("notice", "success", "已上传"); uploadOpen.value = false; uploadQueue.value = []; await loadMaterials(); await loadCourseHome(); }
async function deleteMaterial(id: number) { await run(() => api.delete(`/materials/${id}`), "已删除"); await loadMaterials(); }
function previewMaterial(item: any) { previewItem.value = item; }
async function openPptWorkbench(materialId: number) { materialDetail.value = await run<MaterialDetail>(() => api.get(`/materials/${materialId}`)); currentPageId.value = materialDetail.value?.pages[0]?.id || null; await go("teacherPpt"); }
async function openPptFromLesson(lessonId: number) { const lesson = (courseHome.value.lessons || []).find((item: any) => item.id === lessonId); if (lesson?.material_id) await openPptWorkbench(lesson.material_id); else await go("teacherLessons"); }
function openLessonScript(lesson: any) { if (lesson.material_id) openPptWorkbench(lesson.material_id); }
function prevPage() { const index = Math.max(0, currentPageIndex.value - 1); currentPageId.value = pages.value[index]?.id || null; }
function nextPage() { const index = Math.min(pages.value.length - 1, currentPageIndex.value + 1); currentPageId.value = pages.value[index]?.id || null; }
function firstPage() { currentPageId.value = pages.value[0]?.id || null; }
function lastPage() { currentPageId.value = pages.value[pages.value.length - 1]?.id || null; }
async function saveScript() { if (!activePage.value) return; const page = await run<any>(() => api.patch(`/materials/pages/${activePage.value.id}/script`, { script_text: scriptDraft.value }), "已审核"); if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; } }
async function regenCurrent() { if (!activePage.value) return; const page = await run<any>(() => api.post(`/materials/pages/${activePage.value.id}/script/regenerate`), "已生成"); if (page && materialDetail.value) { const index = materialDetail.value.pages.findIndex((item) => item.id === page.id); if (index >= 0) materialDetail.value.pages[index] = page; scriptDraft.value = page.script_text || ""; } }
async function markAllReviewed() { for (const page of pages.value) await run(() => api.patch(`/materials/pages/${page.id}/script`, { script_text: page.script_text || page.page_text })); emit("notice", "success", "已审核"); if (materialDetail.value) await openPptWorkbench(materialDetail.value.material.id); }
async function publishLessonFromMaterial() { if (!materialDetail.value?.lesson_id) return; await run(() => api.post(`/lessons/${materialDetail.value!.lesson_id}/publish`), "已发布"); }
async function toggleLessonPublish(lesson: any) { await run(() => api.post(`/lessons/${lesson.id}/${lesson.status === 'published' ? 'unpublish' : 'publish'}`), "已更新"); await loadLessons(); }
async function duplicateLesson(id: number) { await run(() => api.post(`/teacher/lessons/${id}/duplicate`), "已复制"); await loadLessons(); }
async function deleteLesson(id: number) { await run(() => api.delete(`/teacher/lessons/${id}`), "已删除"); await loadLessons(); }
async function openLessonPreview(id: number) { await run(() => api.get(`/lessons/${id}`)); emit("notice", "info", "已打开"); }
async function openStudent(id: number) { if (!currentCourse.value) return; studentDrawer.value = await run(() => api.get(`/teacher/courses/${currentCourse.value.id}/students/${id}`)); studentTab.value = "base"; }
async function remindStudent(id: number) { if (!currentCourse.value) return; await run(() => api.post(`/teacher/courses/${currentCourse.value.id}/students/${id}/remind`), "已提醒"); }
async function removeStudent(id: number) { if (!currentCourse.value) return; await run(() => api.delete(`/teacher/courses/${currentCourse.value.id}/students/${id}`), "已移出"); studentDrawer.value = null; await loadStudents(); }
async function batchRemind() { for (const item of filteredStudents.value) await remindStudent(item.student.id); }
function clearStudentFilter() { Object.assign(studentFilter, { keyword: "", progress: "", active: "" }); }
async function exportCurrent() { if (!currentCourse.value) return; if (active.value === "teacherStudents") await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/students/export`, `students-${currentCourse.value!.course_code}.csv`), "已导出"); if (active.value === "teacherAnalytics") { const days = analysisRange.value === "本周" ? 7 : analysisRange.value === "本月" ? 30 : 120; await run(() => api.download(`/teacher/courses/${currentCourse.value!.id}/analysis/export`, `analysis-${currentCourse.value!.course_code}.csv`, { days }), "已导出"); } }
function retryTask() { emit("notice", "info", "已重试"); }
function copyText(text: string) { navigator.clipboard?.writeText(text); emit("notice", "success", "已复制"); }
async function saveProfile() { const data = await run<any>(() => api.patch("/teacher/profile", { nickname: profileForm.nickname, bio: profileForm.bio, organization: profileForm.organization, department: profileForm.department }), "已保存"); if (data) Object.assign(profileForm, { nickname: data.user?.nickname || profileForm.nickname, bio: data.user?.bio || "", organization: data.teacher_profile?.organization || "", department: data.teacher_profile?.department || "" }); profileEditing.value = false; }
async function changePassword() { if (passwordForm.new_password !== passwordConfirm.value) return emit("notice", "warning", "密码不一致"); await run(() => api.post("/auth/me/password", passwordForm), "已保存"); Object.assign(passwordForm, { old_password: "", new_password: "" }); passwordConfirm.value = ""; }
async function saveNotice() { const data = await run<any[]>(() => api.put("/teacher/profile/notifications", { settings: noticeSettings.map((item) => ({ key: item.key, enabled: item.enabled })) }), "已保存"); if (data) noticeSettings.splice(0, noticeSettings.length, ...data); }

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

onMounted(async () => { await loadCourses(); await loadActive(); });

const MetricCard = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, value: { type: [String, Number], required: true }, sub: { type: String, default: "" }, tone: { type: String, default: "primary" }, danger: { type: Boolean, default: false } }, setup(p) { return () => h("article", { class: ["metric-card", p.tone, p.danger ? "danger" : ""] }, [h("div", [h("span", { class: "metric-icon" }, [h(p.icon as any, { size: 20 })]), h("span", p.label)]), h("strong", String(p.value)), h("small", p.sub)]); } });
const EmptyState = defineComponent({ props: { text: { type: String, required: true }, success: { type: Boolean, default: false } }, setup(p, { slots }) { return () => h("div", { class: "empty" }, [p.success ? h(CheckCircle, { size: 30 }) : h(Inbox, { size: 30 }), h("span", p.text), slots.default?.()]); } });
const CourseRequired = defineComponent(() => () => h("div", { class: "empty page-empty" }, [h(BookOpen, { size: 48 }), h("span", "请选择课程")]));
const QuickAction = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, sub: { type: String, required: true } }, emits: ["click"], setup(p, { emit: update }) { return () => h("button", { class: "quick-action", onClick: () => update("click") }, [h(p.icon as any, { size: 22 }), h("strong", p.label), h("small", p.sub)]); } });
const TaskList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, emits: ["retry"], setup(p, { emit: update }) { return () => h("div", { class: "task-list" }, p.items.length ? p.items.map((item) => h("div", { class: "task-item" }, [h(item.status === "ready" ? CheckCircle : item.status === "failed" ? XCircle : item.status === "processing" ? RefreshCw : Clock, { size: 16, class: item.status }), h("span", item.title), h("small", statusText(item.status)), item.status === "failed" ? h("button", { class: "link-btn", onClick: () => update("retry", item) }, "重试") : null])) : [h(EmptyState, { text: "暂无任务" })]); } });
const LessonRows = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true }, studentTotal: { type: Number, required: true } }, emits: ["open"], setup(p, { emit: update }) { return () => h("div", { class: "lesson-rows" }, p.items.slice(0, 6).map((item, index) => h("button", { class: "lesson-row", onClick: () => update("open", item) }, [h("b", index + 1), h("div", [h("strong", item.title), h("small", `${item.page_count || 0}页 · ${item.learned_count || 0}/${p.studentTotal}人`), h("progress", { value: item.average_progress || 0, max: 100 })]), h("span", { class: ["tag", statusClass(item.status)] }, statusText(item.status))]))); } });
const MaterialTypeList = defineComponent({ props: { stats: { type: Object as PropType<Record<string, number>>, required: true } }, setup(p) { return () => h("div", { class: "type-list" }, ["pptx", "pdf", "docx", "txt"].map((type) => h("div", [h(fileIcon(type), { size: 16 }), h("span", typeText(type)), h("strong", `${p.stats[type] || 0}份`)]))); } });
const ActivityList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h("div", { class: "activity-list" }, p.items.length ? p.items.map((item) => h("div", { class: "activity-item" }, [h("i", { class: item.tone }), h("span", item.text), h("small", relativeTime(item.time))])) : [h(EmptyState, { text: "暂无活动" })]); } });
const ProgressList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h("div", { class: "progress-list" }, p.items.length ? p.items.map((item) => h("div", { class: "student-progress-row" }, [h("span", { class: "avatar mini" }, firstChar(item.student.nickname)), h("strong", item.student.nickname), h(ProgressBar, { value: item.progress_percent }), h("small", `${item.progress_percent}%`)])) : [h(EmptyState, { text: "暂无学生" })]); } });
const ProgressBar = defineComponent({ props: { value: { type: Number, required: true } }, setup(p) { return () => h("progress", { class: ["progress-bar", p.value < 30 ? "low" : p.value < 70 ? "mid" : "high"], value: p.value, max: 100 }); } });
const MaterialStatus = defineComponent({ props: { item: { type: Object, required: true } }, setup(p) { return () => h("small", { class: "material-status" }, p.item.parse_status === "ready" ? "脚本已生成 · 语音已合成" : p.item.parse_status === "processing" ? "正在生成脚本" : p.item.parse_status === "failed" ? "解析失败" : "待处理"); } });
const LayerCard = defineComponent({ props: { label: { type: String, required: true }, value: { type: Number, required: true }, tone: { type: String, default: "primary" } }, setup(p) { return () => h("article", { class: ["layer-card", p.tone] }, [h("strong", p.label), h("span", `${p.value} 人`), h("progress", { value: p.value, max: Math.max(1, studentPayload.value.stats?.total || 1) })]); } });
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
.course-popover, .user-popover { position: absolute; top: 38px; min-width: 220px; z-index: var(--z-dropdown); border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 8px; }
.course-popover button, .user-popover button { display: flex; width: 100%; align-items: center; gap: 8px; min-height: 34px; border: 0; border-radius: 8px; background: transparent; color: var(--color-text-body); padding: 0 10px; text-align: left; }
.course-popover button.active, .course-popover button:hover, .user-popover button:hover { background: var(--color-primary-50); color: var(--color-primary-700); }
.user-popover { right: 0; min-width: 160px; }
.icon-btn, .icon-action { position: relative; display: inline-flex; width: 34px; height: 34px; align-items: center; justify-content: center; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-secondary); }
.icon-btn:hover, .icon-action:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.icon-btn em { position: absolute; top: 0; right: 0; min-width: 16px; height: 16px; border-radius: 8px; background: var(--color-danger-500); color: white; font-size: 10px; font-style: normal; line-height: 16px; }
.avatar { display: inline-flex; width: 36px; height: 36px; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-ai-gradient); color: white; font-weight: 700; }
.avatar.mini { width: 24px; height: 24px; font-size: 12px; }
.avatar.large { position: relative; width: 80px; height: 80px; font-size: 26px; }
.avatar.large svg { position: absolute; right: 0; bottom: 0; border-radius: 50%; background: var(--color-primary-600); padding: 4px; }
.teacher-sidebar { position: fixed; top: 60px; left: 0; bottom: 0; width: 240px; min-height: 0; overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain; border-right: 1px solid var(--color-border-default); background: white; padding: 18px 12px; }
.nav-group { display: grid; gap: 2px; padding: 12px 0; border-bottom: 1px solid var(--color-border-subtle); }
.nav-group > span { padding: 0 12px 8px; color: var(--color-text-muted); font-size: var(--text-overline); font-weight: 600; }
.course-title { display: flex; align-items: center; justify-content: space-between; cursor: pointer; font-style: normal; }
.nav-group button { position: relative; display: flex; height: 40px; align-items: center; gap: 8px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-secondary); padding: 0 12px; text-align: left; }
.nav-group button:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.nav-group button.active { background: var(--color-primary-50); color: var(--color-primary-700); font-weight: 500; }
.nav-group button.active::before { content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: var(--color-primary-600); }
.nav-group button:disabled { opacity: 0.45; }
.teacher-main { margin-left: 240px; padding-top: 60px; }
.teacher-main.immersive { padding-top: 60px; }
.breadcrumb { height: 56px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: white; padding: 0 32px; }
.breadcrumb span { color: var(--color-text-secondary); }
.breadcrumb strong { color: var(--color-text-primary); }
.teacher-content { display: grid; gap: 16px; padding: 32px 32px 64px; animation: fade-slide-up 250ms var(--ease-out); }
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
.recent-course { display: grid; grid-template-columns: 48px 1fr auto; align-items: center; gap: 12px; border-bottom: 1px solid var(--color-border-subtle); padding: 12px 0; }
.cover { display: inline-flex; width: 48px; height: 48px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-ai-gradient); color: white; }
.recent-course div { display: grid; gap: 4px; }
.recent-course strong { color: var(--color-text-primary); }
.recent-course small { color: var(--color-text-muted); }
progress { width: 100%; height: 6px; accent-color: var(--color-primary-600); }
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
.heat-row i { height: 22px; border-radius: 5px; background: var(--color-primary-600); }
.script-row { min-height: 48px; border-bottom: 1px solid var(--color-border-subtle); }
.script-row div { flex: 1; display: grid; }
.task-list { display: grid; gap: 8px; }
.task-item { display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: 8px; min-height: 34px; }
.task-item span { color: var(--color-text-body); }
.task-item small { color: var(--color-text-muted); }
.task-item .processing { color: var(--color-primary-600); animation: spin 1s linear infinite; }
.task-item .failed { color: var(--color-danger-500); }
.task-item .ready { color: var(--color-success-500); }
.filter-card { min-height: 56px; display: grid; grid-template-columns: 240px 140px 120px 1fr auto; align-items: center; gap: 10px; padding: 10px 14px; }
.search-box { display: flex; align-items: center; gap: 8px; height: 36px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: white; padding: 0 10px; }
.search-box input { width: 100%; border: 0; outline: 0; }
.search-box.small { height: 32px; }
.segmented-control { display: flex; background: var(--color-bg-muted); border-radius: var(--radius-md); padding: 4px; }
.segment-btn { min-height: 30px; border: 0; border-radius: 6px; background: transparent; color: var(--color-text-muted); padding: 6px 16px; font-size: 13px; font-weight: 500; transition: all 200ms var(--ease-out); }
.segment-btn.active { background: white; color: var(--color-text-primary); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.view-toggle { display: inline-flex; overflow: hidden; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.view-toggle button { min-height: 32px; border: 0; background: white; color: var(--color-text-secondary); padding: 0 10px; }
.view-toggle .active { background: var(--color-primary-600); color: white; }
.course-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
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
.chapter-edit { display: grid; grid-template-columns: auto 1fr 76px auto; gap: 8px; align-items: center; }
.order-input { text-align: center; }
.advanced { border-top: 1px solid var(--color-border-subtle); padding-top: 12px; }
.advanced summary { display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); font-weight: 600; cursor: pointer; }
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
.course-home-grid { display: grid; grid-template-columns: 45fr 30fr 25fr; gap: 16px; }
.course-bottom-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.lesson-rows { display: grid; gap: 10px; }
.lesson-row { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 10px; min-height: 58px; border: 1px solid var(--color-border-subtle); border-radius: var(--radius-md); background: white; padding: 8px; text-align: left; }
.lesson-row b { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-primary-50); color: var(--color-primary-700); }
.lesson-row div { display: grid; gap: 3px; }
.lesson-row strong { color: var(--color-text-primary); }
.lesson-row small { color: var(--color-text-muted); }
.full { width: 100%; }
.type-list { display: grid; gap: 10px; margin: 12px 0; }
.type-list div { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; }
.activity-list { display: grid; gap: 12px; }
.activity-item { display: grid; grid-template-columns: 10px 1fr auto; gap: 8px; align-items: center; }
.activity-item i { width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary-600); }
.activity-item i.success { background: var(--color-success-500); }
.activity-item span { color: var(--color-text-body); font-size: var(--text-body-sm); }
.activity-item small { color: var(--color-text-muted); font-size: 11px; }
.progress-list { display: grid; gap: 10px; }
.student-progress-row { display: grid; grid-template-columns: auto 90px 1fr 52px; align-items: center; gap: 8px; }
.progress-bar.low { accent-color: var(--color-danger-500); }
.progress-bar.mid { accent-color: var(--color-warning-500); }
.progress-bar.high { accent-color: var(--color-success-500); }
.materials-layout { min-height: 640px; display: grid; grid-template-columns: 220px 1fr; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); overflow: hidden; }
.chapter-tree { display: grid; align-content: start; gap: 6px; border-right: 1px solid var(--color-border-default); padding: 12px; }
.chapter-tree button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; min-height: 40px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-body); text-align: left; padding: 0 10px; }
.chapter-tree button.active { background: var(--color-primary-50); color: var(--color-primary-700); box-shadow: inset 3px 0 0 var(--color-primary-600); }
.chapter-tree button.empty { color: var(--color-text-muted); }
.materials-panel { min-width: 0; }
.material-filter { height: 52px; display: grid; grid-template-columns: 1fr 120px 130px 130px auto; align-items: center; gap: 10px; border-bottom: 1px solid var(--color-border-default); padding: 8px 12px; }
.material-list { display: grid; align-content: start; }
.material-list.grid { grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 12px; }
.material-row { display: grid; grid-template-columns: 42px 1fr auto auto; align-items: center; gap: 12px; min-height: 64px; border-bottom: 1px solid var(--color-border-subtle); padding: 10px 14px; }
.material-list.grid .material-row { border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.file-badge { display: inline-flex; width: 32px; height: 32px; align-items: center; justify-content: center; border-radius: var(--radius-md); color: white; background: var(--color-text-muted); }
.file-badge.pptx { background: #F97316; }.file-badge.pdf { background: var(--color-danger-500); }.file-badge.docx { background: var(--color-info-500); }
.material-row strong { color: var(--color-text-primary); }
.material-row small { display: block; color: var(--color-text-muted); }
.material-status { margin-top: 2px; }
.material-row section { display: flex; gap: 4px; }
.ppt-workbench { position: relative; height: calc(100vh - 60px); display: grid; grid-template-columns: 220px 1fr 400px; grid-template-rows: 1fr 48px; background: #0F172A; }
.ppt-head { position: fixed; top: 0; left: 0; right: 0; z-index: var(--z-fixed); height: 60px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid var(--color-border-default); background: white; padding: 0 18px; }
.thumb-column, .script-panel { background: white; overflow: auto; }
.thumb-column { border-right: 1px solid var(--color-border-default); padding: 12px; }
.thumb-top { display: grid; gap: 8px; margin-bottom: 12px; }
.thumb-card { position: relative; width: 100%; min-height: 100px; display: grid; gap: 6px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: white; margin-bottom: 8px; padding: 8px; text-align: left; }
.thumb-card.active { border-color: var(--color-primary-600); box-shadow: var(--shadow-focus); }
.thumb-card span { position: absolute; top: 6px; left: 6px; border-radius: 8px; background: var(--color-primary-600); color: white; padding: 0 6px; font-size: 11px; }
.thumb-card svg { position: absolute; top: 6px; right: 6px; color: var(--color-success-500); }
.thumb-card div { min-height: 52px; display: grid; place-items: center; border-radius: 6px; background: var(--color-bg-muted); color: var(--color-text-secondary); }
.thumb-card small { color: var(--color-text-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.ppt-stage { position: relative; display: grid; place-items: center; padding: 64px 28px; }
.stage-top, .stage-controls { position: absolute; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 8px; border-radius: var(--radius-full); background: rgba(255,255,255,0.15); color: white; backdrop-filter: blur(10px); padding: 8px 12px; }
.stage-top { top: 16px; }
.stage-controls { bottom: 16px; }
.stage-top .icon-action, .stage-controls .icon-action { color: white; }
.slide-preview { width: min(860px, 90%); aspect-ratio: 16 / 9; display: grid; align-content: center; gap: 16px; border: 4px solid white; border-radius: 8px; background: white; box-shadow: 0 20px 50px rgba(0,0,0,0.35); padding: 48px; }
.slide-preview h2 { margin: 0; color: var(--color-text-primary); font-size: 28px; }
.slide-preview p { color: var(--color-text-body); font-size: 18px; line-height: 1.8; }
.script-panel { border-left: 1px solid var(--color-border-default); display: grid; grid-template-rows: auto auto auto 1fr auto auto; }
.script-head { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--color-border-default); }
.script-head h2 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: var(--text-h4); }
.ai-strip { display: flex; align-items: center; gap: 8px; background: var(--color-ai-light); color: #6D28D9; padding: 10px 16px; font-size: var(--text-caption); }
.ai-strip button { margin-left: auto; border: 0; background: transparent; color: #6D28D9; }
.editor-toolbar { display: flex; gap: 6px; border-bottom: 1px solid var(--color-border-default); padding: 8px 12px; }
.editor-toolbar button { border: 1px solid var(--color-border-default); border-radius: 6px; background: white; padding: 4px 8px; }
.script-editor { width: 100%; height: 100%; border: 0; outline: 0; background: #FAFAF7; color: var(--color-text-body); font-size: 15px; line-height: 1.75; resize: none; padding: 18px; }
.word-count { justify-self: end; color: var(--color-text-muted); padding: 4px 12px; }
.script-actions { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--color-border-default); padding: 10px 12px; }
.script-actions span { display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.ppt-status { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--color-border-default); background: white; padding: 0 16px; }
.ppt-status span { color: var(--color-text-secondary); }
.ppt-status div { display: flex; gap: 8px; }
.lesson-card-list { display: grid; gap: 12px; }
.lesson-card { min-height: 108px; display: grid; grid-template-columns: 96px 1fr auto; align-items: center; gap: 16px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 16px; }
.lesson-thumb { width: 96px; height: 72px; display: grid; place-items: center; border-radius: 8px; background: #0F172A; color: white; font-size: 24px; font-weight: 700; }
.lesson-card h2 { margin: 0; display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); font-size: 15px; }
.lesson-card p { color: var(--color-text-secondary); margin: 6px 0 10px; }
.lesson-actions { display: flex; align-items: center; gap: 6px; }
.switch input { display: none; }
.switch span { display: inline-block; width: 36px; height: 20px; border-radius: 10px; background: var(--color-border-strong); }
.switch input:checked + span { background: var(--color-success-500); }
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
.question-row { display: grid; grid-template-columns: 28px 1fr 60px; align-items: center; gap: 8px; min-height: 44px; border-bottom: 1px solid var(--color-border-subtle); }
.question-row b { display: inline-flex; width: 24px; height: 24px; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-primary-600); color: white; }
.activity-layers { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.layer-card { display: grid; gap: 8px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); padding: 14px; }
.layer-card.success progress { accent-color: var(--color-success-500); }
.layer-card.warning progress { accent-color: var(--color-warning-500); }
.layer-card.danger progress { accent-color: var(--color-danger-500); }
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
.strength i { display: block; height: 100%; background: var(--color-success-500); }
.notice-list label { display: flex; align-items: center; gap: 10px; min-height: 36px; }
.modal-mask { position: fixed; inset: 0; z-index: var(--z-modal-bg); display: grid; place-items: center; background: rgba(15,23,42,0.38); backdrop-filter: blur(6px); }
.modal { width: 640px; max-height: 90vh; overflow: auto; border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-xl); padding: 20px; }
.modal.preview-modal { width: 800px; height: 90vh; display: grid; grid-template-rows: auto 1fr; }
.preview-modal iframe { width: 100%; height: 100%; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
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
@keyframes spin { to { transform: rotate(360deg); } }
</style>
