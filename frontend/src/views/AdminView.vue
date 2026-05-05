<template>
  <section class="admin-shell" :class="{ collapsed, 'sidebar-scrollable': sidebarScrollable }">
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <button class="menu-btn" @click="collapsed = !collapsed"><Menu :size="20" />{{ collapsed ? '展开' : '收起' }}</button>
        <span class="logo-mark"><Sparkles :size="17" /></span>
        <strong class="logo-text">系统管理后台</strong>
      </div>

      <nav ref="sidebarNavRef" class="sidebar-nav">
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <span class="nav-title">{{ group.title }}</span>
          <button v-for="item in group.items" :key="item.key" class="nav-link" :class="{ active: active === item.key }" @click="go(item.key)">
            <component :is="item.icon" :size="18" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="side-user">
          <span class="avatar">管</span>
          <div><strong>{{ user.nickname }}</strong><span class="tag tag-ai">Super Admin</span></div>
        </div>
      </div>
    </aside>

    <header class="admin-topbar">
      <div class="topbar-left"></div>
      <div class="top-actions">
        <span class="health-pill" :class="health?.status === 'ok' ? 'ok' : 'warn'"><i></i>{{ health?.status === 'ok' ? '运行正常' : '服务异常' }}</span>
        <button type="button" class="notice-btn" aria-label="通知" @click="openAdminNotifications"><Bell :size="20" /><span>通知</span><em v-if="alertCount">{{ alertCount }}</em></button>
        <span class="divider"></span>
        <div ref="userMenuRef" class="user-menu">
          <button type="button" class="user-trigger" aria-haspopup="menu" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen">
            <span class="avatar">管</span><span>{{ user.nickname }}</span><ChevronDown :size="16" />
          </button>
          <Transition name="top-menu">
            <div v-if="userMenuOpen" class="admin-account-menu top-menu-panel" role="menu">
              <button type="button" role="menuitem" @click="openAdminProfile"><User :size="15" />资料</button>
              <button type="button" role="menuitem" @click="$emit('logout')"><LogOut :size="15" />退出</button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <main class="admin-main">
      <div v-if="active !== 'adminServices' && active !== 'adminSystem'" class="breadcrumb">
        <div>
          <span>系统管理</span><ChevronRight :size="14" /><strong>{{ currentTitle }}</strong>
        </div>
        <section class="page-actions">
          <button v-if="active === 'adminDashboard'" class="btn btn-secondary" @click="go('adminMonitor')">监控</button>
          <button v-if="active === 'adminDashboard'" class="btn btn-ghost" @click="go('adminLogs')">日志</button>
          <button v-if="active === 'adminUsers'" class="btn btn-primary" @click="adminModalOpen = true"><Plus :size="16" />创建</button>
          <button v-if="active === 'adminCourses'" class="btn btn-danger" :disabled="!selectedCourses.length" @click="batchDeactivateCourses">下架</button>
          <button v-if="active === 'adminMaterials'" class="btn btn-danger" :disabled="!selectedMaterials.length" @click="batchDeleteMaterials">删除</button>
          <button v-if="active === 'adminModels'" class="btn btn-primary" @click="saveAllModels"><Save :size="16" />保存</button>
          <button v-if="active === 'adminServices'" class="btn btn-secondary" @click="testAllServices"><RefreshCw :size="16" />测试</button>
          <button v-if="active === 'adminServices'" class="btn btn-primary" @click="saveAllServices"><Save :size="16" />保存</button>
          <button v-if="active === 'adminSystem'" class="btn btn-secondary" @click="restoreSettings">默认</button>
          <button v-if="active === 'adminSystem'" class="btn btn-primary" @click="saveSettings"><Save :size="16" />保存</button>
          <button v-if="active === 'adminMonitor'" class="btn btn-secondary" @click="loadMonitor"><RefreshCw :size="16" />刷新</button>
          <button v-if="active === 'adminLogs'" class="btn btn-ghost" @click="exportCurrent">导出</button>
          <button v-if="active === 'adminBackups'" class="btn btn-ai" @click="createBackup"><Database :size="16" />备份</button>
        </section>
      </div>

      <TransitionGroup name="page-switch" tag="section" class="admin-content">
        <section v-if="active === 'adminDashboard'" key="adminDashboard" class="admin-page">
          <article class="welcome-card">
            <span class="welcome-icon"><Sparkles :size="24" /></span>
            <div><h1>欢迎回来，管理员</h1><p>{{ todayText }} · {{ health?.status === 'ok' ? '平台运行正常' : '存在异常服务' }}</p></div>
          </article>
          <div class="metric-grid four">
            <MetricCard :icon="Users" label="注册用户" :value="dashboard.stats?.users_total || 0" trend="本周新增" />
            <MetricCard :icon="BookOpen" label="活跃课程" :value="dashboard.stats?.active_courses || 0" trend="近30天" tone="success" />
            <MetricCard :icon="Sparkles" label="今日 AI" :value="dashboard.stats?.today_ai_calls || 0" trend="调用次数" tone="ai" />
            <MetricCard :icon="Activity" label="异步队列" :value="dashboard.stats?.async_pending || 0" trend="待处理" :danger="(dashboard.stats?.async_pending || 0) > 0" />
          </div>
          <div class="content-row">
            <section class="left-col">
              <article class="panel-card">
                <div class="panel-head">
                  <div><h2>活跃度趋势</h2><span>{{ trendSubtitle }}</span></div>
                  <div class="segmented-control">
                    <button v-for="item in trendOptions" :key="item" type="button" class="segment-btn" :class="{ active: trendRange === item }" @click="setTrendRange(item)">{{ item }}</button>
                  </div>
                </div>
                <AdminChart type="line" :height="280" :labels="activityLabels" :series="activitySeries" />
              </article>
            </section>
            <aside class="right-col">
              <article class="panel-card">
                <div class="panel-head"><h2><Server :size="18" />服务状态</h2><button class="btn btn-ai btn-sm" @click="testAllServices"><RefreshCw :size="14" />测试</button></div>
                <div class="service-list">
                  <div v-for="item in healthItems.slice(0, 8)" :key="item.key" class="service-row">
                    <component :is="serviceIcon(item.key)" :size="16" />
                    <span>{{ item.name }}</span>
                    <span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span>
                    <small>{{ item.metric }}</small>
                  </div>
                  <EmptyState v-if="!healthItems.length" text="暂无状态" />
                </div>
              </article>
            </aside>
          </div>
        </section>

        <section v-if="active === 'adminUsers'" key="adminUsers" class="admin-page">
          <div class="metric-grid three">
            <MetricCard :icon="Users" label="全部用户" :value="userStats.total || 0" :trend="`本周 +${userStats.weekly_new || 0}`" />
            <MetricCard :icon="GraduationCap" label="教师" :value="userStats.teachers || 0" trend="授课账号" tone="success" />
            <MetricCard :icon="User" label="学生" :value="userStats.students || 0" trend="学习账号" tone="info" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="userFilter.keyword" placeholder="搜索用户名、邮箱、工号" @keyup.enter="loadUsers" /></div>
            <AppSelect v-model="userFilter.role" :options="userRoleFilterOptions" />
            <AppSelect v-model="userFilter.status" :options="userStatusOptions" />
            <button class="btn btn-ghost" @click="clearUserFilter"><X :size="16" />清除</button>
            <span class="spacer"></span>
            <button class="btn btn-secondary" :disabled="!selectedUsers.length" @click="batchDisableUsers"><CheckSquare :size="16" />批量</button>
            <button class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出</button>
          </article>
          <article class="table-card">
            <div v-if="selectedUsers.length" class="bulk-bar"><AppCheckbox :model-value="true" :label="`已选 ${selectedUsers.length} 人`" @update:model-value="selectedUsers = []" /><button @click="batchDisableUsers">禁用</button><button @click="openBatchResetPasswordModal">重置密码</button><button @click="batchDeleteUsers">删除</button><button @click="selectedUsers = []">取消</button></div>
            <table class="admin-table">
              <thead><tr><th class="check-col"><AppCheckbox :model-value="selectedUsers.length === users.length && users.length > 0" @update:model-value="toggleAllUsers" /></th><th>用户</th><th>角色</th><th>状态</th><th>所属课程</th><th>注册时间</th><th>最近登录</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in users" :key="item.id" :class="{ disabled: item.status === 'disabled', selected: selectedUsers.includes(item.id) }">
                  <td><AppCheckbox :model-value="selectedUsers.includes(item.id)" @update:model-value="toggleSelect(selectedUsers, item.id)" /></td>
                  <td><div class="identity"><span class="avatar small">{{ firstChar(item.nickname) }}</span><div><strong>{{ item.nickname }}</strong><span>{{ item.email }}</span></div></div></td>
                  <td><AppSelect class="role-select" :model-value="item.role" :options="userRoleOptions" :disabled="isPending(`role:${item.id}`)" @update:model-value="selectUserRole(item, $event)" /></td>
                  <td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td>
                  <td>
                    <div v-if="item.course_count" class="course-chip-list">
                      <span v-for="course in (item.courses || []).slice(0, 2)" :key="`${course.relation}-${course.id}`" class="course-chip" :title="course.name">
                        <BookOpen :size="13" />{{ course.name }}<em>{{ course.role }}</em>
                      </span>
                      <span v-if="item.course_count > 2" class="course-more">+{{ item.course_count - 2 }}</span>
                    </div>
                    <span v-else class="muted-cell">暂无</span>
                  </td>
                  <td>{{ shortDate(item.created_at) }}</td>
                  <td :class="{ stale: isStale(item.last_login_at) }">{{ relativeTime(item.last_login_at) }}</td>
                  <td class="row-actions"><button class="text-action" @click="openUserDetail(item.id)"><Eye :size="14" />详情</button><button class="text-action" :data-loading="isPending(`reset:${item.id}`)" :disabled="isPending(`reset:${item.id}`)" @click="openResetPasswordModal(item)"><KeyRound :size="14" />修改密码</button><button class="text-action danger" :data-loading="isPending(`delete:${item.id}`)" :disabled="isPending(`delete:${item.id}`)" @click="deleteUser(item.id)"><Trash2 :size="14" />删除</button></td>
                </tr>
                <tr v-if="!users.length"><td colspan="8"><EmptyState text="暂无用户" /></td></tr>
              </tbody>
            </table>
          </article>
        </section>

        <section v-if="active === 'adminCourses'" key="adminCourses" class="admin-page">
          <div class="metric-grid four">
            <MetricCard :icon="BookOpen" label="全部课程" :value="courseStats.total || 0" trend="平台课程" />
            <MetricCard :icon="Activity" label="活跃课程" :value="courseStats.active || 0" trend="正常开放" tone="success" />
            <MetricCard :icon="FileCheck" label="待审资料" :value="courseStats.pending_materials || 0" trend="需关注" :danger="(courseStats.pending_materials || 0) > 0" />
            <MetricCard :icon="Plus" label="本月新增" :value="courseStats.monthly_new || 0" trend="新建课程" tone="info" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="courseFilter.keyword" placeholder="课程名称/教师名" @keyup.enter="loadCourses" /></div>
            <AppSelect v-model="courseFilter.status" :options="courseStatusOptions" />
            <input v-model="courseTerm" class="input" placeholder="学期" />
            <button class="btn btn-ghost" @click="clearCourseFilter"><X :size="16" />重置</button>
            <span class="spacer"></span>
            <div class="view-toggle"><button :class="{ active: courseView === 'table' }" @click="courseView = 'table'"><List :size="16" />表格</button><button :class="{ active: courseView === 'grid' }" @click="courseView = 'grid'"><Grid2X2 :size="16" />卡片</button></div>
          </article>
          <article v-if="courseView === 'table'" class="table-card">
            <table class="admin-table">
              <thead><tr><th class="check-col"><AppCheckbox :model-value="selectedCourses.length === filteredCourses.length && filteredCourses.length > 0" @update:model-value="toggleAllCourses" /></th><th>课程名称</th><th>主讲教师</th><th>学期</th><th>学生数</th><th>资料数</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in filteredCourses" :key="item.id">
                  <td><AppCheckbox :model-value="selectedCourses.includes(item.id)" @update:model-value="toggleSelect(selectedCourses, item.id)" /></td>
                  <td><strong>{{ item.name }}</strong><span class="tag mono">{{ item.course_code }}</span></td>
                  <td><span class="avatar mini">{{ firstChar(item.teacher_name) }}</span>{{ item.teacher_name || item.teacher_id }}</td>
                  <td>{{ item.term }}</td><td><Users :size="14" />{{ item.student_count || 0 }}</td><td><FileText :size="14" />{{ item.material_count || 0 }}</td>
                  <td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td><td>{{ shortDate(item.created_at) }}</td>
                  <td class="row-actions"><button class="icon-action" @click="openCourseDetail(item.id)"><Eye :size="15" />详情</button><button class="icon-action" @click="openTakeover(item)"><UserCheck :size="15" />接管</button><button class="icon-action danger" @click="deactivateCourse(item.id)"><Ban :size="15" />下架</button></td>
                </tr>
              </tbody>
            </table>
          </article>
          <div v-else class="course-card-grid">
            <article v-for="item in filteredCourses" :key="item.id" class="course-admin-card" :class="{ inactive: item.status !== 'active' }">
              <div><strong>{{ item.name }}</strong><span class="tag mono">{{ item.course_code }}</span></div>
              <p>{{ item.teacher_name }} · {{ item.term }}</p>
              <div class="mini-metrics"><span><Users :size="14" />{{ item.student_count || 0 }}</span><span><FileText :size="14" />{{ item.material_count || 0 }}</span></div>
              <button class="icon-action" @click="openCourseDetail(item.id)"><Eye :size="15" />详情</button>
            </article>
          </div>
        </section>

        <section v-if="active === 'adminMaterials'" key="adminMaterials" class="admin-page">
          <div class="metric-grid three">
            <MetricCard :icon="File" label="全部资料" :value="materialStats.total || 0" trend="平台文件" />
            <MetricCard :icon="Upload" label="本月新增" :value="materialStats.monthly_new || 0" trend="上传量" tone="info" />
            <MetricCard :icon="Database" label="存储用量" :value="materialStats.storage_used_label || '0 B'" trend="资料空间" :danger="storagePercent > 90" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="materialFilter.keyword" placeholder="文件名/课程名/教师名" @keyup.enter="loadMaterials" /></div>
            <AppSelect v-model="materialFilter.material_type" :options="materialTypeOptions" />
            <AppSelect v-model="materialFilter.category" :options="materialCategoryOptions" />
            <input v-model.number="materialFilter.teacher_id" class="input narrow" type="number" placeholder="教师ID" />
            <button class="btn btn-ghost" @click="clearMaterialFilter"><X :size="16" />清除</button><span class="spacer"></span><button class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出</button>
          </article>
          <article class="table-card">
            <table class="admin-table">
              <thead><tr><th class="check-col"><AppCheckbox :model-value="selectedMaterials.length === materials.length && materials.length > 0" @update:model-value="toggleAllMaterials" /></th><th>文件名</th><th>所属课程</th><th>上传教师</th><th>类型</th><th>上传时间</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in materials" :key="item.id">
                  <td><AppCheckbox :model-value="selectedMaterials.includes(item.id)" @update:model-value="toggleSelect(selectedMaterials, item.id)" /></td>
                  <td><div class="identity"><component :is="fileIcon(item.material_type)" :size="18" :class="`file-${item.material_type}`" /><div><strong>{{ item.title }}</strong><span>{{ item.size_label || sizeLabel(item.size_bytes) }}</span></div></div></td>
                  <td>{{ item.course_name || item.course_id }}</td><td><span class="avatar mini">{{ firstChar(item.teacher_name) }}</span>{{ item.teacher_name || item.uploader_id }}</td>
                  <td><span class="tag">{{ typeText(item.material_type) }}</span></td><td>{{ shortDate(item.created_at) }}</td>
                  <td><span class="tag" :class="statusClass(item.parse_status)">{{ statusText(item.parse_status) }}</span></td>
                  <td class="row-actions"><button class="icon-action" @click="previewMaterial(item)"><Eye :size="15" />预览</button><a v-if="item.preview_url" class="icon-action" :href="item.preview_url" target="_blank"><Download :size="15" />下载</a><button class="icon-action danger" @click="deleteMaterial(item.id)"><Trash2 :size="15" />删除</button></td>
                </tr>
              </tbody>
            </table>
          </article>
        </section>

        <section v-if="active === 'adminModels'" key="adminModels" class="admin-page model-layout">
          <aside class="vertical-tabs"><button :class="{ active: modelTab === 'llm' }" @click="modelTab = 'llm'">大模型</button><button :class="{ active: modelTab === 'embedding' }" @click="modelTab = 'embedding'">Embedding</button><button :class="{ active: modelTab === 'usage' }" @click="modelTab = 'usage'">调用统计</button></aside>
          <section class="model-content">
            <div v-if="modelWarning" class="alert alert-danger"><AlertTriangle :size="16" />{{ modelWarning }}<button class="link-btn" @click="modelTab = 'llm'">配置</button></div>
            <article v-if="modelTab === 'llm'" class="panel-card form-panel">
              <div class="panel-head"><div><h2><Sparkles :size="18" />大语言模型</h2><span>按功能配置模型</span></div><button class="btn btn-secondary" @click="testDefaultModel">测试</button></div>
              <div class="form-section"><h3>全局设置</h3><div class="form-grid"><label>供应商<AppSelect v-model="modelGlobal.provider" :options="modelProviderOptions" /></label><label>API Base<input v-model="modelGlobal.endpoint" class="input" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" /></label><label class="wide-field">API Key<PasswordField v-model="modelGlobal.api_key" placeholder="加密存储" /></label></div></div>
              <div class="form-section"><h3>用途分配</h3><div class="purpose-config-grid"><article v-for="item in llmPurposes" :key="item.key" class="purpose-card"><div><component :is="item.icon" :size="16" /><strong>{{ item.label }}</strong></div><input v-model="modelDrafts[item.key].model_name" class="input" placeholder="qwen-max" /><label>Temperature <AppSlider v-model="modelDrafts[item.key].temperature" :min="0" :max="2" :step="0.1" /> <b>{{ modelDrafts[item.key].temperature }}</b></label><label>最大 Token<input v-model.number="modelDrafts[item.key].max_tokens" class="input" type="number" /></label></article></div></div>
            </article>
            <article v-if="modelTab === 'embedding'" class="panel-card form-panel"><div class="panel-head"><div><h2><Layers :size="18" />Embedding 模型</h2><span>用于资料向量化</span></div><button class="btn btn-secondary" @click="testEmbeddingModel">测试</button></div><div class="form-grid"><label>供应商<AppSelect v-model="embeddingDraft.provider" :options="embeddingProviderOptions" /></label><label>模型<input v-model="embeddingDraft.model_name" class="input" placeholder="text-embedding-v2" /></label><label>向量维度<input v-model.number="embeddingDraft.dimensions" class="input" type="number" /></label><label>API Key<PasswordField v-model="embeddingDraft.api_key" /></label><label class="wide-field">API Base<input v-model="embeddingDraft.endpoint" class="input" /></label></div></article>
            <article v-if="modelTab === 'usage'" class="panel-card">
              <div class="panel-head">
                <div><h2>模型调用统计</h2><span>最近调用汇总</span></div>
                <div class="segmented-control">
                  <button v-for="item in usageOptions" :key="item" type="button" class="segment-btn" :class="{ active: usageUnit === item }" @click="usageUnit = item">{{ item }}</button>
                </div>
              </div>
              <div class="metric-grid four compact"><MetricCard :icon="Sparkles" label="调用次数" :value="usageTotal.calls" trend="累计" /><MetricCard :icon="BarChart2" label="Token" :value="usageTotal.tokens" trend="输入/输出" /><MetricCard :icon="Database" label="费用" :value="`$${usageTotal.cost}`" trend="估算" /><MetricCard :icon="Clock" label="响应" value="-" trend="待接入" /></div>
              <AdminChart type="hbar" :labels="usageLabels" :series="usageSeries" />
            </article>
          </section>
        </section>

        <section v-if="active === 'adminServices'" key="adminServices" class="admin-page page-view aliyun-page">
          <div class="page-header aliyun-page-head">
            <div class="breadcrumb"><span>系统管理</span><ChevronRight :size="14" /><span>阿里云服务</span></div>
            <div class="header-actions">
              <button class="btn btn-secondary" @click="testAllServices"><RefreshCw :size="14" />测试全部</button>
              <button class="btn btn-primary" @click="saveAllServices"><Save :size="14" />保存配置</button>
            </div>
          </div>
          <div class="aliyun-card-list">
            <article class="aliyun-card aliyun-oss">
              <header class="aliyun-card-head">
                <div class="aliyun-card-title">
                  <span class="aliyun-card-icon"><Cloud :size="20" /></span>
                  <h2>阿里云 OSS</h2>
                </div>
                <span class="tag" :class="statusClass(serviceStatus('oss'))">{{ statusText(serviceStatus('oss')) }}</span>
                <div class="aliyun-card-actions">
                  <button class="btn btn-secondary btn-sm" @click="testServiceType('oss')"><RefreshCw :size="14" />测试</button>
                  <button class="btn btn-primary btn-sm" @click="saveServiceType('oss')"><Save :size="14" />保存</button>
                  <button class="btn btn-ghost btn-sm aliyun-delete" @click="deleteServiceType('oss')"><Trash2 :size="14" />删除</button>
                </div>
              </header>
              <div class="aliyun-field-grid">
                <label>供应商 / 类型<AppSelect v-model="serviceDrafts.oss.provider" :options="ossProviderOptions" /></label>
                <label>配置名称<input v-model="serviceDrafts.oss.name" class="input" /></label>
                <template v-if="serviceDrafts.oss.provider === 'aliyun'">
                  <label>AccessKey ID<PasswordField v-model="serviceDrafts.oss.access_key_id" /></label>
                  <label>AccessKey Secret<PasswordField v-model="serviceDrafts.oss.access_key_secret" /></label>
                  <label>Bucket 名称<input v-model="serviceDrafts.oss.bucket" class="input" /></label>
                  <label>Region<input v-model="serviceDrafts.oss.region" class="input" /></label>
                  <label>URL 过期<input v-model.number="serviceDrafts.oss.url_expire_hours" class="input" type="number" /></label>
                </template>
              </div>
            </article>

            <article class="aliyun-card aliyun-ocr">
              <header class="aliyun-card-head">
                <div class="aliyun-card-title">
                  <span class="aliyun-card-icon"><Scan :size="20" /></span>
                  <h2>阿里云 OCR</h2>
                </div>
                <span class="tag" :class="statusClass(serviceStatus('ocr'))">{{ statusText(serviceStatus('ocr')) }}</span>
                <div class="aliyun-card-actions">
                  <button class="btn btn-secondary btn-sm" @click="testServiceType('ocr')"><RefreshCw :size="14" />测试</button>
                  <button class="btn btn-primary btn-sm" @click="saveServiceType('ocr')"><Save :size="14" />保存</button>
                  <button class="btn btn-ghost btn-sm aliyun-delete" @click="deleteServiceType('ocr')"><Trash2 :size="14" />删除</button>
                </div>
              </header>
              <div class="aliyun-field-grid">
                <label>供应商 / 类型<AppSelect v-model="serviceDrafts.ocr.provider" :options="aliyunProviderOptions" /></label>
                <label>配置名称<input v-model="serviceDrafts.ocr.name" class="input" /></label>
                <label>AccessKey ID<PasswordField v-model="serviceDrafts.ocr.access_key_id" /></label>
                <label>AccessKey Secret<PasswordField v-model="serviceDrafts.ocr.access_key_secret" /></label>
                <label>超时<input v-model.number="serviceDrafts.ocr.timeout" class="input" type="number" /></label>
                <label>重试<input v-model.number="serviceDrafts.ocr.retries" class="input" type="number" /></label>
                <label>精度<AppSelect v-model="serviceDrafts.ocr.accuracy" :options="ocrAccuracyOptions" /></label>
              </div>
            </article>

            <article class="aliyun-card aliyun-doc-parser">
              <header class="aliyun-card-head">
                <div class="aliyun-card-title">
                  <span class="aliyun-card-icon"><FileCheck :size="20" /></span>
                  <h2>阿里云文档解析</h2>
                </div>
                <span class="tag" :class="statusClass(serviceStatus('doc_parser'))">{{ statusText(serviceStatus('doc_parser')) }}</span>
                <div class="aliyun-card-actions">
                  <button class="btn btn-secondary btn-sm" @click="testServiceType('doc_parser')"><RefreshCw :size="14" />测试</button>
                  <button class="btn btn-primary btn-sm" @click="saveServiceType('doc_parser')"><Save :size="14" />保存</button>
                  <button class="btn btn-ghost btn-sm aliyun-delete" @click="deleteServiceType('doc_parser')"><Trash2 :size="14" />删除</button>
                </div>
              </header>
              <div class="aliyun-field-grid">
                <label>供应商 / 类型<AppSelect v-model="serviceDrafts.doc_parser.provider" :options="docParserProviderOptions" /></label>
                <label>配置名称<input v-model="serviceDrafts.doc_parser.name" class="input" /></label>
                <label>AccessKey ID<PasswordField v-model="serviceDrafts.doc_parser.access_key_id" /></label>
                <label>AccessKey Secret<PasswordField v-model="serviceDrafts.doc_parser.access_key_secret" /></label>
                <label>Region<input v-model="serviceDrafts.doc_parser.region" class="input" /></label>
                <label>任务超时<input v-model.number="serviceDrafts.doc_parser.timeout_seconds" class="input" type="number" min="30" /></label>
                <label>轮询间隔<input v-model.number="serviceDrafts.doc_parser.poll_interval_seconds" class="input" type="number" min="1" /></label>
                <label>拉取步长<input v-model.number="serviceDrafts.doc_parser.layout_step_size" class="input" type="number" min="1" max="3000" /></label>
                <label>增强模式<AppSelect v-model="serviceDrafts.doc_parser.enhancement_mode" :options="enhancementModeOptions" /></label>
                <label>大模型增强<span class="aliyun-check"><AppCheckbox v-model="serviceDrafts.doc_parser.llm_enhancement" variant="switch" label="启用" /></span></label>
                <label>公式增强<span class="aliyun-check"><AppCheckbox v-model="serviceDrafts.doc_parser.formula_enhancement" variant="switch" label="启用" /></span></label>
                <label>HTML 表格<span class="aliyun-check"><AppCheckbox v-model="serviceDrafts.doc_parser.output_html_table" variant="switch" label="启用" /></span></label>
              </div>
            </article>

            <article class="aliyun-card aliyun-tts">
              <header class="aliyun-card-head">
                <div class="aliyun-card-title">
                  <span class="aliyun-card-icon"><Volume2 :size="20" /></span>
                  <h2>阿里云 TTS</h2>
                </div>
                <span class="tag" :class="statusClass(serviceStatus('tts'))">{{ statusText(serviceStatus('tts')) }}</span>
                <div class="aliyun-card-actions">
                  <button class="btn btn-secondary btn-sm" @click="testServiceType('tts')"><RefreshCw :size="14" />测试</button>
                  <button class="btn btn-primary btn-sm" @click="saveServiceType('tts')"><Save :size="14" />保存</button>
                  <button class="btn btn-ghost btn-sm aliyun-delete" @click="deleteServiceType('tts')"><Trash2 :size="14" />删除</button>
                </div>
              </header>
              <div class="aliyun-field-grid">
                <label>供应商 / 类型<AppSelect v-model="serviceDrafts.tts.provider" :options="ttsProviderOptions" /></label>
                <label>配置名称<input v-model="serviceDrafts.tts.name" class="input" /></label>
                <label>AccessKey ID<PasswordField v-model="serviceDrafts.tts.access_key_id" /></label>
                <label>AccessKey Secret<PasswordField v-model="serviceDrafts.tts.access_key_secret" /></label>
                <label>AppKey<input v-model="serviceDrafts.tts.appkey" class="input" /></label>
                <label>音色<input v-model="serviceDrafts.tts.voice" class="input" /></label>
                <label>语速<AppSlider v-model="serviceDrafts.tts.speech_rate" :min="-500" :max="500" :step="10" /></label>
                <label>音量<AppSlider v-model="serviceDrafts.tts.volume" :min="0" :max="100" :step="1" /></label>
              </div>
            </article>

            <article class="aliyun-card aliyun-email">
              <header class="aliyun-card-head">
                <div class="aliyun-card-title">
                  <span class="aliyun-card-icon"><FileText :size="20" /></span>
                  <h2>邮件服务</h2>
                </div>
                <span class="tag" :class="statusClass(serviceStatus('email'))">{{ statusText(serviceStatus('email')) }}</span>
                <div class="aliyun-card-actions">
                  <button class="btn btn-secondary btn-sm" @click="testServiceType('email')"><RefreshCw :size="14" />测试</button>
                  <button class="btn btn-primary btn-sm" @click="saveServiceType('email')"><Save :size="14" />保存</button>
                  <button class="btn btn-ghost btn-sm aliyun-delete" @click="deleteServiceType('email')"><Trash2 :size="14" />删除</button>
                </div>
              </header>
              <div class="aliyun-field-grid">
                <label>供应商 / 类型<AppSelect v-model="serviceDrafts.email.provider" :options="emailProviderOptions" /></label>
                <label>配置名称<input v-model="serviceDrafts.email.name" class="input" /></label>
                <label>Host<input v-model="serviceDrafts.email.host" class="input" /></label>
                <label>Port<input v-model.number="serviceDrafts.email.port" class="input" type="number" /></label>
                <label>发件人<input v-model="serviceDrafts.email.sender" class="input" /></label>
                <label>用户名<input v-model="serviceDrafts.email.username" class="input" /></label>
                <label>密码<PasswordField v-model="serviceDrafts.email.password" /></label>
                <label>SSL<span class="aliyun-check"><AppCheckbox v-model="serviceDrafts.email.use_ssl" variant="switch" label="启用" /></span></label>
              </div>
            </article>
          </div>
        </section>

        <section v-if="active === 'adminSystem'" key="adminSystem" class="admin-page page-view">
          <div class="page-header">
            <div class="breadcrumb"><span>系统管理</span><ChevronRight :size="14" /><span>系统参数</span></div>
            <div class="header-actions">
              <button class="btn btn-secondary" @click="restoreSettings">恢复默认</button>
              <button class="btn btn-primary" @click="saveSettings"><Save :size="14" />保存修改</button>
            </div>
          </div>
          <div class="config-layout">
            <aside class="config-nav"><button v-for="item in settingCategories" :key="item.key" class="config-nav-item" :class="{ active: settingTab === item.key }" @click="settingTab = item.key">{{ item.label }}</button></aside>
            <section class="config-content">
              <div v-if="changedSettings.length" class="alert alert-warning"><AlertTriangle :size="16" />{{ changedSettings.length }} 处未保存<button class="link-btn" @click="saveSettings">保存</button><button class="link-btn" @click="loadSettings">放弃</button></div>
              <article class="card settings-card">
                <div class="card-body">
                  <div v-for="item in activeSettingRows" :key="item.key" class="param-row">
                    <div class="param-info">
                      <div class="param-title">{{ item.label }}</div>
                      <div class="param-desc">{{ item.desc }}</div>
                    </div>
                    <div class="param-control">
                      <component :is="settingControl(item)" :item="item" :drafts="settingDrafts" />
                    </div>
                    <div class="param-current">当前值：{{ formatSettingValue(settingDrafts[item.key]) }}</div>
                  </div>
                </div>
              </article>
            </section>
          </div>
        </section>

        <section v-if="active === 'adminMonitor'" key="adminMonitor" class="admin-page">
          <div class="monitor-top"><span><RefreshCw :size="16" :class="{ spin: autoRefresh }" />{{ lastUpdatedText }}</span><AppCheckbox v-model="autoRefresh" variant="switch" label="自动刷新" /></div>
          <div class="service-overview">
            <article v-for="item in healthItems" :key="item.key" class="monitor-service" :class="statusClass(item.status)"><component :is="serviceIcon(item.key)" :size="20" /><div><strong>{{ item.name }}</strong><span>{{ item.detail }}</span></div><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></article>
          </div>
          <div class="monitor-grid">
            <article class="panel-card"><div class="panel-head"><h2>在线用户</h2><strong>{{ overview.online_users || 0 }}</strong></div><AdminChart type="line" :labels="monitorLabels" :series="onlineSeries" /></article>
            <article class="panel-card"><div class="panel-head"><h2>接口调用</h2><strong>{{ overview.api_call_count_30m || 0 }}</strong></div><AdminChart type="bar" :labels="monitorLabels" :series="apiSeries" /></article>
            <article class="panel-card"><div class="panel-head"><h2>AI 失败率</h2><span class="tag" :class="(overview.ai_failure_count_30m || 0) > 0 ? 'tag-warning' : 'tag-success'">{{ overview.ai_failure_count_30m || 0 }}</span></div><AdminChart type="line" :labels="monitorLabels" :series="aiMonitorSeries" /></article>
          </div>
          <div class="monitor-bottom"><article class="panel-card"><div class="panel-head"><h2><Activity :size="18" />异步任务</h2></div><p>待处理：{{ overview.async_queue_pending || 0 }} · Celery：{{ overview.celery_queue_length ?? '-' }}</p></article><article class="panel-card"><div class="panel-head"><h2><Database :size="18" />数据库缓存</h2></div><p>数据库：{{ statusText(overview.database_status) }} · Redis：{{ statusText(overview.cache_status) }}</p></article></div>
        </section>

        <section v-if="active === 'adminLogs'" key="adminLogs" class="admin-page">
          <div class="log-tabs"><button :class="{ active: logType === 'login' }" @click="logType = 'login'"><UserCheck :size="16" />登录日志</button><button :class="{ active: logType === 'operations' }" @click="logType = 'operations'"><Pencil :size="16" />操作日志</button><button :class="{ active: logType === 'errors' }" @click="logType = 'errors'"><AlertCircle :size="16" />错误日志</button></div>
          <article class="filter-card"><div class="search-field"><Search :size="16" /><input v-model="logKeyword" placeholder="关键词/IP地址" @keyup.enter="loadLogs" /></div><AppSelect v-if="logType === 'login'" v-model="logFilter.success" :options="logSuccessOptions" /><input v-if="logType === 'operations'" v-model="logFilter.action" class="input" placeholder="操作类型" /><AppSelect v-if="logType === 'errors'" v-model="logFilter.level" :options="logLevelOptions" /><input v-model="logFilter.start_at" class="input" type="text" placeholder="开始时间" /><input v-model="logFilter.end_at" class="input" type="text" placeholder="结束时间" /><button class="btn btn-secondary" @click="loadLogs"><Search :size="16" />查询</button></article>
          <article v-if="logType === 'errors' && todayErrors" class="alert alert-danger"><XCircle :size="16" />今日错误 {{ todayErrors }} 次<button class="link-btn" @click="logFilter.level = 'error'; loadLogs()">筛选</button></article>
          <article class="table-card"><table class="admin-table"><thead><tr><th>时间</th><th>主体</th><th>内容</th><th>来源</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="item in logs" :key="item.id"><td>{{ formatTime(item.created_at) }}</td><td>{{ logSubject(item) }}</td><td><code>{{ logContent(item) }}</code></td><td><span class="tag">{{ logMeta(item) }}</span></td><td><span class="tag" :class="item.detail?.resolved ? 'tag-success' : 'tag-warning'">{{ item.detail?.resolved ? '已处理' : '未处理' }}</span></td><td><button class="icon-action" @click="logDetail = item"><Eye :size="15" />详情</button><button v-if="logType === 'errors'" class="icon-action" @click="resolveError(item.id)"><CheckCircle :size="15" />处理</button></td></tr><tr v-if="!logs.length"><td colspan="6"><EmptyState text="暂无日志" /></td></tr></tbody></table></article>
        </section>

        <section v-if="active === 'adminBackups'" key="adminBackups" class="admin-page">
          <article class="backup-summary"><div><span>最后备份</span><strong>{{ backupSummary.last_backup ? relativeTime(backupSummary.last_backup.created_at) : '暂无' }}</strong><small>{{ backupSummary.last_backup?.status || '-' }}</small></div><div><span>备份文件</span><strong>{{ backupSummary.backup_count || 0 }}</strong><small>最旧：{{ shortDate(backupSummary.oldest_at) }}</small></div><div><span>总大小</span><strong>{{ backupSummary.total_size_label || '0 B' }}</strong><small>本地存储</small></div></article>
          <div class="backup-layout">
            <article class="panel-card"><div class="panel-head"><h2><File :size="18" />备份文件</h2><span class="tag">{{ backups.length }}</span></div><table class="admin-table compact-table"><thead><tr><th>名称</th><th>类型</th><th>大小</th><th>状态</th><th>时间</th><th>操作</th></tr></thead><tbody><tr v-for="item in backups" :key="item.id" :class="{ disabled: item.status === 'failed' }"><td class="mono">{{ item.backup_name }}</td><td><span class="tag">全量</span></td><td>{{ sizeLabel(item.file_size_bytes) }}</td><td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td><td>{{ formatTime(item.created_at) }}</td><td class="row-actions"><button class="icon-action" @click="downloadBackup(item)"><Download :size="15" />下载</button><button class="icon-action" @click="verifyBackup(item.id)"><ShieldCheck :size="15" />校验</button><button class="icon-action danger" @click="deleteBackup(item.id)"><Trash2 :size="15" />删除</button></td></tr></tbody></table></article>
            <article class="panel-card"><div class="panel-head"><h2><Settings :size="18" />自动备份</h2></div><div class="policy-form"><AppCheckbox v-model="backupPolicy.enabled" variant="switch" label="启用自动备份" /><label>备份频率<AppSelect v-model="backupPolicy.frequency" :options="backupFrequencyOptions" /></label><label>备份时间<input v-model="backupPolicy.time" class="input" type="text" placeholder="03:00" /></label><label>保留数量<input v-model.number="backupPolicy.retention" class="input" type="number" /></label><label>通知邮箱<input v-model="backupNotifyEmail" class="input" type="email" /></label><button class="btn btn-primary wide-btn" @click="saveBackupPolicy">保存</button></div></article>
          </div>
          <article class="danger-zone"><AlertTriangle :size="18" /><div><strong>数据恢复</strong><span>恢复将覆盖当前数据。</span></div><AppSelect v-model="restoreBackupId" :options="restoreBackupOptions" /><input v-model="restoreConfirm" class="input" placeholder="CONFIRM" /><button class="btn btn-danger" :disabled="restoreConfirm !== 'CONFIRM' || !restoreBackupId" @click="restoreBackupAction">恢复</button></article>
        </section>
      </TransitionGroup>
    </main>

    <Transition name="drawer">
      <aside v-if="userDrawer" class="drawer">
        <div class="drawer-head"><h2>{{ userDrawer.user.nickname }}</h2><span class="tag">{{ roleText(userDrawer.user.role) }}</span><button class="icon-action" @click="userDrawer = null"><X :size="16" />关闭</button></div>
        <div class="drawer-body">
          <section>
            <h3>基本信息</h3>
            <InfoRow label="邮箱" :value="userDrawer.user.email" />
            <InfoRow label="状态" :value="statusText(userDrawer.user.status)" />
            <InfoRow label="注册" :value="formatTime(userDrawer.user.created_at)" />
            <InfoRow label="最近登录" :value="formatTime(userDrawer.user.last_login_at)" />
            <InfoRow label="最近活跃" :value="formatTime(userDrawer.user.last_seen_at)" />
          </section>
          <section>
            <h3>账号权限</h3>
            <label class="drawer-field">用户角色<AppSelect :model-value="userDrawer.user.role" :options="userRoleOptions" :disabled="isPending(`role:${userDrawer.user.id}`)" @update:model-value="selectUserRole(userDrawer.user, $event)" /></label>
          </section>
          <section>
            <h3>关联课程</h3>
            <div v-for="item in userDrawer.courses" :key="`${item.relation}-${item.id}`" class="row-card course-row-card">
              <div><strong>{{ item.name }}</strong><small>{{ item.term }} · {{ item.course_code }} · {{ statusText(item.status) }}</small></div>
              <span class="tag" :class="item.relation === 'teacher' ? 'tag-success' : 'tag-primary'">{{ item.role }}</span>
            </div>
            <EmptyState v-if="!userDrawer.courses.length" text="暂无关联课程" />
          </section>
          <section>
            <h3>操作日志</h3>
            <div v-for="item in userDrawer.logs" :key="item.id" class="timeline-item"><i></i><strong>{{ item.action }}</strong><span>{{ formatTime(item.created_at) }}</span></div>
            <EmptyState v-if="!userDrawer.logs.length" text="暂无日志" />
          </section>
        </div>
        <div class="drawer-foot"><button class="btn btn-danger" :data-loading="isPending(`delete:${userDrawer.user.id}`)" :disabled="isPending(`delete:${userDrawer.user.id}`)" @click="deleteUser(userDrawer.user.id)">删除</button><button class="btn btn-secondary" :data-loading="isPending(`reset:${userDrawer.user.id}`)" :disabled="isPending(`reset:${userDrawer.user.id}`)" @click="openResetPasswordModal(userDrawer.user)">修改密码</button></div>
      </aside>
    </Transition>

    <Transition name="drawer">
      <aside v-if="courseDrawer" class="drawer wide">
        <div class="drawer-head"><h2>{{ courseDrawer.course.name }}</h2><span class="tag" :class="statusClass(courseDrawer.course.status)">{{ statusText(courseDrawer.course.status) }}</span><button class="icon-action" @click="courseDrawer = null"><X :size="16" />关闭</button></div>
        <div class="drawer-body"><section><h3>基本信息</h3><InfoRow label="课程码" :value="courseDrawer.course.course_code" /><InfoRow label="教师" :value="String(courseDrawer.course.teacher_id)" /><InfoRow label="学生" :value="String(courseDrawer.student_count)" /><InfoRow label="资料" :value="String(courseDrawer.material_count)" /></section><section><h3>学生列表</h3><div v-for="item in courseDrawer.students" :key="item.membership_id" class="row-card"><span>{{ item.user.nickname }}</span><span class="tag">{{ item.user.email }}</span></div></section><section><h3>课程资料</h3><div v-for="item in courseDrawer.materials" :key="item.id" class="row-card"><span>{{ item.title }}</span><button class="link-btn" @click="deleteMaterial(item.id)">删除</button></div></section><section><h3>课时列表</h3><div v-for="item in courseDrawer.lessons" :key="item.id" class="row-card"><span>{{ item.title }}</span><span class="tag">{{ item.status }}</span></div></section></div>
        <div class="drawer-foot"><input v-model.number="takeoverTeacherId" class="input" type="number" placeholder="教师ID" /><button class="btn btn-secondary" @click="takeoverCourse(courseDrawer.course.id)">接管</button><button class="btn btn-danger" @click="deactivateCourse(courseDrawer.course.id)">下架</button></div>
      </aside>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="adminModalOpen" class="modal-mask">
        <article class="modal">
          <div class="modal-head"><Shield :size="20" /><h2>创建用户账号</h2><button class="icon-action" @click="adminModalOpen = false"><X :size="16" />关闭</button></div>
          <p v-if="adminFormError" class="form-error input-error-shake"><AlertCircle :size="15" />{{ adminFormError }}</p>
          <div class="form-grid"><label>用户名<input v-model="adminForm.nickname" class="input" :aria-invalid="adminFormError.includes('用户名')" /></label><label>邮箱<input v-model="adminForm.email" class="input" type="email" :aria-invalid="adminFormError.includes('邮箱')" /></label><label>角色<AppSelect v-model="adminForm.role" :options="adminRoleOptions" /></label><label v-if="adminForm.role === 'teacher'">工号<input v-model="adminForm.employee_no" class="input" :aria-invalid="adminFormError.includes('工号')" /></label><label v-if="adminForm.role === 'student'">学号<input v-model="adminForm.student_no" class="input" :aria-invalid="adminFormError.includes('学号')" /></label><label>初始密码<PasswordField v-model="adminForm.password" :aria-invalid="adminFormError.includes('密码')" /></label><label>确认密码<PasswordField v-model="adminForm.confirm" :aria-invalid="adminFormError.includes('密码') || adminFormError.includes('不一致')" /></label><label class="wide-field">备注<textarea v-model="adminForm.note" class="textarea"></textarea></label></div>
          <footer><button class="btn btn-secondary" @click="adminModalOpen = false">取消</button><button class="btn btn-primary" @click="createAdmin"><Plus :size="16" />创建</button></footer>
        </article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="resetPasswordModalOpen" class="modal-mask">
        <article class="modal password-set-modal">
          <div class="modal-head"><KeyRound :size="20" /><h2>{{ resetPasswordContext.mode === 'batch' ? '批量修改密码' : '修改用户密码' }}</h2><button class="icon-action" @click="closeResetPasswordModal"><X :size="16" />关闭</button></div>
          <div class="password-target-card">
            <span class="password-target-icon"><ShieldCheck :size="20" /></span>
            <div><strong>{{ resetPasswordTargetTitle }}</strong><p>{{ resetPasswordTargetSubtitle }}</p></div>
          </div>
          <p v-if="resetPasswordForm.error" class="form-error input-error-shake"><AlertCircle :size="15" />{{ resetPasswordForm.error }}</p>
          <div class="password-form-grid">
            <label>新密码<PasswordField v-model="resetPasswordForm.password" placeholder="输入指定新密码，至少 8 位" :aria-invalid="resetPasswordForm.error.includes('密码')" /></label>
            <label>确认密码<PasswordField v-model="resetPasswordForm.confirm" placeholder="再次输入新密码" :aria-invalid="resetPasswordForm.error.includes('密码') || resetPasswordForm.error.includes('不一致')" /></label>
          </div>
          <div class="password-tools-row">
            <button class="btn btn-secondary" type="button" @click="fillGeneratedResetPassword"><RefreshCw :size="15" />生成随机密码</button>
            <span>批量修改时，所选用户将使用同一个新密码。</span>
          </div>
          <footer><button class="btn btn-secondary" @click="closeResetPasswordModal">取消</button><button class="btn btn-primary" :data-loading="isPending('reset-password-modal')" :disabled="isPending('reset-password-modal')" @click="submitResetPassword"><KeyRound :size="16" />确认修改</button></footer>
        </article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="resetPasswordResult" class="modal-mask">
        <article class="modal password-modal">
          <div class="modal-head"><KeyRound :size="20" /><h2>新密码</h2><button class="icon-action" @click="resetPasswordResult = ''"><X :size="16" />关闭</button></div>
          <div class="password-box">{{ resetPasswordResult }}</div>
          <footer><button class="btn btn-secondary" @click="copyPassword">复制</button><button class="btn btn-primary" @click="resetPasswordResult = ''">关闭</button></footer>
        </article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="previewItem" class="modal-mask">
        <article class="modal preview-modal"><div class="modal-head"><FileText :size="20" /><h2>{{ previewItem.title }}</h2><button class="icon-action" @click="previewItem = null"><X :size="16" />关闭</button></div><iframe v-if="previewItem.preview_url" :src="previewItem.preview_url"></iframe><EmptyState v-else text="暂无预览" /></article>
      </div>
    </Transition>

    <Transition name="modal-pop">
      <div v-if="logDetail" class="modal-mask">
        <article class="modal"><div class="modal-head"><FileText :size="20" /><h2>日志详情</h2><button class="icon-action" @click="logDetail = null"><X :size="16" />关闭</button></div><pre>{{ JSON.stringify(logDetail, null, 2) }}</pre><footer><button class="btn btn-secondary" @click="logDetail = null">关闭</button></footer></article>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  Activity, AlertCircle, AlertTriangle, Ban, BarChart2, Bell, BookOpen, CheckCircle, CheckSquare, ChevronDown,
  ChevronRight, Clock, Cloud, Database, Download, Eye, File, FileCheck, FileText, GraduationCap, Grid2X2,
  Inbox, KeyRound, Layers, LayoutDashboard, List, LogOut, Menu, Pencil, Plus, RefreshCw,
  Save, Scan, Search, Server, Settings, Shield, ShieldCheck, Sparkles, Trash2, Upload, User, UserCheck,
  Users, Volume2, X, XCircle
} from "lucide-vue-next";
import { api } from "../api/client";
import { routeByPage } from "../router";
import type { Role, User as UserType } from "../types";
import AppCheckbox from "../components/AppCheckbox.vue";
import AppSelect from "../components/AppSelect.vue";
import AppSlider from "../components/AppSlider.vue";
import PasswordField from "../components/PasswordField.vue";
import AdminChart from "./admin/AdminChart.vue";

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();
const router = useRouter();

