// 全局配置：后端接口地址
// 开发：微信开发者工具勾选「不校验合法域名」即可使用本机后端
// 生产：替换为已在小程序后台配置 request 合法域名的 https 地址
const ENV = {
  // 本地开发后端
  dev: 'http://127.0.0.1:8000/api/v1',
  // 生产环境（部署后替换为真实 https 域名）
  prod: 'https://your-domain.example.com/api/v1'
};

module.exports = {
  // 切换 dev / prod
  API_BASE: ENV.dev,
  // 本地存储 key
  TOKEN_KEY: 'class_agent_token',
  USER_KEY: 'class_agent_user'
};
