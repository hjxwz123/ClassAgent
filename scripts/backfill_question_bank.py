#!/usr/bin/env python
"""存量题目回填题库脚本（一次性，幂等可重跑，可在服务在线时运行）。

用途
----
题库功能（question_bank_items，检索优先 + 缺口补生成出题）上线时，历史上 AI 已经
生成过的题目还散落在 quiz_questions 里。本脚本把它们按题库口径批量沉淀进题库，
让功能上线第一天就有库存可检索，而不必等新生成慢慢积累。

用法
----
    .venv/bin/python scripts/backfill_question_bank.py            # 全量回填
    .venv/bin/python scripts/backfill_question_bank.py --dry-run  # 只统计不落库

规则（与运行时入库口径一致，见 app/services/learning.py _ingest_questions_into_bank）
----
- 只回填 quiz_type != wrong_book 的卷（错题重练是针对个人错题的定向变式，语境不通用）；
- 跳过已软删除课程的卷（这些课程的题库行永远不可能被检索到，纯死数据）；
- origin：course 类型卷（教师出卷，可能是未发布考卷）标 teacher——学生练习检索会排除
  teacher 来源防泄题；其余标 backfill；
- 按 (course_id, 归一化题干 stem_key) 去重：重做克隆卷、历史重复题只会入库一份；
- 幂等且并发安全：按主键窗口分批提交，逐行 SAVEPOINT 兜底唯一约束冲突——
  与在线服务的实时入库同时运行也不会互相打崩。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.enums import QuizType
from app.db import session as db_session
from app.db.models import Course, QuestionBankItem, Quiz, QuizQuestion
from app.services.learning import _bank_stem_key

BATCH_SIZE = 500


def backfill(*, dry_run: bool) -> None:
    db_session.init_db()
    scanned = 0
    ingested = 0
    skipped_duplicate = 0
    skipped_source = 0
    with db_session.SessionLocal() as db:
        existing_keys = {
            (course_id, stem_key)
            for course_id, stem_key in db.execute(select(QuestionBankItem.course_id, QuestionBankItem.stem_key))
        }
        last_id = 0
        while True:
            rows = db.execute(
                select(QuizQuestion, Quiz)
                .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
                .join(Course, Course.id == Quiz.course_id)
                .where(
                    Quiz.quiz_type != QuizType.WRONG_BOOK.value,
                    Course.deleted_at.is_(None),
                    QuizQuestion.id > last_id,
                )
                .order_by(QuizQuestion.id)
                .limit(BATCH_SIZE)
            ).all()
            if not rows:
                break
            last_id = rows[-1][0].id
            for question, quiz in rows:
                scanned += 1
                # 重做克隆卷（source=retake）一律跳过：错题重练的重做克隆会把"个人错题变式"
                # 带进共享题库；教师考卷的重做克隆会以可检索的 backfill 来源二次入库、绕过防泄题
                # 的 teacher 来源过滤。普通练习的重做克隆与原卷同题干，本就会被去重跳过，不损失覆盖。
                meta = quiz.metadata_json if isinstance(quiz.metadata_json, dict) else {}
                if str(meta.get("source") or "") in {"retake", "wrong_book"}:
                    skipped_source += 1
                    continue
                key = (question.course_id, _bank_stem_key(question.stem))
                if key in existing_keys:
                    skipped_duplicate += 1
                    continue
                existing_keys.add(key)
                if dry_run:
                    ingested += 1
                    continue
                item = QuestionBankItem(
                    course_id=question.course_id,
                    chapter_id=question.chapter_id,
                    knowledge_point_id=question.knowledge_point_id,
                    question_type=question.question_type,
                    difficulty=question.difficulty or "standard",
                    stem=question.stem,
                    options=question.options,
                    reference_answer=question.reference_answer,
                    explanation=question.explanation,
                    stem_key=key[1],
                    source_quiz_id=quiz.id,
                    source_question_id=question.id,
                    origin="teacher" if quiz.quiz_type == QuizType.COURSE.value else "backfill",
                    status="active",
                )
                # 逐行 SAVEPOINT：与在线实时入库并发运行时撞唯一约束只丢这一行，不炸整批
                try:
                    with db.begin_nested():
                        db.add(item)
                        db.flush()
                except IntegrityError:
                    skipped_duplicate += 1
                    continue
                ingested += 1
            if not dry_run:
                db.commit()
    mode = "dry-run 统计" if dry_run else "已入库"
    print(f"扫描 {scanned} 道题；{mode} {ingested} 道；按题干去重跳过 {skipped_duplicate} 道；重做/错题克隆卷跳过 {skipped_source} 道。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="把存量 AI 生成题回填进课程题库")
    parser.add_argument("--dry-run", action="store_true", help="只统计将要入库的数量，不实际写库")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
