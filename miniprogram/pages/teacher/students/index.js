const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    loading: true,
    stats: null,
    students: [],
    filtered: [],
    keyword: '',
    filter: 'all', // all | active | inactive
    // 提醒
    remindOpen: false,
    remindStudent: null,
    remindForm: { title: '', message: '' }
  },

  onShow() {
    tabbar.setTab(this, 2);
    const transfer = getApp().globalData.transfer;
    if (transfer.teacherCourseId) {
      this._pendingCourseId = transfer.teacherCourseId;
      transfer.teacherCourseId = null;
    }
    if (!this.data.courses.length) this.loadCourses();
    else if (this._pendingCourseId) this.applyPendingCourse();
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  applyPendingCourse() {
    const id = this._pendingCourseId;
    this._pendingCourseId = null;
    const course = this.data.courses.find((c) => c.id === id);
    if (course) {
      this.setData({ courseId: id, courseName: course.name });
      this.load();
    }
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      let courseId = this._pendingCourseId || (courses[0] && courses[0].id) || 0;
      this._pendingCourseId = null;
      const course = courses.find((c) => c.id === courseId) || courses[0];
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
      if (courseId) this.load(); else this.setData({ loading: false });
    } catch (err) { this.setData({ loading: false }); toast.error(err.message); }
  },

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
      const data = (await api.get('/teacher/courses/' + this.data.courseId + '/students')) || { stats: {}, items: [] };
      const students = (data.items || []).map((s) => Object.assign({}, s, {
        name: s.student.nickname,
        avatar: api.mediaUrl(s.student.avatar_url),
        no: s.student.student_no,
        lastText: s.last_study_at ? fmt.relativeTime(s.last_study_at) : '从未学习'
      }));
      this.setData({ stats: data.stats || {}, students, loading: false });
      this.applyFilter();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  onSearch(e) { this.setData({ keyword: e.detail.value }); this.applyFilter(); },
  setFilter(e) { this.setData({ filter: e.currentTarget.dataset.filter }); this.applyFilter(); },
  applyFilter() {
    const { students, keyword, filter } = this.data;
    const kw = keyword.trim();
    const filtered = students.filter((s) => {
      if (kw && (s.name || '').indexOf(kw) < 0) return false;
      if (filter === 'active' && !s.last_study_at) return false;
      if (filter === 'inactive' && s.last_study_at) return false;
      return true;
    });
    this.setData({ filtered });
  },

  openDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/teacher/student-detail/index?courseId=' + this.data.courseId + '&studentId=' + id });
  },

  // 提醒
  openRemind(e) {
    const s = this.data.students.find((x) => x.student.id === e.currentTarget.dataset.id);
    this.setData({ remindOpen: true, remindStudent: s, remindForm: { title: '学习提醒', message: '同学，记得继续完成课程学习哦～' } });
  },
  closeRemind() { this.setData({ remindOpen: false }); },
  onRemindTitle(e) { this.setData({ ['remindForm.title']: e.detail.value }); },
  onRemindMsg(e) { this.setData({ ['remindForm.message']: e.detail.value }); },
  async sendRemind() {
    const s = this.data.remindStudent;
    if (!s) return;
    try {
      await api.post('/teacher/courses/' + this.data.courseId + '/students/' + s.student.id + '/remind', this.data.remindForm);
      toast.success('已发送提醒');
      this.setData({ remindOpen: false });
    } catch (err) { toast.error(err.message); }
  }
});
