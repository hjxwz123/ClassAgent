// QA 流式引擎（供全局问答与课堂问答共用）。原为 StudentView 内联，抽出以缩短主文件并复用。
// 关键：delta 帧级合并——长答案有 2000+ SSE delta，逐个提交会强制回流+全列表重渲染，前端跟不上上游。
// 因此 delta 文本先进非响应式缓冲，每帧(rAF)最多向响应式状态提交一次，滚动跟随每帧至多一次，
// 使布局/渲染开销与 token 数解耦。这段逻辑对性能敏感，抽出时保持行为逐字不变。
import { reactive, type Ref } from "vue";

export type QaAttachment = { type: string; url: string; filename?: string; size_bytes?: number; ocr_text?: string };
export type ChatMessage = { id: number; role: "user" | "ai"; text: string; sources?: any[]; attachments?: QaAttachment[]; thought?: string; thoughtOpen?: boolean; record_id?: number; favorite?: boolean; feedback?: "positive" | "negative" | null; outOfScope?: boolean; streaming?: boolean; statusText?: string };
export type QaInputScope = "class" | "global";

type QaDeltaBuffer = { messages: Ref<ChatMessage[]>; text: string; thought: string; follow: boolean };

// follow 跟随滚动的两个钩子：读"是否贴近底部"(在 DOM 变更前读，避免强制回流) 与"必要时滚到底"。
export type QaScrollHooks = {
  isNearLatest: () => boolean;
  keepAtLatest: (wasNearLatest: boolean) => void;
};

export function useQaEngine(hooks: QaScrollHooks) {
  function patchChatMessage(messages: Ref<ChatMessage[]>, id: number, updater: (message: ChatMessage) => ChatMessage) {
    const index = messages.value.findIndex((item) => item.id === id);
    if (index < 0) return;
    messages.value.splice(index, 1, updater({ ...messages.value[index] }));
  }

  const qaDeltaBuffers = new Map<number, QaDeltaBuffer>();
  let qaDeltaFlushFrame = 0;
  function flushQaDeltas() {
    if (qaDeltaFlushFrame) {
      window.cancelAnimationFrame(qaDeltaFlushFrame);
      qaDeltaFlushFrame = 0;
    }
    if (!qaDeltaBuffers.size) return;
    for (const [id, buffer] of qaDeltaBuffers) {
      // 布局读(是否跟随)在本帧 DOM 变更之前做：布局是干净的，读取不触发强制回流
      const shouldFollow = buffer.follow ? hooks.isNearLatest() : false;
      patchChatMessage(buffer.messages, id, (message) => ({
        ...message,
        text: buffer.text ? `${message.text || ""}${buffer.text}` : message.text,
        thought: buffer.thought ? `${message.thought || ""}${buffer.thought}` : message.thought,
        thoughtOpen: buffer.thought ? true : message.thoughtOpen,
        statusText: "",
      }));
      if (buffer.follow) hooks.keepAtLatest(shouldFollow);
    }
    qaDeltaBuffers.clear();
  }
  function queueQaDelta(messages: Ref<ChatMessage[]>, id: number, data: any, follow: boolean) {
    let buffer = qaDeltaBuffers.get(id);
    if (!buffer) {
      buffer = { messages, text: "", thought: "", follow };
      qaDeltaBuffers.set(id, buffer);
    }
    buffer.follow = buffer.follow || follow;
    if (data?.type === "thought") buffer.thought += data?.text || "";
    else buffer.text += data?.text || "";
    if (!qaDeltaFlushFrame) {
      qaDeltaFlushFrame = window.requestAnimationFrame(() => {
        qaDeltaFlushFrame = 0;
        flushQaDeltas();
      });
    }
  }

  function applyQaStreamEvent(messages: Ref<ChatMessage[]>, messageId: number, event: string, data: any) {
    if (event === "stage") {
      // 首 token 前的进度提示（检索中→生成中），让用户不再面对空白干等
      patchChatMessage(messages, messageId, (message) => ({ ...message, statusText: data?.text || "" }));
      return;
    }
    if (event === "created") {
      // 会话/记录已在后端建好，提前挂上 record_id：即使中途停止，该消息也能收藏/反馈
      patchChatMessage(messages, messageId, (message) => ({ ...message, record_id: data?.record_id ?? message.record_id }));
      return;
    }
    if (event === "delta") {
      patchChatMessage(messages, messageId, (message) => data?.type === "thought"
        ? { ...message, thought: `${message.thought || ""}${data.text || ""}`, thoughtOpen: true, statusText: "" }
        : { ...message, text: `${message.text || ""}${data?.text || ""}`, statusText: "" });
      return;
    }
    if (event === "final") {
      patchChatMessage(messages, messageId, (message) => ({
        ...message,
        text: data.answer || message.text,
        thought: data.thinking_process || message.thought || "",
        sources: data.sources || [],
        attachments: data.attachments || message.attachments || [],
        record_id: data.record_id,
        outOfScope: data.is_out_of_scope,
      }));
    }
  }

  // —— 输入法/回车提交（中文输入法确认回车不应发送）——
  const questionCompositionState = reactive<Record<QaInputScope, { active: boolean; endedAt: number }>>({
    class: { active: false, endedAt: 0 },
    global: { active: false, endedAt: 0 },
  });
  function handleQuestionCompositionStart(scope: QaInputScope) {
    questionCompositionState[scope].active = true;
  }
  function handleQuestionCompositionEnd(scope: QaInputScope) {
    questionCompositionState[scope].active = false;
    questionCompositionState[scope].endedAt = Date.now();
  }
  function isImeConfirming(event: KeyboardEvent, scope: QaInputScope) {
    const legacyCode = event.keyCode || event.which;
    return questionCompositionState[scope].active || event.isComposing || legacyCode === 229;
  }
  function submitQuestionOnEnter(event: KeyboardEvent, scope: QaInputScope, submit: () => Promise<void>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    if (isImeConfirming(event, scope)) return;
    if (Date.now() - questionCompositionState[scope].endedAt < 120) {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    void submit();
  }
  // 输入框随内容自适应高度，上限交由 CSS 的 max-height 控制（超出后内部滚动）
  function resizeQuestionInput(el: HTMLTextAreaElement | null) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  return {
    patchChatMessage,
    flushQaDeltas,
    queueQaDelta,
    applyQaStreamEvent,
    questionCompositionState,
    handleQuestionCompositionStart,
    handleQuestionCompositionEnd,
    isImeConfirming,
    submitQuestionOnEnter,
    resizeQuestionInput,
  };
}
