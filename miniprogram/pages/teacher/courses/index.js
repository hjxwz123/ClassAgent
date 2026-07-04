const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

Page({
  data: {
    loading: true,
    error: '',
    courses: [],
    filtered: [],
    keyword: '',
    status: 'all' // all | active | inactive
  },

  onShow() {
    tabbar.setTab(this, 1);
    this.load();
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  async load() {
    // 列表为空时（首次/失败重试）显示骨架屏，避免重试期间落入"暂无课程"假空态
    this.setData({ error: '', loading: !this.data.courses.length });
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      this.setData({ courses: courses.map((c) => Object.assign({}, c, { rate: fmt.percent(c.published_rate) })), loading: false });
      this.applyFilter();
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
  },

  onSearch(e) { this.setData({ keyword: e.detail.value }); this.applyFilter(); },
  setStatus(e) { this.setData({ status: e.currentTarget.dataset.status }); this.applyFilter(); },
  clearFilter() { this.setData({ keyword: '', status: 'all' }); this.applyFilter(); },
  applyFilter() {
    const { courses, keyword, status } = this.data;
    const kw = keyword.trim();
    const filtered = courses.filter((c) => {
      if (kw && c.name.indexOf(kw) < 0) return false;
      if (status === 'active' && c.status !== 'active') return false;
      if (status === 'inactive' && c.status === 'active') return false;
      return true;
    });
    this.setData({ filtered });
  },

  openCourse(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/teacher/course-home/index?courseId=' + id });
  },
  copyCode(e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.code });
  },

  async toggleStatus(e) {
    const { id, status } = e.currentTarget.dataset;
    const activating = status !== 'active';
    const ok = await toast.confirm({
      title: activating ? '上架课程' : '下架课程',
      content: activating ? '上架后学生可加入并学习，确定上架？' : '下架后学生将无法访问课程内容，确定下架？',
      confirmText: activating ? '上架' : '下架',
      danger: !activating
    });
    if (!ok) return;
    try {
      await api.post('/courses/' + id + '/' + (activating ? 'activate' : 'deactivate'));
      toast.success(activating ? '课程已上架' : '课程已下架');
      this.load();
    } catch (err) { toast.error(err.message); }
  },

  onShareAppMessage() {
    return { title: '我的教学课程', path: '/pages/teacher/courses/index' };
  }
});
