import threading

from sqlalchemy import select

from app.db import session as db_session
from app.db.models import Chapter, Course, KnowledgeChunk, KnowledgePoint, User
from app.services import knowledge as knowledge_service


def test_knowledge_point_pre_generation_caps_concurrency_at_15(client, monkeypatch):
    with db_session.SessionLocal() as db:
        teacher = User(
            email="knowledge-concurrency@example.com",
            password_hash="not-used",
            role="teacher",
            nickname="并发测试老师",
            employee_no="KP-CONCURRENCY",
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        course = Course(
            name="知识点并发课程",
            description="并发测试",
            term="2026春",
            course_code="KPCONC",
            teacher_id=teacher.id,
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        chapter = Chapter(course_id=course.id, title="并发章节", order_index=1)
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        db.add_all(
            [
                KnowledgeChunk(
                    course_id=course.id,
                    chapter_id=chapter.id,
                    title=f"片段 {index}",
                    content=f"并发知识点片段 {index}",
                )
                for index in range(30)
            ]
        )
        db.commit()
        course_id = course.id
        chapter_id = chapter.id

    lock = threading.Lock()
    first_wave = threading.Barrier(15)
    state = {"active": 0, "peak": 0, "calls": 0}

    def extract(text, db=None):
        with lock:
            state["active"] += 1
            state["calls"] += 1
            call_number = state["calls"]
            state["peak"] = max(state["peak"], state["active"])
        if call_number <= 15:
            first_wave.wait(timeout=5)
        with lock:
            state["active"] -= 1
        return ["公共知识点", f"知识点{call_number}"]

    monkeypatch.setattr(knowledge_service.ai_service, "extract_knowledge_points", extract)
    with db_session.SessionLocal() as db:
        result = knowledge_service.pre_generate_knowledge_points(
            db,
            course_id=course_id,
            chapter_id=chapter_id,
            max_concurrency=15,
        )

    assert state["calls"] == 30
    assert state["peak"] == 15
    assert result.chunk_count == 30
    assert result.failed_chunk_count == 0
    assert len(result.points) == 8

    def fail_if_called(*args, **kwargs):
        raise AssertionError("existing knowledge points must be reused without another extraction")

    monkeypatch.setattr(knowledge_service.ai_service, "extract_knowledge_points", fail_if_called)
    with db_session.SessionLocal() as db:
        reused = knowledge_service.pre_generate_knowledge_points(
            db,
            course_id=course_id,
            chapter_id=chapter_id,
            max_concurrency=15,
        )
        stored = list(
            db.scalars(
                select(KnowledgePoint).where(
                    KnowledgePoint.course_id == course_id,
                    KnowledgePoint.chapter_id == chapter_id,
                )
            )
        )

    assert reused.reused_existing is True
    assert len(stored) == 8
