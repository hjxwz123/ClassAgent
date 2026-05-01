<template>
  <section v-if="active === 'adminUsers'" class="page">
    <div class="toolbar">
      <input v-model="userFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="userFilter.role" class="select short">
        <option value="">角色</option><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option>
      </select>
      <select v-model="userFilter.status" class="select short">
        <option value="">状态</option><option value="active">启用</option><option value="disabled">禁用</option>
      </select>
      <button class="btn btn-secondary" @click="loadUsers"><Search :size="16" />搜索</button>
    </div>
    <article class="card admin-form">
      <div class="form-row">
        <input v-model="adminForm.email" class="input" placeholder="邮箱" />
        <input v-model="adminForm.nickname" class="input" placeholder="昵称" />
        <input v-model="adminForm.password" class="input" type="password" placeholder="密码" />
        <button class="btn btn-primary" @click="createAdmin"><Plus :size="16" />创建</button>
      </div>
    </article>
    <DataTable :headers="['用户','角色','状态','操作']">
      <tr v-for="item in users" :key="item.id">
        <td><strong>{{ item.nickname }}</strong><br><small>{{ item.email }}</small></td>
        <td><span class="tag">{{ labelOf(roleLabels, item.role) }}</span></td>
        <td><span class="tag" :class="statusClass(item.status)">{{ labelOf(statusLabels, item.status) }}</span></td>
        <td class="ops">
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'student')">设学生</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'teacher')">设教师</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'admin')">设管理</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, 'active', item.role)">启用</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, 'disabled', item.role)">禁用</button>
          <button class="btn btn-ghost btn-xs" @click="resetUser(item.id)">重置</button>
          <button class="btn btn-ghost btn-xs" @click="deleteUser(item.id)">删除</button>
        </td>
      </tr>
      <tr v-if="!users.length"><td colspan="4" class="muted">暂无</td></tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminCourses'" class="page">
    <div class="toolbar">
      <input v-model="courseFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="courseFilter.status" class="select short">
        <option value="">状态</option><option value="active">启用</option><option value="inactive">停用</option>
      </select>
      <button class="btn btn-secondary" @click="loadCourses"><Search :size="16" />搜索</button>
    </div>
    <DataTable :headers="['课程','教师','状态','接管','操作']">
      <tr v-for="item in adminCourses" :key="item.id">
        <td><strong>{{ item.name }}</strong><br><small>{{ item.course_code }}</small></td>
        <td>{{ item.teacher_id }}</td>
        <td><span class="tag" :class="statusClass(item.status)">{{ labelOf(statusLabels, item.status) }}</span></td>
        <td><input v-model.number="takeoverTeacher" class="input mini" type="number" placeholder="ID" /></td>
        <td class="ops">
          <button class="btn btn-ghost btn-xs" @click="loadCourseDetail(item.id)"><Eye :size="14" />详情</button>
          <button class="btn btn-ghost btn-xs" @click="takeover(item.id)">接管</button>
          <button class="btn btn-ghost btn-xs" @click="deactivate(item.id)">停用</button>
        </td>
      </tr>
      <tr v-if="!adminCourses.length"><td colspan="5" class="muted">暂无</td></tr>
    </DataTable>
    <article v-if="adminCourseDetail" class="card detail-card">
      <div class="card-head">
        <h2 class="card-title">{{ adminCourseDetail.course?.name || '课程详情' }}</h2>
        <span class="tag" :class="statusClass(adminCourseDetail.course?.status)">{{ labelOf(statusLabels, adminCourseDetail.course?.status) }}</span>
      </div>
      <div class="detail-grid">
        <div><span>课程码</span><strong>{{ adminCourseDetail.course?.course_code }}</strong></div>
        <div><span>学期</span><strong>{{ adminCourseDetail.course?.term }}</strong></div>
        <div><span>教师</span><strong>{{ adminCourseDetail.course?.teacher_id }}</strong></div>
        <div><span>资料</span><strong>{{ adminCourseDetail.material_count || 0 }}</strong></div>
        <div><span>学生</span><strong>{{ adminCourseDetail.student_count || 0 }}</strong></div>
        <div><span>课程ID</span><strong>{{ adminCourseDetail.course?.id }}</strong></div>
      </div>
      <p v-if="adminCourseDetail.course?.description" class="card-desc">{{ adminCourseDetail.course.description }}</p>
    </article>
  </section>

  <section v-if="active === 'adminMaterials'" class="page">
    <div class="grid stats">
      <StatCard :icon="Upload" label="资料" :value="materialStats.total || 0" />
      <StatCard :icon="CheckCircle" label="就绪" :value="materialStats.ready || 0" />
      <StatCard :icon="XCircle" label="失败" :value="materialStats.failed || 0" danger />
    </div>
    <div class="breakdown-grid">
      <article class="card"><h2 class="card-title">类型</h2><div v-for="item in statEntries(materialStats.by_type, materialTypeLabels)" :key="item.key" class="row"><span>{{ item.label }}</span><span class="tag">{{ item.value }}</span></div></article>
      <article class="card"><h2 class="card-title">分类</h2><div v-for="item in statEntries(materialStats.by_category, categoryLabels)" :key="item.key" class="row"><span>{{ item.label }}</span><span class="tag">{{ item.value }}</span></div></article>
      <article class="card"><h2 class="card-title">教师</h2><div v-for="item in statEntries(materialStats.by_teacher)" :key="item.key" class="row"><span>{{ item.label }}</span><span class="tag">{{ item.value }}</span></div></article>
      <article class="card"><h2 class="card-title">时间</h2><div v-for="item in statEntries(materialStats.by_day).slice(0, 6)" :key="item.key" class="row"><span>{{ item.label }}</span><span class="tag">{{ item.value }}</span></div></article>
    </div>
    <div class="toolbar">
      <input v-model="materialFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="materialFilter.category" class="select short"><option value="">分类</option><option value="courseware">课件</option><option value="handout">讲义</option><option value="exercise">练习</option><option value="reference">参考</option></select>
      <select v-model="materialFilter.material_type" class="select short"><option value="">类型</option><option value="pptx">PPT</option><option value="pdf">PDF</option><option value="docx">Word</option><option value="txt">TXT</option></select>
      <input v-model.number="materialFilter.teacher_id" class="input tiny" type="number" placeholder="教师" />
      <input v-model="materialFilter.start_at" class="input date" type="datetime-local" />
      <input v-model="materialFilter.end_at" class="input date" type="datetime-local" />
      <button class="btn btn-secondary" @click="loadMaterials"><Search :size="16" />搜索</button>
    </div>
    <DataTable :headers="['资料','分类','解析','向量','教师','时间','操作']">
      <tr v-for="item in adminMaterials" :key="item.id">
        <td><strong>{{ item.title }}</strong><br><small>{{ item.original_filename }}</small></td>
        <td>{{ labelOf(categoryLabels, item.category) }} · {{ labelOf(materialTypeLabels, item.material_type) }}</td>
        <td><span class="tag" :class="statusClass(item.parse_status)">{{ labelOf(statusLabels, item.parse_status) }}</span></td>
        <td><span class="tag" :class="statusClass(item.vector_status)">{{ labelOf(statusLabels, item.vector_status) }}</span></td>
        <td>{{ item.uploader_id }}</td>
        <td>{{ formatTime(item.created_at) }}</td>
        <td><button class="btn btn-ghost btn-xs" @click="deleteMaterial(item.id)"><Trash2 :size="14" />删除</button></td>
      </tr>
      <tr v-if="!adminMaterials.length"><td colspan="7" class="muted">暂无</td></tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminModels'" class="page split">
    <section class="card">
      <div class="card-head">
        <h2 class="card-title">模型配置</h2>
        <div class="ops"><button class="btn btn-ghost btn-sm" @click="resetModelForm">新建</button><button class="btn btn-primary" @click="saveModel"><Save :size="16" />保存</button></div>
      </div>
      <div class="model-purpose-grid">
        <button
          v-for="item in purposeEntries"
          :key="item.key"
          class="config-tile"
          :class="{ active: modelForm.purpose === item.key }"
          @click="configureModelPurpose(item.key)"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ item.desc }}</span>
          <em>{{ configuredModels(item.key).length || 0 }}</em>
        </button>
      </div>
      <div class="form-row">
        <select v-model="modelForm.provider" class="select">
          <option value="openai">OpenAI</option>
          <option value="qwen">通义千问</option>
          <option value="deepseek">DeepSeek</option>
          <option value="mock">Mock</option>
        </select>
        <input v-model="modelForm.model_name" class="input" placeholder="模型" />
      </div>
      <div class="form-row">
        <select v-model="modelForm.purpose" class="select">
          <option value="general">通用</option><option value="qa">问答</option><option value="embedding">向量</option><option value="script">讲稿</option><option value="quiz">测验</option><option value="tutoring">辅导</option><option value="analysis">分析</option><option value="study_plan">计划</option>
        </select>
        <input v-model="modelForm.endpoint" class="input" placeholder="Endpoint" />
      </div>
      <input v-model="modelForm.api_key" class="input" type="password" placeholder="API Key" />
      <label class="check"><input v-model="modelForm.is_default" type="checkbox" />默认</label>
      <textarea v-model="modelExtra" class="textarea" placeholder="配置 JSON"></textarea>
      <div class="hint-grid">
        <div><strong>{{ labelOf(purposeLabels, modelForm.purpose) }}</strong><span>{{ purposeDescriptions[modelForm.purpose] }}</span></div>
        <div><strong>默认</strong><span>该用途优先调用</span></div>
      </div>
      <DataTable :headers="['模型','用途','说明','默认','密钥','操作']">
        <tr v-for="item in models" :key="item.id">
          <td><strong>{{ item.provider }}</strong><br><small>{{ item.model_name }}</small></td>
          <td>{{ labelOf(purposeLabels, item.purpose) }}</td>
          <td>{{ purposeDescriptions[item.purpose] || '-' }}</td>
          <td><span class="tag" :class="item.is_default ? 'tag-success' : ''">{{ boolLabel(item.is_default) }}</span></td>
          <td>{{ item.api_key || '-' }}</td>
          <td class="ops"><button class="btn btn-ghost btn-xs" @click="pickModel(item)">编辑</button><button class="btn btn-ghost btn-xs" @click="testModel(item.id)">测试</button><button class="btn btn-ghost btn-xs" @click="deleteModel(item.id)">删除</button></td>
        </tr>
        <tr v-if="!models.length"><td colspan="6" class="muted">暂无</td></tr>
      </DataTable>
    </section>
    <aside class="card">
      <div class="card-head"><h2 class="card-title">用途</h2></div>
      <div v-for="item in purposeEntries" :key="item.key" class="desc-row">
        <strong>{{ item.label }}</strong><span>{{ item.desc }}</span>
      </div>
      <div class="card-head"><h2 class="card-title">用量</h2><button class="btn btn-ghost btn-sm" @click="loadUsage"><RefreshCw :size="14" />刷新</button></div>
      <div v-for="item in usage.items || []" :key="item.provider" class="usage-row">
        <strong>{{ item.provider }}</strong>
        <span>{{ item.call_count }} 次</span>
        <span>{{ item.prompt_tokens }} / {{ item.completion_tokens }}</span>
        <span class="tag">$ {{ Number(item.estimated_cost || 0).toFixed(4) }}</span>
      </div>
      <div v-if="!(usage.items || []).length" class="muted">暂无</div>
    </aside>
  </section>

  <section v-if="active === 'adminServices'" class="page">
    <div class="service-config-grid">
      <article class="card service-card">
        <div class="card-head"><h2 class="card-title">OSS</h2><span class="tag" :class="statusClass(serviceDrafts.oss.config_id ? 'active' : 'not_configured')">{{ serviceDrafts.oss.config_id ? '已配置' : '未配置' }}</span></div>
        <p class="card-desc">{{ serviceDescriptions.oss }}</p>
        <div class="form-row">
          <select v-model="serviceDrafts.oss.provider" class="select"><option value="aliyun">阿里云</option><option value="local">本地</option><option value="mock">Mock</option></select>
          <input v-model="serviceDrafts.oss.name" class="input" placeholder="名称" />
        </div>
        <div v-if="serviceDrafts.oss.provider === 'aliyun'" class="config-fields">
          <input v-model="serviceDrafts.oss.access_key_id" class="input" placeholder="AccessKey ID" />
          <input v-model="serviceDrafts.oss.access_key_secret" class="input" type="password" placeholder="AccessKey Secret" />
          <input v-model="serviceDrafts.oss.endpoint" class="input" placeholder="Endpoint" />
          <input v-model="serviceDrafts.oss.region" class="input" placeholder="Region" />
          <input v-model="serviceDrafts.oss.bucket" class="input" placeholder="Bucket" />
        </div>
        <label class="check"><input v-model="serviceDrafts.oss.is_enabled" type="checkbox" />启用</label>
        <div class="card-actions">
          <button class="btn btn-primary" @click="saveServiceType('oss')">保存</button>
          <button class="btn btn-secondary" @click="testServiceType('oss')">测试</button>
          <button class="btn btn-ghost" @click="deleteServiceType('oss')">删除</button>
        </div>
      </article>

      <article class="card service-card">
        <div class="card-head"><h2 class="card-title">OCR</h2><span class="tag" :class="statusClass(serviceDrafts.ocr.config_id ? 'active' : 'not_configured')">{{ serviceDrafts.ocr.config_id ? '已配置' : '未配置' }}</span></div>
        <p class="card-desc">{{ serviceDescriptions.ocr }}</p>
        <div class="form-row">
          <select v-model="serviceDrafts.ocr.provider" class="select"><option value="aliyun">阿里云</option><option value="mock">Mock</option></select>
          <input v-model="serviceDrafts.ocr.name" class="input" placeholder="名称" />
        </div>
        <div v-if="serviceDrafts.ocr.provider === 'aliyun'" class="config-fields">
          <input v-model="serviceDrafts.ocr.access_key_id" class="input" placeholder="AccessKey ID" />
          <input v-model="serviceDrafts.ocr.access_key_secret" class="input" type="password" placeholder="AccessKey Secret" />
          <input v-model="serviceDrafts.ocr.endpoint" class="input" placeholder="Endpoint" />
          <input v-model="serviceDrafts.ocr.region" class="input" placeholder="Region" />
        </div>
        <label class="check"><input v-model="serviceDrafts.ocr.is_enabled" type="checkbox" />启用</label>
        <div class="card-actions">
          <button class="btn btn-primary" @click="saveServiceType('ocr')">保存</button>
          <button class="btn btn-secondary" @click="testServiceType('ocr')">测试</button>
          <button class="btn btn-ghost" @click="deleteServiceType('ocr')">删除</button>
        </div>
      </article>

      <article class="card service-card">
        <div class="card-head"><h2 class="card-title">文档解析</h2><span class="tag" :class="statusClass(serviceDrafts.doc_parser.config_id ? 'active' : 'not_configured')">{{ serviceDrafts.doc_parser.config_id ? '已配置' : '未配置' }}</span></div>
        <p class="card-desc">{{ serviceDescriptions.doc_parser }}</p>
        <div class="form-row">
          <select v-model="serviceDrafts.doc_parser.provider" class="select"><option value="aliyun">阿里云</option><option value="mock">Mock</option></select>
          <input v-model="serviceDrafts.doc_parser.name" class="input" placeholder="名称" />
        </div>
        <div v-if="serviceDrafts.doc_parser.provider === 'aliyun'" class="config-fields">
          <input v-model="serviceDrafts.doc_parser.access_key_id" class="input" placeholder="AccessKey ID" />
          <input v-model="serviceDrafts.doc_parser.access_key_secret" class="input" type="password" placeholder="AccessKey Secret" />
          <input v-model="serviceDrafts.doc_parser.endpoint" class="input" placeholder="Endpoint" />
          <input v-model="serviceDrafts.doc_parser.region" class="input" placeholder="Region" />
          <input v-model.number="serviceDrafts.doc_parser.timeout_seconds" class="input" type="number" placeholder="任务超时" />
          <input v-model.number="serviceDrafts.doc_parser.poll_interval_seconds" class="input" type="number" placeholder="轮询间隔" />
          <input v-model.number="serviceDrafts.doc_parser.layout_step_size" class="input" type="number" placeholder="拉取步长" />
          <select v-model="serviceDrafts.doc_parser.enhancement_mode" class="select"><option value="VLM">VLM</option><option value="">关闭增强</option></select>
          <label class="check"><input v-model="serviceDrafts.doc_parser.llm_enhancement" type="checkbox" />大模型增强</label>
          <label class="check"><input v-model="serviceDrafts.doc_parser.formula_enhancement" type="checkbox" />公式增强</label>
          <label class="check"><input v-model="serviceDrafts.doc_parser.output_html_table" type="checkbox" />HTML 表格</label>
        </div>
        <label class="check"><input v-model="serviceDrafts.doc_parser.is_enabled" type="checkbox" />启用</label>
        <div class="card-actions">
          <button class="btn btn-primary" @click="saveServiceType('doc_parser')">保存</button>
          <button class="btn btn-secondary" @click="testServiceType('doc_parser')">测试</button>
          <button class="btn btn-ghost" @click="deleteServiceType('doc_parser')">删除</button>
        </div>
      </article>

      <article class="card service-card">
        <div class="card-head"><h2 class="card-title">TTS</h2><span class="tag" :class="statusClass(serviceDrafts.tts.config_id ? 'active' : 'not_configured')">{{ serviceDrafts.tts.config_id ? '已配置' : '未配置' }}</span></div>
        <p class="card-desc">{{ serviceDescriptions.tts }}</p>
        <div class="form-row">
          <select v-model="serviceDrafts.tts.provider" class="select"><option value="aliyun">阿里云</option><option value="mock">Mock</option></select>
          <input v-model="serviceDrafts.tts.name" class="input" placeholder="名称" />
        </div>
        <div v-if="serviceDrafts.tts.provider === 'aliyun'" class="config-fields">
          <input v-model="serviceDrafts.tts.appkey" class="input" placeholder="AppKey" />
          <input v-model="serviceDrafts.tts.token" class="input" type="password" placeholder="Token" />
          <input v-model="serviceDrafts.tts.url" class="input" placeholder="URL" />
          <input v-model="serviceDrafts.tts.voice" class="input" placeholder="音色" />
          <input v-model.number="serviceDrafts.tts.speech_rate" class="input" type="number" placeholder="语速" />
          <input v-model.number="serviceDrafts.tts.volume" class="input" type="number" placeholder="音量" />
        </div>
        <label class="check"><input v-model="serviceDrafts.tts.is_enabled" type="checkbox" />启用</label>
        <div class="card-actions">
          <button class="btn btn-primary" @click="saveServiceType('tts')">保存</button>
          <button class="btn btn-secondary" @click="testServiceType('tts')">测试</button>
          <button class="btn btn-ghost" @click="deleteServiceType('tts')">删除</button>
        </div>
      </article>

      <article class="card service-card">
        <div class="card-head"><h2 class="card-title">邮件</h2><span class="tag" :class="statusClass(serviceDrafts.email.config_id ? 'active' : 'not_configured')">{{ serviceDrafts.email.config_id ? '已配置' : '未配置' }}</span></div>
        <p class="card-desc">{{ serviceDescriptions.email }}</p>
        <div class="form-row">
          <select v-model="serviceDrafts.email.provider" class="select"><option value="smtp">SMTP</option><option value="mock">Mock</option></select>
          <input v-model="serviceDrafts.email.name" class="input" placeholder="名称" />
        </div>
        <div v-if="serviceDrafts.email.provider === 'smtp'" class="config-fields">
          <input v-model="serviceDrafts.email.host" class="input" placeholder="Host" />
          <input v-model.number="serviceDrafts.email.port" class="input" type="number" placeholder="Port" />
          <input v-model="serviceDrafts.email.sender" class="input" placeholder="发件人" />
          <input v-model="serviceDrafts.email.username" class="input" placeholder="用户名" />
          <input v-model="serviceDrafts.email.password" class="input" type="password" placeholder="密码" />
          <label class="check"><input v-model="serviceDrafts.email.use_ssl" type="checkbox" />SSL</label>
          <label class="check"><input v-model="serviceDrafts.email.use_tls" type="checkbox" />TLS</label>
        </div>
        <label class="check"><input v-model="serviceDrafts.email.is_enabled" type="checkbox" />启用</label>
        <div class="card-actions">
          <button class="btn btn-primary" @click="saveServiceType('email')">保存</button>
          <button class="btn btn-secondary" @click="testServiceType('email')">测试</button>
          <button class="btn btn-ghost" @click="deleteServiceType('email')">删除</button>
        </div>
      </article>
    </div>
  </section>

  <section v-if="active === 'adminSystem'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">系统参数</h2><button class="btn btn-primary" @click="saveSetting"><Save :size="16" />保存</button></div>
      <input v-model="settingKey" class="input" placeholder="Key" />
      <textarea v-model="settingValue" class="textarea" placeholder="Value JSON"></textarea>
      <div class="hint-grid">
        <div><strong>含义</strong><span>{{ settingDescription(settingKey) }}</span></div>
      </div>
    </section>
    <aside class="card">
      <div v-for="item in settings" :key="item.id" class="row" @click="pickSetting(item)">
        <span><strong>{{ item.setting_key }}</strong><small>{{ settingDescription(item.setting_key, item.description) }}</small></span><span class="tag">{{ item.category }}</span>
      </div>
      <div v-if="!settings.length" class="muted">暂无</div>
    </aside>
  </section>

  <section v-if="active === 'adminMonitor'" class="page">
    <div class="grid stats">
      <StatCard :icon="Users" label="在线" :value="overview.online_users || 0" />
      <StatCard :icon="BarChart2" label="API" :value="overview.api_call_count_30m || 0" />
      <StatCard :icon="Sparkles" label="AI" :value="overview.ai_call_count_30m || 0" />
      <StatCard :icon="XCircle" label="失败" :value="overview.ai_failure_count_30m || 0" danger />
    </div>
    <div class="monitor-grid">
      <article v-for="item in monitorRows" :key="item.label" class="card status-card">
        <span class="status-icon"><component :is="item.icon" :size="20" /></span>
        <div><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
        <span class="tag" :class="statusClass(item.status)">{{ labelOf(statusLabels, item.status) }}</span>
      </article>
    </div>
  </section>

  <section v-if="active === 'adminLogs'" class="page">
    <div class="toolbar">
      <select v-model="logType" class="select short"><option value="login">登录</option><option value="operations">操作</option><option value="errors">错误</option></select>
      <input v-model.number="logLimit" class="input tiny" type="number" />
      <input v-model.number="logFilter.user_id" class="input tiny" type="number" placeholder="用户" />
      <select v-if="logType === 'login'" v-model="logFilter.success" class="select short"><option value="">结果</option><option value="true">成功</option><option value="false">失败</option></select>
      <input v-if="logType === 'operations'" v-model="logFilter.action" class="input short" placeholder="动作" />
      <input v-if="logType === 'operations'" v-model="logFilter.target_type" class="input short" placeholder="对象" />
      <input v-if="logType === 'errors'" v-model="logFilter.level" class="input short" placeholder="级别" />
      <input v-if="logType === 'errors'" v-model="logFilter.source" class="input short" placeholder="来源" />
      <input v-model="logFilter.start_at" class="input date" type="datetime-local" />
      <input v-model="logFilter.end_at" class="input date" type="datetime-local" />
      <button class="btn btn-secondary" @click="loadLogs"><Search :size="16" />查看</button>
    </div>
    <DataTable :headers="['时间','主体','内容','来源']">
      <tr v-for="item in logs" :key="item.id">
        <td>{{ formatTime(item.created_at) }}</td>
        <td>{{ logSubject(item) }}</td>
        <td>{{ logContent(item) }}</td>
        <td><span class="tag">{{ logMeta(item) }}</span></td>
      </tr>
      <tr v-if="!logs.length"><td colspan="4" class="muted">暂无</td></tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminBackups'" class="page">
    <div class="toolbar"><button class="btn btn-primary" @click="createBackup"><Database :size="16" />备份</button></div>
    <DataTable :headers="['文件','状态','触发','时间','操作']">
      <tr v-for="item in backups" :key="item.id">
        <td>{{ fileName(item.file_path || item.backup_name) }}</td>
        <td><span class="tag" :class="statusClass(item.status)">{{ labelOf(statusLabels, item.status) }}</span></td>
        <td>{{ item.trigger_user_id || '-' }}</td>
        <td>{{ formatTime(item.created_at) }}</td>
        <td class="ops"><button class="btn btn-ghost btn-xs" @click="restoreBackup(item.id)">恢复</button><button class="btn btn-ghost btn-xs" @click="deleteBackup(item.id)">删除</button></td>
      </tr>
      <tr v-if="!backups.length"><td colspan="5" class="muted">暂无</td></tr>
    </DataTable>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { BarChart2, CheckCircle, Database, Eye, HardDrive, Plus, RefreshCw, Save, Search, Server, Sparkles, Trash2, Upload, Users, XCircle } from "lucide-vue-next";
