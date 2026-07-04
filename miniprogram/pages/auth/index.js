const api = require('../../utils/api');
const toast = require('../../utils/toast');

Page({
  data: {
    submitting: false,
    login: { email: '', password: '' },
    errors: {}
  },

  onLoad() {
    // 已登录直接跳转
    const auth = require('../../utils/auth');
    if (auth.isLoggedIn()) {
      this.redirectByRole(auth.role());
    }
  },

  onInput(e) {
    const { group, field } = e.currentTarget.dataset;
    const next = Object.assign({}, this.data[group]);
    next[field] = e.detail.value;
    this.setData({ [group]: next });
  },

  validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  redirectByRole(role) {
    const url = role === 'teacher' ? '/pages/teacher/home/index' : '/pages/student/home/index';
    wx.reLaunch({ url });
  },

  async doLogin() {
    // 防重入：提交中直接忽略重复触发
    if (this.data.submitting) return;
    const { email, password } = this.data.login;
    const errors = {};
    if (!this.validateEmail(email)) errors.email = '请输入有效邮箱';
    if (!password) errors.password = '请输入密码';
    if (Object.keys(errors).length) return this.setData({ errors });
    this.setData({ submitting: true, errors: {} });
    try {
      const data = await api.post('/auth/login', { email, password });
      getApp().setSession(data.access_token, data.user);
      toast.success('欢迎回来');
      setTimeout(() => this.redirectByRole(data.user.role), 400);
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ submitting: false });
    }
  },

  onShareAppMessage() {
    return { title: '智学黑板 · AI 课程学习助手', path: '/pages/auth/index' };
  }
});
