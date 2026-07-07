// 从 AdminView.vue 抽出的纯展示/表单型子组件（仅依赖 props + 顶部 import，无父作用域响应式闭包）。
// 均为渲染函数组件，行为与原内联定义完全一致。
import { defineComponent, h } from "vue";
import { Inbox } from "../../../icons";
import AppCheckbox from "../../../components/AppCheckbox.vue";
import AppSelect from "../../../components/AppSelect.vue";
import AppSlider from "../../../components/AppSlider.vue";

// 系统设置项的动态控件：按 item.type 渲染不同输入控件，值读写传入的 drafts 草稿对象。
export const SettingControl = defineComponent({
  props: { item: { type: Object, required: true }, drafts: { type: Object, required: true } },
  setup(innerProps) {
    return () => {
      const key = (innerProps.item as any).key;
      const item = innerProps.item as any;
      const drafts = innerProps.drafts as Record<string, any>;
      const update = (event: Event) => { drafts[key] = (event.target as HTMLInputElement).value; };
      if (item.type === "number") {
        const clampNumber = (raw: number) => {
          let value = Number.isFinite(raw) ? raw : 0;
          if (typeof item.min === "number" && value < item.min) value = item.min;
          if (typeof item.max === "number" && value > item.max) value = item.max;
          return value;
        };
        return h("input", { class: "input form-control", type: "number", min: item.min, max: item.max, step: item.step, value: drafts[key], onInput: (event: Event) => { drafts[key] = clampNumber(Number((event.target as HTMLInputElement).value)); } });
      }
      if (item.type === "range") return h(AppSlider, { modelValue: Number(drafts[key] || 0), min: item.min, max: item.max, "onUpdate:modelValue": (value: number) => { drafts[key] = value; } });
      if (item.type === "toggle") return h(AppCheckbox, { modelValue: !!drafts[key], label: "启用", variant: "switch", "onUpdate:modelValue": (value: boolean) => { drafts[key] = value; } });
      if (item.type === "textarea") return h("textarea", { class: "textarea form-control", value: drafts[key], onInput: update });
      if (item.type === "select") return h(AppSelect, { modelValue: drafts[key], options: item.options.map((option: string) => ({ label: option, value: option })), "onUpdate:modelValue": (value: unknown) => { drafts[key] = value; } });
      if (item.type === "checks") return h("div", { class: "checkbox-group" }, item.options.map((option: string) => h(AppCheckbox, { label: option, modelValue: Array.isArray(drafts[key]) && drafts[key].includes(option), "onUpdate:modelValue": (checked: boolean) => {
        const current = Array.isArray(drafts[key]) ? [...drafts[key]] : [];
        drafts[key] = checked ? [...new Set([...current, option])] : current.filter((value) => value !== option);
      } })));
      if (item.type === "json") return h("textarea", { class: "textarea form-control", value: JSON.stringify(drafts[key] || {}, null, 2), onInput: (event: Event) => { try { drafts[key] = JSON.parse((event.target as HTMLTextAreaElement).value || "{}"); } catch { drafts[key] = (event.target as HTMLTextAreaElement).value; } } });
      return h("input", { class: "input form-control", value: drafts[key], onInput: update });
    };
  }
});

export const TrendingUpIcon = defineComponent(() => () => h("span", { class: "trend-dot" }));

export const MetricCard = defineComponent({
  props: { icon: { type: Object, required: true }, label: { type: String, required: true }, value: { type: [String, Number], required: true }, trend: { type: String, default: "" }, tone: { type: String, default: "primary" }, danger: { type: Boolean, default: false } },
  setup(p) {
    return () => h("article", { class: ["metric-card", p.tone, p.danger ? "danger" : ""] }, [h("div", [h("span", { class: "metric-icon" }, [h(p.icon as any, { size: 20 })]), h("span", p.label)]), h("strong", String(p.value)), h("small", [h(TrendingUpIcon), p.trend])]);
  }
});

export const EmptyState = defineComponent({ props: { text: { type: String, required: true } }, setup(p) { return () => h("div", { class: "empty" }, [h(Inbox, { size: 28 }), h("span", p.text)]); } });

export const InfoRow = defineComponent({ props: { label: { type: String, required: true }, value: { type: String, required: true } }, setup(p) { return () => h("div", { class: "info-row" }, [h("span", p.label), h("strong", p.value)]); } });
