// 从 StudentView.vue 抽出的列表/卡片型子组件。仅依赖 props/emits + 图标 + utils 纯函数，无父作用域响应式闭包。
// 行为与原内联定义完全一致。
import { computed, defineComponent, h, ref, type PropType } from "vue";
import { Check, Clock, Eye, Play, RefreshCw } from "../../../icons";
import { relativeTime } from "../../../utils/datetime";
import { answerIndexSet, rawReferenceValue, referenceDisplayText, statusText } from "../../../utils/quiz";
import { EmptyState } from "./primitives";

// 个人主页学习动态时间线。
export const ActivityTimeline = defineComponent({
  props: { items: { type: Array as PropType<any[]>, default: () => [] } },
  setup(p) {
    return () => h("article", { class: "profile-activity-card" }, [
      h("div", { class: "section-head" }, [h("h2", [h(Clock, { size: 18 }), "学习动态"])]),
      p.items.length
        ? p.items.map((item) => h("div", { class: "profile-timeline-item", key: `${item.type}-${item.title}-${item.time}` }, [
          h("i"),
          h("div", { class: "profile-timeline-content" }, [
            h("div", { class: "profile-timeline-head" }, [
              h("strong", item.title || "学习记录"),
              h("time", relativeTime(item.time))
            ]),
            item.meta ? h("p", item.meta) : null
          ])
        ]))
        : h(EmptyState, { text: "暂无动态" })
    ]);
  }
});

// 辅导页历史题目条。
export const HistoryStrip = defineComponent({
  props: { title: { type: String, required: true }, items: { type: Array as PropType<any[]>, default: () => [] } },
  emits: ["pick"],
  setup(p, { emit: update }) {
    return () => h("article", { class: "tutoring-history-card" }, [
      h("header", { class: "tutoring-history-head" }, [
        h("h2", [h(Clock, { size: 18 }), p.title]),
        h("span", { class: "tag" }, `${p.items.length} 条`)
      ]),
      p.items.length ? h("div", { class: "tutoring-history-grid" }, p.items.slice(0, 6).map((item) => h("button", { type: "button", key: item.id, class: "tutoring-history-item", onClick: () => update("pick", item) }, [
        h("strong", item.corrected_text || item.ocr_text || item.raw_text || "题目"),
        h("small", relativeTime(item.created_at))
      ]))) : h(EmptyState, { text: "暂无记录" })
    ]);
  }
});

// 测验/练习卡片：三态（未开始/进行中/已完成），已完成挂"再练一卷"。
export const QuizCard = defineComponent({
  props: {
    quiz: { type: Object as PropType<any>, required: true },
    hasDraft: { type: Boolean, default: false },
    retaking: { type: Boolean, default: false }
  },
  emits: ["open", "review", "retake"],
  setup(p, { emit: update }) {
    const attempts = computed(() => Array.isArray(p.quiz.attempts) ? p.quiz.attempts : []);
    const latestAttempt = computed(() => p.quiz.latest_attempt || p.quiz.last_attempt || p.quiz.best_attempt || attempts.value[0] || null);
    const attempted = computed(() => Boolean(latestAttempt.value?.id));
    const status = computed(() => (attempted.value ? "done" : p.hasDraft ? "doing" : "todo"));
    const meta = computed(() => {
      const parts: string[] = [];
      const count = Number(p.quiz.question_count || p.quiz.questions_count || 0);
      if (count) parts.push(`${count} 题`);
      if (p.quiz.total_score) parts.push(`${Math.round(Number(p.quiz.total_score))} 分`);
      const latest = latestAttempt.value;
      if (latest?.id) parts.push(`最近 ${Math.round(Number(latest.score || 0))} 分 · 对 ${latest.correct_count ?? "-"}/${latest.total_count ?? "-"}`);
      return parts.join(" · ");
    });
    const attemptLabel = (item: any, index: number) => {
      const order = attempts.value.length - index;
      const score = item?.score !== undefined ? `${Math.round(Number(item.score))}分` : "解析";
      return attempts.value.length > 1 ? `第${order}次 ${score}` : `解析 ${score}`;
    };
    return () => h("article", { class: ["quiz-card", `quiz-status-${status.value}`] }, [
      h("h2", p.quiz.title),
      h("p", meta.value || p.quiz.description || statusText(p.quiz.status || "published")),
      h("footer", [
        h("span", { class: ["tag", status.value === "done" ? "tag-success" : status.value === "doing" ? "tag-warning" : ""] }, status.value === "done" ? "已完成" : status.value === "doing" ? "进行中" : "未开始"),
        attempts.value.slice(0, 3).map((item: any, index: number) => h("button", {
          type: "button",
          class: "btn btn-secondary btn-sm",
          onClick: () => update("review", item.id),
        }, [h(Eye, { size: 14 }), attemptLabel(item, index)])),
        attempted.value
          ? h("button", { type: "button", class: "btn btn-ghost btn-sm", "data-loading": p.retaking, disabled: p.retaking, onClick: () => { if (!p.retaking) update("retake"); } }, [h(RefreshCw, { size: 14 }), "再练一卷"])
          : h("button", { type: "button", class: "btn btn-primary btn-sm", onClick: () => update("open") }, [h(Play, { size: 14 }), status.value === "doing" ? "继续作答" : "开始作答"])
      ])
    ]);
  }
});

