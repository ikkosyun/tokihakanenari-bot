"""tokihakanenari bot のオーケストレーションスクリプト。

3つのモードで使う:
  --dry-run   画像とキャプションをローカル(preview/)に生成するだけ。投稿しない。
              GitHub Actionsを組む前に、まずこれで見た目を確認する。
  --generate  本番用。docs/images/ に画像を生成し、GitHub Actionsが
              その後 git commit & push して GitHub Pages に公開する。
  --publish   docs/images/ の画像が公開URLで閲覧できる状態になった後に呼び、
              Instagramへ投稿する。

通常は GitHub Actions のワークフローが --generate → (commit/push) → --publish
の順に呼び出す。ローカルでの動作確認は --dry-run だけで完結する。
"""
import argparse
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from caption import build_caption, compute_day_stats
from season import theme_for_month

JST = timezone(timedelta(hours=9))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # GitHub Actionsではsecretsが直接環境変数として渡るので不要

ROOT = Path(__file__).parent
DOCS_IMAGES = ROOT / "docs" / "images"
PREVIEW_DIR = ROOT / "preview"


def _parse_date(value: str | None) -> date:
    if value is None:
        # GitHub Actionsランナーはシステム時刻がUTCのため、date.today()だと
        # JST 0:00〜8:59台に実行された場合に前日の日付になってしまう。
        # 「今日」は常にJSTの暦日で判定する。
        return datetime.now(JST).date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _generate(target_date: date, out_dir: Path) -> tuple[Path, str, str]:
    """画像・キャプションを生成し、(画像パス, ファイル名の日付文字列, キャプション) を返す。"""
    import image_gen
    import chart
    import story

    stats = compute_day_stats(target_date)
    theme = theme_for_month(target_date.month)
    time_story = story.generate_time_story(theme)
    caption = build_caption(stats, theme, time_story)

    date_str = target_date.strftime("%Y-%m-%d")
    tmp_hourglass = out_dir / f".hourglass-{date_str}.png"
    final_image = out_dir / f"{date_str}.jpg"

    image_gen.generate_hourglass_image(theme, stats, tmp_hourglass)
    chart.compose_image(tmp_hourglass, stats, theme, final_image)
    tmp_hourglass.unlink(missing_ok=True)

    return final_image, date_str, caption


def cmd_dry_run(target_date: date) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    image_path, date_str, caption = _generate(target_date, PREVIEW_DIR)
    print(f"[dry-run] 画像を生成しました: {image_path}")
    print("---- キャプション ----")
    print(caption)


def cmd_generate(target_date: date) -> None:
    DOCS_IMAGES.mkdir(parents=True, exist_ok=True)
    image_path, date_str, caption = _generate(target_date, DOCS_IMAGES)

    (DOCS_IMAGES / f"{date_str}.caption.txt").write_text(caption, encoding="utf-8")
    (DOCS_IMAGES / "latest.txt").write_text(date_str, encoding="utf-8")

    print(f"[generate] 画像を生成しました: {image_path}")


def cmd_publish() -> None:
    import instagram_post

    base_url = os.environ["GH_PAGES_BASE_URL"].rstrip("/")
    date_str = (DOCS_IMAGES / "latest.txt").read_text(encoding="utf-8").strip()
    caption = (DOCS_IMAGES / f"{date_str}.caption.txt").read_text(encoding="utf-8")
    image_url = f"{base_url}/images/{date_str}.jpg"

    media_id = instagram_post.post_image(image_url, caption)
    print(f"[publish] Instagramに投稿しました。media_id={media_id}")

    story_id = instagram_post.post_story(image_url)
    print(f"[publish] ストーリーにも投稿しました。story_id={story_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--publish", action="store_true")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD（省略時は今日）")
    args = parser.parse_args()

    target_date = _parse_date(args.date)

    if args.dry_run:
        cmd_dry_run(target_date)
    elif args.generate:
        cmd_generate(target_date)
    elif args.publish:
        cmd_publish()


if __name__ == "__main__":
    main()
