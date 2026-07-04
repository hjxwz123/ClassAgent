const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    courseId: 0,
    loading: true,
    error: '',
    home: null,
    lessonsShown: [],
    expandLessons: false
  },

  onLoad(query) {
    const courseId = Number(query.courseId || 0);
    this.setData({ courseId });
    this.load();
  },

  onShow() {
    // 从课时学习等页面返回时静默刷新（5s 节流，首次由 onLoad 加载）
    if (this._lastLoadTs && Date.now() - this._lastLoadTs > 5000) this.load(true);
  },

  onPullDownRefresh() {
    this.load(true).finally(() => wx.stopPullDownRefresh());
  },

  async load(silent) {
    // 注意：bindtap 重试会把事件对象传进来，只有显式 true 才是静默刷新
    silent = silent === true;
    if (!silent) this.setData({ loading: true, error: '' });
    try {
      const home = (await api.get('/student/courses/' + this.data.courseId + '/home')) || {};
      const lessons = home.lessons || [];
      this._lastLoadTs = Date.now();
      this.setData({
        home,
        lessonsShown: this.data.expandLessons ? lessons : lessons.slice(0, 5),
        loading: false,
        error: ''
      });
      wx.setNavigationBarTitle({ title: (home.course && home.course.name) || '课程主页' });
    } catch (err) {
      if (silent) return; // 静默刷新失败不打扰，保留旧数据
      this.setData({ loading: false, error: err.message || '加载失败' });
    }
  },

  onShareAppMessage() {
    const name = (this.data.home && this.data.home.course && this.data.home.course.name) || '课程';
    return {
      title: name + ' · 课程主页',
      path: '/subpackages/student-course/course-home/index?courseId=' + this.data.courseId
    };
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
    const lessons = (this.data.home && this.data.home.lessons) || [];
    // 优先进入第一个未学完的课时，全部学完则打开第一课
    const target = lessons.find((l) => (l.progress_percent || 0) < 100) || lessons[0];
    if (target) this.openLesson({ currentTarget: { dataset: { id: target.id } } });
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
