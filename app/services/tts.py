import wave
from io import BytesIO
from uuid import uuid4

from app.services.storage import storage_service


class MockTTSService:
    sample_rate = 16000

    def synthesize(self, text: str) -> tuple[str, float]:
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
        )
        return storage_service.public_url(relative_path), duration


tts_service = MockTTSService()
