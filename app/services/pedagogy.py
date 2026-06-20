from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, Callable

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db.models import CourseMaterial, Lesson, LessonPage, PedagogyArtifact
from app.services.ai import ai_service
from app.services.parser import _extract_text_payload
from app.services.retrieval import page_numbers_from_query, query_terms, score_text_for_query


ARTIFACT_PAGE_SUMMARY = "page_summary"
ARTIFACT_CHAPTER_OUTLINE = "chapter_outline"
ARTIFACT_CONCEPT_CARD = "concept_card"
ARTIFACT_PROBLEM_TEMPLATE = "problem_template"
ARTIFACT_MISCONCEPTION_CARD = "misconception_card"
ARTIFACT_DISCUSSION_PROMPT = "discussion_prompt"
ARTIFACT_QUICK_CHECK = "quick_check"
ARTIFACT_DEMO = "demo"

CORE_ARTIFACT_TYPES = {
    ARTIFACT_PAGE_SUMMARY,
    ARTIFACT_CHAPTER_OUTLINE,
    ARTIFACT_CONCEPT_CARD,
    ARTIFACT_PROBLEM_TEMPLATE,
    ARTIFACT_MISCONCEPTION_CARD,
    ARTIFACT_DISCUSSION_PROMPT,
    ARTIFACT_QUICK_CHECK,
    ARTIFACT_DEMO,
}

QA_ARTIFACT_TYPES = {
    ARTIFACT_CHAPTER_OUTLINE,
    ARTIFACT_PAGE_SUMMARY,
    ARTIFACT_CONCEPT_CARD,
    ARTIFACT_PROBLEM_TEMPLATE,
    ARTIFACT_MISCONCEPTION_CARD,
    ARTIFACT_DISCUSSION_PROMPT,
    ARTIFACT_QUICK_CHECK,
}

TUTORING_ARTIFACT_TYPES = {
    ARTIFACT_PROBLEM_TEMPLATE,
    ARTIFACT_CONCEPT_CARD,
    ARTIFACT_MISCONCEPTION_CARD,
    ARTIFACT_PAGE_SUMMARY,
}

QUIZ_ARTIFACT_TYPES = {
    ARTIFACT_CHAPTER_OUTLINE,
    ARTIFACT_CONCEPT_CARD,
    ARTIFACT_PROBLEM_TEMPLATE,
    ARTIFACT_MISCONCEPTION_CARD,
    ARTIFACT_PAGE_SUMMARY,
}

ARTIFACT_TYPE_LABELS = {
    ARTIFACT_PAGE_SUMMARY: "页面摘要",
    ARTIFACT_CHAPTER_OUTLINE: "章节大纲",
    ARTIFACT_CONCEPT_CARD: "知识点",
    ARTIFACT_PROBLEM_TEMPLATE: "例题模板",
    ARTIFACT_MISCONCEPTION_CARD: "易错点",
    ARTIFACT_DISCUSSION_PROMPT: "讨论",
    ARTIFACT_QUICK_CHECK: "快问",
    ARTIFACT_DEMO: "演示",
}

SCENE_TYPE_BY_ARTIFACT = {
    ARTIFACT_PAGE_SUMMARY: "explain",
    ARTIFACT_CHAPTER_OUTLINE: "explain",
    ARTIFACT_CONCEPT_CARD: "explain",
    ARTIFACT_PROBLEM_TEMPLATE: "example",
    ARTIFACT_MISCONCEPTION_CARD: "mistake",
    ARTIFACT_DISCUSSION_PROMPT: "discussion",
    ARTIFACT_QUICK_CHECK: "quick_check",
    ARTIFACT_DEMO: "demo",
}

