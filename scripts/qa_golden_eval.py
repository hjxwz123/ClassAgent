#!/usr/bin/env python
"""QA golden 回归评估脚本（最小可行版）。

用途
----
QA 链路（app/services/knowledge.py 的 search_course_knowledge 检索
→ app/services/qa.py 重排/上下文组装 → LLM 生成）在调整召回/重排阈值、
提示词或模型后，没有任何自动化质量校验。本脚本提供一个可手动运行的
回归评估：给定一份 golden 问答集，验证「检索 + 轻量重排后，目标资料
仍然能进入上下文」，避免一次调参悄悄打掉一批常见问题的召回。

用法
----
    .venv/bin/python scripts/qa_golden_eval.py --cases scripts/qa_golden_cases.json
    .venv/bin/python scripts/qa_golden_eval.py --cases scripts/qa_golden_cases.json --with-llm

- 默认模式（检索级）：对每个 case 调用 search_course_knowledge 取回
  KnowledgeChunk 列表，断言 expect_context_keywords 中每个关键词至少
  出现在某个返回片段（标题+正文）里。不调用 LLM，快且省钱。
- --with-llm 模式（可选）：在检索通过的基础上，把片段按线上同款格式
  （"资料片段：{标题}\\n{正文}"）拼成 contexts，调用
  ai_service.answer_question 生成非流式回答，再断言
  expect_answer_keywords 出现在回答文本里。会真实消耗 LLM 配额。

怎么建自己的 golden 集
----------------------
1. 复制 scripts/qa_golden_cases.example.json 为 scripts/qa_golden_cases.json
   （后者建议加进 .gitignore，属于每个人/每门课自己的数据）。
2. 每门课挑 10~20 条「学生真的会问、且课程资料里明确有答案」的问题：
   - question 用学生的自然问法，不要写成资料原文；
   - expect_context_keywords 从资料原文里挑 1~3 个有区分度的短语
     （太通用的词如"函数"命中不说明问题，太长的整句又容易因换行/空格断开）；
   - 可选 chapter_id 用于模拟章节内提问的过滤行为；
   - 可选 expect_answer_keywords 给 --with-llm 模式断言回答质量。
3. 建议把本脚本纳入发布前 checklist：每次改动召回/重排阈值
  （qa.rerank.min_score 等运行时配置）、提示词、嵌入或对话模型后，
   先跑一遍检索级评估，通过率 100% 再发布。

为什么不进 CI
-------------
- 依赖真实数据库（本地经 SSH 隧道到 MySQL 13306）与真实向量库/嵌入
  服务，CI 环境没有这些数据与凭据；
- golden 集与具体课程资料强绑定，属于环境数据而非代码资产；
- --with-llm 模式还要消耗真实模型配额且结果非确定。
  因此定位为"发布前手动回归"，而非 CI 门禁。

注意事项
--------
- 运行前需先执行 ./local/start-dev.sh 建立 SSH 隧道（MySQL 13306），
  否则脚本会在连接检查阶段给出提示并退出（exit code 2）。
- search_course_knowledge 在课程向量索引缺失时会触发同步回填
  （重嵌入整门课的 chunk），首跑可能较慢，属服务层既有行为。
- 通过率 < 100% 时退出码为 1，可直接接入 shell 判断。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# 允许在仓库任意位置执行：把仓库根目录加入 sys.path，才能 import app.*
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """折叠空白并转小写，缓解 PDF 抽取文本换行/多空格导致的匹配失败。"""
    return " ".join(str(text or "").split()).lower()


def _normalize_tight(text: str) -> str:
    """去掉全部空白的版本：中文资料常被抽取成"字 与 字"带空格的形态。"""
    return "".join(str(text or "").split()).lower()


def _keyword_hit(keyword: str, text: str) -> bool:
    """关键词命中判断：先按折叠空白匹配，再退化到去空白匹配。"""
    return _normalize(keyword) in _normalize(text) or _normalize_tight(keyword) in _normalize_tight(text)


def _preview(text: str, limit: int = 80) -> str:
    clean = " ".join(str(text or "").split())
    return clean[:limit] + ("…" if len(clean) > limit else "")


# ---------------------------------------------------------------------------
# case 加载与校验
# ---------------------------------------------------------------------------


def load_cases(path: Path) -> list[dict[str, Any]]:
    """读取 golden 集。兼容两种顶层结构：case 数组，或 {"cases": [...]}。

    以 "_" 开头的键（如 "_说明"）视为给人看的注释字段，直接忽略。
    """
    if not path.exists():
        print(f"[错误] golden 集文件不存在：{path}")
        print("       可先复制 scripts/qa_golden_cases.example.json 改成自己的课程数据。")
        raise SystemExit(2)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[错误] golden 集不是合法 JSON：{path}\n       {exc}")
        raise SystemExit(2) from exc

    if isinstance(raw, dict):
        raw_cases = raw.get("cases")
        if not isinstance(raw_cases, list):
            print('[错误] JSON 顶层为对象时必须包含 "cases" 数组。')
            raise SystemExit(2)
    elif isinstance(raw, list):
        raw_cases = raw
    else:
        print("[错误] JSON 顶层必须是 case 数组或含 cases 数组的对象。")
        raise SystemExit(2)

    cases: list[dict[str, Any]] = []
    for index, item in enumerate(raw_cases, start=1):
        if not isinstance(item, dict):
            print(f"[错误] 第 {index} 个 case 不是对象，已忽略。")
            continue
        case = {key: value for key, value in item.items() if not str(key).startswith("_")}
        problems: list[str] = []
        if not str(case.get("name") or "").strip():
            case["name"] = f"case-{index}"
        if not isinstance(case.get("course_id"), int):
            problems.append("course_id 必须是整数")
        if not str(case.get("question") or "").strip():
            problems.append("question 不能为空")
        keywords = case.get("expect_context_keywords")
        if not isinstance(keywords, list) or not any(str(k).strip() for k in keywords):
            problems.append("expect_context_keywords 必须是非空字符串数组")
        if case.get("chapter_id") is not None and not isinstance(case.get("chapter_id"), int):
            problems.append("chapter_id 若提供必须是整数")
        if problems:
            print(f"[错误] case「{case['name']}」字段不合法：{'；'.join(problems)}")
            raise SystemExit(2)
        cases.append(case)

    if not cases:
        print("[错误] golden 集为空，没有可执行的 case。")
        raise SystemExit(2)
    return cases


# ---------------------------------------------------------------------------
# 数据库连接
# ---------------------------------------------------------------------------


def open_session():
    """建立数据库会话，连接失败时给出「先启动本地隧道」的明确提示。"""
    try:
        from sqlalchemy import text as sa_text

        from app.db.session import SessionLocal
    except Exception as exc:  # noqa: BLE001 - 环境/依赖问题统一给提示
        print(f"[错误] 导入 app 模块失败：{exc}")
        print("       请确认使用仓库虚拟环境运行：.venv/bin/python scripts/qa_golden_eval.py …")
        raise SystemExit(2) from exc

    session = SessionLocal()
    try:
        session.execute(sa_text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - OperationalError 等一律视为连不上
        session.close()
        print("[错误] 数据库连接失败，无法执行评估。")
        print("       本地开发需先启动 SSH 隧道与依赖服务：./local/start-dev.sh")
        print("       （隧道就绪后 MySQL 监听 127.0.0.1:13306，脚本读取 app 配置的 DATABASE_URL）")
        print(f"       底层错误：{exc}")
        raise SystemExit(2) from exc
    return session


# ---------------------------------------------------------------------------
# 单 case 评估
# ---------------------------------------------------------------------------


def diagnose_empty_retrieval(db, *, course_id: int) -> str:
    """检索为空时的友好诊断：区分课程不存在 / 课程无资料 / 单纯没检到。"""
    try:
        from sqlalchemy import func, select

        from app.db.models import Course, KnowledgeChunk

        course = db.get(Course, course_id)
        if course is None or getattr(course, "deleted_at", None) is not None:
            return f"course_id={course_id} 不存在（或已删除），请检查 golden 集里的课程 ID"
        chunk_count = db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.course_id == course_id)) or 0
        if chunk_count == 0:
            return f"课程「{course.name}」(id={course_id}) 没有任何知识块，请先上传并解析课程资料"
        return f"课程「{course.name}」(id={course_id}) 有 {chunk_count} 个知识块，但本问题未检索到任何片段"
    except Exception as exc:  # noqa: BLE001 - 诊断失败不影响主流程
        return f"检索结果为空（附加诊断失败：{exc}）"


def eval_retrieval_case(db, case: dict[str, Any], *, limit: int) -> tuple[bool, list[str], list]:
    """检索级评估：返回 (是否通过, 详情行列表, 检索片段列表)。

    片段列表原样返回给 --with-llm 模式复用，避免重复检索导致两级结果不一致。
    """
    from app.services.knowledge import search_course_knowledge

    details: list[str] = []
    started = time.monotonic()
    chunks = search_course_knowledge(
        db,
        course_id=case["course_id"],
        query=case["question"],
        chapter_id=case.get("chapter_id"),
        limit=limit,
    )
    elapsed = time.monotonic() - started

    if not chunks:
        details.append(f"检索为空：{diagnose_empty_retrieval(db, course_id=case['course_id'])}")
        details.append(f"耗时 {elapsed:.1f}s")
        return False, details, []

    keywords = [str(k) for k in case["expect_context_keywords"] if str(k).strip()]
    missing: list[str] = []
    for keyword in keywords:
        hit_index = next(
            (i for i, chunk in enumerate(chunks, start=1) if _keyword_hit(keyword, f"{chunk.title}\n{chunk.content}")),
            None,
        )
        if hit_index is None:
            missing.append(keyword)
            details.append(f"未命中：「{keyword}」")
        else:
            chunk = chunks[hit_index - 1]
            details.append(f"命中：「{keyword}」→ 片段#{hit_index} (chunk_id={chunk.id}, 标题={_preview(chunk.title, 40)})")

    if missing:
        details.append(f"检索返回 {len(chunks)} 个片段（耗时 {elapsed:.1f}s），内容概览：")
        for i, chunk in enumerate(chunks, start=1):
            details.append(f"  片段#{i} chunk_id={chunk.id} 标题={_preview(chunk.title, 40)} 正文={_preview(chunk.content, 70)}")
        return False, details, chunks

    details.append(f"检索返回 {len(chunks)} 个片段，全部 {len(keywords)} 个关键词命中（耗时 {elapsed:.1f}s）")
    return True, details, chunks


def eval_llm_case(db, case: dict[str, Any], chunks) -> tuple[bool | None, list[str]]:
    """生成级评估（--with-llm）：返回 (是否通过/None=跳过, 详情行列表)。

    说明：qa 服务的完整非流式入口 qa.ask_question 需要真实 User 对象、
    会创建会话并把 QARecord / AI 用量写入数据库，评估脚本直接调用属于
    「硬凑」且会污染业务数据，故不走该入口。
    这里改调它底层同款的生成函数 ai_service.answer_question：contexts 按
    线上 _chunk_context 的同款格式（"资料片段：{标题}\\n{正文}"）拼装，
    能覆盖「检索片段 → 提示词 → 模型回答」这段链路。
    TODO: 若未来 qa 服务拆出「无需 User、不落库」的纯回答函数
    （如 answer_without_persist(db, course_id, question)），可替换为
    全链路调用，把 agent 规划、多路召回与 rerank 池也纳入评估。
    """
    answer_keywords = [str(k) for k in (case.get("expect_answer_keywords") or []) if str(k).strip()]
    if not answer_keywords:
        return None, ["未配置 expect_answer_keywords，跳过 LLM 断言"]
    if not chunks:
        return False, ["检索为空，无上下文可供生成，LLM 断言直接判 FAIL"]

    from app.services.ai import ai_service

    contexts = [f"资料片段：{chunk.title or '资料片段'}\n{chunk.content}" for chunk in chunks]
    started = time.monotonic()
    try:
        answer, out_of_scope, _thinking = ai_service.answer_question(
            question=case["question"],
            contexts=contexts,
            history=None,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001 - LLM 调用失败不应让整个评估崩溃
        return False, [f"LLM 调用失败：{exc}"]
    elapsed = time.monotonic() - started

    details = [f"LLM 回答 {len(answer)} 字（out_of_scope={out_of_scope}，耗时 {elapsed:.1f}s）：{_preview(answer, 100)}"]
    missing = [keyword for keyword in answer_keywords if not _keyword_hit(keyword, answer)]
    for keyword in answer_keywords:
        mark = "命中" if keyword not in missing else "未命中"
        details.append(f"{mark}：回答关键词「{keyword}」")
    return not missing, details


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="QA golden 回归评估：验证检索+重排后目标资料仍能进入上下文。")
    parser.add_argument("--cases", required=True, help="golden 集 JSON 路径（见 scripts/qa_golden_cases.example.json）")
    parser.add_argument("--with-llm", action="store_true", help="额外调用 LLM 生成回答并断言 expect_answer_keywords（消耗模型配额）")
    parser.add_argument("--limit", type=int, default=5, help="每个问题检索返回的片段数上限（默认 5，与线上默认一致）")
    args = parser.parse_args()

    # 压掉 app 内部 INFO 日志，保留 WARNING（如向量回填提示），让评估输出可读
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    cases = load_cases(Path(args.cases).expanduser())
    db = open_session()

    total = len(cases)
    passed = 0
    print(f"共加载 {total} 个 case（模式：{'检索级 + LLM 生成级' if args.with_llm else '检索级'}，limit={args.limit}）")
    print("-" * 72)

    try:
        for index, case in enumerate(cases, start=1):
            header = f"[{index}/{total}] {case['name']} (course_id={case['course_id']}) 问题：{_preview(case['question'], 40)}"
            try:
                retrieval_ok, detail_lines, chunks = eval_retrieval_case(db, case, limit=args.limit)
                case_ok = retrieval_ok
                if args.with_llm:
                    # LLM 断言复用同一批检索片段，避免重复检索导致两级结果不一致
                    llm_ok, llm_lines = eval_llm_case(db, case, chunks)
                    detail_lines.extend(f"[LLM] {line}" for line in llm_lines)
                    if llm_ok is False:
                        case_ok = False
            except Exception as exc:  # noqa: BLE001 - 单 case 异常不拖垮整体评估
                db.rollback()
                case_ok = False
                detail_lines = [f"评估过程中抛出异常：{exc.__class__.__name__}: {exc}"]

            print(f"{header} -> {'PASS' if case_ok else 'FAIL'}")
            for line in detail_lines:
                print(f"    {line}")
            if case_ok:
                passed += 1
    finally:
        db.close()

    rate = passed / total * 100 if total else 0.0
    print("-" * 72)
    print(f"汇总：总数 {total}，通过 {passed}，通过率 {rate:.1f}%")
    if passed < total:
        print("存在未通过 case：请检查召回/重排阈值、课程资料索引或 golden 集关键词是否过期。")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
