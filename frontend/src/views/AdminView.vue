<template>
  <section class="admin-shell" :class="{ collapsed, 'sidebar-scrollable': sidebarScrollable }">
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <button class="menu-btn" aria-label="折叠" @click="collapsed = !collapsed"><Menu :size="20" /></button>
        <span class="logo-mark"><Sparkles :size="17" /></span>
        <strong v-if="!collapsed" class="logo-text">系统管理后台</strong>
      </div>

      <nav ref="sidebarNavRef" class="sidebar-nav">
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <span v-if="!collapsed" class="nav-title">{{ group.title }}</span>
          <button v-for="item in group.items" :key="item.key" class="nav-link" :class="{ active: active === item.key }" @click="go(item.key)">
            <component :is="item.icon" :size="18" />
            <span v-if="!collapsed">{{ item.label }}</span>
            <em v-if="collapsed">{{ item.label }}</em>
          </button>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="side-user">
          <span class="avatar">管</span>
          <div v-if="!collapsed"><strong>{{ user.nickname }}</strong><span class="tag tag-ai">Super Admin</span></div>
        </div>
      </div>
    </aside>

    <header class="admin-topbar">
      <div class="topbar-left"></div>
      <div class="top-actions">
        <span class="health-pill" :class="health?.status === 'ok' ? 'ok' : 'warn'"><i></i>{{ health?.status === 'ok' ? '运行正常' : '服务异常' }}</span>
        <button class="notice-btn" aria-label="通知"><Bell :size="20" /><em v-if="alertCount">{{ alertCount }}</em></button>
        <span class="divider"></span>
        <div class="user-menu">
          <button class="user-trigger" @click="userMenuOpen = !userMenuOpen">
            <span class="avatar">管</span><span>{{ user.nickname }}</span><ChevronDown :size="16" />
          </button>
          <Transition name="top-popover" appear>
            <div v-if="userMenuOpen" class="dropdown top-popover-panel">
              <button @click="go('profile')"><User :size="15" />资料</button>
              <button @click="$emit('logout')"><LogOut :size="15" />退出</button>
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

      <section class="admin-content">
        <section v-if="active === 'adminDashboard'" class="admin-page">
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

        <section v-if="active === 'adminUsers'" class="admin-page">
          <div class="metric-grid three">
            <MetricCard :icon="Users" label="全部用户" :value="userStats.total || 0" :trend="`本周 +${userStats.weekly_new || 0}`" />
            <MetricCard :icon="GraduationCap" label="教师" :value="userStats.teachers || 0" trend="授课账号" tone="success" />
            <MetricCard :icon="User" label="学生" :value="userStats.students || 0" trend="学习账号" tone="info" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="userFilter.keyword" placeholder="搜索用户名、邮箱、工号" @keyup.enter="loadUsers" /></div>
            <select v-model="userFilter.role" class="select"><option value="">全部</option><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option></select>
            <select v-model="userFilter.status" class="select"><option value="">全部</option><option value="active">正常</option><option value="disabled">禁用</option></select>
            <button class="btn btn-ghost" @click="clearUserFilter"><X :size="16" />清除</button>
            <span class="spacer"></span>
            <button class="btn btn-secondary" :disabled="!selectedUsers.length" @click="batchDisableUsers"><CheckSquare :size="16" />批量</button>
            <button class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出</button>
          </article>
          <article class="table-card">
            <div v-if="selectedUsers.length" class="bulk-bar"><label><input type="checkbox" checked @change="selectedUsers = []" /> 已选 {{ selectedUsers.length }} 人</label><button @click="batchDisableUsers">禁用</button><button @click="batchResetUsers">重置密码</button><button @click="batchDeleteUsers">删除</button><button @click="selectedUsers = []">取消</button></div>
            <table class="admin-table">
              <thead><tr><th class="check-col"><input type="checkbox" :checked="selectedUsers.length === users.length && users.length > 0" @change="toggleAllUsers" /></th><th>用户</th><th>角色</th><th>状态</th><th>所属课程</th><th>注册时间</th><th>最近登录</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in users" :key="item.id" :class="{ disabled: item.status === 'disabled', selected: selectedUsers.includes(item.id) }">
                  <td><input type="checkbox" :checked="selectedUsers.includes(item.id)" @change="toggleSelect(selectedUsers, item.id)" /></td>
                  <td><div class="identity"><span class="avatar small">{{ firstChar(item.nickname) }}</span><div><strong>{{ item.nickname }}</strong><span>{{ item.email }}</span></div></div></td>
                  <td><select class="select role-select" :value="item.role" :disabled="isPending(`role:${item.id}`)" @change="selectUserRole(item, $event)"><option v-for="role in userRoleOptions" :key="role.value" :value="role.value">{{ role.label }}</option></select></td>
                  <td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td>
                  <td><BookOpen :size="14" /> {{ item.course_count || '-' }}</td>
                  <td>{{ shortDate(item.created_at) }}</td>
                  <td :class="{ stale: isStale(item.last_login_at) }">{{ relativeTime(item.last_login_at) }}</td>
                  <td class="row-actions"><button class="text-action" @click="openUserDetail(item.id)"><Eye :size="14" />详情</button><button class="text-action" :data-loading="isPending(`reset:${item.id}`)" :disabled="isPending(`reset:${item.id}`)" @click="resetUser(item.id)"><KeyRound :size="14" />重置密码</button><button class="text-action danger" :data-loading="isPending(`delete:${item.id}`)" :disabled="isPending(`delete:${item.id}`)" @click="deleteUser(item.id)"><Trash2 :size="14" />删除</button></td>
                </tr>
                <tr v-if="!users.length"><td colspan="8"><EmptyState text="暂无用户" /></td></tr>
              </tbody>
            </table>
          </article>
        </section>

        <section v-if="active === 'adminCourses'" class="admin-page">
          <div class="metric-grid four">
            <MetricCard :icon="BookOpen" label="全部课程" :value="courseStats.total || 0" trend="平台课程" />
            <MetricCard :icon="Activity" label="活跃课程" :value="courseStats.active || 0" trend="正常开放" tone="success" />
            <MetricCard :icon="FileCheck" label="待审资料" :value="courseStats.pending_materials || 0" trend="需关注" :danger="(courseStats.pending_materials || 0) > 0" />
            <MetricCard :icon="Plus" label="本月新增" :value="courseStats.monthly_new || 0" trend="新建课程" tone="info" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="courseFilter.keyword" placeholder="课程名称/教师名" @keyup.enter="loadCourses" /></div>
            <select v-model="courseFilter.status" class="select"><option value="">全部</option><option value="active">正常</option><option value="inactive">下架</option></select>
            <input v-model="courseTerm" class="input" placeholder="学期" />
            <button class="btn btn-ghost" @click="clearCourseFilter"><X :size="16" />重置</button>
            <span class="spacer"></span>
            <div class="view-toggle"><button :class="{ active: courseView === 'table' }" @click="courseView = 'table'"><List :size="16" /></button><button :class="{ active: courseView === 'grid' }" @click="courseView = 'grid'"><Grid2X2 :size="16" /></button></div>
          </article>
          <article v-if="courseView === 'table'" class="table-card">
            <table class="admin-table">
              <thead><tr><th class="check-col"><input type="checkbox" :checked="selectedCourses.length === courses.length && courses.length > 0" @change="toggleAllCourses" /></th><th>课程名称</th><th>主讲教师</th><th>学期</th><th>学生数</th><th>资料数</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in filteredCourses" :key="item.id">
                  <td><input type="checkbox" :checked="selectedCourses.includes(item.id)" @change="toggleSelect(selectedCourses, item.id)" /></td>
                  <td><strong>{{ item.name }}</strong><span class="tag mono">{{ item.course_code }}</span></td>
                  <td><span class="avatar mini">{{ firstChar(item.teacher_name) }}</span>{{ item.teacher_name || item.teacher_id }}</td>
                  <td>{{ item.term }}</td><td><Users :size="14" />{{ item.student_count || 0 }}</td><td><FileText :size="14" />{{ item.material_count || 0 }}</td>
                  <td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td><td>{{ shortDate(item.created_at) }}</td>
                  <td class="row-actions"><button class="icon-action" @click="openCourseDetail(item.id)"><Eye :size="15" /></button><button class="icon-action" @click="openTakeover(item)"><UserCheck :size="15" /></button><button class="icon-action danger" @click="deactivateCourse(item.id)"><Ban :size="15" /></button></td>
                </tr>
              </tbody>
            </table>
          </article>
          <div v-else class="course-card-grid">
            <article v-for="item in filteredCourses" :key="item.id" class="course-admin-card" :class="{ inactive: item.status !== 'active' }">
              <div><strong>{{ item.name }}</strong><span class="tag mono">{{ item.course_code }}</span></div>
              <p>{{ item.teacher_name }} · {{ item.term }}</p>
              <div class="mini-metrics"><span><Users :size="14" />{{ item.student_count || 0 }}</span><span><FileText :size="14" />{{ item.material_count || 0 }}</span></div>
              <button class="icon-action" @click="openCourseDetail(item.id)"><MoreHorizontal :size="16" /></button>
            </article>
          </div>
        </section>

        <section v-if="active === 'adminMaterials'" class="admin-page">
          <div class="metric-grid three">
            <MetricCard :icon="File" label="全部资料" :value="materialStats.total || 0" trend="平台文件" />
            <MetricCard :icon="Upload" label="本月新增" :value="materialStats.monthly_new || 0" trend="上传量" tone="info" />
            <MetricCard :icon="Database" label="存储用量" :value="materialStats.storage_used_label || '0 B'" trend="资料空间" :danger="storagePercent > 90" />
          </div>
          <article class="filter-card">
            <div class="search-field"><Search :size="16" /><input v-model="materialFilter.keyword" placeholder="文件名/课程名/教师名" @keyup.enter="loadMaterials" /></div>
            <select v-model="materialFilter.material_type" class="select"><option value="">全部</option><option value="pptx">PPT</option><option value="pdf">PDF</option><option value="docx">Word</option><option value="txt">TXT</option></select>
            <select v-model="materialFilter.category" class="select"><option value="">分类</option><option value="courseware">课件</option><option value="handout">讲义</option><option value="exercise">练习</option><option value="reference">参考</option></select>
            <input v-model.number="materialFilter.teacher_id" class="input narrow" type="number" placeholder="教师ID" />
            <button class="btn btn-ghost" @click="clearMaterialFilter"><X :size="16" />清除</button><span class="spacer"></span><button class="btn btn-ghost" @click="exportCurrent"><Download :size="16" />导出</button>
          </article>
          <article class="table-card">
            <table class="admin-table">
              <thead><tr><th class="check-col"><input type="checkbox" :checked="selectedMaterials.length === materials.length && materials.length > 0" @change="toggleAllMaterials" /></th><th>文件名</th><th>所属课程</th><th>上传教师</th><th>类型</th><th>上传时间</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                <tr v-for="item in materials" :key="item.id">
                  <td><input type="checkbox" :checked="selectedMaterials.includes(item.id)" @change="toggleSelect(selectedMaterials, item.id)" /></td>
                  <td><div class="identity"><component :is="fileIcon(item.material_type)" :size="18" :class="`file-${item.material_type}`" /><div><strong>{{ item.title }}</strong><span>{{ item.size_label || sizeLabel(item.size_bytes) }}</span></div></div></td>
                  <td>{{ item.course_name || item.course_id }}</td><td><span class="avatar mini">{{ firstChar(item.teacher_name) }}</span>{{ item.teacher_name || item.uploader_id }}</td>
                  <td><span class="tag">{{ typeText(item.material_type) }}</span></td><td>{{ shortDate(item.created_at) }}</td>
                  <td><span class="tag" :class="statusClass(item.parse_status)">{{ statusText(item.parse_status) }}</span></td>
                  <td class="row-actions"><button class="icon-action" @click="previewMaterial(item)"><Eye :size="15" /></button><a v-if="item.preview_url" class="icon-action" :href="item.preview_url" target="_blank"><Download :size="15" /></a><button class="icon-action danger" @click="deleteMaterial(item.id)"><Trash2 :size="15" /></button></td>
                </tr>
              </tbody>
            </table>
          </article>
        </section>

        <section v-if="active === 'adminModels'" class="admin-page model-layout">
          <aside class="vertical-tabs"><button :class="{ active: modelTab === 'llm' }" @click="modelTab = 'llm'">大模型</button><button :class="{ active: modelTab === 'embedding' }" @click="modelTab = 'embedding'">Embedding</button><button :class="{ active: modelTab === 'usage' }" @click="modelTab = 'usage'">调用统计</button></aside>
          <section class="model-content">
            <div v-if="modelWarning" class="alert alert-danger"><AlertTriangle :size="16" />{{ modelWarning }}<button class="link-btn" @click="modelTab = 'llm'">配置</button></div>
            <article v-if="modelTab === 'llm'" class="panel-card form-panel">
              <div class="panel-head"><div><h2><Sparkles :size="18" />大语言模型</h2><span>按功能配置模型</span></div><button class="btn btn-secondary" @click="testDefaultModel">测试</button></div>
              <div class="form-section"><h3>全局设置</h3><div class="form-grid"><label>供应商<select v-model="modelGlobal.provider" class="select"><option value="qwen">通义千问</option><option value="deepseek">DeepSeek</option><option value="openai">OpenAI</option><option value="azure">Azure</option><option value="mock">Mock</option><option value="custom">自定义</option></select></label><label>API Base<input v-model="modelGlobal.endpoint" class="input" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" /></label><label class="wide-field">API Key<input v-model="modelGlobal.api_key" class="input" type="password" placeholder="加密存储" /></label></div></div>
              <div class="form-section"><h3>用途分配</h3><div class="purpose-config-grid"><article v-for="item in llmPurposes" :key="item.key" class="purpose-card"><div><component :is="item.icon" :size="16" /><strong>{{ item.label }}</strong></div><input v-model="modelDrafts[item.key].model_name" class="input" placeholder="qwen-max" /><label>Temperature <input v-model.number="modelDrafts[item.key].temperature" type="range" min="0" max="2" step="0.1" /> <b>{{ modelDrafts[item.key].temperature }}</b></label><label>最大 Token<input v-model.number="modelDrafts[item.key].max_tokens" class="input" type="number" /></label></article></div></div>
            </article>
            <article v-if="modelTab === 'embedding'" class="panel-card form-panel"><div class="panel-head"><div><h2><Layers :size="18" />Embedding 模型</h2><span>用于资料向量化</span></div><button class="btn btn-secondary" @click="testEmbeddingModel">测试</button></div><div class="form-grid"><label>供应商<select v-model="embeddingDraft.provider" class="select"><option value="qwen">通义千问</option><option value="openai">OpenAI</option><option value="mock">Mock</option></select></label><label>模型<input v-model="embeddingDraft.model_name" class="input" placeholder="text-embedding-v2" /></label><label>向量维度<input v-model.number="embeddingDraft.dimensions" class="input" type="number" /></label><label>API Key<input v-model="embeddingDraft.api_key" class="input" type="password" /></label><label class="wide-field">API Base<input v-model="embeddingDraft.endpoint" class="input" /></label></div></article>
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

        <section v-if="active === 'adminServices'" class="admin-page page-view">
          <div class="page-header">
            <div class="breadcrumb"><span>系统管理</span><ChevronRight :size="14" /><span>阿里云服务</span></div>
            <div class="header-actions">
              <button class="btn btn-secondary" @click="testAllServices"><RefreshCw :size="14" />测试全部</button>
              <button class="btn btn-primary" @click="saveAllServices"><Save :size="14" />保存配置</button>
            </div>
          </div>
          <div class="config-content service-config-stack">
            <ServiceConfigCard title="阿里云 OSS" :icon="Cloud" type="oss" :draft="serviceDrafts.oss" :status="serviceStatus('oss')" @save="saveServiceType('oss')" @test="testServiceType('oss')" @remove="deleteServiceType('oss')">
              <div class="form-group"><label class="form-label">供应商 / 类型</label><select v-model="serviceDrafts.oss.provider" class="form-control select"><option value="aliyun">阿里云 OSS</option><option value="local">本地存储</option><option value="mock">Mock</option></select></div>
              <div class="form-group"><label class="form-label">配置名称</label><input v-model="serviceDrafts.oss.name" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">AccessKey ID</label><input v-model="serviceDrafts.oss.access_key_id" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">AccessKey Secret</label><input v-model="serviceDrafts.oss.access_key_secret" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">Bucket 名称</label><input v-model="serviceDrafts.oss.bucket" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">Endpoint</label><input v-model="serviceDrafts.oss.endpoint" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">Region</label><input v-model="serviceDrafts.oss.region" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">URL 过期</label><input v-model.number="serviceDrafts.oss.url_expire_hours" class="form-control input" type="number" /></div>
            </ServiceConfigCard>
            <ServiceConfigCard title="阿里云 OCR" :icon="Scan" type="ocr" :draft="serviceDrafts.ocr" :status="serviceStatus('ocr')" @save="saveServiceType('ocr')" @test="testServiceType('ocr')" @remove="deleteServiceType('ocr')">
              <div class="form-group"><label class="form-label">供应商 / 类型</label><select v-model="serviceDrafts.ocr.provider" class="form-control select"><option value="aliyun">阿里云 OCR</option><option value="mock">Mock</option></select></div>
              <div class="form-group"><label class="form-label">配置名称</label><input v-model="serviceDrafts.ocr.name" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">AccessKey ID</label><input v-model="serviceDrafts.ocr.access_key_id" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">AccessKey Secret</label><input v-model="serviceDrafts.ocr.access_key_secret" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">Endpoint</label><input v-model="serviceDrafts.ocr.endpoint" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">超时</label><input v-model.number="serviceDrafts.ocr.timeout" class="form-control input" type="number" /></div>
              <div class="form-group"><label class="form-label">重试</label><input v-model.number="serviceDrafts.ocr.retries" class="form-control input" type="number" /></div>
              <div class="form-group"><label class="form-label">精度</label><select v-model="serviceDrafts.ocr.accuracy" class="form-control select"><option value="normal">普通</option><option value="high">高精度</option></select></div>
            </ServiceConfigCard>
            <ServiceConfigCard title="阿里云 TTS" :icon="Volume2" type="tts" :draft="serviceDrafts.tts" :status="serviceStatus('tts')" @save="saveServiceType('tts')" @test="testServiceType('tts')" @remove="deleteServiceType('tts')">
              <div class="form-group"><label class="form-label">供应商 / 类型</label><select v-model="serviceDrafts.tts.provider" class="form-control select"><option value="aliyun">阿里云 TTS</option><option value="mock">Mock</option></select></div>
              <div class="form-group"><label class="form-label">配置名称</label><input v-model="serviceDrafts.tts.name" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">AccessKey ID</label><input v-model="serviceDrafts.tts.access_key_id" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">AccessKey Secret</label><input v-model="serviceDrafts.tts.access_key_secret" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">AppKey</label><input v-model="serviceDrafts.tts.appkey" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">Token</label><input v-model="serviceDrafts.tts.token" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">URL</label><input v-model="serviceDrafts.tts.url" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">音色</label><input v-model="serviceDrafts.tts.voice" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">语速</label><input v-model.number="serviceDrafts.tts.speech_rate" class="form-control input" type="range" min="-500" max="500" /></div>
              <div class="form-group"><label class="form-label">音量</label><input v-model.number="serviceDrafts.tts.volume" class="form-control input" type="range" min="0" max="100" /></div>
            </ServiceConfigCard>
            <ServiceConfigCard title="邮件服务" :icon="FileText" type="email" :draft="serviceDrafts.email" :status="serviceStatus('email')" @save="saveServiceType('email')" @test="testServiceType('email')" @remove="deleteServiceType('email')">
              <div class="form-group"><label class="form-label">供应商 / 类型</label><select v-model="serviceDrafts.email.provider" class="form-control select"><option value="smtp">SMTP</option><option value="mock">Mock</option></select></div>
              <div class="form-group"><label class="form-label">配置名称</label><input v-model="serviceDrafts.email.name" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">Host</label><input v-model="serviceDrafts.email.host" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">Port</label><input v-model.number="serviceDrafts.email.port" class="form-control input" type="number" /></div>
              <div class="form-group"><label class="form-label">发件人</label><input v-model="serviceDrafts.email.sender" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">用户名</label><input v-model="serviceDrafts.email.username" class="form-control input" /></div>
              <div class="form-group"><label class="form-label">密码</label><input v-model="serviceDrafts.email.password" class="form-control input" type="password" /></div>
              <div class="form-group"><label class="form-label">SSL</label><label class="checkbox-label inline"><input v-model="serviceDrafts.email.use_ssl" type="checkbox" />启用</label></div>
            </ServiceConfigCard>
          </div>
        </section>

        <section v-if="active === 'adminSystem'" class="admin-page page-view">
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

        <section v-if="active === 'adminMonitor'" class="admin-page">
          <div class="monitor-top"><span><RefreshCw :size="16" :class="{ spin: autoRefresh }" />{{ lastUpdatedText }}</span><label class="switch-line"><input v-model="autoRefresh" type="checkbox" />自动刷新</label></div>
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

        <section v-if="active === 'adminLogs'" class="admin-page">
          <div class="log-tabs"><button :class="{ active: logType === 'login' }" @click="logType = 'login'"><UserCheck :size="16" />登录日志</button><button :class="{ active: logType === 'operations' }" @click="logType = 'operations'"><Pencil :size="16" />操作日志</button><button :class="{ active: logType === 'errors' }" @click="logType = 'errors'"><AlertCircle :size="16" />错误日志</button></div>
          <article class="filter-card"><div class="search-field"><Search :size="16" /><input v-model="logKeyword" placeholder="关键词/IP地址" @keyup.enter="loadLogs" /></div><select v-if="logType === 'login'" v-model="logFilter.success" class="select"><option value="">全部</option><option value="true">成功</option><option value="false">失败</option></select><input v-if="logType === 'operations'" v-model="logFilter.action" class="input" placeholder="操作类型" /><select v-if="logType === 'errors'" v-model="logFilter.level" class="select"><option value="">全部</option><option value="warning">WARNING</option><option value="error">ERROR</option><option value="critical">CRITICAL</option></select><input v-model="logFilter.start_at" class="input" type="datetime-local" /><input v-model="logFilter.end_at" class="input" type="datetime-local" /><button class="btn btn-secondary" @click="loadLogs"><Search :size="16" />查询</button></article>
          <article v-if="logType === 'errors' && todayErrors" class="alert alert-danger"><XCircle :size="16" />今日错误 {{ todayErrors }} 次<button class="link-btn" @click="logFilter.level = 'error'; loadLogs()">筛选</button></article>
          <article class="table-card"><table class="admin-table"><thead><tr><th>时间</th><th>主体</th><th>内容</th><th>来源</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="item in logs" :key="item.id"><td>{{ formatTime(item.created_at) }}</td><td>{{ logSubject(item) }}</td><td><code>{{ logContent(item) }}</code></td><td><span class="tag">{{ logMeta(item) }}</span></td><td><span class="tag" :class="item.detail?.resolved ? 'tag-success' : 'tag-warning'">{{ item.detail?.resolved ? '已处理' : '未处理' }}</span></td><td><button class="icon-action" @click="logDetail = item"><Eye :size="15" /></button><button v-if="logType === 'errors'" class="icon-action" @click="resolveError(item.id)"><CheckCircle :size="15" /></button></td></tr><tr v-if="!logs.length"><td colspan="6"><EmptyState text="暂无日志" /></td></tr></tbody></table></article>
        </section>

        <section v-if="active === 'adminBackups'" class="admin-page">
          <article class="backup-summary"><div><span>最后备份</span><strong>{{ backupSummary.last_backup ? relativeTime(backupSummary.last_backup.created_at) : '暂无' }}</strong><small>{{ backupSummary.last_backup?.status || '-' }}</small></div><div><span>备份文件</span><strong>{{ backupSummary.backup_count || 0 }}</strong><small>最旧：{{ shortDate(backupSummary.oldest_at) }}</small></div><div><span>总大小</span><strong>{{ backupSummary.total_size_label || '0 B' }}</strong><small>本地存储</small></div></article>
          <div class="backup-layout">
            <article class="panel-card"><div class="panel-head"><h2><File :size="18" />备份文件</h2><span class="tag">{{ backups.length }}</span></div><table class="admin-table compact-table"><thead><tr><th>名称</th><th>类型</th><th>大小</th><th>状态</th><th>时间</th><th>操作</th></tr></thead><tbody><tr v-for="item in backups" :key="item.id" :class="{ disabled: item.status === 'failed' }"><td class="mono">{{ item.backup_name }}</td><td><span class="tag">全量</span></td><td>{{ sizeLabel(item.file_size_bytes) }}</td><td><span class="tag" :class="statusClass(item.status)">{{ statusText(item.status) }}</span></td><td>{{ formatTime(item.created_at) }}</td><td class="row-actions"><button class="icon-action" @click="downloadBackup(item)"><Download :size="15" /></button><button class="icon-action" @click="verifyBackup(item.id)"><ShieldCheck :size="15" /></button><button class="icon-action danger" @click="deleteBackup(item.id)"><Trash2 :size="15" /></button></td></tr></tbody></table></article>
            <article class="panel-card"><div class="panel-head"><h2><Settings :size="18" />自动备份</h2></div><div class="policy-form"><label class="switch-line"><input v-model="backupPolicy.enabled" type="checkbox" />启用自动备份</label><label>备份频率<select v-model="backupPolicy.frequency" class="select"><option value="daily">每天</option><option value="6h">每6小时</option><option value="hourly">每小时</option></select></label><label>备份时间<input v-model="backupPolicy.time" class="input" type="time" /></label><label>保留数量<input v-model.number="backupPolicy.retention" class="input" type="number" /></label><label>通知邮箱<input v-model="backupNotifyEmail" class="input" type="email" /></label><button class="btn btn-primary wide-btn" @click="saveBackupPolicy">保存</button></div></article>
          </div>
          <article class="danger-zone"><AlertTriangle :size="18" /><div><strong>数据恢复</strong><span>恢复将覆盖当前数据。</span></div><select v-model.number="restoreBackupId" class="select"><option :value="0">选择备份</option><option v-for="item in backups" :key="item.id" :value="item.id">{{ item.backup_name }}</option></select><input v-model="restoreConfirm" class="input" placeholder="CONFIRM" /><button class="btn btn-danger" :disabled="restoreConfirm !== 'CONFIRM' || !restoreBackupId" @click="restoreBackupAction">恢复</button></article>
        </section>
      </section>
    </main>

    <aside v-if="userDrawer" class="drawer">
      <div class="drawer-head"><h2>{{ userDrawer.user.nickname }}</h2><span class="tag">{{ roleText(userDrawer.user.role) }}</span><button class="icon-action" @click="userDrawer = null"><X :size="16" /></button></div>
      <div class="drawer-body"><section><h3>基本信息</h3><InfoRow label="邮箱" :value="userDrawer.user.email" /><InfoRow label="状态" :value="statusText(userDrawer.user.status)" /><InfoRow label="注册" :value="formatTime(userDrawer.user.created_at)" /></section><section><h3>账号权限</h3><label class="drawer-field">用户角色<select class="select" :value="userDrawer.user.role" :disabled="isPending(`role:${userDrawer.user.id}`)" @change="selectUserRole(userDrawer.user, $event)"><option v-for="role in userRoleOptions" :key="role.value" :value="role.value">{{ role.label }}</option></select></label></section><section><h3>已加入课程</h3><div v-for="item in userDrawer.courses" :key="item.id" class="row-card"><span>{{ item.name }}</span><span class="tag">{{ item.role }}</span></div></section><section><h3>操作日志</h3><div v-for="item in userDrawer.logs" :key="item.id" class="timeline-item"><i></i><strong>{{ item.action }}</strong><span>{{ formatTime(item.created_at) }}</span></div></section></div>
      <div class="drawer-foot"><button class="btn btn-danger" :data-loading="isPending(`delete:${userDrawer.user.id}`)" :disabled="isPending(`delete:${userDrawer.user.id}`)" @click="deleteUser(userDrawer.user.id)">删除</button><button class="btn btn-secondary" :data-loading="isPending(`reset:${userDrawer.user.id}`)" :disabled="isPending(`reset:${userDrawer.user.id}`)" @click="resetUser(userDrawer.user.id)">重置密码</button></div>
    </aside>

    <aside v-if="courseDrawer" class="drawer wide">
      <div class="drawer-head"><h2>{{ courseDrawer.course.name }}</h2><span class="tag" :class="statusClass(courseDrawer.course.status)">{{ statusText(courseDrawer.course.status) }}</span><button class="icon-action" @click="courseDrawer = null"><X :size="16" /></button></div>
      <div class="drawer-body"><section><h3>基本信息</h3><InfoRow label="课程码" :value="courseDrawer.course.course_code" /><InfoRow label="教师" :value="String(courseDrawer.course.teacher_id)" /><InfoRow label="学生" :value="String(courseDrawer.student_count)" /><InfoRow label="资料" :value="String(courseDrawer.material_count)" /></section><section><h3>学生列表</h3><div v-for="item in courseDrawer.students" :key="item.membership_id" class="row-card"><span>{{ item.user.nickname }}</span><span class="tag">{{ item.user.email }}</span></div></section><section><h3>课程资料</h3><div v-for="item in courseDrawer.materials" :key="item.id" class="row-card"><span>{{ item.title }}</span><button class="link-btn" @click="deleteMaterial(item.id)">删除</button></div></section><section><h3>课堂列表</h3><div v-for="item in courseDrawer.lessons" :key="item.id" class="row-card"><span>{{ item.title }}</span><span class="tag">{{ item.status }}</span></div></section></div>
      <div class="drawer-foot"><input v-model.number="takeoverTeacherId" class="input" type="number" placeholder="教师ID" /><button class="btn btn-secondary" @click="takeoverCourse(courseDrawer.course.id)">接管</button><button class="btn btn-danger" @click="deactivateCourse(courseDrawer.course.id)">下架</button></div>
    </aside>

    <div v-if="adminModalOpen" class="modal-mask">
      <article class="modal">
        <div class="modal-head"><Shield :size="20" /><h2>创建管理员账号</h2><button class="icon-action" @click="adminModalOpen = false"><X :size="16" /></button></div>
        <p v-if="adminFormError" class="form-error"><AlertCircle :size="15" />{{ adminFormError }}</p>
        <div class="form-grid"><label>用户名<input v-model="adminForm.nickname" class="input" /></label><label>邮箱<input v-model="adminForm.email" class="input" type="email" /></label><label>初始密码<input v-model="adminForm.password" class="input" type="password" /></label><label>确认密码<input v-model="adminForm.confirm" class="input" type="password" /></label><label class="wide-field">备注<textarea v-model="adminForm.note" class="textarea"></textarea></label></div>
        <footer><button class="btn btn-secondary" @click="adminModalOpen = false">取消</button><button class="btn btn-primary" @click="createAdmin"><Plus :size="16" />创建</button></footer>
      </article>
    </div>

    <div v-if="resetPasswordResult" class="modal-mask">
      <article class="modal password-modal">
        <div class="modal-head"><KeyRound :size="20" /><h2>新密码</h2><button class="icon-action" @click="resetPasswordResult = ''"><X :size="16" /></button></div>
        <div class="password-box">{{ resetPasswordResult }}</div>
        <footer><button class="btn btn-secondary" @click="copyPassword">复制</button><button class="btn btn-primary" @click="resetPasswordResult = ''">关闭</button></footer>
      </article>
    </div>

    <div v-if="previewItem" class="modal-mask">
      <article class="modal preview-modal"><div class="modal-head"><FileText :size="20" /><h2>{{ previewItem.title }}</h2><button class="icon-action" @click="previewItem = null"><X :size="16" /></button></div><iframe v-if="previewItem.preview_url" :src="previewItem.preview_url"></iframe><EmptyState v-else text="暂无预览" /></article>
    </div>

    <div v-if="logDetail" class="modal-mask">
      <article class="modal"><div class="modal-head"><FileText :size="20" /><h2>日志详情</h2><button class="icon-action" @click="logDetail = null"><X :size="16" /></button></div><pre>{{ JSON.stringify(logDetail, null, 2) }}</pre><footer><button class="btn btn-secondary" @click="logDetail = null">关闭</button></footer></article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  Activity, AlertCircle, AlertTriangle, Ban, BarChart2, Bell, BookOpen, CheckCircle, CheckSquare, ChevronDown,
  ChevronRight, Clock, Cloud, Database, Download, Eye, File, FileCheck, FileText, GraduationCap, Grid2X2,
  Inbox, KeyRound, Layers, LayoutDashboard, List, LogOut, Menu, MoreHorizontal, Pencil, Plus, RefreshCw,
  Save, Scan, Search, Server, Settings, Shield, ShieldCheck, Sparkles, Trash2, Upload, User, UserCheck,
  Users, Volume2, X, XCircle
} from "lucide-vue-next";
import { api } from "../api/client";
import type { Role, User as UserType } from "../types";
import AdminChart from "./admin/AdminChart.vue";

