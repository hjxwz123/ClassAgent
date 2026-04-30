from pathlib import Path

import fitz
from docx import Document
from pptx import Presentation

from app.core.enums import MaterialType
from app.core.errors import bad_request


def _normalize_page(title: str | None, content: str, page_number: int) -> dict:
    clean_content = content.strip()
    return {
        "page_number": page_number,
        "page_title": title.strip() if title else None,
        "page_text": clean_content or "本页未提取到有效文字内容。",
    }


def parse_pptx(path: Path) -> list[dict]:
    presentation = Presentation(path.as_posix())
    pages: list[dict] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        title = slide.shapes.title.text if slide.shapes.title and slide.shapes.title.text else None
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                parts.append(shape.text)
        pages.append(_normalize_page(title, "\n".join(parts), index))
    return pages


def parse_pdf(path: Path) -> list[dict]:
    pages: list[dict] = []
    document = fitz.open(path.as_posix())
    for index, page in enumerate(document, start=1):
        pages.append(_normalize_page(f"第{index}页", page.get_text("text"), index))
    return pages


def parse_docx(path: Path) -> list[dict]:
    document = Document(path.as_posix())
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    if not paragraphs:
        return [_normalize_page("文档内容", "", 1)]
    grouped: list[dict] = []
    buffer: list[str] = []
    page_number = 1
    for paragraph in paragraphs:
        buffer.append(paragraph)
        if len("\n".join(buffer)) >= 700:
            grouped.append(_normalize_page(f"第{page_number}段", "\n".join(buffer), page_number))
            page_number += 1
            buffer = []
    if buffer:
        grouped.append(_normalize_page(f"第{page_number}段", "\n".join(buffer), page_number))
    return grouped


def parse_txt(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    blocks = [block.strip() for block in content.split("\n\n") if block.strip()]
    if not blocks:
        return [_normalize_page("文本内容", "", 1)]
    return [_normalize_page(f"第{index}段", block, index) for index, block in enumerate(blocks, start=1)]


def parse_material(path: Path, material_type: str) -> list[dict]:
    if material_type == MaterialType.PPTX.value:
        return parse_pptx(path)
    if material_type == MaterialType.PDF.value:
        return parse_pdf(path)
    if material_type == MaterialType.DOCX.value:
        return parse_docx(path)
    if material_type == MaterialType.TXT.value:
        return parse_txt(path)
    raise bad_request("暂不支持该资料类型解析")