type ServiceKey = "oss" | "ocr" | "doc_parser" | "tts" | "email";

const collapsed = ref(false);
const userMenuOpen = ref(false);
const sidebarNavRef = ref<HTMLElement | null>(null);
const userMenuRef = ref<HTMLElement | null>(null);
const sidebarScrollable = ref(false);
const pendingAction = ref("");
const active = ref(props.pageKey || "adminDashboard");
const trendOptions = ["7天", "30天", "90天"];
const trendRange = ref("30天");
const usageOptions = ["次数", "Token", "费用"];
const dashboard = ref<any>({});
const health = ref<any>(null);
const overview = ref<any>({});
const monitorSeriesData = ref<any>({ points: [] });
const users = ref<any[]>([]);
const userStats = ref<any>({});
const courses = ref<any[]>([]);
const courseStats = ref<any>({});
const materials = ref<any[]>([]);
const materialStats = ref<any>({});
const models = ref<any[]>([]);
const usage = ref<any>({});
const services = ref<any[]>([]);
const settings = ref<any[]>([]);
const logs = ref<any[]>([]);
const backups = ref<any[]>([]);
const backupSummary = ref<any>({});
const userDrawer = ref<any | null>(null);
const courseDrawer = ref<any | null>(null);
const previewItem = ref<any | null>(null);
const logDetail = ref<any | null>(null);
const adminModalOpen = ref(false);
const adminFormError = ref("");
const resetPasswordResult = ref("");
const resetPasswordModalOpen = ref(false);
const resetPasswordContext = reactive({ mode: "single" as "single" | "batch", ids: [] as number[], names: [] as string[], emails: [] as string[] });
const resetPasswordForm = reactive({ password: "", confirm: "", error: "" });
const selectedUsers = ref<number[]>([]);
const selectedCourses = ref<number[]>([]);
const selectedMaterials = ref<number[]>([]);
const courseView = ref<"table" | "grid">("table");
const courseTerm = ref("");
const modelTab = ref<"llm" | "embedding" | "usage">("llm");
const usageUnit = ref("次数");
const settingTab = ref("upload");
const logType = ref<"login" | "operations" | "errors">("login");
const logKeyword = ref("");
const autoRefresh = ref(true);
const lastUpdatedAt = ref<Date | null>(null);
const takeoverTeacherId = ref<number | null>(null);
const restoreBackupId = ref(0);
const restoreConfirm = ref("");
let refreshTimer: number | undefined;
let sidebarResizeObserver: ResizeObserver | undefined;

