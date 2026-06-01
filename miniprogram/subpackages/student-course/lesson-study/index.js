const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    lessonId: 0,
    courseId: 0,
    loading: true,
    lesson: null,
    pages: [],
    current: 0, // index
    navTop: 60,
    statusBar: 20,
    // 字幕
    subtitleMode: 'full', // full | keyword | hidden
    // 抽屉
    drawerOpen: false,
    drawerTab: 'script', // script | activity | qa | note
    // 缩略图
    thumbOpen: false,
    // 笔记
    note: '',
    noteState: '已保存',
    // 抽屉问答
    qaInput: '',
    qaMessages: [],
    qaSending: false,
    // 完成卡
    completeOpen: false,
    studyMinutes: 0,
    // 计时
    elapsed: 0
  },

  onLoad(query) {
    const sys = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const statusBar = sys.statusBarHeight || 20;
    this.setData({
      lessonId: Number(query.lessonId || 0),
      courseId: Number(query.courseId || 0),
      statusBar,
      navTop: statusBar + 8
    });
    this.load();
    // 学习计时
    this._timer = setInterval(() => {
      this.data.elapsed += 1;
      if (this.data.elapsed % 30 === 0) this.saveProgress(false, true);
    }, 1000);
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer);
    this.saveProgress(false, true);
  },

  async load() {
    try {
      const detail = (await api.get('/lessons/' + this.data.lessonId)) || {};
      const pages = detail.pages || [];
      let current = 0;
      try {
        const progress = await api.get('/lessons/' + this.data.lessonId + '/progress');
        if (progress && progress.current_page) current = Math.max(0, Math.min(pages.length - 1, progress.current_page - 1));
      } catch (e) { /* 无进度 */ }
      this.setData({ lesson: detail.lesson, pages, current, loading: false });
      this.loadNote();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  back() { wx.navigateBack(); },

  // ===== 翻页 =====
  onSwiperChange(e) {
    const current = e.detail.current;
    if (current === this.data.current) return;
    this.setData({ current, qaMessages: [] });
    this.loadNote();
    this.saveProgress(false, true);
  },
  prevPage() {
    if (this.data.current > 0) this.setData({ current: this.data.current - 1 });
  },
  nextPage() {
    if (this.data.current < this.data.pages.length - 1) {
      this.setData({ current: this.data.current + 1 });
    } else {
      this.finish();
    }
  },

  cycleSubtitle() {
    const order = ['full', 'keyword', 'hidden'];
    const idx = order.indexOf(this.data.subtitleMode);
    this.setData({ subtitleMode: order[(idx + 1) % order.length] });
  },

  // ===== 进度 =====
  async saveProgress(completed, silent) {
    if (!this.data.lesson) return;
    try {
      await api.post('/lessons/' + this.data.lessonId + '/progress', {
        current_page: this.data.current + 1,
        added_seconds: 30,
        completed: !!completed
      });
      if (!silent) toast.success('已保存');
    } catch (e) { /* 静默 */ }
  },

  finish() {
    this.saveProgress(true, true);
    this.setData({ completeOpen: true, studyMinutes: Math.max(1, Math.round(this.data.elapsed / 60)) });
  },
  closeComplete() { this.setData({ completeOpen: false }); },
  backToCourse() { wx.navigateBack(); },
  goPractice() {
    wx.redirectTo({ url: '/subpackages/student-learning/quizzes/index?courseId=' + this.data.courseId });
  },

  // ===== 抽屉 =====
  openDrawer(e) {
    const tab = (e.currentTarget.dataset.tab) || 'script';
    this.setData({ drawerOpen: true, drawerTab: tab });
  },
  closeDrawer() { this.setData({ drawerOpen: false }); },
  switchDrawerTab(e) { this.setData({ drawerTab: e.currentTarget.dataset.tab }); },

  // ===== 缩略图 =====
  toggleThumb() { this.setData({ thumbOpen: !this.data.thumbOpen }); },
  jumpPage(e) {
    this.setData({ current: e.currentTarget.dataset.index, thumbOpen: false });
    this.loadNote();
  },

  // ===== 笔记 =====
  curPage() { return this.data.pages[this.data.current]; },
  async loadNote() {
    const page = this.curPage();
    if (!page) return;
    try {
      const note = await api.get('/student/pages/' + page.id + '/note');
      this.setData({ note: (note && note.content) || '', noteState: '已保存' });
    } catch (e) {
      this.setData({ note: '', noteState: '已保存' });
    }
  },
  onNoteInput(e) {
    this.setData({ note: e.detail.value, noteState: '未保存' });
    if (this._noteTimer) clearTimeout(this._noteTimer);
    this._noteTimer = setTimeout(() => this.saveNote(), 1200);
  },
  async saveNote() {
    const page = this.curPage();
    if (!page) return;
    this.setData({ noteState: '保存中' });
    try {
      await api.put('/student/pages/' + page.id + '/note', { content: this.data.note });
      this.setData({ noteState: '已保存' });
    } catch (e) {
      this.setData({ noteState: '保存失败' });
    }
  },

  // ===== 抽屉内问答 =====
  onQaInput(e) { this.setData({ qaInput: e.detail.value }); },
  async sendPageQa() {
    const q = this.data.qaInput.trim();
    if (!q || this.data.qaSending) return;
    const page = this.curPage();
    const msgs = this.data.qaMessages.concat([{ role: 'user', text: q }, { role: 'ai', text: '', pending: true }]);
    const aiIdx = msgs.length - 1;
    this.setData({ qaMessages: msgs, qaInput: '', qaSending: true });
    try {
      const data = await api.post('/qa/ask', {
        course_id: this.data.courseId || (this.data.lesson && this.data.lesson.course_id),
        question: q,
        lesson_page_id: page && page.id
      });
      const next = this.data.qaMessages.slice();
      next[aiIdx] = { role: 'ai', text: data.answer || '（无回答）', pending: false };
      this.setData({ qaMessages: next, qaSending: false });
    } catch (err) {
      const next = this.data.qaMessages.slice();
      next[aiIdx] = { role: 'ai', text: '回答失败：' + err.message, pending: false, error: true };
      this.setData({ qaMessages: next, qaSending: false });
    }
  }
});
