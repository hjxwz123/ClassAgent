// 出题（quiz.generate / wrong_book_practice）非阻塞进度：对齐网页端
// composables/useGenerationProgress.ts + GenerationProgressPanel.vue 的口径。
// 后端 POST /learning/quizzes/generate 同步档直接返回卷（含 id）；异步档返回 { task_id, status }，
// 需轮询 GET /learning/generation-tasks/{id}（detail.step 推进 preparing→…→assembling）。
const api = require('./api');

// 与后端 app/services/ai.py generate_quiz_questions 的 on_step 上报一一对应
const STEP_ORDER = ['preparing', 'drafting', 'reviewing', 'refining', 'assembling'];
// 5 个 step 收敛成 4 行（drafting/refining 都是"AI 在写候选题"，合并展示），与网页端一致
const ROWS = [
  { key: 'preparing', label: '分析知识点与课程素材', covers: ['preparing'] },
  { key: 'drafting', label: 'AI 生成候选题目', covers: ['drafting', 'refining'] },
  { key: 'reviewing', label: '质量把关', covers: ['reviewing'] },
  { key: 'assembling', label: '组卷完成', covers: ['assembling'] }
];

// 由当前 step + status 计算 4 行的状态（pending/active/done），逐字对齐网页 rowsFor()
function stepRows(step, status) {
  const currentIndex = STEP_ORDER.indexOf(step || 'preparing');
  return ROWS.map(function (row) {
    const indices = row.covers.map(function (k) { return STEP_ORDER.indexOf(k); });
    const rowMin = Math.min.apply(null, indices);
    const rowMax = Math.max.apply(null, indices);
    let state;
    if (status === 'ready') state = 'done';
    else if (status === 'failed') state = currentIndex > rowMax ? 'done' : 'pending';
    else if (currentIndex > rowMax) state = 'done';
    else if (currentIndex >= rowMin) state = 'active';
    else state = 'pending';
    return { key: row.key, label: row.label, state: state };
  });
}

function extractStep(res) {
  if (res && res.detail && res.detail.step) return res.detail.step;
  if (res && res.generation_task && res.generation_task.detail && res.generation_task.detail.step) return res.generation_task.detail.step;
  return null;
}

function sleep(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }

// 轮询指定出题任务直到 ready/failed/timeout/cancelled（对齐网页 pollGenerationProgress）。
// opts.alive() 返回 false 时（用户已离开/关闭面板）尽快退出，让上层 submit 及时收尾、解锁按钮。
async function pollTask(taskId, opts) {
  opts = opts || {};
  const intervalMs = opts.intervalMs || 2500;
  const timeoutMs = opts.timeoutMs || 300000;
  const onTick = opts.onTick || function () {};
  const alive = opts.alive || function () { return true; };
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await sleep(intervalMs);
    if (!alive()) return { status: 'cancelled', step: null };
    let res = null;
    try {
      res = await api.get('/learning/generation-tasks/' + taskId);
    } catch (err) {
      const msg = (err && err.message) || '';
      // 无权/不存在/登录过期是终态；网络抖动等下一拍再查
      if (msg.indexOf('无权') >= 0 || msg.indexOf('不存在') >= 0 || msg.indexOf('过期') >= 0) return { status: 'failed', step: null };
      continue;
    }
    if (!res) continue;
    const step = extractStep(res);
    onTick(step, String(res.status || 'processing'));
    if (Number(res.id) > 0) return { status: 'ready', step: step, quizId: Number(res.id) };
    if (String(res.status) === 'failed') return { status: 'failed', step: step };
  }
  return { status: 'timeout', step: null };
}

// ── 页面驱动：把"提交出题 → 面板进度 → 完成/失败"整套流程收敛在这里 ──
// 约定 page.data 含 genShow/genTitle/genStatus/genStep；page 在 onUnload/onHide 调 stopProgress(page)。
// 会话令牌 page._genSeq：每次 submit 领一个 token，_cancel（离开页/关面板）自增令牌使其失效；
// 全流程按 token 判 alive，取消后不再 setData、不强制跳转、并让 submit 尽快 resolve 解锁按钮。

