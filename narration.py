"""リール動画のナレーション音声を Gemini TTS で生成する。

読み上げるのは「日付になりました。今年はあと◯日、残り◯%です」という一言だけ
（本文キャプションのようなランダム性は持たせない、事実だけを読む）。
音声出力は秒あたり固定トークン数で課金されるため、コストは他のテキスト生成と
同様に無視できる小ささ（1本あたり1円未満）。
"""
import base64
import os
import time
import wave
from pathlib import Path

import requests

from caption import DayStats

DEFAULT_MODEL = os.environ.get("GEMINI_TTS_MODEL") or "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = os.environ.get("GEMINI_TTS_VOICE") or "Kore"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Gemini TTSの音声出力仕様（固定）: 16bit PCM, モノラル, 24kHz
_SAMPLE_RATE = 24000
_SAMPLE_WIDTH = 2
_CHANNELS = 1


def build_narration_text(stats: DayStats) -> str:
    return (
        f"{stats.year}年{stats.month}月{stats.day}日になりました。"
        f"今年はあと{stats.remaining_days}日、残り{stats.remaining_percent:.1f}%です"
    )


def _call_gemini_tts(model: str, voice: str, text: str, api_key: str,
                      retry_delays: list[int]) -> requests.Response | None:
    url = f"{API_BASE}/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }

    last_res = None
    for attempt, delay in enumerate([0, *retry_delays]):
        if delay:
            time.sleep(delay)
        res = requests.post(url, params={"key": api_key}, json=body, timeout=60)
        if res.ok:
            return res
        last_res = res
        if res.status_code != 503:
            break
    return None if last_res is None or not last_res.ok else last_res


def generate_narration_audio(text: str, out_path: Path, model: str = DEFAULT_MODEL,
                              voice: str = DEFAULT_VOICE) -> Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    # 画像生成と同じくGemini側の一時的な混雑(503)に備えてリトライする。
    res = _call_gemini_tts(model, voice, text, api_key, retry_delays=[10, 30])
    if res is None:
        raise RuntimeError(f"Gemini TTS API error: モデル {model} で音声生成に失敗しました")

    data = res.json()
    inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    audio_bytes = base64.b64decode(inline["data"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(audio_bytes)

    return out_path
