const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

Page({
  data: {
    loading: true,
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
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      this.setData({ courses: courses.map((c) => Object.assign({}, c, { rate: fmt.percent(c.published_rate) })), loading: false });
      this.applyFilter();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  onSearch(e) { this.setData({ keyword: e.detail.value }); this.applyFilter(); },
  setStatus(e) { this.setData({ status: e.currentTarget.dataset.status }); this.applyFilter(); },
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
  }
});
