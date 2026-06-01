const auth = require('../utils/auth');

const STUDENT_TABS = [
  { path: '/pages/student/home/index', text: '首页', icon: '⌂' },
  { path: '/pages/student/courses/index', text: '课程', icon: '▤' },
  { path: '/pages/student/qa/index', text: 'AI 问答', icon: '✦', center: true },
  { path: '/pages/student/wrong-book/index', text: '错题本', icon: '✗' },
  { path: '/pages/student/profile/index', text: '我的', icon: '◔' }
];

const TEACHER_TABS = [
  { path: '/pages/teacher/home/index', text: '工作台', icon: '◳' },
  { path: '/pages/teacher/courses/index', text: '课程', icon: '▤' },
  { path: '/pages/teacher/students/index', text: '学生', icon: '◔' },
  { path: '/pages/teacher/analytics/index', text: '分析', icon: '◈' },
  { path: '/pages/teacher/profile/index', text: '我的', icon: '☰' }
];

Component({
  data: {
    selected: 0,
    role: 'student',
    list: STUDENT_TABS
  },
  lifetimes: {
    attached() {
      this.refreshRole();
    }
  },
  pageLifetimes: {
    show() {
      this.refreshRole();
    }
  },
  methods: {
    refreshRole() {
      const role = auth.role() || 'student';
      const list = role === 'teacher' ? TEACHER_TABS : STUDENT_TABS;
      this.setData({ role, list });
    },
    onTap(e) {
      const idx = e.currentTarget.dataset.index;
      const item = this.data.list[idx];
      if (!item) return;
      wx.switchTab({ url: item.path });
    }
  }
});
