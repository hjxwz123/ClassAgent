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
    navHeight: 44, // 自绘导航栏高度(px)，按胶囊位置计算
    navPadRight: 16, // 导航栏右侧留白(px)，避开胶囊
    loading: true,
    error: false,
    quiz: null,
    questions: [],
    current: 0,
    answers: {}, // questionId -> index | [index] | string
    answeredMap: {}, // questionId -> 是否已作答（与 answeredCount 同口径）
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
    const statusBar = sys.statusBarHeight || 20;
    // 按胶囊按钮位置计算导航栏高度与右侧留白，避免计时被胶囊遮挡
    let navHeight = 44;
    let navPadRight = 16;
    try {
      const rect = wx.getMenuButtonBoundingClientRect();
      if (rect && rect.width) {
        navHeight = (rect.top - statusBar) * 2 + rect.height;
        navPadRight = (sys.windowWidth || sys.screenWidth) - rect.left + 8;
      }
    } catch (e) { /* 取不到胶囊信息时用默认值 */ }
    this.setData({ quizId: Number(query.quizId || 0), statusBar, navHeight, navPadRight });
    // 侧滑/物理返回时二次确认，避免误触丢失作答
    if (wx.enableAlertBeforeUnload) {
      wx.enableAlertBeforeUnload({ message: '退出后本次作答不会保存，确定离开吗？' });
    }
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
    this.setData({ loading: true, error: false });
    try {
      const detail = await api.get('/learning/quizzes/' + this.data.quizId);
      const questions = (detail.questions || []).map((q) => this.normalize(q));
      this.setData({ quiz: detail.quiz, questions, loading: false });
      this.renderCurrent();
    } catch (err) {
      this.setData({ loading: false, error: true });
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
    wx.vibrateShort && wx.vibrateShort({ type: 'light' });
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
    // 预计算每题是否已答，题号面板与已答计数共用同一口径（空串/空数组视为未答）
    let n = 0;
    const answeredMap = {};
    this.data.questions.forEach((q) => {
      const a = this.data.answers[q.id];
      const answered = a !== undefined && a !== '' && !(Array.isArray(a) && !a.length);
      answeredMap[q.id] = answered;
      if (answered) n++;
    });
    this.setData({ answeredCount: n, answeredMap });
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
    if (ok) {
      // 已确认过一次，关闭系统返回询问，避免二次弹窗
      if (wx.disableAlertBeforeUnload) wx.disableAlertBeforeUnload({});
      wx.navigateBack();
    }
  },

  async submit() {
    if (this.data.submitting) return;
    const total = this.data.questions.length;
    const unanswered = total - this.data.answeredCount;
    const ok = await toast.confirm({
      title: '确认交卷',
      content: unanswered > 0 ? ('还有 ' + unanswered + ' 题未作答，确定交卷？') : '已完成全部题目，确定交卷？',
      confirmText: '交卷'
    });
    if (!ok) return;
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      const answers = Object.keys(this.data.answers).map((qid) => ({ question_id: Number(qid), answer: this.data.answers[qid] }));
      const attempt = await api.postLong('/learning/quizzes/' + this.data.quizId + '/submit', { answers });
      // 已成功提交，返回不再需要确认
      if (wx.disableAlertBeforeUnload) wx.disableAlertBeforeUnload({});
      getApp().globalData.transfer.attempt = attempt;
      wx.redirectTo({ url: '/subpackages/student-learning/quiz-result/index?attemptId=' + (attempt.attempt && attempt.attempt.id) });
    } catch (err) {
      toast.error(err.message);
      this.setData({ submitting: false });
    }
  }
});