const props = defineProps<{ user: UserType; pageKey?: string }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();
const router = useRouter();

type ServiceKey = "oss" | "ocr" | "tts" | "email";

const routeByKey: Record<string, string> = {
  profile: "/profile",
  adminDashboard: "/admin",
  adminUsers: "/admin/users",
  adminCourses: "/admin/courses",
  adminMaterials: "/admin/materials",
  adminModels: "/admin/models",
  adminServices: "/admin/services",
  adminSystem: "/admin/system",
  adminMonitor: "/admin/monitor",
  adminLogs: "/admin/logs",
  adminBackups: "/admin/backups"
};

const collapsed = ref(false);
const userMenuOpen = ref(false);
const sidebarNavRef = ref<HTMLElement | null>(null);
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
const courseFilter = reactive({ keyword: "", status: "" });
const materialFilter = reactive({ keyword: "", category: "", material_type: "", teacher_id: null as number | null });
const logFilter = reactive({ success: "", action: "", level: "", source: "", start_at: "", end_at: "" });
const adminForm = reactive({ email: "", nickname: "", password: "", confirm: "", note: "" });
const modelGlobal = reactive({ provider: "qwen", endpoint: "https://dashscope.aliyuncs.com/compatible-mode/v1", api_key: "" });
const modelDrafts = reactive<Record<string, any>>({});
const embeddingDraft = reactive({ config_id: null as number | null, provider: "qwen", model_name: "text-embedding-v2", endpoint: "", api_key: "", dimensions: 1536 });
const settingDrafts = reactive<Record<string, any>>({});
const originalSettings = ref<Record<string, any>>({});
const backupPolicy = reactive({ enabled: false, frequency: "daily", time: "03:00", retention: 30 });
const backupNotifyEmail = ref("");
const serviceDrafts = reactive<Record<ServiceKey, any>>({
  oss: { config_id: null, provider: "aliyun", name: "OSS", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "", bucket: "", url_expire_hours: 24 },
  ocr: { config_id: null, provider: "aliyun", name: "OCR", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "", timeout: 10, retries: 3, accuracy: "normal" },
  tts: { config_id: null, provider: "aliyun", name: "TTS", is_enabled: true, access_key_id: "", access_key_secret: "", appkey: "", token: "", url: "", voice: "xiaoyun", speech_rate: 0, volume: 50, sample_rate: 16000, format: "wav" },
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
  { key: "classroom", label: "课堂音频" },
  { key: "quiz", label: "测验参数" },
  { key: "interface", label: "界面公告" },
  { key: "backup", label: "备份参数" }
];
const settingRows = [
  { key: "upload.max_size_mb", category: "upload", label: "单文件大小", desc: "上传文件上限", type: "number" },
  { key: "upload.allowed_types", category: "upload", label: "文件格式", desc: "支持资料格式", type: "checks", options: ["ppt", "pptx", "pdf", "doc", "docx", "txt"] },
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
const activitySeries = computed(() => [{ name: "活跃用户", data: (dashboard.value.activity_trend || []).map((item: any) => item.active_users), color: "#4F46E5" }, { name: "AI 调用", data: (dashboard.value.activity_trend || []).map((item: any) => item.ai_calls), color: "#06B6D4" }]);
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
  return [{ name: "次数", data: items.map((item: any) => item.call_count || 0), color: "#8B5CF6" }];
});
const activeSettingRows = computed(() => settingRows.filter((item) => item.category === settingTab.value));
const changedSettings = computed(() => Object.keys(settingDrafts).filter((key) => JSON.stringify(settingDrafts[key]) !== JSON.stringify(originalSettings.value[key])));
const monitorLabels = computed(() => (monitorSeriesData.value.points || []).map((item: any) => item.time));
const onlineSeries = computed(() => [{ name: "在线", data: (monitorSeriesData.value.points || []).map((item: any) => item.online_users), color: "#4F46E5" }]);
const apiSeries = computed(() => [{ name: "API", data: (monitorSeriesData.value.points || []).map((item: any) => item.api_calls), color: "#06B6D4" }]);
const aiMonitorSeries = computed(() => [{ name: "AI", data: (monitorSeriesData.value.points || []).map((item: any) => item.ai_calls), color: "#8B5CF6" }, { name: "失败率", data: (monitorSeriesData.value.points || []).map((item: any) => item.ai_failure_rate), color: "#EF4444" }]);
const lastUpdatedText = computed(() => (lastUpdatedAt.value ? `${relativeTime(lastUpdatedAt.value.toISOString())}更新` : "未更新"));
const todayErrors = computed(() => logs.value.filter((item) => String(item.level).toLowerCase() === "error").length);

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
async function go(key: string) {
  await router.push(routeByKey[key] || "/admin");
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
  return { mysql: Database, redis: Server, vector: Layers, celery: Activity, oss: Cloud, tts: Volume2, ocr: Scan, email: FileText, llm: Sparkles }[key] || Server;
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
        if (innerProps.item.type === "range") return h("input", { class: "input form-control", type: "range", min: innerProps.item.min, max: innerProps.item.max, value: innerProps.drafts[key], onInput: (event: Event) => { innerProps.drafts[key] = Number((event.target as HTMLInputElement).value); } });
        if (innerProps.item.type === "toggle") return h("label", { class: "checkbox-label inline" }, [h("input", { type: "checkbox", checked: !!innerProps.drafts[key], onChange: (event: Event) => { innerProps.drafts[key] = (event.target as HTMLInputElement).checked; } }), "启用"]);
        if (innerProps.item.type === "textarea") return h("textarea", { class: "textarea form-control", value: innerProps.drafts[key], onInput: update });
        if (innerProps.item.type === "select") return h("select", { class: "select form-control", value: innerProps.drafts[key], onChange: update }, innerProps.item.options.map((option: string) => h("option", { value: option }, option)));
        if (innerProps.item.type === "checks") return h("div", { class: "checkbox-group" }, innerProps.item.options.map((option: string) => h("label", { class: "checkbox-label" }, [h("input", { type: "checkbox", checked: Array.isArray(innerProps.drafts[key]) && innerProps.drafts[key].includes(option), onChange: (event: Event) => {
          const current = Array.isArray(innerProps.drafts[key]) ? [...innerProps.drafts[key]] : [];
          innerProps.drafts[key] = (event.target as HTMLInputElement).checked ? [...new Set([...current, option])] : current.filter((value) => value !== option);
        } }), option])));
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
  if (adminForm.password.length < 8) return void (adminFormError.value = "密码至少8位");
  if (adminForm.password !== adminForm.confirm) return void (adminFormError.value = "两次密码不一致");
  try {
    await api.post("/admin/users/admin", { email: adminForm.email, nickname: adminForm.nickname, password: adminForm.password });
    emit("notice", "success", "已创建");
    adminModalOpen.value = false;
    Object.assign(adminForm, { email: "", nickname: "", password: "", confirm: "", note: "" });
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
function selectUserRole(item: any, event: Event) {
  void updateUserRole(item, (event.target as HTMLSelectElement).value as Role);
}
function copyPassword() {
  if (!resetPasswordResult.value) return;
  navigator.clipboard?.writeText(resetPasswordResult.value);
  emit("notice", "success", "已复制");
}
async function resetUser(id: number, password = generateTempPassword(), ask = true, silent = false) {
  if (ask && !window.confirm(`将用户密码重置为：${password}`)) return false;
  const updated = await withPending(`reset:${id}`, async () => run(() => api.post(`/admin/users/${id}/reset-password`, { new_password: password })));
  if (!updated) return false;
  resetPasswordResult.value = password;
  if (!silent) emit("notice", "success", `新密码：${password}`);
  return true;
}
async function deleteUser(id: number) { await withPending(`delete:${id}`, async () => { await run(() => api.delete(`/admin/users/${id}`), "已删除"); userDrawer.value = null; await loadUsers(); }); }
async function batchDisableUsers() { for (const id of selectedUsers.value) await run(() => api.patch(`/admin/users/${id}`, { status: "disabled" })); selectedUsers.value = []; await loadUsers(); }
async function batchResetUsers() {
  if (!selectedUsers.value.length) return;
  const password = generateTempPassword();
  if (!window.confirm(`将 ${selectedUsers.value.length} 个用户密码重置为：${password}`)) return;
  let successCount = 0;
  for (const id of selectedUsers.value) {
    if (await resetUser(id, password, false, true)) successCount += 1;
  }
  if (!successCount) return;
  resetPasswordResult.value = password;
  emit("notice", "success", `${successCount} 人新密码：${password}`);
  selectedUsers.value = [];
}
async function batchDeleteUsers() { for (const id of selectedUsers.value) await run(() => api.delete(`/admin/users/${id}`)); selectedUsers.value = []; await loadUsers(); }
function toggleAllUsers(event: Event) { selectedUsers.value = (event.target as HTMLInputElement).checked ? users.value.map((item) => item.id) : []; }
function clearUserFilter() { Object.assign(userFilter, { keyword: "", role: "", status: "" }); loadUsers(); }
async function openCourseDetail(id: number) { courseDrawer.value = await run(() => api.get(`/admin/courses/${id}`)); }
function openTakeover(item: any) { courseDrawer.value = { course: item, student_count: item.student_count, material_count: item.material_count, students: [], materials: [], lessons: [] }; }
async function takeoverCourse(id: number) { if (!takeoverTeacherId.value) return; await run(() => api.post(`/admin/courses/${id}/takeover`, { teacher_id: takeoverTeacherId.value }), "已接管"); await loadCourses(); }
async function deactivateCourse(id: number) { await run(() => api.post(`/admin/courses/${id}/deactivate`), "已下架"); await loadCourses(); }
async function batchDeactivateCourses() { for (const id of selectedCourses.value) await deactivateCourse(id); selectedCourses.value = []; }
function toggleAllCourses(event: Event) { selectedCourses.value = (event.target as HTMLInputElement).checked ? filteredCourses.value.map((item) => item.id) : []; }
function clearCourseFilter() { Object.assign(courseFilter, { keyword: "", status: "" }); courseTerm.value = ""; loadCourses(); }
function previewMaterial(item: any) { previewItem.value = item; }
async function deleteMaterial(id: number) { await run(() => api.delete(`/admin/materials/${id}`), "已删除"); await loadMaterials(); }
async function batchDeleteMaterials() { for (const id of selectedMaterials.value) await run(() => api.delete(`/admin/materials/${id}`)); selectedMaterials.value = []; await loadMaterials(); }
function toggleAllMaterials(event: Event) { selectedMaterials.value = (event.target as HTMLInputElement).checked ? materials.value.map((item) => item.id) : []; }
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
function serviceConfigPayload(type: ServiceKey) { const draft = serviceDrafts[type]; const { config_id, provider, name, is_enabled, ...config } = draft; return config; }
function serviceMissing(type: ServiceKey) {
  const draft = serviceDrafts[type];
  if (!draft.name || !draft.provider) return "服务必填";
  if (["mock", "local"].includes(draft.provider)) return "";
  const required: Record<ServiceKey, string[]> = { oss: ["access_key_id", "access_key_secret", "endpoint", "bucket"], ocr: ["access_key_id", "access_key_secret", "endpoint"], tts: ["appkey", "token", "url", "voice"], email: ["host", "port", "sender"] };
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
onMounted(async () => {
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
const ServiceConfigCard = defineComponent({
  props: { title: { type: String, required: true }, icon: { type: Object, required: true }, type: { type: String, required: true }, draft: { type: Object, required: true }, status: { type: String, required: true } },
  emits: ["save", "test", "remove"],
  setup(p, { slots, emit: update }) {
    return () => h("article", { class: "card service-config-card" }, [
      h("div", { class: "card-header" }, [
        h("div", { class: "card-title" }, [
          h(p.icon as any, { size: 20 }),
          p.title,
          h("span", { class: ["tag", statusClass(p.status)] }, statusText(p.status))
        ]),
        h("div", { class: "header-actions" }, [
          h("button", { class: "btn btn-secondary btn-sm", onClick: () => update("test") }, "测试"),
          h("button", { class: "btn btn-primary btn-sm", onClick: () => update("save") }, "保存"),
          h("button", { class: "btn btn-ghost btn-sm", onClick: () => update("remove") }, "删除")
        ])
      ]),
      h("div", { class: "card-body grid-2" }, slots.default?.())
    ]);
  }
});
</script>

<style scoped>
.admin-shell { min-width: 1280px; height: 100vh; overflow: hidden; background: var(--color-bg-page); color: var(--color-text-body); }
.admin-topbar { position: fixed; top: 0; left: 240px; right: 0; z-index: var(--z-sticky); height: 60px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--color-border-default); background: var(--color-bg-surface); padding: 0 24px; transition: left 250ms var(--ease-out); }
.collapsed .admin-topbar { left: 64px; }
.topbar-left { min-width: 1px; }
.top-actions, .user-trigger, .identity, .panel-head h2, .service-row, .mini-metrics, .monitor-top, .switch-line { display: flex; align-items: center; gap: var(--space-2); }
.logo-mark { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: var(--radius-md); color: white; background: var(--color-ai-gradient); }
.logo-text { min-width: 0; color: var(--color-text-primary); font-size: 16px; font-weight: 600; letter-spacing: .5px; white-space: nowrap; }
.health-pill { display: inline-flex; align-items: center; gap: 6px; min-height: 26px; padding: 0 10px; border-radius: var(--radius-full); font-size: var(--text-caption); }
.health-pill i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.health-pill.ok { background: var(--color-success-50); color: var(--color-success-700); }
.health-pill.warn { background: var(--color-danger-50); color: var(--color-danger-700); }
.notice-btn, .icon-action { position: relative; display: inline-flex; width: 32px; height: 32px; align-items: center; justify-content: center; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-secondary); }
.notice-btn:hover, .icon-action:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.text-action { display: inline-flex; align-items: center; justify-content: center; gap: 4px; min-height: 30px; border: 0; border-radius: var(--radius-md); background: var(--color-bg-muted); color: var(--color-text-secondary); padding: 0 8px; font-size: var(--text-caption); }
.text-action:hover { background: var(--color-primary-50); color: var(--color-primary-700); }
.text-action.danger { color: var(--color-danger-700); }
.text-action.danger:hover { background: var(--color-danger-50); color: var(--color-danger-700); }
.form-error { display: flex; align-items: center; gap: 6px; min-height: 34px; border: 1px solid var(--color-danger-100); border-radius: var(--radius-md); background: var(--color-danger-50); color: var(--color-danger-700); padding: 0 10px; font-size: var(--text-body-sm); }
.notice-btn em { position: absolute; top: 0; right: 0; min-width: 16px; height: 16px; border-radius: 8px; background: var(--color-danger-500); color: white; font-size: 10px; font-style: normal; line-height: 16px; text-align: center; }
.divider { width: 1px; height: 24px; background: var(--color-border-default); }
.avatar { display: inline-flex; width: 32px; height: 32px; align-items: center; justify-content: center; border-radius: var(--radius-full); background: var(--color-ai-gradient); color: white; font-weight: 700; }
.avatar.small { width: 30px; height: 30px; font-size: 13px; }
.avatar.mini { width: 24px; height: 24px; font-size: 12px; margin-right: 6px; }
.user-menu { position: relative; }
.user-trigger { border: 0; background: transparent; color: var(--color-text-body); }
.dropdown { position: absolute; right: 0; top: 40px; z-index: var(--z-dropdown); min-width: 150px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-lg); padding: 6px; }
.dropdown button { display: flex; width: 100%; align-items: center; gap: 8px; border: 0; border-radius: 8px; background: transparent; padding: 8px; color: var(--color-text-body); }
.dropdown button:hover { background: var(--color-bg-muted); }
.admin-sidebar { position: fixed; top: 0; bottom: 0; left: 0; z-index: calc(var(--z-sticky) + 1); width: 240px; border-right: 1px solid var(--color-border-default); background: var(--color-bg-surface); transition: width 250ms var(--ease-out); display: flex; flex-direction: column; }
.collapsed .admin-sidebar { width: 64px; }
.sidebar-header { height: 60px; display: flex; align-items: center; gap: 12px; flex-shrink: 0; padding: 0 20px; }
.collapsed .sidebar-header { justify-content: center; padding: 0; }
.menu-btn { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-muted); transition: background 200ms var(--ease-out), color 200ms var(--ease-out); }
.menu-btn:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.collapsed .menu-btn { display: none; }
.sidebar-nav { flex: 1 1 auto; min-height: 0; overflow: visible; overscroll-behavior: contain; padding: 16px 12px; }
.sidebar-scrollable .sidebar-nav { overflow-y: auto; overflow-x: hidden; }
.nav-group { margin-bottom: 24px; padding: 0; border-bottom: 0; }
.nav-title { display: block; padding: 0 12px 8px; color: var(--color-text-muted); font-size: 11px; font-weight: 600; letter-spacing: .5px; text-transform: uppercase; }
.nav-link { position: relative; display: flex; width: 100%; height: 40px; align-items: center; gap: 12px; border: 0; border-radius: var(--radius-md); background: transparent; color: var(--color-text-muted); padding: 0 12px; text-align: left; font-size: 14px; transition: all 200ms var(--ease-out); margin-bottom: 4px; }
.nav-link.active { background: var(--color-primary-50); color: var(--color-primary-700); }
.nav-link.active svg { color: var(--color-primary-600); }
.nav-link.active::before { display: none; }
.nav-link:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.nav-link em { position: absolute; left: 44px; z-index: var(--z-tooltip); visibility: hidden; opacity: 0; pointer-events: none; white-space: nowrap; border-radius: 6px; background: var(--color-text-primary); color: white; padding: 4px 8px; font-style: normal; font-size: var(--text-caption); box-shadow: var(--shadow-lg); transform: translateX(-4px) scale(.96); transform-origin: left center; transition: opacity 180ms var(--ease-out), transform 180ms var(--ease-out), visibility 180ms; }
.collapsed .nav-link { justify-content: center; padding: 0; }
.collapsed .nav-link:hover em { visibility: visible; opacity: 1; transform: translateX(0) scale(1); }
.sidebar-footer { flex-shrink: 0; border-top: 1px solid var(--color-border-default); padding: 16px 12px; }
.side-user { display: flex; align-items: center; gap: 12px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: var(--color-bg-page); padding: 12px; }
.collapsed .side-user { justify-content: center; padding: 8px; }
.side-user div { display: grid; gap: 4px; }
.side-user strong { color: var(--color-text-primary); }
.admin-main { height: 100vh; margin-left: 240px; padding-top: 60px; overflow-y: auto; transition: margin-left 250ms var(--ease-out); }
.collapsed .admin-main { margin-left: 64px; }
.breadcrumb { height: 64px; display: flex; align-items: center; justify-content: space-between; background: transparent; padding: 0 32px; }
.breadcrumb > div { display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary); }
.breadcrumb strong { color: var(--color-text-primary); }
.page-actions { display: flex; align-items: center; gap: var(--space-2); }
.admin-content { padding: 0 32px 48px; }
.admin-page { display: grid; gap: 24px; animation: fade-slide-up var(--duration-base) var(--ease-out); }
.page-view { align-content: start; }
.page-header { min-height: 64px; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.page-header .breadcrumb { height: auto; display: flex; align-items: center; justify-content: flex-start; gap: 6px; background: transparent; color: var(--color-text-secondary); padding: 0; }
.page-header .breadcrumb span:last-child { color: var(--color-text-primary); font-weight: 600; }
.welcome-card, .panel-card, .filter-card, .table-card, .backup-summary, .danger-zone, .service-config-card { background: var(--color-bg-surface); border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
.welcome-card { min-height: 96px; display: flex; align-items: center; gap: 20px; padding: 24px 32px; }
.welcome-card h1 { margin: 0; color: var(--color-text-primary); font-size: 20px; font-weight: 600; }
.welcome-card p { margin: 6px 0 0; color: var(--color-text-muted); font-size: 13px; }
.welcome-icon, .metric-icon { display: inline-flex; width: 42px; height: 42px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--color-primary-50); color: var(--color-primary-600); }
.welcome-icon { width: 48px; height: 48px; border-radius: var(--radius-lg); color: white; background: var(--color-ai-gradient); box-shadow: 0 4px 12px rgba(99, 102, 241, .2); }
.metric-grid { display: grid; gap: 20px; }
.metric-grid.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.metric-grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.metric-grid.compact .metric-card strong { font-size: 24px; }
.metric-card { position: relative; min-height: 132px; display: flex; flex-direction: column; justify-content: space-between; padding: 20px; overflow: hidden; background: white; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); transition: transform 200ms var(--ease-out), box-shadow 200ms var(--ease-out); }
.metric-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.metric-card > div { display: flex; align-items: center; gap: 12px; color: var(--color-text-muted); }
.metric-card strong { display: block; margin-top: 14px; color: var(--color-text-primary); font-size: 28px; font-weight: 700; line-height: 1; }
.metric-card small { display: inline-flex; align-items: center; gap: 6px; color: var(--color-text-muted); font-size: 12px; margin-top: 8px; }
.metric-card.success .metric-icon { background: var(--color-success-50); color: var(--color-success-700); }
.metric-card.info .metric-icon { background: var(--color-info-50); color: var(--color-info-700); }
.metric-card.ai .metric-icon { background: var(--color-ai-light); color: #6D28D9; }
.metric-card.danger { border-color: #FECACA; background: var(--color-danger-50); }
.metric-card.danger .metric-icon { background: white; color: var(--color-danger-500); }
.metric-card.danger strong, .metric-card.danger small { color: var(--color-danger-700); }
.metric-card.danger::after { display: none; }
.trend-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.content-row { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
.left-col, .right-col, .service-config-stack { display: grid; gap: 16px; }
.panel-card, .service-config-card { padding: 20px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.panel-head h2 { margin: 0; color: var(--color-text-primary); font-size: var(--text-h4); }
.panel-head span { color: var(--color-text-muted); font-size: var(--text-caption); }
.panel-head strong { color: var(--color-primary-700); font-size: var(--text-h3); }
.segmented-control { display: flex; background: var(--color-bg-muted); border-radius: var(--radius-md); padding: 4px; }
.segment-btn { min-height: 30px; border: 0; border-radius: 6px; background: transparent; color: var(--color-text-muted); padding: 6px 16px; font-size: 13px; font-weight: 500; transition: all 200ms var(--ease-out); }
.segment-btn.active { background: white; color: var(--color-text-primary); box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.view-toggle { display: inline-flex; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); overflow: hidden; }
.view-toggle button { min-height: 30px; border: 0; background: white; color: var(--color-text-secondary); padding: 0 10px; }
.view-toggle button.active { background: var(--color-primary-600); color: white; }
.service-list { display: grid; }
.service-row { min-height: 48px; display: grid; grid-template-columns: auto 1fr auto 58px; border-bottom: 1px solid var(--color-border-subtle); }
.service-row span:nth-child(2) { color: var(--color-text-body); }
.service-row small { color: var(--color-text-muted); text-align: right; }
.timeline, .settings-list { display: grid; gap: 12px; }
.timeline-item { position: relative; display: grid; grid-template-columns: 12px 1fr; gap: 4px 10px; }
.timeline-item i { grid-row: 1 / 3; width: 9px; height: 9px; margin-top: 6px; border-radius: 50%; background: var(--color-primary-600); }
.timeline-item i.warning { background: var(--color-warning-500); }
.timeline-item i.danger { background: var(--color-danger-500); }
.timeline-item strong { color: var(--color-text-primary); font-size: var(--text-body-sm); }
.timeline-item span { color: var(--color-text-muted); font-size: var(--text-caption); }
.rank-row, .mini-user, .task-row, .row-card, .info-row { display: flex; align-items: center; gap: 10px; min-height: 38px; }
.rank-row b { width: 24px; text-align: center; }
.rank-1 { color: #B45309; }.rank-2 { color: #64748B; }.rank-3 { color: #92400E; }
.rank-row progress { flex: 1; height: 7px; accent-color: var(--color-primary-600); }
.mini-user div { display: grid; flex: 1; }
.mini-user strong { color: var(--color-text-primary); }
.mini-user span { color: var(--color-text-muted); font-size: var(--text-caption); }
.task-row svg { color: var(--color-warning-500); }
.link-btn { border: 0; background: transparent; color: var(--color-primary-700); font-weight: 500; }
.filter-card { min-height: 56px; display: flex; align-items: center; gap: 10px; padding: 10px 14px; }
.search-field { display: flex; align-items: center; gap: 8px; width: 280px; height: 36px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: white; padding: 0 10px; }
.search-field input { width: 100%; border: 0; outline: 0; color: var(--color-text-body); }
.filter-card .select { max-width: 130px; }
.filter-card .input { max-width: 170px; }
.filter-card .narrow { max-width: 96px; }
.spacer { flex: 1; }
.table-card { overflow: hidden; }
.admin-table { width: 100%; border-collapse: collapse; font-size: var(--text-body-sm); }
.admin-table th, .admin-table td { border-bottom: 1px solid var(--color-border-subtle); padding: 12px 14px; text-align: left; vertical-align: middle; }
.admin-table th { height: 44px; background: var(--color-bg-muted); color: var(--color-text-secondary); font-weight: 600; }
.admin-table tr.disabled { background: var(--color-danger-50); color: var(--color-text-muted); }
.admin-table tr.selected { background: var(--color-primary-50); }
.admin-table td svg { display: inline-block; vertical-align: middle; }
.check-col { width: 42px; }
.identity div { display: grid; }
.identity strong { color: var(--color-text-primary); }
.identity span { color: var(--color-text-muted); font-size: var(--text-caption); }
.role-select { width: 96px; min-width: 96px; }
.row-actions { display: flex; gap: 4px; white-space: nowrap; }
.icon-action.danger { color: var(--color-danger-700); }
.stale { color: var(--color-danger-700); }
.bulk-bar { display: flex; align-items: center; gap: 12px; min-height: 48px; background: var(--color-primary-600); color: white; padding: 0 14px; }
.bulk-bar button { border: 0; background: transparent; color: white; font-weight: 600; }
.course-card-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.course-admin-card { position: relative; min-height: 148px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 16px; }
.course-admin-card.inactive { opacity: 0.65; }
.course-admin-card > button { position: absolute; top: 12px; right: 12px; }
.course-admin-card strong { display: block; color: var(--color-text-primary); margin-bottom: 8px; }
.course-admin-card p { color: var(--color-text-secondary); }
.mini-metrics span { display: inline-flex; align-items: center; gap: 5px; color: var(--color-text-secondary); }
.file-pptx, .file-ppt { color: #F97316; }.file-pdf { color: var(--color-danger-500); }.file-docx, .file-doc { color: var(--color-info-500); }
.model-layout { display: flex; align-items: flex-start; gap: 32px; }
.vertical-tabs { position: sticky; top: 0; width: 180px; flex-shrink: 0; display: grid; gap: 2px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 8px; }
.vertical-tabs button { min-height: 38px; border: 0; border-radius: var(--radius-sm); background: transparent; text-align: left; padding: 0 16px; color: var(--color-text-secondary); transition: background 200ms var(--ease-out), color 200ms var(--ease-out), transform 200ms var(--ease-out); }
.vertical-tabs button:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.vertical-tabs button.active { background: var(--color-primary-50); color: var(--color-primary-700); font-weight: 600; }
.model-content { flex: 1; max-width: 900px; display: grid; gap: 24px; min-width: 0; }
.config-layout { display: flex; align-items: flex-start; gap: 32px; }
.config-nav { position: sticky; top: 0; width: 180px; flex-shrink: 0; display: grid; gap: 2px; border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); background: var(--color-bg-surface); box-shadow: var(--shadow-sm); padding: 8px; }
.config-nav-item { min-height: 38px; border: 0; border-radius: var(--radius-sm); background: transparent; text-align: left; padding: 0 16px; color: var(--color-text-secondary); transition: background 200ms var(--ease-out), color 200ms var(--ease-out); }
.config-nav-item:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.config-nav-item.active { background: var(--color-primary-50); color: var(--color-primary-700); font-weight: 600; }
.config-content { flex: 1; max-width: 900px; min-width: 0; display: grid; gap: 24px; }
.config-card { background: var(--color-bg-surface); border: 1px solid var(--color-border-default); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); overflow: hidden; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--color-border-default); padding: 16px 24px; }
.card-title { display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); font-size: 16px; font-weight: 600; line-height: 24px; }
.card-title svg { color: var(--color-primary-600); }
.card-title .tag { margin-left: 12px; font-weight: 500; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.card-body { padding: 24px; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.form-group { display: grid; gap: 6px; margin: 0; }
.form-label { color: var(--color-text-body); font-size: 13px; font-weight: 500; }
.form-control { width: 100%; height: 36px; border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm); background: var(--color-bg-surface); color: var(--color-text-primary); padding: 0 12px; }
.form-control:focus { outline: none; border-color: var(--color-primary-600); box-shadow: var(--shadow-focus); }
textarea.form-control { height: auto; min-height: 88px; padding: 12px; resize: vertical; }
.form-control[type="range"] { border: 0; background: transparent; box-shadow: none; padding: 0; }
.alert { display: flex; align-items: center; gap: 10px; border-radius: var(--radius-md); padding: 12px 14px; }
.alert-danger { background: var(--color-danger-50); color: var(--color-danger-700); }
.alert-info { background: var(--color-info-50); color: var(--color-info-700); }
.form-panel { max-width: 900px; padding: 0; overflow: hidden; }
.form-panel > .panel-head { border-bottom: 1px solid var(--color-border-default); margin: 0; padding: 16px 24px; }
.form-panel > .form-grid { padding: 24px; }
.form-section { border-top: 1px dashed var(--color-border-default); padding: 24px; margin: 0; }
.form-panel > .panel-head + .form-section { border-top: 0; }
.form-section h3 { margin: 0 0 16px; color: var(--color-text-primary); font-size: var(--text-body); }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.form-grid label, .policy-form label { display: grid; gap: 6px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.wide-field { grid-column: 1 / -1; }
.purpose-config-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.purpose-card { display: grid; gap: 10px; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); padding: 14px; }
.purpose-card div { display: flex; align-items: center; gap: 8px; color: var(--color-text-primary); }
.card-tools { display: flex; align-items: center; gap: 8px; }
.service-config-stack { max-width: 900px; }
.service-config-card { padding: 0; overflow: hidden; }
.service-config-card .btn-sm { min-height: 32px; }
.settings-list { padding: 12px 32px; }
.setting-row { display: grid; grid-template-columns: 200px minmax(260px, 1fr) 140px; align-items: center; gap: 16px; border-bottom: 1px dashed var(--color-border-default); padding: 20px 0; }
.setting-row > div { display: grid; gap: 4px; }
.setting-row strong { color: var(--color-text-primary); }
.setting-row span, .setting-row small { color: var(--color-text-muted); font-size: var(--text-caption); }
.settings-card { padding: 0; overflow: hidden; }
.settings-card .card-body { padding: 12px 32px; }
.param-row { display: grid; grid-template-columns: 200px minmax(260px, 1fr) 140px; align-items: center; gap: 16px; border-bottom: 1px dashed var(--color-border-default); padding: 20px 0; }
.param-row:last-child { border-bottom: 0; }
.param-info { display: grid; gap: 4px; }
.param-title { color: var(--color-text-primary); font-weight: 600; }
.param-desc, .param-current { color: var(--color-text-muted); font-size: var(--text-caption); }
.param-control { min-width: 0; }
.param-current { line-height: 18px; word-break: break-all; }
.checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; }
.checkbox-label { display: inline-flex; align-items: center; gap: 6px; color: var(--color-text-body); font-size: var(--text-body-sm); line-height: 20px; }
.checkbox-label.inline { min-height: 36px; }
.check-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.monitor-top { justify-content: flex-end; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.spin { animation: spin 1s linear infinite; }
.service-overview { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.monitor-service { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; min-height: 72px; border-left: 4px solid var(--color-primary-600); border-radius: var(--radius-lg); background: white; box-shadow: var(--shadow-sm); padding: 12px; }
.monitor-service.tag-danger { border-left-color: var(--color-danger-500); background: var(--color-danger-50); }
.monitor-service.tag-warning { border-left-color: var(--color-warning-500); background: var(--color-warning-50); }
.monitor-service div { display: grid; }
.monitor-service strong { color: var(--color-text-primary); }
.monitor-service span { color: var(--color-text-muted); font-size: var(--text-caption); }
.monitor-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.monitor-bottom, .backup-layout { display: grid; grid-template-columns: 55fr 45fr; gap: 16px; }
.log-tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--color-border-default); }
.log-tabs button { display: inline-flex; align-items: center; gap: 8px; min-height: 42px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-text-secondary); }
.log-tabs button.active { border-bottom-color: var(--color-primary-600); color: var(--color-primary-700); font-weight: 600; }
code, pre, .mono { font-family: var(--font-family-mono); }
pre { max-height: 420px; overflow: auto; border-radius: var(--radius-md); background: #0F172A; color: #E2E8F0; padding: 14px; font-size: 13px; }
.backup-summary { display: grid; grid-template-columns: repeat(3, 1fr); padding: 18px; }
.backup-summary div { display: grid; gap: 4px; border-right: 1px solid var(--color-border-subtle); padding: 0 18px; }
.backup-summary div:last-child { border-right: 0; }
.backup-summary span, .backup-summary small { color: var(--color-text-muted); font-size: var(--text-caption); }
.backup-summary strong { color: var(--color-text-primary); font-size: var(--text-h2); }
.compact-table th, .compact-table td { padding: 10px; }
.policy-form { display: grid; gap: 12px; }
.wide-btn { width: 100%; }
.danger-zone { display: grid; grid-template-columns: auto 1fr 220px 180px auto; align-items: center; gap: 14px; border-left: 4px solid var(--color-danger-500); background: var(--color-danger-50); padding: 16px; }
.danger-zone strong { display: block; color: var(--color-danger-700); }
.danger-zone span { color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.drawer { position: fixed; top: 60px; right: 0; bottom: 0; z-index: var(--z-fixed); width: 480px; display: grid; grid-template-rows: auto 1fr auto; border-left: 1px solid var(--color-border-default); background: white; box-shadow: var(--shadow-xl); }
.drawer.wide { width: 560px; }
.drawer-head, .drawer-foot { display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--color-border-default); padding: 16px; }
.drawer-head h2 { flex: 1; margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.drawer-body { overflow: auto; display: grid; align-content: start; gap: 18px; padding: 18px; }
.drawer-body h3 { margin: 0 0 10px; color: var(--color-text-primary); font-size: var(--text-h4); }
.drawer-field { display: grid; gap: 8px; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.drawer-foot { border-top: 1px solid var(--color-border-default); border-bottom: 0; justify-content: flex-end; }
.row-card, .info-row { justify-content: space-between; border-bottom: 1px solid var(--color-border-subtle); padding: 8px 0; }
.info-row span { color: var(--color-text-muted); }
.info-row strong { color: var(--color-text-primary); }
.modal-mask { position: fixed; inset: 0; z-index: var(--z-modal-bg); display: grid; place-items: center; background: rgba(15,23,42,0.35); backdrop-filter: blur(6px); }
.modal { width: 640px; max-height: 90vh; overflow: auto; border-radius: var(--radius-xl); background: white; box-shadow: var(--shadow-xl); padding: 20px; }
.modal.password-modal { width: 420px; }
.modal.preview-modal { width: 800px; height: 90vh; display: grid; grid-template-rows: auto 1fr; }
.preview-modal iframe { width: 100%; height: 100%; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); }
.modal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.modal-head h2 { flex: 1; margin: 0; color: var(--color-text-primary); font-size: var(--text-h3); }
.modal footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.password-box { min-height: 46px; display: flex; align-items: center; border: 1px solid var(--color-border-default); border-radius: var(--radius-md); background: var(--color-bg-muted); color: var(--color-text-primary); font-family: var(--font-family-mono); font-size: 18px; padding: 0 14px; user-select: all; }
.empty { min-height: 90px; display: grid; place-items: center; gap: 8px; color: var(--color-text-muted); }
@media (max-width: 1279px) { .admin-shell { min-width: 1280px; } }
</style>