import { api } from "../../api/client";
import StatCard from "../../components/StatCard.vue";
import DataTable from "./DataTable.vue";

const props = defineProps<{ active: string; notice: (type: "success" | "warning" | "error" | "info", text: string) => void }>();

const users = ref<any[]>([]);
const adminCourses = ref<any[]>([]);
const adminCourseDetail = ref<any | null>(null);
const adminMaterials = ref<any[]>([]);
const materialStats = ref<any>({});
const models = ref<any[]>([]);
const usage = ref<any>({});
const services = ref<any[]>([]);
const settings = ref<any[]>([]);
const overview = ref<any>({});
const logs = ref<any[]>([]);
const backups = ref<any[]>([]);

const userFilter = reactive({ role: "", status: "", keyword: "" });
const courseFilter = reactive({ keyword: "", status: "" });
const materialFilter = reactive({ keyword: "", category: "", material_type: "", teacher_id: null as number | null, start_at: "", end_at: "" });
const adminForm = reactive({ email: "", password: "Admin123456", nickname: "" });
const takeoverTeacher = ref<number | null>(null);
const modelForm = reactive({ config_id: null as number | null, provider: "openai", model_name: "", purpose: "general", endpoint: "", api_key: "", is_default: true });
const modelExtra = ref('{"temperature":0.2}');
type ServiceKey = "oss" | "ocr" | "doc_parser" | "tts" | "email";
const serviceDrafts = reactive({
  oss: { config_id: null as number | null, provider: "aliyun", name: "OSS", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "", bucket: "" },
  ocr: { config_id: null as number | null, provider: "aliyun", name: "OCR", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "" },
  doc_parser: { config_id: null as number | null, provider: "aliyun", name: "文档解析", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "docmind-api.cn-hangzhou.aliyuncs.com", region: "cn-hangzhou", timeout_seconds: 600, poll_interval_seconds: 5, layout_step_size: 100, output_format: "markdown", llm_enhancement: true, enhancement_mode: "VLM", formula_enhancement: false, output_html_table: false },
  tts: { config_id: null as number | null, provider: "aliyun", name: "TTS", is_enabled: true, appkey: "", token: "", url: "", voice: "", speech_rate: 0, volume: 50 },
  email: { config_id: null as number | null, provider: "smtp", name: "邮件", is_enabled: true, host: "", port: 465, sender: "", username: "", password: "", use_ssl: true, use_tls: false }
});
const settingKey = ref("");
const settingValue = ref("{}");
const logType = ref("login");
const logLimit = ref(100);
const logFilter = reactive({ user_id: null as number | null, success: "", action: "", target_type: "", level: "", source: "", start_at: "", end_at: "" });

