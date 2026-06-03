const api = require('../../../utils/api');
const toast = require('../../../utils/toast');

const LEVELS = [
  { value: 'beginner', label: '入门' },
  { value: 'standard', label: '标准' },
  { value: 'advanced', label: '进阶' }
];

Page({
  data: {
    courseId: 0,
    loading: true,
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
    generating: false
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.init();
  },

  async init() {
    try {
      const [detail, weak] = await Promise.all([
        api.get('/courses/' + this.data.courseId).catch(() => null),
        api.get('/learning/weak-points', { course_id: this.data.courseId }).catch(() => [])
      ]);
      this.setData({ chapters: (detail && detail.chapters) || [], weakPoints: weak || [] });
      this.loadPoints();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  async loadPoints() {
    this.setData({ loading: true });
    try {
      const points = (await api.get('/learning/knowledge-points', { course_id: this.data.courseId, chapter_id: this.data.chapterId || undefined })) || [];
      this.setData({ points, loading: false });
      this.applyFilter();
      if (points[0]) this.select({ currentTarget: { dataset: { id: points[0].id } } });
      else this.setData({ selected: null });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
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
    const selected = this.data.points.find((p) => p.id === id);
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
    this.setData({ generating: true });
    try {
      const quiz = await api.post('/learning/quizzes/generate', {
        course_id: this.data.courseId,
        chapter_id: this.data.selected.chapter_id || undefined,
        knowledge_point_ids: [this.data.selected.id],
        title: this.data.selected.name + ' 练习',
        quiz_type: 'practice',
        question_count: count
      });
      if (quiz && quiz.id) {
        toast.success('练习已生成');
        wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + quiz.id });
      } else {
        toast.info('练习已加入生成队列');
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ generating: false });
    }
  }
});
