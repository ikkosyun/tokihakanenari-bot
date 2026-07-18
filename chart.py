"""砂時計イラスト＋縦棒グラフ＋テキストをひとつのInstagram投稿画像に合成する。

数値に関わる部分（棒グラフの高さ・日付や残り日数の文字）はすべてPillowで
座標計算して描くため、Geminiのイラスト生成に数値のズレは影響しない。
"""
import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from caption import DayStats
from season import SeasonTheme

CANVAS_SIZE = 1080
MARGIN = 60
HOURGLASS_BOX = 640  # 左側に配置する砂時計イラストの一辺
BAR_WIDTH = 120
BAR_HEIGHT = 640
BAR_X = 860
BAR_Y = MARGIN + 40

_FONT_CANDIDATES = [
    # Windows（ローカルのdry-run用）
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    # Linux / GitHub Actions（`fonts-noto-cjk` を事前installしておく）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]


def _find_japanese_font() -> str:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for pattern in ("/usr/share/fonts/**/NotoSansCJK*.ttc",
                    "/usr/share/fonts/**/NotoSansCJK*.otf"):
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    raise RuntimeError(
        "日本語フォントが見つかりません。Windowsでは通常自動検出されますが、"
        "GitHub Actions(Ubuntu)では事前に `sudo apt-get install -y fonts-noto-cjk` "
        "を実行してください。"
    )


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_find_japanese_font(), size)


def _draw_gradient_background(theme: SeasonTheme) -> Image.Image:
    canvas = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE))
    top_rgb = Image.new("RGB", (1, 1), theme.bg_top).getpixel((0, 0))
    bottom_rgb = Image.new("RGB", (1, 1), theme.bg_bottom).getpixel((0, 0))
    for y in range(CANVAS_SIZE):
        t = y / (CANVAS_SIZE - 1)
        r = round(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = round(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = round(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        ImageDraw.Draw(canvas).line([(0, y), (CANVAS_SIZE, y)], fill=(r, g, b))
    return canvas


def _paste_hourglass(canvas: Image.Image, hourglass_path: Path) -> None:
    hourglass = Image.open(hourglass_path).convert("RGBA")
    side = min(hourglass.size)
    left = (hourglass.width - side) // 2
    top = (hourglass.height - side) // 2
    hourglass = hourglass.crop((left, top, left + side, top + side))
    hourglass = hourglass.resize((HOURGLASS_BOX, HOURGLASS_BOX), Image.LANCZOS)
    paste_x = MARGIN
    paste_y = (CANVAS_SIZE - HOURGLASS_BOX) // 2 - 40
    canvas.paste(hourglass, (paste_x, paste_y), hourglass)


def _draw_bar(draw: ImageDraw.ImageDraw, stats: DayStats, theme: SeasonTheme) -> None:
    # 外枠（うっすら）
    draw.rounded_rectangle(
        [BAR_X, BAR_Y, BAR_X + BAR_WIDTH, BAR_Y + BAR_HEIGHT],
        radius=24, outline=theme.text_color, width=3,
    )
    # 25%刻みの目盛り
    for i in range(1, 4):
        y = BAR_Y + BAR_HEIGHT * i // 4
        draw.line([(BAR_X, y), (BAR_X + BAR_WIDTH, y)], fill=theme.text_color, width=1)

    # 残り%ぶんだけ下から塗りつぶす（時間が経つほど埋まりが減っていく）
    fill_ratio = max(0.0, min(1.0, stats.remaining_percent / 100))
    fill_height = round(BAR_HEIGHT * fill_ratio)
    fill_top = BAR_Y + (BAR_HEIGHT - fill_height)
    if fill_height > 0:
        draw.rounded_rectangle(
            [BAR_X, fill_top, BAR_X + BAR_WIDTH, BAR_Y + BAR_HEIGHT],
            radius=24, fill=theme.accent,
        )

    label_font = _font(34)
    label = f"{stats.remaining_percent:.1f}%"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    label_w = bbox[2] - bbox[0]
    draw.text((BAR_X + BAR_WIDTH / 2 - label_w / 2, BAR_Y + BAR_HEIGHT + 16),
               label, font=label_font, fill=theme.text_color)


def _draw_text_block(draw: ImageDraw.ImageDraw, stats: DayStats, theme: SeasonTheme) -> None:
    date_font = _font(46)
    big_font = _font(72)
    small_font = _font(32)

    date_str = f"{stats.year}.{stats.month:02d}.{stats.day:02d}"
    remain_str = f"残り {stats.remaining_days} 日"

    y = CANVAS_SIZE - MARGIN - 170
    draw.text((MARGIN, y), date_str, font=date_font, fill=theme.text_color)
    draw.text((MARGIN, y + 60), remain_str, font=big_font, fill=theme.accent)
    draw.text((MARGIN, y + 150), theme.label, font=small_font, fill=theme.text_color)


def compose_image(hourglass_path: Path, stats: DayStats, theme: SeasonTheme,
                   out_path: Path) -> Path:
    canvas = _draw_gradient_background(theme)
    _paste_hourglass(canvas, hourglass_path)
    draw = ImageDraw.Draw(canvas)
    _draw_bar(draw, stats, theme)
    _draw_text_block(draw, stats, theme)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
