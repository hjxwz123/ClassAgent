const api = require('../../../utils/api');
const toast = require('../../../utils/toast');
const gen = require('../../../utils/generation');

const LEVELS = [
  { value: 'beginner', label: '入门' },
  { value: 'standard', label: '标准' },
  { value: 'advanced', label: '进阶' }
];

Page({
  data: {
    courseId: 0,
    loading: true,
    error: false,
    chapters: [],
    chapterId: 0,
    keyword: '',
    points: [],
    filtered: [],
    weakPoints: [],
    selected: null,
    levels: LEVELS,
    level: 'standard',
    content: {},
    generating: false,
    // 出题进度浮层
    genShow: false,
    genTitle: 'AI 出题',
    genStatus: 'processing',
    genStep: 'preparing'
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.init();
  },

  onUnload() { gen.stopProgress(this); },

  async init() {
    try {
      const [detail, weak] = await Promise.all([
        api.get('/courses/' + this.data.courseId).catch(() => null),
        api.get('/learning/weak-points', { course_id: this.data.courseId }).catch(() => [])
      ]);
      this.setData({ chapters: (detail && detail.chapters) || [], weakPoints: weak || [] });
      this.loadPoints();
    } catch (err) {
      this.setData({ loading: false, error: true });
      toast.error(err.message);
    }
  },

  async loadPoints() {
    this.setData({ loading: true, error: false });
    try {
      const points = (await api.get('/learning/knowledge-points', { course_id: this.data.courseId, chapter_id: this.data.chapterId || undefined })) || [];
      this.setData({ points, loading: false });
      this.applyFilter();
      if (points[0]) this.select({ currentTarget: { dataset: { id: points[0].id } } });
      else this.setData({ selected: null });
    } catch (err) {
      // 加载失败与"暂无知识点"区分，展示错误占位并允许重试
      this.setData({ loading: false, error: true });
      toast.error(err.message);
    }
  },

  onShareAppMessage() {
    return {
      title: '知识点精讲',
      path: '/subpackages/student-learning/knowledge/index?courseId=' + this.data.courseId
    };
  },

  selectChapter(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({ chapterId: this.data.chapterId === id ? 0 : id });
    this.loadPoints();
  },
  onSearch(e) { this.setData({ keyword: e.detail.value }); this.applyFilter(); },
  applyFilter() {
    const kw = this.data.keyword.trim();
    const filtered = this.data.points.filter((p) => !kw || (p.name || '').indexOf(kw) >= 0);
    this.setData({ filtered });
  },

  select(e) {
    const id = e.currentTarget.dataset.id;
    const found = this.data.points.find((p) => p.id === id);
    // WXML 不能调用 Page 方法，所属章节名在这里算好挂到 selected 上
    const selected = found ? Object.assign({}, found, { chapterName: this.chapterName(found.chapter_id) }) : null;
    this.setData({ selected });
    this.refreshContent();
  },
  setLevel(e) { this.setData({ level: e.currentTarget.dataset.level }); this.refreshContent(); },
  refreshContent() {
    const s = this.data.selected;
    const content = (s && s.content_by_level && s.content_by_level[this.data.level]) || {};
    this.setData({ content });
  },

  chapterName(id) {
    const c = this.data.chapters.find((x) => x.id === id);
    return c ? c.title : '未分组';
  },

  async generate(e) {
    const count = Number(e.currentTarget.dataset.count);
    if (!this.data.selected) return;
    if (this.data.generating) return;
    const selected = this.data.selected;
    const title = selected.name + ' 练习';
    this.setData({ generating: true });
    const res = await gen.submit(this, {
      title,
      request: () => api.postLong('/learning/quizzes/generate', {
        course_id: this.data.courseId,
        chapter_id: selected.chapter_id || undefined,
        knowledge_point_ids: [selected.id],
        title,
        quiz_type: 'practice',
        question_count: count
      }),
      onReady: (quizId) => wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + quizId })
    });
    this.setData({ generating: false });
    if (res.status === 'ready') toast.success('练习已生成');
    else if (res.status === 'error') toast.error(res.error.message);
    else if (res.status === 'failed') toast.error('AI 出题失败，请稍后重试');
    else if (res.status === 'timeout') toast.info('出题仍在后台进行，稍后可在练习页查看');
    else if (res.status === 'queued') toast.info('练习已加入生成队列，完成后可在练习页查看');
  },

  dismissGen() { gen.dismissProgress(this); }
});
