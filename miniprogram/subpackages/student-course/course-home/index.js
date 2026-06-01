const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    courseId: 0,
    loading: true,
    home: null,
    lessonsShown: [],
    expandLessons: false
  },

  onLoad(query) {
    const courseId = Number(query.courseId || 0);
    this.setData({ courseId });
    this.load();
  },

  async load() {
    try {
      const home = (await api.get('/student/courses/' + this.data.courseId + '/home')) || {};
      const lessons = home.lessons || [];
      this.setData({
        home,
        lessonsShown: lessons.slice(0, 5),
        loading: false
      });
      wx.setNavigationBarTitle({ title: (home.course && home.course.name) || '课程主页' });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  toggleLessons() {
    const lessons = this.data.home.lessons || [];
    const expandLessons = !this.data.expandLessons;
    this.setData({ expandLessons, lessonsShown: expandLessons ? lessons : lessons.slice(0, 5) });
  },

  openLesson(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/student-course/lesson-study/index?lessonId=' + id + '&courseId=' + this.data.courseId });
  },

  // 快捷入口
  goLessons() {
    const first = (this.data.home.lessons || [])[0];
    if (first) this.openLesson({ currentTarget: { dataset: { id: first.id } } });
    else toast.info('课程暂无课时');
  },
  goQa() {
    getApp().globalData.transfer.qaCourseId = this.data.courseId;
    wx.switchTab({ url: '/pages/student/qa/index' });
  },
  goMaterials() {
    wx.navigateTo({ url: '/subpackages/student-course/materials/index?courseId=' + this.data.courseId });
  },
  goQuizzes() {
    wx.navigateTo({ url: '/subpackages/student-learning/quizzes/index?courseId=' + this.data.courseId });
  },
  goKnowledge() {
    wx.navigateTo({ url: '/subpackages/student-learning/knowledge/index?courseId=' + this.data.courseId });
  }
});