// 同步档下 POST 会阻塞到出题完成、拿不到 task_id，靠并发轮询任务列表把 detail.step 实时喂进面板；
// 异步档下 POST 秒回，本轮询随 stopList 立即停止，无额外开销。
function _startList(page) {
  page._genListStopped = false;
  const poll = function () {
    if (page._genListStopped) return;
    api.get('/learning/generation-tasks', { course_id: page.data.courseId }).then(function (items) {
      if (page._genListStopped || !page.data.genShow) return;
      const list = items || [];
      const active = list.find(function (t) { return t.status === 'processing' || t.status === 'pending'; }) || list[0];
      if (active && active.detail && active.detail.step) {
        page.setData({ genStep: active.detail.step, genStatus: active.status === 'failed' ? 'processing' : (active.status || 'processing') });
      }
    }).catch(function () {}).then(function () {
      if (!page._genListStopped) page._genListTimer = setTimeout(poll, 2500);
    });
  };
  page._genListTimer = setTimeout(poll, 1500);
}
function _stopList(page) {
  page._genListStopped = true;
  if (page._genListTimer) { clearTimeout(page._genListTimer); page._genListTimer = null; }
}
// 作废当前进行中的出题会话（离开页面/关闭面板）：自增令牌 + 停列表轮询
function _cancel(page) {
  page._genSeq = (page._genSeq || 0) + 1;
  _stopList(page);
}
function stopProgress(page) { _cancel(page); }
// 用户点面板关闭：作废会话并隐藏面板（出题仍在后台跑，完成后不再强制跳转）
function dismissProgress(page) { _cancel(page); page.setData({ genShow: false }); }

async function _track(page, result, alive) {
  if (result && Number(result.id) > 0) return { status: 'ready', quizId: Number(result.id) };
  const taskId = Number(result && result.task_id);
  if (taskId > 0) {
    return await pollTask(taskId, {
      alive: alive,
      onTick: function (step, status) {
        if (!alive()) return;
        page.setData({ genStep: step || 'preparing', genStatus: status === 'ready' ? 'ready' : (status === 'failed' ? 'failed' : 'processing') });
      }
    });
  }
  return { status: 'queued' };
}

// request(): () => Promise，内部发 postLong；onReady(quizId)：完成后的跳转（会话仍有效时才触发）。
// 返回 { status: 'ready'|'failed'|'timeout'|'queued'|'cancelled'|'error', quizId?, error? } 供调用方弹提示。
async function submit(page, options) {
  const title = options.title || 'AI 出题';
  const token = page._genSeq = (page._genSeq || 0) + 1;
  const alive = function () { return page._genSeq === token; };
  page.setData({ genShow: true, genTitle: title, genStatus: 'processing', genStep: 'preparing' });
  _startList(page);
  let outcome;
  try {
    const result = await options.request();
    _stopList(page);
    outcome = await _track(page, result, alive);
  } catch (err) {
    _stopList(page);
    if (alive()) page.setData({ genStatus: 'failed' });
    return { status: 'error', error: err };
  }
  // 已离开页面/关闭面板：不跳转、不再动面板
  if (!alive() || outcome.status === 'cancelled') return { status: 'cancelled' };
  if (outcome.status === 'ready') {
    page.setData({ genStatus: 'ready', genStep: 'assembling' });
    // 让"组卷完成"态可见一瞬再跳转；这 500ms 内若被取消则不跳转
    setTimeout(function () {
      if (!alive()) return;
      page.setData({ genShow: false });
      if (typeof options.onReady === 'function') options.onReady(outcome.quizId);
    }, 500);
    return { status: 'ready', quizId: outcome.quizId };
  }
  if (outcome.status === 'failed') { page.setData({ genStatus: 'failed' }); return { status: 'failed' }; }
  // timeout / queued：面板收起，交给列表刷新兜底
  page.setData({ genShow: false });
  return { status: outcome.status };
}

module.exports = { STEP_ORDER, stepRows, extractStep, pollTask, submit, stopProgress, dismissProgress };
