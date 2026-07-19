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

from caption import DayStats
from season import SeasonTheme

DEFAULT_MODEL = os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _sand_description(remaining_percent: float) -> str:
    """残り%を上下の砂の比率としてそのまま明示する（時の経過を体感させる）。"""
    top_pct = round(remaining_percent)
    bottom_pct = 100 - top_pct
    return (
        f"exactly {top_pct}% of all the sand is still sitting in the upper bulb, "
        f"and exactly {bottom_pct}% of the sand has already fallen and piled up "
        f"in the lower bulb. This is a strict physical requirement, not a vague "
        f"suggestion: measure the sand volume in each bulb and make sure the "
        f"upper bulb's sand volume is {top_pct}% of the total and the lower "
        f"bulb's sand volume is {bottom_pct}% of the total. "
        + (
            "At this level the upper bulb must look almost completely full, "
            "packed with sand nearly to the top, while the lower bulb is nearly bare."
            if top_pct >= 80 else
            "At this level the upper bulb must look almost completely empty, "
            "just a thin residue of sand left, while the lower bulb is piled "
            "high and nearly full."
            if top_pct <= 20 else
            "The two bulbs should look visually distinguishable in fill level, "
            "not equal."
        )
    )


def build_prompt(theme: SeasonTheme, stats: DayStats) -> str:
    return (
        "A vintage brass hourglass filled with glittering golden sand, placed on a "
        "dark polished wood table, photorealistic, glassy and luxurious feel with a "
        "real sense of transparency in the glass. A small burning tea light candle "
        "is set perfectly on top of the hourglass, casting a warm glow and gentle "
        "flicker. Fine sand drifts down, catching soft cinematic light with tiny "
        "glowing dust particles in the air. "
        f"Sand level (important, depict accurately): {_sand_description(stats.remaining_percent)}. "
        f"Background: a soft-focused, blurred bokeh backdrop evoking {theme.prompt_palette}, "
        "shallow depth of field, high-end editorial product photography, ultra-detailed, "
        "8k quality, elegant and premium mood. "
        "Composition (strict): the hourglass (including its base and posts) must be "
        "positioned in the left half of the frame and must not extend past 60% of the "
        "frame's width from the left edge. Keep the entire right third of the frame, and "
        "the lower area, as clear, mostly empty softly-blurred background for a later "
        "overlay - do not let the hourglass, its stand, or any sand particles cross into "
        "that space. The photo must fill the entire square frame edge to edge with no "
        "blank, cut-off, or unfinished areas. "
        "IMPORTANT: absolutely no text, no numbers, no letters, no watermark, no calendar "
        "tiles, no digits, no progress bars, no UI elements, no graphs anywhere in the "
        "image - pure photography only, nothing else added on top."
    )


def generate_hourglass_image(theme: SeasonTheme, stats: DayStats, save_path: Path,
                              model: str = DEFAULT_MODEL) -> Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    url = f"{API_BASE}/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": build_prompt(theme, stats)}]}],
        "generationConfig": {"imageConfig": {"aspectRatio": "1:1"}},
    }

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
