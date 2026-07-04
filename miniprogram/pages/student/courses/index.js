const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

Page({
  data: {
    loading: true,
    error: false,
    courses: [],
    filtered: [],
    keyword: '',
    filter: 'all', // all | active | done
    // 加入课程
    joinOpen: false,
    joinCode: '',
    joinChecking: false,
    joinError: '',
    joinPreview: null,
    joining: false
  },

  onShow() {
    tabbar.setTab(this, 1);
    this.load();
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh());
  },

  async load() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      this.setData({ courses, loading: false, error: false });
      this.applyFilter();
    } catch (err) {
      // 首次加载失败时展示错误占位，与"还没有加入课程"空态区分
      this.setData({ loading: false, error: !this.data.courses.length });
      toast.error(err.message);
    }
  },

  // 错误占位"重新加载"
  retryLoad() {
    this.setData({ loading: true, error: false });
    this.load();
  },

  onShareAppMessage() {
    return { title: '智学黑板 · 我的课程', path: '/pages/student/courses/index' };
  },

  onSearch(e) {
    this.setData({ keyword: e.detail.value });
    this.applyFilter();
  },

  setFilter(e) {
    this.setData({ filter: e.currentTarget.dataset.filter });
    this.applyFilter();
  },

  applyFilter() {
    const { courses, keyword, filter } = this.data;
    const kw = keyword.trim();
    const filtered = courses.filter((c) => {
      if (kw && c.name.indexOf(kw) < 0) return false;
      if (filter === 'active' && c.progress_percent >= 100) return false;
      if (filter === 'done' && c.progress_percent < 100) return false;
      return true;
    });
    this.setData({ filtered });
  },

  openCourse(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/student-course/course-home/index?courseId=' + id });
  },

  goQa(e) {
    const id = e.currentTarget.dataset.id;
    getApp().globalData.transfer.qaCourseId = id;
    wx.switchTab({ url: '/pages/student/qa/index' });
  },

  // ===== 加入课程 =====
  openJoin() {
    this.setData({ joinOpen: true, joinCode: '', joinError: '', joinPreview: null });
  },
  closeJoin() {
    this.setData({ joinOpen: false });
  },
  onJoinInput(e) {
    this.setData({ joinCode: (e.detail.value || '').toUpperCase(), joinError: '', joinPreview: null });
  },
  async validateCode() {
    const code = this.data.joinCode.trim();
    if (!code) return this.setData({ joinError: '请输入课程码' });
    this.setData({ joinChecking: true, joinError: '' });
    try {
      const data = await api.get('/student/courses/preview', { course_code: code });
      if (data && data.already_joined) {
        this.setData({ joinPreview: data, joinError: '你已加入该课程' });
      } else {
        this.setData({ joinPreview: data, joinError: '' });
      }
    } catch (err) {
      this.setData({ joinError: err.message || '课程码不存在或已停用', joinPreview: null });
    } finally {
      this.setData({ joinChecking: false });
    }
  },
  async confirmJoin() {
    if (this.data.joining) return;
    if (!this.data.joinPreview || this.data.joinPreview.already_joined) return;
    this.setData({ joining: true });
    try {
      await api.post('/courses/join', { course_code: this.data.joinCode.trim() });
      toast.success('已加入课程');
      this.setData({ joinOpen: false });
      this.load();
    } catch (err) {
      this.setData({ joinError: err.message });
    } finally {
      this.setData({ joining: false });
    }
  },

  async leaveCourse(e) {
    const id = e.currentTarget.dataset.id;
    const ok = await toast.confirm({ title: '退出课程', content: '退出后将无法查看课程内容，确定退出？', confirmText: '退出', danger: true });
    if (!ok) return;
    try {
      await api.post('/courses/' + id + '/leave');
      toast.success('已退出');
      this.load();
    } catch (err) {
      toast.error(err.message);
    }
  },

  copyCode(e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.code });
  }
});
