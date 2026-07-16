const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    courseId: 0,
    loading: true,
    error: '',
    home: null
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  async load() {
    this.setData({ loading: !this.data.home, error: '' });
    try {
      const home = (await api.get('/teacher/courses/' + this.data.courseId + '/home')) || {};
      this.setData({ home, loading: false });
      const name = (home.course && (home.course.name || (home.course.course && home.course.course.name)));
      if (name) wx.setNavigationBarTitle({ title: name });
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
  },

  goStudents() {
    const transfer = getApp().globalData.transfer;
    transfer.teacherCourseId = this.data.courseId;
    transfer.teacherBackCourseId = this.data.courseId; // 标记来自课程主页：目标 tab 页显示返回按钮
    wx.switchTab({ url: '/pages/teacher/students/index' });
  },
  goAnalytics() {
    const transfer = getApp().globalData.transfer;
    transfer.teacherCourseId = this.data.courseId;
    transfer.teacherBackCourseId = this.data.courseId;
    wx.switchTab({ url: '/pages/teacher/analytics/index' });
  },
  // 资料/课时管理暂无移动端页面，给出提示避免"假按钮"
  noticeDesktop() { toast.info('请前往网页端管理'); },
  copyCode() {
    const c = this.data.home.course || {};
    const code = c.course_code || (c.course && c.course.course_code);
    if (code) { wx.setClipboardData({ data: code }); }
  },

  onShareAppMessage() {
    const c = (this.data.home && this.data.home.course) || {};
    return {
      title: c.name || '课程主页',
      path: '/subpackages/teacher/course-home/index?courseId=' + this.data.courseId
    };
  }
});
