const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const auth = require('../../../utils/auth');
const { API_BASE } = require('../../../config');

const CATS = [
  { key: '', label: '全部' },
  { key: 'courseware', label: '课件' },
  { key: 'reading', label: '阅读' },
  { key: 'reference', label: '参考' }
];

// 详情文本预览上限（字符）
const PREVIEW_LIMIT = 3000;

Page({
  data: {
    courseId: 0,
    loading: true,
    error: '',
    materials: [],
    cats: CATS,
    category: '',
    keyword: '',
    detailOpen: false,
    detail: null,
    previewText: '',
    previewTruncated: false
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },

  onPullDownRefresh() {
    this.load(true).finally(() => wx.stopPullDownRefresh());
  },

  async load(silent) {
    // 注意：bindtap 重试会把事件对象传进来，只有显式 true 才是静默刷新
    silent = silent === true;
    // 分类/搜索连点竞态：只采纳最后一次请求的响应
    const seq = (this._reqSeq || 0) + 1;
    this._reqSeq = seq;
    if (!silent) this.setData({ loading: true, error: '' });
    try {
      const res = await api.get('/materials', { course_id: this.data.courseId, category: this.data.category || undefined, keyword: this.data.keyword || undefined });
      if (seq !== this._reqSeq) return; // 过期响应丢弃
      const list = Array.isArray(res) ? res : (res.items || []);
      // 列表只保留渲染要用的字段，剔除 extracted_text 等大字段
      const materials = list.map((m) => {
        const parsed = m.parse_status === 'completed' || m.parse_status === 'ready';
        return {
          id: m.id,
          title: m.title,
          category: m.category,
          parse_status: m.parse_status,
          created_at: m.created_at,
          sizeText: fmt.fileSize(m.size_bytes),
          statusText: parsed ? '已解析' : (m.parse_status === 'failed' ? '解析失败' : '解析中'),
          statusClass: parsed ? 'tag--success' : (m.parse_status === 'failed' ? 'tag--error' : 'tag--warning')
        };
      });
      this.setData({ materials, loading: false, error: '' });
    } catch (err) {
      if (seq !== this._reqSeq) return;
      this.setData({ loading: false, error: err.message || '加载失败' });
    }
  },

  setCategory(e) { this.setData({ category: e.currentTarget.dataset.key }); this.load(); },
  onSearch(e) { this.setData({ keyword: e.detail.value }); },
  doSearch() { this.load(); },

  async openMaterial(e) {
    const id = e.currentTarget.dataset.id;
    toast.loading('加载中');
    try {
      const detail = await api.get('/materials/' + id);
      const m = (detail && detail.material) || {};
      const full = m.extracted_text || '';
      // 详情只 setData 展示字段，全文只截取前 PREVIEW_LIMIT 字预览
      this.setData({
        detail: {
          material: {
            id: m.id,
            title: m.title,
            category: m.category,
            original_filename: m.original_filename
          }
        },
        previewText: full.slice(0, PREVIEW_LIMIT),
        previewTruncated: full.length > PREVIEW_LIMIT,
        detailOpen: true
      });
    } catch (err) {
      toast.error(err.message);
    } finally {
      toast.hideLoading();
    }
  },
  closeDetail() { this.setData({ detailOpen: false }); },

  openFile() {
    const m = this.data.detail && this.data.detail.material;
    if (!m) return;
    const url = API_BASE + '/materials/' + m.id + '/content';
    toast.loading('打开中');
    wx.downloadFile({
      url,
      header: { Authorization: 'Bearer ' + auth.getToken() },
      success(res) {
        toast.hideLoading();
        if (res.statusCode !== 200) { toast.error('文件加载失败'); return; }
        wx.openDocument({
          filePath: res.tempFilePath,
          showMenu: true,
          fail() { toast.error('暂不支持预览该格式'); }
        });
      },
      fail() { toast.hideLoading(); toast.error('文件加载失败'); }
    });
  }
});
