const api = require('../../../utils/api');
const fmt = require('../../../utils/format');
const toast = require('../../../utils/toast');
const tabbar = require('../../../utils/tabbar');

const PROMPTS = [
  '帮我梳理这门课程的重点',
  '这个知识点我没懂，换个方式讲讲',
  '给我出两道练习题',
  '我最近的薄弱点是什么'
];

Page({
  data: {
    courses: [],
    courseId: 0,
    courseName: '选择课程',
    coursePickerOpen: false,
    messages: [],
    conversationId: null,
    input: '',
    attachments: [],
    sending: false,
    scrollTo: '',
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
    if (transfer.qaCourseId) {
      this.pendingCourseId = transfer.qaCourseId;
      transfer.qaCourseId = null;
    }
  },

  async loadCourses() {
    try {
      const courses = (await api.get('/student/courses')) || [];
      let courseId = this.pendingCourseId || (courses[0] && courses[0].id) || 0;
      this.pendingCourseId = null;
      const course = courses.find((c) => c.id === courseId);
      this.setData({ courses, courseId, courseName: course ? course.name : '选择课程' });
    } catch (err) {
      toast.error(err.message);
    }
  },

  toggleCoursePicker() {
    this.setData({ coursePickerOpen: !this.data.coursePickerOpen });
  },
  pickCourse(e) {
    const id = e.currentTarget.dataset.id;
    const course = this.data.courses.find((c) => c.id === id);
    this.setData({ courseId: id, courseName: course ? course.name : '选择课程', coursePickerOpen: false, messages: [], conversationId: null });
  },

  newConversation() {
    this.setData({ messages: [], conversationId: null, attachments: [], input: '' });
  },

  onInput(e) { this.setData({ input: e.detail.value }); },
  usePrompt(e) { this.setData({ input: e.currentTarget.dataset.text }); },

  // 图片附件
  async chooseImage() {
    if (this.data.attachments.length >= 3) return toast.info('最多 3 张图片');
    if (!this.data.courseId) return toast.info('请先选择课程');
    try {
      const res = await wx.chooseMedia({ count: 3 - this.data.attachments.length, mediaType: ['image'], sizeType: ['compressed'] });
      for (const file of res.tempFiles) {
        toast.loading('上传中');
        try {
          const att = await api.upload('/qa/attachments/image', file.tempFilePath, { formData: { course_id: this.data.courseId } });
          // displayUrl 用于 <image> 显示（绝对地址），url 保留原值回传后端
          att.displayUrl = api.mediaUrl(att.url);
          this.setData({ attachments: this.data.attachments.concat([att]) });
        } catch (err) {
          toast.error(err.message);
        } finally {
          toast.hideLoading();
        }
      }
    } catch (e) { /* 用户取消 */ }
  },
  removeAttachment(e) {
    const idx = e.currentTarget.dataset.index;
    const attachments = this.data.attachments.slice();
    attachments.splice(idx, 1);
    this.setData({ attachments });
  },
  previewAttachment(e) {
    const url = e.currentTarget.dataset.url;
    const urls = (e.currentTarget.dataset.list || this.data.attachments).map((a) => a.displayUrl || api.mediaUrl(a.url));
    wx.previewImage({ urls, current: url });
  },

  async send() {
    const question = this.data.input.trim();
    if (!question) return;
    if (!this.data.courseId) return toast.info('请先选择课程');
    if (this.data.sending) return;

    const messages = this.data.messages.slice();
    messages.push({ role: 'user', text: question, attachments: this.data.attachments.slice() });
    messages.push({ role: 'ai', text: '', thinking: '', sources: [], pending: true, showThinking: false });
    const aiIndex = messages.length - 1;
    this.setData({ messages, input: '', sending: true, attachments: [], scrollTo: 'msg-' + aiIndex });

    try {
      // 回传后端时剔除仅用于显示的 displayUrl 字段
      const sendAtts = (messages[aiIndex - 1].attachments || []).map((a) => ({
        type: a.type || 'image',
        url: a.url,
        filename: a.filename,
        size_bytes: a.size_bytes,
        ocr_text: a.ocr_text
      }));
      const data = await api.post('/qa/ask', {
        course_id: this.data.courseId,
        question,
        conversation_id: this.data.conversationId || undefined,
        attachments: sendAtts
      });
      const next = this.data.messages.slice();
      next[aiIndex] = {
        role: 'ai',
        text: data.answer || '（无回答）',
        thinking: data.thinking_process || '',
        sources: data.sources || [],
        record_id: data.record_id,
        favorite: false,
        outOfScope: data.is_out_of_scope,
        showThinking: false,
        pending: false
      };
      this.setData({ messages: next, conversationId: data.conversation_id, sending: false, scrollTo: 'msg-' + aiIndex });
    } catch (err) {
      const next = this.data.messages.slice();
      next[aiIndex] = { role: 'ai', text: '回答失败：' + err.message, pending: false, error: true };
      this.setData({ messages: next, sending: false });
    }
  },

  toggleThinking(e) {
    const idx = e.currentTarget.dataset.index;
    const messages = this.data.messages.slice();
    messages[idx].showThinking = !messages[idx].showThinking;
    this.setData({ messages });
  },
  copyAnswer(e) {
    wx.setClipboardData({ data: e.currentTarget.dataset.text });
  },
  async favorite(e) {
    const idx = e.currentTarget.dataset.index;
    const msg = this.data.messages[idx];
    if (!msg.record_id) return;
    try {
      await api.post('/qa/' + msg.record_id + '/favorite', { is_favorite: !msg.favorite });
      const messages = this.data.messages.slice();
      messages[idx].favorite = !msg.favorite;
      this.setData({ messages });
      toast.success(messages[idx].favorite ? '已收藏' : '已取消');
    } catch (err) { toast.error(err.message); }
  },
  async feedback(e) {
    const idx = e.currentTarget.dataset.index;
    const msg = this.data.messages[idx];
    if (!msg.record_id) return;
    try {
      await api.post('/qa/' + msg.record_id + '/feedback', { feedback: e.currentTarget.dataset.value });
      toast.success('感谢反馈');
    } catch (err) { toast.error(err.message); }
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
    this.setData({ historyOpen: false });
    toast.loading('加载中');
    try {
      const records = (await api.get('/qa/conversations/' + id)) || [];
      const messages = [];
      records.forEach((r) => {
        const atts = (r.attachments || []).map((a) => Object.assign({}, a, { displayUrl: api.mediaUrl(a.url) }));
        messages.push({ role: 'user', text: r.question, attachments: atts });
        messages.push({ role: 'ai', text: r.answer, thinking: r.thinking_process || '', sources: r.sources || [], record_id: r.id, favorite: r.is_favorite, showThinking: false, pending: false });
      });
      this.setData({ messages, conversationId: id, scrollTo: 'msg-' + (messages.length - 1) });
    } catch (err) {
      toast.error(err.message);
    } finally {
      toast.hideLoading();
    }
  },

  goTutoring() {
    wx.navigateTo({ url: '/subpackages/student-learning/tutoring/index?courseId=' + this.data.courseId });
  }
});
