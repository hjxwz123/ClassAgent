import { defineComponent, h, onBeforeUnmount, ref, Transition, type PropType } from "vue";
import { BookMarked, BookOpen, Check, ChevronDown, Copy, Sparkles } from "../../../icons";
import { renderRichText } from "../../../utils/richText";
import BrandLogo from "../../../components/BrandLogo.vue";

type QaAttachment = { type: string; url: string; filename?: string; size_bytes?: number; ocr_text?: string };
type ChatMessage = {
  id: number;
  role: "user" | "ai";
  text: string;
  sources?: any[];
  attachments?: QaAttachment[];
  thought?: string;
  thoughtOpen?: boolean;
  record_id?: number;
  favorite?: boolean;
  outOfScope?: boolean;
  streaming?: boolean;
};

export default defineComponent({
  name: "ChatList",
  props: {
    messages: { type: Array as PropType<ChatMessage[]>, default: () => [] },
    thinking: { type: Boolean, default: false },
    large: { type: Boolean, default: false },
    userAvatarUrl: { type: String, default: "" },
    userName: { type: String, default: "" }
  },
  emits: ["toggle-thought", "copy", "favorite", "feedback"],
  setup(p, { emit }) {
    const expandedSourceMessageIds = ref<number[]>([]);
    const burstingMessageIds = ref<number[]>([]);
    const burstTimers = new Map<number, number>();
    const imageFallback = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='84' height='84' viewBox='0 0 84 84'%3E%3Crect width='84' height='84' rx='16' fill='%23F9F8F6'/%3E%3Cpath d='M23 56l12-14 9 10 6-7 11 11H23z' fill='%2300B8D4' opacity='.72'/%3E%3Ccircle cx='56' cy='29' r='7' fill='%23121614' opacity='.82'/%3E%3C/svg%3E";
    function sourceLabel(source: any, index: number) {
      return source?.title || source?.material_title || source?.chapter_title || source?.course_name || `来源${index + 1}`;
    }
    function sourceKey(source: any, index: number) {
      const parts = [
        source?.type,
        source?.lesson_id,
        source?.lesson_page_id,
        source?.page_number,
        source?.chunk_id,
        source?.material_id,
        source?.chapter_id,
        source?.course_id,
        source?.title,
        source?.material_title,
        source?.chapter_title,
        source?.course_name
      ].filter((item) => item !== undefined && item !== null && item !== "");
      return parts.length ? parts.join(":") : `${sourceLabel(source, index)}:${index}`;
    }
    function uniqueSources(message: ChatMessage) {
      const seen = new Set<string>();
      const items: any[] = [];
      for (const [index, source] of (message.sources || []).entries()) {
        const key = sourceKey(source, index);
        if (seen.has(key)) continue;
        seen.add(key);
        items.push(source);
      }
      return items;
    }
    function sourcePreviewLimit() {
      return p.large ? 8 : 6;
    }
    function sourcesExpanded(message: ChatMessage) {
      return expandedSourceMessageIds.value.includes(message.id);
    }
    function toggleSources(message: ChatMessage) {
      if (sourcesExpanded(message)) {
        expandedSourceMessageIds.value = expandedSourceMessageIds.value.filter((id) => id !== message.id);
        return;
      }
      expandedSourceMessageIds.value = [...expandedSourceMessageIds.value, message.id];
    }
    function sourceSection(message: ChatMessage, classes: string, labelClass: string, tagClass = "tag") {
      const sources = uniqueSources(message);
      if (!sources.length) return null;
      const previewLimit = sourcePreviewLimit();
      const expanded = sourcesExpanded(message);
      const visibleSources = expanded ? sources : sources.slice(0, previewLimit);
      return h("div", { class: classes }, [
        h("span", { class: labelClass }, [h(BookOpen, { size: 14 }), "引用来源："]),
        ...visibleSources.map((source, index) => h("span", { class: tagClass, key: sourceKey(source, index) }, sourceLabel(source, index))),
        sources.length > previewLimit
          ? h(
            "button",
            {
              type: "button",
              class: `${tagClass} source-toggle`,
              "aria-expanded": expanded,
              onClick: () => toggleSources(message)
            },
            expanded ? "收起" : `展开全部 ${sources.length}`
          )
          : null
      ]);
    }
    function handleImageError(event: Event) {
      const image = event.currentTarget as HTMLImageElement;
      if (image.src === imageFallback) return;
      image.src = imageFallback;
    }
    function attachmentNodes(message: ChatMessage) {
      if (!message.attachments?.length) return null;
      return h("div", { class: "chat-attachments" }, message.attachments.map((item, index) => h("a", { key: `${item.url}-${index}`, href: item.url, target: "_blank", class: "chat-attachment" }, [
        h("img", { src: item.url, alt: item.filename || "图片", onError: handleImageError }),
        h("span", item.filename || `图片${index + 1}`)
      ])));
    }
    function triggerLogoBurst(message: ChatMessage) {
      if (message.role !== "ai") return;
      window.clearTimeout(burstTimers.get(message.id));
      burstingMessageIds.value = burstingMessageIds.value.filter((id) => id !== message.id);
      requestAnimationFrame(() => {
        burstingMessageIds.value = [...burstingMessageIds.value, message.id];
        burstTimers.set(message.id, window.setTimeout(() => {
          burstingMessageIds.value = burstingMessageIds.value.filter((id) => id !== message.id);
          burstTimers.delete(message.id);
        }, 720));
      });
    }
    function bubble(message: ChatMessage) {
      if (p.large && message.role === "user") {
        return h("div", { class: "chat-bubble bubble-user" }, [h("p", message.text), attachmentNodes(message)]);
      }
      if (p.large && message.role === "ai") {
        return h("div", { class: "chat-bubble bubble-ai" }, [
          message.thought ? h("button", { type: "button", class: "thought-toggle thinking-process", onClick: () => emit("toggle-thought", message) }, [h(Sparkles, { size: 13 }), "思考过程", h(ChevronDown, { size: 13, class: { rotate: message.thoughtOpen } })]) : null,
          h(Transition, { name: "thought-roll" }, { default: () => message.thought && message.thoughtOpen ? h("div", { class: "thought markdown-body", innerHTML: renderRichText(message.thought) }) : null }),
          h("div", { class: "ai-content-card" }, [
            message.outOfScope ? h("span", { class: "tag tag-warning" }, "可能超纲") : null,
            message.text
              ? h("div", { class: "ai-text markdown-body", innerHTML: renderRichText(message.text) })
              : h("div", { class: "ai-text streaming-placeholder" }, message.streaming ? "AI 正在生成..." : ""),
            sourceSection(message, "source-tags references-area", "source-label ref-label", "tag ref-tag"),
            h("div", { class: "msg-actions ai-action-bar" }, [
              h("button", { type: "button", title: "复制", class: "ai-action-btn", disabled: !message.text, onClick: () => emit("copy", message.text) }, [h(Copy, { size: 16 }), "复制"]),
              !message.streaming && message.record_id ? h("button", { type: "button", title: message.favorite ? "已收藏" : "收藏", class: "ai-action-btn", onClick: () => emit("favorite", message) }, [h(BookMarked, { size: 16 }), message.favorite ? "已收藏" : "收藏"]) : null,
              !message.streaming && message.record_id ? h("button", { type: "button", title: "有用", class: "ai-action-btn success", onClick: () => emit("feedback", message, "positive") }, [h(Check, { size: 16 }), "有用"]) : null
            ])
          ])
        ]);
      }
      const body = [
        message.thought ? h("button", { type: "button", class: "thought-toggle", onClick: () => emit("toggle-thought", message) }, [h(Sparkles, { size: 13 }), "思考过程", h(ChevronDown, { size: 13, class: { rotate: message.thoughtOpen } })]) : null,
        h(Transition, { name: "thought-roll" }, { default: () => message.thought && message.thoughtOpen ? h("div", { class: "thought markdown-body", innerHTML: renderRichText(message.thought) }) : null }),
        message.outOfScope ? h("span", { class: "tag tag-warning" }, "可能超纲") : null,
        message.role === "ai"
          ? (message.text ? h("div", { class: "ai-text markdown-body", innerHTML: renderRichText(message.text) }) : h("div", { class: "ai-text streaming-placeholder" }, message.streaming ? "AI 正在生成..." : ""))
          : [h("p", message.text), attachmentNodes(message)],
        sourceSection(message, "source-tags", "source-label"),
        h("div", { class: "msg-actions" }, [
          h("button", { type: "button", title: "复制", disabled: !message.text, onClick: () => emit("copy", message.text) }, [h(Copy, { size: 13 }), "复制"]),
          message.role === "ai" && p.large && !message.streaming && message.record_id ? h("button", { type: "button", title: message.favorite ? "已收藏" : "收藏", onClick: () => emit("favorite", message) }, [h(BookMarked, { size: 13 }), message.favorite ? "已收藏" : "收藏"]) : null,
          message.role === "ai" && p.large && !message.streaming && message.record_id ? h("button", { type: "button", title: "有用", class: "success", onClick: () => emit("feedback", message, "positive") }, [h(Check, { size: 13 }), "有用"]) : null
        ])
      ];
      return h("div", { class: "chat-bubble" }, body);
    }
    function defaultUserAvatar() {
      return h("svg", { class: "default-user-avatar", viewBox: "0 0 64 64", role: "img", "aria-label": "默认头像" }, [
        h("rect", { width: 64, height: 64, rx: 32, fill: "#F9F8F6" }),
        h("circle", { cx: 32, cy: 25, r: 11, fill: "#00B8D4", opacity: "0.95" }),
        h("path", { d: "M16 53c2.8-10.2 9-15.4 16-15.4S45.2 42.8 48 53", fill: "#121614", opacity: "0.92" }),
        h("path", { d: "M48 12l1.8 4.4L54 18l-4.2 1.6L48 24l-1.8-4.4L42 18l4.2-1.6L48 12Z", fill: "#06B6D4" }),
        h("path", { d: "M18 14l1.1 2.7L22 18l-2.9 1.3L18 22l-1.1-2.7L14 18l2.9-1.3L18 14Z", fill: "#00E5FF" })
      ]);
    }
    function avatar(message: ChatMessage) {
      if (message.role === "user") {
        return h("span", { class: ["chat-avatar", "avatar-user"] }, [
          p.userAvatarUrl
            ? h("img", { class: "chat-avatar-image", src: p.userAvatarUrl, alt: p.userName || "用户头像" })
            : defaultUserAvatar()
        ]);
      }
      return h(
        "button",
        {
          type: "button",
          class: ["chat-avatar", "avatar-ai", { "is-bursting": burstingMessageIds.value.includes(message.id) }],
          title: "智学黑板",
          "aria-label": "触发助手图标动画",
          onClick: () => triggerLogoBurst(message)
        },
        [h(BrandLogo, { class: "chat-avatar-logo" })]
      );
    }
    onBeforeUnmount(() => {
      burstTimers.forEach((timer) => window.clearTimeout(timer));
      burstTimers.clear();
    });
    return () => {
      const hasStreamingMessage = p.messages.some((message) => message.streaming);
      return h("div", { class: ["chat-list", p.large ? "large" : ""] }, [
        ...p.messages.map((message) => h("article", { key: message.id, class: ["chat-msg", p.large ? "message-row" : "", message.role] }, message.role === "user" ? [avatar(message), bubble(message)] : [avatar(message), bubble(message)])),
        p.thinking && !hasStreamingMessage ? h("div", { class: "thinking ai-thinking-border" }, [h("i", { class: "dot-1" }), h("i", { class: "dot-2" }), h("i", { class: "dot-3" }), h("span", "AI 正在思考...")]) : null
      ]);
    };
  }
});
