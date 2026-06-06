from collections.abc import Iterator
from dataclasses import dataclass
import html
from pathlib import Path
import re
from time import sleep
from typing import Any

from fastapi import UploadFile
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import MaterialType, QAFeedback, QuestionType, UserRole
from app.core.errors import bad_request, forbidden, not_found
from app.db.models import Chapter, Course, CourseMaterial, CourseMembership, KnowledgeChunk, Lesson, LessonPage, QAConversation, QARecord, User
from app.schemas.qa import QAAskRequest
from app.services.ai import ai_service
from app.services.knowledge import search_course_knowledge
from app.services.learning_signals import record_qa_learning_signals
from app.services.parser import _extract_text_payload
from app.services.ocr import ocr_service
from app.services.pedagogy import QA_ARTIFACT_TYPES, artifact_contexts, artifact_sources, search_pedagogy_artifacts
from app.services.retrieval import page_numbers_from_query, query_terms, score_text_for_query
from app.services.storage import storage_service
from app.services.usage import log_ai_usage


_THINK_START_TAGS = ("<think>", "<thinking>")
_THINK_END_TAGS = ("</think>", "</thinking>")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_QA_IMAGE_LIMIT_BYTES = 10 * 1024 * 1024
_STREAM_CHUNK_SIZE = 36
_STREAM_CHUNK_DELAY_SECONDS = 0.015
_QA_HISTORY_MESSAGE_LIMIT = 900
_QA_FALLBACK_PAGE_SCAN_LIMIT = 240
_QA_VECTOR_CONTEXT_LIMIT = 8
_QA_DETAIL_VECTOR_CONTEXT_LIMIT = 10
_QA_RELATED_PAGE_CONTEXT_LIMIT = 6
_QA_CHAPTER_RANGE_MAX = 8
_CHAPTER_NUM_TOKEN = r"\d{1,3}|[零〇一二两三四五六七八九十百]{1,8}"
_PAGE_NUM_TOKEN = r"\d{1,4}|[零〇一二两三四五六七八九十百]{1,8}"
_CHAPTER_RANGE_PATTERN = re.compile(
    rf"(?:第\s*)?(?P<start>{_CHAPTER_NUM_TOKEN})\s*(?:章\s*)?(?:[-~—–至到])\s*(?:第\s*)?(?P<end>{_CHAPTER_NUM_TOKEN})\s*章"
)
_CHAPTER_SINGLE_PATTERN = re.compile(rf"(?:第\s*)?(?P<num>{_CHAPTER_NUM_TOKEN})\s*章")
_CHAPTER_LIST_PATTERN = re.compile(
    rf"(?P<body>(?:第\s*)?(?:{_CHAPTER_NUM_TOKEN})\s*(?:章)?(?:\s*(?:[、,，/]|和|与|及)\s*(?:第\s*)?(?:{_CHAPTER_NUM_TOKEN})\s*(?:章)?)+)"
)
_SLIDE_PAGE_PATTERN = re.compile(
    rf"(?:第\s*)?(?P<num>{_PAGE_NUM_TOKEN})\s*(?:页|頁|张|張|张幻灯片|張幻燈片|页ppt|页PPT|slide|Slide|幻灯片|幻燈片)"
)
_SECTION_PATTERN = re.compile(r"(?<!\d)(?P<chapter>\d{1,2})\s*[.．]\s*(?P<section>\d{1,2})(?!\d)")
_SPECIFIC_PAGE_HINT_PATTERN = re.compile(r"(第\s*\d+\s*(?:页|張|张|幻灯片|slide)|这页|这一页|当前页|本页|这张|这一张)")
_QUIZ_REQUEST_PATTERN = re.compile(r"(出|生成|来|做).{0,8}(题|练习|测验|测试|选择题|判断题|简答题)|考考我|刷题|练几道")
_LARGE_REQUEST_PATTERN = re.compile(
    r"(全部内容|所有内容|完整内容|从头到尾|逐页|一页一页|一张一张|每一页|每张|每页|"
    r"完整讲(?:一遍|完|一下)?|详细讲(?:完整|完|一遍)?|系统讲(?:一遍|完)|整体学一遍)"
)
_CHAPTER_WIDE_CONTENT_PATTERN = re.compile(
    r"(第\s*.+章|本章|这一章|当前章).{0,12}(全部|所有|完整).{0,8}(内容|知识点|课件|ppt|PPT|幻灯片|页面)"
)
_CHAPTER_SUMMARY_PATTERN = re.compile(r"(第\s*.+章|章节|本章|这一章|当前章).{0,12}(讲了什么|总结|概括|梳理|重点|框架|提纲|复习)")
_COURSE_SUMMARY_PATTERN = re.compile(r"(这门课|本课程|整门课|全部课程|课程整体).{0,12}(讲了什么|总结|概括|梳理|重点|框架|提纲|复习)")
_TABLE_QUESTION_PATTERN = re.compile(r"(表格|表中|表里|表内|对比表|列表|表\s*\d*)")
_FIGURE_QUESTION_PATTERN = re.compile(r"(图片|图表|图中|图里|这张图|这幅图|流程图|示意图|结构图|曲线图|柱状图|折线图)")
_COMPARE_QUESTION_PATTERN = re.compile(r"(区别|不同|对比|比较|异同|联系|差异|VS|vs)")
_PRINCIPLE_QUESTION_PATTERN = re.compile(r"(为什么|原理|机制|流程|步骤|如何|怎么实现|怎样实现|推导|证明)")
_CONCEPT_QUESTION_PATTERN = re.compile(r"(什么是|是什么|定义|概念|是什么意思|是啥)")
_NOTE_REQUEST_PATTERN = re.compile(r"(整理|生成|帮我).{0,8}(笔记|复习资料|知识清单|知识点清单)")
_HTML_TABLE_PATTERN = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)
_HTML_ROW_PATTERN = re.compile(r"<tr[\s\S]*?</tr>", re.IGNORECASE)
_HTML_CELL_PATTERN = re.compile(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_QUIZ_COUNT_PATTERN = re.compile(r"(?P<count>\d{1,2}|[一二两三四五六七八九十])\s*道")
_QUIZ_TYPE_COUNT_PATTERN = re.compile(
    r"(?P<count>\d{1,2}|[一二两三四五六七八九十])\s*道\s*(?P<label>单选题|多选题|选择题|判断题|填空题|简答题|问答题)"
)
_QUIZ_SHOW_ANSWER_PATTERN = re.compile(r"(显示|给出|附上|带上|包含|要).{0,6}(答案|解析)|答案和解析|带答案|附答案")
_QUIZ_TYPE_LABELS = {
    QuestionType.SINGLE_CHOICE.value: "选择题",
    QuestionType.MULTIPLE_CHOICE.value: "多选题",
    QuestionType.JUDGE.value: "判断题",
    QuestionType.BLANK.value: "填空题",
    QuestionType.SHORT_ANSWER.value: "简答题",
}
_QUIZ_LABEL_TO_TYPE = {
    "单选题": QuestionType.SINGLE_CHOICE.value,
    "选择题": QuestionType.SINGLE_CHOICE.value,
    "多选题": QuestionType.MULTIPLE_CHOICE.value,
    "判断题": QuestionType.JUDGE.value,
    "填空题": QuestionType.BLANK.value,
    "简答题": QuestionType.SHORT_ANSWER.value,
    "问答题": QuestionType.SHORT_ANSWER.value,
}
_QA_QUERY_STOPWORDS = {
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
_GENERAL_AI_NOTICE = "提示：以下回答未在当前课程资料中检索到直接依据，属于通用知识说明，请结合老师要求和课程内容自行核对。"
_GENERAL_AI_DISABLED_NOTICE = "当前课程资料中没有检索到可直接支撑该问题的内容，且本课程未开启“资料外也可回答”。请换一种问法，或联系老师开启该开关。"


@dataclass
class ClassroomAgentPlan:
    question_type: str
    scope: str
    keywords: list[str]
    search_phrases: list[str]
    expanded_terms: list[str]
    chapter_ids: list[int]
    chapter_id: int | None
    page_numbers: list[int]
    section_numbers: list[str]
    tools: list[str]
    retrieval_query: str
    large_request: bool = False


@dataclass
class ExtractedTable:
    columns: list[str]
    rows: list[list[str]]
    raw: str
    source_format: str


def _assert_student_course_access(db: Session, *, course_id: int, user: User) -> None:
    if user.role != UserRole.STUDENT.value:
        raise forbidden("仅学生可使用该功能")
    membership = db.scalar(
        select(CourseMembership.id).where(CourseMembership.course_id == course_id, CourseMembership.user_id == user.id)
    )
    if membership is None:
        raise forbidden("仅可在已加入课程内提问")


def _course_allows_general_ai_answer(db: Session, *, course_id: int) -> bool:
    course = db.get(Course, course_id)
    return bool(course and getattr(course, "allow_general_ai_answer", False))


def _get_or_create_course_conversation(db: Session, *, user: User, payload: QAAskRequest) -> QAConversation:
    conversation = None
    if payload.conversation_id:
        conversation = db.scalar(
            select(QAConversation).where(
                QAConversation.id == payload.conversation_id,
                QAConversation.user_id == user.id,
                QAConversation.course_id == payload.course_id,
            )
        )
    if conversation is None:
        conversation = QAConversation(course_id=payload.course_id, user_id=user.id, title=payload.question[:30])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation


def _find_tag(buffer: str, tags: tuple[str, ...]) -> tuple[int, str] | None:
    lower = buffer.lower()
    matches = [(index, tag) for tag in tags if (index := lower.find(tag)) >= 0]
    return min(matches, key=lambda item: item[0]) if matches else None


def _safe_text_length(buffer: str, tags: tuple[str, ...]) -> int:
    lower = buffer.lower()
    hold = 0
    for size in range(1, min(len(lower), max(len(tag) for tag in tags) - 1) + 1):
        suffix = lower[-size:]
        if any(tag.startswith(suffix) for tag in tags):
            hold = size
    return len(buffer) - hold


def _split_thinking_tags(state: dict[str, object], chunk: str) -> list[tuple[str, str]]:
    state["buffer"] = str(state.get("buffer") or "") + chunk
    parts: list[tuple[str, str]] = []
    while state["buffer"]:
        buffer = str(state["buffer"])
        in_think = bool(state.get("in_think"))
        tags = _THINK_END_TAGS if in_think else _THINK_START_TAGS
        match = _find_tag(buffer, tags)
        kind = "thought" if in_think else "answer"
        if match:
            index, tag = match
            text = buffer[:index]
            if text:
                parts.append((kind, text))
            state["buffer"] = buffer[index + len(tag) :]
            state["in_think"] = not in_think
            continue
        safe_len = _safe_text_length(buffer, tags)
        if safe_len <= 0:
            break
        parts.append((kind, buffer[:safe_len]))
        state["buffer"] = buffer[safe_len:]
        break
    return parts


def _flush_thinking_tags(state: dict[str, object]) -> list[tuple[str, str]]:
    buffer = str(state.get("buffer") or "")
    if not buffer:
        return []
    state["buffer"] = ""
    return [("thought" if bool(state.get("in_think")) else "answer", buffer)]


def _text_chunks(text: str, *, size: int = _STREAM_CHUNK_SIZE) -> list[str]:
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    buffer = ""
    break_chars = set("，。！？；、,.!?; \n")
    for char in text:
        buffer += char
        if len(buffer) >= size and (char in break_chars or len(buffer) >= size * 2):
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def _stream_text_delta(kind: str, text: str, answer_parts: list[str], thought_parts: list[str]) -> Iterator[dict]:
    chunks = _text_chunks(text)
    target = thought_parts if kind == "thought" else answer_parts
    for chunk in chunks:
        target.append(chunk)
        yield {"event": "delta", "data": {"type": kind, "text": chunk}}
        if len(chunks) > 1:
            sleep(_STREAM_CHUNK_DELAY_SECONDS)


def _attachment_dicts(payload: QAAskRequest) -> list[dict]:
    return [attachment.model_dump(mode="json", exclude_none=True) for attachment in payload.attachments]


def _question_with_attachments(question: str, attachments: list[dict]) -> str:
    if not attachments:
        return question
    lines = [question.strip()]
    for index, attachment in enumerate(attachments, start=1):
        filename = attachment.get("filename") or f"图片{index}"
        ocr_text = str(attachment.get("ocr_text") or "").strip()
        if ocr_text:
            lines.append(f"学生上传图片{index}（{filename}）OCR识别内容：{ocr_text}")
        else:
            lines.append(f"学生上传图片{index}（{filename}），未识别到可用文字。")
    return "\n\n".join(lines)


def _lesson_page_context(db: Session, *, course_id: int, lesson_page_id: int | None) -> tuple[list[str], list[dict]]:
    if lesson_page_id is None:
        return [], []
    row = db.execute(
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(LessonPage.id == lesson_page_id, Lesson.course_id == course_id)
    ).first()
    if row is None:
        return [], []
    page, lesson, material = row
    page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
    script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
    parts = [
        f"当前课时：{lesson.title}",
        f"资料类型：{_material_kind_label(material)}",
        f"当前页：第{page.page_number}页 {page.page_title or ''}".strip(),
    ]
    if material is not None:
        parts.insert(1, f"资料文件：{material.title}")
    if page_text:
        parts.append(f"页面内容：\n{page_text}")
    if script_text and script_text != page_text:
        parts.append(f"讲解文稿：\n{script_text}")
    source = _page_source(page, lesson, material)
    return ["\n\n".join(parts)], [source]


def _trim_context(value: str, limit: int = 1200) -> str:
    clean = str(value or "").strip()
    return clean[:limit]


def _compact_excerpt(value: str, *, limit: int = 120) -> str:
    clean = " ".join(str(value or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def _page_excerpt(page: LessonPage, *, limit: int = 140) -> str:
    page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
    script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
    return _compact_excerpt(" ".join(part for part in [page.page_title or "", page_text, script_text if script_text != page_text else ""] if part), limit=limit)


def _material_read_tool(material: CourseMaterial | None) -> str:
    material_type = str(getattr(material, "material_type", "") or "").lower()
    filename = str(getattr(material, "original_filename", "") or "").lower()
    if material_type == MaterialType.PPTX.value or filename.endswith((".ppt", ".pptx")):
        return "read_slide"
    if material_type == MaterialType.PDF.value or filename.endswith(".pdf"):
        return "read_page"
    return "read_page"


def _material_kind_label(material: CourseMaterial | None) -> str:
    tool = _material_read_tool(material)
    if tool == "read_slide":
        return "PPT 幻灯片"
    if str(getattr(material, "material_type", "") or "").lower() == MaterialType.PDF.value:
        return "PDF 页面"
    return "课件页面"


def _clean_table_cell(value: str) -> str:
    text = _HTML_TAG_PATTERN.sub("", html.unescape(str(value or "")))
    return " ".join(text.replace("\\|", "|").split())


def _split_markdown_table_row(line: str) -> list[str]:
    clean = str(line or "").strip()
    if not clean or "|" not in clean:
        return []
    if clean.startswith("|"):
        clean = clean[1:]
    if clean.endswith("|"):
        clean = clean[:-1]
    cells = [_clean_table_cell(cell.strip()) for cell in clean.split("|")]
    return cells if len(cells) >= 2 else []


def _is_markdown_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", str(cell or "").strip()) for cell in cells)


def _normalize_table(columns: list[str], rows: list[list[str]], *, raw: str, source_format: str) -> ExtractedTable | None:
    clean_columns = [_clean_table_cell(column) or f"列{index}" for index, column in enumerate(columns, start=1)]
    width = len(clean_columns)
    clean_rows: list[list[str]] = []
    for row in rows:
        cells = [_clean_table_cell(cell) for cell in row]
        if len(cells) < width:
            cells.extend("" for _ in range(width - len(cells)))
        if len(cells) > width:
            cells = cells[:width]
        if any(cells):
            clean_rows.append(cells)
    if width < 2 or not clean_rows:
        return None
    return ExtractedTable(columns=clean_columns, rows=clean_rows[:12], raw=_trim_context(raw, limit=1600), source_format=source_format)


def _extract_markdown_tables(text: str) -> list[ExtractedTable]:
    lines = str(text or "").splitlines()
    tables: list[ExtractedTable] = []
    index = 0
    while index < len(lines):
        first = _split_markdown_table_row(lines[index])
        second = _split_markdown_table_row(lines[index + 1]) if index + 1 < len(lines) else []
        if first and second and _is_markdown_separator_row(second):
            raw_lines = [lines[index], lines[index + 1]]
            rows: list[list[str]] = []
            index += 2
            while index < len(lines):
                cells = _split_markdown_table_row(lines[index])
                if not cells:
                    break
                rows.append(cells)
                raw_lines.append(lines[index])
                index += 1
            table = _normalize_table(first, rows, raw="\n".join(raw_lines), source_format="markdown")
            if table:
                tables.append(table)
            continue
        index += 1
    return tables


def _extract_html_tables(text: str) -> list[ExtractedTable]:
    tables: list[ExtractedTable] = []
    for match in _HTML_TABLE_PATTERN.finditer(str(text or "")):
        rows = []
        for row_match in _HTML_ROW_PATTERN.finditer(match.group()):
            cells = [_clean_table_cell(cell) for cell in _HTML_CELL_PATTERN.findall(row_match.group())]
            if cells:
                rows.append(cells)
        if len(rows) < 2:
            continue
        table = _normalize_table(rows[0], rows[1:], raw=match.group(), source_format="html")
        if table:
            tables.append(table)
    return tables


def _extract_tsv_tables(text: str) -> list[ExtractedTable]:
    tables: list[ExtractedTable] = []
    block: list[str] = []

    def flush() -> None:
        nonlocal block
        if len(block) < 2:
            block = []
            return
        rows = [[_clean_table_cell(cell) for cell in line.split("\t")] for line in block]
        width = len(rows[0])
        if width >= 2 and all(len(row) == width for row in rows[: min(len(rows), 5)]):
            table = _normalize_table(rows[0], rows[1:], raw="\n".join(block), source_format="tsv")
            if table:
                tables.append(table)
        block = []

    for line in str(text or "").splitlines():
        if "\t" in line and len([cell for cell in line.split("\t") if cell.strip()]) >= 2:
            block.append(line)
        else:
            flush()
    flush()
    return tables


def _extract_tables_from_text(text: str, *, limit: int = 4) -> list[ExtractedTable]:
    tables: list[ExtractedTable] = []
    for table in [*_extract_html_tables(text), *_extract_markdown_tables(text), *_extract_tsv_tables(text)]:
        identity = (tuple(table.columns), tuple(tuple(row) for row in table.rows))
        if any(identity == (tuple(item.columns), tuple(tuple(row) for row in item.rows)) for item in tables):
            continue
        tables.append(table)
        if len(tables) >= limit:
            break
    return tables


def _format_table_for_context(table: ExtractedTable, *, index: int) -> str:
    lines = [
        f"表格{index}（{table.source_format}）：",
        "列：" + " | ".join(table.columns),
    ]
    for row_index, row in enumerate(table.rows, start=1):
        pairs = [f"{column}={value}" for column, value in zip(table.columns, row, strict=False) if value]
        lines.append(f"- 第{row_index}行：" + "；".join(pairs))
    if table.raw:
        lines.append(f"原表片段：{_compact_excerpt(table.raw, limit=260)}")
    return "\n".join(lines)


def _quiz_count_from_question(question: str) -> int:
    text = str(question or "")
    typed_total = 0
    for match in _QUIZ_TYPE_COUNT_PATTERN.finditer(text):
        count = _chapter_number_token(match.group("count"))
        if count:
            typed_total += int(count)
    if typed_total:
        return max(1, min(typed_total, 10))
    match = _QUIZ_COUNT_PATTERN.search(text)
    if not match:
        return 5
    count = _chapter_number_token(match.group("count"))
    return max(1, min(int(count or 5), 10))


def _quiz_type_counts_from_question(question: str, *, total_count: int) -> dict[str, int] | None:
    text = str(question or "")
    counts: dict[str, int] = {}
    for match in _QUIZ_TYPE_COUNT_PATTERN.finditer(text):
        question_type = _QUIZ_LABEL_TO_TYPE.get(match.group("label"))
        count = _chapter_number_token(match.group("count"))
        if question_type and count:
            counts[question_type] = counts.get(question_type, 0) + int(count)
    if counts:
        return counts if sum(counts.values()) == total_count else None
    for label, question_type in _QUIZ_LABEL_TO_TYPE.items():
        if label in text:
            return {question_type: total_count}
    return None


def _quiz_show_answers(question: str) -> bool:
    return bool(_QUIZ_SHOW_ANSWER_PATTERN.search(str(question or "")))


def _format_reference_answer(item: dict) -> str:
    reference = item.get("reference_answer")
    options = item.get("options") if isinstance(item.get("options"), list) else []
    if isinstance(reference, dict):
        value = reference.get("value")
        if isinstance(value, list):
            answers = [options[index] if isinstance(index, int) and 0 <= index < len(options) else str(index) for index in value]
            return "、".join(str(answer) for answer in answers)
        if isinstance(value, int):
            return str(options[value]) if 0 <= value < len(options) else str(value)
        keywords = reference.get("keywords")
        if isinstance(keywords, list):
            return "、".join(str(item) for item in keywords)
    return str(reference or "").strip()


def _format_generated_quiz(questions: list[dict], *, show_answers: bool) -> str:
    lines = ["工具 generate_quiz 结果："]
    for index, item in enumerate(questions, start=1):
        question_type = str(item.get("question_type") or "")
        label = _QUIZ_TYPE_LABELS.get(question_type, question_type or "题目")
        lines.append(f"{index}. 【{label}】{item.get('stem') or ''}")
        options = item.get("options")
        if isinstance(options, list) and options:
            for option_index, option in enumerate(options):
                marker = chr(ord("A") + option_index)
                lines.append(f"   {marker}. {option}")
        if show_answers:
            answer = _format_reference_answer(item)
            if answer:
                lines.append(f"   答案：{answer}")
            explanation = str(item.get("explanation") or "").strip()
            if explanation:
                lines.append(f"   解析：{explanation}")
    if not show_answers:
        lines.append("答案策略：学生未要求答案，本次只展示题目；如果学生继续要求，再显示答案和解析。")
    return "\n".join(lines)


def _generate_quiz_context(
    db: Session,
    *,
    plan: ClassroomAgentPlan,
    question: str,
    source_contexts: list[str],
    chunks: list[KnowledgeChunk],
) -> str:
    source_pieces = [str(item).strip() for item in source_contexts if str(item or "").strip()]
    source_pieces.extend(_chunk_context(chunk) for chunk in chunks if _chunk_context(chunk))
    source_text = "\n\n".join(dict.fromkeys(source_pieces))[:18000]
    if not source_text.strip():
        return "工具 generate_quiz 结果：当前课件中没有找到足够内容生成练习题。"
    count = _quiz_count_from_question(question)
    type_counts = _quiz_type_counts_from_question(question, total_count=count)
    show_answers = _quiz_show_answers(question)
    topic = "、".join(plan.keywords[:4]) or "课程知识点"
    try:
        kwargs: dict[str, Any] = {
            "topic": topic,
            "source_text": source_text,
            "count": count,
            "db": db,
        }
        if type_counts:
            kwargs["type_counts"] = type_counts
        questions = ai_service.generate_quiz_questions(**kwargs)
    except Exception as exc:
        return f"工具 generate_quiz 结果：出题工具暂时失败，错误信息：{_compact_excerpt(str(exc), limit=160)}。"
    return _format_generated_quiz(questions, show_answers=show_answers)


def _qa_history_limit() -> int:
    return max(1, min(int(get_settings().qa_context_turn_limit or 6), 12))


def _conversation_history(db: Session, *, conversation_id: int) -> list[QARecord]:
    rows = list(
        db.scalars(
            select(QARecord)
            .where(QARecord.conversation_id == conversation_id)
            .order_by(QARecord.created_at.desc(), QARecord.id.desc())
            .limit(_qa_history_limit())
        )
    )
    return list(reversed(rows))


def _strip_agent_answer_suffix(answer: str) -> str:
    text = str(answer or "").strip()
    if not text:
        return ""
    markers = ("\n\n来源：", "\n来源：", "\n\n你还可以继续问：", "\n你还可以继续问：")
    cut_points = [index for marker in markers if (index := text.find(marker)) >= 0]
    if cut_points:
        text = text[: min(cut_points)].strip()
    return text


def _history_messages(records: list[QARecord]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for record in records:
        question = _trim_context(record.question, limit=500)
        answer = _trim_context(_strip_agent_answer_suffix(record.answer), limit=_QA_HISTORY_MESSAGE_LIMIT)
        if question:
            messages.append({"role": "user", "content": question})
        if answer:
            messages.append({"role": "assistant", "content": answer})
    return messages


def _question_with_history_for_retrieval(question: str, history: list[dict[str, str]]) -> str:
    if not history:
        return question
    lines = ["前序对话："]
    for item in history[-4:]:
        speaker = "学生" if item["role"] == "user" else "AI"
        lines.append(f"{speaker}：{item['content']}")
    lines.append(f"当前问题：{question}")
    return "\n\n".join(lines)[:3000]


def _page_numbers_from_query(query: str) -> set[int]:
    return page_numbers_from_query(query)


def _query_terms(query: str) -> list[str]:
    return query_terms(query, stopwords=_QA_QUERY_STOPWORDS, limit=14)


def _score_text_for_query(*, title: str, text: str, page_number: int | None, query: str) -> int:
    return score_text_for_query(
        title=title,
        text=text,
        page_number=page_number,
        query=query,
        stopwords=_QA_QUERY_STOPWORDS,
        term_limit=14,
    )


def _chapter_number_token(value: str) -> int | None:
    token = str(value or "").strip().replace("两", "二").replace("〇", "零")
    if not token:
        return None
    if token.isdigit():
        number = int(token)
        return number if number > 0 else None
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if token in digits and digits[token] > 0:
        return digits[token]
    if "百" in token:
        left, _, right = token.partition("百")
        hundred = digits.get(left, 1 if not left else 0)
        tail = _chapter_number_token(right) if right else 0
        number = hundred * 100 + int(tail or 0)
        return number if number > 0 else None
    if "十" in token:
        left, _, right = token.partition("十")
        ten = digits.get(left, 1 if not left else 0)
        one = digits.get(right, 0) if right else 0
        number = ten * 10 + one
        return number if number > 0 else None
    return None


def _chapter_display_number(chapter: Chapter) -> int | None:
    for match in _CHAPTER_SINGLE_PATTERN.finditer(chapter.title or ""):
        number = _chapter_number_token(match.group("num"))
        if number is not None:
            return number
    try:
        order_index = int(chapter.order_index or 0)
    except (TypeError, ValueError):
        order_index = 0
    return order_index if order_index > 0 else None


def _chapters_from_query(query: str, chapters: list[Chapter]) -> list[Chapter]:
    if not query or not chapters:
        return []
    by_number: dict[int, list[Chapter]] = {}
    for chapter in chapters:
        number = _chapter_display_number(chapter)
        if number is not None:
            by_number.setdefault(number, []).append(chapter)

    selected_ids: set[int] = set()
    for match in _CHAPTER_RANGE_PATTERN.finditer(query):
        start = _chapter_number_token(match.group("start"))
        end = _chapter_number_token(match.group("end"))
        if start is None or end is None:
            continue
        if start > end:
            start, end = end, start
        if end - start + 1 > _QA_CHAPTER_RANGE_MAX:
            end = start + _QA_CHAPTER_RANGE_MAX - 1
        for number in range(start, end + 1):
            selected_ids.update(chapter.id for chapter in by_number.get(number, []))

    range_spans = [match.span() for match in _CHAPTER_RANGE_PATTERN.finditer(query)]
    for match in _CHAPTER_SINGLE_PATTERN.finditer(query):
        if any(start <= match.start() and match.end() <= end for start, end in range_spans):
            continue
        number = _chapter_number_token(match.group("num"))
        if number is not None:
            selected_ids.update(chapter.id for chapter in by_number.get(number, []))

    for match in _CHAPTER_LIST_PATTERN.finditer(query):
        body = match.group("body")
        if "章" not in body:
            continue
        for value in re.findall(rf"(?:第\s*)?({_CHAPTER_NUM_TOKEN})\s*(?:章)?", body):
            number = _chapter_number_token(value)
            if number is not None:
                selected_ids.update(chapter.id for chapter in by_number.get(number, []))

    if not selected_ids:
        return []
    return [chapter for chapter in chapters if chapter.id in selected_ids]


def _slide_page_numbers_from_query(query: str) -> list[int]:
    numbers = set(_page_numbers_from_query(query))
    for match in _SLIDE_PAGE_PATTERN.finditer(str(query or "")):
        number = _chapter_number_token(match.group("num"))
        if number is not None:
            numbers.add(number)
    return sorted(number for number in numbers if number > 0)


def _section_numbers_from_query(query: str) -> list[str]:
    values: list[str] = []
    for match in _SECTION_PATTERN.finditer(str(query or "")):
        value = f"{int(match.group('chapter'))}.{int(match.group('section'))}"
        if value not in values:
            values.append(value)
    return values[:4]


def _infer_question_type(
    *,
    question: str,
    scope: str,
    has_chapter_target: bool,
    page_numbers: list[int],
    lesson_page_id: int | None,
) -> str:
    text = str(question or "")
    if _QUIZ_REQUEST_PATTERN.search(text):
        return "quiz_request"
    if _NOTE_REQUEST_PATTERN.search(text):
        return "note_request"
    if _TABLE_QUESTION_PATTERN.search(text):
        return "table_question"
    if _FIGURE_QUESTION_PATTERN.search(text):
        return "figure_question"
    if page_numbers or (lesson_page_id is not None and _SPECIFIC_PAGE_HINT_PATTERN.search(text)):
        return "specific_slide"
    if scope == "course_overview" or _COURSE_SUMMARY_PATTERN.search(text):
        return "course_overview"
    if has_chapter_target and _is_large_content_request(text):
        return "large_chapter_request"
    if scope == "chapter_overview" or _CHAPTER_SUMMARY_PATTERN.search(text):
        return "chapter_overview"
    if _COMPARE_QUESTION_PATTERN.search(text):
        return "compare"
    if _PRINCIPLE_QUESTION_PATTERN.search(text):
        return "principle"
    if _CONCEPT_QUESTION_PATTERN.search(text):
        return "concept"
    return "specific"


def _is_large_content_request(question: str) -> bool:
    text = str(question or "")
    return bool(_LARGE_REQUEST_PATTERN.search(text) or _CHAPTER_WIDE_CONTENT_PATTERN.search(text))


def _agent_tools_for_type(question_type: str) -> list[str]:
    mapping = {
        "specific_slide": ["read_slide", "read_page", "quote_source"],
        "table_question": ["search_courseware", "extract_table", "quote_source"],
        "figure_question": ["search_courseware", "analyze_figure", "quote_source"],
        "large_chapter_request": ["get_chapter_summary", "get_section_summary", "quote_source"],
        "chapter_overview": ["get_chapter_summary", "quote_source"],
        "course_overview": ["get_chapter_summary", "get_section_summary", "quote_source"],
        "quiz_request": ["search_courseware", "get_chapter_summary", "generate_quiz", "quote_source"],
        "note_request": ["search_courseware", "get_section_summary", "quote_source"],
        "compare": ["search_courseware", "quote_source"],
        "principle": ["search_courseware", "quote_source"],
        "concept": ["search_courseware", "quote_source"],
    }
    return mapping.get(question_type, ["search_courseware", "quote_source"])


def _build_agent_retrieval_query(
    *,
    question_for_ai: str,
    question_type: str,
    keywords: list[str],
    search_phrases: list[str] | None = None,
    expanded_terms: list[str] | None = None,
    chapter_ids: list[int],
    page_numbers: list[int],
    section_numbers: list[str],
) -> str:
    parts: list[str] = []
    if search_phrases:
        parts.append("\n".join(search_phrases[:6]))
    if keywords:
        parts.append(" ".join(keywords[:10]))
    if expanded_terms:
        parts.append(" ".join(expanded_terms[:8]))
    if section_numbers:
        parts.append(" ".join(section_numbers[:4]))
    if page_numbers:
        parts.append(" ".join(f"第{item}页" for item in page_numbers[:8]))
    if not parts:
        parts.append(question_for_ai)
    return "\n".join(part for part in parts if part).strip()[:3600]


def _classroom_agent_plan(
    db: Session,
    *,
    course_id: int,
    payload: QAAskRequest,
    question_for_ai: str,
) -> ClassroomAgentPlan:
    course = db.get(Course, course_id)
    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    chapter_rows = [{"id": chapter.id, "title": chapter.title, "order_index": chapter.order_index} for chapter in chapters]
    explicit_chapters = _chapters_from_query(payload.question, chapters)
    explicit_chapter_ids = [chapter.id for chapter in explicit_chapters]
    try:
        classification = ai_service.classify_qa_question_scope(
            question=payload.question,
            course_name=course.name if course else "",
            chapters=chapter_rows,
            db=db,
        )
    except Exception:
        classification = {"scope": "specific", "chapter_id": None, "confidence": 0, "reason": "classifier_unavailable"}
    scope = str(classification.get("scope") or "specific")
    if scope not in {"specific", "chapter_overview", "course_overview"}:
        scope = "specific"
    classified_chapter_id = classification.get("chapter_id")
    try:
        classified_chapter_id = int(classified_chapter_id) if classified_chapter_id is not None else None
    except (TypeError, ValueError):
        classified_chapter_id = None
    valid_chapter_ids = {chapter.id for chapter in chapters}
    if classified_chapter_id not in valid_chapter_ids:
        classified_chapter_id = None
    if payload.chapter_id is not None and payload.chapter_id in valid_chapter_ids and not explicit_chapter_ids:
        explicit_chapter_ids = [payload.chapter_id]
    page_numbers = _slide_page_numbers_from_query(payload.question)
    section_numbers = _section_numbers_from_query(payload.question)
    has_chapter_target = bool(explicit_chapter_ids or classified_chapter_id or payload.chapter_id)
    if explicit_chapter_ids and (_CHAPTER_SUMMARY_PATTERN.search(payload.question) or _is_large_content_request(payload.question)):
        scope = "chapter_overview"
    question_type = _infer_question_type(
        question=payload.question,
        scope=scope,
        has_chapter_target=has_chapter_target,
        page_numbers=page_numbers,
        lesson_page_id=payload.lesson_page_id,
    )
    if question_type == "large_chapter_request":
        scope = "chapter_overview"
    heuristic_keywords = _query_terms(payload.question) or [item for item in ai_service.extract_keywords(payload.question, limit=8) if item]
    retrieval_plan = ai_service.plan_courseware_retrieval(
        question=payload.question,
        question_type=question_type,
        course_name=course.name if course else "",
        chapter_titles=[chapter.title for chapter in explicit_chapters] or [chapter.title for chapter in chapters],
        history=[{"role": "user", "content": question_for_ai}] if question_for_ai != payload.question else None,
        db=db,
    )
    planned_keywords = [str(item).strip() for item in retrieval_plan.get("keywords", []) if str(item).strip()]
    search_phrases = [str(item).strip() for item in retrieval_plan.get("search_phrases", []) if str(item).strip()]
    expanded_terms = [str(item).strip() for item in retrieval_plan.get("expanded_terms", []) if str(item).strip()]
    keywords = list(dict.fromkeys([*planned_keywords, *heuristic_keywords]))[:12]
    if not search_phrases:
        search_phrases = keywords[:4]
    chapter_id = explicit_chapter_ids[0] if len(explicit_chapter_ids) == 1 else classified_chapter_id
    retrieval_query = _build_agent_retrieval_query(
        question_for_ai=question_for_ai,
        question_type=question_type,
        keywords=keywords,
        search_phrases=search_phrases,
        expanded_terms=expanded_terms,
        chapter_ids=explicit_chapter_ids,
        page_numbers=page_numbers,
        section_numbers=section_numbers,
    )
    return ClassroomAgentPlan(
        question_type=question_type,
        scope=scope,
        keywords=keywords[:12],
        search_phrases=search_phrases[:8],
        expanded_terms=expanded_terms[:8],
        chapter_ids=explicit_chapter_ids,
        chapter_id=chapter_id,
        page_numbers=page_numbers[:8],
        section_numbers=section_numbers,
        tools=_agent_tools_for_type(question_type),
        retrieval_query=retrieval_query,
        large_request=question_type == "large_chapter_request",
    )


def _page_context_text(page: LessonPage, lesson: Lesson, material: CourseMaterial | None = None) -> str:
    page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
    script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
    material_label = _material_kind_label(material)
    pieces = [
        f"相关课件：{lesson.title}",
        f"资料类型：{material_label}",
        f"页面：第{page.page_number}页 {page.page_title or ''}".strip(),
    ]
    if material is not None:
        pieces.insert(1, f"资料文件：{material.title}")
    if page_text:
        pieces.append(f"页面内容：{_trim_context(page_text, limit=1800)}")
    if script_text and script_text != page_text:
        pieces.append(f"讲解文稿：{_trim_context(script_text, limit=1200)}")
    return "\n".join(pieces)


def _page_source(page: LessonPage, lesson: Lesson, material: CourseMaterial | None = None) -> dict:
    tool = _material_read_tool(material)
    title = f"{lesson.title} · 第{page.page_number}页"
    if material is not None and material.title and material.title != lesson.title:
        title = f"{material.title} · {title}"
    return {
        "title": title,
        "lesson_id": lesson.id,
        "lesson_page_id": page.id,
        "page_number": page.page_number,
        "material_id": material.id if material is not None else lesson.material_id,
        "material_title": material.title if material is not None else None,
        "material_type": material.material_type if material is not None else None,
        "type": "lesson_page",
        "tool": tool,
        "excerpt": _page_excerpt(page),
    }


def _specified_page_context(
    db: Session,
    *,
    course_id: int,
    page_numbers: list[int],
    lesson_id: int | None = None,
    chapter_id: int | None = None,
    limit: int = 6,
) -> tuple[list[str], list[dict]]:
    if not page_numbers:
        return [], []
    statement = (
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(
            Lesson.course_id == course_id,
            LessonPage.page_number.in_(page_numbers),
        )
    )
    if lesson_id is not None:
        statement = statement.where(Lesson.id == lesson_id)
    elif chapter_id is not None:
        statement = statement.where(Lesson.chapter_id == chapter_id)
    rows = list(db.execute(statement.order_by(Lesson.id, LessonPage.page_number).limit(limit)))
    contexts: list[str] = []
    sources: list[dict] = []
    for page, lesson, material in rows:
        tool = _material_read_tool(material)
        contexts.append(f"工具 {tool} 结果：\n" + _page_context_text(page, lesson, material))
        sources.append(_page_source(page, lesson, material))
    return contexts, sources


def _chapter_layered_context(
    db: Session,
    *,
    course_id: int,
    chapter_ids: list[int],
    page_sample_limit: int = 4,
    lesson_limit: int = 20,
) -> tuple[list[str], list[dict]]:
    if not chapter_ids:
        return [], []
    contexts: list[str] = []
    sources: list[dict] = []
    chapters = list(
        db.scalars(
            select(Chapter)
            .where(Chapter.course_id == course_id, Chapter.id.in_(chapter_ids))
            .order_by(Chapter.order_index, Chapter.id)
        )
    )
    for chapter in chapters:
        lessons = list(
            db.scalars(
                select(Lesson)
                .where(Lesson.course_id == course_id, Lesson.chapter_id == chapter.id)
                .order_by(Lesson.id)
                .limit(lesson_limit)
            )
        )
        lines = [f"工具 get_chapter_summary 结果：章节：{chapter.title}"]
        if chapter.description:
            lines.append(f"章节说明：{chapter.description}")
        if not lessons:
            lines.append("该章节暂未关联已解析课件页。")
        for lesson in lessons:
            lines.append(f"小节/课件：{lesson.title}（共{lesson.page_count or 0}页）")
            if lesson.summary:
                lines.append(f"小节摘要：{_trim_context(lesson.summary, limit=260)}")
            pages = list(
                db.scalars(
                    select(LessonPage)
                    .where(LessonPage.lesson_id == lesson.id)
                    .order_by(LessonPage.page_number)
                    .limit(page_sample_limit)
                )
            )
            for page in pages:
                page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
                title = page.page_title or "本页内容"
                lines.append(f"- 第{page.page_number}页 {title}：{_trim_context(page_text, limit=160)}")
        contexts.append("\n".join(lines))
        sources.append({"chapter_id": chapter.id, "chapter_title": chapter.title, "type": "chapter_summary", "tool": "get_chapter_summary"})
    return contexts, sources


def _table_or_figure_context(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None,
    lesson_id: int | None,
    kind: str,
    limit: int = 4,
) -> tuple[list[str], list[dict]]:
    if kind == "table":
        return _extract_table_context(
            db,
            course_id=course_id,
            query=query,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            limit=limit,
        )
    page_contexts, page_sources = _page_keyword_context(
        db,
        course_id=course_id,
        query=query,
        lesson_id=lesson_id,
        chapter_id=chapter_id,
        limit=limit,
    )
    if not page_contexts:
        return [], []
    tool = "analyze_figure"
    label = "图片/流程图/图表文本线索候选"
    contexts = [f"工具 {tool} 结果（{label}）：\n{context}" for context in page_contexts]
    sources: list[dict] = []
    for source in page_sources:
        item = dict(source)
        item["tool"] = tool
        sources.append(item)
    return contexts, sources


def _extract_table_context(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None,
    lesson_id: int | None,
    limit: int = 4,
) -> tuple[list[str], list[dict]]:
    statement = (
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(Lesson.course_id == course_id)
    )
    if lesson_id is not None:
        statement = statement.where(Lesson.id == lesson_id)
    elif chapter_id is not None:
        statement = statement.where(Lesson.chapter_id == chapter_id)
    rows = list(db.execute(statement.order_by(Lesson.id, LessonPage.page_number).limit(_QA_FALLBACK_PAGE_SCAN_LIMIT)))
    scored_tables: list[tuple[int, LessonPage, Lesson, CourseMaterial | None, list[ExtractedTable]]] = []
    scored_pages: list[tuple[int, LessonPage, Lesson, CourseMaterial | None]] = []
    for page, lesson, material in rows:
        text = "\n".join(
            part
            for part in [
                page.page_title or "",
                _extract_text_payload(page.page_text) or str(page.page_text or ""),
                _extract_text_payload(page.script_text) or str(page.script_text or ""),
            ]
            if part
        )
        score = _score_text_for_query(title=f"{lesson.title} {page.page_title or ''}", text=text, page_number=page.page_number, query=query)
        tables = _extract_tables_from_text(text, limit=3)
        if tables:
            table_text = "\n".join(" ".join([*table.columns, *[cell for row in table.rows for cell in row]]) for table in tables)
            table_score = score + _score_text_for_query(title=lesson.title, text=table_text, page_number=page.page_number, query=query) + 60
            scored_tables.append((table_score, page, lesson, material, tables))
        elif score > 0:
            scored_pages.append((score, page, lesson, material))
    scored_tables.sort(key=lambda item: (item[0], -item[1].page_number), reverse=True)
    contexts: list[str] = []
    sources: list[dict] = []
    for _score, page, lesson, material, tables in scored_tables[:limit]:
        table_blocks = "\n\n".join(_format_table_for_context(table, index=index) for index, table in enumerate(tables, start=1))
        contexts.append(
            "工具 extract_table 结果：\n"
            + f"来源页面：{lesson.title} 第{page.page_number}页 {page.page_title or ''}\n"
            + table_blocks
        )
        source = _page_source(page, lesson, material)
        source["tool"] = "extract_table"
        source["table_count"] = len(tables)
        sources.append(source)
    if contexts:
        return contexts, sources

    scored_pages.sort(key=lambda item: (item[0], -item[1].page_number), reverse=True)
    for _score, page, lesson, material in scored_pages[:limit]:
        contexts.append(
            "工具 extract_table 结果：未在候选页解析到 Markdown/HTML/TSV 结构化表格；以下为相关页面文字，回答时必须说明未找到明确表格结构。\n"
            + _page_context_text(page, lesson, material)
        )
        source = _page_source(page, lesson, material)
        source["tool"] = "extract_table"
        source["table_count"] = 0
        sources.append(source)
    return contexts, sources


def _chunk_source(chunk: KnowledgeChunk) -> dict:
    source = dict(chunk.source_meta or {})
    source.update(
        {
            "type": source.get("type") or "knowledge_chunk",
            "chunk_id": chunk.id,
            "title": chunk.title,
            "material_id": source.get("material_id") or chunk.material_id,
            "lesson_page_id": source.get("lesson_page_id") or chunk.lesson_page_id,
            "chapter_id": source.get("chapter_id") or chunk.chapter_id,
            "excerpt": source.get("excerpt") or _compact_excerpt(chunk.content, limit=140),
        }
    )
    return source


def _lesson_id_for_page(db: Session, *, course_id: int, lesson_page_id: int | None) -> int | None:
    if lesson_page_id is None:
        return None
    return db.scalar(
        select(Lesson.id)
        .join(LessonPage, LessonPage.lesson_id == Lesson.id)
        .where(LessonPage.id == lesson_page_id, Lesson.course_id == course_id)
    )


def _lesson_outline_context(db: Session, *, course_id: int, lesson_id: int | None, limit: int = 80) -> tuple[list[str], list[dict]]:
    if lesson_id is None:
        return [], []
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course_id:
        return [], []
    pages = list(
        db.scalars(
            select(LessonPage)
            .where(LessonPage.lesson_id == lesson_id)
            .order_by(LessonPage.page_number)
            .limit(limit)
        )
    )
    if not pages:
        return [], []
    lines = [f"当前课件：{lesson.title}", "全页索引："]
    for page in pages:
        page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
        script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
        summary = _trim_context(" ".join(part for part in [page_text, script_text if script_text != page_text else ""] if part), limit=180)
        title = page.page_title or "本页内容"
        lines.append(f"- 第{page.page_number}页 {title}：{summary}")
    return [
        "\n".join(lines)
    ], [
        {
            "title": f"{lesson.title} · 全页索引",
            "lesson_id": lesson.id,
            "type": "lesson_outline",
        }
    ]


def _page_keyword_context(
    db: Session,
    *,
    course_id: int,
    query: str,
    lesson_id: int | None = None,
    chapter_id: int | None = None,
    exclude_page_id: int | None = None,
    limit: int = 4,
) -> tuple[list[str], list[dict]]:
    statement = (
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(Lesson.course_id == course_id)
    )
    if lesson_id is not None:
        statement = statement.where(Lesson.id == lesson_id)
    elif chapter_id is not None:
        statement = statement.where(Lesson.chapter_id == chapter_id)
    rows = list(db.execute(statement.order_by(Lesson.id, LessonPage.page_number).limit(_QA_FALLBACK_PAGE_SCAN_LIMIT)))
    scored: list[tuple[int, LessonPage, Lesson, CourseMaterial | None]] = []
    for page, lesson, material in rows:
        if exclude_page_id is not None and page.id == exclude_page_id:
            continue
        text = " ".join(
            part
            for part in [
                page.page_title or "",
                _extract_text_payload(page.page_text) or str(page.page_text or ""),
                _extract_text_payload(page.script_text) or str(page.script_text or ""),
            ]
            if part
        )
        score = _score_text_for_query(title=f"{lesson.title} {page.page_title or ''}", text=text, page_number=page.page_number, query=query)
        if score > 0:
            scored.append((score, page, lesson, material))
    scored.sort(key=lambda item: (item[0], -item[1].page_number), reverse=True)
    contexts = [_page_context_text(page, lesson, material) for _score, page, lesson, material in scored[:limit]]
    sources = [_page_source(page, lesson, material) for _score, page, lesson, material in scored[:limit]]
    return contexts, sources


def _material_keyword_context(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None = None,
    limit: int = 3,
) -> tuple[list[str], list[dict]]:
    statement = select(CourseMaterial).where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
    if chapter_id is not None:
        statement = statement.where(CourseMaterial.chapter_id == chapter_id)
    materials = list(db.scalars(statement.order_by(CourseMaterial.id).limit(80)))
    scored: list[tuple[int, CourseMaterial]] = []
    for material in materials:
        text = _extract_text_payload(material.extracted_text) or str(material.extracted_text or "").strip()
        score = _score_text_for_query(title=material.title, text=text, page_number=None, query=query)
        if score > 0:
            scored.append((score, material))
    scored.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
    contexts = [
        f"相关资料：{material.title}\n{_trim_context(_extract_text_payload(material.extracted_text) or str(material.extracted_text or ''), limit=2200)}"
        for _score, material in scored[:limit]
    ]
    sources = [
        {
            "material_id": material.id,
            "material_title": material.title,
            "material_type": material.material_type,
            "type": "material",
            "tool": "search_courseware",
            "excerpt": _compact_excerpt(_extract_text_payload(material.extracted_text) or str(material.extracted_text or ""), limit=140),
        }
        for _score, material in scored[:limit]
    ]
    return contexts, sources


def _chapter_context(
    db: Session,
    *,
    course_id: int,
    chapter_id: int | None,
    limit: int = 8,
    page_limit: int | None = None,
) -> tuple[list[str], list[dict]]:
    if chapter_id is None:
        return [], []
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.course_id != course_id:
        return [], []
    contexts: list[str] = []
    sources: list[dict] = []
    heading = f"章节：{chapter.title}"
    if chapter.description:
        contexts.append(f"{heading}\n章节说明：{chapter.description}")
        sources.append({"chapter_id": chapter.id, "chapter_title": chapter.title, "type": "chapter"})

    chunk_limit = max(0, int(limit))
    page_limit = max(1, int(page_limit if page_limit is not None else max(limit * 3, 12)))
    chunks = list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.course_id == course_id, KnowledgeChunk.chapter_id == chapter_id)
            .order_by(KnowledgeChunk.id)
            .limit(chunk_limit)
        )
    )
    for chunk in chunks:
        content = _trim_context(chunk.content)
        if not content:
            continue
        contexts.append(f"{heading}\n资料片段：{chunk.title}\n{content}")
        source = dict(chunk.source_meta or {})
        source.update({"chapter_id": chapter.id, "chapter_title": chapter.title, "chunk_id": chunk.id, "title": chunk.title, "excerpt": _compact_excerpt(chunk.content, limit=140)})
        sources.append(source)

    page_rows = db.execute(
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(Lesson.course_id == course_id, Lesson.chapter_id == chapter_id)
        .order_by(Lesson.id, LessonPage.page_number)
        .limit(page_limit)
    )
    for page, lesson, material in page_rows:
        page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
        script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
        pieces = [f"{heading}", f"课时：{lesson.title}", f"资料类型：{_material_kind_label(material)}", f"页面：第{page.page_number}页 {page.page_title or ''}".strip()]
        if material is not None:
            pieces.insert(2, f"资料文件：{material.title}")
        if page_text:
            pieces.append(f"页面内容：{_trim_context(page_text, limit=1000)}")
        if script_text and script_text != page_text:
            pieces.append(f"讲解文稿：{_trim_context(script_text, limit=800)}")
        if not page_text and not script_text:
            continue
        contexts.append("\n".join(pieces))
        source = _page_source(page, lesson, material)
        source.update({"chapter_id": chapter.id, "chapter_title": chapter.title})
        sources.append(source)
    if contexts:
        return contexts, sources

    materials = list(
        db.scalars(
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id, CourseMaterial.chapter_id == chapter_id, CourseMaterial.deleted_at.is_(None))
            .order_by(CourseMaterial.id)
            .limit(4)
        )
    )
    for material in materials:
        text = _extract_text_payload(material.extracted_text) or str(material.extracted_text or "").strip()
        if not text:
            continue
        contexts.append(f"{heading}\n资料：{material.title}\n{_trim_context(text, limit=1800)}")
        sources.append(
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "material_id": material.id,
                "material_title": material.title,
                "material_type": material.material_type,
                "excerpt": _compact_excerpt(text, limit=140),
            }
        )
    return contexts, sources


