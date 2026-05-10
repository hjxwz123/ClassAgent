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
    clean = sanitize_quiz_source_text(source_text)
    sentences = [item.strip(" ：:，,") for item in re.split(r"[。！？!?；;\n]+", clean) if item.strip()]
    return [item[:110] for item in sentences if _valid_quiz_sentence(item)][:limit]


_QUIZ_NOISE_WORDS = {
    "http",
    "https",
    "jpeg",
    "jpg",
    "png",
    "gif",
    "webp",
    "classagent",
    "oss",
    "aliyuncs",
    "beijing",
    "docmind",
    "docmind_images",
    "com",
    "cn",
}

_GENERIC_OPTION_PATTERNS = (
    r"只需要记住结论",
    r"无需理解",
    r"不需要理解",
    r"与本课程资料.*无关",
    r"与课程内容无关",
    r"可以跳过",
    r"固定答案",
    r"任何场景.*直接套用",
)

_DIRECT_SHORT_ANSWER_PATTERNS = (
    r"何时",
    r"什么时候",
    r"在哪个阶段",
    r"是什么",
    r"什么是",
    r"哪一(?:个|项|种)",
    r"哪个",
    r"下列",
    r"是否",
    r"对不对",
    r"正确吗",
    r"谁",
    r"多少",
    r"几年",
    r"哪年",
)

_EXPLANATORY_SHORT_ANSWER_PATTERNS = (
    r"简述",
    r"说明",
    r"解释",
    r"阐述",
    r"分析",
    r"概括",
    r"比较",
    r"列举",
    r"描述",
    r"谈谈",
    r"为什么",
    r"原因",
    r"作用",
    r"关系",
    r"区别",
    r"联系",
    r"特点",
    r"步骤",
    r"任务",
)


def _contains_quiz_noise(value: str) -> bool:
    text = _clean_text(value)
    lower = text.lower()
    if re.search(r"https?://|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)", text, re.I):
        return True
    if re.search(r"\b[a-f0-9]{8,}\b", lower):
        return True
    if re.search(r"\b\w+\.(?:jpeg|jpg|png|gif|webp|bmp)\b", lower):
        return True
    return any(re.search(rf"\b{re.escape(word)}\b", lower) for word in _QUIZ_NOISE_WORDS)