const roleLabels: Record<string, string> = { student: "学生", teacher: "教师", admin: "管理员" };
const statusLabels: Record<string, string> = { active: "启用", disabled: "禁用", inactive: "停用", ready: "就绪", pending: "待处理", processing: "处理中", failed: "失败", success: "成功", ok: "正常", down: "异常", not_configured: "未配置", published: "发布", draft: "草稿" };
const categoryLabels: Record<string, string> = { courseware: "课件", handout: "讲义", exercise: "练习", reference: "参考" };
const materialTypeLabels: Record<string, string> = { ppt: "PPT", pptx: "PPT", pdf: "PDF", doc: "Word", docx: "Word", txt: "TXT" };
const purposeLabels: Record<string, string> = { general: "通用", qa: "问答", embedding: "向量", script: "讲稿", quiz: "测验", tutoring: "辅导", analysis: "分析", study_plan: "计划" };
const purposeDescriptions: Record<string, string> = {
  general: "通用兜底模型",
  qa: "课程 RAG 问答",
  embedding: "资料向量化",
  script: "课堂讲稿生成",
  quiz: "测验与评分",
  tutoring: "题目分级辅导",
  analysis: "教学分析建议",
  study_plan: "学习计划生成"
};
const serviceDescriptions: Record<string, string> = {
  oss: "未配默认本地",
  ocr: "图片题识别",
  doc_parser: "资料文档解析",
  tts: "讲稿转语音",
  email: "验证码邮件"
};
const serviceRequiredKeys: Record<string, string[]> = {
  oss: ["access_key_id", "access_key_secret", "endpoint", "bucket"],
  ocr: ["access_key_id", "access_key_secret", "endpoint", "region"],
  doc_parser: ["access_key_id", "access_key_secret", "endpoint"],
  tts: ["appkey", "token", "url", "voice"],
  email: ["host", "port", "sender"]
};
const settingDescriptions: Record<string, string> = {
  "upload.max_size_mb": "单文件上传上限，单位 MB",
  "course.material.max_count": "单课程资料数量上限",
  "lesson.script.max_length": "课堂讲解脚本最大长度",
  "qa.context.turn_limit": "问答多轮上下文轮数",
  "quiz.default_question_count": "默认测验题量",
  "tutoring.default_release_level": "题目辅导默认开放级别",
  "tts.default_voice": "默认 TTS 音色",
  "tts.default_rate": "默认 TTS 语速",
  "tts.default_volume": "默认 TTS 音量",
  "system.announcement": "系统公告内容",
  "backup.schedule": "数据库定期备份计划"
};