const userFilter = reactive({ keyword: "", role: "", status: "" });
const userRoleOptions: Array<{ value: Role; label: string }> = [
  { value: "student", label: "学生" },
  { value: "teacher", label: "教师" },
  { value: "admin", label: "管理员" }
];
const userRoleFilterOptions = [{ label: "全部", value: "" }, ...userRoleOptions];
const adminRoleOptions: Array<{ value: Role; label: string }> = [
  { value: "teacher", label: "教师" },
  { value: "admin", label: "管理员" },
  { value: "student", label: "学生" }
];
const userStatusOptions = [{ label: "全部", value: "" }, { label: "正常", value: "active" }, { label: "禁用", value: "disabled" }];
const courseStatusOptions = [{ label: "全部", value: "" }, { label: "正常", value: "active" }, { label: "下架", value: "inactive" }];
const materialTypeOptions = [{ label: "全部", value: "" }, { label: "PPT", value: "pptx" }, { label: "PDF", value: "pdf" }, { label: "Word", value: "docx" }, { label: "TXT", value: "txt" }];
const materialCategoryOptions = [{ label: "分类", value: "" }, { label: "课件", value: "courseware" }, { label: "讲义", value: "handout" }, { label: "练习", value: "exercise" }, { label: "参考", value: "reference" }];
const modelProviderOptions = [{ label: "通义千问", value: "qwen" }, { label: "DeepSeek", value: "deepseek" }, { label: "OpenAI", value: "openai" }, { label: "Azure", value: "azure" }, { label: "Mock", value: "mock" }, { label: "自定义", value: "custom" }];
const embeddingProviderOptions = [{ label: "通义千问", value: "qwen" }, { label: "OpenAI", value: "openai" }, { label: "Mock", value: "mock" }];
const ossProviderOptions = [{ label: "阿里云 OSS", value: "aliyun" }, { label: "本地存储", value: "local" }, { label: "Mock", value: "mock" }];
const aliyunProviderOptions = [{ label: "阿里云 OCR", value: "aliyun" }, { label: "Mock", value: "mock" }];
const docParserProviderOptions = [{ label: "阿里云 DocMind", value: "aliyun" }, { label: "Mock", value: "mock" }];
const ttsProviderOptions = [{ label: "阿里云 TTS", value: "aliyun" }, { label: "Mock", value: "mock" }];
const emailProviderOptions = [{ label: "SMTP", value: "smtp" }, { label: "Mock", value: "mock" }];
const ocrAccuracyOptions = [{ label: "普通", value: "normal" }, { label: "高精度", value: "high" }];
const enhancementModeOptions = [{ label: "VLM", value: "VLM" }, { label: "关闭", value: "" }];
const logSuccessOptions = [{ label: "全部", value: "" }, { label: "成功", value: "true" }, { label: "失败", value: "false" }];
const logLevelOptions = [{ label: "全部", value: "" }, { label: "WARNING", value: "warning" }, { label: "ERROR", value: "error" }, { label: "CRITICAL", value: "critical" }];
const backupFrequencyOptions = [{ label: "每天", value: "daily" }, { label: "每6小时", value: "6h" }, { label: "每小时", value: "hourly" }];
const courseFilter = reactive({ keyword: "", status: "" });
const materialFilter = reactive({ keyword: "", category: "", material_type: "", teacher_id: null as number | null });
const logFilter = reactive({ success: "", action: "", level: "", source: "", start_at: "", end_at: "" });
const adminForm = reactive({ email: "", nickname: "", password: "", confirm: "", role: "teacher" as Role, student_no: "", employee_no: "", note: "" });
const modelGlobal = reactive({ provider: "qwen", endpoint: "https://dashscope.aliyuncs.com/compatible-mode/v1", api_key: "" });
const modelDrafts = reactive<Record<string, any>>({});
const embeddingDraft = reactive({ config_id: null as number | null, provider: "qwen", model_name: "text-embedding-v2", endpoint: "", api_key: "", dimensions: 1536 });
const settingDrafts = reactive<Record<string, any>>({});
const originalSettings = ref<Record<string, any>>({});
const backupPolicy = reactive({ enabled: false, frequency: "daily", time: "03:00", retention: 30 });
const backupNotifyEmail = ref("");
const serviceDrafts = reactive<Record<ServiceKey, any>>({
  oss: { config_id: null, provider: "aliyun", name: "OSS", is_enabled: true, access_key_id: "", access_key_secret: "", region: "cn-hangzhou", bucket: "", url_expire_hours: 24 },
  ocr: { config_id: null, provider: "aliyun", name: "OCR", is_enabled: true, access_key_id: "", access_key_secret: "", region: "cn-hangzhou", timeout: 10, retries: 3, accuracy: "normal" },
  doc_parser: { config_id: null, provider: "aliyun", name: "文档解析", is_enabled: true, access_key_id: "", access_key_secret: "", region: "cn-hangzhou", timeout_seconds: 600, poll_interval_seconds: 5, layout_step_size: 100, output_format: "markdown", llm_enhancement: true, enhancement_mode: "VLM", formula_enhancement: false, output_html_table: false },
  tts: { config_id: null, provider: "aliyun", name: "TTS", is_enabled: true, access_key_id: "", access_key_secret: "", appkey: "", voice: "xiaoyun", speech_rate: 0, volume: 50, sample_rate: 16000, format: "wav" },
  email: { config_id: null, provider: "smtp", name: "邮件", is_enabled: true, host: "", port: 465, sender: "", username: "", password: "", use_ssl: true, use_tls: false }
});

