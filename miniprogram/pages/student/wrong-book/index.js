const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

// 触底分批渲染的每批条数
const PAGE_SIZE = 20;

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    loading: true,
    filtered: [],
    weakPoints: [],
    keyword: '',
    status: 'all', // all | pending | resolved
    stats: { total: 0, pending: 0, repeat: 0, week: 0 },
    generating: false
  },

  onShow() {
    tabbar.setTab(this, 3);
    if (!this.data.courses.length) this.loadCourses();
  },
  onPullDownRefresh() {
    // 课程列表为空时先补拉课程（loadCourses 内会连带刷错题），否则直接刷新错题
    const task = this.data.courses.length ? this.load() : this.loadCourses();
    task.then(() => wx.stopPullDownRefresh());
  },

  // 触底追加渲染下一批错题（全量在 this._all，data 只放已渲染部分）
  onReachBottom() {
    const all = this._all || [];
    const shown = this.data.filtered.length;
    if (shown >= all.length) return;
    const patch = {};
    all.slice(shown, shown + PAGE_SIZE).forEach((item, i) => {
      patch['filtered[' + (shown + i) + ']'] = item;
    });
    this.setData(patch);
  },

  onShareAppMessage() {
    return { title: '智学黑板 · 错题本', path: '/pages/student/wrong-book/index' };
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      const courseId = (courses[0] && courses[0].id) || 0;
      this.setData({ courses, courseId, courseName: courses[0] ? courses[0].name : '选择课程' });
      if (courseId) {
        await this.load();
      } else {
        // 没有任何课程时关闭骨架屏，走"先加入课程"空态
        this.setData({ loading: false });
      }
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  goCourses() { wx.switchTab({ url: '/pages/student/courses/index' }); },

  toggleCoursePicker() { this.setData({ coursePickerOpen: !this.data.coursePickerOpen }); },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    const course = this.data.courses.find((c) => c.id === id);
    this.setData({ courseId: id, courseName: course ? course.name : '', coursePickerOpen: false });
    this.load();
  },

  async load() {
    if (!this.data.courseId) return;
    this.setData({ loading: true });
    try {
      const [wrongs, weak] = await Promise.all([
        api.get('/learning/wrong-questions', { course_id: this.data.courseId }),
        api.get('/learning/weak-points', { course_id: this.data.courseId })
      ]);
      const list = (wrongs || []).map((w) => Object.assign({}, w, { expanded: false }));
      const now = Date.now();
      const week = list.filter((w) => w.last_wrong_at && (now - new Date(String(w.last_wrong_at).replace(/-/g, '/').replace('T', ' ')).getTime()) < 7 * 864e5).length;
      const stats = {
        total: list.length,
        pending: list.filter((w) => !w.is_resolved).length,
        repeat: list.filter((w) => w.wrong_count > 1).length,
        week
      };
      this._wrongs = list;
      this.setData({ weakPoints: weak || [], stats, loading: false });
      this.applyFilter();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  onSearch(e) { this.setData({ keyword: e.detail.value }); this.applyFilter(); },
  setStatus(e) { this.setData({ status: e.currentTarget.dataset.status }); this.applyFilter(); },

  applyFilter() {
    const { keyword, status } = this.data;
    const kw = keyword.trim();
    // 全量筛选结果放内存，data 只渲染首批，触底再分批追加
    this._all = (this._wrongs || []).filter((w) => {
      if (status === 'pending' && w.is_resolved) return false;
      if (status === 'resolved' && !w.is_resolved) return false;
      if (kw && (w.question.stem || '').indexOf(kw) < 0) return false;
      return true;
    });
    this.setData({ filtered: this._all.slice(0, PAGE_SIZE) });
  },

  toggleExpand(e) {
    const idx = e.currentTarget.dataset.index;
    const item = this.data.filtered[idx];
    if (!item) return;
    const expanded = !item.expanded;
    if (this._all && this._all[idx]) this._all[idx].expanded = expanded;
    // 路径 setData 只更新单条，避免整列表重渲染
    this.setData({ ['filtered[' + idx + '].expanded']: expanded });
  },

  async startPractice() {
    if (!(this._wrongs || []).length) return toast.info('本课程暂无错题');
    this.setData({ generating: true });
    try {
      const quiz = await api.post('/learning/wrong-questions/practice', undefined, { course_id: this.data.courseId });
      if (quiz && quiz.id) {
        toast.success('已生成重练');
        getApp().globalData.transfer.quiz = quiz;
        wx.navigateTo({ url: '/subpackages/student-learning/quiz-answer/index?quizId=' + quiz.id });
      } else {
        toast.info('错题重练已加入生成队列，完成后会通知你');
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ generating: false });
    }
  }
});
