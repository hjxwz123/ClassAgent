const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const tabbar = require('../../../utils/tabbar');
const auth = require('../../../utils/auth');

Page({
  data: {
    loading: true,
    greeting: '',
    nickname: '',
    dashboard: null,
    statsView: [],
    continueProgress: 0,
    todayTotal: 0,
    todayDone: 0,
    weakPoints: []
  },

  onLoad() {
    if (!auth.isLoggedIn()) {
      wx.reLaunch({ url: '/pages/auth/index' });
      return;
    }
    const user = auth.getUser() || {};
    this.setData({ greeting: fmt.greeting(), nickname: user.nickname || '同学' });
    this.load();
  },

  onShow() {
    tabbar.setTab(this, 0);
  },

  onPullDownRefresh() {
    this.load(true).then(() => wx.stopPullDownRefresh());
  },

  async load(refresh) {
    this.setData({ loading: !refresh ? true : this.data.loading });
    try {
      const d = await api.get('/student/dashboard');
      const stats = d.stats || {};
      const statsView = [
        { label: '本周学习', value: stats.study_hours || 0, unit: 'h' },
        { label: '完成率', value: fmt.percent(stats.completion_rate), unit: '%' },
        { label: '正确率', value: fmt.percent(stats.accuracy), unit: '%' }
      ];
      const cont = d.continue_learning;
      const continueProgress = cont && cont.progress ? fmt.percent((cont.progress.current_page || 0) / Math.max(1, (cont.lesson && cont.lesson.page_count) || 1)) : 0;
      const tasks = d.today_tasks || [];
      const todayDone = tasks.filter((t) => t.status === 'done').length;
      const rec = d.recommendation || {};
      this.setData({
        dashboard: d,
        statsView,
        continueProgress,
        todayTotal: tasks.length,
        todayDone,
        weakPoints: (rec.weak_points || []).slice(0, 4),
        loading: false
      });
    } catch (err) {
      this.setData({ loading: false });
      require('../../../utils/toast').error(err.message);
    }
  },

  goCourses() { wx.switchTab({ url: '/pages/student/courses/index' }); },
  goQa() { wx.switchTab({ url: '/pages/student/qa/index' }); },
  goPlans() { wx.navigateTo({ url: '/subpackages/student-learning/plans/index' }); },

  continueLearning() {
    const cont = this.data.dashboard && this.data.dashboard.continue_learning;
    if (!cont || !cont.lesson) return this.goCourses();
    getApp().globalData.transfer.lesson = { lessonId: cont.lesson.id, courseId: cont.course && cont.course.id };
    wx.navigateTo({ url: '/subpackages/student-course/lesson-study/index?lessonId=' + cont.lesson.id });
  },

  openCourse(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/student-course/course-home/index?courseId=' + id });
  },

  openRecommendLesson() {
    const rec = this.data.dashboard && this.data.dashboard.recommendation;
    if (rec && rec.lesson && rec.lesson.lesson) {
      wx.navigateTo({ url: '/subpackages/student-course/lesson-study/index?lessonId=' + rec.lesson.lesson.id });
    } else {
      this.goCourses();
    }
  }
});
