const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');
const auth = require('../../../utils/auth');

Page({
  data: {
    loading: true,
    profile: null,
    overview: [],
    achievements: [],
    tab: 'info', // info | archive | account
    form: { nickname: '', avatar_url: '', school: '', bio: '' },
    saving: false,
    notices: [],
    // 改密
    pwdOpen: false,
    pwd: { old_password: '', new_password: '', confirm: '' },
    submitting: false
  },

  onShow() {
    tabbar.setTab(this, 4);
    this.load();
  },
  onPullDownRefresh() { this.load().then(() => wx.stopPullDownRefresh()); },

  async load() {
    try {
      const data = (await api.get('/student/profile')) || {};
      const s = data.stats || {};
      const overview = [
        { label: '总学习时长', value: s.study_hours || 0, unit: 'h' },
        { label: '完成率', value: fmt.percent(s.completion_rate), unit: '%' },
        { label: '知识问答', value: s.qa_count || 0, unit: '' },
        { label: '正确率', value: fmt.percent(s.accuracy), unit: '%' }
      ];
      const patch = {
        profile: data,
        overview,
        achievements: data.achievements || [],
        notices: (data.notification_settings || []).filter((n) => n.key !== 'plan'),
        loading: false
      };
      // 表单有未保存修改时不覆盖，避免 onShow 刷新丢掉输入
      if (!this._dirty) {
        patch.form = {
          nickname: (data.user && data.user.nickname) || '',
          avatar_url: api.mediaUrl((data.user && data.user.avatar_url) || ''),
          school: (data.student_profile && data.student_profile.school) || '',
          bio: (data.user && data.user.bio) || ''
        };
      }
      this.setData(patch);
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  switchTab(e) { this.setData({ tab: e.currentTarget.dataset.tab }); },
  onForm(e) {
    const field = e.currentTarget.dataset.field;
    this._dirty = true;
    this.setData({ ['form.' + field]: e.detail.value });
  },

  async changeAvatar() {
    let res;
    try {
      res = await wx.chooseMedia({ count: 1, mediaType: ['image'], sizeType: ['compressed'] });
    } catch (e) {
      return; // 用户取消选图
    }
    toast.loading('上传中');
    try {
      const data = await api.upload('/student/profile/avatar', res.tempFiles[0].tempFilePath);
      // 接口返回完整 profile：头像在 data.user.avatar_url
      const url = api.mediaUrl((data && data.user && data.user.avatar_url) || '');
      if (url) {
        this.setData({ ['form.avatar_url']: url, ['profile.user.avatar_url']: url });
        const user = auth.getUser() || {};
        user.avatar_url = url;
        auth.setUser(user);
      }
      // 先收起 loading 再弹成功提示，避免 hideLoading 把 toast 一起关掉
      toast.hideLoading();
      toast.success('头像已更新');
    } catch (e) {
      toast.hideLoading();
      if (e && e.message) toast.error(e.message);
    }
  },

  async saveProfile() {
    if (this.data.saving) return;
    this.setData({ saving: true });
    try {
      const data = await api.patch('/student/profile', {
        nickname: this.data.form.nickname,
        avatar_url: this.data.form.avatar_url,
        bio: this.data.form.bio,
        school: this.data.form.school
      });
      toast.success('已保存');
      this._dirty = false;
      if (data && data.user) {
        const user = auth.getUser() || {};
        user.nickname = data.user.nickname;
        auth.setUser(user);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ saving: false });
    }
  },

  toggleNotice(e) {
    const idx = e.currentTarget.dataset.index;
    const notices = this.data.notices.slice();
    notices[idx].enabled = !notices[idx].enabled;
    this.setData({ notices });
    api.put('/student/notifications', { settings: notices.map((n) => ({ key: n.key, enabled: n.enabled })) })
      .then(() => toast.success('已保存'))
      .catch((err) => {
        // 保存失败回滚开关状态，避免界面与服务端不一致
        const rollback = this.data.notices.slice();
        if (rollback[idx]) rollback[idx].enabled = !rollback[idx].enabled;
        this.setData({ notices: rollback });
        toast.error(err.message);
      });
  },

  openPwd() { this.setData({ pwdOpen: true, pwd: { old_password: '', new_password: '', confirm: '' } }); },
  closePwd() { this.setData({ pwdOpen: false }); },
  onPwd(e) { this.setData({ ['pwd.' + e.currentTarget.dataset.field]: e.detail.value }); },
  async submitPwd() {
    if (this.data.submitting) return;
    const { old_password, new_password, confirm } = this.data.pwd;
    if (!new_password || new_password.length < 8) return toast.info('新密码至少 8 位');
    if (new_password !== confirm) return toast.info('两次密码不一致');
    this.setData({ submitting: true });
    try {
      await api.post('/auth/me/password', { old_password, new_password });
      toast.success('密码已修改');
      this.setData({ pwdOpen: false });
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ submitting: false });
    }
  },

  async logout() {
    const ok = await toast.confirm({ title: '退出登录', content: '确定退出当前账号？', confirmText: '退出', danger: true });
    if (!ok) return;
    getApp().clearSession();
    wx.reLaunch({ url: '/pages/auth/index' });
  }
});
