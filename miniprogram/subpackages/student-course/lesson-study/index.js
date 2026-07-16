const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const md = require('../../../utils/markdown');
const auth = require('../../../utils/auth');
const { API_BASE } = require('../../../config');

// wx.openDocument 支持的原课件格式
const OPENABLE_TYPES = ['pdf', 'ppt', 'pptx', 'doc', 'docx', 'xls', 'xlsx'];

Page({
  data: {
    lessonId: 0,
    courseId: 0,
    loading: true,
    error: '',
    lesson: null,
    pages: [],
    current: 0, // index
    navTop: 60,
    statusBar: 20,
    navRightPx: 12, // 顶栏右侧按钮距屏幕右缘（px），避开胶囊
    // 字幕（默认关闭，需要时点顶栏"字幕"手动开启）
    subtitleMode: 'hidden', // full | hidden
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
    // 顶栏右侧按钮避开胶囊：定位到胶囊左侧留 12px 间距
    let navRightPx = 12;
    try {
      const rect = wx.getMenuButtonBoundingClientRect();
      const winWidth = sys.windowWidth || sys.screenWidth || 375;
      if (rect && rect.left) navRightPx = winWidth - rect.left + 12;
    } catch (e) { /* 忽略，用默认值 */ }
    this.setData({
      lessonId: Number(query.lessonId || 0),
      courseId: Number(query.courseId || 0),
      statusBar,
      navTop: statusBar + 8,
      navRightPx
    });
    this.load();
    // 学习计时
    this._lastReportTs = Date.now();
    this._timer = setInterval(() => {
      this.data.elapsed += 1;
      if (this.data.elapsed % 30 === 0) this.saveProgress(false, true);
    }, 1000);
  },

  onUnload() {
    if (this._timer) clearInterval(this._timer);
    this.flushNote();
    this.saveProgress(false, true);
  },

  async load() {
    this.setData({ loading: true, error: '' });
    try {
      const detail = (await api.get('/lessons/' + this.data.lessonId)) || {};
      // 课件页文本是 Markdown（网页端渲染为幻灯片）：转 rich-text 节点做课件化排版，
      // 不再整屏裸文本；同时剔除 page_text 原文，缩略图只留短摘要，减小 setData 体积
      const pages = (detail.pages || []).map((p) => ({
        id: p.id,
        page_title: p.page_title,
        nodes: md.toNodes(p.page_text || ''),
        thumbText: p.page_title || md.toPlainText(p.page_text || '').slice(0, 60),
        subtitle_text: p.subtitle_text,
        script_text: p.script_text,
        pedagogy: p.pedagogy || []
      }));
      // 原课件文件（PPT/PDF 等）：给"看原件"入口，用微信原生文档预览打开
      const material = detail.material || null;
      const materialOpenable = !!(material && OPENABLE_TYPES.indexOf(String(material.material_type || '').toLowerCase()) >= 0);
      let current = 0;
      try {
        const progress = await api.get('/lessons/' + this.data.lessonId + '/progress');
        if (progress && progress.current_page) current = Math.max(0, Math.min(pages.length - 1, progress.current_page - 1));
      } catch (e) { /* 无进度 */ }
      this._lastPage = current; // 初始页已处理，避免 swiper 初次回调重复副作用
      this._materialId = material ? material.id : 0;
      this.setData({ lesson: detail.lesson, pages, current, materialOpenable, loading: false, error: '' });
      this.loadNote();
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
    }
  },

  // 用微信原生文档预览打开原课件（PPT/PDF/Word 等），临时文件按课时缓存避免重复下载
  openOriginal() {
    if (!this._materialId) return;
    if (this._docPath) {
      wx.openDocument({ filePath: this._docPath, showMenu: true, fail: () => toast.error('暂不支持预览该格式') });
      return;
    }
    const that = this;
    toast.loading('打开课件中');
    wx.downloadFile({
      url: API_BASE + '/materials/' + this._materialId + '/content',
      header: { Authorization: 'Bearer ' + auth.getToken() },
      success(res) {
        toast.hideLoading();
        if (res.statusCode !== 200) { toast.error('课件加载失败'); return; }
        that._docPath = res.tempFilePath;
        wx.openDocument({ filePath: res.tempFilePath, showMenu: true, fail: () => toast.error('暂不支持预览该格式') });
      },
      fail() { toast.hideLoading(); toast.error('课件加载失败'); }
    });
  },

  back() { wx.navigateBack(); },

  // ===== 翻页 =====
  // 统一翻页副作用：flush 旧页笔记、清空页内问答、加载新页笔记、上报进度。
  // swiper bindchange 与按钮 setData 都会走到这里，用 _lastPage 去重避免重复执行。
  onPageChanged(current) {
    if (this._lastPage === current) return;
    this._lastPage = current;
    this.flushNote();
    this.setData({ qaMessages: [] });
    this.loadNote();
    this.saveProgress(false, true);
  },
  onSwiperChange(e) {
    const current = e.detail.current;
    if (current !== this.data.current) this.setData({ current });
    this.onPageChanged(current);
  },
  prevPage() {
    if (this.data.current > 0) {
      const current = this.data.current - 1;
      this.setData({ current });
      this.onPageChanged(current);
    }
  },
  nextPage() {
    if (this.data.current < this.data.pages.length - 1) {
      const current = this.data.current + 1;
      this.setData({ current });
      this.onPageChanged(current);
    } else {
      this.finish();
    }
  },

  toggleSubtitle() {
    // 两态开关：显示 / 隐藏
    const next = this.data.subtitleMode === 'hidden' ? 'full' : 'hidden';
    this.setData({ subtitleMode: next });
    toast.info(next === 'hidden' ? '字幕已隐藏' : '字幕已显示');
  },

  // ===== 进度 =====
  async saveProgress(completed, silent) {
    if (!this.data.lesson) return;
    // 按真实经过时间上报，封顶 30 秒
    const now = Date.now();
    const added = Math.min(30, Math.max(0, Math.round((now - (this._lastReportTs || now)) / 1000)));
    this._lastReportTs = now;
    try {
      await api.post('/lessons/' + this.data.lessonId + '/progress', {
        current_page: this.data.current + 1,
        added_seconds: added,
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
    const current = Number(e.currentTarget.dataset.index);
    this.setData({ current, thumbOpen: false });
    this.onPageChanged(current);
  },

  // ===== 笔记 =====
  curPage() { return this.data.pages[this.data.current]; },
  async loadNote() {
    const page = this.curPage();
    if (!page) return;
    try {
      const note = await api.get('/student/pages/' + page.id + '/note');
      this._notePageId = page.id;
      this._noteDraft = (note && note.content) || '';
      this.setData({ note: this._noteDraft, noteState: '已保存' });
    } catch (e) {
      this._notePageId = page.id;
      this._noteDraft = '';
      this.setData({ note: '', noteState: '已保存' });
    }
  },
  onNoteInput(e) {
    // 快照正在编辑的页面与内容，翻页后仍能保存到正确的页
    this._notePageId = (this.curPage() || {}).id;
    this._noteDraft = e.detail.value;
    this.setData({ note: e.detail.value, noteState: '未保存' });
    if (this._noteTimer) clearTimeout(this._noteTimer);
    this._noteTimer = setTimeout(() => this.saveNote(), 1200);
  },
  async saveNote() {
    this._noteTimer = null;
    const pageId = this._notePageId;
    if (!pageId) return;
    const content = this._noteDraft != null ? this._noteDraft : this.data.note;
    this.setData({ noteState: '保存中' });
    try {
      await api.put('/student/pages/' + pageId + '/note', { content });
      this.setData({ noteState: '已保存' });
    } catch (e) {
      this.setData({ noteState: '保存失败' });
    }
  },
  // 翻页/退出前立即保存尚未落盘的笔记（用编辑时的 pageId 快照）
  flushNote() {
    if (!this._noteTimer) return;
    clearTimeout(this._noteTimer);
    this._noteTimer = null;
    this.saveNote();
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
      // AI 生成耗时较长，用长超时请求
      const data = await api.postLong('/qa/ask', {
        course_id: this.data.courseId || (this.data.lesson && this.data.lesson.course_id),
        question: q,
        lesson_page_id: page && page.id
      });
      const next = this.data.qaMessages.slice();
      next[aiIdx] = { role: 'ai', text: md.toPlainText(data.answer || '') || '（无回答）', pending: false };
      this.setData({ qaMessages: next, qaSending: false });
    } catch (err) {
      const next = this.data.qaMessages.slice();
      next[aiIdx] = { role: 'ai', text: '回答失败：' + err.message, pending: false, error: true };
      // 失败时把问题回填输入框，便于修改后重发
      this.setData({ qaMessages: next, qaSending: false, qaInput: q });
      toast.error('提问失败，已回填问题');
    }
  }
});
