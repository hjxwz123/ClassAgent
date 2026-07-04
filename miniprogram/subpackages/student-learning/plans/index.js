const api = require('../../../utils/api');
const toast = require('../../../utils/toast');

function ymd(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    loading: true,
    plans: [],
    plan: null,
    tasks: [],
    todayTasks: [],
    today: '',
    // 月历当前展示的年月（可切换）
    viewYear: 0,
    viewMonth: 0, // 0-11
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
    const now = new Date();
    this.setData({
      courseId: Number(query.courseId || 0),
      today: ymd(now),
      viewYear: now.getFullYear(),
      viewMonth: now.getMonth()
    });
    this.loadCourses();
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      const courseId = this.data.courseId || (courses[0] && courses[0].id) || 0;
      const course = courses.find((c) => c.id === courseId);
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
      this.load();
    } catch (err) { toast.error(err.message); this.setData({ loading: false }); }
  },

  // 课程切换（胶囊 + 底部 sheet）
  toggleCoursePicker() { this.setData({ coursePickerOpen: !this.data.coursePickerOpen }); },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    const course = this.data.courses.find((c) => c.id === id);
    this.setData({ courseId: id, courseName: course ? course.name : '', coursePickerOpen: false });
    this.load();
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh());
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
    // 展示月份的日历（可通过左右箭头切换）
    const year = this.data.viewYear;
    const month = this.data.viewMonth;
    const first = new Date(year, month, 1);
    const startWeekday = first.getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push({ blank: true, key: 'b' + i });
    for (let d = 1; d <= daysInMonth; d++) {
      const ds = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      cells.push({ key: 'd' + d, day: d, date: ds, done: !!doneDates[ds], hasTask: !!taskDates[ds], isToday: ds === today });
    }
    // "本月打卡"始终按真实当前月统计，不随日历翻页变化
    const nowPrefix = today.slice(0, 7);
    let monthCheckin = 0;
    Object.keys(doneDates).forEach((ds) => { if (ds.indexOf(nowPrefix) === 0) monthCheckin++; });
    const done = this.data.tasks.filter((t) => t.status === 'done').length;
    this.setData({
      todayTasks,
      calendar: cells,
      monthLabel: year + ' 年 ' + (month + 1) + ' 月',
      stats: { monthCheckin, total: this.data.tasks.length, done }
    });
  },

  // 月历翻页
  prevMonth() {
    let y = this.data.viewYear;
    let m = this.data.viewMonth - 1;
    if (m < 0) { m = 11; y -= 1; }
    this.setData({ viewYear: y, viewMonth: m });
    this.buildView();
  },
  nextMonth() {
    let y = this.data.viewYear;
    let m = this.data.viewMonth + 1;
    if (m > 11) { m = 0; y += 1; }
    this.setData({ viewYear: y, viewMonth: m });
    this.buildView();
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
    if (this.data.generating) return;
    if (!this.data.form.goal.trim()) return toast.info('请输入学习目标');
    if (!this.data.courseId) return toast.info('请选择课程');
    this.setData({ generating: true });
    try {
      await api.postLong('/learning/plans', {
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
