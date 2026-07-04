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
    error: '',
    stats: null,
    filtered: [],
    filtering: false,
    keyword: '',
    filter: 'all', // all | active | inactive
    // 提醒
    remindOpen: false,
    remindStudent: null,
    remindForm: { title: '', message: '' },
    sending: false
  },

  // 全量学生列表仅存实例字段，避免 data 里重复保存两份大数组
  _students: [],

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
  onPullDownRefresh() { this.retryLoad().then(() => wx.stopPullDownRefresh()); },

  // 重试入口：课程列表未加载成功则先拉课程，否则重拉学生数据
  retryLoad() {
    if (!this.data.courses.length) return this.loadCourses();
    return this.load();
  },

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
    this.setData({ loading: true, error: '' });
    try {
      const courses = (await api.get('/teacher/courses')) || [];
      let courseId = this._pendingCourseId || (courses[0] && courses[0].id) || 0;
      this._pendingCourseId = null;
      const course = courses.find((c) => c.id === courseId) || courses[0];
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
      if (courseId) this.load(); else this.setData({ loading: false });
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
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
    this.setData({ loading: true, error: '' });
    try {
      const data = (await api.get('/teacher/courses/' + this.data.courseId + '/students')) || { stats: {}, items: [] };
      this._students = (data.items || []).map((s) => Object.assign({}, s, {
        name: s.student.nickname,
        avatar: api.mediaUrl(s.student.avatar_url),
        no: s.student.student_no,
        lastText: s.last_study_at ? fmt.relativeTime(s.last_study_at) : '从未学习'
      }));
      this.setData({ stats: data.stats || {}, loading: false });
      this.applyFilter();
    } catch (err) {
      this.setData({ loading: false, error: err.message || '加载失败' });
      toast.error(err.message);
    }
  },

  onSearch(e) {
    // keyword 必须走 setData：否则渲染层永远是 ''，"清除筛选"的 setData('') 无 diff，输入框文字清不掉。
    // 短字符串 setData 开销可忽略，重的过滤计算仍做 200ms 防抖
    this.setData({ keyword: e.detail.value });
    if (this._searchTimer) clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => { this.applyFilter(); }, 200);
  },
  setFilter(e) { this.setData({ filter: e.currentTarget.dataset.filter }); this.applyFilter(); },
  clearFilter() { this.setData({ keyword: '', filter: 'all' }); this.applyFilter(); },
  applyFilter() {
    const students = this._students;
    const { keyword, filter } = this.data;
    const kw = keyword.trim();
    const filtered = students.filter((s) => {
      if (kw && (s.name || '').indexOf(kw) < 0) return false;
      if (filter === 'active' && !s.last_study_at) return false;
      if (filter === 'inactive' && s.last_study_at) return false;
      return true;
    });
    // filtering: 有学生但被筛选条件过滤，用于区分空态文案
    this.setData({ filtered, filtering: !!(kw || filter !== 'all') && students.length > 0 });
  },

  openDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/subpackages/teacher/student-detail/index?courseId=' + this.data.courseId + '&studentId=' + id });
  },

  // 复制课程码，引导邀请学生加入
  copyCourseCode() {
    const course = this.data.courses.find((c) => c.id === this.data.courseId);
    if (course && course.course_code) { wx.setClipboardData({ data: course.course_code }); }
  },

  // 提醒
  openRemind(e) {
    const s = this._students.find((x) => x.student.id === e.currentTarget.dataset.id);
    this.setData({ remindOpen: true, remindStudent: s, remindForm: { title: '学习提醒', message: '同学，记得继续完成课程学习哦～' } });
  },
  closeRemind() { this.setData({ remindOpen: false }); },
  onRemindTitle(e) { this.setData({ ['remindForm.title']: e.detail.value }); },
  onRemindMsg(e) { this.setData({ ['remindForm.message']: e.detail.value }); },
  async sendRemind() {
    if (this.data.sending) return;
    const s = this.data.remindStudent;
    if (!s) return;
    if (!(this.data.remindForm.message || '').trim()) return toast.info('请输入提醒内容');
    this.setData({ sending: true });
    try {
      await api.post('/teacher/courses/' + this.data.courseId + '/students/' + s.student.id + '/remind', this.data.remindForm);
      toast.success('已发送提醒');
      this.setData({ remindOpen: false });
    } catch (err) { toast.error(err.message); }
    finally { this.setData({ sending: false }); }
  }
});
