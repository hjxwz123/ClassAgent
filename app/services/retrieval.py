from __future__ import annotations

import re

from app.services.ai import ai_service


_DEFAULT_QUERY_STOPWORDS = {
    "前序对话",
    "当前问题",
    "学生上传",
    "ocr识别内容",
    "这个",
    "那个",
    "什么",
    "请问",
    "帮我",
    "一下",
    "关于",
    "内容",
    "解释",
    "例子",
    "回答",
    "怎么",
    "如何",
    "为什么",
}
_MATH_EXPRESSION_PATTERN = re.compile(
    r"(?<![\w.])\(?-?\d+(?:\.\d+)?\)?(?:\s*[+\-*/xX×÷]\s*\(?-?\d+(?:\.\d+)?\)?){1,5}(?![\w.])"
)
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def focused_query_text(query: str) -> str:
    text = " ".join(str(query or "").split()).strip()
    if not text:
        return ""
    marker = "当前问题："
    if marker in text:
        tail = text.rsplit(marker, 1)[-1].strip()
        if tail:
            return tail
    return text


def page_numbers_from_query(query: str) -> set[int]:
    text = focused_query_text(query)
    numbers: set[int] = set()
    for pattern in (r"第\s*(\d{1,4})\s*页", r"(?<!\d)(\d{1,4})\s*页", r"\bp\s*(\d{1,4})\b"):
        for value in re.findall(pattern, text, flags=re.IGNORECASE):
            number = int(value)
            if number > 0:
                numbers.add(number)
    return numbers


def normalize_math_text(text: str) -> str:
    return _MATH_EXPRESSION_PATTERN.sub(lambda match: _canonical_math_expression(match.group()), str(text or ""))


def abstract_numbers_text(text: str) -> str:
    return _MATH_EXPRESSION_PATTERN.sub(lambda match: _placeholder_math_expression(match.group()), str(text or ""))


def extract_math_signatures(text: str) -> list[str]:
    signatures: list[str] = []
    for match in _MATH_EXPRESSION_PATTERN.finditer(str(text or "")):
        signature = _canonical_math_expression(match.group())
        if signature and signature not in signatures:
            signatures.append(signature)
    return signatures


def extract_math_placeholders(text: str) -> list[str]:
    placeholders: list[str] = []
    for match in _MATH_EXPRESSION_PATTERN.finditer(str(text or "")):
        placeholder = _placeholder_math_expression(match.group())
        if placeholder and placeholder not in placeholders:
            placeholders.append(placeholder)
    return placeholders


def build_retrieval_query_variants(query: str, *, limit: int = 6) -> list[str]:
    original = " ".join(str(query or "").split()).strip()
    base = focused_query_text(query)
    variants: list[str] = []

    def add(value: str) -> None:
        clean = " ".join(str(value or "").split()).strip()
        if clean and clean not in variants:
            variants.append(clean)

    add(original)
    if base != original:
        add(base)

    normalized = normalize_math_text(base)
    if normalized != base:
        add(normalized)

    abstracted = abstract_numbers_text(base)
    if abstracted != base:
        add(abstracted)

    return variants[:limit]


def query_terms(query: str, *, stopwords: set[str] | None = None, limit: int = 16) -> list[str]:
    text = focused_query_text(query)
    if not text:
        return []
    blocked = set(_DEFAULT_QUERY_STOPWORDS)
    blocked.update(stopwords or set())

    terms: list[str] = []
    normalized = normalize_math_text(text)
    candidates = [
        *ai_service.extract_keywords(text, limit=12),
        *ai_service.extract_keywords(normalized, limit=8),
        *re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", text),
        *re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", normalized),
        *re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", abstract_numbers_text(text)),
    ]
    for phrase in re.findall(r"[\u4e00-\u9fff]{3,16}", text):
        for size in (4, 3, 2):
            candidates.extend(phrase[index : index + size] for index in range(max(len(phrase) - size + 1, 0)))
    for signature in extract_math_signatures(text):
        candidates.append(signature)
    candidates.extend(extract_math_placeholders(text))

    for item in candidates:
        term = str(item).strip().lower()
        if not term or term.isdigit() or len(term) < 2 or term in blocked:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:limit]


def score_text_for_query(
    *,
    title: str,
    text: str,
    page_number: int | None,
    query: str,
    stopwords: set[str] | None = None,
    term_limit: int = 16,
) -> int:
    page_numbers = page_numbers_from_query(query)
    terms = query_terms(query, stopwords=stopwords, limit=term_limit)
    raw_haystack = f"{title}\n{text}".lower()
    normalized_haystack = normalize_math_text(raw_haystack)
    placeholder_haystack = abstract_numbers_text(raw_haystack).lower()
    query_signatures = extract_math_signatures(query)
    query_placeholders = extract_math_placeholders(query)
    text_signatures = set(extract_math_signatures(raw_haystack))
    text_placeholders = set(extract_math_placeholders(raw_haystack))

    score = 0
    if page_number is not None and page_number in page_numbers:
        score += 100
    for term in terms:
        if term in raw_haystack:
            score += 5 + min(len(term), 12)
        elif term in normalized_haystack:
            score += 8 + min(len(term), 12)
        elif term in placeholder_haystack:
            score += 8 + min(len(term), 12)
    for signature in query_signatures:
        if signature in text_signatures:
            score += 36
    for placeholder in query_placeholders:
        if placeholder in text_placeholders:
            score += 24
    return score


def _canonical_math_expression(expression: str) -> str:
    compact = re.sub(r"\s+", "", str(expression or ""))
    if not compact:
        return ""
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", compact):
        return ""
    compact = compact.replace("x", "*").replace("X", "*").replace("×", "*").replace("÷", "/")
    if len(_NUMBER_PATTERN.findall(compact)) < 2:
        return ""
    return _NUMBER_PATTERN.sub("N", compact).lower()


def _placeholder_math_expression(expression: str) -> str:
    compact = re.sub(r"\s+", "", str(expression or ""))
    if not compact:
        return ""
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", compact):
        return ""
    compact = compact.replace("x", "*").replace("X", "*").replace("×", "*").replace("÷", "/")
    if len(_NUMBER_PATTERN.findall(compact)) < 2:
        return ""
    return _NUMBER_PATTERN.sub("数字", compact).lower()
