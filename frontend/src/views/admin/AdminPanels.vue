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
      <div class="card-head"><h2 class="card-title">模型配置</h2><button class="btn btn-primary" @click="saveModel"><Save :size="16" />保存</button></div>
      <div class="form-row">
        <input v-model="modelForm.provider" class="input" placeholder="提供商" />
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
      <DataTable :headers="['模型','用途','默认','密钥','操作']">
        <tr v-for="item in models" :key="item.id">
          <td><strong>{{ item.provider }}</strong><br><small>{{ item.model_name }}</small></td>
          <td>{{ labelOf(purposeLabels, item.purpose) }}</td>
          <td><span class="tag" :class="item.is_default ? 'tag-success' : ''">{{ boolLabel(item.is_default) }}</span></td>
          <td>{{ item.api_key || '-' }}</td>
          <td class="ops"><button class="btn btn-ghost btn-xs" @click="pickModel(item)">编辑</button><button class="btn btn-ghost btn-xs" @click="testModel(item.id)">测试</button></td>
        </tr>
        <tr v-if="!models.length"><td colspan="5" class="muted">暂无</td></tr>
      </DataTable>
    </section>
    <aside class="card">
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

  <section v-if="active === 'adminServices'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">服务配置</h2><button class="btn btn-primary" @click="saveService"><Save :size="16" />保存</button></div>
      <div class="form-row">
        <select v-model="serviceForm.service_type" class="select">
          <option value="oss">OSS</option><option value="ocr">OCR</option><option value="tts">TTS</option><option value="email">邮件</option>
        </select>
        <select v-model="serviceForm.provider" class="select">
          <option value="aliyun">阿里云</option><option value="smtp">SMTP</option><option value="local">本地</option><option value="mock">Mock</option>
        </select>
      </div>
      <input v-model="serviceForm.name" class="input" placeholder="名称" />
      <label class="check"><input v-model="serviceForm.is_enabled" type="checkbox" />启用</label>
      <textarea v-model="serviceConfig" class="textarea" placeholder="配置 JSON"></textarea>
      <DataTable :headers="['服务','提供方','启用','操作']">
        <tr v-for="item in services" :key="item.id">
          <td>{{ labelOf(serviceLabels, item.service_type) }}<br><small>{{ item.name }}</small></td>
          <td>{{ labelOf(providerLabels, item.provider) }}</td>
          <td><span class="tag" :class="item.is_enabled ? 'tag-success' : ''">{{ boolLabel(item.is_enabled) }}</span></td>
          <td class="ops"><button class="btn btn-ghost btn-xs" @click="pickService(item)">编辑</button><button class="btn btn-ghost btn-xs" @click="testService(item.id)">测试</button></td>
        </tr>
        <tr v-if="!services.length"><td colspan="4" class="muted">暂无</td></tr>
      </DataTable>
    </section>
    <aside class="card">
      <div class="card-head"><h2 class="card-title">存储</h2><span class="tag tag-primary">{{ storageMode }}</span></div>
      <div class="row"><span>OSS</span><span class="tag">{{ ossEnabled ? '启用' : '未配' }}</span></div>
      <div class="row"><span>本地</span><span class="tag tag-success">可用</span></div>
    </aside>
  </section>

  <section v-if="active === 'adminSystem'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">系统参数</h2><button class="btn btn-primary" @click="saveSetting"><Save :size="16" />保存</button></div>
      <input v-model="settingKey" class="input" placeholder="Key" />
      <textarea v-model="settingValue" class="textarea" placeholder="Value JSON"></textarea>
    </section>
    <aside class="card">
      <div v-for="item in settings" :key="item.id" class="row" @click="pickSetting(item)">
        <span>{{ item.setting_key }}</span><span class="tag">{{ item.category }}</span>
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
const serviceForm = reactive({ config_id: null as number | null, service_type: "oss", provider: "aliyun", name: "", is_enabled: true });
const serviceConfig = ref("{}");
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
const serviceLabels: Record<string, string> = { oss: "OSS", ocr: "OCR", tts: "TTS", email: "邮件" };
const providerLabels: Record<string, string> = { aliyun: "阿里云", smtp: "SMTP", local: "本地", mock: "Mock" };

const ossEnabled = computed(() => services.value.some((item) => item.service_type === "oss" && item.is_enabled && item.provider !== "local"));
const storageMode = computed(() => (ossEnabled.value ? "OSS" : "本地"));
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
  await run(() => api.post("/admin/model-configs", { ...modelForm, extra_config: JSON.parse(modelExtra.value || "{}") }), "已保存");
  await loadModels();
}
function pickModel(item: any) {
  Object.assign(modelForm, { config_id: item.id, provider: item.provider, model_name: item.model_name, purpose: item.purpose, endpoint: item.endpoint || "", api_key: "", is_default: item.is_default });
  modelExtra.value = JSON.stringify(item.extra_config || {}, null, 2);
}
async function testModel(id: number) { const data = await run(() => api.post<any>(`/admin/model-configs/${id}/test`)); if (data) props.notice(data.success ? "success" : "warning", data.message); }
async function loadServices() { services.value = (await run(() => api.get<any[]>("/admin/service-configs"))) || []; }
async function saveService() {
  await run(() => api.post("/admin/service-configs", { ...serviceForm, config: JSON.parse(serviceConfig.value || "{}") }), "已保存");
  await loadServices();
}
function pickService(item: any) {
  Object.assign(serviceForm, { config_id: item.id, service_type: item.service_type, provider: item.provider, name: item.name, is_enabled: item.is_enabled });
  serviceConfig.value = JSON.stringify(item.config || {}, null, 2);
}
async function testService(id: number) { const data = await run(() => api.post<any>(`/admin/service-configs/${id}/test`)); if (data) props.notice(data.success ? "success" : "warning", data.message); }
async function loadSettings() { settings.value = (await run(() => api.get<any[]>("/admin/system-settings"))) || []; }
function pickSetting(item: any) { settingKey.value = item.setting_key; settingValue.value = JSON.stringify(item.setting_value ?? {}, null, 2); }
async function saveSetting() { await run(() => api.put(`/admin/system-settings/${settingKey.value}`, { value: JSON.parse(settingValue.value || "null") }), "已保存"); await loadSettings(); }
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
.check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
small { color: var(--color-text-muted); }
@media (max-width: 767px) {
  .admin-form .form-row { grid-template-columns: 1fr; }
}
</style>
