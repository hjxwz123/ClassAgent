const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const gen = require('../../../utils/generation');

// 与网页端 useStudentQuiz.ts 对齐的出题选项
const COUNTS = [5, 10, 15, 20];
const TYPES = [
  { value: 'single_choice', label: '单选' },
  { value: 'multiple_choice', label: '多选' },
  { value: 'judge', label: '判断' },
  { value: 'blank', label: '填空' },
  { value: 'short_answer', label: '简答' }
];
const DIFFICULTIES = [
  { value: 'mixed', label: '混合' },
  { value: 'easy', label: '基础' },
  { value: 'standard', label: '标准' },
  { value: 'hard', label: '较难' }
];

Page({
  data: {
    courseId: 0,
    loading: true,
    error: false,
    tab: 'quiz', // quiz | practice
    quizzes: [],
    chapters: [],
    wrongCount: 0,
    // 章节练习配置（对齐网页端）
    counts: COUNTS,
    count: 10,
    selectedChapters: [], // 多选章节 id
    chapterSel: {}, // { [id]: true } 供 WXML 判选中
    types: TYPES,
    selectedTypes: ['single_choice', 'judge'],
    typeSel: { single_choice: true, judge: true },
    difficulties: DIFFICULTIES,
    difficulty: 'mixed',
    preferWeak: true,
    showCustom: false,
    customText: '',
    generating: false,
    // 出题进度浮层
    genShow: false,
    genTitle: 'AI 出题',
    genStatus: 'processing',
    genStep: 'preparing'
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },

  onShow() {
    // 从作答返回时刷新
    if (this._loaded) this.loadQuizzes();
  },

  onUnload() {
    gen.stopProgress(this);
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

  // 章节多选（对齐网页 selectedPracticeChapters）
  toggleChapter(e) {
    const id = e.currentTarget.dataset.id;
    const set = Object.assign({}, this.data.chapterSel);
    if (set[id]) delete set[id]; else set[id] = true;
    const selectedChapters = this.data.chapters.filter((c) => set[c.id]).map((c) => c.id);
    this.setData({ chapterSel: set, selectedChapters });
  },
  setCount(e) { this.setData({ count: e.currentTarget.dataset.count }); },
  // 题型多选（至少保留一种），对齐网页 toggleQuizType
  toggleType(e) {
    const value = e.currentTarget.dataset.value;
    const set = Object.assign({}, this.data.typeSel);
    if (set[value]) {
      if (this.data.selectedTypes.length <= 1) return; // 至少保留一种题型
      delete set[value];
    } else {
      set[value] = true;
    }
    const selectedTypes = TYPES.filter((t) => set[t.value]).map((t) => t.value);
    this.setData({ typeSel: set, selectedTypes });
  },
  setDifficulty(e) { this.setData({ difficulty: e.currentTarget.dataset.value }); },
  toggleWeak(e) { this.setData({ preferWeak: e.detail.value }); },
  toggleCustom() { this.setData({ showCustom: !this.data.showCustom }); },
  onCustomInput(e) { this.setData({ customText: e.detail.value }); },

  // 把所选题型均分到总题量（余数给靠前题型），转成后端 question_type_counts（对齐网页 quizTypeCounts）
  buildTypeCounts(total) {
    const types = this.data.selectedTypes;
    if (!types.length) return undefined;
    const base = Math.floor(total / types.length);
    const remainder = total % types.length;
    const counts = {};
    types.forEach((type, index) => {
      const value = base + (index < remainder ? 1 : 0);
      if (value > 0) counts[type] = value;
    });
    return Object.keys(counts).length ? counts : undefined;
  },

  // 章节范围 + 出题模式的卷名（对齐网页 practiceQuizTitle）：
  // 单章「函数 · 章节练习」；多章「第一章 等3章 · 薄弱点强化」；无章「全课程 · 章节练习」
  practiceTitle(chapterIds) {
    const chapters = this.data.chapters.filter((c) => chapterIds.indexOf(c.id) >= 0);
    const scope = chapters.length === 1
      ? chapters[0].title
      : (chapters.length > 1 ? (chapters[0].title + ' 等' + chapters.length + '章') : '全课程');
    return scope + ' · ' + (this.data.preferWeak ? '薄弱点强化' : '章节练习');
  },

  async generate() {
    if (this.data.generating) return;
    const chapterIds = this.data.selectedChapters.slice();
    const total = this.data.count;
    const title = this.practiceTitle(chapterIds);
    const custom = this.data.customText.trim();
    this.setData({ generating: true });
    const res = await gen.submit(this, {
      title,
      request: () => api.postLong('/learning/quizzes/generate', {
        course_id: this.data.courseId,
        chapter_id: chapterIds.length === 1 ? chapterIds[0] : undefined,
        chapter_ids: chapterIds,
        title,
        quiz_type: 'practice',
        question_count: total,
        question_type_counts: this.buildTypeCounts(total),
        // 后端字段名是 prefer_weak_points；旧名 prefer_weak 会被 pydantic 静默忽略。
        prefer_weak_points: this.data.preferWeak,
        difficulty: this.data.difficulty || 'mixed',
        custom_instructions: custom || undefined
      }),
      onReady: (quizId) => wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + quizId })
    });
    this.setData({ generating: false });
    if (res.status === 'ready') { toast.success('练习已生成'); this.loadQuizzes(); }
    else if (res.status === 'error') toast.error(res.error.message);
    else if (res.status === 'failed') toast.error('AI 出题失败，请稍后重试');
    else if (res.status === 'timeout') { toast.info('出题仍在后台进行，完成后可在列表查看'); this.loadQuizzes(); }
    else if (res.status === 'queued') { toast.info('练习已加入生成队列，完成后可在列表查看'); this.loadQuizzes(); }
  },

  dismissGen() { gen.dismissProgress(this); },

  retryWrong() {
    if (!this.data.wrongCount) return toast.info('暂无待重练错题');
    // 错题本是 tabBar 页，直接 switchTab，避免同 tick 连发多个导航 API
    wx.switchTab({ url: '/pages/student/wrong-book/index' });
  }
});
