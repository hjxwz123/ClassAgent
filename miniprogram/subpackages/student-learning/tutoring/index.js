const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

const STEPS = [
  { level: 1, name: '第一步 · 提示', hint: '点拨方向' },
  { level: 2, name: '第二步 · 思路', hint: '解题思路' },
  { level: 3, name: '第三步 · 详解', hint: '完整解答' }
];

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    mode: 'text', // text | image
    text: '',
    submitting: false,
    problem: null,
    steps: STEPS,
    guidance: {}, // level -> content
    openLevel: { 1: false, 2: false, 3: false },
    loadingLevel: 0,
    history: []
  },

  onLoad(query) {
    const courseId = Number(query.courseId || 0);
    if (courseId) this.setData({ courseId });
    this.loadCourses();
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      let courseId = this.data.courseId || (courses[0] && courses[0].id) || 0;
      const course = courses.find((c) => c.id === courseId);
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
      this.loadHistory();
    } catch (err) { toast.error(err.message); }
  },

  toggleCoursePicker() { this.setData({ coursePickerOpen: !this.data.coursePickerOpen }); },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    const course = this.data.courses.find((c) => c.id === id);
    this.setData({ courseId: id, courseName: course ? course.name : '', coursePickerOpen: false });
    this.loadHistory();
  },

  setMode(e) { this.setData({ mode: e.currentTarget.dataset.mode }); },
  onText(e) { this.setData({ text: e.detail.value }); },

  async submitText() {
    const text = this.data.text.trim();
    if (text.length < 2) return toast.info('请输入题目');
    if (!this.data.courseId) return toast.info('请先选择课程');
    this.setData({ submitting: true });
    try {
      const problem = await api.post('/tutoring/problems/text', { course_id: this.data.courseId, text });
      this.applyProblem(problem);
      toast.success('已提交');
    } catch (err) { toast.error(err.message); }
    finally { this.setData({ submitting: false }); }
  },

  async chooseImage() {
    if (!this.data.courseId) return toast.info('请先选择课程');
    try {
      const res = await wx.chooseMedia({ count: 1, mediaType: ['image'], sizeType: ['compressed'], sourceType: ['album', 'camera'] });
      toast.loading('识别中');
      const problem = await api.upload('/tutoring/problems/image', res.tempFiles[0].tempFilePath, { formData: { course_id: this.data.courseId } });
      this.applyProblem(problem);
      toast.hideLoading();
      toast.success('已识别');
    } catch (err) {
      toast.hideLoading();
      if (err && err.message) toast.error(err.message);
    }
  },

  applyProblem(problem) {
    this.setData({
      problem,
      guidance: {},
      openLevel: { 1: false, 2: false, 3: false }
    });
    // 自动展开第一步
    this.loadGuidance({ currentTarget: { dataset: { level: 1 } } });
    this.loadHistory();
  },

  async loadGuidance(e) {
    const level = Number(e.currentTarget.dataset.level);
    if (!this.data.problem) return;
    // 已加载则切换展开
    if (this.data.guidance[level] !== undefined) {
      this.setData({ ['openLevel.' + level]: !this.data.openLevel[level] });
      return;
    }
    this.setData({ loadingLevel: level });
    try {
      const g = await api.get('/tutoring/problems/' + this.data.problem.id + '/guidance', { level });
      this.setData({ ['guidance.' + level]: (g && g.content) || '暂无内容', ['openLevel.' + level]: true });
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ loadingLevel: 0 });
    }
  },

  async loadHistory() {
    if (!this.data.courseId) return;
    try {
      const history = (await api.get('/tutoring/history', { course_id: this.data.courseId })) || [];
      this.setData({ history });
    } catch (e) { /* ignore */ }
  },
  openHistory(e) {
    const item = this.data.history.find((h) => h.id === e.currentTarget.dataset.id);
    if (item) this.applyProblem(item);
    wx.pageScrollTo({ scrollTop: 0, duration: 200 });
  }
});
