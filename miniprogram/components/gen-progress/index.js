// 出题进度浮层：右下角 4 行步骤清单，对齐网页端 GenerationProgressPanel。
// 由页面传入 show/title/status/step，内部据 status+step 算出各行状态。
const gen = require('../../utils/generation');

Component({
  properties: {
    show: { type: Boolean, value: false },
    title: { type: String, value: 'AI 出题' },
    status: { type: String, value: 'processing' }, // processing | ready | failed
    step: { type: String, value: 'preparing' }
  },
  data: { rows: [] },
  lifetimes: {
    attached() {
      this.setData({ rows: gen.stepRows(this.data.step, this.data.status) });
    }
  },
  observers: {
    'status, step': function (status, step) {
      this.setData({ rows: gen.stepRows(step, status) });
    }
  },
  methods: {
    onDismiss() { this.triggerEvent('dismiss'); }
  }
});
