import html
import json
import logging
import re
import time
import wave
from io import BytesIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, bad_request
from app.services.runtime_config import get_enabled_service_config
from app.services.storage import storage_service


LOGGER = logging.getLogger(__name__)


MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[(?P<alt>[^\]]*)]\(\s*(?:<[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]*['\"])?\s*\)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[(?P<label>[^\]]+)]\(\s*(?:<[^>]+>|[^)\s]+)(?:\s+['\"][^'\"]*['\"])?\s*\)")
HTML_IMG_PATTERN = re.compile(r"""<img\b[^>]*>""", re.IGNORECASE)
HTML_ALT_PATTERN = re.compile(r"""\balt=["'](?P<alt>[^"']+)["']""", re.IGNORECASE)
CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)```", re.DOTALL)
RAW_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
LATEX_REPLACEMENTS = {
    r"\geq": "大于等于",
    r"\leq": "小于等于",
    r"\neq": "不等于",
    r"\times": "乘以",
    r"\cdot": "乘以",
    r"\div": "除以",
    r"\pm": "正负",
    r"\to": "趋向",
    r"\rightarrow": "趋向",
    r"\leftarrow": "反向趋向",
    r"\infty": "无穷",
    r"\alpha": "阿尔法",
    r"\beta": "贝塔",
    r"\gamma": "伽马",
    r"\Gamma": "伽马",
    r"\delta": "德尔塔",
    r"\lambda": "兰姆达",
    r"\mu": "缪",
    r"\pi": "派",
    r"\sum": "求和",
    r"\prod": "连乘",
    r"\sqrt": "根号",
}


def _html_image_alt(match: re.Match[str]) -> str:
    alt_match = HTML_ALT_PATTERN.search(match.group(0))
    if alt_match is None:
        return ""
    return html.unescape(alt_match.group("alt")).strip()


def _clean_latex(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\\frac\s*{([^{}]+)}\s*{([^{}]+)}", r"\1 除以 \2", cleaned)
    cleaned = re.sub(r"\\(?:mathrm|mathbb|mathbf|mathcal|text)\s*{([^{}]*)}", r"\1", cleaned)
    for marker in (r"\left", r"\right", r"\begin", r"\end"):
        cleaned = cleaned.replace(marker, " ")
    for source, target in LATEX_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, f" {target} ")
    cleaned = re.sub(r"\\[a-zA-Z]+", " ", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    cleaned = cleaned.replace("_", " 下标 ").replace("^", " 上标 ")
    cleaned = cleaned.replace("&", " ").replace("\\\\", " ")
    return cleaned


def markdown_to_speech_text(value: str | None) -> str:
    """Convert lesson Markdown into plain text before sending it to TTS."""
    if not value:
        return ""
    text = html.unescape(str(value)).replace("\r\n", "\n").replace("\r", "\n")
    text = CODE_FENCE_PATTERN.sub(lambda match: match.group(1), text)
    text = HTML_IMG_PATTERN.sub(_html_image_alt, text)
    text = MARKDOWN_IMAGE_PATTERN.sub(lambda match: (match.group("alt") or "").strip(), text)
    text = MARKDOWN_LINK_PATTERN.sub(lambda match: match.group("label").strip(), text)
    text = RAW_URL_PATTERN.sub("", text)
    text = re.sub(r"\$\$(.*?)\$\$", lambda match: _clean_latex(match.group(1)), text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", lambda match: _clean_latex(match.group(1)), text)
    text = _clean_latex(text)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if TABLE_SEPARATOR_PATTERN.match(line):
            continue
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*[-*+]\s+\[[ xX]\]\s+", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)
        line = line.replace("|", " ")
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"[*_~`#>{}\[\]\(\)]+", " ", text)
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class TTSService:
    sample_rate = 16000
    default_nls_url = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
    token_region = "cn-shanghai"
    token_domain = "nls-meta.cn-shanghai.aliyuncs.com"
    token_api_version = "2019-02-28"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._token_cache: dict[tuple[str, str], tuple[str, int]] = {}

    # 中文 TTS 大致 4~5 字/秒，按 4.5 字/秒估算朗读时长。
    _ESTIMATE_CHARS_PER_SECOND = 4.5

    def _estimate_duration(self, text: str) -> float:
        # #58: 去掉原 30 秒硬上限，避免长音频被记成 30 秒。仅保留下限，避免过短。
        return max(2.0, round(max(len(text), 1) / self._ESTIMATE_CHARS_PER_SECOND, 2))

    def _duration_from_wav(self, content: bytes, fallback_text: str) -> float:
        try:
            with wave.open(BytesIO(content), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                rate = wav_file.getframerate()
                return round(frame_count / rate, 2) if rate else self._estimate_duration(fallback_text)
        except wave.Error:
            return self._estimate_duration(fallback_text)

    def _duration_from_pcm(self, content: bytes, sample_rate: int) -> float | None:
        # 原始 PCM（无文件头）：每采样 16bit 单声道，时长 = 字节数 / (采样率 * 2)。
        if sample_rate <= 0 or not content:
            return None
        return round(len(content) / (sample_rate * 2), 2)

    def _duration_for_format(self, content: bytes, audio_format: str, fallback_text: str, sample_rate: int) -> float:
        # #58: 对所有格式尽量从真实音频字节推算时长，无法解析时退回不被 30s 截断的合理估算。
        fmt = (audio_format or "").lower()
        if fmt == "wav":
            return self._duration_from_wav(content, fallback_text)
        if fmt == "pcm":
            pcm_duration = self._duration_from_pcm(content, sample_rate)
            if pcm_duration is not None:
                return pcm_duration
        if fmt in {"mp3", "mp3-16k", "mp3-8k"}:
            mp3_duration = self._duration_from_mp3(content)
            if mp3_duration is not None:
                return mp3_duration
        return self._estimate_duration(fallback_text)

    def _duration_from_mp3(self, content: bytes) -> float | None:
        # 无第三方解析库时，按 MP3 帧头逐帧累加每帧时长得到较真实的总时长。
        if not content:
            return None
        try:
            return self._scan_mp3_frames(content)
        except Exception:  # noqa: BLE001 - 解析失败时回退估算，不应让时长计算抛错
            LOGGER.warning("MP3 duration parse failed", exc_info=True)
            return None

    _MP3_BITRATES_V1_L3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
    _MP3_BITRATES_V2_L3 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
    _MP3_SAMPLE_RATES = {
        3: (44100, 48000, 32000),  # MPEG1
        2: (22050, 24000, 16000),  # MPEG2
        0: (11025, 12000, 8000),   # MPEG2.5
    }

    def _scan_mp3_frames(self, content: bytes) -> float | None:
        offset = 0
        length = len(content)
        # 跳过 ID3v2 头（若存在）。
        if length >= 10 and content[:3] == b"ID3":
            size = (content[6] << 21) | (content[7] << 14) | (content[8] << 7) | content[9]
            offset = 10 + size
        total_seconds = 0.0
        frames = 0
        while offset + 4 <= length:
            if content[offset] != 0xFF or (content[offset + 1] & 0xE0) != 0xE0:
                offset += 1
                continue
            header = content[offset:offset + 4]
            version_bits = (header[1] >> 3) & 0x03
            layer_bits = (header[1] >> 1) & 0x03
            bitrate_index = (header[2] >> 4) & 0x0F
            sample_rate_index = (header[2] >> 2) & 0x03
            padding = (header[2] >> 1) & 0x01
            if layer_bits != 0x01 or bitrate_index in (0, 15) or sample_rate_index == 0x03:
                offset += 1
                continue
            sample_rates = self._MP3_SAMPLE_RATES.get(version_bits)
            if not sample_rates:
                offset += 1
                continue
            sample_rate = sample_rates[sample_rate_index]
            bitrate_table = self._MP3_BITRATES_V1_L3 if version_bits == 3 else self._MP3_BITRATES_V2_L3
            bitrate = bitrate_table[bitrate_index] * 1000
            if bitrate <= 0 or sample_rate <= 0:
                offset += 1
                continue
            samples_per_frame = 1152 if version_bits == 3 else 576
            frame_length = int((samples_per_frame // 8 * bitrate) / sample_rate) + padding
            if frame_length <= 0:
                offset += 1
                continue
            total_seconds += samples_per_frame / sample_rate
            frames += 1
            offset += frame_length
        if frames == 0:
            return None
        return round(total_seconds, 2)

    def _nls_url(self) -> str:
        return self.default_nls_url

    def _clean_config(self, config: dict) -> dict:
        cleaned = dict(config)
        for key in (
            "access_key_id",
            "access_key_secret",
            "appkey",
            "voice",
            "format",
            "url",
            "token",
        ):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        return cleaned

    def _create_token(self, config: dict) -> tuple[str, int]:
        config = self._clean_config(config)
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
        try:
            response = client.do_action_with_exception(request)
        except Exception as exc:
            # #60: 阿里云 SDK 原始异常（含 RequestId/错误码等）仅写服务端日志，对外统一文案。
            LOGGER.warning("TTS token request failed", exc_info=True)
            raise bad_request("语音服务令牌获取失败，请稍后重试或联系管理员") from exc
        payload = json.loads(response.decode("utf-8") if isinstance(response, bytes) else response)
        token_data = payload.get("Token") if isinstance(payload, dict) else None
        token = token_data.get("Id") if isinstance(token_data, dict) else None
        expire_time = int(token_data.get("ExpireTime") or 0) if isinstance(token_data, dict) else 0
        if not token or not expire_time:
            # #60: 原始响应 payload 仅写服务端日志，对用户返回统一友好文案。
            LOGGER.warning("TTS token acquisition failed: %s", payload)
            raise bad_request("语音服务令牌获取失败，请稍后重试或联系管理员")
        return str(token), expire_time

    def _access_token(self, config: dict) -> str:
        config = self._clean_config(config)
        cache_key = (str(config["access_key_id"]), str(config["access_key_secret"]))
        now = int(time.time())
        cached = self._token_cache.get(cache_key)
        if cached and cached[1] - 60 > now:
            return cached[0]
        token, expire_time = self._create_token(config)
        self._token_cache[cache_key] = (token, expire_time)
        return token

    def _release_synthesizer(self, synthesizer) -> None:
        # #59: 尽力释放底层 websocket 连接；不同 SDK 版本方法名可能是 shutdown/close，
        # 释放失败不应影响主流程，仅记日志。
        for method_name in ("shutdown", "close"):
            method = getattr(synthesizer, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:  # noqa: BLE001 - 释放阶段异常吞掉但记录，避免掩盖原始错误
                    LOGGER.warning("Failed to release TTS synthesizer via %s", method_name, exc_info=True)
                return

    def _synthesize_aliyun_bytes(self, text: str, config: dict) -> tuple[bytes, str]:
        config = self._clean_config(config)
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
        # #59: 用 try/finally 确保即便 start() 抛异常，也调用 SDK 的 shutdown/close 释放 websocket，
        # 避免连接泄漏。
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
            # #60: 原始 SDK 异常仅写服务端日志，对用户返回统一友好文案。
            LOGGER.warning("TTS synthesis failed", exc_info=True)
            raise bad_request("语音合成失败，请稍后重试或联系管理员") from exc
        finally:
            self._release_synthesizer(synthesizer)
        if errors:
            LOGGER.warning("TTS synthesis returned error: %s", errors[-1][:300])
            raise bad_request("语音合成失败，请稍后重试或联系管理员")
        content = b"".join(chunks)
        if not content:
            raise bad_request("TTS 合成失败: 未返回音频数据")
        return content, audio_format

    def _synthesize_aliyun(self, text: str, db: Session, config: dict) -> tuple[str, float]:
        config = self._clean_config(config)
        content, audio_format = self._synthesize_aliyun_bytes(text, config)
        # 讲解音频属课程教学资料，落到私有存储（不经无鉴权的 /static 暴露）。
        # 存"相对路径"，由 storage.normalize_public_url 在每次序列化时签发短时效 /media 链接，
        # 这样不会过期断播，且 generated/audio/ 已在签名白名单内。
        relative_path = storage_service.save_bytes(
            content,
            folder="generated/audio",
            filename=f"{uuid4().hex}.{audio_format}",
            db=db,
            public=False,
        )
        # #58: 按真实音频字节推算时长（wav/pcm/mp3），无法解析时退回不被 30s 截断的合理估算。
        sample_rate = int(config.get("sample_rate") or self.sample_rate)
        duration = self._duration_for_format(content, audio_format, text, sample_rate)
        return relative_path, duration

    def test_config(self, config: dict) -> dict:
        try:
            self._synthesize_aliyun_bytes("连接测试", self._clean_config(config))
        except AppError as exc:
            # 我方友好文案（已脱敏）可直接回显给管理员。
            message = exc.detail.get("message") if isinstance(exc.detail, dict) else "TTS 配置测试失败"
            return {"success": False, "message": message}
        except Exception:
            # #60: 原始 SDK 异常细节仅写服务端日志，对管理员返回统一文案。
            LOGGER.warning("TTS config test failed", exc_info=True)
            return {"success": False, "message": "TTS 配置测试失败，请检查配置或稍后重试"}
        return {"success": True, "message": "TTS 配置可用"}

    def synthesize(self, text: str, db: Session | None = None) -> tuple[str, float]:
        speech_text = markdown_to_speech_text(text) or "本页暂无可朗读内容。"
        service = get_enabled_service_config(db, "tts")
        if service is not None:
            if service.provider == "aliyun":
                return self._synthesize_aliyun(speech_text, db, self._clean_config(service.config))
            raise bad_request(f"暂不支持的 TTS 服务提供方: {service.provider}")
        raise bad_request("TTS 服务未配置，请先在管理员服务配置中启用 tts")


tts_service = TTSService()
