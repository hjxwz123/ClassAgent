// 统一 SVG 图标组件：以 base64 data-URI 渲染，颜色/尺寸由属性传入
// 用法：<icon name="search" size="36rpx" color="#999990" />
// 风格：功能图标用线性描边(line)，状态/装饰图标用实心填充(solid)

function wrap(inner) {
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' + inner + '</svg>';
}
function line(paths, c) {
  return wrap('<g fill="none" stroke="' + c + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + paths + '</g>');
}
function solid(paths, c) {
  return wrap('<g fill="' + c + '">' + paths + '</g>');
}

const ICONS = {
  // ===== 线性（功能） =====
  search: (c) => line('<circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>', c),
  'chevron-down': (c) => line('<polyline points="6 9 12 15 18 9"/>', c),
  'chevron-up': (c) => line('<polyline points="6 15 12 9 18 15"/>', c),
  send: (c) => line('<path d="M21 3 3 10.5l7 2.5 2.5 7L21 3Z"/><path d="M21 3 10 14"/>', c),
  camera: (c) => line('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7l1.5-3h5L16 7"/><circle cx="12" cy="13.5" r="3.5"/>', c),
  grid: (c) => line('<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>', c),
  edit: (c) => line('<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="M14 6l4 4"/>', c),
  home: (c) => line('<path d="M4 11l8-7 8 7"/><path d="M6 10v9h12v-9"/>', c),
  user: (c) => line('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>', c),
  chart: (c) => line('<path d="M4 20h16"/><line x1="7" y1="20" x2="7" y2="12"/><line x1="12" y1="20" x2="12" y2="6"/><line x1="17" y1="20" x2="17" y2="14"/>', c),
  dashboard: (c) => line('<rect x="4" y="4" width="7" height="9" rx="1"/><rect x="13" y="4" width="7" height="5" rx="1"/><rect x="13" y="11" width="7" height="9" rx="1"/><rect x="4" y="15" width="7" height="5" rx="1"/>', c),
  menu: (c) => line('<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/>', c),
  cross: (c) => line('<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>', c),
  circle: (c) => line('<circle cx="12" cy="12" r="8"/>', c),
  check: (c) => line('<polyline points="5 13 10 18 19 6"/>', c),
  list: (c) => wrap(
    '<g fill="none" stroke="' + c + '" stroke-width="2" stroke-linecap="round"><line x1="9" y1="7" x2="20" y2="7"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="17" x2="20" y2="17"/></g>' +
    '<g fill="' + c + '"><rect x="3.5" y="5.5" width="3" height="3" rx="0.7"/><rect x="3.5" y="10.5" width="3" height="3" rx="0.7"/><rect x="3.5" y="15.5" width="3" height="3" rx="0.7"/></g>'
  ),

  // ===== 实心（状态 / 装饰） =====
  play: (c) => solid('<path d="M8 5v14l11-7L8 5Z"/>', c),
  spark: (c) => solid('<path d="M12 2l2.3 7.7L22 12l-7.7 2.3L12 22l-2.3-7.7L2 12l7.7-2.3L12 2Z"/>', c),
  'thumb-up': (c) => solid('<path d="M2 10h3v10H2z"/><path d="M7 20h9.4a2 2 0 0 0 2-1.6l1.3-6.8A1.6 1.6 0 0 0 18.1 9.4H13l.9-4.2a1.9 1.9 0 0 0-3.6-1.1L7 9.7V20Z"/>', c),
  'thumb-down': (c) => solid('<path d="M2 4h3v10H2z"/><path d="M7 4h9.4a2 2 0 0 1 2 1.6l1.3 6.8A1.6 1.6 0 0 1 18.1 14.6H13l.9 4.2a1.9 1.9 0 0 1-3.6 1.1L7 14.3V4Z"/>', c),
  celebrate: (c) => solid('<path d="M3 21l4.5-13 8.5 8.5L3 21Z"/><circle cx="13" cy="3" r="1.3"/><circle cx="16.5" cy="4.5" r="1.3"/><circle cx="20" cy="8" r="1.3"/><circle cx="21" cy="13" r="1.3"/>', c),
  puzzle: (c) => solid('<path d="M14.5 3a2.5 2.5 0 0 0-5 0c0 .4.1.7.3 1H6a1 1 0 0 0-1 1v3.8c.3-.2.6-.3 1-.3a2.5 2.5 0 0 1 0 5c-.4 0-.7-.1-1-.3V20a1 1 0 0 0 1 1h3.8c-.2-.3-.3-.6-.3-1a2.5 2.5 0 0 1 5 0c0 .4-.1.7-.3 1H18a1 1 0 0 0 1-1v-3.5c.3.2.6.3 1 .3a2.5 2.5 0 0 0 0-5c-.4 0-.7.1-1 .3V5a1 1 0 0 0-1-1h-3.2c.2-.3.3-.6.3-1Z"/>', c),
  folder: (c) => solid('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>', c),
  book: (c) => solid('<path d="M5 4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v15H7a2 2 0 0 0-2 2V4Z"/>', c),
  users: (c) => solid('<circle cx="9" cy="8" r="3.6"/><path d="M2.5 19.5C2.5 15.9 5.4 14 9 14s6.5 1.9 6.5 5.5Z"/><circle cx="17.2" cy="8.6" r="2.9"/><path d="M16 14.1c3 .1 5.5 1.8 5.5 5.4H18Z"/>', c),
  medal: (c) => wrap(
    '<g fill="none" stroke="' + c + '" stroke-width="2" stroke-linejoin="round"><path d="M8 2l2.5 7M16 2l-2.5 7"/></g>' +
    '<circle cx="12" cy="15" r="6.2" fill="' + c + '"/>' +
    '<path d="M12 11.6l1.1 2.3 2.5.3-1.9 1.7.5 2.5L12 17l-2.2 1.4.5-2.5-1.9-1.7 2.5-.3 1.1-2.3Z" fill="#fff"/>'
  ),
  lock: (c) => wrap(
    '<rect x="5" y="10" width="14" height="11" rx="2.5" fill="' + c + '"/>' +
    '<path d="M8 10V7.5a4 4 0 0 1 8 0V10" fill="none" stroke="' + c + '" stroke-width="2"/>'
  ),
  calendar: (c) => wrap(
    '<rect x="4" y="5" width="16" height="16" rx="2.5" fill="' + c + '"/>' +
    '<line x1="8" y1="2.5" x2="8" y2="6.5" stroke="' + c + '" stroke-width="2" stroke-linecap="round"/>' +
    '<line x1="16" y1="2.5" x2="16" y2="6.5" stroke="' + c + '" stroke-width="2" stroke-linecap="round"/>' +
    '<g fill="#fff"><rect x="7" y="11" width="3" height="3" rx="0.5"/><rect x="14" y="11" width="3" height="3" rx="0.5"/><rect x="7" y="16" width="3" height="3" rx="0.5"/></g>'
  ),
  note: (c) => wrap(
    '<rect x="4" y="3" width="13" height="18" rx="2.5" fill="' + c + '"/>' +
    '<g stroke="#fff" stroke-width="1.6" stroke-linecap="round"><line x1="7.5" y1="8" x2="13.5" y2="8"/><line x1="7.5" y1="12" x2="13.5" y2="12"/><line x1="7.5" y1="16" x2="11" y2="16"/></g>'
  ),
  file: (c) => wrap(
    '<path d="M6 3h8l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" fill="' + c + '"/>' +
    '<path d="M14 3v5h5" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>'
  ),
  'check-circle': (c) => wrap(
    '<circle cx="12" cy="12" r="9" fill="' + c + '"/>' +
    '<polyline points="8 12.5 11 15.5 16 9" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
  )
};

