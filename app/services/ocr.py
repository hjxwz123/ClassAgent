from fastapi import UploadFile


class MockOCRService:
    def recognize(self, upload: UploadFile) -> str:
        return f"未配置 OCR 服务，已接收图片 {upload.filename or 'unknown'}，请学生手动修正识别结果。"


ocr_service = MockOCRService()