// 错题卡：三态掌握 + 连对进度点 + 点击卡内展开完整题目/正确答案/解析。
export const WrongCard = defineComponent({
  props: { item: { type: Object as PropType<any>, required: true }, generating: { type: Boolean, default: false } },
  emits: ["practice"],
  setup(p, { emit: update }) {
    const open = ref(false);
    const question = computed(() => p.item.question || {});
    const mastery = computed<"pending" | "consolidating" | "resolved">(() => {
      if (p.item.mastery === "consolidating" || p.item.mastery === "resolved" || p.item.mastery === "pending") return p.item.mastery;
      if (p.item.is_resolved) return "resolved";
      return Number(p.item.correct_streak || 0) >= 1 ? "consolidating" : "pending";
    });
    const masteryText = computed(() => ({ pending: "未掌握", consolidating: "巩固中", resolved: "已掌握" }[mastery.value]));
    // 艾宾浩斯复习进度：走完整条曲线（review_total 档）即掌握；is_due 表示到复习时间。
    const reviewTotal = computed(() => Math.max(1, Number(p.item.review_total || 6)));
    const reviewStage = computed(() => Math.min(reviewTotal.value, Math.max(0, Number(p.item.review_stage ?? p.item.correct_streak ?? 0))));
    const isDue = computed(() => !!p.item.is_due);
    function nextReviewLabel() {
      if (isDue.value || mastery.value === "resolved") return "";
      const raw = p.item.next_review_at;
      if (!raw) return "";
      const target = new Date(raw).getTime();
      if (Number.isNaN(target)) return "";
      const days = Math.ceil((target - Date.now()) / 86400000);
      if (days <= 0) return "";
      return days === 1 ? "明天复习" : `${days} 天后复习`;
    }
    const isChoice = computed(() => ["single_choice", "multiple_choice", "judge"].includes(question.value.question_type));
    const options = computed(() => (Array.isArray(question.value.options) ? question.value.options : []));
    const correctSet = computed(() => answerIndexSet(rawReferenceValue(question.value), options.value));
    function renderExpanded() {
      const referenceRow = { question: question.value, correct_answer: rawReferenceValue(question.value) };
      return h("section", { class: "wrong-card-detail" }, [
        isChoice.value && options.value.length
          ? h("div", { class: "exam-review-options" }, options.value.map((option: any, index: number) => h("div", {
            key: index,
            class: ["exam-review-opt", correctSet.value.has(index) ? "is-correct" : ""]
          }, [
            h("span", { class: "exam-review-letter" }, String.fromCharCode(65 + index)),
            h("span", { class: "exam-review-text" }, typeof option === "object" ? option.text || option.label || JSON.stringify(option) : String(option)),
            correctSet.value.has(index) ? h("span", { class: "exam-review-badge correct" }, [h(Check, { size: 12 }), "正确答案"]) : null
          ])))
          : h("div", { class: "exam-review-answer reference" }, [h("small", "参考答案"), h("p", referenceDisplayText(referenceRow))]),
        question.value.explanation ? h("div", { class: "exam-review-explain" }, [h("small", "解析"), h("p", question.value.explanation)]) : null
      ]);
    }
    return () => h("article", { class: ["wrong-card", `mastery-${mastery.value}`, isDue.value ? "is-due" : "", open.value ? "open" : ""] }, [
      h("div", { class: "wrong-card-top" }, [
        h("span", { class: ["wrong-state", mastery.value] }, masteryText.value),
        isDue.value
          ? h("span", { class: "wrong-due-badge", title: "已到艾宾浩斯复习时间" }, [h(Clock, { size: 12 }), "待复习"])
          : (nextReviewLabel() ? h("span", { class: "wrong-next-review", title: "下次按遗忘曲线复习的时间" }, [h(Clock, { size: 12 }), nextReviewLabel()]) : null),
        h("span", { class: "wrong-review-progress", title: "按遗忘曲线 1→2→4→7→15→30 天复习，走完整条曲线即掌握" }, [
          "复习 ",
          ...Array.from({ length: reviewTotal.value }, (_unused, index) => h("i", { class: ["streak-dot", index < reviewStage.value ? "on" : ""] })),
          ` ${reviewStage.value}/${reviewTotal.value}`
        ]),
        h("span", { class: "wrong-times" }, `错 ${p.item.wrong_count || 1} 次`)
      ]),
      h("h2", { onClick: () => { open.value = !open.value; } }, question.value.stem || "错题"),
      open.value ? renderExpanded() : h("p", { class: "wrong-card-hint", onClick: () => { open.value = true; } }, question.value.explanation || "点击题干或\"查看题目与解析\"展开完整题目与解析"),
      h("div", { class: "wrong-card-tags" }, [
        h("span", { class: "tag tag-warning" }, p.item.knowledge_point_name || "未标注知识点"),
        p.item.last_wrong_at ? h("span", { class: "tag" }, `最近出错 ${relativeTime(p.item.last_wrong_at)}`) : null,
        p.item.resolved_at && mastery.value === "resolved" ? h("span", { class: "tag tag-success" }, `掌握于 ${relativeTime(p.item.resolved_at)}`) : null
      ]),
      h("footer", [
        h("button", { type: "button", class: "btn btn-ghost btn-sm", onClick: () => { open.value = !open.value; } }, [h(Eye, { size: 14 }), open.value ? "收起题目" : "查看题目与解析"]),
        h("button", { type: "button", class: "btn btn-primary btn-sm", "data-loading": p.generating, disabled: p.generating, onClick: () => { if (!p.generating) update("practice"); } }, [h(RefreshCw, { size: 14 }), isDue.value ? "开始复习" : (mastery.value === "resolved" ? "再巩固一次" : "变式重练")])
      ])
    ]);
  }
});
