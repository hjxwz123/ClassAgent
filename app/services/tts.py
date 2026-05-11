import html
import json
import re
import time
import wave
from io import BytesIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_enabled_service_config
from app.services.storage import storage_service


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
        response = client.do_action_with_exception(request)
        payload = json.loads(response.decode("utf-8") if isinstance(response, bytes) else response)
        token_data = payload.get("Token") if isinstance(payload, dict) else None
        token = token_data.get("Id") if isinstance(token_data, dict) else None
        expire_time = int(token_data.get("ExpireTime") or 0) if isinstance(token_data, dict) else 0
        if not token or not expire_time:
            raise bad_request(f"TTS Token 获取失败: {payload}")
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
        config = self._clean_config(config)
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
            self._synthesize_aliyun_bytes("连接测试", self._clean_config(config))
        except Exception as exc:
            return {"success": False, "message": str(exc)}
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
