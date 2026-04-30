from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class MockAIService:
    def extract_keywords(self, text: str, *, limit: int = 6) -> list[str]:
        candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", text)
        keywords: list[str] = []
        for item in candidates:
            token = item.lower()
            if token not in keywords:
                keywords.append(token)
            if len(keywords) >= limit:
                break
        return keywords or ["课程内容"]

    def generate_page_script(self, *, title: str | None, content: str) -> str:
        heading = title or "本页内容"
        summary = _clean_text(content)
        summary = summary[:220] if len(summary) > 220 else summary
        return (
            f"{heading}的核心内容如下：\n"
            f"1. 先理解本页定义与背景：{summary or '本页暂无可提取文字。'}\n"
            f"2. 再关注概念之间的联系与典型应用。\n"
            f"3. 最后结合课程上下文总结本页重点并准备继续学习。"
        )

    def summarize_lesson(self, title: str, page_texts: Sequence[str]) -> str:
        merged = " ".join(text.strip() for text in page_texts if text.strip())
        merged = merged[:200] if len(merged) > 200 else merged
        return f"{title}：{merged or '该资料已生成课堂页面，可继续补充讲解脚本。'}"

    def answer_question(self, *, question: str, contexts: Sequence[str], history: Sequence[str] | None = None) -> tuple[str, bool]:
        if not contexts:
            return (
                "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。",
                True,
            )
        context = " ".join(_clean_text(item) for item in contexts if item)
        context = context[:320]
        history_hint = ""
        if history:
            history_hint = f"\n结合前序对话，可继续沿着“{history[-1][:30]}”这个方向理解。"
        answer = (
            f"根据当前课程资料，问题“{question}”可以这样理解：\n"
            f"{context}\n"
            "如果你要继续追问，建议从定义、适用条件、典型例题三个角度继续展开。"
            f"{history_hint}"
        )
        return answer, False

    def extract_knowledge_points(self, text: str) -> list[str]:
        return self.extract_keywords(text, limit=5)

    def generate_problem_guidance(self, *, problem_text: str, level: int) -> str:
        snippet = _clean_text(problem_text)[:180]
        if level == 1:
            return f"先判断题目考查的核心对象与已知条件，再围绕“{snippet}”提炼解题入口。"
        if level == 2:
            return f"关键步骤建议分三步：整理条件、选择公式或定理、逐步代入并检查边界情况。题干片段：{snippet}"
        return (
            f"完整解析：\n"
            f"1. 明确题目目标并重述条件：{snippet}\n"
            "2. 选择正确的概念、定理或公式。\n"
            "3. 逐步推导并给出最终答案。\n"
            "4. 回看是否遗漏单位、定义域、符号方向等细节。"
        )

    def generate_common_mistakes(self, knowledge_points: Sequence[str]) -> list[str]:
        base = knowledge_points[0] if knowledge_points else "该知识点"
        return [
            f"忽略 {base} 的适用前提。",
            "只记结论，没有先整理已知条件。",
            "计算完成后没有回头检查边界条件或符号。"
        ]

    def generate_similar_questions(self, knowledge_points: Sequence[str]) -> list[str]:
        base = knowledge_points[0] if knowledge_points else "当前知识点"
        return [
            f"围绕 {base} 的基础概念判断题。",
            f"围绕 {base} 的标准步骤计算题。",
            f"围绕 {base} 的综合应用题。"
        ]

    def generate_knowledge_explanation(self, *, name: str, difficulty: str, source_text: str) -> dict[str, str]:
        source = _clean_text(source_text)[:260]
        tone = {
            "beginner": "用最直观的方式先理解它是什么、为什么需要它。",
            "standard": "从定义、原理、应用场景三个层面完整掌握。",
            "advanced": "进一步关注限制条件、变形思路和综合题中的使用方式。",
        }.get(difficulty, "从定义、原理、应用场景三个层面完整掌握。")
        return {
            "name": name,
            "difficulty": difficulty,
            "definition": f"{name}：{tone}",
            "principle": f"相关原理材料摘要：{source or '可结合课程资料进一步补充。'}",
            "example": f"例题建议：围绕 {name} 设计一道从条件识别到步骤推导的典型题。",
            "common_mistake": f"常见错误：对 {name} 的适用范围理解不清。"
        }

    def generate_quiz_questions(self, *, topic: str, source_text: str, count: int) -> list[dict]:
        snippet = _clean_text(source_text)[:120] or topic
        templates = [
            {
                "question_type": "single_choice",
                "stem": f"关于“{topic}”，下列说法最符合课程资料的是哪一项？",
                "options": ["只看结论即可", f"需要结合资料中的条件与定义：{snippet[:24]}", "与课程内容无关", "完全依赖记忆即可"],
                "reference_answer": {"value": 1},
                "explanation": f"课程资料强调要结合定义和条件理解：{snippet}",
                "score": 10,
                "difficulty": "standard",
            },
            {
                "question_type": "judge",
                "stem": f"判断：{topic} 在任何条件下都可以直接套用固定公式。",
                "options": ["正确", "错误"],
                "reference_answer": {"value": 1},
                "explanation": "课程学习中应先判断适用条件，再决定是否直接套用。",
                "score": 10,
                "difficulty": "standard",
            },
            {
                "question_type": "short_answer",
                "stem": f"请简述学习“{topic}”时最关键的两个步骤。",
                "options": None,
                "reference_answer": {"keywords": self.extract_keywords(source_text, limit=3)},
                "explanation": "先整理条件，再结合定义或定理推导。",
                "score": 20,
                "difficulty": "advanced",
            },
        ]
        questions: list[dict] = []
        while len(questions) < count:
            template = templates[len(questions) % len(templates)].copy()
            questions.append(template)
        return questions

    def score_subjective_answer(
        self,
        *,
        reference_keywords: Sequence[str],
        user_answer: str,
        full_score: float,
    ) -> tuple[float, str]:
        tokens = set(self.extract_keywords(user_answer, limit=12))
        expected = {keyword.lower() for keyword in reference_keywords}
        if not expected:
            return round(full_score * 0.6, 2), "答案已提交，当前采用通用评分策略。"
        matched = len(tokens & expected)
        score = round(full_score * matched / len(expected), 2)
        score = min(full_score, max(score, full_score * 0.2 if user_answer.strip() else 0))
        feedback = (
            f"命中关键词 {matched}/{len(expected)}。"
            if user_answer.strip()
            else "答案为空，建议先按步骤写出关键结论。"
        )
        return score, feedback

    def generate_study_plan(
        self,
        *,
        goal: str,
        available_days: int,
        daily_minutes: int,
        course_name: str,
    ) -> list[dict]:
        today = datetime.now(UTC).date()
        tasks: list[dict] = []
        for index in range(available_days):
            current = today + timedelta(days=index)
            tasks.append(
                {
                    "title": f"{course_name} 第{index + 1}天学习任务",
                    "task_date": current.isoformat(),
                    "task_type": "study_plan",
                    "estimated_minutes": daily_minutes,
                    "summary": f"围绕目标“{goal}”完成听课、复习或练习。",
                }
            )
        return tasks


ai_service = MockAIService()
