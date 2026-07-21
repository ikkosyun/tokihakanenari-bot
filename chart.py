"""砂時計イラスト（Gemini）＋セグメント式の光る残り時間バー＋テキストを合成する。

数値に関わる部分（バーの点灯数・日付や残り日数の文字）はすべてPillowで
座標計算して描くため、Geminiのイラスト生成に数値のズレは影響しない。
Geminiには写真風のシーン全体（背景込み）を作らせ、Pillow側は
その上にカード風の縁取り・光る残り時間バー・文字を重ねるだけにしている。
"""
import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from caption import DayStats
from season import SeasonTheme

CANVAS_SIZE = 1080
MARGIN = 56
STORY_SIZE = (1080, 1920)

BAR_SEGMENTS = 16
BAR_WIDTH = 84
BAR_HEIGHT = 560
BAR_X = 760  # 砂時計との間の余白を詰めるため、右端固定ではなく少し中央寄りに配置
BAR_Y = 150

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


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    return Image.new("RGB", (1, 1), hex_color).getpixel((0, 0))


def _load_photo_background(hourglass_path: Path) -> Image.Image:
    photo = Image.open(hourglass_path).convert("RGBA")
    side = min(photo.size)
    left = (photo.width - side) // 2
    top = (photo.height - side) // 2
    photo = photo.crop((left, top, left + side, top + side))
    return photo.resize((CANVAS_SIZE, CANVAS_SIZE), Image.LANCZOS)


def _draw_bottom_scrim(canvas: Image.Image) -> None:
    """下部のテキストが読みやすいよう、暗いグラデーションを重ねる。"""
    scrim = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)
    scrim_top = int(CANVAS_SIZE * 0.62)
    for y in range(scrim_top, CANVAS_SIZE):
        t = (y - scrim_top) / (CANVAS_SIZE - scrim_top - 1)
        alpha = int(190 * t)
        draw.line([(0, y), (CANVAS_SIZE, y)], fill=(5, 8, 18, alpha))
    canvas.alpha_composite(scrim)


def _draw_card_border(canvas: Image.Image, theme: SeasonTheme) -> None:
    """写真の縁に、ネオン風に光るカードフレームを重ねて高級感を出す。"""
    inset = 24
    accent = _hex_to_rgb(theme.accent)
    line_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(line_layer).rounded_rectangle(
        [inset, inset, CANVAS_SIZE - inset, CANVAS_SIZE - inset],
        radius=36, outline=(*accent, 255), width=3,
    )
    # 遠くまでふわっと広がるグロー(強)と、輪郭のすぐ外側の明るいグロー(弱)を重ねる
    canvas.alpha_composite(line_layer.filter(ImageFilter.GaussianBlur(18)))
    canvas.alpha_composite(line_layer.filter(ImageFilter.GaussianBlur(6)))
    canvas.alpha_composite(line_layer)


