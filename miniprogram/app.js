const auth = require('./utils/auth');

App({
  globalData: {
    user: null,
    // 课时学习 / 作答页跨页传参缓冲
    transfer: {}
  },

  onLaunch() {
    // 启动时恢复登录态
    const user = auth.getUser();
    if (user) {
      // 管理员仅限网页端管理后台，禁止进入小程序：清除历史遗留的管理员会话
      if (user.role === 'admin') {
        this.clearSession();
      } else {
        this.globalData.user = user;
      }
    }
    // 新版本就绪后提示重启，避免用户长期停留在旧缓存版本
    if (wx.getUpdateManager) {
      const updateManager = wx.getUpdateManager();
      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本已准备好，是否重启应用？',
          success(res) {
            if (res.confirm) updateManager.applyUpdate();
          }
        });
      });
    }
  },

  // 设置/清除会话
  setSession(token, user) {
    auth.setToken(token);
    auth.setUser(user);
    this.globalData.user = user;
  },

  clearSession() {
    auth.clear();
    this.globalData.user = null;
  }
});