_ARTIFACT_RETRIEVAL_LIMIT = 8
_ARTIFACT_QUERY_STOPWORDS = {
    "课程",
    "资料",
    "内容",
    "知识",
    "问题",
    "题目",
    "这道",
    "这个",
    "明显",
    "没有",
    "没讲过",
    "怎么做",
    "是什么",
    "背景",
}
_NOISE_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*\]\([^)]+\)|https?://\S+|\b\S+\.(?:jpeg|jpg|png|gif|webp|bmp)\b|\b[a-f0-9]{16,}\b",
    flags=re.IGNORECASE,
)
_PROBLEM_INTENT_PATTERN = re.compile(r"题|例|求|解|证明|推导|计算|判断|步骤|方法|模板|变式|思路")
_NON_TEACHING_TITLE_PATTERN = re.compile(
    r"(封面|目录|大纲|课程介绍|教师介绍|教材介绍|参考资料|参考文献|致谢|谢谢|联系方式|课程安排|章节安排|考核方式|学习要求|版权|声明|结束)",
    flags=re.IGNORECASE,
)
_TEACHING_SIGNAL_PATTERN = re.compile(
    r"(定义|定理|性质|公式|证明|推导|算法|步骤|方法|模型|概念|原理|例题|例|计算|求解|应用|分析|比较|分类|结构|流程|规则|条件|结论|矩阵|函数|系统|网络|数据|语法|语义|线性|概率|统计)",
    flags=re.IGNORECASE,
)


def _compact_text(value: Any, *, limit: int | None = None) -> str:
    if value is None:
        return ""
    text = _extract_text_payload(value) if isinstance(value, str) else str(value)
    text = _NOISE_IMAGE_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit is not None and len(text) > limit:
        return text[:limit].rstrip()
    return text


def _listify(value: Any, *, limit: int = 8) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[\n；;]+", value)
    elif isinstance(value, dict):
        items = value.values()
    elif isinstance(value, Iterable):
        items = value
    else:
        items = [value]
    results: list[str] = []
    for item in items:
        text = _compact_text(item, limit=260)
        if text and text not in results:
            results.append(text)
        if len(results) >= limit:
            break
    return results


def _flatten_payload(value: Any, *, limit: int = 1600) -> str:
    pieces: list[str] = []

    def walk(item: Any) -> None:
        if item is None or len("\n".join(pieces)) >= limit:
            return
        if isinstance(item, dict):
            for key, val in item.items():
                if key in {"image", "image_url", "url"}:
                    continue
                if isinstance(val, (dict, list, tuple)):
                    walk(val)
                else:
                    text = _compact_text(val, limit=220)
                    if text:
                        pieces.append(f"{key}: {text}")
            return
        if isinstance(item, (list, tuple, set)):
            for val in item:
                walk(val)
            return
        text = _compact_text(item, limit=220)
        if text:
            pieces.append(text)

    walk(value)
    return "\n".join(dict.fromkeys(pieces))[:limit]


def _first(items: Sequence[str], fallback: str) -> str:
    return next((item for item in items if item), fallback)


def _artifact_title(base: str, suffix: str, *, limit: int = 120) -> str:
    title = _compact_text(f"{base}{suffix}", limit=limit)
    return title or suffix.strip("：") or "教学对象"


def _fallback_page_payload(*, page: LessonPage, lesson: Lesson) -> dict[str, Any]:
    raw_text = _compact_text(page.page_text, limit=2200)
    title = page.page_title or f"{lesson.title} 第{page.page_number}页"
    keywords = [item for item in ai_service.extract_keywords(raw_text or title, limit=8) if item != "课程内容"]
    if not keywords:
        keywords = [title]
    summary = raw_text[:220] if raw_text else f"{title} 暂无可提取正文，可结合教师讲解继续补充。"
    main = keywords[0]
    return {
        "page_summary": summary,
        "learning_objectives": [f"理解 {main} 的含义、条件和应用位置"],
        "key_points": keywords[:5],
        "knowledge_points": keywords[:5],
        "misconceptions": [
            {
                "title": f"{main} 的适用前提",
                "description": f"容易只记住结论，忽略 {main} 使用时需要满足的条件和上下文。",
                "correction": "先判断题目或材料是否满足前提，再套用方法。",
            }
        ],
        "problem_templates": [
            {
                "name": f"{main} 应用题型",
                "conditions": ["题干给出对象、条件或现象，需要判断适用的概念、规则或步骤"],
                "steps": ["识别考查对象", "列出已知条件和目标", "选择对应概念或方法", "按步骤推理并回看限制条件"],
                "mistakes": ["没有先判断条件是否匹配", "把具体例子当作固定答案"],
                "variable_slots": ["对象", "条件", "目标", "参数或符号"],
                "transfer_prompt": f"如果题目换成新的对象或数值，仍先判断是否考查 {main}，再迁移同一套步骤。",
            }
        ],
        "prerequisites": keywords[1:4],
        "quick_checks": [f"{main} 的适用条件是什么？", f"遇到同类问题时第一步应判断什么？"],
        "discussion_prompts": [f"请举一个与 {main} 同结构但条件变化的例子，并说明步骤是否变化。"],
        "demo_ideas": [f"用一个小例子演示 {main} 从条件识别到结论形成的过程。"],
    }


