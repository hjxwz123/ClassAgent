import json
import time
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
    token_region = "cn-shanghai"
    token_domain = "nls-meta.cn-shanghai.aliyuncs.com"
    token_api_version = "2019-02-28"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._token_cache: dict[tuple[str, str], tuple[str, int]] = {}

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

    def _nls_url(self) -> str:
        return self.default_nls_url

    def _create_token(self, config: dict) -> tuple[str, int]:
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkcore.request import CommonRequest
        except ImportError as exc:
            raise RuntimeError("缺少阿里云公共 SDK 依赖，无法生成 TTS Token") from exc

        client = AcsClient(config["access_key_id"], config["access_key_secret"], self.token_region)
        request = CommonRequest()
        request.set_method("POST")
        request.set_domain(self.token_domain)
        request.set_version(self.token_api_version)
        request.set_action_name("CreateToken")
        response = client.do_action_with_exception(request)
        payload = json.loads(response.decode("utf-8") if isinstance(response, bytes) else response)
        token_data = payload.get("Token") if isinstance(payload, dict) else None
        token = token_data.get("Id") if isinstance(token_data, dict) else None
        expire_time = int(token_data.get("ExpireTime") or 0) if isinstance(token_data, dict) else 0
        if not token or not expire_time:
            raise bad_request(f"TTS Token 获取失败: {payload}")
        return str(token), expire_time

    def _access_token(self, config: dict) -> str:
        cache_key = (str(config["access_key_id"]), str(config["access_key_secret"]))
        now = int(time.time())
        cached = self._token_cache.get(cache_key)
        if cached and cached[1] - 60 > now:
            return cached[0]
        token, expire_time = self._create_token(config)
        self._token_cache[cache_key] = (token, expire_time)
        return token

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
        required = ["access_key_id", "access_key_secret", "appkey", "voice"]
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
            url=self._nls_url(),
            token=self._access_token(config),
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
