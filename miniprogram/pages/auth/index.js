const api = require('../../utils/api');
const toast = require('../../utils/toast');

Page({
  data: {
    mode: 'login', // login | register | reset
    submitting: false,
    // 登录
    login: { email: '', password: '' },
    // 注册
    register: { email: '', password: '', nickname: '', student_no: '', employee_no: '', role: 'student' },
    // 找回
    reset: { email: '', code: '', new_password: '' },
    resetRequested: false,
    debugCode: '',
    errors: {}
  },

  onLoad() {
    // 已登录直接跳转
    const auth = require('../../utils/auth');
    if (auth.isLoggedIn()) {
      this.redirectByRole(auth.role());
    }
  },

  switchMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode, errors: {} });
  },

  onInput(e) {
    const { group, field } = e.currentTarget.dataset;
    const next = Object.assign({}, this.data[group]);
    next[field] = e.detail.value;
    this.setData({ [group]: next });
  },

  pickRole(e) {
    const register = Object.assign({}, this.data.register, { role: e.currentTarget.dataset.role });
    this.setData({ register });
  },

  validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  redirectByRole(role) {
    const url = role === 'teacher' ? '/pages/teacher/home/index' : '/pages/student/home/index';
    wx.reLaunch({ url });
  },

  async doLogin() {
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

  async doRegister() {
    const { email, password, nickname, student_no, employee_no, role } = this.data.register;
    const errors = {};
    if (!this.validateEmail(email)) errors.email = '请输入有效邮箱';
    if (!password || password.length < 8) errors.password = '密码至少 8 位';
    if (!nickname || nickname.length < 2) errors.nickname = '昵称至少 2 个字';
    if (Object.keys(errors).length) return this.setData({ errors });
    this.setData({ submitting: true, errors: {} });
    try {
      const payload = { email, password, nickname, role };
      if (role === 'student' && student_no) payload.student_no = student_no;
      if (role === 'teacher' && employee_no) payload.employee_no = employee_no;
      await api.post('/auth/register', payload);
      toast.success('注册成功，请登录');
      this.setData({ mode: 'login', login: { email, password: '' } });
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ submitting: false });
    }
  },

  async requestReset() {
    const { email } = this.data.reset;
    if (!this.validateEmail(email)) return this.setData({ errors: { email: '请输入有效邮箱' } });
    this.setData({ submitting: true, errors: {} });
    try {
      const data = await api.post('/auth/password/reset/request', { email });
      this.setData({ resetRequested: true, debugCode: (data && data.debug_code) || '' });
      toast.info(this.data.debugCode ? '验证码已生成（调试）' : '验证码已发送至邮箱');
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ submitting: false });
    }
  },

  async confirmReset() {
    const { email, code, new_password } = this.data.reset;
    const errors = {};
    if (!code) errors.code = '请输入验证码';
    if (!new_password || new_password.length < 8) errors.new_password = '新密码至少 8 位';
    if (Object.keys(errors).length) return this.setData({ errors });
    this.setData({ submitting: true, errors: {} });
    try {
      await api.post('/auth/password/reset/confirm', { email, code, new_password });
      toast.success('密码已重置，请登录');
      this.setData({ mode: 'login', resetRequested: false, login: { email, password: '' } });
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ submitting: false });
    }
  }
});
