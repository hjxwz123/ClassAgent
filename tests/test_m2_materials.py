from io import BytesIO
from pathlib import Path

import fitz
from docx import Document
from pptx import Presentation

from app.services.parser import parse_material


def register_user(client, *, email, password, nickname, role, student_no=None, employee_no=None):
    payload = {
        "email": email,
        "password": password,
        "nickname": nickname,
        "role": role,
        "student_no": student_no,
        "employee_no": employee_no,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def login_user(client, *, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def build_pptx_bytes() -> bytes:
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "极限定义"
    slide.placeholders[1].text = "极限描述函数在某点附近的变化趋势。"
    slide2 = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide2.shapes.title.text = "连续性"
    slide2.placeholders[1].text = "连续函数在区间内没有跳跃。"
    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def build_docx_bytes() -> bytes:
    document = Document()
    document.add_heading("导数概念", level=1)
    document.add_paragraph("导数表示函数变化率。")
    document.add_paragraph("几何意义是切线斜率。")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_pdf_bytes() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "积分用于度量累积量。")
    return pdf.tobytes()


def build_txt_bytes() -> bytes:
    return "矩阵可以表示线性变换。\n\n行列式反映缩放系数。".encode("utf-8")


def test_document_parsers_cover_all_supported_types(tmp_path: Path):
    pptx_path = tmp_path / "demo.pptx"
    pptx_path.write_bytes(build_pptx_bytes())
    pdf_path = tmp_path / "demo.pdf"
    pdf_path.write_bytes(build_pdf_bytes())
    docx_path = tmp_path / "demo.docx"
    docx_path.write_bytes(build_docx_bytes())
    txt_path = tmp_path / "demo.txt"
    txt_path.write_bytes(build_txt_bytes())

    assert len(parse_material(pptx_path, "pptx")) == 2
    assert len(parse_material(pdf_path, "pdf")) == 1
    assert len(parse_material(docx_path, "docx")) >= 1
    assert len(parse_material(txt_path, "txt")) == 2


def test_material_management_flow(client):
    register_user(
        client,
        email="teacher2@example.com",
        password="Teacher123",
        nickname="王老师",
        role="teacher",
        employee_no="T2026002",
    )
    register_user(
        client,
        email="student2@example.com",
        password="Student123",
        nickname="赵同学",
        role="student",
        student_no="S2026002",
    )
    teacher_login = login_user(client, email="teacher2@example.com", password="Teacher123")
    teacher_headers = auth_headers(teacher_login["access_token"])
    student_login = login_user(client, email="student2@example.com", password="Student123")
    student_headers = auth_headers(student_login["access_token"])

    course_resp = client.post(
        "/api/v1/courses",
        json={"name": "线性代数", "description": "矩阵与向量", "term": "2026春"},
        headers=teacher_headers,
    )
    assert course_resp.status_code == 200, course_resp.text
    course = course_resp.json()["data"]

    chapter_resp = client.post(
        f"/api/v1/courses/{course['id']}/chapters",
        json={"title": "第一章 矩阵", "description": "基础内容", "order_index": 1},
        headers=teacher_headers,
    )
    assert chapter_resp.status_code == 200, chapter_resp.text
    chapter = chapter_resp.json()["data"]

    join_resp = client.post(
        "/api/v1/courses/join",
        json={"course_code": course["course_code"]},
        headers=student_headers,
    )
    assert join_resp.status_code == 200, join_resp.text

    upload_resp = client.post(
        "/api/v1/materials",
        data={
            "course_id": str(course["id"]),
            "title": "矩阵基础课件",
            "category": "courseware",
            "chapter_id": str(chapter["id"]),
        },
        files={
            "file": (
                "matrix.pptx",
                build_pptx_bytes(),
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        },
        headers=teacher_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    material = upload_resp.json()["data"]
    assert material["parse_status"] == "ready"
    assert material["vector_status"] == "ready"
    assert material["preview_url"]

    detail_resp = client.get(f"/api/v1/materials/{material['id']}", headers=teacher_headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["data"]
    assert detail["lesson_page_count"] == 2
    assert len(detail["pages"]) == 2
    assert detail["pages"][0]["script_text"]
    assert detail["pages"][0]["audio_url"].endswith(".wav")

    page_id = detail["pages"][0]["id"]
    update_script_resp = client.patch(
        f"/api/v1/materials/pages/{page_id}/script",
        json={"script_text": "这是教师手动修订后的讲解脚本。"},
        headers=teacher_headers,
    )
    assert update_script_resp.status_code == 200, update_script_resp.text
    assert update_script_resp.json()["data"]["script_text"] == "这是教师手动修订后的讲解脚本。"

    regenerate_resp = client.post(
        f"/api/v1/materials/pages/{page_id}/script/regenerate",
        headers=teacher_headers,
    )
    assert regenerate_resp.status_code == 200, regenerate_resp.text
    assert regenerate_resp.json()["data"]["audio_url"].endswith(".wav")

    student_list_resp = client.get(
        "/api/v1/materials",
        params={"course_id": course["id"], "keyword": "矩阵"},
        headers=student_headers,
    )
    assert student_list_resp.status_code == 200, student_list_resp.text
    assert len(student_list_resp.json()["data"]) == 1

    reprocess_resp = client.post(
        f"/api/v1/materials/{material['id']}/reprocess",
        headers=teacher_headers,
    )
    assert reprocess_resp.status_code == 200, reprocess_resp.text

    update_material_resp = client.patch(
        f"/api/v1/materials/{material['id']}",
        json={"title": "矩阵基础课件-修订版", "category": "handout", "chapter_id": chapter["id"]},
        headers=teacher_headers,
    )
    assert update_material_resp.status_code == 200, update_material_resp.text
    assert update_material_resp.json()["data"]["title"] == "矩阵基础课件-修订版"

    delete_resp = client.delete(f"/api/v1/materials/{material['id']}", headers=teacher_headers)
    assert delete_resp.status_code == 200, delete_resp.text
