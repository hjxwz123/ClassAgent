import wave
from io import BytesIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_enabled_service_config
from app.services.storage import storage_service


class TTSService:
    sample_rate = 16000
    default_nls_url = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"

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

    def _nls_url(self, config: dict) -> str:
        url = str(config.get("url") or self.default_nls_url).strip()
        if url.startswith("http://") or url.startswith("https://"):
            scheme, rest = url.split("://", 1)
            host = rest.split("/", 1)[0]
            ws_scheme = "wss" if scheme == "https" else "ws"
            return f"{ws_scheme}://{host}/ws/v1"
        return url

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

    def _synthesize_aliyun_bytes(self, text: str, config: dict) -> tuple[bytes, str]:
        required = ["appkey", "token", "voice"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"TTS 配置缺少字段: {', '.join(missing)}")
        try:
            import nls
        except ImportError as exc:
            raise RuntimeError("缺少阿里云智能语音交互 Python SDK 依赖") from exc

        audio_format = str(config.get("format") or "wav").lower()
        chunks: list[bytes] = []
        errors: list[str] = []

        def on_data(data, *_) -> None:
            chunks.append(bytes(data))

        def on_error(message, *_) -> None:
            errors.append(str(message))

        synthesizer = nls.NlsSpeechSynthesizer(
            url=self._nls_url(config),
            token=config["token"],
            appkey=config["appkey"],
            long_tts=bool(config.get("long_tts", False)),
            on_data=on_data,
            on_error=on_error,
        )
        try:
            synthesizer.start(
                text=text,
                voice=config.get("voice") or self.settings.default_tts_voice,
                aformat=audio_format,
                sample_rate=int(config.get("sample_rate") or self.sample_rate),
                volume=int(config.get("volume", self.settings.default_tts_volume)),
                speech_rate=int(config.get("speech_rate", self.settings.default_tts_rate)),
                pitch_rate=int(config.get("pitch_rate", 0)),
                wait_complete=True,
                start_timeout=int(config.get("start_timeout_seconds") or 10),
                completed_timeout=int(config.get("completed_timeout_seconds") or self.settings.external_service_timeout_seconds),
            )
        except Exception as exc:
            raise bad_request(f"TTS 合成失败: {exc}") from exc
        if errors:
            raise bad_request(f"TTS 合成失败: {errors[-1][:300]}")
        content = b"".join(chunks)
        if not content:
            raise bad_request("TTS 合成失败: 未返回音频数据")
        return content, audio_format

    def _synthesize_aliyun(self, text: str, db: Session, config: dict) -> tuple[str, float]:
        content, audio_format = self._synthesize_aliyun_bytes(text, config)
        relative_path = storage_service.save_bytes(
            content,
            folder="generated/audio",
            filename=f"{uuid4().hex}.{audio_format}",
            db=db,
        )
        duration = self._duration_from_wav(content, text) if audio_format == "wav" else self._estimate_duration(text)
        return storage_service.public_url(relative_path, db=db), duration

    def test_config(self, config: dict) -> dict:
        try:
            self._synthesize_aliyun_bytes("连接测试", config)
        except Exception as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "message": "TTS 配置可用"}

    def synthesize(self, text: str, db: Session | None = None) -> tuple[str, float]:
        service = get_enabled_service_config(db, "tts")
        if service is not None:
            return self._synthesize_aliyun(text, db, service.config)
        if self.settings.app_env == "production":
            raise bad_request("TTS 服务未配置，请先在管理员服务配置中启用 tts")
        return self._synthesize_mock(text, db)


tts_service = TTSService()
