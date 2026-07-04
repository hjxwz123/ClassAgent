const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const tabbar = require('../../../utils/tabbar');
const toast = require('../../../utils/toast');
const auth = require('../../../utils/auth');

Page({
  data: {
    loading: true,
    error: '',
    nickname: '',
    greeting: '',
    dashboard: null,
    statCards: []
  },

  onLoad() {
    this.load();
  },
  onShow() {
    tabbar.setTab(this, 0);
    // 问候语随时段变化，每次显示时重新计算
    const user = auth.getUser() || {};
    this.setData({ nickname: user.nickname || '老师', greeting: fmt.greeting() });
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  async load() {
    this.setData({ loading: !this.data.dashboard, error: '' });
    try {
      const d = await api.get('/teacher/dashboard');
      const s = d.stats || {};
      const statCards = [
        { label: '我的课程', value: s.course_total || 0 },
        { label: '学生总数', value: s.student_total || 0 },
        { label: '本周提问', value: s.weekly_qa || 0 },
        { label: '待处理', value: s.pending_scripts || 0, warn: (s.pending_scripts || 0) > 0 }
      ];
      this.setData({ dashboard: d, statCards, loading: false });
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
  },

  openCourse(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/teacher/course-home/index?courseId=' + id });
  },
  goCourses() { wx.switchTab({ url: '/pages/teacher/courses/index' }); }
});
