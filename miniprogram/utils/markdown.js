// 轻量 Markdown -> rich-text 节点转换（无三方依赖）
// 后端 AI 回答按 Markdown 输出（标题/加粗/列表/代码块/公式），此前小程序按纯文本渲染，
// "**加粗**"、"### 标题"、"$公式$" 等符号原样露出。这里做面向阅读的降级渲染：
// 标题/加粗/行内代码/代码块/列表/引用/分割线还原样式，表格转行文本，LaTeX 去壳保留内容。
// 输出 rich-text 可用的 nodes 数组，样式全部内联（rich-text 不吃页面 wxss 类）。

const S = {
  p: 'display:block;margin:0 0 16rpx;line-height:1.7;word-break:break-word;',
  h1: 'display:block;font-size:34rpx;font-weight:700;margin:20rpx 0 12rpx;line-height:1.5;',
  h2: 'display:block;font-size:32rpx;font-weight:700;margin:20rpx 0 10rpx;line-height:1.5;',
  h3: 'display:block;font-size:30rpx;font-weight:600;margin:16rpx 0 8rpx;line-height:1.5;',
  strong: 'font-weight:700;',
  em: 'font-style:italic;',
  code: 'font-family:Menlo,monospace;font-size:26rpx;background:#EFEEE9;border-radius:6rpx;padding:2rpx 8rpx;word-break:break-all;',
  pre: 'display:block;font-family:Menlo,monospace;font-size:24rpx;background:#121614;color:#E8E8E4;border-radius:12rpx;padding:20rpx 24rpx;margin:12rpx 0 16rpx;white-space:pre-wrap;word-break:break-all;line-height:1.6;',
  li: 'display:block;margin:0 0 8rpx;line-height:1.7;',
  quote: 'display:block;border-left:6rpx solid #E6E4DD;color:#666560;padding:4rpx 0 4rpx 20rpx;margin:0 0 16rpx;line-height:1.7;',
  hr: 'display:block;height:1rpx;background:#E6E4DD;margin:20rpx 0;',
  tableRow: 'display:block;margin:0 0 6rpx;line-height:1.7;color:#444440;'
};

// 去掉 LaTeX 定界符但保留公式内容（小程序不渲染公式，露出 $ 符号更难读）
function stripLatexDelimiters(text) {
  return text
    .replace(/\$\$([\s\S]+?)\$\$/g, ' $1 ')
    .replace(/\$([^$\n]+?)\$/g, '$1')
    .replace(/\\\((.+?)\\\)/g, '$1')
    .replace(/\\\[([\s\S]+?)\\\]/g, ' $1 ');
}

// 行内解析：**加粗**、*斜体*、`代码`、[文字](链接)->文字、![图](url)->省略
function inlineNodes(text) {
  const nodes = [];
  let rest = text;
  const pattern = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\*([^*\n]+)\*)|(!?\[([^\]]*)\]\(([^)]*)\))/;
  while (rest) {
    const m = rest.match(pattern);
    if (!m) { nodes.push({ type: 'text', text: rest }); break; }
    if (m.index > 0) nodes.push({ type: 'text', text: rest.slice(0, m.index) });
    if (m[1]) nodes.push({ name: 'span', attrs: { style: S.strong }, children: [{ type: 'text', text: m[2] }] });
    else if (m[3]) nodes.push({ name: 'span', attrs: { style: S.code }, children: [{ type: 'text', text: m[4] }] });
    else if (m[5]) nodes.push({ name: 'span', attrs: { style: S.em }, children: [{ type: 'text', text: m[6] }] });
    else if (m[7]) {
      // 链接/图片：只保留可读文字（小程序内无法开外链）
      if (m[8]) nodes.push({ type: 'text', text: m[8] });
    }
    rest = rest.slice(m.index + m[0].length);
  }
  return nodes.length ? nodes : [{ type: 'text', text: '' }];
}

function block(name, style, children) {
  return { name: name || 'div', attrs: { style }, children };
}

// markdown 文本 -> rich-text nodes
function toNodes(markdown) {
  const text = stripLatexDelimiters(String(markdown || ''));
  const lines = text.split('\n');
  const nodes = [];
  let i = 0;
  let para = [];

  const flushPara = () => {
    if (!para.length) return;
    nodes.push(block('div', S.p, inlineNodes(para.join(' '))));
    para = [];
  };

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trimEnd();
    const trimmed = line.trim();

    // 代码块
    if (/^```/.test(trimmed)) {
      flushPara();
      i++;
      const code = [];
      while (i < lines.length && !/^```/.test(lines[i].trim())) { code.push(lines[i]); i++; }
      i++; // 跳过结尾 ```
      nodes.push(block('div', S.pre, [{ type: 'text', text: code.join('\n') }]));
      continue;
    }
    // 空行
    if (!trimmed) { flushPara(); i++; continue; }
    // 分割线
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) { flushPara(); nodes.push(block('div', S.hr, [])); i++; continue; }
    // 标题
    const hm = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (hm) {
      flushPara();
      const style = hm[1].length === 1 ? S.h1 : hm[1].length === 2 ? S.h2 : S.h3;
      nodes.push(block('div', style, inlineNodes(hm[2])));
      i++;
      continue;
    }
    // 引用
    if (/^>\s?/.test(trimmed)) {
      flushPara();
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) { quote.push(lines[i].trim().replace(/^>\s?/, '')); i++; }
      nodes.push(block('div', S.quote, inlineNodes(quote.join(' '))));
      continue;
    }
    // 无序/有序列表
    const ul = trimmed.match(/^[-*+]\s+(.*)$/);
    const ol = trimmed.match(/^(\d+)[.、)]\s+(.*)$/);
    if (ul || ol) {
      flushPara();
      let n = 0;
      while (i < lines.length) {
        const t = lines[i].trim();
        const mu = t.match(/^[-*+]\s+(.*)$/);
        const mo = t.match(/^(\d+)[.、)]\s+(.*)$/);
        if (!mu && !mo) break;
        n++;
        const marker = mu ? '• ' : (mo[1] + '. ');
        const content = mu ? mu[1] : mo[2];
        nodes.push(block('div', S.li, [{ type: 'text', text: marker }].concat(inlineNodes(content))));
        i++;
      }
      continue;
    }
    // 表格：转为"值 · 值 · 值"行文本（小程序 rich-text 表格排版不可控，降级为可读文本）
    if (/^\|.*\|$/.test(trimmed)) {
      flushPara();
      while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) {
        const rowText = lines[i].trim().replace(/^\||\|$/g, '');
        // 跳过分隔行 |---|---|
        if (!/^[\s:|-]+$/.test(rowText)) {
          const cells = rowText.split('|').map((c) => c.trim()).filter((c) => c);
          nodes.push(block('div', S.tableRow, [{ type: 'text', text: cells.join(' · ') }]));
        }
        i++;
      }
      continue;
    }
    // 普通段落行
    para.push(trimmed);
    i++;
  }
  flushPara();
  return nodes;
}

// 去 markdown 符号的纯文本（列表预览、通知等场景）
function toPlainText(markdown) {
  return stripLatexDelimiters(String(markdown || ''))
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^>\s?/gm, '')
    .replace(/^[-*+]\s+/gm, '')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\n{2,}/g, '\n')
    .trim();
}

module.exports = { toNodes, toPlainText };
