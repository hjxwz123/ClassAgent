const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

const COUNTS = [5, 10, 15];

Page({
  data: {
    courseId: 0,
    loading: true,
    tab: 'quiz', // quiz | practice
    quizzes: [],
    chapters: [],
    wrongCount: 0,
    // 章节练习配置
    selectedChapters: [],
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
      this.setData({ loading: false });
      toast.error(err.message);
    }
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

  openQuiz(e) {
    const id = e.currentTarget.dataset.id;
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

  // 章节练习
  toggleChapter(e) {
    const id = e.currentTarget.dataset.id;
    const sel = this.data.selectedChapters.slice();
    const idx = sel.indexOf(id);
    if (idx >= 0) sel.splice(idx, 1); else sel.push(id);
    this.setData({ selectedChapters: sel });
  },
  setCount(e) { this.setData({ count: e.currentTarget.dataset.count }); },
  toggleWeak(e) { this.setData({ preferWeak: e.detail.value }); },

  async generate() {
    this.setData({ generating: true });
    try {
      const chapterId = this.data.selectedChapters[0] || undefined;
      const quiz = await api.post('/learning/quizzes/generate', {
        course_id: this.data.courseId,
        chapter_id: chapterId,
        title: '章节练习',
        quiz_type: 'practice',
        question_count: this.data.count,
        prefer_weak: this.data.preferWeak
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
    wx.navigateBack({ delta: 1, fail() { wx.switchTab({ url: '/pages/student/wrong-book/index' }); } });
    wx.switchTab({ url: '/pages/student/wrong-book/index' });
  }
});
