"""Gemini APIで砂時計イラストを生成する。

数値やキャプションなどの「正確さが必要なテキスト」は、AI画像生成に描かせると
誤字や崩れが起きやすいため、ここでは装飾的なイラスト部分だけをGeminiに任せ、
日付や残り日数の文字は chart.py 側で Pillow を使って正確に描画する。

公式SDK(google-genai)は google-auth 経由で cryptography(Rustビルド)に依存し、
環境によってはビルドに失敗するため、ここではAPIキー認証のみで完結する
REST APIを requests で直接叩く実装にしている。
"""
import base64
import os
from pathlib import Path

import requests

from season import SeasonTheme

DEFAULT_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def build_prompt(theme: SeasonTheme) -> str:
    return (
        "A beautiful, artistic hourglass (sandglass) illustration, photorealistic "
        "digital art style, symbolizing the preciousness of passing time. "
        f"Color palette and mood: {theme.prompt_palette}. "
        "The sand is gently falling, catching soft light. Elegant, calm, emotional "
        "atmosphere that makes the viewer feel how precious a single day and a "
        "single hour are. Centered composition, roughly square framing, "
        "clean simple background suitable for compositing onto another image. "
        "IMPORTANT: absolutely no text, no numbers, no letters, no watermark, "
        "no calendar digits anywhere in the image."
    )


def generate_hourglass_image(theme: SeasonTheme, save_path: Path,
                              model: str = DEFAULT_MODEL) -> Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    url = f"{API_BASE}/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": build_prompt(theme)}]}]}

    res = requests.post(url, params={"key": api_key}, json=body, timeout=120)
    if not res.ok:
        raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text}")

    data = res.json()
    parts = data["candidates"][0]["content"]["parts"]
    for part in parts:
        inline = part.get("inlineData")
        if inline and inline.get("data"):
            image_bytes = base64.b64decode(inline["data"])
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(image_bytes)
            return save_path

    raise RuntimeError("Geminiのレスポンスに画像データが含まれていませんでした")
