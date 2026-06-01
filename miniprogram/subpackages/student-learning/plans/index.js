const api = require('../../../utils/api');
const toast = require('../../../utils/toast');

function ymd(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

Page({
  data: {
    courses: [],
    courseId: 0,
    loading: true,
    plans: [],
    plan: null,
    tasks: [],
    todayTasks: [],
    today: '',
    monthLabel: '',
    calendar: [],
    weekDays: ['日', '一', '二', '三', '四', '五', '六'],
    stats: { monthCheckin: 0, total: 0, done: 0 },
    // 生成
    genOpen: false,
    form: { goal: '', daily_minutes: 30, available_days: 7 },
    generating: false
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0), today: ymd(new Date()) });
    this.loadCourses();
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      const courseId = this.data.courseId || (courses[0] && courses[0].id) || 0;
      this.setData({ courses, courseId });
      this.load();
    } catch (err) { toast.error(err.message); this.setData({ loading: false }); }
  },

  async load() {
    this.setData({ loading: true });
    try {
      const plans = (await api.get('/learning/plans', { course_id: this.data.courseId || undefined })) || [];
      const plan = plans[0] || null;
      let tasks = [];
      if (plan) tasks = (await api.get('/learning/plans/' + plan.id + '/tasks')) || [];
      this.setData({ plans, plan, tasks });
      this.buildView();
      this.setData({ loading: false });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  buildView() {
    const today = this.data.today;
    const todayTasks = this.data.tasks.filter((t) => t.task_date === today);
    // 完成日期集合
    const doneDates = {};
    this.data.tasks.forEach((t) => { if (t.status === 'done') doneDates[t.task_date] = true; });
    const taskDates = {};
    this.data.tasks.forEach((t) => { taskDates[t.task_date] = true; });
    // 当月日历
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const first = new Date(year, month, 1);
    const startWeekday = first.getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push({ blank: true, key: 'b' + i });
    let monthCheckin = 0;
    for (let d = 1; d <= daysInMonth; d++) {
      const ds = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      const done = !!doneDates[ds];
      if (done) monthCheckin++;
      cells.push({ key: 'd' + d, day: d, date: ds, done, hasTask: !!taskDates[ds], isToday: ds === today });
    }
    const done = this.data.tasks.filter((t) => t.status === 'done').length;
    this.setData({
      todayTasks,
      calendar: cells,
      monthLabel: year + ' 年 ' + (month + 1) + ' 月',
      stats: { monthCheckin, total: this.data.tasks.length, done }
    });
  },

  async checkin(e) {
    const id = e.currentTarget.dataset.id;
    try {
      await api.post('/learning/tasks/' + id + '/checkin', { notes: '' });
      wx.vibrateShort && wx.vibrateShort({ type: 'light' });
      toast.success('已打卡');
      // 本地标记
      const tasks = this.data.tasks.map((t) => t.id === id ? Object.assign({}, t, { status: 'done' }) : t);
      this.setData({ tasks });
      this.buildView();
    } catch (err) { toast.error(err.message); }
  },

  // 生成计划
  openGen() { this.setData({ genOpen: true }); },
  closeGen() { this.setData({ genOpen: false }); },
  onGoal(e) { this.setData({ ['form.goal']: e.detail.value }); },
  onMinutes(e) { this.setData({ ['form.daily_minutes']: Number(e.detail.value) }); },
  onDays(e) { this.setData({ ['form.available_days']: Number(e.detail.value) }); },
  async generate() {
    if (!this.data.form.goal.trim()) return toast.info('请输入学习目标');
    if (!this.data.courseId) return toast.info('请选择课程');
    this.setData({ generating: true });
    try {
      await api.post('/learning/plans', {
        course_id: this.data.courseId,
        title: '学习计划',
        goal: this.data.form.goal,
        available_days: this.data.form.available_days,
        daily_minutes: this.data.form.daily_minutes
      });
      toast.success('计划已生成');
      this.setData({ genOpen: false });
      this.load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ generating: false });
    }
  }
});
