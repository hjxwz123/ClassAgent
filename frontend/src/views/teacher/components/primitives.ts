// 从 TeacherView.vue 抽出的展示型子组件（渲染函数式）。行为与原内联定义一致。
// 原耦合页面状态的两个组件已改为 props 契约：LessonRows 接收 chapters（替代闭包 chapterName），LayerCard 接收 max（替代闭包 studentPayload）。
import { defineComponent, h, TransitionGroup, type PropType } from "vue";
import { BookOpen, CheckCircle, Clock, Inbox, RefreshCw, Wand2, XCircle } from "../../../icons";
import AppProgress from "../../../components/AppProgress.vue";
import { firstChar, fileIcon, relativeTime, statusClass, statusText, typeText } from "./helpers";

export const EmptyState = defineComponent({ props: { text: { type: String, required: true }, success: { type: Boolean, default: false } }, setup(p, { slots }) { return () => h("div", { class: "empty" }, [p.success ? h(CheckCircle, { size: 30 }) : h(Inbox, { size: 30 }), h("span", p.text), slots.default?.()]); } });

export const ProgressBar = defineComponent({ props: { value: { type: Number, required: true } }, setup(p) { return () => h(AppProgress, { class: "progress-bar", value: p.value, tone: p.value < 30 ? "danger" : p.value < 70 ? "warning" : "success" }); } });

export const MetricCard = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, value: { type: [String, Number], required: true }, sub: { type: String, default: "" }, tone: { type: String, default: "primary" }, danger: { type: Boolean, default: false } }, setup(p) { return () => h("article", { class: ["metric-card", p.tone, p.danger ? "danger" : ""] }, [h("div", [h("span", { class: "metric-icon" }, [h(p.icon as any, { size: 20 })]), h("span", p.label)]), h("strong", String(p.value)), h("small", p.sub)]); } });

export const CourseRequired = defineComponent(() => () => h("div", { class: "empty page-empty" }, [h(BookOpen, { size: 48 }), h("span", "请选择课程")]));

export const QuickAction = defineComponent({ props: { icon: { type: Object, required: true }, label: { type: String, required: true }, sub: { type: String, required: true } }, emits: ["click"], setup(p, { emit: update }) { return () => h("button", { class: "quick-action", onClick: () => update("click") }, [h(p.icon as any, { size: 22 }), h("strong", p.label), h("small", p.sub)]); } });

export const TaskList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, emits: ["retry"], setup(p, { emit: update }) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "task-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.id || item.title, class: "task-item" }, [h(item.status === "ready" ? CheckCircle : item.status === "failed" ? XCircle : item.status === "processing" ? RefreshCw : Clock, { size: 16, class: item.status }), h("span", item.title), h("small", statusText(item.status)), item.status === "failed" ? h("button", { class: "link-btn", onClick: () => update("retry", item) }, "重试") : null])) : [h(EmptyState, { key: "empty", text: "暂无任务" })] }); } });

export const LessonRows = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true }, studentTotal: { type: Number, required: true }, disabled: { type: Boolean, default: false }, chapters: { type: Array as PropType<any[]>, default: () => [] } }, emits: ["open"], setup(p, { emit: update }) {
  const chapterOf = (id?: number | null) => (p.chapters || []).find((chapter: any) => chapter.id === id)?.title || "未分章";
  return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "lesson-rows" }, { default: () => p.items.length ? p.items.slice(0, 6).map((item, index) => {
    const progress = Math.round(Number(item.average_progress || 0));
    const progressTone: "success" | "warning" | "danger" = progress >= 70 ? "success" : progress >= 30 ? "warning" : "danger";
    return h("button", { key: item.id, class: "lesson-row", disabled: p.disabled, onClick: () => update("open", item) }, [
      h("span", { class: "lesson-index" }, [h("b", String(index + 1).padStart(2, "0")), h("i")]),
      h("span", { class: "lesson-body" }, [
        h("span", { class: "lesson-title-line" }, [h("strong", item.title), h("span", { class: ["tag", statusClass(item.status)] }, statusText(item.status))]),
        h("small", `${chapterOf(item.chapter_id)} · ${item.page_count || 0} 页 · ${item.learned_count || 0}/${p.studentTotal} 人`),
        h("span", { class: "lesson-progress-line" }, [h(AppProgress, { value: progress, compact: true, tone: progressTone }), h("em", `${progress}%`)])
      ]),
      h("span", { class: "lesson-open-label" }, [h(Wand2, { size: 14 }), h("span", "脚本")])
    ]);
  }) : [h(EmptyState, { key: "empty", text: "暂无课时" })] }); } });

export const MaterialTypeList = defineComponent({ props: { stats: { type: Object as PropType<Record<string, number>>, required: true } }, setup(p) { return () => {
  const rows = ["pptx", "pdf", "docx", "txt"].map((type) => ({ type, count: Number(p.stats[type] || 0) }));
  const max = Math.max(1, ...rows.map((item) => item.count));
  return h(TransitionGroup, { name: "motion-list", tag: "div", class: "type-list" }, { default: () => rows.map((item) => h("div", { key: item.type, class: ["type-row", item.type] }, [
    h("span", { class: "type-icon" }, [h(fileIcon(item.type), { size: 16 })]),
    h("span", { class: "type-body" }, [h("strong", typeText(item.type)), h(AppProgress, { value: item.count, max, compact: true, tone: item.count ? "primary" : "danger" })]),
    h("b", `${item.count}份`)
  ])) });
}; } });

export const ActivityList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "activity-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.id || `${item.tone}-${item.time}-${item.text}`, class: "activity-item" }, [h("i", { class: item.tone }), h("span", item.text), h("small", relativeTime(item.time))])) : [h(EmptyState, { key: "empty", text: "暂无活动" })] }); } });

export const ProgressList = defineComponent({ props: { items: { type: Array as PropType<any[]>, required: true } }, setup(p) { return () => h(TransitionGroup, { name: "motion-list", tag: "div", class: "progress-list" }, { default: () => p.items.length ? p.items.map((item) => h("div", { key: item.student.id, class: "student-progress-row" }, [h("span", { class: "avatar mini" }, firstChar(item.student.nickname)), h("strong", item.student.nickname), h(ProgressBar, { value: item.progress_percent }), h("small", `${item.progress_percent}%`)])) : [h(EmptyState, { key: "empty", text: "暂无学生" })] }); } });

export const MaterialStatus = defineComponent({ props: { item: { type: Object, required: true } }, setup(p) { return () => h("small", { class: ["material-status", p.item.parse_status === "processing" ? "processing" : ""] }, p.item.parse_status === "ready" ? "脚本已生成 · 语音已合成 · 教学结构已就绪" : p.item.parse_status === "processing" ? "正在解析课件、生成脚本和教学结构，请稍候" : p.item.parse_status === "failed" ? "解析失败，可重新解析" : "待处理"); } });

export const LayerCard = defineComponent({ props: { label: { type: String, required: true }, value: { type: Number, required: true }, tone: { type: String, default: "primary" }, max: { type: Number, default: 1 } }, setup(p) { return () => h("article", { class: ["layer-card", p.tone] }, [h("strong", p.label), h("span", `${p.value} 人`), h(AppProgress, { value: p.value, max: Math.max(1, p.max), tone: p.tone as any })]); } });

export const InfoRow = defineComponent({ props: { label: { type: String, required: true }, value: { type: String, required: true } }, setup(p) { return () => h("div", { class: "info-row" }, [h("span", p.label), h("strong", p.value)]); } });
