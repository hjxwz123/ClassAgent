const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

const RANGES = [
  { key: 'week', label: '本周', days: 7 },
  { key: 'month', label: '本月', days: 30 },
  { key: 'all', label: '全部', days: 3650 }
];

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    ranges: RANGES,
    range: 'week',
    loading: true,
    error: '',
    analysis: null,
    metrics: [],
    lessonBars: [],
    layers: []
  },

  onShow() {
    tabbar.setTab(this, 3);
    // 承接课程主页跳转指定的课程
    const transfer = getApp().globalData.transfer;
    if (transfer.teacherCourseId) {
      this._pendingCourseId = transfer.teacherCourseId;
      transfer.teacherCourseId = null;
    }
    if (!this.data.courses.length) this.loadCourses();
    else if (this._pendingCourseId) this.applyPendingCourse();
  },
  onPullDownRefresh() { this.retryLoad().then(() => wx.stopPullDownRefresh()); },

  applyPendingCourse() {
    const id = this._pendingCourseId;
    this._pendingCourseId = null;
    const course = this.data.courses.find((c) => c.id === id);
    if (course) {
      this.setData({ courseId: id, courseName: course.name });
      this.load();
    }
  },

  // 重试入口：课程列表未加载成功则先拉课程，否则重拉分析数据
  retryLoad() {
    if (!this.data.courses.length) return this.loadCourses();
    return this.load();
  },

  async loadCourses() {
    // 在途去重：onShow 可能连续触发（首次进入 + 从课程主页跳转），并发请求会互抢 pendingCourseId
    if (this._loadingCourses) return;
    this._loadingCourses = true;
    this.setData({ loading: true, error: '' });
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      let courseId = this._pendingCourseId || 0;
      this._pendingCourseId = null;
      let course = courses.find((c) => c.id === courseId);
      if (!course) { course = courses[0]; courseId = (course && course.id) || 0; }
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
      if (courseId) this.load(); else this.setData({ loading: false });
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    } finally {
      this._loadingCourses = false;
    }
  },

  toggleCoursePicker() { this.setData({ coursePickerOpen: !this.data.coursePickerOpen }); },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    const course = this.data.courses.find((c) => c.id === id);
    this.setData({ courseId: id, courseName: course ? course.name : '', coursePickerOpen: false });
    this.load();
  },
  setRange(e) { this.setData({ range: e.currentTarget.dataset.key }); this.load(); },

  async load() {
    if (!this.data.courseId) return;
    this.setData({ loading: true, error: '' });
    try {
      const days = (RANGES.find((r) => r.key === this.data.range) || RANGES[0]).days;
      const a = await api.get('/teacher/courses/' + this.data.courseId + '/analysis', { days });
      const m = a.metrics || {};
      const metrics = [
        { label: '活跃率', value: fmt.percent(m.active_rate), unit: '%' },
        { label: '完成率', value: fmt.percent(m.completion_rate), unit: '%' },
        { label: '问答总量', value: m.qa_total || 0, unit: '' },
        { label: '平均分', value: Math.round(m.average_score || 0), unit: '' },
        { label: '学习时长', value: m.study_hours || 0, unit: 'h' },
        { label: '薄弱点', value: m.weak_point_count || 0, unit: '' }
      ];
      const lessons = a.lesson_completion || [];
      // 条形宽度直接用绝对百分比，避免相对最大值缩放造成误导
      const lessonBars = lessons.slice(0, 8).map((l) => {
        const v = fmt.percent(l.completion_rate || l.progress_percent || 0);
        return { title: l.title, value: v, width: v };
      });
      const ly = a.student_layers || {};
      const layers = [
        { label: '高活跃', value: ly.high || 0, cls: 'high' },
        { label: '正常', value: ly.normal || 0, cls: 'normal' },
        { label: '低活跃', value: ly.low || 0, cls: 'low' },
        { label: '未活跃', value: ly.inactive || 0, cls: 'inactive' }
      ];
      this.setData({ analysis: a, metrics, lessonBars, layers, loading: false });
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
  }
});
