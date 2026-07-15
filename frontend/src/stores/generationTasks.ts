import { defineStore } from "pinia";
import type { GenerationStepKey } from "../composables/useGenerationProgress";

export interface GenerationPanelTask {
  id: number;
  title: string;
  status: "pending" | "processing" | "ready" | "failed";
  step: GenerationStepKey | null;
}

// 承载右下角"生成中"步骤清单面板的数据，App.vue 根级挂载 GenerationProgressPanel 读取本 store，
// 与 ToastHost 读取 session.toasts 是同一种"根级单例 + 视图侧 upsert/update/remove"模式。
export const useGenerationTasksStore = defineStore("generationTasks", {
  state: () => ({
    tasks: [] as GenerationPanelTask[]
  }),
  actions: {
    upsertTask(task: GenerationPanelTask) {
      this.tasks = [task, ...this.tasks.filter((item) => item.id !== task.id)];
    },
    updateTask(id: number, patch: Partial<GenerationPanelTask>) {
      this.tasks = this.tasks.map((item) => (item.id === id ? { ...item, ...patch } : item));
    },
    removeTask(id: number) {
      this.tasks = this.tasks.filter((item) => item.id !== id);
    }
  }
});
