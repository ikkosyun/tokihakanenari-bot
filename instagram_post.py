"""Instagram Graph APIへの投稿（2ステップ: コンテナ作成 → 公開）。

事前にInstagramアカウントがビジネス/クリエイターアカウント化され、
Facebookページと連携し、instagram_basic / instagram_content_publish
権限を持つアクセストークンを取得していることが前提（README参照）。
"""
import os
import time

import requests

GRAPH_HOST = "https://graph.facebook.com"


def post_image(image_url: str, caption: str) -> str:
    ig_user_id = os.environ["IG_USER_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    api_version = os.environ.get("IG_API_VERSION", "v21.0")

    base = f"{GRAPH_HOST}/{api_version}/{ig_user_id}"

    create_res = requests.post(f"{base}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }, timeout=60)
    _raise_for_status(create_res)
    creation_id = create_res.json()["id"]

    # Instagram側での画像フェッチ・処理待ち
    time.sleep(5)

    publish_res = requests.post(f"{base}/media_publish", data={
        "creation_id": creation_id,
        "access_token": access_token,
    }, timeout=60)
    _raise_for_status(publish_res)

    return publish_res.json()["id"]


def _raise_for_status(res: requests.Response) -> None:
    if not res.ok:
        raise RuntimeError(f"Instagram API error ({res.status_code}): {res.text}")