def _payload_says_non_teaching(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in ("is_teaching_page", "activity_applicable", "has_teaching_content", "should_generate_activity"):
        if key in payload and payload.get(key) is False:
            return True
    return False


def _payload_is_degraded(payload: Any) -> bool:
    """AI 教学结构生成在模型不可用/调用失败时回退到关键词模板，会带 _degraded sentinel。"""
    return isinstance(payload, dict) and bool(payload.get("_degraded"))


def _is_teachable_page(page: LessonPage, lesson: Lesson, payload: Any | None = None) -> bool:
    if _payload_says_non_teaching(payload):
        return False
    title = _compact_text(page.page_title or "", limit=120)
    page_text = _compact_text(page.page_text, limit=1600)
    script_text = _compact_text(page.script_text, limit=800)
    combined = " ".join(part for part in [title, page_text, script_text] if part).strip()
    if not combined:
        return False
    title_is_non_teaching = bool(title and _NON_TEACHING_TITLE_PATTERN.search(title))
    has_teaching_signal = bool(_TEACHING_SIGNAL_PATTERN.search(combined))
    if len(combined) < 60 and not has_teaching_signal:
        return False
    if title_is_non_teaching and (len(combined) < 420 or not has_teaching_signal):
        return False
    if len(combined) < 120 and not has_teaching_signal:
        return False
    administrative_hits = len(
        re.findall(r"(上课时间|办公室|邮箱|成绩|考勤|迟到|请假|教材|参考书|二维码|扫码|课程群|联系电话|答疑时间)", combined)
    )
    if administrative_hits >= 2 and not has_teaching_signal:
        return False
    return True


def _normalize_page_payload(payload: Any, *, page: LessonPage, lesson: Lesson) -> dict[str, Any]:
    fallback = _fallback_page_payload(page=page, lesson=lesson)
    if not isinstance(payload, dict):
        return fallback
    normalized = {**fallback, **payload}
    normalized["page_summary"] = _compact_text(normalized.get("page_summary"), limit=420) or fallback["page_summary"]
    for key in ("learning_objectives", "key_points", "knowledge_points", "prerequisites", "quick_checks", "discussion_prompts", "demo_ideas"):
        values = _listify(normalized.get(key), limit=8)
        normalized[key] = values or fallback[key]
    normalized["misconceptions"] = _normalize_dict_items(
        normalized.get("misconceptions"),
        fallback=fallback["misconceptions"],
        title_key="title",
        content_keys=("description", "correction", "mistake"),
        limit=4,
    )
    normalized["problem_templates"] = _normalize_dict_items(
        normalized.get("problem_templates"),
        fallback=fallback["problem_templates"],
        title_key="name",
        content_keys=("conditions", "steps", "mistakes", "variable_slots", "transfer_prompt"),
        limit=3,
    )
    return normalized


def _normalize_dict_items(
    value: Any,
    *,
    fallback: list[dict[str, Any]],
    title_key: str,
    content_keys: tuple[str, ...],
    limit: int,
) -> list[dict[str, Any]]:
    if value is None:
        return fallback[:limit]
    raw_items = value if isinstance(value, list) else [value]
    results: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            title = _compact_text(item.get(title_key) or item.get("title") or item.get("name"), limit=120)
            payload = dict(item)
        else:
            title = _compact_text(item, limit=120)
            payload = {title_key: title, "description": title}
        if not title:
            title = f"教学对象{len(results) + 1}"
        content_parts = []
        for key in content_keys:
            if key in payload:
                text = _flatten_payload(payload.get(key), limit=500)
                if text:
                    content_parts.append(f"{key}: {text}")
        if not content_parts:
            content_parts.append(_flatten_payload(payload, limit=500))
        payload[title_key] = title
        results.append({**payload, "_content": "\n".join(part for part in content_parts if part)})
        if len(results) >= limit:
            break
    return results or fallback[:limit]


def _base_payload(
    *,
    material: CourseMaterial,
    lesson: Lesson,
    page: LessonPage | None,
    scene_type: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scene_type": scene_type,
        "course_id": material.course_id,
        "material_id": material.id,
        "material_title": material.title,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "chapter_id": material.chapter_id,
    }
    if page is not None:
        payload.update(
            {
                "lesson_page_id": page.id,
                "page_number": page.page_number,
                "page_title": page.page_title,
            }
        )
    if extra:
        payload.update(extra)
    return payload


def _new_artifact(
    *,
    material: CourseMaterial,
    lesson: Lesson,
    page: LessonPage | None,
    artifact_type: str,
    title: str,
    content: str,
    order_index: int,
    summary: str | None = None,
    keywords: list[str] | None = None,
    payload: dict[str, Any] | None = None,
    degraded: bool = False,
) -> PedagogyArtifact:
    scene_type = SCENE_TYPE_BY_ARTIFACT.get(artifact_type, "explain")
    extra = dict(payload or {})
    if degraded:
        # 模型不可用/调用失败时用模板兜底产生的制品：显式标记，避免被 QA/出题当作真实 AI 产物。
        extra["degraded"] = True
        extra["source"] = "template"
    return PedagogyArtifact(
        course_id=material.course_id,
        material_id=material.id,
        lesson_id=lesson.id,
        lesson_page_id=page.id if page is not None else None,
        chapter_id=material.chapter_id,
        artifact_type=artifact_type,
        title=_compact_text(title, limit=255) or ARTIFACT_TYPE_LABELS.get(artifact_type, "教学对象"),
        summary=_compact_text(summary, limit=500) if summary else None,
        content=_compact_text(content, limit=3000) or _compact_text(title, limit=500) or "可结合课程资料进一步补充。",
        keywords=keywords or None,
        payload=_base_payload(material=material, lesson=lesson, page=page, scene_type=scene_type, extra=extra),
        order_index=order_index,
    )


def _page_artifacts(
    *,
    db: Session,
    material: CourseMaterial,
    lesson: Lesson,
    page: LessonPage,
    order_base: int,
    use_ai: bool = True,
    warnings: list[str] | None = None,
) -> list[PedagogyArtifact]:
    if not _is_teachable_page(page, lesson):
        return []
    raw_payload: dict[str, Any] | None = None
    if use_ai:
        raw_payload = ai_service.generate_pedagogy_artifacts(
            material_title=material.title,
            lesson_title=lesson.title,
            page_title=page.page_title,
            page_number=page.page_number,
            page_text=page.page_text,
            script_text=page.script_text,
            db=db,
        )
    if _payload_says_non_teaching(raw_payload):
        return []
    # 模型不可用/调用失败时 AI 层会回退关键词模板并带 _degraded；纯模板补齐(use_ai=False)同样不是真实 AI 产物。
    degraded = (not use_ai) or _payload_is_degraded(raw_payload)
    if degraded and warnings is not None:
        page_label = page.page_title or f"第{page.page_number}页"
        if use_ai:
            reason = _compact_text((raw_payload or {}).get("_degraded_reason"), limit=160) or "模型未配置或调用失败"
            warnings.append(f"第{page.page_number}页（{page_label}）教学结构降级为模板：{reason}")
        else:
            warnings.append(f"第{page.page_number}页（{page_label}）教学结构以模板补齐，未走 AI 生成")
    payload = _normalize_page_payload(
        raw_payload,
        page=page,
        lesson=lesson,
    )
    page_title = page.page_title or f"第{page.page_number}页"
    keywords = list(dict.fromkeys([*payload["knowledge_points"], *payload["key_points"]]))[:10]
    artifacts: list[PedagogyArtifact] = [
        _new_artifact(
            material=material,
            lesson=lesson,
            page=page,
            artifact_type=ARTIFACT_PAGE_SUMMARY,
            title=_artifact_title(page_title, "：页面摘要"),
            summary=payload["page_summary"],
            content="\n".join(
                [
                    f"页面摘要：{payload['page_summary']}",
                    f"学习目标：{'；'.join(payload['learning_objectives'])}",
                    f"重点：{'；'.join(payload['key_points'])}",
                    f"前置关系：{'；'.join(payload['prerequisites']) or '无'}",
                ]
            ),
            keywords=keywords,
            payload={
                "learning_objectives": payload["learning_objectives"],
                "key_points": payload["key_points"],
                "prerequisites": payload["prerequisites"],
            },
            order_index=order_base,
        )
    ]
    order = order_base + 1
    for point in payload["knowledge_points"][:5]:
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_CONCEPT_CARD,
                title=_artifact_title(point, "：知识点"),
                summary=f"{point} 是本页需要掌握的知识点。",
                content=f"知识点：{point}\n相关页面：{page_title}\n学习目标：{'；'.join(payload['learning_objectives'][:3])}",
                keywords=[point, *keywords],
                payload={"knowledge_point": point, "key_points": payload["key_points"]},
                order_index=order,
            )
        )
        order += 1
    for item in payload["problem_templates"][:3]:
        name = _compact_text(item.get("name") or item.get("title"), limit=120) or f"{page_title} 例题模板"
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_PROBLEM_TEMPLATE,
                title=_artifact_title(name, ""),
                summary=_compact_text(item.get("transfer_prompt") or item.get("_content"), limit=260),
                content=_problem_template_content(item, name=name),
                keywords=[name, *keywords],
                payload={key: value for key, value in item.items() if key != "_content"},
                order_index=order,
            )
        )
        order += 1
    for item in payload["misconceptions"][:4]:
        title = _compact_text(item.get("title") or item.get("name"), limit=120) or f"{page_title} 易错点"
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_MISCONCEPTION_CARD,
                title=_artifact_title(title, ""),
                summary=_compact_text(item.get("description") or item.get("_content"), limit=260),
                content=_misconception_content(item, title=title),
                keywords=[title, *keywords],
                payload={key: value for key, value in item.items() if key != "_content"},
                order_index=order,
            )
        )
        order += 1
    for question in payload["quick_checks"][:3]:
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_QUICK_CHECK,
                title=_artifact_title("快问：", question),
                summary=question,
                content=f"快问：{question}\n建议学生用一句话说明依据。",
                keywords=keywords,
                payload={"question": question},
                order_index=order,
            )
        )
        order += 1
    for prompt in payload["discussion_prompts"][:2]:
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_DISCUSSION_PROMPT,
                title=_artifact_title("讨论：", prompt),
                summary=prompt,
                content=f"讨论问题：{prompt}\n引导学生说明条件、步骤和结论之间的关系。",
                keywords=keywords,
                payload={"prompt": prompt},
                order_index=order,
            )
        )
        order += 1
    for idea in payload["demo_ideas"][:1]:
        artifacts.append(
            _new_artifact(
                material=material,
                lesson=lesson,
                page=page,
                artifact_type=ARTIFACT_DEMO,
                title=_artifact_title("演示：", idea),
                summary=idea,
                content=f"演示入口：{idea}",
                keywords=keywords,
                payload={"idea": idea},
                order_index=order,
            )
        )
        order += 1
    if degraded:
        for artifact in artifacts:
            artifact.payload = {**(artifact.payload or {}), "degraded": True, "source": "template"}
    return artifacts


