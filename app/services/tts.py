import wave
from io import BytesIO
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_enabled_service_config
from app.services.storage import storage_service


class TTSService:
    sample_rate = 16000

    def __init__(self) -> None:
        self.settings = get_settings()

    def _estimate_duration(self, text: str) -> float:
        return max(2.0, min(30.0, round(max(len(text), 40) / 20, 2)))

    def _duration_from_wav(self, content: bytes, fallback_text: str) -> float:
        try:
            with wave.open(BytesIO(content), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                rate = wav_file.getframerate()
                return round(frame_count / rate, 2) if rate else self._estimate_duration(fallback_text)
        except wave.Error:
            return self._estimate_duration(fallback_text)

    def _synthesize_mock(self, text: str, db: Session | None) -> tuple[str, float]:
        duration = max(2.0, min(30.0, round(max(len(text), 40) / 20, 2)))
        frame_count = int(self.sample_rate * duration)
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)
        relative_path = storage_service.save_bytes(
            buffer.getvalue(),
            folder="generated/audio",
            filename=f"{uuid4().hex}.wav",
            db=db,
        )
        return storage_service.public_url(relative_path, db=db), duration

    def _synthesize_aliyun(self, text: str, db: Session, config: dict) -> tuple[str, float]:
        required = ["appkey", "token", "url", "voice"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"TTS 配置缺少字段: {', '.join(missing)}")
        audio_format = str(config.get("format") or "wav").lower()
        payload = {
            "appkey": config["appkey"],
            "token": config["token"],
            "text": text,
            "format": audio_format,
            "sample_rate": int(config.get("sample_rate") or self.sample_rate),
            "voice": config.get("voice") or self.settings.default_tts_voice,
            "speech_rate": int(config.get("speech_rate", self.settings.default_tts_rate)),
            "volume": int(config.get("volume", self.settings.default_tts_volume)),
        }
        with httpx.Client(timeout=self.settings.external_service_timeout_seconds) as client:
            if str(config.get("method", "GET")).upper() == "POST":
                response = client.post(str(config["url"]), json=payload)
            else:
                response = client.get(str(config["url"]), params=payload)
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or "json" in content_type.lower():
            raise bad_request(f"TTS 合成失败: {response.text[:300]}")
        relative_path = storage_service.save_bytes(
            response.content,
            folder="generated/audio",
            filename=f"{uuid4().hex}.{audio_format}",
            db=db,
        )
        duration = self._duration_from_wav(response.content, text) if audio_format == "wav" else self._estimate_duration(text)
        return storage_service.public_url(relative_path, db=db), duration

    def synthesize(self, text: str, db: Session | None = None) -> tuple[str, float]:
        service = get_enabled_service_config(db, "tts")
        if service is not None:
            return self._synthesize_aliyun(text, db, service.config)
        if self.settings.app_env == "production":
            raise bad_request("TTS 服务未配置，请先在管理员服务配置中启用 tts")
        return self._synthesize_mock(text, db)


tts_service = TTSService()