// 小程序无 btoa，自实现 ASCII 字符串的 base64 编码（SVG 全为 ASCII）
// (name|color) -> data-URI 缓存，跨实例复用
const SRC_CACHE = {};

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
function base64(str) {
  let out = '';
  for (let i = 0; i < str.length; i += 3) {
    const a = str.charCodeAt(i) & 0xff;
    const hasB = i + 1 < str.length;
    const hasC = i + 2 < str.length;
    const b = hasB ? str.charCodeAt(i + 1) & 0xff : 0;
    const d = hasC ? str.charCodeAt(i + 2) & 0xff : 0;
    out += B64[a >> 2];
    out += B64[((a & 3) << 4) | (b >> 4)];
    out += hasB ? B64[((b & 15) << 2) | (d >> 6)] : '=';
    out += hasC ? B64[d & 63] : '=';
  }
  return out;
}

Component({
  properties: {
    name: { type: String, value: '' },
    size: { type: String, value: '32rpx' },
    color: { type: String, value: '#2C2B29' }
  },
  data: { src: '' },
  lifetimes: {
    attached() { this._render(); }
  },
  observers: {
    'name, color': function () { this._render(); }
  },
  methods: {
    _render() {
      const fn = ICONS[this.data.name];
      if (!fn) { this.setData({ src: '' }); return; }
      // 同名同色图标在列表里会出现几十次，模块级缓存避免重复 SVG 拼串 + base64 编码
      const key = this.data.name + '|' + (this.data.color || '#2C2B29');
      let src = SRC_CACHE[key];
      if (!src) {
        const svg = fn(this.data.color || '#2C2B29');
        src = 'data:image/svg+xml;base64,' + base64(svg);
        SRC_CACHE[key] = src;
      }
      if (src !== this.data.src) this.setData({ src });
    }
  }
});
