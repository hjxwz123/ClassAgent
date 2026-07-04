// 统一的 Toast / 确认弹窗封装
const auth = require('./auth');

function success(text) {
  const title = text || '已完成';
  // 带图标的 toast 标题超过约 7 个汉字会被截断，长文案自动降级为纯文字
  if (title.length > 7) {
    wx.showToast({ title, icon: 'none', duration: 2000 });
    return;
  }
  wx.showToast({ title, icon: 'success', duration: 1800 });
}

function info(text) {
  wx.showToast({ title: text || '', icon: 'none', duration: 2000 });
}

function error(text) {
  wx.showToast({ title: text || '操作失败', icon: 'none', duration: 2400 });
}

function loading(text) {
  wx.showLoading({ title: text || '加载中', mask: true });
}

function hideLoading() {
  wx.hideLoading();
}

// 二次确认，返回 Promise<boolean>；确认键颜色按当前角色主题（教师红/学生青），danger 恒为警示红
function confirm(options) {
  options = options || {};
  const roleColor = auth.role() === 'teacher' ? '#D94925' : '#00B8D4';
  return new Promise((resolve) => {
    wx.showModal({
      title: options.title || '确认操作',
      content: options.content || '',
      confirmText: options.confirmText || '确认',
      cancelText: options.cancelText || '取消',
      confirmColor: options.danger ? '#C62828' : (options.color || roleColor),
      success(res) { resolve(!!res.confirm); },
      fail() { resolve(false); }
    });
  });
}

module.exports = { success, info, error, loading, hideLoading, confirm };
