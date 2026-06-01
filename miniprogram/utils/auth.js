const { TOKEN_KEY, USER_KEY } = require('../config');

function getToken() {
  try {
    return wx.getStorageSync(TOKEN_KEY) || '';
  } catch (e) {
    return '';
  }
}

function setToken(token) {
  wx.setStorageSync(TOKEN_KEY, token || '');
}

function getUser() {
  try {
    return wx.getStorageSync(USER_KEY) || null;
  } catch (e) {
    return null;
  }
}

function setUser(user) {
  wx.setStorageSync(USER_KEY, user || null);
}

function clear() {
  wx.removeStorageSync(TOKEN_KEY);
  wx.removeStorageSync(USER_KEY);
}

function isLoggedIn() {
  return !!getToken();
}

function role() {
  const user = getUser();
  return user ? user.role : '';
}

module.exports = { getToken, setToken, getUser, setUser, clear, isLoggedIn, role };