def _cjk_count(value: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", value))


def _has_formula_signal(value: str) -> bool:
    return bool(re.search(r"(:=|->|→|=>|[A-Z]\.[A-Za-z]|[SL]-属性|[A-Z]\s*→)", value))


def sanitize_quiz_source_text(source_text: str) -> str:
    raw = str(source_text or "")
    raw = re.sub(r"!\[[^\]]*\]\([^)]+\)", "\n", raw)
    raw = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", raw)
    raw = re.sub(r"https?://\S+", " ", raw, flags=re.I)
    raw = re.sub(r"\b\S+\.(?:jpeg|jpg|png|gif|webp|bmp)\b", " ", raw, flags=re.I)
    raw = re.sub(r"\b[a-f0-9]{8,}\b", " ", raw, flags=re.I)
    raw = re.sub(r"\b(?:classagent|aliyuncs|docmind_images|docmind|oss-cn-[a-z-]+|oss|https?|jpeg|jpg|png|gif|webp|bmp)\b", " ", raw, flags=re.I)
    pieces: list[str] = []
    for line in raw.splitlines():
        clean = _clean_text(line).strip(" ：:，,")
        clean = re.sub(r"^第\s*\d+\s*页\s*[>：:、,，.\-—]*\s*", "", clean)
        clean = re.sub(r"\b第\s*\d+\s*页\b", "", clean)
        clean = _clean_text(clean).strip(" ：:，,")
        if not clean:
            continue
        if _contains_quiz_noise(clean):
            continue
        if re.fullmatch(r"第\s*\d+\s*页", clean):
            continue
        if _cjk_count(clean) < 2 and not _has_formula_signal(clean):
            continue
        for index in range(0, len(clean), 420):
            chunk = clean[index : index + 420].strip()
            if chunk:
                pieces.append(chunk)
    return "\n".join(pieces)


def _valid_quiz_sentence(value: str) -> bool:
    text = _clean_text(value).strip(" ：:，,")
    if len(text) < 6:
        return False
    if _contains_quiz_noise(text):
        return False
    if re.fullmatch(r"第\s*\d+\s*页", text):
        return False
    return _cjk_count(text) >= 4 or _has_formula_signal(text)


def _valid_quiz_option(value: str) -> bool:
    text = _clean_text(value).strip(" ：:，,")
    if len(text) < 2:
        return False
    if _contains_quiz_noise(text):
        return False
    if re.fullmatch(r"第\s*\d+\s*页", text):
        return False
    if any(re.search(pattern, text) for pattern in _GENERIC_OPTION_PATTERNS):
        return False
    return _cjk_count(text) >= 2 or _has_formula_signal(text)


def _valid_quiz_keyword(value: str) -> bool:
    text = _clean_text(value).strip(" ：:，,._-")
    if len(text) < 2 or len(text) > 28:
        return False
    if _is_generic_quiz_label(text) or _contains_quiz_noise(text):
        return False
    if re.fullmatch(r"第\s*\d+\s*页", text):
        return False
    if _cjk_count(text) == 0 and not re.search(r"[SL]-属性|[A-Z]\.[A-Za-z]|[A-Z]\s*→", text):
        return False
    return True


def _valid_short_answer_stem(stem: str) -> bool:
    text = _clean_text(stem)
    if len(text) < 10:
        return False
    if any(re.search(pattern, text) for pattern in _DIRECT_SHORT_ANSWER_PATTERNS):
        return False
    return any(re.search(pattern, text) for pattern in _EXPLANATORY_SHORT_ANSWER_PATTERNS)


def _quiz_answer_index(value: Any, *, options: list[str] | None = None, question_type: str = "single_choice") -> int | None:
    if isinstance(value, bool):
        return 0 if value else 1
    if isinstance(value, int):
        return value
    text = _clean_text(str(value or ""))
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if len(text) == 1 and text.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return ord(text.upper()) - ord("A")
    if question_type == "judge":
        if text.lower() in {"true", "yes", "正确", "对", "是"}:
            return 0
        if text.lower() in {"false", "no", "错误", "错", "否"}:
            return 1
    if options:
        for index, option in enumerate(options):
            if _clean_text(option) == text:
                return index
    return None


def _quiz_answer_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    text = _clean_text(str(value or ""))
    if not text:
        return []
    if re.fullmatch(r"[A-Za-z]{2,}", text):
        return list(text)
    if re.search(r"[,，、;；\s]+", text):
        return [item for item in re.split(r"[,，、;；\s]+", text) if item]
    return [value]


def _normalize_quiz_reference_answer(item: dict[str, Any], *, options: list[str] | None, question_type: str) -> dict[str, Any]:
    raw = _quiz_item_value(
        item,
        "reference_answer",
        "answer",
        "correct_answer",
        "correctAnswer",
        "correct",
        "答案",
        "正确答案",
    )
    if question_type in {"single_choice", "multiple_choice", "judge"}:
        candidates: list[Any] = []
        if isinstance(raw, dict):
            for key in (
                "value",
                "values",
                "answer",
                "correct_answer",
                "correctAnswer",
                "correct",
                "option_index",
                "option_indexes",
                "index",
                "indexes",
                "key",
                "text",
                "choice",
                "correct_option",
                "correct_options",
                "judge",
                "答案",
                "正确答案",
            ):
                if key in raw:
                    candidates.append(raw[key])
        else:
            candidates.append(raw)
        if question_type == "multiple_choice":
            indexes: list[int] = []
            for candidate in candidates:
                for value in _quiz_answer_values(candidate):
                    index = _quiz_answer_index(value, options=options, question_type=question_type)
                    if index is not None and options and 0 <= index < len(options) and index not in indexes:
                        indexes.append(index)
            return {"value": indexes} if indexes else {}
        for candidate in candidates:
            index = _quiz_answer_index(candidate, options=options, question_type=question_type)
            if index is not None and options and 0 <= index < len(options):
                return {"value": index}
        return {}
    if isinstance(raw, dict) and isinstance(raw.get("keywords"), list):
        keywords = [str(item).strip() for item in raw["keywords"] if _valid_quiz_keyword(str(item))]
        return {"keywords": keywords} if keywords else {}
    if isinstance(raw, list):
        keywords = [str(item).strip() for item in raw if _valid_quiz_keyword(str(item))]
        return {"keywords": keywords} if keywords else {}
    if raw:
        keywords = []
        for item in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", str(raw)):
            if _valid_quiz_keyword(item) and item not in keywords:
                keywords.append(item)
            if len(keywords) >= 5:
                break
        return {"keywords": keywords} if keywords else {}
    return {}


def _quiz_item_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _normalize_quiz_question_type(value: Any) -> str:
    raw = _clean_text(str(value or "")).strip()
    text = raw.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "single_choice": "single_choice",
        "single": "single_choice",
        "choice": "single_choice",
        "select": "single_choice",
        "multiple_choice": "multiple_choice",
        "multi_choice": "multiple_choice",
        "multiple": "multiple_choice",
        "judge": "judge",
        "judgement": "judge",
        "judgment": "judge",
        "true_false": "judge",
        "truefalse": "judge",
        "short_answer": "short_answer",
        "shortanswer": "short_answer",
        "short": "short_answer",
        "blank": "blank",
        "fill_blank": "blank",
        "essay": "essay",
    }
    if text in aliases:
        return aliases[text]
    if any(label in raw for label in ("单选", "单项选择", "选择题")):
        return "single_choice"
    if any(label in raw for label in ("多选", "多项选择")):
        return "multiple_choice"
    if "判断" in raw or "正误" in raw:
        return "judge"
    if any(label in raw for label in ("简答", "问答")):
        return "short_answer"
    if "填空" in raw:
        return "blank"
    if "论述" in raw:
        return "essay"
    return "short_answer"


_QUIZ_GENERATION_TYPES = {"single_choice", "multiple_choice", "judge", "blank", "short_answer"}


def _quiz_has_calculation_context(source_text: str) -> bool:
    return _has_formula_signal(source_text) or bool(
        re.search(
            r"(公式|计算|推导|矩阵|行列式|方程|函数|概率|统计|算法|复杂度|比例|百分比|利率|成本|收益|"
            r"速度|面积|体积|浓度|电压|电流|求解|证明|\d+\s*[+\-*/=<>])",
            source_text,
        )
    )


def _quiz_generation_style_instruction(*, count: int, candidate_count: int, source_text: str) -> str:
    applied_target = max(1, min(candidate_count, math.ceil(max(count, 1) * 0.6)))
    concept_limit = max(1, math.floor(candidate_count * 0.35))
    calculation_instruction = (
        f"资料包含公式、算法、数量关系或推导信号，候选题中至少 {max(1, min(applied_target, candidate_count))} 道应为计算题、推导题、步骤题或条件判断题；"
        if _quiz_has_calculation_context(source_text)
        else "若当前知识点不适合计算，必须用案例分析题、场景应用题、例题变式题或错误诊断题替代计算题；"
    )
    return (
        "题目风格硬性要求：不要只出概念记忆题；"
        f"直接问定义、是什么、包括哪些、哪项表述正确的纯概念题最多 {concept_limit} 道候选题；"
        f"至少 {applied_target} 道候选题必须是应用题、计算题、案例题、例题变式题、错误诊断题或综合分析题；"
        "items 数组前面的题目优先放应用/计算/案例/变式题，概念题放在后面，避免系统选题时只选到概念题；"
        "应用型题目必须给出具体情境、条件、数据、公式、案例、学生错误答案或新例子，要求学生计算结果、选择方案、分析原因、判断适用条件或说明步骤；"
        "可以基于资料中的知识点构造新的小案例、新数值和新例题，但结论必须能由课程资料知识点和通用学科知识推出；"
        f"{calculation_instruction}"
        "禁止所有题干都写成“下列说法正确的是/哪一项正确/是什么”。"
    )


