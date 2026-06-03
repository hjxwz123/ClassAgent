const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

Page({
  data: {
    attemptId: 0,
    loading: true,
    attempt: null,
    quiz: null,
    rows: [],
    accuracy: 0,
    scoreText: ''
  },

  onLoad(query) {
    this.setData({ attemptId: Number(query.attemptId || 0) });
    const cached = getApp().globalData.transfer.attempt;
    if (cached && cached.attempt && cached.attempt.id === this.data.attemptId) {
      getApp().globalData.transfer.attempt = null;
      this.render(cached);
    } else {
      this.load();
    }
  },

  async load() {
    try {
      const data = await api.get('/learning/attempts/' + this.data.attemptId);
      this.render(data);
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  answerText(value, question) {
    if (value === null || value === undefined || value === '') return '-';
    const options = Array.isArray(question.options) ? question.options : [];
    const one = (v) => {
      let idx = null;
      if (typeof v === 'number') idx = v;
      else if (typeof v === 'string' && /^\d+$/.test(v)) idx = Number(v);
      else if (typeof v === 'string' && /^[A-Za-z]$/.test(v.trim())) idx = v.trim().toUpperCase().charCodeAt(0) - 65;
      if (idx !== null && options[idx] !== undefined) {
        const raw = options[idx];
        const t = typeof raw === 'object' ? (raw.text || raw.label || '') : String(raw);
        return (LETTERS[idx] || idx) + '. ' + t;
      }
      return String(v);
    };
    return Array.isArray(value) ? value.map(one).join('；') : one(value);
  },

  render(data) {
    const attempt = data.attempt || {};
    const rows = (data.answers || []).map((row) => Object.assign({}, row, {
      userText: this.answerText(row.user_answer, row.question || {}),
      correctText: this.answerText(row.correct_answer, row.question || {}),
      expanded: !row.is_correct
    }));
    this.setData({
      attempt,
      quiz: data.quiz,
      rows,
      accuracy: fmt.percent(attempt.accuracy),
      scoreText: Math.round(attempt.score || 0) + ' / ' + Math.round(attempt.total_score || 0),
      loading: false
    });
  },

  toggleRow(e) {
    const idx = e.currentTarget.dataset.index;
    const rows = this.data.rows.slice();
    rows[idx].expanded = !rows[idx].expanded;
    this.setData({ rows });
  },

  done() {
    wx.navigateBack({ fail() { wx.switchTab({ url: '/pages/student/home/index' }); } });
  }
});
