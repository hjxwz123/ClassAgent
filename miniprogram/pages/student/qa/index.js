const api = require('../../../utils/api');
const sse = require('../../../utils/sse');
const md = require('../../../utils/markdown');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

const PROMPTS = [
  '帮我梳理这门课程的重点',
  '这个知识点我没懂，换个方式讲讲',
  '给我出两道练习题',
  '我最近的薄弱点是什么'
];

// 流式增量的渲染节流间隔：小程序 setData 有固定开销，按 ~6 帧/秒批量上屏，
// 视觉仍是连续打字机效果，但渲染成本与 token 数解耦
const FLUSH_INTERVAL = 160;

let seq = 1;
function nextKey() { return 'm' + (seq++); }

Page({
  data: {
    courses: [],
    coursesError: false,
    courseId: 0,
    courseName: '选择课程',
    backCourseId: 0, // >0 时从课程详情页进入，顶栏显示"返回课程"按钮
    coursePickerOpen: false,
    messages: [],
    conversationId: null,
    input: '',
    attachments: [],
    sending: false,
    scrollTop: 0,
    prompts: PROMPTS,
    // 历史
    historyOpen: false,
    historyLoading: false,
    history: []
  },

  onLoad() {
    this.loadCourses();
  },

  onShow() {
    tabbar.setTab(this, 2);
    const transfer = getApp().globalData.transfer;
    // 仅当从课程详情页进入时显示"返回课程"按钮；其余入口（tab 切换等）清除，避免残留错误的返回目标
    const backCourseId = transfer.qaBackCourseId || 0;
    transfer.qaBackCourseId = null;
    if (backCourseId !== this.data.backCourseId) this.setData({ backCourseId });
    if (transfer.qaCourseId) {
      this.pendingCourseId = transfer.qaCourseId;
      transfer.qaCourseId = null;
      // QA 是常驻 tab 页，第二次起 onLoad 不再触发：
      // 课程已加载时直接切换，否则重拉课程列表消费 pendingCourseId
      if (this.data.courses.length) this.applyPendingCourse();
      else this.loadCourses();
    } else if (!this.data.courses.length) {
      // 首次加载失败后再次进入时自动补拉
      this.loadCourses();
    }
  },

  onShareAppMessage() {
    return { title: '智学黑板 · 课程专属 AI 问答', path: '/pages/student/qa/index' };
  },

  // 作废在途的流式回答：中止请求并递增代次，让旧流的一切回调(增量/final/错误)全部失效。
  // 切课程/开历史/清空对话前必须调用，否则旧流会往新消息数组的旧下标写数据、并把旧会话 id 写回。
  cancelStream() {
    this._streamSeq = (this._streamSeq || 0) + 1;
    if (this._streamHandle) {
      try { this._streamHandle.abort(); } catch (e) { /* 已结束 */ }
      this._streamHandle = null;
    }
    if (this.data.sending) this.setData({ sending: false });
  },

  applyPendingCourse() {
    const id = this.pendingCourseId;
    this.pendingCourseId = null;
    if (!id || id === this.data.courseId) return;
    const course = this.data.courses.find((c) => c.id === id);
    if (!course) return;
    this.cancelStream();
    this.setData({ courseId: id, courseName: course.name, messages: [], conversationId: null });
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      let courseId = this.pendingCourseId || this.data.courseId || (courses[0] && courses[0].id) || 0;
      this.pendingCourseId = null;
      const course = courses.find((c) => c.id === courseId);
      if (!course) courseId = (courses[0] && courses[0].id) || 0;
      const picked = courses.find((c) => c.id === courseId);
      this.setData({ courses, coursesError: false, courseId, courseName: picked ? picked.name : '选择课程' });
    } catch (err) {
      this.setData({ coursesError: true });
      toast.error(err.message);
    }
  },

  toggleCoursePicker() {
    this.setData({ coursePickerOpen: !this.data.coursePickerOpen });
  },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    if (id === this.data.courseId) { this.setData({ coursePickerOpen: false }); return; }
    const course = this.data.courses.find((c) => c.id === id);
    const hadConversation = this.data.messages.length > 0;
    this.cancelStream();
    // 手动切到其它课程后，"返回课程"入口已与当前所看课程不一致，一并清除避免回错课程
    this.setData({ courseId: id, courseName: course ? course.name : '选择课程', coursePickerOpen: false, messages: [], conversationId: null, backCourseId: 0 });
    if (hadConversation) toast.info('已切换课程，原对话可在历史中找回');
  },
  goJoinCourse() {
    this.setData({ coursePickerOpen: false });
    wx.switchTab({ url: '/pages/student/courses/index' });
  },

  // 从课程详情页 switchTab 进入 QA 后返回栈已清空，提供显式入口回到该课程主页
  backToCourse() {
    const id = this.data.backCourseId;
    if (!id) return;
    wx.navigateTo({ url: '/subpackages/student-course/course-home/index?courseId=' + id });
  },

  newConversation() {
    if (this.data.sending) return toast.info('正在回答中，请先停止');
    this.setData({ messages: [], conversationId: null, attachments: [], input: '' });
  },

  onInput(e) { this.setData({ input: e.detail.value }); },
  usePrompt(e) { this.setData({ input: e.currentTarget.dataset.text }); },

  // 历史对话中的图片预览
  previewAttachment(e) {
    const list = e.currentTarget.dataset.list || this.data.attachments;
    const urls = list.map((a) => a.displayUrl || api.mediaUrl(a.url));
    const idx = e.currentTarget.dataset.index || 0;
    wx.previewImage({ urls, current: urls[idx] });
  },

  // ===== 发送（流式）=====
  scrollToBottom() {
    this._scrollSeq = (this._scrollSeq || 100000) + 1;
    this.setData({ scrollTop: this._scrollSeq });
  },

  send() {
    const question = this.data.input.trim();
    if (!question) return;
    this.askQuestion(question);
  },

  retry(e) {
    const idx = e.currentTarget.dataset.index;
    const msg = this.data.messages[idx];
    if (!msg || !msg.question || this.data.sending) return;
    // 移除失败气泡及其对应的用户消息，重新发送
    const messages = this.data.messages.slice(0, Math.max(0, idx - 1));
    this.setData({ messages });
    this.askQuestion(msg.question);
  },

  askQuestion(question) {
    if (!this.data.courseId) return toast.info('请先选择课程');
    if (this.data.sending) return;
    wx.vibrateShort({ type: 'light' });

    const userMsg = { k: nextKey(), role: 'user', text: question, attachments: this.data.attachments.slice() };
    const aiMsg = { k: nextKey(), role: 'ai', text: '', thinking: '', sources: [], pending: true, statusText: '正在连接…', showThinking: false, question };
    const base = this.data.messages.length;
    this.setData({
      ['messages[' + base + ']']: userMsg,
      ['messages[' + (base + 1) + ']']: aiMsg,
      input: '',
      sending: true,
      attachments: []
    });
    this.scrollToBottom();
    const aiIndex = base + 1;
    this.streamAnswer(question, aiIndex);
  },

  streamAnswer(question, aiIndex) {
    const prefix = 'messages[' + aiIndex + ']';
    // 流代次：切课程/开历史/新对话会递增 _streamSeq，本次流的所有回调据此失效，
    // 杜绝旧流往新消息数组的旧下标写数据、或把旧会话 id 写回。
    const seq = this._streamSeq = (this._streamSeq || 0) + 1;
    const alive = () => seq === this._streamSeq;
    let text = '';
    let thinking = '';
    let started = false;
    let recordId = null;
    let convId = this.data.conversationId;
    let flushTimer = null;
    let dirty = false;

    const flush = () => {
      flushTimer = null;
      if (!dirty || !alive()) return;
      dirty = false;
      const patch = {};
      patch[prefix + '.text'] = text;
      patch[prefix + '.thinking'] = thinking;
      if (!started && (text || thinking)) {
        started = true;
        patch[prefix + '.pending'] = false;
        patch[prefix + '.streaming'] = true;
      }
      this.setData(patch);
      this.scrollToBottom();
    };
    const scheduleFlush = () => {
      dirty = true;
      if (!flushTimer) flushTimer = setTimeout(flush, FLUSH_INTERVAL);
    };

    const handle = sse.streamPost('/qa/ask/stream', {
      course_id: this.data.courseId,
      question,
      conversation_id: convId || undefined,
      attachments: []
    }, (event, data) => {
      if (!alive()) return;
      if (event === 'stage') {
        if (!started) this.setData({ [prefix + '.statusText']: (data && data.text) || '正在生成回答…' });
        return;
      }
      if (event === 'created') {
        convId = (data && data.conversation_id) || convId;
        recordId = (data && data.record_id) || null;
        return;
      }
      if (event === 'delta') {
        if (data.type === 'thought') thinking += data.text || '';
        else text += data.text || '';
        scheduleFlush();
        return;
      }
      if (event === 'final') {
        if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; }
        const answer = (data && data.answer) || text || '（无回答）';
        this.setData({
          [prefix]: {
            k: (this.data.messages[aiIndex] || {}).k || nextKey(),
            role: 'ai',
            text: answer,
            nodes: md.toNodes(answer),
            thinking: (data && data.thinking_process) || thinking || '',
            sources: (data && data.sources) || [],
            record_id: (data && data.record_id) || recordId,
            favorite: false,
            feedback: '',
            outOfScope: !!(data && data.is_out_of_scope),
            showThinking: false,
            pending: false,
            streaming: false,
            question
          },
          conversationId: (data && data.conversation_id) || convId
        });
        this.scrollToBottom();
      }
    });

    this._streamHandle = handle;
    handle.finished.then(() => {
      if (!alive()) return;
      this._streamHandle = null;
      this.setData({ sending: false });
    }).catch((err) => {
      if (flushTimer) { clearTimeout(flushTimer); flushTimer = null; }
      // 已被 cancelStream 作废（切课程/开历史触发的中止）：状态已由取消方处理，这里不再碰页面数据
      if (!alive()) return;
      this._streamHandle = null;
      if (err && err.aborted) {
        // 主动停止：保留已生成内容并结束流式态（后端会把完整回答落库，可从历史查看）
        const patch = { sending: false };
        patch[prefix + '.pending'] = false;
        patch[prefix + '.streaming'] = false;
        if (!text && !thinking) {
          patch[prefix + '.text'] = '已停止生成';
        } else {
          // 同步累积全文：flush 有 160ms 节流，text 可能领先渲染层一拍
          patch[prefix + '.text'] = text;
          patch[prefix + '.thinking'] = thinking;
          patch[prefix + '.nodes'] = md.toNodes(text);
        }
        this.setData(patch);
        return;
      }
      if (err && err.code === 'NO_CHUNK') {
        // 老基础库回退非流式（放宽超时）
        this.fallbackAsk(question, aiIndex);
        return;
      }
      this.setData({
        sending: false,
        [prefix]: { k: (this.data.messages[aiIndex] || {}).k || nextKey(), role: 'ai', text: '回答失败：' + err.message, pending: false, streaming: false, error: true, question }
      });
    });
  },

  async fallbackAsk(question, aiIndex) {
    const prefix = 'messages[' + aiIndex + ']';
    const seq = this._streamSeq; // 等待期间被切课程/开历史则丢弃结果
    try {
      const data = await api.postLong('/qa/ask', {
        course_id: this.data.courseId,
        question,
        conversation_id: this.data.conversationId || undefined,
        attachments: []
      });
      if (seq !== this._streamSeq) return;
      const answer = data.answer || '（无回答）';
      this.setData({
        sending: false,
        conversationId: data.conversation_id,
        [prefix]: {
          k: (this.data.messages[aiIndex] || {}).k || nextKey(),
          role: 'ai',
          text: answer,
          nodes: md.toNodes(answer),
          thinking: data.thinking_process || '',
          sources: data.sources || [],
          record_id: data.record_id,
          favorite: false,
          feedback: '',
          outOfScope: !!data.is_out_of_scope,
          showThinking: false,
          pending: false,
          question
        }
      });
      this.scrollToBottom();
    } catch (err) {
      if (seq !== this._streamSeq) return;
      this.setData({
        sending: false,
        [prefix]: { k: (this.data.messages[aiIndex] || {}).k || nextKey(), role: 'ai', text: '回答失败：' + err.message, pending: false, error: true, question }
      });
    }
  },

  stopGeneration() {
    if (this._streamHandle) {
      wx.vibrateShort({ type: 'light' });
      this._streamHandle.abort();
    }
  },

  onUnload() {
    if (this._streamHandle) this._streamHandle.abort();
  },
  onHide() {
    // 页面隐藏不中断：后端已解耦落库，回来后可从历史查看完整回答
  },

  toggleThinking(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ ['messages[' + idx + '].showThinking']: !this.data.messages[idx].showThinking });
  },
  copyAnswer(e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.text });
  },
  async favorite(e) {
    const idx = e.currentTarget.dataset.index;
    const msg = this.data.messages[idx];
    if (!msg.record_id || msg.favoritePending) return;
    this.setData({ ['messages[' + idx + '].favoritePending']: true });
    try {
      await api.post('/qa/' + msg.record_id + '/favorite', { is_favorite: !msg.favorite });
      wx.vibrateShort({ type: 'light' });
      this.setData({ ['messages[' + idx + '].favorite']: !msg.favorite });
      toast.success(!msg.favorite ? '已收藏' : '已取消');
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ ['messages[' + idx + '].favoritePending']: false });
    }
  },
  async feedback(e) {
    const idx = e.currentTarget.dataset.index;
    const value = e.currentTarget.dataset.value;
    const msg = this.data.messages[idx];
    if (!msg.record_id || msg.feedbackPending || msg.feedback === value) return;
    this.setData({ ['messages[' + idx + '].feedbackPending']: true });
    try {
      await api.post('/qa/' + msg.record_id + '/feedback', { feedback: value });
      wx.vibrateShort({ type: 'light' });
      this.setData({ ['messages[' + idx + '].feedback']: value });
      toast.success('感谢反馈');
    } catch (err) {
      toast.error(err.message);
    } finally {
      this.setData({ ['messages[' + idx + '].feedbackPending']: false });
    }
  },

  // ===== 历史 =====
  async openHistory() {
    this.setData({ historyOpen: true, historyLoading: true });
    try {
      const history = (await api.get('/qa/history', { course_id: this.data.courseId })) || [];
      this.setData({ history, historyLoading: false });
    } catch (err) {
      this.setData({ historyLoading: false });
      toast.error(err.message);
    }
  },
  closeHistory() { this.setData({ historyOpen: false }); },
  async openConversation(e) {
    const id = e.currentTarget.dataset.id;
    this.cancelStream();
    this.setData({ historyOpen: false });
    toast.loading('加载中');
    try {
      const records = (await api.get('/qa/conversations/' + id)) || [];
      const messages = [];
      records.forEach((r) => {
        const atts = (r.attachments || []).map((a) => Object.assign({}, a, { displayUrl: api.mediaUrl(a.url) }));
        messages.push({ k: nextKey(), role: 'user', text: r.question, attachments: atts });
        messages.push({
          k: nextKey(),
          role: 'ai',
          text: r.answer,
          nodes: md.toNodes(r.answer),
          thinking: r.thinking_process || '',
          sources: r.sources || [],
          record_id: r.id,
          favorite: r.is_favorite,
          feedback: '',
          showThinking: false,
          pending: false,
          question: r.question
        });
      });
      this.setData({ messages, conversationId: id });
      this.scrollToBottom();
    } catch (err) {
      toast.error(err.message);
    } finally {
      toast.hideLoading();
    }
  },

  goTutoring() {
    if (!this.data.courseId) return toast.info('请先选择课程');
    wx.navigateTo({ url: '/subpackages/student-learning/tutoring/index?courseId=' + this.data.courseId });
  }
});
