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
    analysis: null,
    metrics: [],
    lessonBars: [],
    layers: []
  },

  onShow() {
    tabbar.setTab(this, 3);
    if (!this.data.courses.length) this.loadCourses();
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  async loadCourses() {
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      const courseId = (courses[0] && courses[0].id) || 0;
      this.setData({ courses, courseId, courseName: courses[0] ? courses[0].name : '选择课程' });
      if (courseId) this.load(); else this.setData({ loading: false });
    } catch (err) { this.setData({ loading: false }); toast.error(err.message); }
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
    this.setData({ loading: true });
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
      const maxRate = Math.max(1, ...lessons.map((l) => fmt.percent(l.completion_rate || l.progress_percent || 0)));
      const lessonBars = lessons.slice(0, 8).map((l) => {
        const v = fmt.percent(l.completion_rate || l.progress_percent || 0);
        return { title: l.title, value: v, width: Math.round(v / maxRate * 100) };
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
      this.setData({ loading: false });
      toast.error(err.message);
    }
  }
});