const navGroups = [
  { title: "概览", items: [{ key: "adminDashboard", label: "总览仪表盘", icon: LayoutDashboard }] },
  { title: "用户与课程", items: [{ key: "adminUsers", label: "用户管理", icon: Users }, { key: "adminCourses", label: "课程管理", icon: BookOpen }, { key: "adminMaterials", label: "资料审核", icon: FileCheck }] },
  { title: "AI 与服务", items: [{ key: "adminModels", label: "AI 模型配置", icon: Sparkles }, { key: "adminServices", label: "阿里云服务", icon: Cloud }] },
  { title: "系统", items: [{ key: "adminSystem", label: "系统参数", icon: Settings }, { key: "adminMonitor", label: "系统监控", icon: Activity }, { key: "adminLogs", label: "日志管理", icon: FileText }, { key: "adminBackups", label: "数据备份", icon: Database }] }
];
const llmPurposes = [
  { key: "qa", label: "课程问答", icon: FileText },
  { key: "script", label: "讲解脚本", icon: Sparkles },
  { key: "quiz", label: "测验题目", icon: CheckSquare },
  { key: "tutoring", label: "题目辅导", icon: Layers },
  { key: "analysis", label: "教学分析", icon: BarChart2 },
  { key: "general", label: "默认通用", icon: Settings }
];
for (const item of llmPurposes) modelDrafts[item.key] = { config_id: null, model_name: "", temperature: 0.2, max_tokens: 2048 };

