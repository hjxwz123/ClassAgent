// 微信小程序 SSE 流式客户端：wx.request({ enableChunked: true }) + onChunkReceived
// 用于 AI 问答等长耗时生成接口——逐 token 打字机渲染，替代"干等完整回答 + 30s 必超时"。
const { API_BASE } = require('../config');
const auth = require('./auth');
const api = require('./api');

// —— 增量 UTF-8 解码 ——
// 小程序运行时没有 TextDecoder；分包可能把多字节汉字从中间截断，
// 因此解码时保留末尾不完整序列的字节，与下一包拼接后再解。
function utf8Decode(bytes) {
  let out = '';
  let i = 0;
  while (i < bytes.length) {
    const b = bytes[i];
    let cp;
    let extra;
    if (b < 0x80) { cp = b; extra = 0; }
    else if ((b & 0xe0) === 0xc0) { cp = b & 0x1f; extra = 1; }
    else if ((b & 0xf0) === 0xe0) { cp = b & 0x0f; extra = 2; }
    else { cp = b & 0x07; extra = 3; }
    if (i + extra >= bytes.length) break; // 末尾序列不完整（正常流由 createChunkDecoder 预先截走，此处兜底畸形字节）
    for (let j = 1; j <= extra; j++) cp = (cp << 6) | (bytes[i + j] & 0x3f);
    i += extra + 1;
    if (cp > 0xffff) {
      cp -= 0x10000;
      out += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff));
    } else {
      out += String.fromCharCode(cp);
    }
  }
  return out;
}

function createChunkDecoder() {
  let tail = null; // Uint8Array | null，上一包末尾的不完整多字节序列
  return function decode(arrayBuffer) {
    const fresh = new Uint8Array(arrayBuffer);
    let all;
    if (tail && tail.length) {
      all = new Uint8Array(tail.length + fresh.length);
      all.set(tail, 0);
      all.set(fresh, tail.length);
    } else {
      all = fresh;
    }
    // 从末尾向前最多回看 3 字节，找到可能被截断的多字节序列起点
    let end = all.length;
    for (let i = all.length - 1; i >= 0 && i >= all.length - 4; i--) {
      const b = all[i];
      if ((b & 0x80) === 0) break; // ASCII，完整
      if ((b & 0xc0) === 0xc0) {   // 首字节
        const need = (b & 0xf0) === 0xf0 ? 4 : ((b & 0xe0) === 0xe0 ? 3 : 2);
        if (i + need > all.length) end = i; // 序列不完整，留到下一包
        break;
      }
      // 10xxxxxx 续字节，继续向前找首字节
    }
    tail = end < all.length ? all.slice(end) : null;
    return utf8Decode(all.subarray(0, end));
  };
}

// —— SSE 流式 POST ——
// onEvent(event, data) 按事件到达顺序回调；返回 { abort() }。
// resolve：流正常结束；reject：网络失败/HTTP 错误/后端 error 事件（携带 err.aborted 标记主动中止）。
// 老基础库不支持 chunked 时 reject(err.code === 'NO_CHUNK')，调用方可回退非流式接口。
function streamPost(path, body, onEvent) {
  const handle = { abort: function () {} };
  const promise = new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream'
    };
    const token = auth.getToken();
    if (token) header.Authorization = 'Bearer ' + token;

    const decode = createChunkDecoder();
    let buffer = '';
    let streamError = null;
    let aborted = false;
    let gotChunk = false;

    const consume = (block) => {
      const lines = block.split(/\r?\n/);
      let event = 'message';
      const dataLines = [];
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.indexOf('event:') === 0) event = line.slice(6).trim() || 'message';
        else if (line.indexOf('data:') === 0) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) return;
      let data = null;
      try { data = JSON.parse(dataLines.join('\n')); } catch (e) { return; }
      if (event === 'error') {
        streamError = new Error((data && data.message) || '生成失败，请稍后重试');
        return;
      }
      try { onEvent(event, data); } catch (e) { /* 页面回调异常不打断流 */ }
    };

    const feed = (text) => {
      buffer += text;
      let sep = buffer.search(/\r?\n\r?\n/);
      while (sep >= 0) {
        const block = buffer.slice(0, sep);
        const m = buffer.slice(sep).match(/^\r?\n\r?\n/);
        buffer = buffer.slice(sep + (m ? m[0].length : 2));
        consume(block);
        sep = buffer.search(/\r?\n\r?\n/);
      }
    };

    const task = wx.request({
      url: API_BASE + path,
      method: 'POST',
      data: body || {},
      header,
      enableChunked: true,
      responseType: 'arraybuffer',
      // 覆盖检索 + 全量生成的最长耗时
      timeout: 300000,
      success(res) {
        if (res.statusCode === 401) {
          api.handleUnauthorized();
          reject(new Error('登录已过期，请重新登录'));
          return;
        }
        if (res.statusCode >= 400) {
          reject(new Error('服务暂时不可用，请稍后重试（' + res.statusCode + '）'));
          return;
        }
        if (buffer.trim()) consume(buffer);
        if (streamError) reject(streamError);
        else resolve();
      },
      fail(err) {
        if (aborted) {
          const e = new Error('已停止生成');
          e.aborted = true;
          reject(e);
          return;
        }
        const msg = err && err.errMsg && err.errMsg.indexOf('timeout') >= 0
          ? '生成超时，请稍后重试'
          : '网络异常，请检查连接';
        reject(new Error(msg));
      }
    });

    if (!task || typeof task.onChunkReceived !== 'function') {
      // 基础库过旧：中止并让调用方回退非流式
      if (task && task.abort) task.abort();
      const e = new Error('当前微信版本不支持流式，将使用普通模式');
      e.code = 'NO_CHUNK';
      reject(e);
      return;
    }

    task.onChunkReceived((res) => {
      gotChunk = true;
      const text = decode(res.data);
      if (text) feed(text);
    });

    handle.abort = function () {
      aborted = true;
      try { task.abort(); } catch (e) { /* 已结束 */ }
    };
  });
  handle.finished = promise;
  return handle;
}

module.exports = { streamPost };