def _problem_template_content(item: dict[str, Any], *, name: str) -> str:
    return "\n".join(
        part
        for part in [
            f"题型：{name}",
            f"适用条件：{_flatten_payload(item.get('conditions'), limit=600)}",
            f"解题步骤：{_flatten_payload(item.get('steps'), limit=900)}",
            f"可替换变量槽位：{_flatten_payload(item.get('variable_slots'), limit=500)}",
            f"易错点：{_flatten_payload(item.get('mistakes'), limit=600)}",
            f"迁移提示：{_compact_text(item.get('transfer_prompt'), limit=500)}",
        ]
        if part.split("：", 1)[-1].strip()
    )


def _misconception_content(item: dict[str, Any], *, title: str) -> str:
    return "\n".join(
        part
        for part in [
            f"易错点：{title}",
            f"错误表现：{_compact_text(item.get('description') or item.get('mistake'), limit=600)}",
            f"纠正方法：{_compact_text(item.get('correction') or item.get('fix'), limit=600)}",
        ]
        if part.split("：", 1)[-1].strip()
    ) or _compact_text(item.get("_content"), limit=900)


def _chapter_outline_artifact(
    *,
    material: CourseMaterial,
    lesson: Lesson,
    pages: Sequence[LessonPage],
    page_artifacts: Sequence[PedagogyArtifact],
    degraded: bool = False,
) -> PedagogyArtifact:
    summaries = [artifact for artifact in page_artifacts if artifact.artifact_type == ARTIFACT_PAGE_SUMMARY]
    concepts = [artifact.title.replace("：知识点", "") for artifact in page_artifacts if artifact.artifact_type == ARTIFACT_CONCEPT_CARD]
    templates = [artifact.title for artifact in page_artifacts if artifact.artifact_type == ARTIFACT_PROBLEM_TEMPLATE]
    mistakes = [artifact.title for artifact in page_artifacts if artifact.artifact_type == ARTIFACT_MISCONCEPTION_CARD]
    page_lines = [
        f"第{page.page_number}页：{page.page_title or _compact_text(page.page_text, limit=28) or '页面内容'}"
        for page in pages
    ]
    content = "\n".join(
        [
            f"课件：{lesson.title}",
            f"章节大纲：{'；'.join(page_lines[:80])}",
            f"学习目标：理解本课件的主要概念、典型题型、易错点和前置关系。",
            f"知识点：{'；'.join(dict.fromkeys(concepts[:30]))}",
            f"例题模板：{'；'.join(dict.fromkeys(templates[:16]))}",
            f"易错点：{'；'.join(dict.fromkeys(mistakes[:16]))}",
        ]
    )
    return _new_artifact(
        material=material,
        lesson=lesson,
        page=None,
        artifact_type=ARTIFACT_CHAPTER_OUTLINE,
        title=f"{lesson.title}：教学结构大纲",
        summary=f"{lesson.title} 共 {len(pages)} 页，已提炼 {len(page_artifacts)} 个教学对象。",
        content=content,
        keywords=list(dict.fromkeys(concepts[:20])),
        payload={
            "page_count": len(pages),
            "pages": [{"page_number": page.page_number, "title": page.page_title} for page in pages],
            "summary_count": len(summaries),
            "concepts": list(dict.fromkeys(concepts[:40])),
            "problem_templates": list(dict.fromkeys(templates[:24])),
            "misconceptions": list(dict.fromkeys(mistakes[:24])),
        },
        order_index=0,
        degraded=degraded,
    )


