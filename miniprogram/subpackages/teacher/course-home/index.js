const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    courseId: 0,
    loading: true,
    home: null
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },

  async load() {
    try {
      const home = (await api.get('/teacher/courses/' + this.data.courseId + '/home')) || {};
      this.setData({ home, loading: false });
      const name = (home.course && (home.course.name || (home.course.course && home.course.course.name)));
      if (name) wx.setNavigationBarTitle({ title: name });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  goStudents() {
    getApp().globalData.transfer.teacherCourseId = this.data.courseId;
    wx.switchTab({ url: '/pages/teacher/students/index' });
  },
  goAnalytics() {
    wx.switchTab({ url: '/pages/teacher/analytics/index' });
  },
  copyCode() {
    const c = this.data.home.course || {};
    const code = c.course_code || (c.course && c.course.course_code);
    if (code) { wx.setClipboardData({ data: code }); }
  }
});
