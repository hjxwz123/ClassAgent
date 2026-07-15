<template>
  <div v-if="tasks.length" class="generation-panel" aria-live="polite">
    <TransitionGroup name="gen-panel-card">
      <article v-for="task in tasks" :key="task.id" class="generation-card" :class="{ failed: task.status === 'failed' }">
        <header>
          <Sparkles :size="15" />
          <strong>{{ task.title }}</strong>
          <button type="button" class="generation-dismiss" aria-label="关闭" @click="emit('dismiss', task.id)"><X :size="12" /></button>
        </header>
        <ol class="generation-steps">
          <li v-for="row in rowsFor(task)" :key="row.key" :class="row.state">
            <LoadingMark v-if="row.state === 'active'" :label="false" class="generation-step-spinner" />
            <CheckCircle v-else-if="row.state === 'done'" :size="16" />
            <span v-else class="generation-step-dot" aria-hidden="true"></span>
            <em>{{ row.label }}</em>
          </li>
        </ol>
        <p v-if="task.status === 'failed'" class="generation-failed-hint">生成失败，可在列表中重试或忽略</p>
      </article>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { CheckCircle, Sparkles, X } from "../icons";
import LoadingMark from "./LoadingMark.vue";
import type { GenerationPanelTask } from "../stores/generationTasks";
import type { GenerationStepKey } from "../composables/useGenerationProgress";

defineProps<{ tasks: GenerationPanelTask[] }>();
const emit = defineEmits<{ dismiss: [id: number] }>();

// 后端 5 个 step key 收敛成 4 行 UI：drafting/refining 对用户来说都是"AI 在写候选题"，
// 合并展示；reviewing 在 practice_fast(学生自助练习)路径下不会触发，届时该行会因为
// currentIndex 已越过它而直接判定为 done，无需额外的"跳过"视觉状态。
const STEP_ORDER: GenerationStepKey[] = ["preparing", "drafting", "reviewing", "refining", "assembling"];
const ROWS: { key: string; label: string; covers: GenerationStepKey[] }[] = [
  { key: "preparing", label: "分析知识点与课程素材", covers: ["preparing"] },
  { key: "drafting", label: "AI 生成候选题目", covers: ["drafting", "refining"] },
  { key: "reviewing", label: "质量把关", covers: ["reviewing"] },
  { key: "assembling", label: "组卷完成", covers: ["assembling"] }
];

function rowsFor(task: GenerationPanelTask) {
  const currentIndex = STEP_ORDER.indexOf(task.step || "preparing");
  return ROWS.map((row) => {
    const rowMinIndex = Math.min(...row.covers.map((key) => STEP_ORDER.indexOf(key)));
    const rowMaxIndex = Math.max(...row.covers.map((key) => STEP_ORDER.indexOf(key)));
    const state =
      task.status === "ready"
        ? "done"
        : task.status === "failed"
          ? (currentIndex > rowMaxIndex ? "done" : "pending")
          : currentIndex > rowMaxIndex
            ? "done"
            : currentIndex >= rowMinIndex
              ? "active"
              : "pending";
    return { key: row.key, label: row.label, state };
  });
}
</script>

<style scoped>
.generation-panel {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: var(--z-fixed);
  display: grid;
  gap: var(--space-3);
  width: 300px;
}
.generation-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-left: 3px solid var(--color-info-500);
  border-radius: var(--radius-md);
  box-shadow: 0 10px 28px rgba(18, 22, 20, .1), 0 2px 6px rgba(18, 22, 20, .05);
  padding: var(--space-3);
}
.generation-card.failed { border-left-color: var(--color-danger-500); }
.generation-card header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-body);
}
.generation-card header strong {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.generation-dismiss {
  flex: 0 0 auto;
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 2px;
}
.generation-steps {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.generation-steps li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}
.generation-steps li.done { color: var(--color-success-700); }
.generation-steps li.active { color: var(--color-text-body); font-weight: 600; }
.generation-steps li > svg { flex: 0 0 auto; color: var(--color-success-500); }
.generation-step-spinner { width: 16px; height: 16px; flex: 0 0 auto; }
.generation-step-dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid var(--color-border-default);
}
.generation-failed-hint {
  margin: var(--space-2) 0 0;
  font-size: 12px;
  color: var(--color-danger-500);
}
.gen-panel-card-enter-active { animation: gen-panel-in var(--duration-base) var(--ease-out) both; }
.gen-panel-card-leave-active { animation: gen-panel-out var(--duration-fast) var(--ease-in) both; }
.gen-panel-card-move { transition: transform var(--duration-base) var(--ease-out); }
@keyframes gen-panel-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes gen-panel-out {
  from { opacity: 1; transform: scale(1); }
  to { opacity: 0; transform: scale(0.96); }
}
@media (max-width: 640px) {
  .generation-panel { left: var(--space-4); right: var(--space-4); width: auto; bottom: var(--space-4); }
}
</style>