const settingCategories = [
  { key: "upload", label: "文件上传" },
  { key: "ai", label: "AI 行为" },
  { key: "classroom", label: "课时音频" },
  { key: "quiz", label: "测验参数" },
  { key: "interface", label: "界面公告" },
  { key: "backup", label: "备份参数" }
];
const settingRows = [
  { key: "upload.max_size_mb", category: "upload", label: "单文件大小", desc: "上传文件上限", type: "number" },
  { key: "upload.allowed_types", category: "upload", label: "文件格式", desc: "支持资料格式", type: "checks", options: ["ppt", "pptx", "pdf", "doc", "docx", "txt", "md", "markdown"] },
  { key: "course.material.max_count", category: "upload", label: "课程资料数", desc: "单课程上限", type: "number" },
  { key: "upload.max_files_once", category: "upload", label: "单次上传数", desc: "一次上传上限", type: "number" },
  { key: "qa.context.turn_limit", category: "ai", label: "上下文轮次", desc: "多轮问答记忆", type: "range", min: 1, max: 20 },
  { key: "tutoring.default_release_level", category: "ai", label: "辅导级别", desc: "默认开放层级", type: "number" },
  { key: "qa.out_of_scope_policy", category: "ai", label: "超范围策略", desc: "课程外回答方式", type: "select", options: ["reject", "answer_with_notice"] },
  { key: "qa.max_answer_tokens", category: "ai", label: "回答 Token", desc: "问答最大长度", type: "number" },
  { key: "qa.source_limit", category: "ai", label: "引用条数", desc: "最多来源数量", type: "number" },
  { key: "lesson.script.max_length", category: "classroom", label: "脚本字数", desc: "每页最大长度", type: "number" },
  { key: "tts.default_rate", category: "classroom", label: "TTS 语速", desc: "默认语速", type: "range", min: -500, max: 500 },
  { key: "tts.default_volume", category: "classroom", label: "TTS 音量", desc: "默认音量", type: "range", min: 0, max: 100 },
  { key: "subtitle.sync_tolerance_ms", category: "classroom", label: "字幕延迟", desc: "同步容忍毫秒", type: "number" },
  { key: "quiz.default_question_count", category: "quiz", label: "默认题量", desc: "生成题目数", type: "number" },
  { key: "quiz.question_ratio", category: "quiz", label: "题型比例", desc: "选择/判断/简答", type: "json" },
  { key: "quiz.practice_show_answer", category: "quiz", label: "练习答案", desc: "作答后显示", type: "toggle" },
  { key: "quiz.exam_show_answer", category: "quiz", label: "测验答案", desc: "交卷后显示", type: "toggle" },
  { key: "system.announcement", category: "interface", label: "系统公告", desc: "公告内容", type: "textarea" },
  { key: "system.announcement_enabled", category: "interface", label: "公告启用", desc: "是否展示", type: "toggle" },
  { key: "system.announcement_scope", category: "interface", label: "公告对象", desc: "展示范围", type: "select", options: ["student", "teacher", "all"] },
  { key: "system.logo_url", category: "interface", label: "Logo URL", desc: "平台标识", type: "text" },
  { key: "backup.schedule", category: "backup", label: "备份计划", desc: "自动备份策略", type: "json" },
  { key: "backup.notify_email", category: "backup", label: "通知邮箱", desc: "失败通知", type: "text" }
];

