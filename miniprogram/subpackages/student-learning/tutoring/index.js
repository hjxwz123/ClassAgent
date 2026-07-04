const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const md = require('../../../utils/markdown');

const STEPS = [
  { level: 1, name: '第一步 · 提示', hint: '点拨方向' },
  { level: 2, name: '第二步 · 思路', hint: '解题思路' },
  { level: 3, name: '第三步 · 详解', hint: '完整解答' }
];

// 历史列表分批渲染，每批条数
const HISTORY_PAGE = 15;

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
    // OCR 识别结果确认（可编辑后再开始辅导）
    ocrReview: null, // { id, text, imageUrl }
    confirming: false,
    steps: STEPS,
    guidance: {}, // level -> rich-text nodes（markdown 已转换）
    openLevel: { 1: false, 2: false, 3: false },
    loadingLevel: 0,
    history: [],
    historyHasMore: false
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
    if (this.data.submitting) return;
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
      toast.hideLoading();
      // OCR 结果先给用户确认/修改，确认无误后再开始辅导
      this.setData({
        ocrReview: {
          id: problem.id,
          text: problem.corrected_text || problem.ocr_text || '',
          imageUrl: problem.image_path ? api.mediaUrl(problem.image_path) : ''
        },
        problem: null,
        guidance: {},
        openLevel: { 1: false, 2: false, 3: false }
      });
      toast.success('已识别，请核对题目');
    } catch (err) {
      toast.hideLoading();
      if (err && err.message) toast.error(err.message);
    }
  },

  onOcrText(e) { this.setData({ ['ocrReview.text']: e.detail.value }); },
  previewOcrImage() {
    const url = this.data.ocrReview && this.data.ocrReview.imageUrl;
    if (url) wx.previewImage({ urls: [url], current: url });
  },
  async confirmOcr() {
    if (this.data.confirming) return;
    const review = this.data.ocrReview;
    if (!review) return;
    const text = (review.text || '').trim();
    if (text.length < 2) return toast.info('请补全题目内容');
    this.setData({ confirming: true });
    try {
      const problem = await api.post('/tutoring/problems/' + review.id + '/confirm', { corrected_text: text });
      this.setData({ ocrReview: null });
      this.applyProblem(problem);
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ confirming: false });
    }
  },

  applyProblem(problem) {
    this.setData({
      problem,
      ocrReview: null,
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
      // 辅导内容是 markdown，转成 rich-text nodes 渲染
      this.setData({ ['guidance.' + level]: md.toNodes((g && g.content) || '暂无内容'), ['openLevel.' + level]: true });
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
      // 历史可能很多，全量存内存、首屏只渲染一批，触底再追加
      this._allHistory = history;
      this.setData({ history: history.slice(0, HISTORY_PAGE), historyHasMore: history.length > HISTORY_PAGE });
    } catch (e) { /* ignore */ }
  },
  onReachBottom() {
    const all = this._allHistory || [];
    const shown = this.data.history.length;
    if (shown >= all.length) return;
    const next = shown + HISTORY_PAGE;
    this.setData({ history: all.slice(0, next), historyHasMore: all.length > next });
  },
  onPullDownRefresh() {
    this.loadHistory().finally(() => wx.stopPullDownRefresh());
  },
  openHistory(e) {
    const list = this._allHistory || this.data.history;
    const item = list.find((h) => h.id === e.currentTarget.dataset.id);
    if (item) this.applyProblem(item);
    wx.pageScrollTo({ scrollTop: 0, duration: 200 });
  }
});
