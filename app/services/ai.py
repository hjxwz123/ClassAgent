from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from hashlib import blake2b
from typing import Any

import httpx
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_default_model_config


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_json_payload(value: str) -> Any:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_candidates = [index for index in (text.find("{"), text.find("[")) if index >= 0]
        if not start_candidates:
            raise
        start = min(start_candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            raise
        return json.loads(text[start : end + 1])


RAG_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是课程知识问答助手。只能依据给定课程资料回答；如果资料不足，必须说明资料不足，不能编造。",
        ),
        (
            "human",
            "课程资料：\n{context}\n\n历史问题：\n{history}\n\n学生问题：{question}\n请用中文回答，并给出关键依据。",
        ),
    ]
)


class AIService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _fallback_allowed(self) -> bool:
        if self.settings.external_ai_mode == "mock":
            return True
        return self.settings.external_ai_mode == "auto" and self.settings.app_env != "production"

    def _chat_endpoint(self, endpoint: str) -> str:
        endpoint = endpoint.rstrip("/")
        if endpoint.endswith("/chat/completions"):
            return endpoint
        return f"{endpoint}/chat/completions"

    def _embedding_endpoint(self, endpoint: str) -> str:
        endpoint = endpoint.rstrip("/")
        if endpoint.endswith("/embeddings"):
            return endpoint
        return f"{endpoint}/embeddings"

    def _call_chat(
        self,
        db: Session | None,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str | None:
        config = get_default_model_config(db, purpose)
        if config is None or config.provider == "mock":
            if self._fallback_allowed():
                return None
            raise bad_request(f"缺少 {purpose} 模型配置，请先在管理员模型配置中启用模型")
        if not config.endpoint:
            if self._fallback_allowed():
                return None
            raise bad_request(f"{purpose} 模型配置缺少 endpoint")

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(config.extra_config.get("headers") or {})
        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": config.extra_config.get("temperature", 0.2),
        }
        if config.extra_config.get("max_tokens"):
            payload["max_tokens"] = config.extra_config["max_tokens"]
        if json_mode and config.extra_config.get("enable_response_format", True):
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self.settings.external_service_timeout_seconds) as client:
                response = client.post(self._chat_endpoint(config.endpoint), headers=headers, json=payload)
            if response.status_code >= 400:
                raise bad_request(f"模型调用失败: HTTP {response.status_code} {response.text[:300]}")
            body = response.json()
            choices = body.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content")
                if content:
                    return str(content)
            if body.get("output"):
                output = body["output"]
                if isinstance(output, dict):
                    return str(output.get("text") or output.get("content") or "")
            raise bad_request("模型响应格式不符合 OpenAI 兼容规范")
        except Exception:
            if self._fallback_allowed():
                return None
            raise

    def _local_embedding(self, text: str, *, dimension: int) -> list[float]:
        features = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text.lower())
        tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", text.lower())
        features.extend(tokens)
        compact = "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text.lower()))
        for size in (2, 3):
            features.extend(compact[index : index + size] for index in range(max(len(compact) - size + 1, 0)))
        if not features:
            features = ["empty"]
        vector = [0.0] * dimension
        for feature in features:
            digest = blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(len(feature), 8) / 8
            vector[bucket] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    def embed_texts(self, db: Session | None, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        dimension = self.settings.embedding_dimension
        config = get_default_model_config(db, "embedding")
        if config is None or config.provider == "mock" or config.purpose != "embedding":
            if self._fallback_allowed():
                return [self._local_embedding(text, dimension=dimension) for text in texts]
            raise bad_request("缺少 embedding 模型配置，请先在管理员模型配置中启用 embedding")
        if not config.endpoint:
            if self._fallback_allowed():
                return [self._local_embedding(text, dimension=dimension) for text in texts]
            raise bad_request("embedding 模型配置缺少 endpoint")

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(config.extra_config.get("headers") or {})
        payload: dict[str, Any] = {
            "model": config.model_name,
            "input": list(texts),
        }
        if config.extra_config.get("dimensions"):
            payload["dimensions"] = config.extra_config["dimensions"]
        try:
            with httpx.Client(timeout=self.settings.external_service_timeout_seconds) as client:
                response = client.post(self._embedding_endpoint(config.endpoint), headers=headers, json=payload)
            if response.status_code >= 400:
                raise bad_request(f"Embedding 调用失败: HTTP {response.status_code} {response.text[:300]}")
            body = response.json()
            rows = body.get("data") or []
            embeddings = [row.get("embedding") for row in rows if isinstance(row, dict)]
            if len(embeddings) != len(texts) or not all(isinstance(item, list) for item in embeddings):
                raise bad_request("Embedding 响应格式不符合 OpenAI 兼容规范")
            return [[float(value) for value in embedding] for embedding in embeddings]
        except Exception:
            if self._fallback_allowed():
                return [self._local_embedding(text, dimension=dimension) for text in texts]
            raise

    def _call_json(self, db: Session | None, *, purpose: str, system_prompt: str, user_prompt: str) -> Any | None:
        content = self._call_chat(
            db,
            purpose=purpose,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )
        if content is None:
            return None
        try:
            return _parse_json_payload(content)
        except Exception:
            if self._fallback_allowed():
                return None
            raise bad_request("模型未返回合法 JSON")

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

    def generate_page_script(self, *, title: str | None, content: str, db: Session | None = None) -> str:
        result = self._call_chat(
            db,
            purpose="script",
            system_prompt="你是高校课程 AI 讲解助手。根据单页课件内容生成自然、准确、适合课堂播放的中文讲解稿。",
            user_prompt=f"页面标题：{title or '本页内容'}\n页面内容：{content}\n请输出讲解稿正文，不要输出额外说明。",
        )
        if result:
            return result.strip()
        heading = title or "本页内容"
        summary = _clean_text(content)
        summary = summary[:220] if len(summary) > 220 else summary
        return (
            f"{heading}的核心内容如下：\n"
            f"1. 先理解本页定义与背景：{summary or '本页暂无可提取文字。'}\n"
            f"2. 再关注概念之间的联系与典型应用。\n"
            f"3. 最后结合课程上下文总结本页重点并准备继续学习。"
        )

    def summarize_lesson(self, title: str, page_texts: Sequence[str], db: Session | None = None) -> str:
        merged = " ".join(text.strip() for text in page_texts if text.strip())
        result = self._call_chat(
            db,
            purpose="summary",
            system_prompt="你是课程内容摘要助手，请根据课件页面内容生成简洁准确的课堂摘要。",
            user_prompt=f"课堂标题：{title}\n页面内容：{merged[:6000]}\n请输出 100 字以内中文摘要。",
        )
        if result:
            return result.strip()
        merged = merged[:200] if len(merged) > 200 else merged
        return f"{title}：{merged or '该资料已生成课堂页面，可继续补充讲解脚本。'}"

    def answer_question(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[str] | None = None,
        db: Session | None = None,
    ) -> tuple[str, bool]:
        if not contexts:
            return (
                "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。",
                True,
            )
        context = "\n\n".join(_clean_text(item) for item in contexts if item)
        history_text = "\n".join(history or [])
        messages = RAG_ANSWER_PROMPT.format_messages(
            context=context[:8000],
            history=history_text[:1000],
            question=question,
        )
        result = self._call_chat(
            db,
            purpose="qa",
            system_prompt=str(messages[0].content),
            user_prompt=str(messages[1].content),
        )
        if result:
            return result.strip(), False
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

    def extract_knowledge_points(self, text: str, db: Session | None = None) -> list[str]:
        payload = self._call_json(
            db,
            purpose="knowledge",
            system_prompt="你是课程知识点抽取助手。请只返回 JSON。",
            user_prompt=f"从以下课程内容抽取 3 到 8 个知识点，返回格式：{{\"items\":[\"知识点\"]}}\n{text[:6000]}",
        )
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            items = [str(item).strip() for item in payload["items"] if str(item).strip()]
            if items:
                return items[:8]
        return self.extract_keywords(text, limit=5)

    def generate_problem_guidance(self, *, problem_text: str, level: int, db: Session | None = None) -> str:
        level_name = {1: "思路提示", 2: "步骤引导", 3: "完整解析"}.get(level, "解析")
        result = self._call_chat(
            db,
            purpose="tutoring",
            system_prompt="你是题目辅导助手。按学生请求的层级给出帮助，低层级不要直接泄露完整答案。",
            user_prompt=f"题目：{problem_text}\n请求层级：{level_name}\n请输出中文辅导内容。",
        )
        if result:
            return result.strip()
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

    def generate_common_mistakes(self, knowledge_points: Sequence[str], db: Session | None = None) -> list[str]:
        payload = self._call_json(
            db,
            purpose="tutoring",
            system_prompt="你是学习诊断助手。请只返回 JSON。",
            user_prompt=f"知识点：{list(knowledge_points)}\n生成 3 个常见错误，格式：{{\"items\":[\"错误\"]}}",
        )
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            items = [str(item).strip() for item in payload["items"] if str(item).strip()]
            if items:
                return items[:5]
        base = knowledge_points[0] if knowledge_points else "该知识点"
        return [
            f"忽略 {base} 的适用前提。",
            "只记结论，没有先整理已知条件。",
            "计算完成后没有回头检查边界条件或符号。",
        ]

    def generate_similar_questions(self, knowledge_points: Sequence[str], db: Session | None = None) -> list[str]:
        payload = self._call_json(
            db,
            purpose="tutoring",
            system_prompt="你是练习题生成助手。请只返回 JSON。",
            user_prompt=f"知识点：{list(knowledge_points)}\n生成 3 道相似练习题题干，格式：{{\"items\":[\"题干\"]}}",
        )
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            items = [str(item).strip() for item in payload["items"] if str(item).strip()]
            if items:
                return items[:5]
        base = knowledge_points[0] if knowledge_points else "当前知识点"
        return [
            f"围绕 {base} 的基础概念判断题。",
            f"围绕 {base} 的标准步骤计算题。",
            f"围绕 {base} 的综合应用题。",
        ]

    def generate_knowledge_explanation(
        self,
        *,
        name: str,
        difficulty: str,
        source_text: str,
        db: Session | None = None,
    ) -> dict[str, str]:
        payload = self._call_json(
            db,
            purpose="knowledge",
            system_prompt="你是课程知识点讲解助手。请只返回 JSON。",
            user_prompt=(
                f"知识点：{name}\n难度：{difficulty}\n资料：{source_text[:5000]}\n"
                "返回格式：{\"name\":\"\",\"difficulty\":\"\",\"definition\":\"\",\"principle\":\"\",\"example\":\"\",\"common_mistake\":\"\"}"
            ),
        )
        required = {"name", "difficulty", "definition", "principle", "example", "common_mistake"}
        if isinstance(payload, dict) and required.issubset(payload.keys()):
            return {key: str(payload[key]) for key in required}
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
            "common_mistake": f"常见错误：对 {name} 的适用范围理解不清。",
        }

    def generate_quiz_questions(self, *, topic: str, source_text: str, count: int, db: Session | None = None) -> list[dict]:
        payload = self._call_json(
            db,
            purpose="quiz",
            system_prompt="你是课程测验题生成助手。请只返回 JSON，不要输出解释文字。",
            user_prompt=(
                f"主题：{topic}\n资料：{source_text[:8000]}\n题目数量：{count}\n"
                "返回格式：{\"items\":[{\"question_type\":\"single_choice|judge|short_answer\","
                "\"stem\":\"\",\"options\":[\"\"],\"reference_answer\":{},\"explanation\":\"\",\"score\":10,\"difficulty\":\"standard\"}]}"
            ),
        )
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            questions = [item for item in payload["items"] if isinstance(item, dict)]
            normalized: list[dict] = []
            for item in questions[:count]:
                normalized.append(
                    {
                        "question_type": item.get("question_type") or "short_answer",
                        "stem": str(item.get("stem") or ""),
                        "options": item.get("options"),
                        "reference_answer": item.get("reference_answer") or {},
                        "explanation": str(item.get("explanation") or ""),
                        "score": float(item.get("score") or 10),
                        "difficulty": item.get("difficulty") or "standard",
                    }
                )
            if len(normalized) >= count:
                return normalized
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
            questions.append(templates[len(questions) % len(templates)].copy())
        return questions

    def score_subjective_answer(
        self,
        *,
        reference_keywords: Sequence[str],
        user_answer: str,
        full_score: float,
        db: Session | None = None,
    ) -> tuple[float, str]:
        payload = self._call_json(
            db,
            purpose="quiz",
            system_prompt="你是课程主观题评分助手。请只返回 JSON。",
            user_prompt=(
                f"满分：{full_score}\n参考关键词：{list(reference_keywords)}\n学生答案：{user_answer}\n"
                "返回格式：{\"score\":0,\"feedback\":\"\"}"
            ),
        )
        if isinstance(payload, dict) and "score" in payload:
            score = max(0.0, min(float(full_score), float(payload["score"])))
            return round(score, 2), str(payload.get("feedback") or "")
        tokens = set(self.extract_keywords(user_answer, limit=12))
        expected = {keyword.lower() for keyword in reference_keywords}
        if not expected:
            return round(full_score * 0.6, 2), "答案已提交，当前采用通用评分策略。"
        matched = len(tokens & expected)
        score = round(full_score * matched / len(expected), 2)
        score = min(full_score, max(score, full_score * 0.2 if user_answer.strip() else 0))
        feedback = f"命中关键词 {matched}/{len(expected)}。" if user_answer.strip() else "答案为空，建议先按步骤写出关键结论。"
        return score, feedback

    def generate_study_plan(
        self,
        *,
        goal: str,
        available_days: int,
        daily_minutes: int,
        course_name: str,
        db: Session | None = None,
    ) -> list[dict]:
        payload = self._call_json(
            db,
            purpose="study_plan",
            system_prompt="你是学习计划助手。请只返回 JSON。",
            user_prompt=(
                f"课程：{course_name}\n目标：{goal}\n天数：{available_days}\n每天分钟：{daily_minutes}\n"
                "返回格式：{\"items\":[{\"title\":\"\",\"task_type\":\"study_plan\",\"estimated_minutes\":30,\"summary\":\"\"}]}"
            ),
        )
        today = datetime.now(UTC).date()
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            tasks: list[dict] = []
            for index, item in enumerate(payload["items"][:available_days]):
                if not isinstance(item, dict):
                    continue
                tasks.append(
                    {
                        "title": str(item.get("title") or f"{course_name} 第{index + 1}天学习任务"),
                        "task_date": (today + timedelta(days=index)).isoformat(),
                        "task_type": str(item.get("task_type") or "study_plan"),
                        "estimated_minutes": int(item.get("estimated_minutes") or daily_minutes),
                        "summary": str(item.get("summary") or f"围绕目标“{goal}”完成学习。"),
                    }
                )
            if len(tasks) == available_days:
                return tasks
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

    def generate_teaching_suggestion(
        self,
        *,
        high_frequency_questions: int,
        weak_points: Sequence[str],
        inactive_students: int,
        db: Session | None = None,
    ) -> str:
        result = self._call_chat(
            db,
            purpose="analysis",
            system_prompt="你是教学分析助手，请根据学情数据给教师生成可执行建议。",
            user_prompt=(
                f"高频问题数：{high_frequency_questions}\n薄弱点：{list(weak_points)}\n"
                f"低活跃学生数：{inactive_students}\n请输出中文教学建议。"
            ),
        )
        if result:
            return result.strip()
        weak = "、".join(weak_points[:3]) if weak_points else "当前暂无明显薄弱点"
        return (
            f"本课程近期高频问题数为 {high_frequency_questions}。"
            f"建议优先回讲 {weak}，并针对 {inactive_students} 名低活跃学生安排提醒或补学任务。"
        )


ai_service = AIService()