def generate_material_pedagogy_artifacts(
    db: Session,
    *,
    material: CourseMaterial,
    lesson: Lesson,
    pages: Sequence[LessonPage],
    on_progress: Callable[[dict[str, Any]], None] | None = None,
    warnings: list[str] | None = None,
) -> list[PedagogyArtifact]:
    db.execute(delete(PedagogyArtifact).where(PedagogyArtifact.material_id == material.id))
    artifacts: list[PedagogyArtifact] = []
    total_pages = len(pages)
    for index, page in enumerate(pages, start=1):
        page_artifacts = _page_artifacts(
            db=db,
            material=material,
            lesson=lesson,
            page=page,
            order_base=(index - 1) * 100 + 1,
            warnings=warnings,
        )
        artifacts.extend(page_artifacts)
        if on_progress is not None:
            on_progress(
                {
                    "completed_pages": index,
                    "total_pages": total_pages,
                    "page_number": page.page_number,
                }
            )
    if pages:
        artifacts.insert(0, _chapter_outline_artifact(material=material, lesson=lesson, pages=pages, page_artifacts=artifacts))
    for artifact in artifacts:
        db.add(artifact)
    db.flush()
    return artifacts


def ensure_lesson_pedagogy_artifacts(
    db: Session,
    *,
    lesson: Lesson,
    pages: Sequence[LessonPage],
) -> list[PedagogyArtifact]:
    if lesson.material_id is None or not pages:
        return []
    existing_id = db.scalar(select(PedagogyArtifact.id).where(PedagogyArtifact.lesson_id == lesson.id).limit(1))
    if existing_id is not None:
        return []
    material = db.get(CourseMaterial, lesson.material_id)
    if material is None:
        return []
    artifacts: list[PedagogyArtifact] = []
    for index, page in enumerate(pages):
        artifacts.extend(
            _page_artifacts(
                db=db,
                material=material,
                lesson=lesson,
                page=page,
                order_base=index * 100 + 1,
                use_ai=False,
            )
        )
    artifacts.insert(0, _chapter_outline_artifact(material=material, lesson=lesson, pages=pages, page_artifacts=artifacts, degraded=True))
    for artifact in artifacts:
        db.add(artifact)
    db.flush()
    return artifacts


