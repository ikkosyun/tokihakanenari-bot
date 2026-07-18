"""月ごとの季節配色テーマ定義。

Gemini への画像生成プロンプトと、Pillow で描く棒グラフ・テキストの色に
共通で使う「季節のパレット」を1箇所にまとめている。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SeasonTheme:
    month: int
    label: str  # 季節の呼び名（キャプションにも使う）
    prompt_palette: str  # Geminiへのプロンプトに埋め込む配色描写（日本語）
    bg_top: str  # 背景グラデーション上端（hex）
    bg_bottom: str  # 背景グラデーション下端（hex）
    accent: str  # 棒グラフ・強調色（hex）
    text_color: str  # 本文テキスト色（hex、背景とのコントラストを確保）


THEMES: dict[int, SeasonTheme] = {
    1: SeasonTheme(1, "正月・新春", "松の深緑と金箔のような輝き、凛とした冬の空気",
                   "#0b2e1f", "#123524", "#d4af37", "#f5f0e1"),
    2: SeasonTheme(2, "梅の候", "紅梅の濃いピンクと雪の白、澄んだ寒空の青",
                   "#241222", "#3a1a35", "#e8608f", "#f7e9f0"),
    3: SeasonTheme(3, "早春", "桜のつぼみの淡いピンクと若草色、やわらかな春の光",
                   "#2b1f2a", "#3d2b3a", "#f2a6c1", "#fbeef3"),
    4: SeasonTheme(4, "桜満開", "満開の桜のピンクと新緑の黄緑、明るい春の日差し",
                   "#2a1830", "#3f2440", "#ff8fb1", "#fff2f6"),
    5: SeasonTheme(5, "新緑", "みずみずしい新緑の黄緑と澄んだ五月晴れの青",
                   "#0f2a1c", "#163a26", "#7fd858", "#eefcf1"),
    6: SeasonTheme(6, "紫陽花・梅雨", "紫陽花の青紫とグレーがかった雨の空気感",
                   "#1c1f3a", "#262a4d", "#8a7fe0", "#f0eefc"),
    7: SeasonTheme(7, "七夕・盛夏", "夜空の深いブルーと天の川の金色の輝き",
                   "#071233", "#0c1f4d", "#f4c542", "#fff8e6"),
    8: SeasonTheme(8, "真夏", "抜けるような真夏の青空とまぶしい白、入道雲",
                   "#04275c", "#0a3a80", "#ffffff", "#eaf4ff"),
    9: SeasonTheme(9, "実りの秋", "稲穂やかぼちゃを思わせる琥珀色とオレンジ",
                   "#3a2408", "#4f3010", "#e8912a", "#fff3e0"),
    10: SeasonTheme(10, "紅葉", "燃えるような紅葉の赤とオレンジのグラデーション",
                    "#3a0f0a", "#521810", "#e8542a", "#fff0ea"),
    11: SeasonTheme(11, "晩秋", "深紅と焦げ茶色、落ち葉が舞う静かな夕暮れ",
                    "#2a0e0e", "#3d1616", "#b5432a", "#f7e9e2"),
    12: SeasonTheme(12, "冬・年の瀬", "白銀の雪とゴールドの輝き、澄み切った夜空",
                    "#0a1428", "#141f3d", "#e8d9a0", "#f5f7ff"),
}


def theme_for_month(month: int) -> SeasonTheme:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month}")
    return THEMES[month]
