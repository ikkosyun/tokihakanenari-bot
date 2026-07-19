"""生成した画像をSlack Incoming Webhook経由で通知として送る。

Instagram投稿とは独立したオプション機能。SLACK_WEBHOOK_URLが未設定の場合は
何もせずスキップする(Slack通知を使わない環境でもエラーにしない)。
"""
import os

import requests


def post_image_notification(image_url: str, caption: str) -> bool:
    """caption先頭行のテキストと画像をSlackに投稿する。送信したらTrue、
    SLACK_WEBHOOK_URL未設定でスキップしたらFalseを返す。"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False

    text = caption.strip().splitlines()[0]
    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "image", "image_url": image_url, "alt_text": "今日の残り日数"},
        ],
    }
    res = requests.post(webhook_url, json=payload, timeout=30)
    if not res.ok:
        raise RuntimeError(f"Slack Webhook error ({res.status_code}): {res.text}")
    return True