def search_pedagogy_artifacts(
    db: Session,
    *,
    course_id: int,
    query: str,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    lesson_page_id: int | None = None,
    types: set[str] | None = None,
    limit: int = _ARTIFACT_RETRIEVAL_LIMIT,
) -> list[PedagogyArtifact]:
    artifact_types = types or QA_ARTIFACT_TYPES
    statement = select(PedagogyArtifact).where(
        PedagogyArtifact.course_id == course_id,
        PedagogyArtifact.artifact_type.in_(artifact_types),
    )
    if chapter_id is not None:
        statement = statement.where(or_(PedagogyArtifact.chapter_id == chapter_id, PedagogyArtifact.chapter_id.is_(None)))
    if lesson_id is not None:
        statement = statement.where(PedagogyArtifact.lesson_id == lesson_id)
    if lesson_page_id is not None:
        statement = statement.where(
            or_(PedagogyArtifact.lesson_page_id == lesson_page_id, PedagogyArtifact.artifact_type == ARTIFACT_CHAPTER_OUTLINE)
        )
    scan_limit = max(limit * 18, 120)
    candidates = list(
        db.scalars(
            statement.order_by(
                PedagogyArtifact.lesson_id.is_(None),
                PedagogyArtifact.lesson_id,
                PedagogyArtifact.lesson_page_id.is_(None),
                PedagogyArtifact.lesson_page_id,
                PedagogyArtifact.order_index,
                PedagogyArtifact.id,
            ).limit(scan_limit)
        )
    )
    if not candidates:
        return []
    ranked: list[tuple[int, int, PedagogyArtifact]] = []
    page_numbers = page_numbers_from_query(query)
    terms = query_terms(query, stopwords=_ARTIFACT_QUERY_STOPWORDS, limit=24)
    problem_intent = bool(_PROBLEM_INTENT_PATTERN.search(query))
    for artifact in candidates:
        payload = artifact.payload if isinstance(artifact.payload, dict) else {}
        try:
            page_number = int(payload.get("page_number") or 0) or None
        except (TypeError, ValueError):
            page_number = None
        text = "\n".join(
            part
            for part in [
                artifact.summary or "",
                artifact.content or "",
                " ".join(str(item) for item in artifact.keywords or []),
                _flatten_payload(payload, limit=1200),
            ]
            if part
        )
        base_score = score_text_for_query(
            title=artifact.title,
            text=text,
            page_number=page_number,
            query=query,
            stopwords=_ARTIFACT_QUERY_STOPWORDS,
            term_limit=24,
        )
        score = base_score
        if terms and any(term in artifact.title.lower() for term in terms):
            score += 18
        if base_score > 0 and artifact.artifact_type == ARTIFACT_PROBLEM_TEMPLATE and problem_intent:
            score += 42
        if base_score > 0 and artifact.artifact_type in {ARTIFACT_CONCEPT_CARD, ARTIFACT_MISCONCEPTION_CARD} and problem_intent:
            score += 10
        if lesson_page_id is not None and artifact.lesson_page_id == lesson_page_id:
            score += 18
        if lesson_id is not None and artifact.lesson_id == lesson_id:
            score += 8
        if page_number is not None and page_number in page_numbers:
            score += 80
        if score > 0:
            ranked.append((score, -artifact.order_index, artifact))
    ranked.sort(key=lambda item: (item[0], item[1], -item[2].id), reverse=True)
    return [artifact for _, _, artifact in ranked[:limit]]