def _course_context(db: Session, *, course_id: int, limit: int = 12) -> tuple[list[str], list[dict]]:
    course = db.get(Course, course_id)
    if course is None:
        return [], []
    contexts: list[str] = []
    sources: list[dict] = []
    course_heading = f"课程：{course.name}"
    if course.description:
        contexts.append(f"{course_heading}\n课程说明：{course.description}")
        sources.append({"course_id": course.id, "course_name": course.name, "type": "course"})

    chapters = list(db.scalars(select(Chapter).where(Chapter.course_id == course_id).order_by(Chapter.order_index, Chapter.id)))
    if chapters:
        chapter_lines = [f"{item.order_index}. {item.title}" + (f"：{item.description}" if item.description else "") for item in chapters]
        contexts.append(f"{course_heading}\n章节结构：\n" + "\n".join(chapter_lines[:12]))
        sources.append({"course_id": course.id, "course_name": course.name, "type": "chapters"})

    chunks = list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.course_id == course_id)
            .order_by(KnowledgeChunk.chapter_id.is_(None), KnowledgeChunk.chapter_id, KnowledgeChunk.id)
            .limit(limit)
        )
    )
    for chunk in chunks:
        content = _trim_context(chunk.content, limit=1000)
        if not content:
            continue
        title = chunk.title or "资料片段"
        contexts.append(f"{course_heading}\n资料片段：{title}\n{content}")
        source = dict(chunk.source_meta or {})
        source.update({"course_id": course.id, "course_name": course.name, "chunk_id": chunk.id, "title": title, "excerpt": _compact_excerpt(chunk.content, limit=140)})
        sources.append(source)
    if len(contexts) > (2 if chapters else 1):
        return contexts, sources

    page_rows = db.execute(
        select(LessonPage, Lesson, CourseMaterial)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .outerjoin(CourseMaterial, CourseMaterial.id == Lesson.material_id)
        .where(Lesson.course_id == course_id)
        .order_by(Lesson.chapter_id.is_(None), Lesson.chapter_id, Lesson.id, LessonPage.page_number)
        .limit(limit)
    )
    for page, lesson, material in page_rows:
        page_text = _extract_text_payload(page.page_text) or str(page.page_text or "").strip()
        script_text = _extract_text_payload(page.script_text) or str(page.script_text or "").strip()
        pieces = [course_heading, f"课时：{lesson.title}", f"资料类型：{_material_kind_label(material)}", f"页面：第{page.page_number}页 {page.page_title or ''}".strip()]
        if material is not None:
            pieces.insert(2, f"资料文件：{material.title}")
        if page_text:
            pieces.append(f"页面内容：{_trim_context(page_text, limit=1000)}")
        if script_text and script_text != page_text:
            pieces.append(f"讲解文稿：{_trim_context(script_text, limit=1000)}")
        if not page_text and not script_text:
            continue
        contexts.append("\n".join(pieces))
        source = _page_source(page, lesson, material)
        source.update({"course_id": course.id, "course_name": course.name})
        sources.append(source)
    if len(contexts) > (2 if chapters else 1):
        return contexts, sources

    materials = list(
        db.scalars(
            select(CourseMaterial)
            .where(CourseMaterial.course_id == course_id, CourseMaterial.deleted_at.is_(None))
            .order_by(CourseMaterial.chapter_id.is_(None), CourseMaterial.chapter_id, CourseMaterial.id)
            .limit(6)
        )
    )
    for material in materials:
        text = _extract_text_payload(material.extracted_text) or str(material.extracted_text or "").strip()
        if not text:
            continue
        contexts.append(f"{course_heading}\n资料：{material.title}\n{_trim_context(text, limit=1600)}")
        sources.append(
            {
                "course_id": course.id,
                "course_name": course.name,
                "material_id": material.id,
                "material_title": material.title,
                "material_type": material.material_type,
                "excerpt": _compact_excerpt(text, limit=140),
            }
        )
    return contexts, sources


