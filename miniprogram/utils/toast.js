// 统一的 Toast / 确认弹窗封装

function success(text) {
  wx.showToast({ title: text || '已完成', icon: 'success', duration: 1800 });
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

// 二次确认，返回 Promise<boolean>
function confirm(options) {
  options = options || {};
  return new Promise((resolve) => {
    wx.showModal({
      title: options.title || '确认操作',
      content: options.content || '',
      confirmText: options.confirmText || '确认',
      cancelText: options.cancelText || '取消',
      confirmColor: options.danger ? '#C62828' : '#00B8D4',
      success(res) { resolve(!!res.confirm); },
      fail() { resolve(false); }
    });
  });
}

module.exports = { success, info, error, loading, hideLoading, confirm };