def artifact_context(artifact: PedagogyArtifact, *, limit: int = 1600) -> str:
    label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, artifact.artifact_type)
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    page_part = f"第{payload.get('page_number')}页" if payload.get("page_number") else "课件整体"
    payload_text = _flatten_payload(payload, limit=700)
    text = "\n".join(
        part
        for part in [
            f"结构化教学对象：{label}",
            f"来源：{payload.get('material_title') or ''} {page_part}".strip(),
            f"标题：{artifact.title}",
            f"摘要：{artifact.summary}" if artifact.summary else "",
            artifact.content,
            f"补充结构：{payload_text}" if payload_text else "",
        ]
        if part
    )
    return _compact_text(text, limit=limit)


def artifact_contexts(artifacts: Sequence[PedagogyArtifact], *, limit: int = 1600) -> list[str]:
    return [context for artifact in artifacts if (context := artifact_context(artifact, limit=limit))]


def artifact_source(artifact: PedagogyArtifact) -> dict[str, Any]:
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    label = ARTIFACT_TYPE_LABELS.get(artifact.artifact_type, artifact.artifact_type)
    page_number = payload.get("page_number")
    material_title = payload.get("material_title") or "课件"
    title = f"{material_title} · {label}"
    if page_number:
        title = f"{material_title} · 第{page_number}页 · {label}"
    return {
        "type": "pedagogy_artifact",
        "artifact_id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "title": title,
        "material_id": artifact.material_id,
        "material_title": material_title,
        "lesson_id": artifact.lesson_id,
        "lesson_page_id": artifact.lesson_page_id,
        "page_number": page_number,
        "chapter_id": artifact.chapter_id,
        "course_id": artifact.course_id,
    }