_QUIZ_APPLIED_STEM_PATTERN = re.compile(
    r"(案例|场景|情境|应用|计算|求|推导|步骤|分析|原因|影响|条件|方案|设计|选择.*方案|给定|已知|假设|"
    r"若|如果|当.*时|错误|诊断|改正|判断.*适用|例题|变式|实际|业务|工程|实验|数据|表格|代码|算法|"
    r"成本|收益|概率|矩阵|行列式|方程|函数|证明)"
)
_QUIZ_CONCEPT_STEM_PATTERN = re.compile(r"(是什么|定义|包括哪些|哪一项正确|哪项正确|说法正确|表示什么|属于哪)")


def _quiz_application_score(question: dict) -> int:
    stem = str(question.get("stem") or "")
    score = 0
    if _QUIZ_APPLIED_STEM_PATTERN.search(stem):
        score += 3
    if question.get("question_type") in {"blank", "short_answer"} and re.search(r"(分析|说明|解释|比较|步骤|原因)", stem):
        score += 1
    if _QUIZ_CONCEPT_STEM_PATTERN.search(stem):
        score -= 2
    return score


def _prioritize_quiz_question_mix(questions: list[dict]) -> list[dict]:
    return [
        question
        for _index, question in sorted(
            enumerate(questions),
            key=lambda item: (-_quiz_application_score(item[1]), item[0]),
        )
    ]


def _select_quiz_questions_by_type_counts(
    questions: list[dict],
    type_counts: dict[str, int] | None,
) -> tuple[list[dict], dict[str, int]]:
    if not type_counts:
        return questions, {}
    selected: list[dict] = []
    missing: dict[str, int] = {}
    used_indexes: set[int] = set()
    for question_type, expected_count in type_counts.items():
        picked = 0
        for index, question in enumerate(questions):
            if index in used_indexes or question.get("question_type") != question_type:
                continue
            selected.append(question)
            used_indexes.add(index)
            picked += 1
            if picked >= expected_count:
                break
        if picked < expected_count:
            missing[question_type] = expected_count - picked
    return selected, missing


def _normalize_quiz_questions_from_payload(payload: Any, *, count: int, seen_stems: set[str] | None = None) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise bad_request("AI 出题失败：模型未返回有效 JSON 题目")
    seen = seen_stems if seen_stems is not None else set()
    normalized: list[dict] = []
    questions = [item for item in payload["items"] if isinstance(item, dict)]
    for item in questions:
        stem = str(_quiz_item_value(item, "stem", "question", "title", "题干", "问题") or "")
        if _invalid_quiz_stem(stem):
            continue
        clean_stem = _clean_text(stem)
        if clean_stem in seen:
            continue
        explanation = _clean_text(str(_quiz_item_value(item, "explanation", "analysis", "解析", "说明") or ""))
        if _contains_quiz_noise(explanation):
            continue
        question_type = _normalize_quiz_question_type(_quiz_item_value(item, "question_type", "type", "题型"))
        options = _quiz_item_value(item, "options", "choices", "选项")
        if question_type in {"single_choice", "multiple_choice", "judge"}:
            if question_type == "judge":
                clean_options = ["正确", "错误"]
            else:
                if not isinstance(options, list):
                    continue
                clean_options = []
                for option in options:
                    clean_option = _clean_text(str(option))[:90]
                    if clean_option and _valid_quiz_option(clean_option) and clean_option not in clean_options:
                        clean_options.append(clean_option)
                if question_type == "single_choice" and len(clean_options) < 4:
                    continue
                if len(clean_options) < 2:
                    continue
            options = clean_options[:4]
        else:
            options = None
        reference_answer = _normalize_quiz_reference_answer(item, options=options, question_type=question_type)
        if question_type in {"single_choice", "judge"} and "value" not in reference_answer:
            continue
        if question_type == "multiple_choice":
            values = reference_answer.get("value") if isinstance(reference_answer, dict) else None
            if not isinstance(values, list) or not values:
                continue
        if question_type in {"short_answer", "blank"}:
            if not _valid_short_answer_stem(clean_stem):
                if question_type == "short_answer":
                    continue
            min_keywords = 1 if question_type == "blank" else 2
            if "keywords" not in reference_answer or len(reference_answer["keywords"]) < min_keywords:
                continue
        if question_type not in _QUIZ_GENERATION_TYPES:
            continue
        normalized.append(
            {
                "question_type": question_type,
                "stem": clean_stem,
                "options": options,
                "reference_answer": reference_answer,
                "explanation": explanation,
                "score": float(item.get("score") or 10),
                "difficulty": item.get("difficulty") or "standard",
            }
        )
        seen.add(clean_stem)
        if len(normalized) >= count:
            break
    return normalized


