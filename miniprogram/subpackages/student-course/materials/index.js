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

Page({
  data: {
    courseId: 0,
    loading: true,
    materials: [],
    cats: CATS,
    category: '',
    keyword: '',
    detailOpen: false,
    detail: null
  },

  onLoad(query) {
    this.setData({ courseId: Number(query.courseId || 0) });
    this.load();
  },

  async load() {
    this.setData({ loading: true });
    try {
      const res = await api.get('/materials', { course_id: this.data.courseId, category: this.data.category || undefined, keyword: this.data.keyword || undefined });
      const list = Array.isArray(res) ? res : (res.items || []);
      this.setData({ materials: list.map((m) => Object.assign({}, m, { sizeText: fmt.fileSize(m.size_bytes) })), loading: false });
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
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
      this.setData({ detail, detailOpen: true });
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