def artifact_sources(artifacts: Sequence[PedagogyArtifact]) -> list[dict[str, Any]]:
    return [artifact_source(artifact) for artifact in artifacts]


def activity_from_artifact(artifact: PedagogyArtifact) -> dict[str, Any]:
    payload = artifact.payload if isinstance(artifact.payload, dict) else {}
    artifact_type = artifact.artifact_type
    return {
        "id": artifact.id,
        "type": artifact_type,
        "scene_type": payload.get("scene_type") or SCENE_TYPE_BY_ARTIFACT.get(artifact_type, "explain"),
        "label": ARTIFACT_TYPE_LABELS.get(artifact_type, artifact_type),
        "title": artifact.title,
        "summary": artifact.summary,
        "content": artifact.content,
        "keywords": artifact.keywords or [],
        "payload": payload,
        "order_index": artifact.order_index,
    }


def page_activity_payload(db: Session, *, lesson_page_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    ids = [int(item) for item in lesson_page_ids if int(item or 0) > 0]
    if not ids:
        return {}
    page_rows = db.execute(
        select(LessonPage, Lesson)
        .join(Lesson, Lesson.id == LessonPage.lesson_id)
        .where(LessonPage.id.in_(ids))
    )
    teachable_pages = {page.id for page, lesson in page_rows if _is_teachable_page(page, lesson)}
    if not teachable_pages:
        return {}
    artifacts = list(
        db.scalars(
            select(PedagogyArtifact)
            .where(PedagogyArtifact.lesson_page_id.in_(teachable_pages))
            .order_by(PedagogyArtifact.lesson_page_id, PedagogyArtifact.order_index, PedagogyArtifact.id)
        )
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts:
        if artifact.lesson_page_id is not None:
            grouped[int(artifact.lesson_page_id)].append(activity_from_artifact(artifact))
    return dict(grouped)


def quiz_artifact_source_text(
    db: Session,
    *,
    course_id: int,
    chapter_ids: Sequence[int] | None = None,
    limit: int = 80,
) -> tuple[str, int]:
    statement = select(PedagogyArtifact).where(
        PedagogyArtifact.course_id == course_id,
        PedagogyArtifact.artifact_type.in_(QUIZ_ARTIFACT_TYPES),
    )
    if chapter_ids:
        statement = statement.where(or_(PedagogyArtifact.chapter_id.in_(list(chapter_ids)), PedagogyArtifact.chapter_id.is_(None)))
    artifacts = list(
        db.scalars(
            statement.order_by(
                PedagogyArtifact.artifact_type == ARTIFACT_CHAPTER_OUTLINE,
                PedagogyArtifact.lesson_id,
                PedagogyArtifact.lesson_page_id,
                PedagogyArtifact.order_index,
            ).limit(limit)
        )
    )
    contexts = artifact_contexts(artifacts, limit=1200)
    return "\n\n".join(contexts), len(artifacts)