def _chunk_context(chunk: KnowledgeChunk) -> str:
    content = _trim_context(chunk.content, limit=1400)
    title = chunk.title or "资料片段"
    return f"资料片段：{title}\n{content}" if content else ""


def _merge_contexts(primary: list[str], chunks: list[KnowledgeChunk], trailing: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    contexts: list[str] = []
    for text in [*primary, *(_chunk_context(chunk) for chunk in chunks), *(trailing or [])]:
        clean = " ".join(str(text or "").split())
        if not clean or clean in seen:
            continue
        seen.add(clean)
        contexts.append(str(text))
    return contexts


def _agent_instruction_context(plan: ClassroomAgentPlan) -> str:
    label = {
        "concept": "概念解释",
        "principle": "原理说明",
        "compare": "对比问题",
        "chapter_overview": "章节总结",
        "large_chapter_request": "大范围学习请求",
        "specific_slide": "指定页/幻灯片讲解",
        "table_question": "表格问题",
        "figure_question": "图表问题",
        "quiz_request": "练习生成",
        "note_request": "复习整理",
        "course_overview": "课程总览",
    }.get(plan.question_type, "普通知识点问题")
    lines = [
        "智慧课堂 Agent 决策：",
        f"- 问题类型：{label}",
        f"- 调用工具：{', '.join(plan.tools)}",
        "- 回答原则：优先基于教师上传课件；先解释概念，再说明原理或步骤，再给例子或对比，最后简短总结。",
    ]
    if plan.large_request:
        lines.append("- 大范围内容策略：只能先给章节总览、小节摘要和重点难点，不要一次性逐页展开；结尾提示可按小节或每 10 页继续展开。")
    if plan.question_type == "quiz_request":
        lines.append("- 练习生成策略：根据课件知识点直接给题目；默认先不展示答案，除非学生明确要求答案。")
    if plan.question_type == "table_question":
        lines.append("- 表格策略：优先依据表格或结构化页面内容回答；如果课件没有明确表格内容，要说明未找到明确表格。")
    if plan.question_type == "figure_question":
        lines.append("- 图表策略：优先解释课件页面中的图片、流程图或图表文字线索；不要编造不可见图片细节。")
    return "\n".join(lines)


def _source_identity(source: dict[str, Any]) -> tuple[str, ...]:
    keys = ("type", "artifact_id", "chunk_id", "material_id", "lesson_id", "lesson_page_id", "page_number", "chapter_id", "title")
    return tuple(str(source.get(key) or "") for key in keys)


def _source_citation(source: dict[str, Any]) -> str:
    title = (
        source.get("material_title")
        or source.get("chapter_title")
        or source.get("course_name")
        or source.get("title")
        or source.get("filename")
        or "课件资料"
    )
    parts = [str(title)]
    chapter_title = source.get("chapter_title")
    if chapter_title and str(chapter_title) not in str(title):
        parts.append(str(chapter_title))
    page_number = source.get("page_number")
    if page_number:
        page_label = f"第{page_number}"
        if page_label not in str(title):
            parts.append(f"第{page_number}页/幻灯片")
    elif source.get("lesson_page_id"):
        parts.append("课件页")
    artifact_type = source.get("artifact_type")
    if artifact_type and source.get("type") == "pedagogy_artifact":
        parts.append("结构化教学对象")
    return "，".join(part for part in parts if part)


def _normalize_sources(sources: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    seen: set[tuple[str, ...]] = set()
    for source in sources:
        if not isinstance(source, dict) or not source:
            continue
        item = dict(source)
        if not item.get("title"):
            title_parts = [
                item.get("material_title") or item.get("chapter_title") or item.get("course_name") or "课件资料",
                f"第{item.get('page_number')}页" if item.get("page_number") else "",
            ]
            item["title"] = " · ".join(str(part) for part in title_parts if part)
        if item.get("excerpt"):
            item["excerpt"] = _compact_excerpt(str(item.get("excerpt") or ""), limit=140)
        item["citation"] = _source_citation(item)
        identity = _source_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(item)
        if len(normalized) >= 12:
            break
    return normalized


def _format_sources_for_answer(sources: list[dict], *, limit: int = 3) -> str:
    citations: list[str] = []
    for source in sources:
        citation = str(source.get("citation") or _source_citation(source)).strip()
        excerpt = _compact_excerpt(str(source.get("excerpt") or ""), limit=70)
        if citation and excerpt and excerpt not in citation:
            citation = f"{citation}：{excerpt}"
        if citation and citation not in citations:
            citations.append(citation)
        if len(citations) >= limit:
            break
    return "；".join(citations)


def _follow_up_suggestions(plan: ClassroomAgentPlan, *, has_sources: bool) -> list[str]:
    topic = next((item for item in plan.keywords if item not in _QA_QUERY_STOPWORDS), "这个知识点")
    if plan.question_type == "large_chapter_request":
        return ["按小节继续展开", "按每 10 页继续讲", "基于本章出 5 道复习题"]
    if plan.question_type == "chapter_overview":
        return ["展开本章重点难点", "按小节整理笔记", "基于本章出几道练习题"]
    if plan.question_type == "course_overview":
        return ["展开某一章", "整理课程复习提纲", "生成课程重点练习题"]
    if plan.question_type == "quiz_request":
        return ["显示答案和解析", "只出选择题", "按薄弱知识点再出几题"]
    if plan.question_type == "specific_slide":
        return ["总结这一页重点", "继续讲下一页", "基于这一页出练习题"]
    if plan.question_type == "table_question":
        return ["把表格整理成对比要点", "按表格内容出题", "解释表格里的某一项"]
    if plan.question_type == "figure_question":
        return ["按步骤解释流程图", "总结图表核心结论", "用例子说明这张图"]
    if plan.question_type == "compare":
        return [f"把{topic}做成表格对比", f"分别举例说明{topic}", f"出几道{topic}对比题"]
    if not has_sources:
        return ["换一种问法重新检索课件", "指定章节或页码再问", "让老师补充相关课件资料"]
    return [f"{topic}的原理是什么？", f"给我举一个{topic}例子", f"出几道{topic}练习题"]


def _answer_suffix(answer: str, *, sources: list[dict], plan: ClassroomAgentPlan, out_of_scope: bool) -> str:
    pieces: list[str] = []
    if sources and "来源" not in answer[-500:]:
        source_text = _format_sources_for_answer(sources)
        if source_text:
            pieces.append(f"来源：{source_text}")
    suggestions = _follow_up_suggestions(plan, has_sources=bool(sources))
    if suggestions and "你还可以继续问" not in answer and "可继续" not in answer:
        suggestion_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(suggestions[:3], start=1))
        pieces.append(f"你还可以继续问：\n{suggestion_lines}")
    if out_of_scope and not sources and "课程资料" not in answer:
        pieces.insert(0, "当前课件中没有找到这个问题的明确说明。")
    return "\n\n".join(pieces)


def _finalize_classroom_answer(answer: str, *, sources: list[dict], plan: ClassroomAgentPlan, out_of_scope: bool) -> str:
    clean = str(answer or "").strip()
    suffix = _answer_suffix(clean, sources=sources, plan=plan, out_of_scope=out_of_scope)
    if suffix:
        clean = f"{clean}\n\n{suffix}".strip()
    return clean


def _qa_contexts_and_sources(
    db: Session,
    *,
    course_id: int,
    payload: QAAskRequest,
    question_for_ai: str,
    history: list[dict[str, str]] | None = None,
    agent_plan: ClassroomAgentPlan | None = None,
) -> tuple[list[str], list[dict], list]:
    agent_plan = agent_plan or _classroom_agent_plan(db, course_id=course_id, payload=payload, question_for_ai=question_for_ai)
    retrieval_query = agent_plan.retrieval_query or question_for_ai
    scope = agent_plan.scope
    chapter_target_ids = list(dict.fromkeys(agent_plan.chapter_ids))
    retrieval_chapter_id = payload.chapter_id if payload.chapter_id is not None else (agent_plan.chapter_id if scope != "course_overview" else None)
    lesson_id = _lesson_id_for_page(db, course_id=course_id, lesson_page_id=payload.lesson_page_id)

    if agent_plan.large_request:
        target_ids = chapter_target_ids or ([retrieval_chapter_id] if retrieval_chapter_id is not None else [])
        if target_ids:
            contexts, sources = _chapter_layered_context(db, course_id=course_id, chapter_ids=target_ids)
        else:
            contexts, sources = _course_context(db, course_id=course_id)
        if contexts:
            contexts = _merge_contexts([_agent_instruction_context(agent_plan), *contexts], [], [])
        return contexts, _normalize_sources(sources), []

    artifact_hits = []
    chunks = []
    if chapter_target_ids:
        artifact_limit = max(2, 8 // max(len(chapter_target_ids), 1))
        chunk_limit = max(2, _QA_VECTOR_CONTEXT_LIMIT // max(len(chapter_target_ids), 1))
        for chapter_id in chapter_target_ids:
            artifact_hits.extend(
                search_pedagogy_artifacts(
                    db,
                    course_id=course_id,
                    query=retrieval_query,
                    chapter_id=chapter_id,
                    lesson_id=None,
                    lesson_page_id=None,
                    types=QA_ARTIFACT_TYPES,
                    limit=artifact_limit,
                )
            )
            chunks.extend(
                search_course_knowledge(
                    db,
                    course_id=course_id,
                    query=retrieval_query,
                    chapter_id=chapter_id,
                    lesson_id=None,
                    lesson_page_id=None,
                    limit=chunk_limit,
                )
            )
    else:
        artifact_hits = search_pedagogy_artifacts(
            db,
            course_id=course_id,
            query=retrieval_query,
            chapter_id=None if lesson_id is not None else retrieval_chapter_id,
            lesson_id=lesson_id,
            lesson_page_id=None,
            types=QA_ARTIFACT_TYPES,
            limit=10 if lesson_id is not None else 8,
        )
        chunks = search_course_knowledge(
            db,
            course_id=course_id,
            query=retrieval_query,
            chapter_id=None if lesson_id is not None else retrieval_chapter_id,
            lesson_id=lesson_id,
            lesson_page_id=None,
            limit=_QA_DETAIL_VECTOR_CONTEXT_LIMIT if lesson_id is not None else _QA_VECTOR_CONTEXT_LIMIT,
        )
    page_contexts, page_sources = _lesson_page_context(db, course_id=course_id, lesson_page_id=payload.lesson_page_id)
    if agent_plan.page_numbers:
        specified_contexts, specified_sources = _specified_page_context(
            db,
            course_id=course_id,
            page_numbers=agent_plan.page_numbers,
            lesson_id=lesson_id,
            chapter_id=retrieval_chapter_id,
        )
        page_contexts.extend(specified_contexts)
        page_sources.extend(specified_sources)

    fallback_chapter_id = payload.chapter_id if payload.chapter_id is not None else retrieval_chapter_id
    tool_contexts: list[str] = []
    tool_sources: list[dict] = []
    if agent_plan.question_type == "table_question":
        tool_contexts, tool_sources = _table_or_figure_context(
            db,
            course_id=course_id,
            query=retrieval_query,
            chapter_id=fallback_chapter_id,
            lesson_id=lesson_id,
            kind="table",
        )
    elif agent_plan.question_type == "figure_question":
        tool_contexts, tool_sources = _table_or_figure_context(
            db,
            course_id=course_id,
            query=retrieval_query,
            chapter_id=fallback_chapter_id,
            lesson_id=lesson_id,
            kind="figure",
        )

    related_page_contexts: list[str] = []
    related_page_sources: list[dict] = []
    if chapter_target_ids:
        page_limit = max(2, _QA_RELATED_PAGE_CONTEXT_LIMIT // max(len(chapter_target_ids), 1))
        for chapter_id in chapter_target_ids:
            chapter_page_contexts, chapter_page_sources = _page_keyword_context(
                db,
                course_id=course_id,
                query=retrieval_query,
                lesson_id=None,
                chapter_id=chapter_id,
                exclude_page_id=payload.lesson_page_id,
                limit=page_limit,
            )
            related_page_contexts.extend(chapter_page_contexts)
            related_page_sources.extend(chapter_page_sources)
    else:
        related_page_contexts, related_page_sources = _page_keyword_context(
            db,
            course_id=course_id,
            query=retrieval_query,
            lesson_id=lesson_id,
            chapter_id=fallback_chapter_id,
            exclude_page_id=payload.lesson_page_id,
            limit=_QA_RELATED_PAGE_CONTEXT_LIMIT,
        )
    rewritten_query = ""
    if not chapter_target_ids and not artifact_hits and not chunks and not related_page_contexts and not page_contexts and not tool_contexts:
        rewritten_query = ai_service.rewrite_retrieval_query(question=payload.question, history=history, db=db)
        if rewritten_query and rewritten_query.strip() not in {payload.question.strip(), question_for_ai.strip(), retrieval_query.strip()}:
            artifact_hits = search_pedagogy_artifacts(
                db,
                course_id=course_id,
                query=rewritten_query,
                chapter_id=None if lesson_id is not None else retrieval_chapter_id,
                lesson_id=lesson_id,
                lesson_page_id=None,
                types=QA_ARTIFACT_TYPES,
                limit=10 if lesson_id is not None else 8,
            )
            chunks = search_course_knowledge(
                db,
                course_id=course_id,
                query=rewritten_query,
                chapter_id=None if lesson_id is not None else retrieval_chapter_id,
                lesson_id=lesson_id,
                lesson_page_id=None,
                limit=_QA_DETAIL_VECTOR_CONTEXT_LIMIT if lesson_id is not None else _QA_VECTOR_CONTEXT_LIMIT,
            )
            related_page_contexts, related_page_sources = _page_keyword_context(
                db,
                course_id=course_id,
                query=rewritten_query,
                lesson_id=lesson_id,
                chapter_id=fallback_chapter_id,
                exclude_page_id=payload.lesson_page_id,
                limit=_QA_RELATED_PAGE_CONTEXT_LIMIT,
            )
    lesson_outline_contexts, lesson_outline_sources = _lesson_outline_context(db, course_id=course_id, lesson_id=lesson_id)
    chapter_contexts: list[str] = []
    chapter_sources: list[dict] = []
    course_contexts: list[str] = []
    course_sources: list[dict] = []
    material_contexts: list[str] = []
    material_sources: list[dict] = []
    if agent_plan.question_type in {"chapter_overview", "quiz_request", "note_request"} and (chapter_target_ids or retrieval_chapter_id):
        for chapter_id in chapter_target_ids or ([retrieval_chapter_id] if retrieval_chapter_id is not None else []):
            current_contexts, current_sources = _chapter_context(
                db,
                course_id=course_id,
                chapter_id=chapter_id,
                limit=8,
                page_limit=32 if agent_plan.question_type == "chapter_overview" else 20,
            )
            chapter_contexts.extend(current_contexts)
            chapter_sources.extend(current_sources)
    elif scope == "chapter_overview":
        chapter_contexts, chapter_sources = _chapter_context(db, course_id=course_id, chapter_id=retrieval_chapter_id, page_limit=32)
    if scope == "course_overview" and not page_contexts and not chapter_contexts:
        course_contexts, course_sources = _course_context(db, course_id=course_id)
    if not related_page_contexts and not chunks:
        material_query = rewritten_query or retrieval_query
        if chapter_target_ids:
            for chapter_id in chapter_target_ids:
                current_contexts, current_sources = _material_keyword_context(
                    db,
                    course_id=course_id,
                    query=material_query,
                    chapter_id=chapter_id,
                    limit=2,
                )
                material_contexts.extend(current_contexts)
                material_sources.extend(current_sources)
        else:
            material_contexts, material_sources = _material_keyword_context(
                db,
                course_id=course_id,
                query=material_query,
                chapter_id=fallback_chapter_id,
            )
    structured_contexts = artifact_contexts(artifact_hits)
    primary_contexts = [
        *page_contexts,
        *chapter_contexts,
        *course_contexts,
        *structured_contexts,
        *tool_contexts,
        *related_page_contexts,
        *material_contexts,
    ]
    if agent_plan.question_type == "quiz_request":
        quiz_context = _generate_quiz_context(
            db,
            plan=agent_plan,
            question=payload.question,
            source_contexts=primary_contexts,
            chunks=chunks,
        )
        if quiz_context:
            primary_contexts = [quiz_context, *primary_contexts]
    if primary_contexts or chunks:
        primary_contexts = [_agent_instruction_context(agent_plan), *primary_contexts]
    contexts = _merge_contexts(
        primary_contexts,
        chunks,
        trailing=lesson_outline_contexts,
    )
    sources = [
        *page_sources,
        *chapter_sources,
        *course_sources,
        *artifact_sources(artifact_hits),
        *tool_sources,
        *related_page_sources,
        *material_sources,
        *(_chunk_source(chunk) for chunk in chunks),
        *lesson_outline_sources,
    ]
    return contexts, _normalize_sources(sources), chunks


def upload_qa_image(db: Session, *, user: User, course_id: int, upload: UploadFile) -> dict:
    _assert_student_course_access(db, course_id=course_id, user=user)
    suffix = Path(upload.filename or "").suffix.lower()
    content_type = (upload.content_type or "").lower()
    if suffix not in _IMAGE_SUFFIXES and not content_type.startswith("image/"):
        raise bad_request("请上传图片文件")
    relative_path, size_bytes = storage_service.save_upload(upload, folder=f"qa_images/course_{course_id}/user_{user.id}", db=db)
    if size_bytes <= 0:
        raise bad_request("图片文件为空")
    if size_bytes > _QA_IMAGE_LIMIT_BYTES:
        raise bad_request("图片大小不能超过 10MB")
    ocr_text = ocr_service.recognize(upload, db=db)
    return {
        "type": "image",
        "url": storage_service.public_url(relative_path, db=db),
        "filename": upload.filename or "image",
        "size_bytes": size_bytes,
        "ocr_text": ocr_text,
    }


def ask_question(db: Session, *, user: User, payload: QAAskRequest) -> QARecord:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    conversation = _get_or_create_course_conversation(db, user=user, payload=payload)
    history = _conversation_history(db, conversation_id=conversation.id)
    history_for_prompt = _history_messages(history)
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    retrieval_question = _question_with_history_for_retrieval(question_for_ai, history_for_prompt)
    agent_plan = _classroom_agent_plan(db, course_id=payload.course_id, payload=payload, question_for_ai=retrieval_question)
    contexts, sources, _chunks = _qa_contexts_and_sources(
        db,
        course_id=payload.course_id,
        payload=payload,
        question_for_ai=agent_plan.retrieval_query,
        history=history_for_prompt,
        agent_plan=agent_plan,
    )
    allow_general_ai_answer = _course_allows_general_ai_answer(db, course_id=payload.course_id)
    if contexts:
        answer, out_of_scope, thinking_process = ai_service.answer_question(
            question=question_for_ai,
            contexts=contexts,
            history=history_for_prompt,
            db=db,
        )
    elif allow_general_ai_answer:
        general_answer, thinking_process = ai_service.answer_general_question(
            question=question_for_ai,
            history=history_for_prompt,
            db=db,
        )
        answer = f"{_GENERAL_AI_NOTICE}\n\n{general_answer}".strip()
        out_of_scope = True
    else:
        answer = _GENERAL_AI_DISABLED_NOTICE
        out_of_scope = True
        thinking_process = None
    answer = _finalize_classroom_answer(answer, sources=sources, plan=agent_plan, out_of_scope=out_of_scope)
    record = QARecord(
        conversation_id=conversation.id,
        course_id=payload.course_id,
        user_id=user.id,
        lesson_page_id=payload.lesson_page_id,
        question=payload.question,
        answer=answer,
        thinking_process=thinking_process,
        is_out_of_scope=out_of_scope,
        sources=sources,
        attachments=attachments,
        keywords=agent_plan.keywords or ai_service.extract_keywords(payload.question),
    )
    db.add(record)
    log_ai_usage(
        db,
        module="qa",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(question_for_ai),
        completion_chars=len(answer),
        success=not out_of_scope,
        error_message="out_of_scope" if out_of_scope else None,
    )
    db.commit()
    db.refresh(record)
    record_qa_learning_signals(db, user=user, record=record)
    return record


def ask_question_stream(db: Session, *, user: User, payload: QAAskRequest) -> Iterator[dict]:
    _assert_student_course_access(db, course_id=payload.course_id, user=user)
    conversation = _get_or_create_course_conversation(db, user=user, payload=payload)
    history = _conversation_history(db, conversation_id=conversation.id)
    history_for_prompt = _history_messages(history)
    attachments = _attachment_dicts(payload)
    question_for_ai = _question_with_attachments(payload.question, attachments)
    retrieval_question = _question_with_history_for_retrieval(question_for_ai, history_for_prompt)
    agent_plan = _classroom_agent_plan(db, course_id=payload.course_id, payload=payload, question_for_ai=retrieval_question)
    contexts, sources, _chunks = _qa_contexts_and_sources(
        db,
        course_id=payload.course_id,
        payload=payload,
        question_for_ai=agent_plan.retrieval_query,
        history=history_for_prompt,
        agent_plan=agent_plan,
    )
    allow_general_ai_answer = _course_allows_general_ai_answer(db, course_id=payload.course_id)
    out_of_scope = not contexts
    answer_parts: list[str] = []
    thought_parts: list[str] = []
    tag_state: dict[str, object] = {"buffer": "", "in_think": False}
    ai_error_message: str | None = None

    if not contexts:
        if allow_general_ai_answer:
            general_answer, general_thinking = ai_service.answer_general_question(
                question=question_for_ai,
                history=history_for_prompt,
                db=db,
            )
            answer = f"{_GENERAL_AI_NOTICE}\n\n{general_answer}".strip()
            if general_thinking:
                yield from _stream_text_delta("thought", general_thinking, answer_parts, thought_parts)
            yield from _stream_text_delta("answer", answer, answer_parts, thought_parts)
        else:
            answer = _GENERAL_AI_DISABLED_NOTICE
            yield from _stream_text_delta("answer", answer, answer_parts, thought_parts)
    else:
        try:
            for delta in ai_service.stream_answer_question(
                question=question_for_ai,
                contexts=contexts,
                history=history_for_prompt,
                db=db,
            ):
                if delta.kind == "reasoning":
                    yield from _stream_text_delta("thought", delta.text, answer_parts, thought_parts)
                    continue
                for kind, text in _split_thinking_tags(tag_state, delta.text):
                    yield from _stream_text_delta(kind, text, answer_parts, thought_parts)
        except Exception as exc:
            answer_parts.clear()
            thought_parts.clear()
            tag_state = {"buffer": "", "in_think": False}
            try:
                fallback_answer, fallback_out_of_scope, fallback_thinking = ai_service.answer_question(
                    question=question_for_ai,
                    contexts=contexts,
                    history=history_for_prompt,
                    db=db,
                )
                out_of_scope = fallback_out_of_scope
                if fallback_thinking:
                    yield from _stream_text_delta("thought", fallback_thinking, answer_parts, thought_parts)
                for kind, text in _split_thinking_tags(tag_state, fallback_answer):
                    yield from _stream_text_delta(kind, text, answer_parts, thought_parts)
            except Exception as fallback_exc:
                ai_error_message = str(fallback_exc or exc)
                answer = "AI 服务暂时不可用，请稍后重试，或联系管理员检查问答模型配置。"
                answer_parts.append(answer)
                yield {"event": "delta", "data": {"type": "answer", "text": answer}}

    for kind, text in _flush_thinking_tags(tag_state):
        yield from _stream_text_delta(kind, text, answer_parts, thought_parts)

    answer = "".join(answer_parts).strip()
    thinking_process = "".join(thought_parts).strip() or None
    if not answer:
        answer = "当前没有生成有效回答，请换一种问法或稍后重试。"
        answer_parts.append(answer)
        yield {"event": "delta", "data": {"type": "answer", "text": answer}}
    suffix = _answer_suffix(answer, sources=sources, plan=agent_plan, out_of_scope=out_of_scope)
    if suffix:
        yield from _stream_text_delta("answer", f"\n\n{suffix}", answer_parts, thought_parts)
        answer = "".join(answer_parts).strip()
    record = QARecord(
        conversation_id=conversation.id,
        course_id=payload.course_id,
        user_id=user.id,
        lesson_page_id=payload.lesson_page_id,
        question=payload.question,
        answer=answer,
        thinking_process=thinking_process,
        is_out_of_scope=out_of_scope,
        sources=sources,
        attachments=attachments,
        keywords=agent_plan.keywords or ai_service.extract_keywords(payload.question),
    )
    db.add(record)
    log_ai_usage(
        db,
        module="qa",
        user_id=user.id,
        course_id=payload.course_id,
        prompt_chars=len(question_for_ai),
        completion_chars=len(answer),
        success=not out_of_scope and ai_error_message is None,
        error_message=ai_error_message[:500] if ai_error_message else ("out_of_scope" if out_of_scope else None),
    )
    db.commit()
    db.refresh(record)
    record_qa_learning_signals(db, user=user, record=record)
    yield {
        "event": "final",
        "data": {
            "conversation_id": record.conversation_id,
            "record_id": record.id,
            "question": record.question,
            "answer": record.answer,
            "thinking_process": record.thinking_process,
            "is_out_of_scope": record.is_out_of_scope,
            "sources": record.sources or [],
            "attachments": record.attachments or [],
        },
    }


def list_history(db: Session, *, user: User, course_id: int | None = None, lesson_id: int | None = None, keyword: str | None = None) -> list[dict]:
    if user.role == UserRole.STUDENT.value:
        if course_id is None:
            course_ids = list(
                db.scalars(select(CourseMembership.course_id).where(CourseMembership.user_id == user.id).limit(2))
            )
            if len(course_ids) != 1:
                return []
            course_id = course_ids[0]
        _assert_student_course_access(db, course_id=course_id, user=user)
    conversation_statement = select(QAConversation.id).where(QAConversation.user_id == user.id)
    if course_id is not None:
        conversation_statement = conversation_statement.where(QAConversation.course_id == course_id)
    lesson_page_ids = None
    if lesson_id is not None:
        lesson_page_ids = (
            select(LessonPage.id)
            .join(Lesson, Lesson.id == LessonPage.lesson_id)
            .where(Lesson.id == lesson_id)
        )
        if course_id is not None:
            lesson_page_ids = lesson_page_ids.where(Lesson.course_id == course_id)
        lesson_conversation_ids = select(QARecord.conversation_id).where(
            QARecord.user_id == user.id,
            QARecord.lesson_page_id.in_(lesson_page_ids),
        )
        if course_id is not None:
            lesson_conversation_ids = lesson_conversation_ids.where(QARecord.course_id == course_id)
        conversation_statement = conversation_statement.where(QAConversation.id.in_(lesson_conversation_ids))
    else:
        lesson_conversation_ids = select(QARecord.conversation_id).where(
            QARecord.user_id == user.id,
            QARecord.lesson_page_id.is_not(None),
        )
        if course_id is not None:
            lesson_conversation_ids = lesson_conversation_ids.where(QARecord.course_id == course_id)
        conversation_statement = conversation_statement.where(QAConversation.id.not_in(lesson_conversation_ids))
    if keyword:
        like = f"%{keyword}%"
        keyword_conversation_ids = select(QARecord.conversation_id).where(
            QARecord.user_id == user.id,
            or_(QARecord.question.like(like), QARecord.answer.like(like)),
        )
        if course_id is not None:
            keyword_conversation_ids = keyword_conversation_ids.where(QARecord.course_id == course_id)
        conversation_statement = conversation_statement.where(QAConversation.id.in_(keyword_conversation_ids))

    conversation_ids = conversation_statement.subquery()
    conversation_id_select = select(conversation_ids.c.id)
    summary_record_statement = select(
        QARecord.id.label("record_id"),
        QARecord.conversation_id.label("conversation_id"),
        QARecord.course_id.label("course_id"),
        QARecord.user_id.label("user_id"),
        QARecord.lesson_page_id.label("lesson_page_id"),
        QARecord.question.label("question"),
        QARecord.answer.label("answer"),
        QARecord.attachments.label("attachments"),
        QARecord.created_at.label("created_at"),
        QARecord.updated_at.label("updated_at"),
        func.row_number()
        .over(
            partition_by=QARecord.conversation_id,
            order_by=[QARecord.created_at.desc(), QARecord.id.desc()],
        )
        .label("row_number"),
    ).where(QARecord.user_id == user.id, QARecord.conversation_id.in_(conversation_id_select))
    if lesson_page_ids is not None:
        summary_record_statement = summary_record_statement.where(QARecord.lesson_page_id.in_(lesson_page_ids))
    summary_records = summary_record_statement.subquery()
    counts = (
        select(
            QARecord.conversation_id.label("conversation_id"),
            func.count(QARecord.id).label("record_count"),
            func.max(case((QARecord.is_favorite.is_(True), 1), else_=0)).label("favorite_count"),
        )
        .where(QARecord.user_id == user.id, QARecord.conversation_id.in_(conversation_id_select))
        .group_by(QARecord.conversation_id)
        .subquery()
    )
    rows = db.execute(
        select(
            QAConversation.id.label("conversation_id"),
            QAConversation.course_id.label("conversation_course_id"),
            QAConversation.user_id.label("conversation_user_id"),
            QAConversation.title.label("title"),
            summary_records.c.record_id,
            summary_records.c.course_id,
            summary_records.c.user_id,
            summary_records.c.lesson_page_id,
            summary_records.c.question,
            summary_records.c.answer,
            summary_records.c.attachments,
            summary_records.c.created_at,
            summary_records.c.updated_at,
            counts.c.record_count,
            counts.c.favorite_count,
        )
        .join(summary_records, summary_records.c.conversation_id == QAConversation.id)
        .join(counts, counts.c.conversation_id == QAConversation.id)
        .where(QAConversation.id.in_(conversation_id_select), summary_records.c.row_number == 1)
        .order_by(summary_records.c.created_at.desc(), summary_records.c.record_id.desc())
    )
    items: list[dict] = []
    for row in rows:
        answer = str(row.answer or "").strip()
        items.append(
            {
                "id": int(row.record_id),
                "conversation_id": int(row.conversation_id),
                "course_id": int(row.course_id or row.conversation_course_id),
                "user_id": int(row.user_id or row.conversation_user_id),
                "title": row.title or row.question[:30],
                "question": row.question,
                "answer_preview": answer[:160],
                "lesson_page_id": row.lesson_page_id,
                "attachments": row.attachments or [],
                "is_favorite": bool(row.favorite_count),
                "record_count": int(row.record_count or 0),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )
    return items


def list_conversation_records(db: Session, *, user: User, conversation_id: int) -> list[QARecord]:
    conversation = db.scalar(
        select(QAConversation).where(QAConversation.id == conversation_id, QAConversation.user_id == user.id)
    )
    if conversation is None:
        raise not_found("问答对话不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=conversation.course_id, user=user)
    return list(
        db.scalars(
            select(QARecord)
            .where(QARecord.conversation_id == conversation_id, QARecord.user_id == user.id)
            .order_by(QARecord.created_at.asc(), QARecord.id.asc())
        )
    )


def update_favorite(db: Session, *, record_id: int, user: User, is_favorite: bool) -> QARecord:
    record = db.scalar(select(QARecord).where(QARecord.id == record_id, QARecord.user_id == user.id))
    if record is None:
        raise not_found("问答记录不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=record.course_id, user=user)
    record.is_favorite = is_favorite
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_feedback(db: Session, *, record_id: int, user: User, feedback: str, feedback_comment: str | None) -> QARecord:
    if feedback not in {item.value for item in QAFeedback}:
        raise bad_request("反馈值不合法")
    record = db.scalar(select(QARecord).where(QARecord.id == record_id, QARecord.user_id == user.id))
    if record is None:
        raise not_found("问答记录不存在")
    if user.role == UserRole.STUDENT.value:
        _assert_student_course_access(db, course_id=record.course_id, user=user)
    record.feedback = feedback
    record.feedback_comment = feedback_comment
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
