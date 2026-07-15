// 出题任务(quiz.generate/teacher_weak_quiz/wrong_book_practice)轮询原语：只抽取学生端/教师端
// 重复的"sleep → GET /learning/generation-tasks/{id} → 解析 status/step/quiz id"逻辑；
// 成功/失败后的差异化收尾（toast+CTA vs 自动打开审核弹窗）仍留在各自调用方，不在此处合并。
import { api, ApiError } from "../api/client";

// 与后端 app/services/ai.py generate_quiz_questions 的 on_step 上报口径一一对应。
export type GenerationStepKey = "preparing" | "drafting" | "reviewing" | "refining" | "assembling";

export type GenerationPollOutcome =
  | { status: "ready"; step: GenerationStepKey | null; quizId: number }
  | { status: "failed"; step: GenerationStepKey | null }
  | { status: "timeout"; step: GenerationStepKey | null };

// 导出供教师端沿用自有轮询循环时提取 step 使用，避免两处各写一遍同样的取值链路。
export function extractGenerationStep(res: any): GenerationStepKey | null {
  const step = res?.detail?.step ?? res?.generation_task?.detail?.step ?? null;
  return (step as GenerationStepKey) || null;
}

export async function pollGenerationProgress(
  taskId: number,
  {
    intervalMs = 2500,
    timeoutMs = 300000,
    onTick,
  }: { intervalMs?: number; timeoutMs?: number; onTick?: (step: GenerationStepKey | null, status: string) => void } = {}
): Promise<GenerationPollOutcome> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    let res: any = null;
    try {
      res = await api.get<any>(`/learning/generation-tasks/${taskId}`);
    } catch (error) {
      // 鉴权失效/无权/任务不存在是终态；其余(网络抖动)等下一拍再查
      if (error instanceof ApiError && [401, 403, 404].includes(error.status)) return { status: "failed", step: null };
      continue;
    }
    if (!res) continue;
    const step = extractGenerationStep(res);
    onTick?.(step, String(res.status || "processing"));
    if (Number(res.id) > 0) return { status: "ready", step, quizId: Number(res.id) };
    if (String(res.status) === "failed") return { status: "failed", step };
  }
  return { status: "timeout", step: null };
}
