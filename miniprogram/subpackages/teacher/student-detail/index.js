const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

Page({
  data: {
    courseId: 0,
    studentId: 0,
    loading: true,
    detail: null,
    student: null,
    lessonProgress: [],
    qaRecords: [],
    weakPoints: [],
    stats: {}
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0), studentId: Number(query.studentId || 0) });
    this.load();
  },

  async load() {
    try {
      const d = await api.get('/teacher/courses/' + this.data.courseId + '/students/' + this.data.studentId);
      const lessonProgress = (d.lesson_progress || []).map((lp) => Object.assign({}, lp, {
        lastText: lp.last_study_at ? fmt.relativeTime(lp.last_study_at) : '未学习'
      }));
      const student = d.student ? Object.assign({}, d.student, { avatar_url: api.mediaUrl(d.student.avatar_url) }) : null;
      this.setData({
        detail: d,
        student,
        lessonProgress,
        qaRecords: d.qa_records || [],
        weakPoints: d.weak_points || [],
        stats: d.stats || {},
        loading: false
      });
      if (d.student) wx.setNavigationBarTitle({ title: d.student.nickname });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  async remind() {
    const ok = await toast.confirm({ title: '发送提醒', content: '向该学生发送学习提醒？', confirmText: '发送' });
    if (!ok) return;
    try {
      await api.post('/teacher/courses/' + this.data.courseId + '/students/' + this.data.studentId + '/remind', {
        title: '学习提醒',
        message: '同学，记得继续完成课程学习哦～'
      });
      toast.success('已发送提醒');
    } catch (err) { toast.error(err.message); }
  }
});
