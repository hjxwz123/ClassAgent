from __future__ import annotations

import ast
import base64
import binascii
import hashlib
import html
import json
import mimetypes
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import MaterialType
from app.core.errors import bad_request
from app.services.runtime_config import RuntimeServiceConfig, get_enabled_service_config
from app.services.storage import storage_service


SERVICE_TYPE = "doc_parser"
DEFAULT_ENDPOINT = "docmind-api.cn-hangzhou.aliyuncs.com"
DEFAULT_REGION = "cn-hangzhou"
DEFAULT_LAYOUT_STEP_SIZE = 100
SUPPORTED_MATERIAL_TYPES = {MaterialType.PPTX.value, MaterialType.PDF.value, MaterialType.DOCX.value, MaterialType.TXT.value}
MARKDOWN_IMAGE_URL_PATTERN = re.compile(
    r"!\[(?P<alt>[^\]]*)]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^)\s]+))(?:\s+['\"][^'\"]*['\"])?\s*\)"
)
HTML_IMAGE_URL_PATTERN = re.compile(r"""<img\b[^>]*\bsrc=["'](?P<src>[^"']+)["'][^>]*>""", re.IGNORECASE)
DATA_IMAGE_PATTERN = re.compile(r"^data:(?P<mime>image/[a-z0-9.+-]+);base64,(?P<data>.+)$", re.IGNORECASE | re.DOTALL)
MAX_MARKDOWN_IMAGE_BYTES = 15 * 1024 * 1024
SIGNED_IMAGE_QUERY_KEYS = {"Expires", "OSSAccessKeyId", "Signature", "security-token", "x-oss-security-token"}
IMAGE_FILENAME_ALT_PATTERN = re.compile(r"^[A-Fa-f0-9_-]{12,}\.(?:png|jpe?g|gif|webp|bmp|svg)$", re.IGNORECASE)


def _normalize_page(title: str | None, content: str, page_number: int) -> dict:
    clean_content = content.strip()
    return {
        "page_number": page_number,
        "page_title": title.strip() if title else None,
        "page_text": clean_content or "本页未提取到有效文字内容。",
    }


def _to_plain_data(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_map"):
        return value.to_map()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
        return {"text": text}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    return value


def _read_value(value: Any, *keys: str) -> Any:
    if value is None:
        return None
    for key in keys:
        if isinstance(value, dict):
            for candidate in {key, key[:1].upper() + key[1:], key[:1].lower() + key[1:]}:
                if candidate in value:
                    return value[candidate]
        if hasattr(value, key):
            return getattr(value, key)
    return None


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "启用", "是"}


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _api_error_message(body: Any) -> str | None:
    data = _to_plain_data(body)
    if not isinstance(data, dict):
        return None
    code = data.get("Code") or data.get("code")
    if code is None:
        return None
    if str(code).lower() in {"200", "ok", "success"}:
        return None
    return str(data.get("Message") or data.get("message") or code)


def _output_formats(value: Any) -> list[str] | None:
    if value is None or value == "":
        return ["markdown"]
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [str(value).strip()]
    formats = [item for item in items if item]
    return formats or None


TEXT_PAYLOAD_KEYS = ("markdownContent", "markdown_content", "llmResult", "llm_result", "page_text", "script_text", "content", "text")


