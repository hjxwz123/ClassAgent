const api = require('../../../utils/api');
const toast = require('../../../utils/toast');

const TYPE_LABEL = {
  single_choice: '单选',
  multiple_choice: '多选',
  judge: '判断',
  blank: '填空',
  short_answer: '简答'
};
const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

Page({
  data: {
    quizId: 0,
    statusBar: 20,
    loading: true,
    quiz: null,
    questions: [],
    current: 0,
    answers: {}, // questionId -> index | [index] | string
    answeredCount: 0,
    elapsed: 0,
    timeText: '00:00',
    panelOpen: false,
    submitting: false,
    typeLabel: TYPE_LABEL,
    letters: LETTERS,
    view: null // 当前题视图（含选项渲染）
  },

  onLoad(query) {
    const sys = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    this.setData({ quizId: Number(query.quizId || 0), statusBar: sys.statusBarHeight || 20 });
    this.load();
    this._timer = setInterval(() => {
      const e = this.data.elapsed + 1;
      const m = String(Math.floor(e / 60)).padStart(2, '0');
      const s = String(e % 60).padStart(2, '0');
      this.setData({ elapsed: e, timeText: m + ':' + s });
    }, 1000);
  },
  onUnload() { if (this._timer) clearInterval(this._timer); },

  async load() {
    try {
      const detail = await api.get('/learning/quizzes/' + this.data.quizId);
      const questions = (detail.questions || []).map((q) => this.normalize(q));
      this.setData({ quiz: detail.quiz, questions, loading: false });
      this.renderCurrent();
    } catch (err) {
      this.setData({ loading: false });
      toast.error(err.message);
    }
  },

  normalize(q) {
    let options = Array.isArray(q.options) ? q.options : [];
    if (q.question_type === 'judge' && !options.length) options = ['正确', '错误'];
    const opts = options.map((o, i) => ({
      index: i,
      letter: LETTERS[i] || (i + 1),
      text: typeof o === 'object' ? (o.text || o.label || JSON.stringify(o)) : String(o)
    }));
    return Object.assign({}, q, { opts, isChoice: ['single_choice', 'multiple_choice', 'judge'].indexOf(q.question_type) >= 0, isMulti: q.question_type === 'multiple_choice' });
  },

  renderCurrent() {
    const q = this.data.questions[this.data.current];
    if (!q) return;
    const ans = this.data.answers[q.id];
    const opts = q.opts.map((o) => ({
      ...o,
      selected: q.isMulti ? (Array.isArray(ans) && ans.indexOf(o.index) >= 0) : (ans === o.index)
    }));
    this.setData({ view: Object.assign({}, q, { opts, textAnswer: (!q.isChoice ? (ans || '') : '') }) });
  },

  selectOption(e) {
    const q = this.data.view;
    const idx = e.currentTarget.dataset.index;
    const answers = Object.assign({}, this.data.answers);
    if (q.isMulti) {
      const arr = Array.isArray(answers[q.id]) ? answers[q.id].slice() : [];
      const pos = arr.indexOf(idx);
      if (pos >= 0) arr.splice(pos, 1); else arr.push(idx);
      answers[q.id] = arr.sort();
    } else {
      answers[q.id] = idx;
    }
    this.setData({ answers });
    this.refreshAnsweredCount();
    this.renderCurrent();
  },
  onTextAnswer(e) {
    const q = this.data.view;
    const answers = Object.assign({}, this.data.answers);
    answers[q.id] = e.detail.value;
    this.setData({ answers });
    this.refreshAnsweredCount();
  },

  refreshAnsweredCount() {
    let n = 0;
    this.data.questions.forEach((q) => {
      const a = this.data.answers[q.id];
      if (a !== undefined && a !== '' && !(Array.isArray(a) && !a.length)) n++;
    });
    this.setData({ answeredCount: n });
  },

  prev() { if (this.data.current > 0) { this.setData({ current: this.data.current - 1 }); this.renderCurrent(); } },
  next() { if (this.data.current < this.data.questions.length - 1) { this.setData({ current: this.data.current + 1 }); this.renderCurrent(); } },
  jump(e) { this.setData({ current: e.currentTarget.dataset.index, panelOpen: false }); this.renderCurrent(); },
  togglePanel() { this.setData({ panelOpen: !this.data.panelOpen }); },

  isAnswered(qid) {
    const a = this.data.answers[qid];
    return a !== undefined && a !== '' && !(Array.isArray(a) && !a.length);
  },

  async exit() {
    const ok = await toast.confirm({ title: '退出作答', content: '退出后作答进度不会保存，确定退出？', confirmText: '退出', danger: true });
    if (ok) wx.navigateBack();
  },

  async submit() {
    const total = this.data.questions.length;
    const unanswered = total - this.data.answeredCount;
    const ok = await toast.confirm({
      title: '确认交卷',
      content: unanswered > 0 ? ('还有 ' + unanswered + ' 题未作答，确定交卷？') : '已完成全部题目，确定交卷？',
      confirmText: '交卷'
    });
    if (!ok) return;
    this.setData({ submitting: true });
    try {
      const answers = Object.keys(this.data.answers).map((qid) => ({ question_id: Number(qid), answer: this.data.answers[qid] }));
      const attempt = await api.post('/learning/quizzes/' + this.data.quizId + '/submit', { answers });
      getApp().globalData.transfer.attempt = attempt;
      wx.redirectTo({ url: '/subpackages/student-learning/quiz-result/index?attemptId=' + (attempt.attempt && attempt.attempt.id) });
    } catch (err) {
      toast.error(err.message);
      this.setData({ submitting: false });
    }
  }
});
