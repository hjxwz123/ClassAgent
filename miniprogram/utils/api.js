const { API_BASE } = require('../config');
const auth = require('./auth');

// 拼接带 query 的 url
function buildUrl(path, query) {
  let url = API_BASE + path;
  if (query) {
    const parts = [];
    Object.keys(query).forEach((key) => {
      const value = query[key];
      if (value !== undefined && value !== null && value !== '') {
        parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(value));
      }
    });
    if (parts.length) url += (url.indexOf('?') >= 0 ? '&' : '?') + parts.join('&');
  }
  return url;
}

// 将后端 FastAPI 校验错误转换为可读文案（对齐 web 端 client.ts）
function fieldName(loc) {
  const parts = (loc || []).filter((item) => ['body', 'query', 'path'].indexOf(String(item)) < 0);
  return parts.length ? parts.join('.') : '参数';
}

function issueText(issue) {
  const type = String(issue.type || '');
  const ctx = issue.ctx || {};
  if (type.indexOf('missing') >= 0) return '不能为空';
  if (type.indexOf('string_too_short') >= 0) return '至少 ' + (ctx.min_length || 1) + ' 位';
  if (type.indexOf('string_too_long') >= 0) return '最多 ' + (ctx.max_length || '') + ' 位';
  if (type.indexOf('greater_than_equal') >= 0) return '不能小于 ' + (ctx.ge || '');
  if (type.indexOf('less_than_equal') >= 0) return '不能大于 ' + (ctx.le || '');
  if (type.indexOf('int_parsing') >= 0 || type.indexOf('float_parsing') >= 0) return '必须为数字';
  return issue.msg || issue.message || '格式不正确';
}

function errorMessage(payload) {
  if (!payload) return '网络异常，请稍后重试';
  if (Array.isArray(payload.data) && payload.data.length) {
    const details = payload.data.slice(0, 3).map((item) => fieldName(item.loc) + '：' + issueText(item)).join('；');
    const suffix = payload.data.length > 3 ? '；更多参数有误' : '';
    return (payload.message || '请求参数校验失败') + '：' + details + suffix;
  }
  return payload.message || '请求失败';
}

let redirecting = false;
function handleUnauthorized() {
  if (redirecting) return;
  redirecting = true;
  const app = getApp();
  if (app) app.clearSession();
  wx.reLaunch({
    url: '/pages/auth/index',
    complete() { setTimeout(() => { redirecting = false; }, 800); }
  });
}

function request(path, options) {
  options = options || {};
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' };
    const token = auth.getToken();
    if (token) header.Authorization = 'Bearer ' + token;

    wx.request({
      url: buildUrl(path, options.query),
      method: options.method || 'GET',
      data: options.data || {},
      header,
      // AI 生成类接口耗时远超 30s，允许调用方按需放宽
      timeout: options.timeout || 30000,
      success(res) {
        const payload = res.data;
        // 登录/注册等 /auth/ 接口的 401 是"账号密码错误"，不是会话过期：
        // 透传后端文案，不能清会话并 reLaunch（否则登录页输错密码会被整页重载、输入全丢）
        if (res.statusCode === 401 && path.indexOf('/auth/') !== 0) {
          handleUnauthorized();
          reject(new Error('登录已过期，请重新登录'));
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300 && payload && payload.code === 0) {
          resolve(payload.data);
          return;
        }
        reject(new Error(errorMessage(payload)));
      },
      fail(err) {
        const msg = err && err.errMsg && err.errMsg.indexOf('timeout') >= 0
          ? '请求超时，请重试'
          : '网络异常，请检查连接';
        reject(new Error(msg));
      }
    });
  });
}

// 上传文件（图片等），字段名 file
function upload(path, filePath, options) {
  options = options || {};
  return new Promise((resolve, reject) => {
    const header = {};
    const token = auth.getToken();
    if (token) header.Authorization = 'Bearer ' + token;
    wx.uploadFile({
      url: buildUrl(path, options.query),
      filePath,
      name: options.name || 'file',
      formData: options.formData || {},
      header,
      success(res) {
        let payload = null;
        try { payload = JSON.parse(res.data); } catch (e) { payload = null; }
        if (res.statusCode === 401) { handleUnauthorized(); reject(new Error('登录已过期')); return; }
        if (res.statusCode >= 200 && res.statusCode < 300 && payload && payload.code === 0) {
          resolve(payload.data);
          return;
        }
        reject(new Error(errorMessage(payload)));
      },
      fail() { reject(new Error('上传失败，请重试')); }
    });
  });
}

// 把后端返回的相对资源地址（如 /static/xxx）补成绝对地址，
// 否则小程序 <image> / previewImage / downloadFile 无法加载。
function mediaUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  // API_BASE 形如 https://host/api/v1，取其 origin
  const m = API_BASE.match(/^(https?:\/\/[^/]+)/);
  const origin = m ? m[1] : '';
  return origin + (url.charAt(0) === '/' ? url : '/' + url);
}

module.exports = {
  get: (path, query) => request(path, { method: 'GET', query }),
  post: (path, data, query) => request(path, { method: 'POST', data, query }),
  patch: (path, data) => request(path, { method: 'PATCH', data }),
  put: (path, data) => request(path, { method: 'PUT', data }),
  del: (path) => request(path, { method: 'DELETE' }),
  // AI 生成等长耗时请求：默认 300s 超时；query 与 post 对齐，供 /wrong-questions/practice 这类带查询参数的长调用使用
  postLong: (path, data, query, timeout) => request(path, { method: 'POST', data, query, timeout: timeout || 300000 }),
  upload,
  buildUrl,
  mediaUrl,
  handleUnauthorized
};
