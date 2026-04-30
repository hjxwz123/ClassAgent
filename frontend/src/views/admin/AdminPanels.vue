<template>
  <section v-if="active === 'adminUsers'" class="page">
    <div class="toolbar">
      <input v-model="userFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="userFilter.role" class="select short"><option value="">角色</option><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option></select>
      <button class="btn btn-secondary" @click="loadUsers">搜索</button>
      <button class="btn btn-primary" @click="createAdmin">创建</button>
    </div>
    <div class="form-row">
      <input v-model="adminForm.email" class="input" placeholder="邮箱" />
      <input v-model="adminForm.nickname" class="input" placeholder="昵称" />
      <input v-model="adminForm.password" class="input" type="password" placeholder="密码" />
    </div>
    <DataTable :headers="['用户','角色','状态','操作']">
      <tr v-for="item in users" :key="item.id">
        <td>{{ item.nickname }}<br><small>{{ item.email }}</small></td>
        <td>{{ item.role }}</td>
        <td>{{ item.status }}</td>
        <td class="ops">
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'student')">设生</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'teacher')">设师</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, item.status, 'admin')">设管</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, 'active', item.role)">启用</button>
          <button class="btn btn-ghost btn-xs" @click="setUser(item.id, 'disabled', item.role)">禁用</button>
          <button class="btn btn-ghost btn-xs" @click="resetUser(item.id)">重置</button>
          <button class="btn btn-ghost btn-xs" @click="deleteUser(item.id)">删除</button>
        </td>
      </tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminCourses'" class="page">
    <div class="toolbar">
      <input v-model="courseFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="courseFilter.status" class="select short"><option value="">状态</option><option value="active">active</option><option value="inactive">inactive</option></select>
      <button class="btn btn-secondary" @click="loadCourses">搜索</button>
    </div>
    <DataTable :headers="['课程','教师','状态','操作']">
      <tr v-for="item in adminCourses" :key="item.id">
        <td>{{ item.name }}<br><small>{{ item.course_code }}</small></td>
        <td>{{ item.teacher_id }}</td>
        <td>{{ item.status }}</td>
        <td class="ops">
          <input v-model.number="takeoverTeacher" class="input mini" type="number" />
          <button class="btn btn-ghost btn-xs" @click="loadCourseDetail(item.id)">详情</button>
          <button class="btn btn-ghost btn-xs" @click="takeover(item.id)">接管</button>
          <button class="btn btn-ghost btn-xs" @click="deactivate(item.id)">停用</button>
        </td>
      </tr>
    </DataTable>
    <article v-if="adminCourseDetail" class="card detail-card">
      <div class="card-head"><h2 class="card-title">{{ adminCourseDetail.course?.name || '课程详情' }}</h2><span class="tag">{{ adminCourseDetail.student_count || 0 }}人</span></div>
      <pre>{{ adminCourseDetail }}</pre>
    </article>
  </section>

  <section v-if="active === 'adminMaterials'" class="page">
    <div class="grid stats">
      <StatCard :icon="Upload" label="资料" :value="materialStats.total || 0" />
      <StatCard :icon="CheckCircle" label="就绪" :value="materialStats.ready || 0" />
      <StatCard :icon="XCircle" label="失败" :value="materialStats.failed || 0" danger />
    </div>
    <div class="toolbar">
      <input v-model="materialFilter.keyword" class="input short" placeholder="关键词" />
      <select v-model="materialFilter.category" class="select short"><option value="">分类</option><option value="courseware">课件</option><option value="handout">讲义</option><option value="exercise">练习</option><option value="reference">参考</option></select>
      <select v-model="materialFilter.material_type" class="select short"><option value="">类型</option><option value="pptx">PPT</option><option value="pdf">PDF</option><option value="docx">Word</option><option value="txt">TXT</option></select>
      <input v-model.number="materialFilter.teacher_id" class="input tiny" type="number" placeholder="教师" />
      <input v-model="materialFilter.start_at" class="input date" type="datetime-local" />
      <input v-model="materialFilter.end_at" class="input date" type="datetime-local" />
      <button class="btn btn-secondary" @click="loadMaterials">搜索</button>
    </div>
    <DataTable :headers="['资料','分类','状态','操作']">
      <tr v-for="item in adminMaterials" :key="item.id">
        <td>{{ item.title }}</td><td>{{ item.category }}</td><td>{{ item.parse_status }}</td>
        <td><button class="btn btn-ghost btn-xs" @click="deleteMaterial(item.id)">删除</button></td>
      </tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminModels'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">模型配置</h2><button class="btn btn-primary" @click="saveModel">保存</button></div>
      <div class="form-row">
        <input v-model="modelForm.provider" class="input" placeholder="provider" />
        <input v-model="modelForm.model_name" class="input" placeholder="model" />
      </div>
      <div class="form-row">
        <select v-model="modelForm.purpose" class="select">
          <option value="general">通用</option><option value="qa">问答</option><option value="embedding">向量</option><option value="script">讲稿</option><option value="quiz">测验</option><option value="tutoring">辅导</option><option value="analysis">分析</option><option value="study_plan">计划</option>
        </select>
        <input v-model="modelForm.endpoint" class="input" placeholder="endpoint" />
      </div>
      <input v-model="modelForm.api_key" class="input" placeholder="api_key" />
      <label class="check"><input v-model="modelForm.is_default" type="checkbox" />默认</label>
      <textarea v-model="modelExtra" class="textarea" placeholder="extra_config JSON"></textarea>
      <DataTable :headers="['模型','用途','默认','操作']">
        <tr v-for="item in models" :key="item.id">
          <td>{{ item.provider }} / {{ item.model_name }}</td><td>{{ item.purpose }}</td><td>{{ item.is_default }}</td>
          <td class="ops"><button class="btn btn-ghost btn-xs" @click="pickModel(item)">编辑</button><button class="btn btn-ghost btn-xs" @click="testModel(item.id)">测试</button></td>
        </tr>
      </DataTable>
    </section>
    <aside class="card">
      <div class="card-head"><h2 class="card-title">用量</h2><button class="btn btn-ghost btn-sm" @click="loadUsage">刷新</button></div>
      <div v-for="item in usage.items || []" :key="item.provider" class="row">
        <span>{{ item.provider }}</span><span class="tag">{{ item.call_count }}</span>
      </div>
    </aside>
  </section>

  <section v-if="active === 'adminServices'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">服务配置</h2><button class="btn btn-primary" @click="saveService">保存</button></div>
      <div class="form-row">
        <select v-model="serviceForm.service_type" class="select">
          <option value="oss">OSS</option><option value="ocr">OCR</option><option value="tts">TTS</option><option value="email">邮件</option>
        </select>
        <select v-model="serviceForm.provider" class="select">
          <option value="aliyun">阿里云</option><option value="smtp">SMTP</option><option value="local">本地</option><option value="mock">Mock</option>
        </select>
      </div>
      <input v-model="serviceForm.name" class="input" placeholder="name" />
      <label class="check"><input v-model="serviceForm.is_enabled" type="checkbox" />启用</label>
      <textarea v-model="serviceConfig" class="textarea" placeholder="config JSON"></textarea>
      <DataTable :headers="['服务','提供方','启用','操作']">
        <tr v-for="item in services" :key="item.id">
          <td>{{ item.service_type }}</td><td>{{ item.provider }}</td><td>{{ item.is_enabled }}</td>
          <td class="ops"><button class="btn btn-ghost btn-xs" @click="pickService(item)">编辑</button><button class="btn btn-ghost btn-xs" @click="testService(item.id)">测试</button></td>
        </tr>
      </DataTable>
    </section>
    <aside class="card"><p class="card-desc">本地存储</p></aside>
  </section>

  <section v-if="active === 'adminSystem'" class="page split">
    <section class="card">
      <div class="card-head"><h2 class="card-title">系统参数</h2><button class="btn btn-primary" @click="saveSetting">保存</button></div>
      <input v-model="settingKey" class="input" placeholder="key" />
      <textarea v-model="settingValue" class="textarea" placeholder="value JSON"></textarea>
    </section>
    <aside class="card">
      <div v-for="item in settings" :key="item.id" class="row" @click="pickSetting(item)">
        <span>{{ item.setting_key }}</span><span class="tag">{{ item.category }}</span>
      </div>
    </aside>
  </section>

  <section v-if="active === 'adminMonitor'" class="page">
    <div class="grid stats">
      <StatCard :icon="Users" label="在线" :value="overview.online_users || 0" />
      <StatCard :icon="BarChart2" label="API" :value="overview.api_call_count_30m || 0" />
      <StatCard :icon="Sparkles" label="AI" :value="overview.ai_call_count_30m || 0" />
      <StatCard :icon="XCircle" label="失败" :value="overview.ai_failure_count_30m || 0" danger />
    </div>
    <article class="card"><pre>{{ overview }}</pre></article>
  </section>

  <section v-if="active === 'adminLogs'" class="page">
    <div class="toolbar">
      <select v-model="logType" class="select short"><option value="login">登录</option><option value="operations">操作</option><option value="errors">错误</option></select>
      <input v-model.number="logLimit" class="input tiny" type="number" />
      <input v-model.number="logFilter.user_id" class="input tiny" type="number" placeholder="用户" />
      <input v-model="logFilter.action" class="input short" placeholder="动作" />
      <input v-model="logFilter.target_type" class="input short" placeholder="对象" />
      <input v-model="logFilter.level" class="input short" placeholder="级别" />
      <input v-model="logFilter.source" class="input short" placeholder="来源" />
      <input v-model="logFilter.start_at" class="input date" type="datetime-local" />
      <input v-model="logFilter.end_at" class="input date" type="datetime-local" />
      <button class="btn btn-secondary" @click="loadLogs">查看</button>
    </div>
    <DataTable :headers="['时间','类型','内容']">
      <tr v-for="item in logs" :key="item.id">
        <td>{{ item.created_at }}</td><td>{{ item.action || item.level || item.email }}</td><td><pre>{{ item }}</pre></td>
      </tr>
    </DataTable>
  </section>

  <section v-if="active === 'adminBackups'" class="page">
    <div class="toolbar"><button class="btn btn-primary" @click="createBackup">备份</button></div>
    <DataTable :headers="['文件','状态','时间','操作']">
      <tr v-for="item in backups" :key="item.id">
        <td>{{ item.file_path || item.backup_name }}</td><td>{{ item.status }}</td><td>{{ item.created_at }}</td>
        <td class="ops"><button class="btn btn-ghost btn-xs" @click="restoreBackup(item.id)">恢复</button><button class="btn btn-ghost btn-xs" @click="deleteBackup(item.id)">删除</button></td>
      </tr>
    </DataTable>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";
import { BarChart2, CheckCircle, Sparkles, Upload, Users, XCircle } from "lucide-vue-next";
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
const logFilter = reactive({ user_id: null as number | null, action: "", target_type: "", level: "", source: "", start_at: "", end_at: "" });

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
  if (logType.value === "login") return { ...base, user_id: logFilter.user_id };
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
onMounted(loadActive);
</script>

<style scoped>
.short { max-width: 220px; }
.tiny { max-width: 96px; }
.date { max-width: 180px; }
.mini { max-width: 72px; height: 28px; }
.ops { white-space: nowrap; }
.detail-card { margin-top: var(--space-4); }
.check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
pre {
  max-width: 520px;
  overflow: auto;
  margin: 0;
  font-family: var(--font-family-mono);
  font-size: var(--text-caption);
  white-space: pre-wrap;
}
</style>
