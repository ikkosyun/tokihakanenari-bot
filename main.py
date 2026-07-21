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

from caption import build_caption, compute_day_stats, extract_story
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

# 日付表示＋残り%表示＋本文を合わせて、この文字数以内に収める(旧Twitterの140字を踏襲)。
CAPTION_TOTAL_LIMIT = 140

# 直近何日分の投稿本文を「重複禁止」としてGeminiに渡すか。
RECENT_HISTORY_DAYS = 7


def _recent_stories(out_dir: Path, target_date: date, days: int = RECENT_HISTORY_DAYS) -> list[str]:
    """直近days日分の、既に保存済みのキャプションから本文だけを集める。
    ファイルが無い日(履歴が浅い/dry-run用ディレクトリ等)は単に読み飛ばす。"""
    recent = []
    for i in range(1, days + 1):
        d = target_date - timedelta(days=i)
        caption_path = out_dir / f"{d.strftime('%Y-%m-%d')}.caption.txt"
        if caption_path.exists():
            recent.append(extract_story(caption_path.read_text(encoding="utf-8")))
    return recent


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

    # 日付＋残り%のヘッダーは文字数制限に含めず、本文だけをCAPTION_TOTAL_LIMIT以内にする。
    recent = _recent_stories(out_dir, target_date)
    daily_story = story.generate_daily_story(theme, max_length=CAPTION_TOTAL_LIMIT, avoid=recent)
    caption = build_caption(stats, theme, daily_story)

    date_str = target_date.strftime("%Y-%m-%d")
    tmp_hourglass = out_dir / f".hourglass-{date_str}.png"
    final_image = out_dir / f"{date_str}.jpg"
    story_image = out_dir / f"{date_str}_story.jpg"

    image_gen.generate_hourglass_image(theme, stats, tmp_hourglass)
    chart.compose_image(tmp_hourglass, stats, theme, final_image)
    tmp_hourglass.unlink(missing_ok=True)
    chart.compose_story_image(final_image, story_image)

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
    import slack_post

    base_url = os.environ["GH_PAGES_BASE_URL"].rstrip("/")
    date_str = (DOCS_IMAGES / "latest.txt").read_text(encoding="utf-8").strip()
    caption = (DOCS_IMAGES / f"{date_str}.caption.txt").read_text(encoding="utf-8")
    image_url = f"{base_url}/images/{date_str}.jpg"
    story_image_url = f"{base_url}/images/{date_str}_story.jpg"

    media_id = instagram_post.post_image(image_url, caption)
    print(f"[publish] Instagramに投稿しました。media_id={media_id}")

    story_id = instagram_post.post_story(story_image_url)
    print(f"[publish] ストーリーにも投稿しました。story_id={story_id}")

    # Slack通知はあくまでおまけ機能。Instagram投稿(本体)が成功していれば、
    # Slack側の一時的な失敗だけでジョブ全体を失敗扱いにはしない。
    try:
        if slack_post.post_image_notification(image_url, caption):
            print("[publish] Slackにも通知を送りました。")
    except Exception as e:
        print(f"[publish] Slack通知に失敗しましたが、Instagram投稿は完了しているため続行します: {e}")


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