const purposeEntries = computed(() => Object.entries(purposeLabels).map(([key, label]) => ({ key, label, desc: purposeDescriptions[key] })));
const monitorRows = computed(() => [
  { label: "数据库", value: overview.value.database_status || "-", status: overview.value.database_status || "not_configured", icon: Database },
  { label: "缓存", value: overview.value.cache_status || "-", status: overview.value.cache_status || "not_configured", icon: Server },
  { label: "异步队列", value: overview.value.async_queue_pending ?? 0, status: (overview.value.async_queue_pending || 0) > 0 ? "processing" : "ok", icon: HardDrive },
  { label: "Celery", value: overview.value.celery_queue_length ?? "-", status: overview.value.celery_queue_length === null ? "not_configured" : "ok", icon: BarChart2 }
]);

function labelOf(map: Record<string, string>, value: unknown) {
  if (value === undefined || value === null || value === "") return "-";
  return map[String(value)] || String(value);
}
function statusClass(status: unknown) {
  if (["ready", "published", "active", "success", "ok"].includes(String(status))) return "tag-success";
  if (["pending", "processing", "review", "not_configured"].includes(String(status))) return "tag-warning";
  if (["failed", "inactive", "disabled", "down"].includes(String(status))) return "tag-danger";
  return "";
}
function boolLabel(value: boolean) {
  return value ? "是" : "否";
}
function statEntries(source: Record<string, unknown> | undefined, labels: Record<string, string> = {}) {
  return Object.entries(source || {}).map(([key, value]) => ({ key, label: labelOf(labels, key), value }));
}
function formatTime(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
function fileName(path: string | null | undefined) {
  if (!path) return "-";
  return path.split("/").pop() || path;
}
function logSubject(item: any) {
  if (logType.value === "login") return `用户 ${item.user_id || "-"}`;
  if (logType.value === "operations") return item.target_id ? `${item.target_type} #${item.target_id}` : item.target_type || "-";
  return item.level || "-";
}
function logContent(item: any) {
  if (logType.value === "login") return item.success ? "登录成功" : "登录失败";
  if (logType.value === "operations") return item.action || "-";
  return item.message || "-";
}
function logMeta(item: any) {
  if (logType.value === "login") return item.login_ip || "-";
  if (logType.value === "operations") return item.user_id ? `用户 ${item.user_id}` : "-";
  return item.source || "-";
}
function parseJsonObject(value: string) {
  const parsed = JSON.parse(value || "{}");
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("JSON 必须是对象");
  return parsed as Record<string, unknown>;
}
function settingDescription(key: string, fallback?: string) {
  return settingDescriptions[key] || fallback || "自定义系统参数";
}
async function run<T>(task: () => Promise<T>, ok?: string) {
  try {
    const data = await task();
    if (ok) props.notice("success", ok);
    return data;
  } catch (error) {
    props.notice("error", (error as Error).message);
    return null;
  }
}
async function loadUsers() { users.value = (await run(() => api.get<any[]>("/admin/users", userFilter))) || []; }
async function createAdmin() { await run(() => api.post("/admin/users/admin", adminForm), "已创建"); await loadUsers(); }
async function setUser(id: number, status: string, role: string) { await run(() => api.patch(`/admin/users/${id}`, { status, role }), "已更新"); await loadUsers(); }
async function resetUser(id: number) { await run(() => api.post(`/admin/users/${id}/reset-password`, { new_password: "Admin123456" }), "已重置"); }
async function deleteUser(id: number) { await run(() => api.delete(`/admin/users/${id}`), "已删除"); await loadUsers(); }
async function loadCourses() { adminCourses.value = (await run(() => api.get<any[]>("/admin/courses", courseFilter))) || []; }
async function loadCourseDetail(id: number) { adminCourseDetail.value = await run(() => api.get(`/admin/courses/${id}`)); }
async function deactivate(id: number) { await run(() => api.post(`/admin/courses/${id}/deactivate`), "已停用"); await loadCourses(); }
async function takeover(id: number) { if (!takeoverTeacher.value) return; await run(() => api.post(`/admin/courses/${id}/takeover`, { teacher_id: takeoverTeacher.value }), "已接管"); await loadCourses(); }
async function loadMaterials() {
  adminMaterials.value = (await run(() => api.get<any[]>("/admin/materials", materialFilter))) || [];
  materialStats.value = (await run(() => api.get("/admin/materials/stats"))) || {};
}
async function deleteMaterial(id: number) { await run(() => api.delete(`/admin/materials/${id}`), "已删除"); await loadMaterials(); }
async function loadModels() { models.value = (await run(() => api.get<any[]>("/admin/model-configs"))) || []; await loadUsage(); }
async function loadUsage() { usage.value = (await run(() => api.get("/admin/model-usage"))) || {}; }
async function saveModel() {
  if (!modelForm.provider.trim() || !modelForm.model_name.trim() || !modelForm.purpose.trim()) {
    props.notice("warning", "模型必填");
    return;
  }
  if (modelForm.provider !== "mock" && !modelForm.endpoint.trim()) {
    props.notice("warning", "Endpoint 必填");
    return;
  }
  if (!modelForm.config_id && modelForm.provider !== "mock" && !modelForm.api_key.trim()) {
    props.notice("warning", "密钥必填");
    return;
  }
  let extra_config: Record<string, unknown>;
  try {
    extra_config = parseJsonObject(modelExtra.value);
  } catch (error) {
    props.notice("warning", (error as Error).message);
    return;
  }
  await run(() => api.post("/admin/model-configs", { ...modelForm, extra_config }), "已保存");
  resetModelForm();
  await loadModels();
}
function pickModel(item: any) {
  Object.assign(modelForm, { config_id: item.id, provider: item.provider, model_name: item.model_name, purpose: item.purpose, endpoint: item.endpoint || "", api_key: "", is_default: item.is_default });
  modelExtra.value = JSON.stringify(item.extra_config || {}, null, 2);
}
function configuredModels(purpose: string) {
  return models.value.filter((item) => item.purpose === purpose);
}
function configureModelPurpose(purpose: string) {
  const current = configuredModels(purpose)[0];
  if (current) pickModel(current);
  else Object.assign(modelForm, { config_id: null, purpose, provider: "openai", model_name: "", endpoint: "", api_key: "", is_default: true });
}
function resetModelForm() {
  Object.assign(modelForm, { config_id: null, provider: "openai", model_name: "", purpose: "general", endpoint: "", api_key: "", is_default: true });
  modelExtra.value = '{"temperature":0.2}';
}
async function testModel(id: number) { const data = await run(() => api.post<any>(`/admin/model-configs/${id}/test`)); if (data) props.notice(data.success ? "success" : "warning", data.message); }
async function deleteModel(id: number) { await run(() => api.delete(`/admin/model-configs/${id}`), "已删除"); await loadModels(); }
async function loadServices() {
  services.value = (await run(() => api.get<any[]>("/admin/service-configs"))) || [];
  hydrateServiceDrafts();
}
function hydrateServiceDrafts() {
  (["oss", "ocr", "doc_parser", "tts", "email"] as ServiceKey[]).forEach((key) => {
    const item = services.value.find((service) => service.service_type === key);
    if (!item) return;
    Object.assign(serviceDrafts[key], {
      config_id: item.id,
      provider: item.provider,
      name: item.name,
      is_enabled: item.is_enabled,
      ...(item.config || {})
    });
  });
}
function serviceConfigPayload(type: ServiceKey) {
  if (type === "oss") {
    const item = serviceDrafts.oss;
    return { access_key_id: item.access_key_id, access_key_secret: item.access_key_secret, endpoint: item.endpoint, region: item.region, bucket: item.bucket };
  }
  if (type === "ocr") {
    const item = serviceDrafts.ocr;
    return { access_key_id: item.access_key_id, access_key_secret: item.access_key_secret, endpoint: item.endpoint, region: item.region };
  }
  if (type === "doc_parser") {
    const item = serviceDrafts.doc_parser;
    return {
      access_key_id: item.access_key_id,
      access_key_secret: item.access_key_secret,
      endpoint: item.endpoint,
      region: item.region,
      timeout_seconds: item.timeout_seconds,
      poll_interval_seconds: item.poll_interval_seconds,
      layout_step_size: item.layout_step_size,
      output_format: item.output_format,
      llm_enhancement: item.llm_enhancement,
      enhancement_mode: item.enhancement_mode,
      formula_enhancement: item.formula_enhancement,
      output_html_table: item.output_html_table
    };
  }
  if (type === "tts") {
    const item = serviceDrafts.tts;
    return { appkey: item.appkey, token: item.token, url: item.url, voice: item.voice, speech_rate: item.speech_rate, volume: item.volume };
  }
  const item = serviceDrafts.email;
  return { host: item.host, port: item.port, sender: item.sender, username: item.username, password: item.password, use_ssl: item.use_ssl, use_tls: item.use_tls };
}
function validateServiceType(type: ServiceKey) {
  const draft = serviceDrafts[type];
  if (!draft.name.trim() || !draft.provider.trim()) return "服务必填";
  if (["local", "mock"].includes(draft.provider)) return "";
  const config = serviceConfigPayload(type) as Record<string, unknown>;
  const missing = (serviceRequiredKeys[type] || []).filter((key) => !config[key]);
  return missing.length ? `缺少 ${missing.join(", ")}` : "";
}
async function saveServiceType(type: ServiceKey) {
  const error = validateServiceType(type);
  if (error) {
    props.notice("warning", error);
    return;
  }
  const draft = serviceDrafts[type];
  await run(() => api.post("/admin/service-configs", {
    config_id: draft.config_id,
    service_type: type,
    provider: draft.provider,
    name: draft.name,
    is_enabled: draft.is_enabled,
    config: serviceConfigPayload(type)
  }), "已保存");
  await loadServices();
}
async function testServiceType(type: ServiceKey) {
  const id = serviceDrafts[type].config_id;
  if (!id) {
    props.notice("warning", "先保存");
    return;
  }
  const data = await run(() => api.post<any>(`/admin/service-configs/${id}/test`));
  if (data) props.notice(data.success ? "success" : "warning", data.message);
}
async function deleteServiceType(type: ServiceKey) {
  const id = serviceDrafts[type].config_id;
  if (!id) return;
  await run(() => api.delete(`/admin/service-configs/${id}`), "已删除");
  resetServiceDraft(type);
  await loadServices();
}
function resetServiceDraft(type: ServiceKey) {
  if (type === "oss") Object.assign(serviceDrafts.oss, { config_id: null, provider: "aliyun", name: "OSS", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "", bucket: "" });
  if (type === "ocr") Object.assign(serviceDrafts.ocr, { config_id: null, provider: "aliyun", name: "OCR", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "", region: "" });
  if (type === "doc_parser") Object.assign(serviceDrafts.doc_parser, { config_id: null, provider: "aliyun", name: "文档解析", is_enabled: true, access_key_id: "", access_key_secret: "", endpoint: "docmind-api.cn-hangzhou.aliyuncs.com", region: "cn-hangzhou", timeout_seconds: 600, poll_interval_seconds: 5, layout_step_size: 100, output_format: "markdown", llm_enhancement: true, enhancement_mode: "VLM", formula_enhancement: false, output_html_table: false });
  if (type === "tts") Object.assign(serviceDrafts.tts, { config_id: null, provider: "aliyun", name: "TTS", is_enabled: true, appkey: "", token: "", url: "", voice: "", speech_rate: 0, volume: 50 });
  if (type === "email") Object.assign(serviceDrafts.email, { config_id: null, provider: "smtp", name: "邮件", is_enabled: true, host: "", port: 465, sender: "", username: "", password: "", use_ssl: true, use_tls: false });
}
async function loadSettings() { settings.value = (await run(() => api.get<any[]>("/admin/system-settings"))) || []; }
function pickSetting(item: any) { settingKey.value = item.setting_key; settingValue.value = JSON.stringify(item.setting_value ?? {}, null, 2); }
async function saveSetting() {
  if (!settingKey.value.trim()) {
    props.notice("warning", "Key 必填");
    return;
  }
  let value: unknown;
  try {
    value = JSON.parse(settingValue.value || "null");
  } catch {
    props.notice("warning", "JSON 错误");
    return;
  }
  await run(() => api.put(`/admin/system-settings/${settingKey.value}`, { value }), "已保存");
  await loadSettings();
}
async function loadOverview() { overview.value = (await run(() => api.get("/admin/monitoring/overview"))) || {}; }
function logQuery() {
  const base: Record<string, unknown> = { limit: logLimit.value, start_at: logFilter.start_at, end_at: logFilter.end_at };
  if (logType.value === "login") return { ...base, user_id: logFilter.user_id, success: logFilter.success === "" ? undefined : logFilter.success === "true" };
  if (logType.value === "operations") return { ...base, user_id: logFilter.user_id, action: logFilter.action, target_type: logFilter.target_type };
  return { ...base, level: logFilter.level, source: logFilter.source };
}
async function loadLogs() { logs.value = (await run(() => api.get<any[]>(`/admin/logs/${logType.value}`, logQuery()))) || []; }
async function loadBackups() { backups.value = (await run(() => api.get<any[]>("/admin/backups"))) || []; }
async function createBackup() { await run(() => api.post("/admin/backups"), "已备份"); await loadBackups(); }
async function restoreBackup(id: number) { await run(() => api.post(`/admin/backups/${id}/restore`), "已恢复"); await loadBackups(); }
async function deleteBackup(id: number) { await run(() => api.delete(`/admin/backups/${id}`), "已删除"); await loadBackups(); }

async function loadActive() {
  if (props.active === "adminUsers") await loadUsers();
  if (props.active === "adminCourses") await loadCourses();
  if (props.active === "adminMaterials") await loadMaterials();
  if (props.active === "adminModels") await loadModels();
  if (props.active === "adminServices") await loadServices();
  if (props.active === "adminSystem") await loadSettings();
  if (props.active === "adminMonitor") await loadOverview();
  if (props.active === "adminLogs") await loadLogs();
  if (props.active === "adminBackups") await loadBackups();
}
watch(() => props.active, loadActive);
watch(logType, loadLogs);
onMounted(loadActive);
</script>

<style scoped>
.short { max-width: 220px; }
.tiny { max-width: 96px; }
.date { max-width: 180px; }
.mini { max-width: 72px; height: 28px; }
.ops { white-space: nowrap; }
.admin-form, .detail-card, .breakdown-grid { margin-bottom: var(--space-4); }
.admin-form .form-row { grid-template-columns: repeat(3, minmax(0, 1fr)) auto; }
.detail-grid, .breakdown-grid, .monitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
}
.detail-grid { margin-bottom: var(--space-4); }
.detail-grid div {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.detail-grid span, .status-card span, .usage-row span {
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.detail-grid strong, .status-card strong {
  display: block;
  margin-top: var(--space-1);
  color: var(--color-text-primary);
}
.breakdown-grid .card {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  box-shadow: none;
}
.status-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--space-3);
}
.status-icon {
  display: inline-flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}
.usage-row {
  display: grid;
  gap: var(--space-1);
  border-bottom: 1px solid var(--color-border-subtle);
  padding: var(--space-3) 0;
}
.model-purpose-grid, .service-config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.config-tile {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-1) var(--space-3);
  min-height: 84px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  padding: var(--space-3);
  text-align: left;
}
.config-tile span {
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.config-tile em {
  grid-row: 1 / 3;
  grid-column: 2;
  align-self: center;
  min-width: 28px;
  border-radius: var(--radius-full);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-style: normal;
  text-align: center;
}
.config-tile.active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}
.service-card {
  display: grid;
  align-content: start;
  gap: var(--space-3);
}
.config-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.hint-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
  margin: var(--space-3) 0 var(--space-4);
}
.hint-grid div, .desc-row {
  display: grid;
  gap: var(--space-1);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.desc-row { margin-bottom: var(--space-2); }
.hint-grid span, .desc-row span {
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
small { display: block; color: var(--color-text-muted); }
@media (max-width: 767px) {
  .admin-form .form-row { grid-template-columns: 1fr; }
}
</style>
