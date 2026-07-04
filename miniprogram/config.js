// 全局配置：后端接口地址
// 开发：微信开发者工具勾选「不校验合法域名」即可使用本机后端
// 生产：替换为已在小程序后台配置 request 合法域名的 https 地址
const ENV = {
  // 本地开发后端
  dev: 'http://127.0.0.1:8000/api/v1',
  // 生产环境（部署后替换为真实 https 域名）
  prod: 'https://api.example.com/api/v1'
};

// 按小程序运行环境自动选择：仅开发者工具的开发版走 dev（本机后端），
// 体验版跑在真机上（127.0.0.1 是手机自己且 http 配不了合法域名），和正式版一样走 prod。
function resolveApiBase() {
  try {
    const info = wx.getAccountInfoSync();
    const envVersion = info && info.miniProgram && info.miniProgram.envVersion;
    if (envVersion === 'develop') return ENV.dev;
  } catch (e) {
    // 取不到环境信息时按生产处理
  }
  return ENV.prod;
}

module.exports = {
  API_BASE: resolveApiBase(),
  // 本地存储 key
  TOKEN_KEY: 'class_agent_token',
  USER_KEY: 'class_agent_user'
};