def _draw_day_tile(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                    stats: DayStats, theme: SeasonTheme) -> None:
    """フリップカレンダー風の、日付だけを見せる小さなタイル(バインダーリング＋色帯つき)。"""
    x, y = MARGIN + 24, MARGIN + 30
    w, h = 120, 142
    accent = _hex_to_rgb(theme.accent)
    header_h = int(h * 0.34)

    # 影
    draw.rounded_rectangle([x + 5, y + 8, x + w + 5, y + h + 8],
                            radius=16, fill=(0, 0, 0, 110))

    # タイル本体をオフスクリーンで作り、角丸マスクで綺麗にクリップする
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tile)
    tdraw.rectangle([0, 0, w, h], fill=(250, 250, 252, 255))
    tdraw.rectangle([0, 0, w, header_h], fill=(*accent, 255))
    tdraw.line([(0, header_h), (w, header_h)], fill=(0, 0, 0, 40), width=1)

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=16, fill=255)
    tile.putalpha(mask)

    label_font = _font(20)
    label = f"{stats.month}月"
    bbox = tdraw.textbbox((0, 0), label, font=label_font)
    lw = bbox[2] - bbox[0]
    tdraw.text((w / 2 - lw / 2, header_h / 2 - 13), label, font=label_font,
                fill=(255, 255, 255, 255))

    day_font = _font(58)
    day_str = str(stats.day)
    bbox = tdraw.textbbox((0, 0), day_str, font=day_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tdraw.text((w / 2 - tw / 2, header_h + (h - header_h) / 2 - th / 2 - 4), day_str,
                font=day_font, fill=(30, 30, 34, 255))

    canvas.alpha_composite(tile, (x, y))

    # バインダーリング(タイル上端をまたぐ小さな金属リング)
    for ring_cx in (x + w * 0.28, x + w * 0.72):
        ring_y = y
        draw.ellipse([ring_cx - 9, ring_y - 10, ring_cx + 9, ring_y + 8],
                      fill=(60, 60, 65, 255), outline=(*accent, 255), width=2)
        draw.ellipse([ring_cx - 4, ring_y - 5, ring_cx + 4, ring_y + 3],
                      fill=(15, 15, 18, 255))


def _draw_progress_bar(canvas: Image.Image, draw: ImageDraw.ImageDraw,
                        stats: DayStats, theme: SeasonTheme) -> None:
    accent = _hex_to_rgb(theme.accent)
    fill_ratio = max(0.0, min(1.0, stats.remaining_percent / 100))
    lit_segments = round(BAR_SEGMENTS * fill_ratio)

    gap = 6
    seg_height = (BAR_HEIGHT - gap * (BAR_SEGMENTS - 1)) / BAR_SEGMENTS

    # 光っているセグメントぶんの、ぼかしたグロー(発光)レイヤー
    if lit_segments > 0:
        glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow_layer)
        lit_top = BAR_Y + (BAR_SEGMENTS - lit_segments) * (seg_height + gap)
        gdraw.rounded_rectangle(
            [BAR_X - 10, lit_top - 10, BAR_X + BAR_WIDTH + 10, BAR_Y + BAR_HEIGHT + 10],
            radius=20, fill=(*accent, 200),
        )
        canvas.alpha_composite(glow_layer.filter(ImageFilter.GaussianBlur(22)))

    # 外側のカプセル型フレーム(うっすら白)
    draw.rounded_rectangle(
        [BAR_X - 8, BAR_Y - 8, BAR_X + BAR_WIDTH + 8, BAR_Y + BAR_HEIGHT + 8],
        radius=BAR_WIDTH / 2 + 8, outline=(255, 255, 255, 140), width=2,
    )

    for i in range(BAR_SEGMENTS):
        seg_top = BAR_Y + i * (seg_height + gap)
        seg_bottom = seg_top + seg_height
        is_lit = i >= (BAR_SEGMENTS - lit_segments)
        if is_lit:
            fill = (*accent, 255)
        else:
            fill = (255, 255, 255, 40)
        draw.rounded_rectangle(
            [BAR_X, seg_top, BAR_X + BAR_WIDTH, seg_bottom],
            radius=10, fill=fill,
        )

    label_font = _font(58)
    label = f"{stats.remaining_percent:.1f}%"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    label_w, label_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    label_x = BAR_X + BAR_WIDTH / 2 - label_w / 2
    label_y = BAR_Y + BAR_HEIGHT + 30

    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_layer).text((label_x, label_y), label, font=label_font,
                                     fill=(*accent, 255))
    canvas.alpha_composite(glow_layer.filter(ImageFilter.GaussianBlur(10)))

    draw.text((label_x + 2, label_y + 3), label, font=label_font, fill=(0, 0, 0, 140))
    draw.text((label_x, label_y), label, font=label_font, fill=(255, 255, 255, 255))

    small_font = _font(24)
    caption = "残り時間"
    cap_bbox = draw.textbbox((0, 0), caption, font=small_font)
    cap_w = cap_bbox[2] - cap_bbox[0]
    draw.text((BAR_X + BAR_WIDTH / 2 - cap_w / 2, label_y + label_h + 28),
               caption, font=small_font, fill=(*accent, 255))


def _draw_shadowed_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
                         font: ImageFont.FreeTypeFont, fill) -> None:
    x, y = xy
    draw.text((x + 2, y + 3), text, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), text, font=font, fill=fill)


def _draw_text_block(draw: ImageDraw.ImageDraw, stats: DayStats, theme: SeasonTheme) -> None:
    date_font = _font(44)
    big_font = _font(68)
    small_font = _font(30)

    date_str = f"{stats.year}.{stats.month:02d}.{stats.day:02d}"
    remain_str = f"残り {stats.remaining_days} 日"

    y = CANVAS_SIZE - MARGIN - 165
    _draw_shadowed_text(draw, (MARGIN, y), date_str, date_font, (255, 255, 255, 255))
    _draw_shadowed_text(draw, (MARGIN, y + 58), remain_str, big_font,
                         (*_hex_to_rgb(theme.accent), 255))
    _draw_shadowed_text(draw, (MARGIN, y + 148), theme.label, small_font,
                         (235, 235, 235, 255))


