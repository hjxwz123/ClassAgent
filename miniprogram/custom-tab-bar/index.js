const auth = require('../utils/auth');

const STUDENT_TABS = [
  { path: '/pages/student/home/index', text: '首页', icon: 'home' },
  { path: '/pages/student/courses/index', text: '课程', icon: 'list' },
  { path: '/pages/student/qa/index', text: 'AI 问答', icon: 'spark', center: true },
  { path: '/pages/student/wrong-book/index', text: '错题本', icon: 'cross' },
  { path: '/pages/student/profile/index', text: '我的', icon: 'user' }
];

const TEACHER_TABS = [
  { path: '/pages/teacher/home/index', text: '工作台', icon: 'dashboard' },
  { path: '/pages/teacher/courses/index', text: '课程', icon: 'list' },
  { path: '/pages/teacher/students/index', text: '学生', icon: 'user' },
  { path: '/pages/teacher/analytics/index', text: '分析', icon: 'chart' },
  { path: '/pages/teacher/profile/index', text: '我的', icon: 'menu' }
];

Component({
  data: {
    selected: 0,
    role: 'student',
    list: STUDENT_TABS,
    activeColor: '#00b8d4'
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
      const activeColor = role === 'teacher' ? '#d94925' : '#00b8d4';
      this.setData({ role, list, activeColor });
    },
    onTap(e) {
      const idx = e.currentTarget.dataset.index;
      const item = this.data.list[idx];
      if (!item) return;
      wx.switchTab({ url: item.path });
    }
  }
});
