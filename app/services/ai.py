from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from collections.abc import Iterator, Sequence
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


_GENERIC_QUIZ_LABELS = {
    "章节练习",
    "薄弱点章节练习",
    "错题重练",
    "章节自练",
    "课程测验",
    "练习",
    "测验",
}


def _is_generic_quiz_label(value: str) -> bool:
    text = _clean_text(value)
    return not text or text in _GENERIC_QUIZ_LABELS or any(label in text for label in ("章节练习", "薄弱点章节练习", "错题重练"))


def _quiz_source_sentences(source_text: str, *, limit: int = 8) -> list[str]:
    clean = _clean_text(source_text)
    sentences = [item.strip(" ：:，,") for item in re.split(r"[。！？!?；;\n]+", clean) if item.strip()]
    return [item[:90] for item in sentences if len(item) >= 6][:limit]


def _invalid_quiz_stem(stem: str) -> bool:
    text = _clean_text(stem)
    if not text:
        return True
    if "课程资料的是哪一项" in text:
        return True
    return bool(re.search(r"关于[“\"']?(章节练习|薄弱点章节练习|错题重练|章节自练)[”\"']?", text))


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


@dataclass
class ChatResult:
    content: str
    reasoning: str | None = None


@dataclass
class ChatDelta:
    kind: str
    text: str


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
        result = self._call_chat_with_meta(
            db,
            purpose=purpose,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
        )
        return result.content if result else None

    def _split_thinking_from_content(self, content: str) -> ChatResult:
        match = re.search(r"<think(?:ing)?>(.*?)</think(?:ing)?>", content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ChatResult(content=content)
        reasoning = match.group(1).strip()
        answer = (content[: match.start()] + content[match.end() :]).strip()
        return ChatResult(content=answer or content.strip(), reasoning=reasoning or None)

    def _reasoning_from_message(self, message: dict[str, Any]) -> str | None:
        for key in ("reasoning_content", "reasoning", "thinking", "thought", "thoughts"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                text = "\n".join(str(item).strip() for item in value if str(item).strip())
                if text:
                    return text
        return None

    def _text_from_content_part(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            pieces: list[str] = []
            for item in value:
                if isinstance(item, str):
                    pieces.append(item)
                elif isinstance(item, dict):
                    pieces.append(str(item.get("text") or item.get("content") or ""))
            return "".join(pieces)
        return str(value)

    def _call_chat_with_meta(
        self,
        db: Session | None,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> ChatResult | None:
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
                    result = self._split_thinking_from_content(str(content))
                    result.reasoning = self._reasoning_from_message(message) or result.reasoning
                    return result
            if body.get("output"):
                output = body["output"]
                if isinstance(output, dict):
                    content = str(output.get("text") or output.get("content") or "")
                    result = self._split_thinking_from_content(content)
                    result.reasoning = self._reasoning_from_message(output) or result.reasoning
                    return result
            raise bad_request("模型响应格式不符合 OpenAI 兼容规范")
        except Exception:
            if self._fallback_allowed():
                return None
            raise

    def _stream_chat_with_meta(
        self,
        db: Session | None,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> Iterator[ChatDelta]:
        config = get_default_model_config(db, purpose)
        if config is None or config.provider == "mock":
            if self._fallback_allowed():
                return
            raise bad_request(f"缺少 {purpose} 模型配置，请先在管理员模型配置中启用模型")
        if not config.endpoint:
            if self._fallback_allowed():
                return
            raise bad_request(f"{purpose} 模型配置缺少 endpoint")

        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
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
            "stream": True,
        }
        if config.extra_config.get("max_tokens"):
            payload["max_tokens"] = config.extra_config["max_tokens"]
        if json_mode and config.extra_config.get("enable_response_format", True):
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self.settings.external_service_timeout_seconds) as client:
                with client.stream("POST", self._chat_endpoint(config.endpoint), headers=headers, json=payload) as response:
                    if response.status_code >= 400:
                        error_text = response.read().decode("utf-8", errors="ignore")
                        raise bad_request(f"模型调用失败: HTTP {response.status_code} {error_text[:300]}")
                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" not in content_type:
                        body = response.read()
                        payload_text = body.decode("utf-8", errors="ignore")
                        parsed = _parse_json_payload(payload_text)
                        choices = parsed.get("choices") if isinstance(parsed, dict) else []
                        message = choices[0].get("message") if choices else None
                        if isinstance(message, dict):
                            content = self._text_from_content_part(message.get("content"))
                            result = self._split_thinking_from_content(content)
                            reasoning = self._reasoning_from_message(message) or result.reasoning
                            if reasoning:
                                yield ChatDelta("reasoning", reasoning)
                            if result.content:
                                yield ChatDelta("content", result.content)
                        return
                    for line in response.iter_lines():
                        text = line.strip()
                        if not text or not text.startswith("data:"):
                            continue
                        data = text[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") if isinstance(chunk, dict) else None
                        if choices:
                            delta = choices[0].get("delta") or {}
                            reasoning = self._reasoning_from_message(delta)
                            if reasoning:
                                yield ChatDelta("reasoning", reasoning)
                            content = self._text_from_content_part(delta.get("content"))
                            if content:
                                yield ChatDelta("content", content)
                            continue
                        output = chunk.get("output") if isinstance(chunk, dict) else None
                        if isinstance(output, dict):
                            reasoning = self._reasoning_from_message(output)
                            if reasoning:
                                yield ChatDelta("reasoning", reasoning)
                            content = self._text_from_content_part(output.get("text") or output.get("content"))
                            if content:
                                yield ChatDelta("content", content)
        except Exception:
            if self._fallback_allowed():
                return
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
            system_prompt="你是高校课程 AI 讲解助手。根据单页课件内容生成自然、准确、适合课时讲解和语音播放的中文讲解稿。",
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
            system_prompt="你是课程内容摘要助手，请根据课件页面内容生成简洁准确的课时摘要。",
            user_prompt=f"课时标题：{title}\n页面内容：{merged[:6000]}\n请输出 100 字以内中文摘要。",
        )
        if result:
            return result.strip()
        merged = merged[:200] if len(merged) > 200 else merged
        return f"{title}：{merged or '该资料已生成课时页面，可继续补充讲解脚本。'}"

    def answer_question(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[str] | None = None,
        db: Session | None = None,
    ) -> tuple[str, bool, str | None]:
        if not contexts:
            return (
                "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。",
                True,
                None,
            )
        context = "\n\n".join(_clean_text(item) for item in contexts if item)
        history_text = "\n".join(history or [])
        messages = RAG_ANSWER_PROMPT.format_messages(
            context=context[:8000],
            history=history_text[:1000],
            question=question,
        )
        result = self._call_chat_with_meta(
            db,
            purpose="qa",
            system_prompt=str(messages[0].content),
            user_prompt=str(messages[1].content),
        )
        if result:
            return result.content.strip(), False, result.reasoning
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
        return answer, False, "本次使用本地降级逻辑：根据检索到的课程片段生成回答，未收到上游模型思考过程。"

    def stream_answer_question(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[str] | None = None,
        db: Session | None = None,
    ) -> Iterator[ChatDelta]:
        if not contexts:
            yield ChatDelta("content", "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。")
            return
        context = "\n\n".join(_clean_text(item) for item in contexts if item)
        history_text = "\n".join(history or [])
        messages = RAG_ANSWER_PROMPT.format_messages(
            context=context[:6000],
            history=history_text[:1000],
            question=question,
        )
        emitted = False
        for delta in self._stream_chat_with_meta(
            db,
            purpose="qa",
            system_prompt=str(messages[0].content),
            user_prompt=str(messages[1].content),
        ):
            emitted = True
            yield delta
        if emitted:
            return
        context_excerpt = context[:320]
        history_hint = ""
        if history:
            history_hint = f"\n结合你前面的问题（{'；'.join(history[-2:])}），可以把本题和前序概念一起对照。"
        yield ChatDelta(
            "content",
            "根据已检索到的课程资料，可以这样理解："
            f"{context_excerpt}"
            "\n\n如果你要继续追问，建议从定义、适用条件、典型例题三个角度继续展开。"
            f"{history_hint}",
        )

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
        clean_source = _clean_text(source_text)
        payload = self._call_json(
            db,
            purpose="quiz",
            system_prompt="你是课程测验题生成助手。请只返回 JSON，不要输出解释文字。",
            user_prompt=(
                f"考查主题：{topic}\n课程资料：{clean_source[:8000]}\n题目数量：{count}\n"
                "要求：只能依据课程资料出题；题干必须包含资料中的具体概念、定义、公式、案例或事实；"
                "禁止把“章节练习、薄弱点章节练习、错题重练、测验”等练习名称当作考点；"
                "如果资料不足以出题，返回 {\"items\":[]}。\n"
                "返回格式：{\"items\":[{\"question_type\":\"single_choice|judge|short_answer\","
                "\"stem\":\"\",\"options\":[\"\"],\"reference_answer\":{},\"explanation\":\"\",\"score\":10,\"difficulty\":\"standard\"}]}"
            ),
        )
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            questions = [item for item in payload["items"] if isinstance(item, dict)]
            normalized: list[dict] = []
            for item in questions[:count]:
                stem = str(item.get("stem") or "")
                if _invalid_quiz_stem(stem):
                    continue
                normalized.append(
                    {
                        "question_type": item.get("question_type") or "short_answer",
                        "stem": stem,
                        "options": item.get("options"),
                        "reference_answer": item.get("reference_answer") or {},
                        "explanation": str(item.get("explanation") or ""),
                        "score": float(item.get("score") or 10),
                        "difficulty": item.get("difficulty") or "standard",
                    }
                )
            if len(normalized) >= count:
                return normalized
        sentences = _quiz_source_sentences(clean_source)
        if not sentences:
            raise bad_request("课程资料不足，无法生成有效题目")
        keywords = [item for item in self.extract_keywords(clean_source, limit=12) if not _is_generic_quiz_label(item)]
        if not keywords and not _is_generic_quiz_label(topic):
            keywords = [topic]
        if not keywords:
            keywords = [sentences[0][:18]]
        questions: list[dict] = []
        while len(questions) < count:
            index = len(questions)
            concept = keywords[index % len(keywords)]
            evidence = sentences[index % len(sentences)]
            mode = index % 3
            if mode == 0:
                questions.append(
                    {
                        "question_type": "single_choice",
                        "stem": f"根据课程资料，“{concept}”更接近下列哪种表述？",
                        "options": [
                            evidence[:64],
                            "只需要记住结论，不需要理解条件",
                            "与本课程资料中的核心内容无关",
                            "在任何场景下都可以直接套用固定答案",
                        ],
                        "reference_answer": {"value": 0},
                        "explanation": f"资料中的依据是：{evidence}",
                        "score": 10,
                        "difficulty": "standard",
                    }
                )
            elif mode == 1:
                questions.append(
                    {
                        "question_type": "judge",
                        "stem": f"判断：理解“{concept}”时应结合课程资料中的具体条件或语境。",
                        "options": ["正确", "错误"],
                        "reference_answer": {"value": 0},
                        "explanation": f"课程资料相关表述：{evidence}",
                        "score": 10,
                        "difficulty": "standard",
                    }
                )
            else:
                questions.append(
                    {
                        "question_type": "short_answer",
                        "stem": f"请结合课程资料，简述“{concept}”的含义或作用。",
                        "options": None,
                        "reference_answer": {"keywords": self.extract_keywords(evidence, limit=3)},
                        "explanation": f"答题时应围绕资料中的关键依据展开：{evidence}",
                        "score": 20,
                        "difficulty": "advanced",
                    }
                )
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

    def generate_student_recommendation(
        self,
        *,
        course_count: int,
        pending_tasks: int,
        recent_lesson_title: str | None,
        weak_points: Sequence[str],
        study_hours: float,
        completion_rate: float,
        accuracy: float,
        db: Session | None = None,
    ) -> str:
        weak = list(weak_points[:3])
        result = self._call_chat(
            db,
            purpose="analysis",
            system_prompt="你是学生学习助手，请根据学生个人学习数据生成一条简短、可执行的今日学习建议。",
            user_prompt=(
                f"已加入课程数：{course_count}\n今日待完成任务数：{pending_tasks}\n"
                f"最近学习课时：{recent_lesson_title or '暂无'}\n薄弱知识点：{weak}\n"
                f"本周学习小时：{study_hours}\n课时完成率：{completion_rate}%\n练习正确率：{accuracy}%\n"
                "请输出 1 句话中文建议，面向学生本人，不要提到教师管理。"
            ),
        )
        if result:
            return result.strip()
        if pending_tasks > 0:
            return f"今天先完成 {pending_tasks} 个学习任务，再用 10 分钟复盘最近课时。"
        if weak:
            return f"建议今天优先复盘 {weak[0]}，并完成 3 到 5 道相关练习。"
        if recent_lesson_title:
            return f"建议从《{recent_lesson_title}》继续学习，并在课后整理 3 个关键概念。"
        return "建议选择一门课程完成一个课时，并用练习检查掌握情况。"


ai_service = AIService()