def compose_image(hourglass_path: Path, stats: DayStats, theme: SeasonTheme,
                   out_path: Path) -> Path:
    canvas = _load_photo_background(hourglass_path)
    _draw_bottom_scrim(canvas)

    draw = ImageDraw.Draw(canvas)
    _draw_progress_bar(canvas, draw, stats, theme)
    _draw_text_block(draw, stats, theme)
    _draw_day_tile(canvas, draw, stats, theme)
    _draw_card_border(canvas, theme)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path


def _max_font_size_for_width(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                              lo: int = 10, hi: int = 260) -> int:
    """指定した幅に収まる最大のフォントサイズを二分探索で求める。"""
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        bbox = draw.textbbox((0, 0), text, font=_font(mid))
        if bbox[2] - bbox[0] <= max_width:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def compose_reel_frame(square_image_path: Path, narration_text: str, theme: SeasonTheme,
                        out_path: Path) -> Path:
    """リール動画用の1フレーム(9:16)を作る。上部にフィード用の正方形画像をそのまま置き、
    下部の黒帯にナレーション文をそのまま3行で大きく表示する（音声と同じ文言を字幕的に見せる）。

    3行の分け方は文中の「。」「、」で固定（ナレーション文は日付・残り日数・残り%の
    3要素で構成される前提のため、汎用的な自動折り返しではなくこの前提に合わせている）。
    """
    W, H = STORY_SIZE
    square = Image.open(square_image_path).convert("RGB").resize((W, W), Image.LANCZOS)

    canvas = Image.new("RGB", (W, H), (8, 10, 16))
    canvas.paste(square, (0, 0))
    draw = ImageDraw.Draw(canvas)

    date_part, _, rest = narration_text.partition("。")
    remain_part, _, percent_part = rest.partition("、")
    lines = [
        (date_part + "。", (235, 235, 235)),
        (remain_part + "、", _hex_to_rgb(theme.accent)),
        (percent_part, _hex_to_rgb(theme.accent)),
    ]

    band_top = W
    band_h = H - W
    side_margin = 56
    max_text_width = W - side_margin * 2
    gap = 22
    v_padding = 36

    sizes = [_max_font_size_for_width(draw, text, max_text_width) for text, _ in lines]
    sizes[2] = sizes[1]  # %の行は残り日数の行とサイズを揃える

    def line_heights(sizes):
        return [draw.textbbox((0, 0), text, font=_font(s))[3]
                - draw.textbbox((0, 0), text, font=_font(s))[1]
                for (text, _), s in zip(lines, sizes)]

    heights = line_heights(sizes)
    total_h = sum(heights) + gap * (len(lines) - 1)
    available_h = band_h - v_padding * 2
    if total_h > available_h:
        scale = available_h / total_h
        sizes = [max(10, int(s * scale)) for s in sizes]
        heights = line_heights(sizes)
        total_h = sum(heights) + gap * (len(lines) - 1)

    # textbboxのtop/leftオフセット(フォントの行送り分の余白)を打ち消してから配置しないと、
    # 黒帯の中で見た目の中心がずれる。
    y = band_top + (band_h - total_h) / 2
    for (text, color), size, h in zip(lines, sizes, heights):
        f = _font(size)
        bbox = draw.textbbox((0, 0), text, font=f)
        w = bbox[2] - bbox[0]
        x = (W - w) / 2
        draw_x, draw_y = x - bbox[0], y - bbox[1]
        draw.text((draw_x + 3, draw_y + 4), text, font=f, fill=(0, 0, 0, 180))
        draw.text((draw_x, draw_y), text, font=f, fill=color)
        y += h + gap

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=92)
    return out_path


def compose_story_image(square_image_path: Path, out_path: Path) -> Path:
    """フィード用の正方形(1080x1080)画像を、Instagramストーリーの9:16枠に
    クロップされず全体が収まるよう変換する。上下の余白は同じ画像を拡大・ぼかした
    ものでレターボックス状に埋める。"""
    square = Image.open(square_image_path).convert("RGB")
    w, h = STORY_SIZE

    bg_scale = h / square.height
    bg = square.resize((round(square.width * bg_scale), h), Image.LANCZOS)
    if bg.width >= w:
        left = (bg.width - w) // 2
        bg = bg.crop((left, 0, left + w, h))
    else:
        padded = Image.new("RGB", (w, h), (8, 10, 16))
        padded.paste(bg, ((w - bg.width) // 2, 0))
        bg = padded
    bg = bg.filter(ImageFilter.GaussianBlur(50))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)

    canvas = bg
    canvas.paste(square, (0, (h - square.height) // 2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=92)
    return out_path
