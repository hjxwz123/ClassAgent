// 从 StudentView.vue 抽出的纯展示型子组件（仅依赖 props/emits/slots + 图标，无父作用域闭包）。
// 均为渲染函数组件，行为与原内联定义完全一致。
import { defineComponent, h, type PropType } from "vue";
import { BookOpen, CheckCircle, Play, Sparkles } from "../../../icons";
import LoadingMark from "../../../components/LoadingMark.vue";

export const PageTitle = defineComponent({
  props: { title: { type: String, required: true }, sub: { type: String, default: "" } },
  setup(p, { slots }) {
    return () => h("div", { class: "page-title-row" }, [
      h("div", [h("h1", p.title), p.sub ? h("p", p.sub) : null]),
      h("div", { class: "page-title-actions" }, slots.default?.())
    ]);
  }
});

export const DefaultUserAvatar = defineComponent({
  setup() {
    return () => h("svg", { class: "default-user-avatar", viewBox: "0 0 64 64", role: "img", "aria-label": "默认头像" }, [
      h("rect", { width: 64, height: 64, rx: 32, fill: "#F9F8F6" }),
      h("circle", { cx: 32, cy: 25, r: 11, fill: "#00B8D4", opacity: "0.95" }),
      h("path", { d: "M16 53c2.8-10.2 9-15.4 16-15.4S45.2 42.8 48 53", fill: "#121614", opacity: "0.92" }),
      h("path", { d: "M48 12l1.8 4.4L54 18l-4.2 1.6L48 24l-1.8-4.4L42 18l4.2-1.6L48 12Z", fill: "#06B6D4" }),
      h("path", { d: "M18 14l1.1 2.7L22 18l-2.9 1.3L18 22l-1.1-2.7L14 18l2.9-1.3L18 14Z", fill: "#00E5FF" })
    ]);
  }
});

export const RingProgress = defineComponent({
  props: { value: { type: Number, default: 0 }, tone: { type: String, default: "primary" } },
  setup(p) {
    return () => {
      const value = Math.max(0, Math.min(100, Number(p.value || 0)));
      const stroke = p.tone === "success" ? "#2E7D32" : p.tone === "ai" ? "#00B8D4" : "#00B8D4";
      const radius = 28;
      const circumference = 2 * Math.PI * radius;
      return h("svg", { width: 72, height: 72, viewBox: "0 0 72 72", style: { transform: "rotate(-90deg)" } }, [
        h("circle", { cx: 36, cy: 36, r: radius, fill: "none", stroke: "rgba(140,148,143,.22)", "stroke-width": 8 }),
        h("circle", {
          cx: 36,
          cy: 36,
          r: radius,
          fill: "none",
          stroke,
          "stroke-linecap": "round",
          "stroke-width": 8,
          "stroke-dasharray": circumference,
          "stroke-dashoffset": circumference * (1 - value / 100)
        })
      ]);
    };
  }
});

export const RingBlock = defineComponent({
  props: {
    label: { type: String, required: true },
    value: { type: Number, default: 0 },
    text: { type: String, required: true },
    sub: { type: String, default: "" },
    tone: { type: String, default: "primary" }
  },
  setup(p) {
    return () => h("div", { class: ["ring-block", p.tone] }, [
      h("span", { class: "ring-wrap" }, [h(RingProgress, { value: p.value, tone: p.tone }), h("strong", p.text)]),
      h("span", p.label),
      h("small", p.sub)
    ]);
  }
});

export const EmptyState = defineComponent({
  props: { text: { type: String, default: "暂无数据" } },
  setup(p) {
    return () => h("div", { class: "empty" }, [h(BookOpen, { size: 28 }), h("span", p.text)]);
  }
});

export const QuickTile = defineComponent({
  props: { icon: { type: Object, required: true }, label: { type: String, required: true }, sub: { type: String, default: "" } },
  emits: ["click"],
  setup(p, { emit: update }) {
    return () => h("button", { type: "button", class: "quick-tile", onClick: () => update("click") }, [
      h("span", [h(p.icon as any, { size: 18 })]),
      h("strong", p.label),
      h("small", p.sub)
    ]);
  }
});

export const LessonItem = defineComponent({
  props: {
    lesson: { type: Object as PropType<any>, required: true },
    index: { type: Number, required: true },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false }
  },
  emits: ["open"],
  setup(p, { emit: update }) {
    return () => h("button", { type: "button", class: ["lesson-item", p.lesson.progress_percent > 0 && p.lesson.progress_percent < 100 ? "current" : "", p.loading ? "loading" : ""], disabled: p.disabled || p.loading, onClick: () => update("open") }, [
      h("b", String(p.index + 1).padStart(2, "0")),
      h("div", [h("strong", p.lesson.title), h("small", p.loading ? "正在打开课时..." : `第 ${p.lesson.current_page || 1} 页 · ${p.lesson.progress_percent || 0}%`)]),
      p.loading ? h(LoadingMark, { label: false, class: "inline-loading-mark" }) : p.lesson.progress_percent >= 100 ? h(CheckCircle, { size: 18 }) : h(Play, { size: 18 })
    ]);
  }
});

export const MiniMetric = defineComponent({
  props: {
    icon: { type: Object, required: true },
    label: { type: String, required: true },
    value: { type: [String, Number], required: true },
    tone: { type: String, default: "primary" }
  },
  setup(p) {
    return () => h("div", { class: ["mini-metric", p.tone] }, [
      h("span", { class: "mini-metric-icon" }, [h(p.icon as any, { size: 18 })]),
      h("div", { class: "mini-metric-copy" }, [h("strong", String(p.value)), h("span", p.label)])
    ]);
  }
});

export const EmptyGuide = defineComponent({
  setup() {
    return () => h("div", { class: "empty-guide" }, [h(Sparkles, { size: 38 }), h("strong", "等待题目"), h("span", "输入后开始辅导")]);
  }
});
