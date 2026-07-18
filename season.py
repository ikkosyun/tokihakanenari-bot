"""月ごとの季節配色テーマ定義。

Gemini への画像生成プロンプト（背景の情景描写）と、Pillow で描く
バー・文字の強調色に共通で使う「季節のテーマ」を1箇所にまとめている。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeasonTheme:
    month: int
    label: str  # 季節の呼び名（キャプション・小話のテーマにも使う）
    prompt_palette: str  # Geminiへの背景描写プロンプト（具体的な情景で指定する）
    accent: str  # バー・強調テキストの色（hex）
    text_color: str  # 本文テキスト色（hex、背景とのコントラストを確保）


THEMES: dict[int, SeasonTheme] = {
    1: SeasonTheme(1, "正月・新春",
                   "a crisp New Year's morning: pine trees dusted with snow, a "
                   "brilliant golden sunrise, clear pale blue winter sky",
                   "#d4af37", "#f5f0e1"),
    2: SeasonTheme(2, "梅の候",
                   "deep pink plum blossoms in a quiet garden, soft winter "
                   "sunlight, a clear pale blue sky",
                   "#e8608f", "#f7e9f0"),
    3: SeasonTheme(3, "早春",
                   "cherry blossom buds just about to bloom, a gentle spring "
                   "breeze, soft pastel pink and pale blue sky",
                   "#f2a6c1", "#fbeef3"),
    4: SeasonTheme(4, "桜満開",
                   "a full bloom cherry blossom avenue with petals drifting in "
                   "the wind, bright spring sunlight, vivid blue sky",
                   "#ff8fb1", "#fff2f6"),
    5: SeasonTheme(5, "新緑", "fresh vivid green new leaves, a clear early-summer "
                   "blue sky, bright and refreshing sunlight",
                   "#7fd858", "#eefcf1"),
    6: SeasonTheme(6, "紫陽花・梅雨",
                   "blue and purple hydrangea flowers in a garden after rain, "
                   "soft misty overcast light, gentle rain droplets",
                   "#8a7fe0", "#f0eefc"),
    7: SeasonTheme(7, "真夏の海", "a vivid, dazzling summer sky and calm blue ocean, "
                   "brilliant white clouds, clear turquoise water, bright "
                   "sunlight reflecting on the sea",
                   "#1fb6e8", "#eaf9ff"),
    8: SeasonTheme(8, "真夏", "a blazing deep blue summer sky with towering white "
                   "cumulonimbus clouds, intense bright sunlight",
                   "#0a8fd4", "#eaf4ff"),
    9: SeasonTheme(9, "実りの秋", "golden ripe rice fields swaying in the autumn "
                   "breeze, a clear high autumn sky, warm amber light",
                   "#e8912a", "#fff3e0"),
    10: SeasonTheme(10, "紅葉", "a mountainside blazing with red and orange autumn "
                    "leaves (momiji), crisp clear air, soft autumn sunlight",
                    "#e8542a", "#fff0ea"),
    11: SeasonTheme(11, "晩秋", "a quiet tree-lined path scattered with fallen "
                    "russet and brown leaves, a soft late-autumn evening glow",
                    "#b5432a", "#f7e9e2"),
    12: SeasonTheme(12, "冬・年の瀬",
                    "a serene snow-covered landscape under a clear, crisp cold "
                    "night sky filled with stars, soft silver-blue moonlight",
                    "#8fb8e8", "#f5f7ff"),
}


def theme_for_month(month: int) -> SeasonTheme:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return THEMES[month]