def _decode_serialized_payload(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            decoded = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return text
        return decoded if isinstance(decoded, (dict, list, str)) else text


def _extract_serialized_text_values(value: str) -> str:
    key_pattern = re.compile(r"['\"](?:" + "|".join(TEXT_PAYLOAD_KEYS) + r")['\"]\s*:\s*")
    pieces: list[str] = []
    cursor = 0
    while True:
        match = key_pattern.search(value, cursor)
        if match is None:
            break
        cursor = match.end()
        while cursor < len(value) and value[cursor].isspace():
            cursor += 1
        if cursor >= len(value) or value[cursor] not in {"'", '"'}:
            continue
        quote = value[cursor]
        cursor += 1
        raw = ""
        escaped = False
        while cursor < len(value):
            char = value[cursor]
            cursor += 1
            if escaped:
                raw += f"\\{char}"
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                if raw.strip():
                    pieces.append(raw)
                break
            raw += char
        if escaped and raw.strip():
            pieces.append(f"{raw}\\")
    return "\n\n".join(pieces)


def _extract_text_payload(value: Any) -> str:
    value = _decode_serialized_payload(value)
    if value is None:
        return ""
    if hasattr(value, "to_map"):
        value = value.to_map()
    if isinstance(value, str):
        extracted = _extract_serialized_text_values(value) if value.lstrip().startswith(("{", "[")) else ""
        text = extracted or value
        return text.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"').strip()
    if isinstance(value, list):
        pieces = [_extract_text_payload(item) for item in value]
        return "\n\n".join(piece for piece in pieces if piece)
    if isinstance(value, dict):
        blocks = value.get("blocks")
        if isinstance(blocks, list):
            pieces = [_extract_text_payload(block) for block in blocks]
            text = "\n".join(piece for piece in pieces if piece)
            if text:
                return text
        for key in TEXT_PAYLOAD_KEYS:
            if key in value:
                text = _extract_text_payload(value.get(key))
                if text:
                    return text
        pieces = [_extract_text_payload(item) for item in value.values()]
        return "\n\n".join(piece for piece in pieces if piece)
    return str(value).strip()


def _layout_text(layout: dict) -> str:
    for key in TEXT_PAYLOAD_KEYS:
        if key in layout:
            text = _extract_text_payload(layout.get(key))
            if text:
                return text
    return _extract_text_payload(layout.get("blocks"))


def _layout_title(layout: dict, fallback: str | None = None) -> str | None:
    text = str(layout.get("text") or fallback or "").strip()
    if not text:
        content = _layout_text(layout)
        text = content.splitlines()[0].strip("# ").strip() if content else ""
    return text[:120] or None


def _markdown_image_urls(content: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for pattern in (MARKDOWN_IMAGE_URL_PATTERN, HTML_IMAGE_URL_PATTERN):
        for match in pattern.finditer(content):
            raw = match.groupdict().get("angle") or match.groupdict().get("plain") or match.groupdict().get("src")
            if not raw:
                continue
            value = raw.strip()
            if value and value not in seen:
                urls.append(value)
                seen.add(value)
    return urls


def _is_remote_url(value: str) -> bool:
    try:
        parsed = urlsplit(html.unescape(value))
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_temporary_docmind_url(value: str) -> bool:
    try:
        parsed = urlsplit(html.unescape(value))
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    query = parse_qs(parsed.query)
    return bool(SIGNED_IMAGE_QUERY_KEYS.intersection(query))


def _local_docmind_image_url(value: str) -> str | None:
    try:
        parsed = urlsplit(html.unescape(value))
    except ValueError:
        return None
    path = parsed.path.lstrip("/")
    marker = "docmind_images/"
    if marker not in path:
        return None
    relative_path = path[path.index(marker) :]
    if not relative_path:
        return None
    if not storage_service.absolute_path(relative_path).is_file():
        return None
    return storage_service.normalize_public_url(storage_service.local_public_url(relative_path))


def _image_suffix(url: str, content_type: str | None) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
        return suffix
    mime = str(content_type or "").split(";", 1)[0].strip().lower()
    guessed = mimetypes.guess_extension(mime) if mime else None
    if guessed == ".jpe":
        return ".jpg"
    return guessed if guessed in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"} else ".png"


def _persist_data_image(url: str, *, db: Session | None, cache: dict[str, str | None]) -> str | None:
    data_url = html.unescape(url).strip()
    if data_url in cache:
        return cache[data_url]
    cache[data_url] = None
    match = DATA_IMAGE_PATTERN.match(data_url)
    if match is None:
        return None
    try:
        content = base64.b64decode(match.group("data"), validate=True)
    except (binascii.Error, ValueError):
        return None
    if not content or len(content) > MAX_MARKDOWN_IMAGE_BYTES:
        return None
    digest = hashlib.sha256(content).hexdigest()
    suffix = _image_suffix(f"image.{match.group('mime').split('/', 1)[1]}", match.group("mime"))
    relative_path = storage_service.save_bytes(
        content,
        folder=f"docmind_images/{digest[:2]}",
        filename=f"{digest}{suffix}",
        db=db,
    )
    public_url = storage_service.public_url(relative_path, db=db)
    cache[data_url] = public_url
    return public_url


def _persist_markdown_image(
    client: httpx.Client,
    url: str,
    *,
    db: Session | None,
    cache: dict[str, str | None],
) -> str | None:
    download_url = html.unescape(url)
    if DATA_IMAGE_PATTERN.match(download_url.strip()):
        return _persist_data_image(download_url, db=db, cache=cache)
    if download_url in cache:
        return cache[download_url]
    cache[download_url] = None
    if not _is_remote_url(download_url):
        return None
    try:
        response = client.get(download_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    content_type = response.headers.get("content-type", "")
    content = response.content
    if not content or len(content) > MAX_MARKDOWN_IMAGE_BYTES:
        return None
    mime = content_type.split(";", 1)[0].strip().lower()
    if not mime.startswith("image/"):
        suffix = Path(urlsplit(download_url).path).suffix.lower()
        if mime and mime not in {"application/octet-stream", "binary/octet-stream"}:
            return None
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
            return None
    digest = hashlib.sha256(download_url.encode("utf-8")).hexdigest()
    suffix = _image_suffix(download_url, content_type)
    relative_path = storage_service.save_bytes(
        content,
        folder=f"docmind_images/{digest[:2]}",
        filename=f"{digest}{suffix}",
        db=db,
    )
    public_url = storage_service.public_url(relative_path, db=db)
    cache[download_url] = public_url
    return public_url


def _same_image_url(left: str | None, right: str) -> bool:
    if not left:
        return False
    return html.unescape(left).strip() == html.unescape(right).strip()


def _strip_unavailable_image(content: str, raw_url: str) -> str:
    placeholder = "（图片未能保存，请重新解析资料）"

    def display_alt(alt: str) -> str:
        clean = html.unescape(alt).strip()
        if IMAGE_FILENAME_ALT_PATTERN.fullmatch(clean):
            return ""
        return clean

    def replace_markdown(match: re.Match[str]) -> str:
        url = match.groupdict().get("angle") or match.groupdict().get("plain")
        if not _same_image_url(url, raw_url):
            return match.group(0)
        alt = display_alt(match.groupdict().get("alt") or "")
        return alt or placeholder

    def replace_html(match: re.Match[str]) -> str:
        if not _same_image_url(match.groupdict().get("src"), raw_url):
            return match.group(0)
        alt_match = re.search(r"""\balt=["'](?P<alt>[^"']+)["']""", match.group(0), flags=re.IGNORECASE)
        alt = display_alt(alt_match.group("alt") if alt_match else "")
        return alt or placeholder

    return HTML_IMAGE_URL_PATTERN.sub(replace_html, MARKDOWN_IMAGE_URL_PATTERN.sub(replace_markdown, content))


def _replace_image_url(content: str, raw_url: str, new_url: str) -> str:
    def display_alt(alt: str) -> str:
        clean = html.unescape(alt).strip()
        return "课件图片" if IMAGE_FILENAME_ALT_PATTERN.fullmatch(clean) else clean

    def replace_markdown(match: re.Match[str]) -> str:
        url = match.groupdict().get("angle") or match.groupdict().get("plain")
        if not _same_image_url(url, raw_url):
            return match.group(0)
        alt = display_alt(match.groupdict().get("alt") or "")
        return f"![{alt}]({new_url})"

    def replace_html(match: re.Match[str]) -> str:
        if not _same_image_url(match.groupdict().get("src"), raw_url):
            return match.group(0)
        updated = match.group(0).replace(match.groupdict().get("src") or "", new_url)
        alt_match = re.search(r"""\balt=["'](?P<alt>[^"']*)["']""", updated, flags=re.IGNORECASE)
        if alt_match and IMAGE_FILENAME_ALT_PATTERN.fullmatch(html.unescape(alt_match.group("alt")).strip()):
            updated = updated[: alt_match.start("alt")] + "课件图片" + updated[alt_match.end("alt") :]
        return updated

    return HTML_IMAGE_URL_PATTERN.sub(replace_html, MARKDOWN_IMAGE_URL_PATTERN.sub(replace_markdown, content))


def _localize_markdown_images(content: str, db: Session | None, cache: dict[str, str | None]) -> str:
    urls = _markdown_image_urls(content)
    if not urls:
        return content
    rewritten = content
    with httpx.Client(
        timeout=httpx.Timeout(20.0, connect=8.0),
        follow_redirects=True,
        headers={"User-Agent": "class-agent-doc-parser/1.0"},
    ) as client:
        for raw_url in urls:
            public_url = _persist_markdown_image(client, raw_url, db=db, cache=cache)
            if not public_url:
                if _is_temporary_docmind_url(raw_url):
                    rewritten = _strip_unavailable_image(rewritten, raw_url)
                continue
            rewritten = _replace_image_url(rewritten, raw_url, public_url)
    return rewritten


def sanitize_temporary_docmind_images(content: str | None) -> str | None:
    if not content:
        return content
    rewritten = str(content)
    for raw_url in _markdown_image_urls(rewritten):
        if _is_temporary_docmind_url(raw_url):
            rewritten = _strip_unavailable_image(rewritten, raw_url)
            continue
        local_url = _local_docmind_image_url(raw_url)
        if local_url and local_url != raw_url:
            rewritten = _replace_image_url(rewritten, raw_url, local_url)
        elif "docmind_images/" in html.unescape(raw_url):
            rewritten = _replace_image_url(rewritten, raw_url, raw_url)
    return rewritten


class DocParserService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self, config: dict):
        required = ["access_key_id", "access_key_secret"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"文档解析配置缺少字段: {', '.join(missing)}")
        try:
            from alibabacloud_docmind_api20220711.client import Client as DocMindClient
            from alibabacloud_tea_openapi import models as openapi_models
        except ImportError as exc:
            raise RuntimeError("缺少阿里云文档解析 SDK 依赖") from exc

        return DocMindClient(
            openapi_models.Config(
                access_key_id=config["access_key_id"],
                access_key_secret=config["access_key_secret"],
                endpoint=DEFAULT_ENDPOINT,
                region_id=str(config.get("region") or DEFAULT_REGION),
                type="access_key",
                connect_timeout=int(self.settings.external_service_timeout_seconds * 1000),
                read_timeout=int(self.settings.external_service_timeout_seconds * 1000),
            )
        )

    def _runtime_options(self):
        from alibabacloud_tea_util import models as util_models

        return util_models.RuntimeOptions(
            connect_timeout=int(self.settings.external_service_timeout_seconds * 1000),
            read_timeout=int(self.settings.external_service_timeout_seconds * 1000),
        )

    def _submit_job(self, path: Path, filename: str, config: dict) -> str:
        try:
            from alibabacloud_docmind_api20220711 import models as docmind_models
        except ImportError as exc:
            raise RuntimeError("缺少阿里云文档解析 SDK 依赖") from exc

        extension = (Path(filename).suffix or path.suffix).lower().lstrip(".")
        if not extension:
            raise bad_request("文档解析需要文件后缀")
        llm_enhancement = _as_bool(config.get("llm_enhancement"), True) or _as_bool(config.get("output_html_table"), False)
        request = docmind_models.SubmitDocParserJobAdvanceRequest(
            file_name=filename,
            file_name_extension=extension,
            formula_enhancement=_as_bool(config.get("formula_enhancement"), False),
            llm_enhancement=llm_enhancement,
            output_html_table=_as_bool(config.get("output_html_table"), False),
            output_format=_output_formats(config.get("output_format")),
            page_index=str(config.get("page_index")).strip() if config.get("page_index") else None,
        )
        if llm_enhancement and config.get("enhancement_mode", "VLM"):
            request.enhancement_mode = str(config.get("enhancement_mode") or "VLM")
        with path.open("rb") as file_object:
            request.file_url_object = file_object
            response = self._client(config).submit_doc_parser_job_advance(request, self._runtime_options())
        if error_message := _api_error_message(response.body):
            raise bad_request(f"文档解析任务提交失败: {error_message}")
        data = _read_value(response.body, "data") if response.body else None
        task_id = _read_value(data, "id")
        if not task_id:
            body = response.body.to_map() if response.body and hasattr(response.body, "to_map") else {}
            raise bad_request(f"文档解析任务提交失败: {body.get('Message') or body.get('message') or '未返回任务 ID'}")
        return str(task_id)

    def _query_status(self, task_id: str, config: dict) -> dict:
        from alibabacloud_docmind_api20220711 import models as docmind_models

        request = docmind_models.QueryDocParserStatusRequest(id=task_id)
        response = self._client(config).query_doc_parser_status(request)
        if error_message := _api_error_message(response.body):
            raise bad_request(f"文档解析状态查询失败: {error_message}")
        body = _to_plain_data(response.body)
        data = _to_plain_data(_read_value(response.body, "data")) if response.body else None
        if isinstance(data, dict):
            return data
        if isinstance(body, dict):
            return body.get("Data") or body.get("data") or body
        return {}

    def _wait_for_success(self, task_id: str, config: dict) -> dict:
        timeout_seconds = _bounded_int(config.get("timeout_seconds") or config.get("timeout"), default=600, minimum=30, maximum=7200)
        poll_interval = _bounded_int(config.get("poll_interval_seconds"), default=5, minimum=1, maximum=60)
        deadline = time.monotonic() + timeout_seconds
        last_status: dict = {}
        while time.monotonic() < deadline:
            last_status = self._query_status(task_id, config)
            status = str(last_status.get("Status") or last_status.get("status") or "").lower()
            if status == "success":
                return last_status
            if status in {"fail", "failed"}:
                message = last_status.get("Message") or last_status.get("message") or last_status.get("Code") or "处理失败"
                raise bad_request(f"文档解析失败: {message}")
            time.sleep(poll_interval)
        progress = last_status.get("Processing") or last_status.get("processing") or 0
        raise bad_request(f"文档解析超时，当前进度 {progress}%")

    def _get_result_batch(self, task_id: str, config: dict, layout_num: int, step_size: int) -> list[dict]:
        from alibabacloud_docmind_api20220711 import models as docmind_models

        request = docmind_models.GetDocParserResultRequest(
            id=task_id,
            layout_num=layout_num,
            layout_step_size=step_size,
        )
        response = self._client(config).get_doc_parser_result(request)
        if error_message := _api_error_message(response.body):
            raise bad_request(f"文档解析结果获取失败: {error_message}")
        data = _to_plain_data(_read_value(response.body, "data")) if response.body else {}
        if isinstance(data, dict):
            layouts = data.get("layouts") or data.get("Layouts") or []
        else:
            layouts = []
        if not isinstance(layouts, list):
            raise bad_request("文档解析结果格式异常")
        return [layout for layout in layouts if isinstance(layout, dict)]

    def _collect_layouts(self, task_id: str, config: dict) -> list[dict]:
        step_size = _bounded_int(
            config.get("layout_step_size"),
            default=DEFAULT_LAYOUT_STEP_SIZE,
            minimum=1,
            maximum=3000,
        )
        layouts: list[dict] = []
        layout_num = 0
        while True:
            batch = self._get_result_batch(task_id, config, layout_num, step_size)
            if not batch:
                break
            layouts.extend(batch)
            layout_num += len(batch)
            if len(batch) < step_size:
                break
        return layouts

    def _pages_from_layouts(self, layouts: list[dict]) -> list[dict]:
        grouped: dict[int, list[dict]] = defaultdict(list)
        for index, layout in enumerate(layouts):
            raw_page = layout.get("pageNum", layout.get("page_num", layout.get("pageNumber", 0)))
            try:
                page_number = int(raw_page) + 1
            except (TypeError, ValueError):
                page_number = 1
            layout["_fallback_order"] = index
            grouped[page_number].append(layout)

        pages: list[dict] = []
        for page_number in sorted(grouped):
            page_layouts = sorted(grouped[page_number], key=lambda item: _safe_int(item.get("index"), item["_fallback_order"]))
            pieces = [piece for piece in (_layout_text(layout) for layout in page_layouts) if piece]
            title = None
            for layout in page_layouts:
                if str(layout.get("type", "")).lower() == "title":
                    title = _layout_title(layout)
                    break
            pages.append(_normalize_page(title or f"第{page_number}页", "\n\n".join(pieces), page_number))
        return pages

    def _mock_pages(self, material_type: str, service: RuntimeServiceConfig) -> list[dict]:
        config = service.config
        configured_pages = config.get("mock_pages_by_type", {}).get(material_type) if isinstance(config.get("mock_pages_by_type"), dict) else None
        configured_pages = configured_pages or config.get("mock_pages")
        if isinstance(configured_pages, list) and configured_pages:
            pages = []
            for index, page in enumerate(configured_pages, start=1):
                if isinstance(page, dict):
                    pages.append(
                        _normalize_page(
                            str(page.get("page_title") or page.get("title") or f"第{index}页"),
                            str(page.get("page_text") or page.get("content") or page.get("text") or ""),
                            _safe_int(page.get("page_number"), index),
                        )
                    )
                else:
                    pages.append(_normalize_page(f"第{index}页", str(page), index))
            return pages

        default_counts = {MaterialType.PPTX.value: 2, MaterialType.PDF.value: 1, MaterialType.DOCX.value: 1, MaterialType.TXT.value: 2}
        counts = config.get("mock_page_counts") if isinstance(config.get("mock_page_counts"), dict) else {}
        count = _bounded_int(counts.get(material_type), default=default_counts.get(material_type, 1), minimum=1, maximum=20)
        default_text = (
            "极限定义\n极限描述函数在某点附近的变化趋势。\n矩阵可以表示线性变换。\n"
            "连续函数在区间内没有跳跃。行列式反映缩放系数。"
        )
        text = str(config.get("mock_text") or default_text)
        return [_normalize_page(f"模拟解析第{index}页", text, index) for index in range(1, count + 1)]

    def parse(self, path: Path, material_type: str, db: Session | None, filename: str | None = None) -> list[dict]:
        if material_type not in SUPPORTED_MATERIAL_TYPES:
            raise bad_request("暂不支持该资料类型解析")
        service = get_enabled_service_config(db, SERVICE_TYPE)
        if service is None:
            raise bad_request("文档解析服务未配置，请先在管理员后台配置阿里云文档解析服务")
        if service.provider == "mock":
            if self.settings.app_env == "production":
                raise bad_request("生产环境不允许使用 Mock 文档解析服务")
            return self._mock_pages(material_type, service)
        if service.provider != "aliyun":
            raise bad_request(f"暂不支持的文档解析服务提供方: {service.provider}")

        task_id = self._submit_job(path, filename or path.name, service.config)
        self._wait_for_success(task_id, service.config)
        pages = self._pages_from_layouts(self._collect_layouts(task_id, service.config))
        image_cache: dict[str, str | None] = {}
        for page in pages:
            page["page_text"] = _localize_markdown_images(page.get("page_text") or "", db, image_cache)
        if not pages:
            raise bad_request("文档解析未返回有效内容")
        return pages


doc_parser_service = DocParserService()


def parse_material(path: Path, material_type: str, db: Session | None = None, filename: str | None = None) -> list[dict]:
    return doc_parser_service.parse(path, material_type, db, filename=filename)
