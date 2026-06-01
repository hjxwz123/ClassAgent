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
      this.globalData.user = user;
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
