const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

const COUNTS = [5, 10, 15];

Page({
  data: {
    courseId: 0,
    loading: true,
    error: false,
    tab: 'quiz', // quiz | practice
    quizzes: [],
    chapters: [],
    wrongCount: 0,
    // 章节练习配置（单选）
    selectedChapter: 0,
    counts: COUNTS,
    count: 5,
    preferWeak: true,
    generating: false
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },

  onShow() {
    // 从作答返回时刷新
    if (this._loaded) this.loadQuizzes();
  },

  async load() {
    this._loaded = true;
    this.setData({ loading: true, error: false });
    try {
      const [quizzes, detail, wrongs] = await Promise.all([
        api.get('/learning/quizzes', { course_id: this.data.courseId }),
        api.get('/courses/' + this.data.courseId).catch(() => null),
        api.get('/learning/wrong-questions', { course_id: this.data.courseId }).catch(() => [])
      ]);
      this.setData({
        quizzes: this.decorate(quizzes || []),
        chapters: (detail && detail.chapters) || [],
        wrongCount: (wrongs || []).filter((w) => !w.is_resolved).length,
        loading: false
      });
    } catch (err) {
      // 加载失败与真空态区分，展示错误占位并允许重试
      this.setData({ loading: false, error: true });
      toast.error(err.message);
    }
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh());
  },

  onShareAppMessage() {
    return {
      title: '练习与测验',
      path: '/subpackages/student-learning/quizzes/index?courseId=' + this.data.courseId
    };
  },

  async loadQuizzes() {
    try {
      const quizzes = await api.get('/learning/quizzes', { course_id: this.data.courseId });
      this.setData({ quizzes: this.decorate(quizzes || []) });
    } catch (e) { /* ignore */ }
  },

  decorate(list) {
    return list.map((q) => {
      const a = q.latest_attempt;
      return Object.assign({}, q, {
        scoreText: a ? (Math.round(a.score) + '/' + Math.round(a.total_score || q.total_score)) : '',
        attempted: !!q.has_attempted
      });
    });
  },

  switchTab(e) { this.setData({ tab: e.currentTarget.dataset.tab }); },

  async openQuiz(e) {
    const id = e.currentTarget.dataset.id;
    const quiz = this.data.quizzes.find((item) => item.id === id);
    // 后端一卷只允许一次作答："再次作答"必须先克隆新卷，否则答完整卷交卷才被 400 拒绝、作答全丢。
    if (quiz && quiz.attempted) {
      if (this.data.retaking) return;
      this.setData({ retaking: true });
      try {
        const clone = await api.post('/learning/quizzes/' + id + '/retake', { mode: 'full' });
        if (clone && clone.id) {
          wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + clone.id });
        } else {
          toast.error('创建重做练习失败，请稍后重试');
        }
      } catch (err) {
        toast.error(err.message);
      } finally {
        this.setData({ retaking: false });
      }
      return;
    }
    wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + id });
  },
  viewResult(e) {
    const q = this.data.quizzes.find((item) => item.id === e.currentTarget.dataset.id);
    if (q && q.latest_attempt) {
      wx.navigateTo({ url: '/subpackages/student-learning/quiz-result/index?attemptId=' + q.latest_attempt.id });
    } else {
      this.openQuiz(e);
    }
  },

  // 章节练习（后端仅支持单章节，UI 单选：再次点击取消选中）
  toggleChapter(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({ selectedChapter: this.data.selectedChapter === id ? 0 : id });
  },
  setCount(e) { this.setData({ count: e.currentTarget.dataset.count }); },
  toggleWeak(e) { this.setData({ preferWeak: e.detail.value }); },

  async generate() {
    if (this.data.generating) return;
    this.setData({ generating: true });
    try {
      const chapterId = this.data.selectedChapter || undefined;
      const quiz = await api.postLong('/learning/quizzes/generate', {
        course_id: this.data.courseId,
        chapter_id: chapterId,
        title: '章节练习',
        quiz_type: 'practice',
        question_count: this.data.count,
        // 后端字段名是 prefer_weak_points；旧名 prefer_weak 会被 pydantic 静默忽略，开关等于摆设。
        prefer_weak_points: this.data.preferWeak
      });
      if (quiz && quiz.id) {
        toast.success('练习已生成');
        wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + quiz.id });
      } else {
        toast.info('练习已加入生成队列，完成后会通知你');
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ generating: false });
    }
  },

  retryWrong() {
    if (!this.data.wrongCount) return toast.info('暂无待重练错题');
    // 错题本是 tabBar 页，直接 switchTab，避免同 tick 连发多个导航 API
    wx.switchTab({ url: '/pages/student/wrong-book/index' });
  }
});