const currentTitle = computed(() => navGroups.flatMap((group) => group.items).find((item) => item.key === active.value)?.label || "总览仪表盘");
const todayText = computed(() => new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" }));
const healthItems = computed(() => health.value?.items || dashboard.value.service_health?.items || []);
const alertCount = computed(() => healthItems.value.filter((item: any) => ["down", "not_configured", "failed"].includes(item.status)).length);
const trendDays = computed(() => Number.parseInt(trendRange.value, 10) || 30);
const trendSubtitle = computed(() => `过去 ${trendDays.value} 天`);
const activityLabels = computed(() => (dashboard.value.activity_trend || []).map((item: any) => item.date));
const activitySeries = computed(() => [{ name: "活跃用户", data: (dashboard.value.activity_trend || []).map((item: any) => item.active_users), color: "#D9A05B" }, { name: "AI 调用", data: (dashboard.value.activity_trend || []).map((item: any) => item.ai_calls), color: "#00B8D4" }]);
const filteredCourses = computed(() => courses.value.filter((item) => !courseTerm.value || String(item.term || "").includes(courseTerm.value)));
const storagePercent = computed(() => Math.round(((materialStats.value.storage_used_bytes || 0) / (materialStats.value.storage_quota_bytes || 1)) * 100));
const modelWarning = computed(() => models.value.some((item) => item.purpose !== "embedding") ? "" : "大语言模型未配置");
const usageTotal = computed(() => {
  const items = usage.value.items || [];
  const calls = items.reduce((sum: number, item: any) => sum + Number(item.call_count || 0), 0);
  const tokens = items.reduce((sum: number, item: any) => sum + Number(item.prompt_tokens || 0) + Number(item.completion_tokens || 0), 0);
  const cost = items.reduce((sum: number, item: any) => sum + Number(item.estimated_cost || 0), 0).toFixed(4);
  return { calls, tokens, cost };
});
const usageLabels = computed(() => (usage.value.items || []).map((item: any) => item.provider));
const usageSeries = computed(() => {
  const items = usage.value.items || [];
  if (usageUnit.value === "Token") return [{ name: "Token", data: items.map((item: any) => Number(item.prompt_tokens || 0) + Number(item.completion_tokens || 0)), color: "#06B6D4" }];
  if (usageUnit.value === "费用") return [{ name: "费用", data: items.map((item: any) => Number(item.estimated_cost || 0)), color: "#10B981" }];
  return [{ name: "次数", data: items.map((item: any) => item.call_count || 0), color: "#D9A05B" }];
});
const activeSettingRows = computed(() => settingRows.filter((item) => item.category === settingTab.value));
const changedSettings = computed(() => Object.keys(settingDrafts).filter((key) => JSON.stringify(settingDrafts[key]) !== JSON.stringify(originalSettings.value[key])));
const monitorLabels = computed(() => (monitorSeriesData.value.points || []).map((item: any) => item.time));
const onlineSeries = computed(() => [{ name: "在线", data: (monitorSeriesData.value.points || []).map((item: any) => item.online_users), color: "#D9A05B" }]);
const apiSeries = computed(() => [{ name: "API", data: (monitorSeriesData.value.points || []).map((item: any) => item.api_calls), color: "#06B6D4" }]);
const aiMonitorSeries = computed(() => [{ name: "AI", data: (monitorSeriesData.value.points || []).map((item: any) => item.ai_calls), color: "#00B8D4" }, { name: "失败率", data: (monitorSeriesData.value.points || []).map((item: any) => item.ai_failure_rate), color: "#C62828" }]);
const lastUpdatedText = computed(() => (lastUpdatedAt.value ? `${relativeTime(lastUpdatedAt.value.toISOString())}更新` : "未更新"));
const todayErrors = computed(() => logs.value.filter((item) => String(item.level).toLowerCase() === "error").length);
const restoreBackupOptions = computed(() => [{ label: "选择备份", value: 0 }, ...backups.value.map((item) => ({ label: item.backup_name, value: item.id }))]);
const resetPasswordTargetTitle = computed(() => {
  if (resetPasswordContext.mode === "batch") return `已选择 ${resetPasswordContext.ids.length} 个账号`;
  return resetPasswordContext.names[0] || "指定账号";
});
const resetPasswordTargetSubtitle = computed(() => {
  if (resetPasswordContext.mode === "batch") return resetPasswordContext.names.slice(0, 3).join("、") + (resetPasswordContext.names.length > 3 ? ` 等 ${resetPasswordContext.names.length} 人` : "");
  return resetPasswordContext.emails[0] || "学生/教师账号";
});

async function run<T>(task: () => Promise<T>, ok?: string) {
  try {
    const data = await task();
    if (ok) emit("notice", "success", ok);
    return data;
  } catch (error) {
    emit("notice", "error", (error as Error).message);
    return null;
  }
}
function isPending(key: string) {
  return pendingAction.value === key;
}
async function withPending<T>(key: string, task: () => Promise<T>) {
  if (pendingAction.value) return null;
  pendingAction.value = key;
  try {
    return await task();
  } finally {
    pendingAction.value = "";
  }
}
function updateSidebarOverflow() {
  nextTick(() => {
    const nav = sidebarNavRef.value;
    if (!nav) return;
    sidebarScrollable.value = nav.scrollHeight > nav.clientHeight + 1;
  });
}
function openAdminNotifications() {
  if (alertCount.value) {
    emit("notice", "warning", `当前有 ${alertCount.value} 个服务状态需要关注`);
    go("adminMonitor");
    return;
  }
  emit("notice", "info", "暂无新通知");
}
function openAdminProfile() {
  userMenuOpen.value = false;
  emit("notice", "info", `${props.user.nickname || "管理员"} · ${props.user.email || "管理账号"}`);
}
async function go(key: string) {
  userMenuOpen.value = false;
  await router.push(routeByPage[key] || "/admin");
}
function statusClass(status: unknown) {
  if (["ok", "ready", "active", "success", "configured"].includes(String(status))) return "tag-success";
  if (["pending", "processing", "warning", "not_configured"].includes(String(status))) return "tag-warning";
  if (["down", "failed", "disabled", "inactive"].includes(String(status))) return "tag-danger";
  return "";
}
function statusText(status: unknown) {
  const map: Record<string, string> = { ok: "正常", ready: "已解析", active: "正常", success: "成功", configured: "已配置", pending: "待处理", processing: "处理中", warning: "告警", not_configured: "未配置", down: "异常", failed: "失败", disabled: "禁用", inactive: "下架" };
  return map[String(status)] || String(status || "-");
}
function roleText(role: string) {
  return { student: "学生", teacher: "教师", admin: "管理员" }[role] || role;
}
function firstChar(value: string) {
  return (value || "-").slice(0, 1);
}
function formatTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
function shortDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("zh-CN");
}
function relativeTime(value?: string | null) {
  if (!value) return "从未";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "刚刚";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`;
  return `${Math.floor(seconds / 86400)}天前`;
}
function isStale(value?: string | null) {
  if (!value) return true;
  return Date.now() - new Date(value).getTime() > 7 * 86400 * 1000;
}
function sizeLabel(size?: number) {
  const value = Number(size || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
}
function serviceIcon(key: string) {
  return { mysql: Database, redis: Server, vector: Layers, celery: Activity, oss: Cloud, tts: Volume2, ocr: Scan, doc_parser: FileCheck, email: FileText, llm: Sparkles }[key] || Server;
}
function fileIcon(type: string) {
  if (["ppt", "pptx"].includes(type)) return FileCheck;
  if (type === "pdf") return FileText;
  return File;
}
function typeText(type: string) {
  return { ppt: "PPT", pptx: "PPT", pdf: "PDF", doc: "Word", docx: "Word", txt: "TXT" }[type] || type;
}
function toggleSelect(target: number[], id: number) {
  const index = target.indexOf(id);
  if (index >= 0) target.splice(index, 1);
  else target.push(id);
}
function exportCurrent() {
  emit("notice", "info", "已准备");
}
function serviceStatus(type: ServiceKey) {
  return healthItems.value.find((item: any) => item.key === type)?.status || (serviceDrafts[type].config_id ? "configured" : "not_configured");
}
function formatSettingValue(value: unknown) {
  if (typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}
function settingControl(item: any) {
  return defineComponent({
    props: { item: { type: Object, required: true }, drafts: { type: Object, required: true } },
    setup(innerProps) {
      return () => {
        const key = innerProps.item.key;
        const update = (event: Event) => { innerProps.drafts[key] = (event.target as HTMLInputElement).value; };
        if (innerProps.item.type === "number") return h("input", { class: "input form-control", type: "number", value: innerProps.drafts[key], onInput: (event: Event) => { innerProps.drafts[key] = Number((event.target as HTMLInputElement).value); } });
        if (innerProps.item.type === "range") return h(AppSlider, { modelValue: Number(innerProps.drafts[key] || 0), min: innerProps.item.min, max: innerProps.item.max, "onUpdate:modelValue": (value: number) => { innerProps.drafts[key] = value; } });
        if (innerProps.item.type === "toggle") return h(AppCheckbox, { modelValue: !!innerProps.drafts[key], label: "启用", variant: "switch", "onUpdate:modelValue": (value: boolean) => { innerProps.drafts[key] = value; } });
        if (innerProps.item.type === "textarea") return h("textarea", { class: "textarea form-control", value: innerProps.drafts[key], onInput: update });
        if (innerProps.item.type === "select") return h(AppSelect, { modelValue: innerProps.drafts[key], options: innerProps.item.options.map((option: string) => ({ label: option, value: option })), "onUpdate:modelValue": (value: unknown) => { innerProps.drafts[key] = value; } });
        if (innerProps.item.type === "checks") return h("div", { class: "checkbox-group" }, innerProps.item.options.map((option: string) => h(AppCheckbox, { label: option, modelValue: Array.isArray(innerProps.drafts[key]) && innerProps.drafts[key].includes(option), "onUpdate:modelValue": (checked: boolean) => {
          const current = Array.isArray(innerProps.drafts[key]) ? [...innerProps.drafts[key]] : [];
          innerProps.drafts[key] = checked ? [...new Set([...current, option])] : current.filter((value) => value !== option);
        } })));
        if (innerProps.item.type === "json") return h("textarea", { class: "textarea form-control", value: JSON.stringify(innerProps.drafts[key] || {}, null, 2), onInput: (event: Event) => { try { innerProps.drafts[key] = JSON.parse((event.target as HTMLTextAreaElement).value || "{}"); } catch { innerProps.drafts[key] = (event.target as HTMLTextAreaElement).value; } } });
        return h("input", { class: "input form-control", value: innerProps.drafts[key], onInput: update });
      };
    }
  });
}

async function loadDashboard() {
  dashboard.value = (await run(() => api.get("/admin/dashboard", { activity_days: trendDays.value }))) || {};
  health.value = dashboard.value.service_health || health.value;
}
async function setTrendRange(value: string) {
  if (trendRange.value === value) return;
  trendRange.value = value;
  await loadDashboard();
}
async function loadHealth() {
  health.value = await run(() => api.get("/admin/service-health"));
}
async function loadUsers() {
  users.value = (await run(() => api.get<any[]>("/admin/users", userFilter))) || [];
  userStats.value = (await run(() => api.get("/admin/users/stats"))) || {};
}
async function loadCourses() {
  courses.value = (await run(() => api.get<any[]>("/admin/courses", courseFilter))) || [];
  courseStats.value = (await run(() => api.get("/admin/courses/stats"))) || {};
}
async function loadMaterials() {
  materials.value = (await run(() => api.get<any[]>("/admin/materials", materialFilter))) || [];
  materialStats.value = (await run(() => api.get("/admin/materials/stats"))) || {};
}
async function loadModels() {
  models.value = (await run(() => api.get<any[]>("/admin/model-configs"))) || [];
  usage.value = (await run(() => api.get("/admin/model-usage"))) || {};
  hydrateModels();
}
async function loadServices() {
  services.value = (await run(() => api.get<any[]>("/admin/service-configs"))) || [];
  hydrateServices();
  await loadHealth();
}
async function loadSettings() {
  const items = (await run(() => api.get<any[]>("/admin/system-settings"))) || [];
  settings.value = items;
  const snapshot: Record<string, any> = {};
  for (const row of settingRows) {
    const item = items.find((entry) => entry.setting_key === row.key);
    settingDrafts[row.key] = item?.setting_value ?? defaultValueForSetting(row);
    snapshot[row.key] = JSON.parse(JSON.stringify(settingDrafts[row.key]));
  }
  originalSettings.value = snapshot;
  const schedule = settingDrafts["backup.schedule"] || {};
  Object.assign(backupPolicy, { enabled: !!schedule.enabled, frequency: schedule.frequency || "daily", time: schedule.time || "03:00", retention: schedule.retention || 30 });
  backupNotifyEmail.value = String(settingDrafts["backup.notify_email"] || "");
}
async function loadMonitor() {
  overview.value = (await run(() => api.get("/admin/monitoring/overview"))) || {};
  monitorSeriesData.value = (await run(() => api.get("/admin/monitoring/timeseries"))) || { points: [] };
  await loadHealth();
  lastUpdatedAt.value = new Date();
}
function logQuery() {
  const base: Record<string, unknown> = { limit: 200, start_at: logFilter.start_at, end_at: logFilter.end_at };
  if (logType.value === "login") return { ...base, success: logFilter.success === "" ? undefined : logFilter.success === "true" };
  if (logType.value === "operations") return { ...base, action: logFilter.action || undefined };
  return { ...base, level: logFilter.level || undefined, source: logFilter.source || undefined };
}
async function loadLogs() {
  logs.value = (await run(() => api.get<any[]>(`/admin/logs/${logType.value}`, logQuery()))) || [];
}
async function loadBackups() {
  backups.value = (await run(() => api.get<any[]>("/admin/backups"))) || [];
  backupSummary.value = (await run(() => api.get("/admin/backups/summary"))) || {};
  await loadSettings();
}
async function loadActive() {
  if (active.value === "adminDashboard") await loadDashboard();
  if (active.value === "adminUsers") await loadUsers();
  if (active.value === "adminCourses") await loadCourses();
  if (active.value === "adminMaterials") await loadMaterials();
  if (active.value === "adminModels") await loadModels();
  if (active.value === "adminServices") await loadServices();
  if (active.value === "adminSystem") await loadSettings();
  if (active.value === "adminMonitor") await loadMonitor();
  if (active.value === "adminLogs") await loadLogs();
  if (active.value === "adminBackups") await loadBackups();
}
function defaultValueForSetting(row: any) {
  if (row.type === "number" || row.type === "range") return 0;
  if (row.type === "toggle") return false;
  if (row.type === "checks") return [];
  if (row.type === "json") return {};
  return "";
}
function hydrateModels() {
  for (const purpose of llmPurposes) {
    const item = models.value.find((model) => model.purpose === purpose.key);
    Object.assign(modelDrafts[purpose.key], { config_id: item?.id || null, model_name: item?.model_name || "", temperature: item?.extra_config?.temperature ?? 0.2, max_tokens: item?.extra_config?.max_tokens ?? 2048 });
    if (item && purpose.key === "qa") Object.assign(modelGlobal, { provider: item.provider, endpoint: item.endpoint || "", api_key: "" });
  }
  const embedding = models.value.find((model) => model.purpose === "embedding");
  if (embedding) Object.assign(embeddingDraft, { config_id: embedding.id, provider: embedding.provider, model_name: embedding.model_name, endpoint: embedding.endpoint || "", api_key: "", dimensions: embedding.extra_config?.dimensions || 1536 });
}
function hydrateServices() {
  for (const key of Object.keys(serviceDrafts) as ServiceKey[]) {
    const item = services.value.find((service) => service.service_type === key);
    if (item) Object.assign(serviceDrafts[key], { config_id: item.id, provider: item.provider, name: item.name, is_enabled: item.is_enabled, ...(item.config || {}) });
  }
}
async function createAdmin() {
  adminFormError.value = "";
  if (!adminForm.nickname.trim()) return void (adminFormError.value = "用户名不能为空");
  if (!adminForm.email.trim()) return void (adminFormError.value = "邮箱不能为空");
  if (adminForm.role === "teacher" && !adminForm.employee_no.trim()) return void (adminFormError.value = "工号不能为空");
  if (adminForm.role === "student" && !adminForm.student_no.trim()) return void (adminFormError.value = "学号不能为空");
  if (adminForm.password.length < 8) return void (adminFormError.value = "密码至少8位");
  if (adminForm.password !== adminForm.confirm) return void (adminFormError.value = "两次密码不一致");
  try {
    const payload: Record<string, unknown> = { email: adminForm.email, nickname: adminForm.nickname, password: adminForm.password, role: adminForm.role };
    if (adminForm.role === "teacher") payload.employee_no = adminForm.employee_no;
    if (adminForm.role === "student") payload.student_no = adminForm.student_no;
    await api.post("/admin/users/admin", payload);
    emit("notice", "success", "已创建");
    adminModalOpen.value = false;
    Object.assign(adminForm, { email: "", nickname: "", password: "", confirm: "", role: "teacher", student_no: "", employee_no: "", note: "" });
    await loadUsers();
  } catch (error) {
    adminFormError.value = (error as Error).message;
    emit("notice", "error", (error as Error).message);
  }
}
async function openUserDetail(id: number) { userDrawer.value = await run(() => api.get(`/admin/users/${id}`)); }
function generateTempPassword() {
  const random = Math.random().toString(36).slice(2, 8);
  return `Agent${random}9`;
}
async function updateUserRole(item: any, role: Role) {
  if (!userRoleOptions.some((option) => option.value === role)) return emit("notice", "warning", "角色不合法");
  if (item.role === role) return;
  await withPending(`role:${item.id}`, async () => {
    const updated = await run<any>(() => api.patch(`/admin/users/${item.id}`, { role }), "已更新");
    if (!updated) return;
    item.role = updated.role;
    if (userDrawer.value?.user?.id === item.id) userDrawer.value.user.role = updated.role;
    await loadUsers();
  });
}
function checkedValue(value: boolean | Event) {
  return typeof value === "boolean" ? value : (value.target as HTMLInputElement).checked;
}
function selectUserRole(item: any, value: unknown) {
  const role = typeof value === "string" ? value : value && (value as Event).target ? ((value as Event).target as HTMLSelectElement).value : "";
  void updateUserRole(item, role as Role);
}
function copyPassword() {
  if (!resetPasswordResult.value) return;
  navigator.clipboard?.writeText(resetPasswordResult.value);
  emit("notice", "success", "已复制");
}
function openResetPasswordModal(item: any) {
  resetPasswordResult.value = "";
  resetPasswordContext.mode = "single";
  resetPasswordContext.ids = [Number(item.id)];
  resetPasswordContext.names = [item.nickname || item.email || `用户 ${item.id}`];
  resetPasswordContext.emails = [item.email || ""];
  Object.assign(resetPasswordForm, { password: "", confirm: "", error: "" });
  resetPasswordModalOpen.value = true;
}
function openBatchResetPasswordModal() {
  if (!selectedUsers.value.length) return;
  const selected = users.value.filter((item) => selectedUsers.value.includes(item.id));
  resetPasswordResult.value = "";
  resetPasswordContext.mode = "batch";
  resetPasswordContext.ids = [...selectedUsers.value];
  resetPasswordContext.names = selected.map((item) => item.nickname || item.email || `用户 ${item.id}`);
  resetPasswordContext.emails = selected.map((item) => item.email || "");
  Object.assign(resetPasswordForm, { password: "", confirm: "", error: "" });
  resetPasswordModalOpen.value = true;
}
function closeResetPasswordModal() {
  resetPasswordModalOpen.value = false;
  Object.assign(resetPasswordForm, { password: "", confirm: "", error: "" });
}
function fillGeneratedResetPassword() {
  const password = generateTempPassword();
  resetPasswordForm.password = password;
  resetPasswordForm.confirm = password;
}
async function resetUser(id: number, password: string, silent = false, usePending = true) {
  const request = () => run(() => api.post(`/admin/users/${id}/reset-password`, { new_password: password }));
  const updated = usePending ? await withPending(`reset:${id}`, request) : await request();
  if (!updated) return false;
  if (!silent) resetPasswordResult.value = password;
  if (!silent) emit("notice", "success", "已重置");
  return true;
}
async function submitResetPassword() {
  resetPasswordForm.error = "";
  const password = resetPasswordForm.password.trim();
  if (!resetPasswordContext.ids.length) return void (resetPasswordForm.error = "请选择要修改的账号");
  if (password.length < 8) return void (resetPasswordForm.error = "密码至少8位");
  if (password.length > 64) return void (resetPasswordForm.error = "密码不能超过64位");
  if (password !== resetPasswordForm.confirm.trim()) return void (resetPasswordForm.error = "两次密码不一致");
  let successCount = 0;
  await withPending("reset-password-modal", async () => {
    for (const id of resetPasswordContext.ids) {
      if (await resetUser(id, password, true, false)) successCount += 1;
    }
  });
  if (!successCount) return;
  resetPasswordResult.value = password;
  resetPasswordModalOpen.value = false;
  selectedUsers.value = [];
  emit("notice", "success", resetPasswordContext.mode === "batch" ? `已修改 ${successCount} 人密码` : "密码已修改");
}
async function deleteUser(id: number) { await withPending(`delete:${id}`, async () => { await run(() => api.delete(`/admin/users/${id}`), "已删除"); userDrawer.value = null; await loadUsers(); }); }
async function batchDisableUsers() { for (const id of selectedUsers.value) await run(() => api.patch(`/admin/users/${id}`, { status: "disabled" })); selectedUsers.value = []; await loadUsers(); }
async function batchDeleteUsers() { for (const id of selectedUsers.value) await run(() => api.delete(`/admin/users/${id}`)); selectedUsers.value = []; await loadUsers(); }
function toggleAllUsers(value: boolean | Event) { selectedUsers.value = checkedValue(value) ? users.value.map((item) => item.id) : []; }
function clearUserFilter() { Object.assign(userFilter, { keyword: "", role: "", status: "" }); loadUsers(); }
async function openCourseDetail(id: number) { courseDrawer.value = await run(() => api.get(`/admin/courses/${id}`)); }
function openTakeover(item: any) { courseDrawer.value = { course: item, student_count: item.student_count, material_count: item.material_count, students: [], materials: [], lessons: [] }; }
async function takeoverCourse(id: number) { if (!takeoverTeacherId.value) return; await run(() => api.post(`/admin/courses/${id}/takeover`, { teacher_id: takeoverTeacherId.value }), "已接管"); await loadCourses(); }
async function deactivateCourse(id: number) { await run(() => api.post(`/admin/courses/${id}/deactivate`), "已下架"); await loadCourses(); }
async function batchDeactivateCourses() { for (const id of selectedCourses.value) await deactivateCourse(id); selectedCourses.value = []; }
function toggleAllCourses(value: boolean | Event) { selectedCourses.value = checkedValue(value) ? filteredCourses.value.map((item) => item.id) : []; }
function clearCourseFilter() { Object.assign(courseFilter, { keyword: "", status: "" }); courseTerm.value = ""; loadCourses(); }
function previewMaterial(item: any) { previewItem.value = item; }
async function deleteMaterial(id: number) { await run(() => api.delete(`/admin/materials/${id}`), "已删除"); await loadMaterials(); }
async function batchDeleteMaterials() { for (const id of selectedMaterials.value) await run(() => api.delete(`/admin/materials/${id}`)); selectedMaterials.value = []; await loadMaterials(); }
function toggleAllMaterials(value: boolean | Event) { selectedMaterials.value = checkedValue(value) ? materials.value.map((item) => item.id) : []; }
function clearMaterialFilter() { Object.assign(materialFilter, { keyword: "", category: "", material_type: "", teacher_id: null }); loadMaterials(); }
async function saveAllModels() {
  for (const purpose of llmPurposes) {
    const draft = modelDrafts[purpose.key];
    if (!draft.model_name) continue;
    await run(() => api.post("/admin/model-configs", { config_id: draft.config_id, provider: modelGlobal.provider, model_name: draft.model_name, purpose: purpose.key, endpoint: modelGlobal.endpoint, api_key: modelGlobal.api_key, is_default: purpose.key === "general", extra_config: { temperature: draft.temperature, max_tokens: draft.max_tokens } }));
  }
  if (embeddingDraft.model_name) await run(() => api.post("/admin/model-configs", { config_id: embeddingDraft.config_id, provider: embeddingDraft.provider, model_name: embeddingDraft.model_name, purpose: "embedding", endpoint: embeddingDraft.endpoint, api_key: embeddingDraft.api_key, is_default: true, extra_config: { dimensions: embeddingDraft.dimensions } }));
  emit("notice", "success", "已保存");
  await loadModels();
}
async function testDefaultModel() { const item = models.value.find((model) => model.purpose === "general") || models.value.find((model) => model.purpose !== "embedding"); if (!item) return emit("notice", "warning", "先保存"); const data = await run(() => api.post<any>(`/admin/model-configs/${item.id}/test`)); if (data) emit("notice", data.success ? "success" : "warning", data.message); }
async function testEmbeddingModel() { const item = models.value.find((model) => model.purpose === "embedding"); if (!item) return emit("notice", "warning", "先保存"); const data = await run(() => api.post<any>(`/admin/model-configs/${item.id}/test`)); if (data) emit("notice", data.success ? "success" : "warning", data.message); }
function serviceConfigPayload(type: ServiceKey) {
  const draft = serviceDrafts[type];
  const { config_id, provider, name, is_enabled, ...config } = draft;
  if (type === "oss" && provider !== "aliyun") return { url_expire_hours: serviceDrafts.oss.url_expire_hours };
  if (["oss", "ocr", "doc_parser"].includes(type)) delete config.endpoint;
  if (type === "tts") {
    delete config.token;
    delete config.url;
  }
  return config;
}
function serviceMissing(type: ServiceKey) {
  const draft = serviceDrafts[type];
  if (!draft.name || !draft.provider) return "服务必填";
  if (["mock", "local"].includes(draft.provider)) return "";
  const required: Record<ServiceKey, string[]> = { oss: ["access_key_id", "access_key_secret", "bucket"], ocr: ["access_key_id", "access_key_secret"], doc_parser: ["access_key_id", "access_key_secret"], tts: ["access_key_id", "access_key_secret", "appkey", "voice"], email: ["host", "port", "sender"] };
  const missing = required[type].filter((key) => !draft[key]);
  return missing.length ? `缺少 ${missing.join(",")}` : "";
}
async function saveServiceType(type: ServiceKey) {
  const error = serviceMissing(type);
  if (error) return emit("notice", "warning", error);
  const draft = serviceDrafts[type];
  await run(() => api.post("/admin/service-configs", { config_id: draft.config_id, service_type: type, provider: draft.provider, name: draft.name, is_enabled: draft.is_enabled, config: serviceConfigPayload(type) }), "已保存");
  await loadServices();
}
async function saveAllServices() { for (const key of Object.keys(serviceDrafts) as ServiceKey[]) await saveServiceType(key); }
async function testServiceType(type: ServiceKey) { const id = serviceDrafts[type].config_id; if (!id) return emit("notice", "warning", "先保存"); const data = await run(() => api.post<any>(`/admin/service-configs/${id}/test`)); if (data) emit("notice", data.success ? "success" : "warning", data.message); }
async function deleteServiceType(type: ServiceKey) { const id = serviceDrafts[type].config_id; if (!id) return; await run(() => api.delete(`/admin/service-configs/${id}`), "已删除"); serviceDrafts[type].config_id = null; await loadServices(); }
async function testAllServices() { const data = await run(() => api.post<any>("/admin/service-health/test-all")); if (data) emit("notice", data.success ? "success" : "warning", data.success ? "全部正常" : "存在异常"); await loadHealth(); }
async function saveSettings() {
  for (const key of changedSettings.value) await run(() => api.put(`/admin/system-settings/${key}`, { value: settingDrafts[key] }));
  emit("notice", "success", "已保存");
  await loadSettings();
}
async function restoreSettings() { await run(() => api.post("/admin/system-settings/restore-defaults"), "已恢复"); await loadSettings(); }
async function saveBackupPolicy() {
  settingDrafts["backup.schedule"] = { ...backupPolicy };
  settingDrafts["backup.notify_email"] = backupNotifyEmail.value;
  await saveSettings();
}
function logSubject(item: any) { if (logType.value === "login") return `用户 ${item.user_id || "-"}`; if (logType.value === "operations") return item.target_type || "-"; return item.level || "-"; }
function logContent(item: any) { if (logType.value === "login") return item.success ? "登录成功" : "登录失败"; if (logType.value === "operations") return item.action || "-"; return item.message || "-"; }
function logMeta(item: any) { if (logType.value === "login") return item.login_ip || "-"; if (logType.value === "operations") return item.user_id ? `用户 ${item.user_id}` : "-"; return item.source || "-"; }
async function resolveError(id: number) { await run(() => api.post(`/admin/logs/errors/${id}/resolve`), "已处理"); await loadLogs(); }
async function createBackup() { await run(() => api.post("/admin/backups"), "已备份"); await loadBackups(); }
async function verifyBackup(id: number) { const data = await run(() => api.post<any>(`/admin/backups/${id}/verify`)); if (data) emit("notice", data.success ? "success" : "warning", data.message); await loadBackups(); }
async function downloadBackup(item: any) { await run(() => api.download(`/admin/backups/${item.id}/download`, `${item.backup_name || `backup_${item.id}`}.zip`)); }
async function deleteBackup(id: number) { await run(() => api.delete(`/admin/backups/${id}`), "已删除"); await loadBackups(); }
async function restoreBackupAction() { if (restoreConfirm.value !== "CONFIRM" || !restoreBackupId.value) return; await run(() => api.post(`/admin/backups/${restoreBackupId.value}/restore`), "已恢复"); restoreConfirm.value = ""; }

watch(() => props.pageKey, (key) => { active.value = key || "adminDashboard"; loadActive(); updateSidebarOverflow(); });
watch(collapsed, updateSidebarOverflow);
watch(logType, loadLogs);
watch(adminModalOpen, (open) => { if (open) adminFormError.value = ""; });
watch(autoRefresh, (enabled) => {
  if (refreshTimer) window.clearInterval(refreshTimer);
  if (enabled) refreshTimer = window.setInterval(() => active.value === "adminMonitor" && loadMonitor(), 30000);
});
function onAdminDocumentPointerDown(event: PointerEvent) {
  if (!userMenuRef.value?.contains(event.target as Node)) userMenuOpen.value = false;
}
function onAdminDocumentKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  userMenuOpen.value = false;
  userDrawer.value = null;
  courseDrawer.value = null;
  adminModalOpen.value = false;
  resetPasswordModalOpen.value = false;
  resetPasswordResult.value = "";
  previewItem.value = null;
  logDetail.value = null;
}
onMounted(async () => {
  document.addEventListener("pointerdown", onAdminDocumentPointerDown);
  document.addEventListener("keydown", onAdminDocumentKeydown);
  await loadHealth();
  await loadActive();
  updateSidebarOverflow();
  sidebarResizeObserver = new ResizeObserver(updateSidebarOverflow);
  if (sidebarNavRef.value) sidebarResizeObserver.observe(sidebarNavRef.value);
  window.addEventListener("resize", updateSidebarOverflow);
  refreshTimer = window.setInterval(() => autoRefresh.value && active.value === "adminMonitor" && loadMonitor(), 30000);
});
onBeforeUnmount(() => {
  if (refreshTimer) window.clearInterval(refreshTimer);
  sidebarResizeObserver?.disconnect();
  document.removeEventListener("pointerdown", onAdminDocumentPointerDown);
  document.removeEventListener("keydown", onAdminDocumentKeydown);
  window.removeEventListener("resize", updateSidebarOverflow);
});

const MetricCard = defineComponent({
  props: { icon: { type: Object, required: true }, label: { type: String, required: true }, value: { type: [String, Number], required: true }, trend: { type: String, default: "" }, tone: { type: String, default: "primary" }, danger: { type: Boolean, default: false } },
  setup(p) {
    return () => h("article", { class: ["metric-card", p.tone, p.danger ? "danger" : ""] }, [h("div", [h("span", { class: "metric-icon" }, [h(p.icon as any, { size: 20 })]), h("span", p.label)]), h("strong", String(p.value)), h("small", [h(TrendingUpIcon), p.trend])]);
  }
});
const TrendingUpIcon = defineComponent(() => () => h("span", { class: "trend-dot" }));
const EmptyState = defineComponent({ props: { text: { type: String, required: true } }, setup(p) { return () => h("div", { class: "empty" }, [h(Inbox, { size: 28 }), h("span", p.text)]); } });
const InfoRow = defineComponent({ props: { label: { type: String, required: true }, value: { type: String, required: true } }, setup(p) { return () => h("div", { class: "info-row" }, [h("span", p.label), h("strong", p.value)]); } });
</script>

<style scoped src="../styles/admin-scoped.css"></style>