def _invalid_quiz_stem(stem: str) -> bool:
    text = _clean_text(stem)
    if not text:
        return True
    if _contains_quiz_noise(text):
        return True
    if re.search(r"“\s*第\s*\d+\s*页\s*”", text):
        return True
    if "课程资料的是哪一项" in text:
        return True
    if "更接近下列哪种表述" in text:
        return True
    if any(re.search(pattern, text) for pattern in _GENERIC_OPTION_PATTERNS):
        return True
    return bool(re.search(r"关于[“\"']?(章节练习|薄弱点章节练习|错题重练|章节自练)[”\"']?", text))


RAG_ANSWER_SYSTEM_PROMPT = (
    "你是课程知识问答助手。必须优先依据给定课程资料回答。"
    "如果资料中包含“结构化教学对象”或“题型模板”，可以把模板中的条件、步骤、变量槽位迁移到学生的新题干，"
    "但要说明这是同题型迁移，不要声称课件出现过完全相同题目。"
    "如果学生要求解释、举例或类比，可以围绕资料中的概念、公式和条件生成教学示例，"
    "并明确这是用于说明资料内容的例子；不要因为资料里没有现成示例就直接说资料不足。"
    "只有当给定资料与问题完全无关或缺少关键定义时，才说明资料不足，不能编造与资料矛盾的内容。"
)
RAG_ANSWER_USER_INSTRUCTIONS = (
    "请用中文回答。若问题提到某一页，优先使用资料中标注的当前页内容；"
    "若要求“用例子解释”，请基于资料里的公式、条件或概念构造一个简短例子，并给出关键依据。"
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
        allow_fallback: bool = True,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
    ) -> str | None:
        result = self._call_chat_with_meta(
            db,
            purpose=purpose,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=json_mode,
            allow_fallback=allow_fallback,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
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
        messages: Sequence[dict[str, str]] | None = None,
        json_mode: bool = False,
        allow_fallback: bool = True,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
    ) -> ChatResult | None:
        config = get_default_model_config(db, purpose)
        if config is None or config.provider == "mock":
            if allow_fallback and self._fallback_allowed():
                return None
            raise bad_request(f"缺少 {purpose} 模型配置，请先在管理员模型配置中启用模型")
        if not config.endpoint:
            if allow_fallback and self._fallback_allowed():
                return None
            raise bad_request(f"{purpose} 模型配置缺少 endpoint")

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(config.extra_config.get("headers") or {})
        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": list(messages) if messages is not None else [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": config.extra_config.get("temperature", 0.2),
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        elif config.extra_config.get("max_tokens"):
            payload["max_tokens"] = config.extra_config["max_tokens"]
        if json_mode and config.extra_config.get("enable_response_format", True):
            payload["response_format"] = {"type": "json_object"}

        try:
            request_timeout = timeout_seconds or self.settings.external_service_timeout_seconds
            timeout = httpx.Timeout(request_timeout, connect=min(15.0, request_timeout), read=request_timeout, write=request_timeout)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(self._chat_endpoint(config.endpoint), headers=headers, json=payload)
                if response.status_code >= 400 and json_mode and "response_format" in payload:
                    retry_payload = dict(payload)
                    retry_payload.pop("response_format", None)
                    response = client.post(self._chat_endpoint(config.endpoint), headers=headers, json=retry_payload)
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
        except httpx.TimeoutException as exc:
            if allow_fallback and self._fallback_allowed():
                return None
            request_timeout = timeout_seconds or self.settings.external_service_timeout_seconds
            raise bad_request(f"模型调用超时：{int(request_timeout)} 秒内未返回结果，请稍后重试，或减少题目数量/资料范围。") from exc
        except httpx.HTTPError as exc:
            if allow_fallback and self._fallback_allowed():
                return None
            raise bad_request(f"模型调用失败: {exc}") from exc
        except Exception:
            if allow_fallback and self._fallback_allowed():
                return None
            raise

    def _stream_chat_with_meta(
        self,
        db: Session | None,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        messages: Sequence[dict[str, str]] | None = None,
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
            "messages": list(messages) if messages is not None else [
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

    def _configured_embedding_dimension(self, config: Any | None) -> int:
        raw_dimension = None
        if config is not None:
            raw_dimension = (config.extra_config or {}).get("dimensions")
        try:
            dimension = int(raw_dimension) if raw_dimension else int(self.settings.embedding_dimension)
        except (TypeError, ValueError):
            dimension = int(self.settings.embedding_dimension)
        return dimension if dimension > 0 else 1536

    def embed_texts(self, db: Session | None, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        config = get_default_model_config(db, "embedding")
        dimension = self._configured_embedding_dimension(config)
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
            vectors = [[float(value) for value in embedding] for embedding in embeddings]
            if config.extra_config.get("dimensions") and any(len(vector) != dimension for vector in vectors):
                actual = len(vectors[0]) if vectors else 0
                raise bad_request(f"Embedding 维度不一致：期望 {dimension}，实际 {actual}")
            return vectors
        except Exception:
            if self._fallback_allowed():
                return [self._local_embedding(text, dimension=dimension) for text in texts]
            raise

    def _call_json(
        self,
        db: Session | None,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        allow_fallback: bool = True,
    ) -> Any | None:
        content = self._call_chat(
            db,
            purpose=purpose,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            allow_fallback=allow_fallback,
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

    def rewrite_retrieval_query(
        self,
        *,
        question: str,
        history: Sequence[Any] | None = None,
        db: Session | None = None,
    ) -> str:
        history_lines = "\n".join(
            f"- {item['role']}: {item['content']}"
            for item in self._normalize_history_messages(history)[-4:]
        )
        try:
            payload = self._call_json(
                db,
                purpose="qa",
                system_prompt=(
                    "你是课程问答检索改写器。你的任务是把学生问题改写成更适合检索课程资料的查询。"
                    "不要回答问题。要去掉具体数字、人名、变量名、样例细节，保留知识点、题型、方法、步骤、条件和目标。"
                    "必须只返回 JSON。"
                ),
                user_prompt=(
                    f"前序对话：\n{history_lines or '无'}\n"
                    f"当前问题：{question}\n"
                    "返回格式："
                    "{\"retrieval_query\":\"改写后的检索查询\","
                    "\"keywords\":[\"关键词1\",\"关键词2\"]}"
                ),
            )
        except Exception:
            payload = None
        if isinstance(payload, dict):
            rewritten = str(payload.get("retrieval_query") or "").strip()
            if rewritten:
                keywords = [str(item).strip() for item in (payload.get("keywords") or []) if str(item).strip()]
                if keywords:
                    return f"{rewritten}\n检索关键词：{' '.join(keywords[:8])}"[:320]
                return rewritten[:320]
        return self._heuristic_retrieval_query(question=question, history=history)

    def classify_qa_question_scope(
        self,
        *,
        question: str,
        course_name: str,
        chapters: Sequence[dict],
        db: Session | None = None,
    ) -> dict[str, Any]:
        chapter_lines = "\n".join(
            f"- id={item.get('id')}, order={item.get('order_index')}, title={item.get('title')}"
            for item in chapters[:30]
        )
        try:
            payload = self._call_json(
                db,
                purpose="qa",
                system_prompt=(
                    "你是课程问答检索意图分类器。只判断问题应该检索的范围，不回答问题。"
                    "必须只返回 JSON。scope 只能是 specific、chapter_overview、course_overview。"
                    "specific 表示询问具体概念、公式、例题、定义或单点疑问；"
                    "chapter_overview 表示要求总结某一章/某个章节的重点、提纲、框架、复习内容；"
                    "course_overview 表示要求总结整门课/当前课程/全部内容的重点、提纲、框架、复习内容。"
                ),
                user_prompt=(
                    f"课程名称：{course_name}\n"
                    f"章节列表：\n{chapter_lines or '无'}\n"
                    f"学生问题：{question}\n"
                    "返回格式："
                    "{\"scope\":\"specific|chapter_overview|course_overview\","
                    "\"chapter_id\":数字或null,"
                    "\"confidence\":0到1,"
                    "\"reason\":\"简短原因\"}"
                ),
            )
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            return {"scope": "specific", "chapter_id": None, "confidence": 0, "reason": "classifier_unavailable"}
        scope = str(payload.get("scope") or "specific").strip()
        if scope not in {"specific", "chapter_overview", "course_overview"}:
            scope = "specific"
        chapter_id = payload.get("chapter_id")
        try:
            chapter_id = int(chapter_id) if chapter_id is not None else None
        except (TypeError, ValueError):
            chapter_id = None
        try:
            confidence = float(payload.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            confidence = 0
        valid_chapter_ids = {int(item["id"]) for item in chapters if item.get("id") is not None}
        if chapter_id not in valid_chapter_ids:
            chapter_id = None
        if scope == "chapter_overview" and chapter_id is None:
            scope = "specific"
        return {
            "scope": scope,
            "chapter_id": chapter_id,
            "confidence": max(0, min(confidence, 1)),
            "reason": str(payload.get("reason") or ""),
        }

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

    def generate_pedagogy_artifacts(
        self,
        *,
        material_title: str,
        lesson_title: str,
        page_title: str | None,
        page_number: int,
        page_text: str,
        script_text: str | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        clean_page = _clean_text(page_text)
        clean_script = _clean_text(script_text or "")
        try:
            payload = self._call_json(
                db,
                purpose="knowledge",
                system_prompt=(
                    "你是高校课程教学结构提炼助手。你的任务是把老师上传课件中的单页内容提炼为可被 QA、题目辅导、"
                    "出题、复盘和教学分析复用的结构化教学对象。不要生成新 PPT，不要虚构与页面矛盾的知识。"
                    "如果页面有例题或方法，请抽象成可迁移的题型模板：题型、条件、步骤、易错点、可替换变量槽位。"
                    "必须只返回 JSON 对象。"
                ),
                user_prompt=(
                    f"课件标题：{material_title}\n"
                    f"课时标题：{lesson_title}\n"
                    f"页码：第{page_number}页\n"
                    f"页面标题：{page_title or '无'}\n"
                    f"页面正文：{clean_page[:5200]}\n"
                    f"讲解稿参考：{clean_script[:1800]}\n"
                    "返回字段："
                    "{"
                    "\"page_summary\":\"100字内页面摘要\","
                    "\"learning_objectives\":[\"学习目标\"],"
                    "\"key_points\":[\"页面重点\"],"
                    "\"knowledge_points\":[\"知识点\"],"
                    "\"misconceptions\":[{\"title\":\"易错点\",\"description\":\"错误表现\",\"correction\":\"纠正方法\"}],"
                    "\"problem_templates\":[{\"name\":\"题型名称\",\"conditions\":[\"适用条件\"],\"steps\":[\"步骤\"],"
                    "\"mistakes\":[\"易错点\"],\"variable_slots\":[\"可替换变量槽位\"],\"transfer_prompt\":\"迁移到同题型新题的提示\"}],"
                    "\"prerequisites\":[\"前置知识或前置页面关系\"],"
                    "\"quick_checks\":[\"课堂快问\"],"
                    "\"discussion_prompts\":[\"讨论问题\"],"
                    "\"demo_ideas\":[\"演示入口\"]"
                    "}"
                ),
            )
        except Exception:
            payload = None
        if isinstance(payload, dict):
            return payload
        keywords = [item for item in self.extract_keywords(clean_page or page_title or lesson_title, limit=8) if item != "课程内容"]
        if not keywords:
            keywords = [page_title or lesson_title or "当前页面"]
        main = keywords[0]
        summary = clean_page[:220] or f"{page_title or lesson_title} 的页面内容需要结合课堂讲解继续补充。"
        return {
            "page_summary": summary,
            "learning_objectives": [f"理解 {main} 的含义、适用条件和应用步骤"],
            "key_points": keywords[:5],
            "knowledge_points": keywords[:5],
            "misconceptions": [
                {
                    "title": f"{main} 的适用前提",
                    "description": f"容易脱离条件直接套用 {main} 的结论或步骤。",
                    "correction": "先判断对象、条件、目标是否匹配，再选择对应方法。",
                }
            ],
            "problem_templates": [
                {
                    "name": f"{main} 应用题型",
                    "conditions": ["题干给出对象、条件或现象，需要选择相应概念、规则或步骤"],
                    "steps": ["识别考查对象", "整理条件和目标", "选择课程中的概念或方法", "按步骤推理并检查限制条件"],
                    "mistakes": ["只匹配表面文字，没有判断题型结构", "忽略条件变化导致的方法边界"],
                    "variable_slots": ["对象", "条件", "目标", "参数或符号"],
                    "transfer_prompt": f"当题干的对象、数值或符号变化时，先保留 {main} 的方法结构，再替换具体变量。",
                }
            ],
            "prerequisites": keywords[1:4],
            "quick_checks": [f"{main} 的适用条件是什么？", "遇到同题型新题时第一步应该判断什么？"],
            "discussion_prompts": [f"请举一个 {main} 的同结构变式，并说明哪些条件被替换。"],
            "demo_ideas": [f"用一个小例子演示 {main} 从条件识别到结论形成的过程。"],
        }

    def _normalize_history_messages(self, history: Sequence[Any] | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for item in history or []:
            if isinstance(item, dict):
                role = str(item.get("role") or "user")
                content = str(item.get("content") or "").strip()
            else:
                role = "user"
                content = str(item or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            messages.append({"role": role, "content": content[:1200]})
        return messages

    def _rag_answer_messages(self, *, context: str, history: Sequence[Any] | None, question: str) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": f"{RAG_ANSWER_SYSTEM_PROMPT}\n\n课程资料：\n{context}",
            },
            *self._normalize_history_messages(history),
            {
                "role": "user",
                "content": f"学生问题：{question}\n{RAG_ANSWER_USER_INSTRUCTIONS}",
            },
        ]
        return messages

    def _history_hint_items(self, history: Sequence[Any] | None) -> list[str]:
        return [item["content"] for item in self._normalize_history_messages(history) if item["role"] == "user"]

    def _heuristic_retrieval_query(self, *, question: str, history: Sequence[Any] | None = None) -> str:
        normalized = _clean_text(question)
        normalized = re.sub(r"\d+(?:\.\d+)?", "数字", normalized)
        normalized = re.sub(r"\b[A-Za-z]\b", "变量", normalized)
        normalized = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]{2,16}\b", "变量", normalized)
        intent_terms: list[str] = []
        for term in ["定义", "概念", "步骤", "思路", "方法", "原理", "公式", "例题", "题型", "区别", "联系", "作用", "判断", "证明", "推导", "计算", "分析", "规则", "模板"]:
            if term in normalized and term not in intent_terms:
                intent_terms.append(term)
        keywords = [item for item in self.extract_keywords(normalized, limit=8) if item != "课程内容"]
        if any(token in question for token in ["这个", "那个", "这题", "那题", "上一个", "继续"]) and history:
            for item in self._history_hint_items(history)[-2:]:
                for keyword in self.extract_keywords(item, limit=4):
                    if keyword != "课程内容" and keyword not in keywords:
                        keywords.append(keyword)
        parts = [normalized]
        focus = [*intent_terms, *keywords]
        if focus:
            parts.append(f"检索重点：{' '.join(focus[:8])}")
        return "\n".join(part for part in parts if part).strip()[:320]

    def answer_question(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[Any] | None = None,
        db: Session | None = None,
    ) -> tuple[str, bool, str | None]:
        if not contexts:
            return (
                "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。",
                True,
                None,
            )
        context = "\n\n".join(_clean_text(item) for item in contexts if item)
        chat_messages = self._rag_answer_messages(context=context[:12000], history=history, question=question)
        result = self._call_chat_with_meta(
            db,
            purpose="qa",
            system_prompt=chat_messages[0]["content"],
            user_prompt=chat_messages[-1]["content"],
            messages=chat_messages,
        )
        if result:
            return result.content.strip(), False, result.reasoning
        context = context[:320]
        history_hint = ""
        history_items = self._history_hint_items(history)
        if history_items:
            history_hint = f"\n结合前序对话，可继续沿着“{history_items[-1][:30]}”这个方向理解。"
        answer = (
            f"根据当前课程资料，问题“{question}”可以这样理解：\n"
            f"{context}\n"
            "如果你要继续追问，建议从定义、适用条件、典型例题三个角度继续展开。"
            f"{history_hint}"
        )
        return answer, False, "本次使用本地降级逻辑：根据检索到的课程片段生成回答，未收到上游模型思考过程。"

    def answer_general_question(
        self,
        *,
        question: str,
        history: Sequence[Any] | None = None,
        db: Session | None = None,
    ) -> tuple[str, str | None]:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是课程问答助手。当前问题没有检索到课程资料中的直接依据。"
                    "你可以基于通用知识回答，但不要伪造课程资料来源，不要声称课程里明确讲过。"
                    "请直接回答问题本身，使用 Markdown 输出；如果涉及公式，使用 $...$ 或 $$...$$ 包裹 LaTeX。"
                ),
            },
            *self._normalize_history_messages(history),
            {
                "role": "user",
                "content": f"学生问题：{question}\n请给出清晰、谨慎的通用说明。",
            },
        ]
        result = self._call_chat_with_meta(
            db,
            purpose="qa",
            system_prompt=messages[0]["content"],
            user_prompt=messages[-1]["content"],
            messages=messages,
        )
        if result:
            return result.content.strip(), result.reasoning
        history_hint = ""
        history_items = self._history_hint_items(history)
        if history_items:
            history_hint = f"\n可结合前序问题“{history_items[-1][:40]}”继续核对你的理解。"
        answer = (
            f"这是一个需要依赖通用知识来回答的问题：{question}\n"
            "建议先明确题目对象、已知条件、目标，再选择相应概念、公式、方法或题型模板。"
            f"{history_hint}"
        )
        return answer, "本次未检索到课程资料依据，使用通用知识降级回答。"

    def stream_answer_question(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[Any] | None = None,
        db: Session | None = None,
    ) -> Iterator[ChatDelta]:
        if not contexts:
            yield ChatDelta("content", "当前课程资料中没有检索到足以支持回答的内容。请换一种问法，或确认该问题是否属于本课程范围。")
            return
        context = "\n\n".join(_clean_text(item) for item in contexts if item)
        chat_messages = self._rag_answer_messages(context=context[:10000], history=history, question=question)
        emitted = False
        for delta in self._stream_chat_with_meta(
            db,
            purpose="qa",
            system_prompt=chat_messages[0]["content"],
            user_prompt=chat_messages[-1]["content"],
            messages=chat_messages,
        ):
            emitted = True
            yield delta
        if emitted:
            return
        context_excerpt = context[:320]
        history_hint = ""
        history_items = self._history_hint_items(history)
        if history_items:
            history_hint = f"\n结合你前面的问题（{'；'.join(history_items[-2:])}），可以把本题和前序概念一起对照。"
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

    def generate_problem_guidance(
        self,
        *,
        problem_text: str,
        level: int,
        contexts: Sequence[str] | None = None,
        db: Session | None = None,
    ) -> str:
        level_name = {1: "思路提示", 2: "步骤引导", 3: "完整解析"}.get(level, "解析")
        context_block = ""
        if contexts:
            context_block = "\n课程资料参考：\n" + "\n\n".join(_clean_text(item) for item in contexts if item)[:10000]
        result = self._call_chat(
            db,
            purpose="tutoring",
            system_prompt=(
                "你是题目辅导助手。按学生请求的层级给出帮助，低层级不要直接泄露完整答案。"
                "优先结合课程资料参考来组织讲解。"
                "请使用 Markdown 输出；如果涉及公式，使用 $...$ 或 $$...$$ 包裹 LaTeX。"
            ),
            user_prompt=(
                f"题目：{problem_text}\n"
                f"请求层级：{level_name}"
                f"{context_block}\n"
                "输出要求："
                "\n- 层级 1 给解题入口和判断方向，不直接给完整答案；"
                "\n- 层级 2 给分步思路，尽量用有序列表；"
                "\n- 层级 3 给完整解析，步骤清晰，必要时给公式。"
            ),
        )
        if result:
            return result.strip()
        snippet = _clean_text(problem_text)[:180]
        if level == 1:
            return (
                "## 解题入口\n"
                f"- 先判断这道题考查的核心对象与已知条件。\n"
                f"- 再围绕“{snippet}”定位对应知识点和可用方法。\n"
                "- 先不要急着代数，先把题型和目标确认清楚。"
            )
        if level == 2:
            return (
                "## 分步思路\n"
                "1. 整理题目条件，明确已知量、未知量和目标。\n"
                "2. 选择合适的概念、定理、公式或题型模板。\n"
                f"3. 结合题干片段“{snippet}”逐步推导，并检查边界条件、符号和单位。"
            )
        return (
            "## 完整解析\n"
            f"1. 明确题目目标并重述条件：{snippet}\n"
            "2. 选择正确的概念、定理、公式或证明路径。\n"
            "3. 按顺序展开推导，必要时写出中间步骤。\n"
            "4. 给出结论后，回看是否遗漏单位、定义域、符号方向等细节。"
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

    def generate_quiz_questions(
        self,
        *,
        topic: str,
        source_text: str,
        count: int,
        type_counts: dict[str, int] | None = None,
        db: Session | None = None,
    ) -> list[dict]:
        clean_source = sanitize_quiz_source_text(source_text)
        if not clean_source.strip():
            raise bad_request("课程资料或知识点清洗后没有足够文本，无法调用 AI 出题")
        normalized_type_counts = {
            key: int(value)
            for key, value in (type_counts or {}).items()
            if key in _QUIZ_GENERATION_TYPES and int(value or 0) > 0
        }
        if normalized_type_counts and sum(normalized_type_counts.values()) != count:
            raise bad_request("题型数量合计必须等于总题量")
        candidate_count = min(20, max(count + 4, math.ceil(count * 1.8)))
        completion_limit = max(2800, min(6500, 340 * max(candidate_count, 1) + 1900))
        type_instruction = (
            "题型分布必须严格满足："
            + "、".join(f"{key} {value} 道" for key, value in normalized_type_counts.items())
            + "；"
            if normalized_type_counts
            else ""
        )
        style_instruction = _quiz_generation_style_instruction(
            count=count,
            candidate_count=candidate_count,
            source_text=clean_source,
        )
        base_prompt = (
            f"考查主题/知识点：{topic}\n课程资料与知识点：{clean_source}\n"
            f"目标题目数量：{count}\n候选题数量：{candidate_count}\n"
            "要求：围绕课程资料中呈现的知识点出题，不能机械照搬资料原句；"
            "可以结合该知识点的通用学科知识、典型应用场景、例题变式和必要背景补全题目；"
            "不得偏离考查主题/知识点，不得引入与当前课程无关的新知识点；"
            "候选题可以多于目标数量，便于教师从有效题中筛选；"
            f"{type_instruction}"
            f"{style_instruction}"
            "题干必须明确指向资料中的具体概念、定义、公式、案例、事实或对应知识点；"
            "禁止把“章节练习、薄弱点章节练习、错题重练、测验”等练习名称当作考点；"
            "禁止把第几页、图片名、URL、OSS域名、文件hash、文件扩展名当作考点或选项；"
            "单选题和多选题必须有 4 个选项，判断题必须只有“正确/错误”两个选项；"
            "question_type 只能使用 single_choice、multiple_choice、judge、blank、short_answer；"
            "reference_answer 对选择题和判断题必须使用 {\"value\": 0} 这种 0 基选项下标；"
            "多选题 reference_answer 使用 {\"value\":[0,2]} 这种 0 基选项下标数组；"
            "填空题和简答题 reference_answer 必须使用 {\"keywords\":[\"关键词\"]}；"
            "直接事实题（例如问“何时、哪个阶段、是什么、哪一项”）必须生成选择题或判断题，不能生成简答题；"
            "简答题只能用于“简述、说明、解释、分析、比较、作用、关系、步骤”等需要展开回答的题，"
            "reference_answer 必须使用 {\"keywords\":[\"关键词\"]}；"
            "如果课程资料和知识点都不足以确定考查范围，返回 {\"items\":[]}。\n"
            "返回格式：{\"items\":[{\"question_type\":\"single_choice|multiple_choice|judge|blank|short_answer\","
            "\"stem\":\"\",\"options\":[\"\"],\"reference_answer\":{},\"explanation\":\"\",\"score\":10,\"difficulty\":\"standard\"}]}"
        )
        content = self._call_chat(
            db,
            purpose="quiz",
            system_prompt="你是课程测验题生成助手。请只返回一个 JSON 对象，不要输出解释文字，不要使用 Markdown 代码块。",
            user_prompt=base_prompt,
            json_mode=False,
            allow_fallback=False,
            max_tokens=completion_limit,
            timeout_seconds=max(self.settings.external_service_timeout_seconds, 300),
        )
        if content is None:
            raise bad_request("AI 出题失败：模型未返回题目内容")
        try:
            payload = _parse_json_payload(content)
        except Exception as exc:
            raise bad_request("AI 出题失败：模型未返回合法 JSON 题目") from exc
        seen_stems: set[str] = set()
        normalized = _normalize_quiz_questions_from_payload(
            payload,
            count=candidate_count,
            seen_stems=seen_stems,
        )
        normalized = _prioritize_quiz_question_mix(normalized)
        if normalized_type_counts:
            selected, missing_by_type = _select_quiz_questions_by_type_counts(normalized, normalized_type_counts)
            if not missing_by_type:
                return selected[:count]
        elif len(normalized) >= count:
            return normalized[:count]

        missing = sum(missing_by_type.values()) if normalized_type_counts else count - len(normalized)
        retry_count = min(20, max(missing + 4, math.ceil(missing * 2.4)))
        retry_content = self._call_chat(
            db,
            purpose="quiz",
            system_prompt="你是课程测验题生成助手。请只返回一个 JSON 对象，不要输出解释文字，不要使用 Markdown 代码块。",
            user_prompt=(
                f"考查主题/知识点：{topic}\n课程资料与知识点：{clean_source}\n"
                f"已有有效题干：{[item['stem'] for item in normalized]}\n"
                f"还缺少 {missing} 道有效题，请再生成 {retry_count} 道不同候选题。\n"
                f"{'缺少题型：' + '、'.join(f'{key} {value} 道' for key, value in missing_by_type.items()) + '。' if normalized_type_counts else ''}"
                "要求同前：围绕课程资料中的知识点出题，可结合通用学科知识生成应用和变式题；"
                "不得偏离考查主题/知识点；题干避开已有题干；"
                f"{style_instruction}"
                "question_type 只能使用 single_choice、multiple_choice、judge、blank、short_answer；"
                "单选/多选 4 个选项，判断题使用正确/错误，reference_answer 使用 0 基下标、下标数组或 keywords。"
                "返回格式：{\"items\":[{\"question_type\":\"single_choice|multiple_choice|judge|blank|short_answer\","
                "\"stem\":\"\",\"options\":[\"\"],\"reference_answer\":{},\"explanation\":\"\",\"score\":10,\"difficulty\":\"standard\"}]}"
            ),
            json_mode=False,
            allow_fallback=False,
            max_tokens=max(2400, min(5200, 340 * retry_count + 1600)),
            timeout_seconds=max(self.settings.external_service_timeout_seconds, 300),
        )
        if retry_content:
            try:
                retry_payload = _parse_json_payload(retry_content)
            except Exception as exc:
                raise bad_request("AI 出题失败：模型未返回合法 JSON 题目") from exc
            normalized.extend(
                _normalize_quiz_questions_from_payload(
                    retry_payload,
                    count=retry_count,
                    seen_stems=seen_stems,
                )
            )
            normalized = _prioritize_quiz_question_mix(normalized)
            if normalized_type_counts:
                selected, missing_by_type = _select_quiz_questions_by_type_counts(normalized, normalized_type_counts)
                if not missing_by_type:
                    return selected[:count]
            elif len(normalized) >= count:
                return normalized[:count]
        if normalized_type_counts and missing_by_type:
            detail = "、".join(f"{key} 缺 {value} 道" for key, value in missing_by_type.items())
            raise bad_request(f"AI 出题失败：模型返回的有效题型不足（{detail}），请重新生成")
        raise bad_request(f"AI 出题失败：模型返回的有效题目不足 {count} 道，请重新生成")

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
