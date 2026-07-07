<template>
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
              <div
                class="cal-day"
                :class="{ 'cal-empty': cell.empty, checked: cell.checked, today: cell.today }"
              >
                {{ cell.label }}
              </div>
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
              <button type="button" class="plan-task-check" :disabled="task.status === 'done'" @click="checkinTask(task)">
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

<script setup lang="ts">
// 学习计划 & 打卡页。原为 StudentView 内联区块，抽为独立页面组件。
// 共享的统计/今日任务/打卡日/成就负载/计划表单与加载器经 useStudentCtx 注入；
// 本页自持日历游标（planCalendarDate）与本地图表/日历派生态。
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../../../api/client";
import { Award, BarChart2, CalendarCheck, Check, ChevronLeft, ChevronRight, Flame, ListChecks, Sparkles } from "../../../icons";
import { EmptyState } from "../components/primitives";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 共享态经 ctx 注入：stats/todayTasks/doneTasks/checkinDays/profilePayload 为外壳持有的 ref，
// planForm 为外壳持有的 reactive（AI 计划弹窗与本页共用），createPlan/loadPlans/loadDashboard 为外壳函数。
const { selectedCourseId, stats, todayTasks, doneTasks, checkinDays, profilePayload, planForm, planCreating, createPlan } = ctx;

// 日历游标：仅本页使用，切换展示月份。
const planCalendarDate = ref(new Date());

// 本地日期键（yyyy-mm-dd，按本地时区），用于把打卡日与日历格对齐。
function localDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// #33：后端 stats 目前只返回当前连续天数(streak_days)，没有“历史最长连续”字段。
// 仅当后端补上 longest_streak 才显示真实值，否则返回 null 由模板渲染占位符，不再把当前连续天数冒充成最长。
const longestStreakDays = computed<number | null>(() => {
  const raw = (stats.value as any).longest_streak ?? (stats.value as any).longest_streak_days;
  return raw === undefined || raw === null ? null : Number(raw);
});
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

function shiftPlanMonth(offset: number) {
  const current = planCalendarDate.value;
  planCalendarDate.value = new Date(current.getFullYear(), current.getMonth() + offset, 1);
}
async function checkinTask(task: any) {
  if (task?.status === "done") return; // 已完成不重复打卡（按钮也已 disabled）。
  const ok = await ctx.run(() => api.post(`/learning/tasks/${task.id}/checkin`, { notes: "" }), "已打卡");
  if (ok !== null) { await ctx.loadDashboard(); await ctx.loadPlans(); }
}

// 换课重拉计划/任务/打卡日（原 StudentView 在 watch(selectedCourseId) 与 loadActive 里对本页的加载）。
watch(selectedCourseId, () => { void ctx.loadPlans(); });
onMounted(() => { void ctx.loadPlans(); });
</script>
