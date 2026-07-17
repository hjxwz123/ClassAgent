// 从 StudentView.vue 抽出的答题/解析主视图（原内联 QuizAnswerView，~430 行，本文件的最大提取）。
// 全部作答状态为组件内部管理（current/marked/elapsed/草稿落 localStorage），
// 不引用任何父页面响应式状态；对外仅通过 props/emits 交互。
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, Teleport, Transition, watch, type PropType } from "vue";
import { AlertTriangle, ArrowLeft, ArrowRight, BookMarked, Check, CheckCircle, Clock, Flag, RefreshCw, Sparkles, X, XCircle } from "../../../icons";
import { relativeTime, timeLabel } from "../../../utils/datetime";
import { answerIndexSet, optionText, referenceDisplayText } from "../../../utils/quiz";
import { renderInlineRichText, renderRichText } from "../../../utils/richText";
import { EmptyState } from "./primitives";

export const QuizAnswerView = defineComponent({
  props: {
    quiz: { type: Object as PropType<any>, default: null },
    answers: { type: Object as PropType<Record<number, any>>, required: true },
    attempt: { type: Object as PropType<any>, default: null },
    submitting: { type: Boolean, default: false },
    retaking: { type: Boolean, default: false },
    // 恢复的草稿（答案已由父组件灌入 answers，这里只取 current/marked/elapsed）
    draft: { type: Object as PropType<any>, default: null },
    // 草稿持久化 key；为空则不落盘（如查看历史解析）
    draftKey: { type: String, default: "" }
  },
  emits: ["answer", "submit", "exit", "retake", "goWrongBook"],
  setup(p, { emit: update }) {
    const questions = computed(() => p.quiz?.questions || []);
    const quizMeta = computed(() => p.quiz?.quiz || {});
    const current = ref(Math.max(0, Math.min(Number(p.draft?.current || 0), Math.max(questions.value.length - 1, 0))));
    const marked = ref<number[]>(Array.isArray(p.draft?.marked) ? p.draft.marked.map(Number) : []);
    const confirming = ref(false);
    const elapsed = ref(Math.max(0, Number(p.draft?.elapsed || 0)));
    const initialRows = (p.attempt?.answers || []) as any[];
    const initialWrong = initialRows.filter((row: any) => !row.is_correct && !row.pending_review).length;
    const onlyWrong = ref(initialWrong > 0 && initialWrong < initialRows.length);
    const saveFlash = ref(false);
    const analysisRefs: Record<string, HTMLElement | null> = {};
    let timer: number | undefined;
    let saveTimer: number | undefined;
    let flashTimer: number | undefined;
    function startTimer() { if (timer || p.attempt) return; timer = window.setInterval(() => { elapsed.value += 1; }, 1000); }
    function stopTimer() { if (timer) { window.clearInterval(timer); timer = undefined; } }
    // 交卷后（或直接查看历史解析时）停表——结果页的"用时"必须是定格值，不能继续跳。
    watch(() => p.attempt, (value) => {
      if (value) {
        stopTimer();
        const rows = (value?.answers || []) as any[];
        const wrong = rows.filter((row: any) => !row.is_correct && !row.pending_review).length;
        onlyWrong.value = wrong > 0 && wrong < rows.length;
      } else {
        startTimer();
      }
    });
    function hasAnyProgress() {
      const answered = questions.value.some((item: any) => hasAnswer(item));
      return answered || marked.value.length > 0 || current.value > 0 || elapsed.value > 5;
    }
    function persistDraft() {
      if (!p.draftKey || p.attempt) return;
      try {
        localStorage.setItem(p.draftKey, JSON.stringify({
          answers: { ...p.answers },
          marked: [...marked.value],
          current: current.value,
          elapsed: elapsed.value,
          savedAt: Date.now(),
        }));
        saveFlash.value = true;
        if (flashTimer) window.clearTimeout(flashTimer);
        flashTimer = window.setTimeout(() => { saveFlash.value = false; }, 1400);
      } catch { /* 存储异常不打断做题 */ }
    }
    function scheduleDraftSave() {
      if (!p.draftKey || p.attempt) return;
      if (saveTimer) window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(persistDraft, 300);
    }
    watch(() => ({ ...p.answers }), scheduleDraftSave, { deep: true });
    watch([marked, current], scheduleDraftSave, { deep: true });
    function exitAndSave() {
      if (p.attempt) { update("exit", false); return; }
      if (hasAnyProgress()) { persistDraft(); update("exit", true); return; }
      if (p.draftKey) { try { localStorage.removeItem(p.draftKey); } catch { /* 忽略 */ } }
      update("exit", false);
    }
    function onKeydown(event: KeyboardEvent) {
      if (p.attempt) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.key === "Escape") { confirming.value = false; return; }
      if (confirming.value) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); current.value = Math.max(0, current.value - 1); return; }
      if (event.key === "ArrowRight") { event.preventDefault(); current.value = Math.min(questions.value.length - 1, current.value + 1); return; }
      if (event.key === "Enter") {
        event.preventDefault();
        if (current.value >= questions.value.length - 1) confirming.value = true;
        else current.value += 1;
        return;
      }
      const item = question.value;
      if (!item || !["single_choice", "multiple_choice", "judge"].includes(item.question_type)) return;
      const options = Array.isArray(item.options) ? item.options : [];
      let index = -1;
      if (/^[1-9]$/.test(event.key)) index = Number(event.key) - 1;
      else if (/^[a-zA-Z]$/.test(event.key)) {
        const letter = event.key.toUpperCase();
        if (letter === "M") { event.preventDefault(); toggleMark(item); return; }
        index = letter.charCodeAt(0) - 65;
      }
      if (index >= 0 && index < options.length) { event.preventDefault(); setAnswer(item, index); }
    }
    function toggleMark(item: any) {
      marked.value = marked.value.includes(item.id) ? marked.value.filter((id) => id !== item.id) : [...marked.value, item.id];
    }
    onMounted(() => { startTimer(); window.addEventListener("keydown", onKeydown); });
    onBeforeUnmount(() => {
      stopTimer();
      window.removeEventListener("keydown", onKeydown);
      if (saveTimer) window.clearTimeout(saveTimer);
      if (flashTimer) window.clearTimeout(flashTimer);
    });
    const question = computed(() => questions.value[current.value] || null);
    const answeredCount = computed(() => questions.value.filter((item: any) => hasAnswer(item)).length);
    const attemptData = computed(() => p.attempt?.attempt || p.attempt);
    const attemptAnswers = computed(() => p.attempt?.answers || []);
    const wrongRows = computed(() => attemptAnswers.value.filter((row: any) => !row.is_correct && !row.pending_review));
    const pendingRows = computed(() => attemptAnswers.value.filter((row: any) => row.pending_review));
    const displayRows = computed(() => (onlyWrong.value ? attemptAnswers.value.filter((row: any) => !row.is_correct) : attemptAnswers.value));
    const unansweredCount = computed(() => Math.max(0, questions.value.length - answeredCount.value));
    const progressPercent = computed(() => Math.round(((current.value + 1) / Math.max(questions.value.length, 1)) * 100));
    const displayDuration = computed(() => {
      const stored = Number(attemptData.value?.duration_seconds);
      if (Number.isFinite(stored) && stored > 0) return timeLabel(stored);
      if (elapsed.value > 0) return timeLabel(elapsed.value);
      return "";
    });
    function answerValue(item: any) {
      return p.answers[item.id];
    }
    function hasAnswer(item: any) {
      const value = p.answers[item.id];
      return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== "";
    }
    function setAnswer(item: any, value: any) {
      if (item.question_type === "multiple_choice") {
        const currentValues = Array.isArray(p.answers[item.id]) ? [...p.answers[item.id]] : [];
        update("answer", item.id, currentValues.includes(value) ? currentValues.filter((entry) => entry !== value) : [...currentValues, value]);
      } else {
        update("answer", item.id, value);
      }
    }
    function optionLabel(index: number) {
      return String.fromCharCode(65 + index);
    }
    function questionTypeLabel(type?: string) {
      const map: Record<string, string> = {
        single_choice: "单选题",
        multiple_choice: "多选题",
        judge: "判断题",
        blank: "填空题",
        short_answer: "简答题",
      };
      return map[String(type || "")] || "题目";
    }
    function difficultyLabel(value?: string) {
      const map: Record<string, string> = {
        easy: "基础难度",
        standard: "标准难度",
        medium: "标准难度",
        hard: "进阶难度",
      };
      return map[String(value || "")] || String(value || "标准难度");
    }
    function submit() {
      if (p.submitting) return;
      confirming.value = false;
      update("submit", elapsed.value);
    }
    function scoreLevel(value: number) {
      if (value >= 90) return "优秀";
      if (value >= 75) return "良好";
      if (value >= 60) return "及格";
      return "待加强";
    }
    function renderQuestionBody(item: any) {
      if (!item) return null;
      const options = Array.isArray(item.options) ? item.options : [];
      if (["single_choice", "multiple_choice", "judge"].includes(item.question_type)) {
        return h("div", { class: "exam-options-group" }, options.map((option: any, index: number) => {
          const value = index;
          const selected = item.question_type === "multiple_choice" ? (answerValue(item) || []).includes(value) : answerValue(item) === value;
          return h("label", { class: "exam-opt-label" }, [
            h("input", {
              type: item.question_type === "multiple_choice" ? "checkbox" : "radio",
              name: `question-${item.id}`,
              class: "exam-opt-input",
              checked: selected,
              onChange: () => setAnswer(item, value)
            }),
            h("div", { class: "exam-opt-card" }, [
              h("div", { class: "exam-opt-letter" }, optionLabel(index)),
              h("div", { class: "exam-opt-text exam-rich-text", innerHTML: renderInlineRichText(typeof option === "object" ? option.text || option.label || JSON.stringify(option) : String(option)) })
            ])
          ]);
        }));
      }
      if (item.question_type === "blank") {
        return h("input", { class: "exam-answer-input", value: answerValue(item) || "", placeholder: "填写答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLInputElement).value) });
      }
      return h("div", { class: "exam-text-answer" }, [
        h("textarea", { class: "exam-answer-textarea", value: answerValue(item) || "", maxlength: 500, placeholder: "写下你的答案", onInput: (event: Event) => setAnswer(item, (event.target as HTMLTextAreaElement).value) }),
        h("small", `${String(answerValue(item) || "").length} / 500`)
      ]);
    }
    function scrollToRow(questionId: number | string) {
      const key = String(questionId);
      const row = attemptAnswers.value.find((item: any) => String(item.question_id) === key);
      // 目标题被"只看错题"过滤掉时先展开全部，再滚动。
      if (onlyWrong.value && row?.is_correct) onlyWrong.value = false;
      void nextTick(() => { analysisRefs[key]?.scrollIntoView({ behavior: "smooth", block: "start" }); });
    }
    function renderReviewOptions(row: any) {
      const questionData = row.question || {};
      const options = Array.isArray(questionData.options) ? questionData.options : [];
      const correctSet = answerIndexSet(row.correct_answer, options);
      const chosenSet = answerIndexSet(row.user_answer, options);
      return h("div", { class: "exam-review-options" }, options.map((option: any, index: number) => {
        const isCorrect = correctSet.has(index);
        const isChosen = chosenSet.has(index);
        const cls = ["exam-review-opt"];
        if (isCorrect) cls.push("is-correct");
        if (isChosen && !isCorrect) cls.push("is-wrong");
        if (isChosen) cls.push("is-chosen");
        return h("div", { key: index, class: cls }, [
          h("span", { class: "exam-review-letter" }, optionLabel(index)),
          h("span", { class: "exam-review-text exam-rich-text", innerHTML: renderInlineRichText(typeof option === "object" ? option.text || option.label || JSON.stringify(option) : String(option)) }),
          isCorrect ? h("span", { class: "exam-review-badge correct" }, [h(Check, { size: 12 }), "正确答案"]) : null,
          isChosen && !isCorrect ? h("span", { class: "exam-review-badge wrong" }, [h(X, { size: 12 }), "你的选择"]) : null,
          isChosen && isCorrect ? h("span", { class: "exam-review-badge chosen" }, "你的选择") : null
        ]);
      }));
    }
    function renderReviewAnswers(row: any) {
      const answered = row.user_answer !== null && row.user_answer !== undefined && row.user_answer !== "";
      return h("div", { class: "exam-review-answers" }, [
        h("div", { class: ["exam-review-answer", row.is_correct ? "good" : "bad"] }, [
          h("small", "你的答案"),
          answered ? h("p", { class: "exam-rich-text", innerHTML: renderInlineRichText(String(optionText(row.user_answer, row.question))) }) : h("p", "未作答")
        ]),
        h("div", { class: "exam-review-answer reference" }, [
          h("small", "参考答案"),
          h("p", { class: "exam-rich-text", innerHTML: renderInlineRichText(referenceDisplayText(row)) })
        ])
      ]);
    }
    function renderAnalysisCard(row: any) {
      const questionData = row.question || {};
      const isChoice = ["single_choice", "multiple_choice", "judge"].includes(questionData.question_type);
      const orderIndex = attemptAnswers.value.findIndex((item: any) => item.question_id === row.question_id);
      const state = row.pending_review ? "pending" : row.is_correct ? "correct" : "wrong";
      return h("article", {
        key: row.question_id,
        class: ["exam-review-card", `is-${state}`],
        ref: (el: any) => { analysisRefs[String(row.question_id)] = el as HTMLElement | null; }
      }, [
        h("header", { class: "exam-review-head" }, [
          h("span", { class: "exam-q-number" }, `Q${orderIndex + 1}`),
          h("span", { class: "exam-tag exam-tag-type" }, questionTypeLabel(questionData.question_type)),
          questionData.knowledge_point_name ? h("span", { class: "exam-tag exam-tag-point" }, questionData.knowledge_point_name) : null,
          h("span", { class: "exam-review-score" }, `${Number(row.score || 0)} / ${Number(questionData.score || 0)} 分`),
          h("span", { class: ["exam-review-state", state] },
            state === "pending" ? [h(Clock, { size: 14 }), "待批改"] : state === "correct" ? [h(CheckCircle, { size: 14 }), "答对"] : [h(XCircle, { size: 14 }), "答错"])
        ]),
        h("div", { class: "exam-review-stem exam-rich-text", innerHTML: renderRichText(questionData.stem || "") }),
        isChoice ? renderReviewOptions(row) : renderReviewAnswers(row),
        questionData.explanation ? h("div", { class: "exam-review-explain" }, [h("small", "解析"), h("div", { class: "exam-review-explain-body exam-rich-text", innerHTML: renderRichText(questionData.explanation) })]) : null,
        row.feedback && row.feedback !== questionData.explanation ? h("div", { class: "exam-review-feedback" }, [h(Sparkles, { size: 14 }), h("span", { class: "exam-rich-text", innerHTML: renderInlineRichText(row.feedback) })]) : null
      ]);
    }
    function renderResult() {
      const accuracy = Number(attemptData.value?.accuracy || 0);
      const total = attemptAnswers.value.length;
      const correctCount = attemptAnswers.value.filter((row: any) => row.is_correct).length;
      const wrongCount = wrongRows.value.length;
      const submittedAt = attemptData.value?.submitted_at || attemptData.value?.created_at;
      const statLine = [
        `答对 ${correctCount}/${total}`,
        `正确率 ${accuracy}%`,
        displayDuration.value ? `用时 ${displayDuration.value}` : (submittedAt ? `提交于 ${relativeTime(submittedAt)}` : "")
      ].filter(Boolean).join(" · ");
      return h("section", { class: "exam-shell exam-result-shell" }, [
        h("header", { class: "exam-header" }, [
          h("button", { type: "button", class: "exam-exit-btn", onClick: () => update("exit", false) }, [h(ArrowLeft, { size: 18 }), "返回列表"]),
          h("div", { class: "exam-title" }, quizMeta.value.title || "练习结果"),
          h("div", { class: "exam-submit-time" }, submittedAt ? `提交于 ${relativeTime(submittedAt)}` : "")
        ]),
        h("main", { class: "exam-result-main" }, [
          h("article", { class: "exam-result-card" }, [
            accuracy >= 60 ? h(CheckCircle, { size: 48 }) : h(XCircle, { size: 48 }),
            h("strong", String(Math.round(Number(attemptData.value?.score || 0)))),
            h("span", `分 / ${Math.round(Number(attemptData.value?.total_score || quizMeta.value.total_score || 100))} 分`),
            h("em", scoreLevel(accuracy)),
            h("small", statLine)
          ]),
          h("article", { class: "exam-result-summary" }, [
            h("div", [
              h("h2", [h(Sparkles, { size: 18 }), "AI 建议"]),
              h("p", { class: "exam-rich-text", innerHTML: renderInlineRichText(attemptData.value?.ai_feedback || "复盘错题，并回看对应知识点。") }),
              wrongCount ? h("button", { type: "button", class: "exam-wrongbook-link", onClick: () => update("goWrongBook") }, [
                h(BookMarked, { size: 14 }), `${wrongCount} 道错题已收入错题本，去看看`, h(ArrowRight, { size: 14 })
              ]) : null,
              pendingRows.value.length ? h("p", { class: "exam-pending-hint" }, `另有 ${pendingRows.value.length} 道主观题待教师批改，暂不计分。`) : null
            ])
          ]),
          h("article", { class: "exam-analysis-card" }, [
            h("div", { class: "exam-analysis-head" }, [
              h("h2", "题目解析"),
              h("div", { class: "exam-overview-grid" }, attemptAnswers.value.map((row: any, index: number) => h("button", {
                key: row.question_id,
                type: "button",
                class: ["exam-overview-btn", row.pending_review ? "pending" : row.is_correct ? "correct" : "wrong"],
                title: `跳转到第 ${index + 1} 题`,
                onClick: () => scrollToRow(row.question_id)
              }, String(index + 1)))),
              wrongCount ? h("button", { type: "button", class: ["exam-onlywrong-toggle", onlyWrong.value ? "active" : ""], onClick: () => { onlyWrong.value = !onlyWrong.value; } }, [
                h("span", { class: "exam-onlywrong-dot" }), `只看错题 (${attemptAnswers.value.filter((row: any) => !row.is_correct).length})`
              ]) : null
            ]),
            displayRows.value.length
              ? displayRows.value.map((row: any) => renderAnalysisCard(row))
              : h("p", { class: "exam-review-empty" }, "全部答对，没有错题可看 🎉")
          ])
        ]),
        h("footer", { class: "exam-action-footer" }, [
          h("div", { class: "exam-footer-container exam-result-actions" }, [
            h("button", { type: "button", class: "exam-btn exam-btn-outline", onClick: () => update("exit", false) }, "返回列表"),
            h("div", { class: "exam-footer-actions" }, [
              h("button", { type: "button", class: "exam-btn exam-btn-outline", "data-loading": p.retaking, disabled: p.retaking, onClick: () => { if (!p.retaking) update("retake", "full"); } }, [h(RefreshCw, { size: 15 }), "再练一卷"]),
              wrongCount ? h("button", { type: "button", class: "exam-btn exam-btn-danger", "data-loading": p.retaking, disabled: p.retaking, onClick: () => { if (!p.retaking) update("retake", "wrong"); } }, [h(RefreshCw, { size: 15 }), `重做错题 (${wrongCount})`]) : null
            ])
          ])
        ])
      ]);
    }
    return () => {
      if (p.attempt) return renderResult();
      const item = question.value;
      if (!item) {
        // 空卷也必须有出口：这是全屏覆盖层，没有退出按钮就只能刷新逃生。
        return h("div", { class: "exam-shell exam-empty-shell" }, [
          h("header", { class: "exam-header" }, [
            h("button", { type: "button", class: "exam-exit-btn", onClick: () => update("exit", false) }, [h(ArrowLeft, { size: 18 }), "返回练习列表"]),
            h("div", { class: "exam-title" }, quizMeta.value.title || "练习")
          ]),
          h(EmptyState, { text: "这份练习暂无题目，请返回列表重新生成" })
        ]);
      }
      const unanswered = questions.value
        .map((entry: any, index: number) => ({ entry, index }))
        .filter(({ entry }: any) => !hasAnswer(entry));
      return h("section", { class: "exam-shell" }, [
        h("header", { class: "exam-header" }, [
          h("button", { type: "button", class: "exam-exit-btn", onClick: exitAndSave }, [h(ArrowLeft, { size: 18 }), "保存并退出"]),
          h("div", { class: "exam-title" }, quizMeta.value.title || "章节练习"),
          h("div", { class: "exam-header-side" }, [
            h(Transition, { name: "fade" }, { default: () => saveFlash.value ? h("span", { class: "exam-save-flash" }, [h(Check, { size: 13 }), "已自动保存"]) : null }),
            h("div", { class: "timer-widget" }, [h(Clock, { size: 16 }), h("span", { class: "timer-text" }, timeLabel(elapsed.value))])
          ])
        ]),
        h("main", { class: "exam-container" }, [
          h("aside", { class: "exam-nav-sidebar" }, [
            h("div", { class: "exam-nav-card" }, [
              h("div", { class: "exam-nav-stats" }, [
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(answeredCount.value)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-answered" }), "已答"])]),
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(marked.value.length)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-marked" }), "标记"])]),
                h("div", { class: "exam-stat-item" }, [h("span", { class: "exam-stat-val" }, String(unansweredCount.value)), h("span", { class: "exam-stat-label" }, [h("i", { class: "exam-dot exam-dot-unanswered" }), "未答"])])
              ]),
              h("div", { class: "exam-q-grid" }, questions.value.map((entry: any, index: number) => h("button", {
              type: "button",
                class: ["exam-q-btn", hasAnswer(entry) ? "answered" : "", index === current.value ? "current" : "", marked.value.includes(entry.id) ? "marked" : ""],
              onClick: () => { current.value = index; }
              }, String(index + 1))))
            ])
          ]),
          h("section", { class: "exam-question-area" }, [
            h("article", { class: "exam-q-card" }, [
              h("div", { class: "exam-q-meta-row" }, [
                h("div", { class: "exam-q-tags" }, [
                  h("span", { class: "exam-q-number" }, `题目 ${current.value + 1}`),
                  h("span", { class: "exam-tag exam-tag-type" }, questionTypeLabel(item.question_type)),
                  h("span", { class: "exam-tag exam-tag-diff" }, difficultyLabel(item.difficulty))
                ]),
                h("button", { type: "button", class: ["exam-mark-btn", marked.value.includes(item.id) ? "is-marked" : ""], title: "快捷键 M", onClick: () => toggleMark(item) }, [
                  h(Flag, { size: 16 }),
                  marked.value.includes(item.id) ? "已标记" : "标记稍后看"
                ])
            ]),
              h("div", { class: "exam-q-stem exam-rich-text", innerHTML: renderRichText(item.stem) }),
              renderQuestionBody(item)
            ])
          ])
        ]),
        h("footer", { class: "exam-action-footer" }, [
          h("div", { class: "exam-footer-container" }, [
            h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: current.value <= 0, onClick: () => { current.value = Math.max(0, current.value - 1); } }, [h(ArrowLeft, { size: 18 }), "上一题"]),
            h("div", { class: "exam-footer-progress" }, [
              h("span", { class: "exam-prog-text" }, `第 ${current.value + 1} / ${questions.value.length} 题`),
              h("div", { class: "exam-prog-bar" }, [h("div", { class: "exam-prog-fill", style: { width: `${progressPercent.value}%` } })])
            ]),
            h("div", { class: "exam-footer-actions" }, [
              h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: current.value >= questions.value.length - 1, onClick: () => { current.value = Math.min(questions.value.length - 1, current.value + 1); } }, ["下一题", h(ArrowRight, { size: 18 })]),
              h("button", { type: "button", class: "exam-btn exam-btn-primary", disabled: p.submitting, "data-loading": p.submitting, onClick: () => { confirming.value = true; } }, [h(Check, { size: 16 }), "交卷"])
            ])
          ])
        ]),
        h(Teleport, { to: "body" }, [
          h(Transition, { name: "modal-pop" }, {
            default: () => confirming.value ? h("div", { class: "exam-modal-mask exam-modal-scope" }, [
              h("article", { class: "exam-confirm-card" }, [
                h("div", { class: "exam-modal-head" }, [h(AlertTriangle, { size: 22 }), h("h2", "确认交卷"), h("button", { type: "button", onClick: () => { confirming.value = false; } }, [h(X, { size: 16 })])]),
                unanswered.length
                  ? h("div", { class: "exam-confirm-warn" }, [
                    h(AlertTriangle, { size: 16 }),
                    h("div", [
                      h("span", [`还有 `, h("b", String(unanswered.length)), ` 道未作答，未答题将计 0 分。点击题号可直接跳转补答：`]),
                      h("div", { class: "exam-confirm-jump" }, unanswered.map(({ index }: any) => h("button", {
                        type: "button",
                        class: "exam-jump-chip",
                        onClick: () => { confirming.value = false; current.value = index; }
                      }, `Q${index + 1}`)))
                    ])
                  ])
                  : h("p", "所有题目均已作答，交卷后将立即批改并展示解析。"),
                marked.value.length ? h("p", { class: "exam-confirm-marked" }, `你还标记了 ${marked.value.length} 道题稍后查看`) : null,
                h("footer", [h("button", { type: "button", class: "exam-btn exam-btn-outline", disabled: p.submitting, onClick: () => { confirming.value = false; } }, unanswered.length ? "写完再交" : "再检查一下"), h("button", { type: "button", class: "exam-btn exam-btn-primary", disabled: p.submitting, "data-loading": p.submitting, onClick: submit }, unanswered.length ? "仍然交卷" : "确认交卷")])
              ])
            ]) : null
          })
        ])
      ]);
    };
  }
});
