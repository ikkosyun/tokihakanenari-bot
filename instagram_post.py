"""Instagram API (Instagram Login) への投稿（2ステップ: コンテナ作成 → 公開）。

事前にInstagramアカウントがビジネス/クリエイターアカウント化され、
「Business Login for Instagram」経由で instagram_business_basic /
instagram_business_content_publish 権限を持つアクセストークンを
取得していることが前提（README参照）。

トークンは graph.facebook.com ではなく graph.instagram.com 宛てに
使う必要がある（Instagramネイティブのログインフローで発行されたトークンのため）。
"""
import os
import time

import requests

GRAPH_HOST = "https://graph.instagram.com"


def _base_url() -> str:
    ig_user_id = os.environ["IG_USER_ID"]
    api_version = os.environ.get("IG_API_VERSION", "v21.0")
    return f"{GRAPH_HOST}/{api_version}/{ig_user_id}"


def _create_container(base: str, access_token: str, image_url: str, **extra) -> str:
    data = {"image_url": image_url, "access_token": access_token, **extra}
    res = requests.post(f"{base}/media", data=data, timeout=60)
    _raise_for_status(res)
    return res.json()["id"]


def _publish_container(base: str, access_token: str, creation_id: str) -> str:
    # Instagram側での画像フェッチ・処理待ち
    time.sleep(5)
    res = requests.post(f"{base}/media_publish", data={
        "creation_id": creation_id,
        "access_token": access_token,
    }, timeout=60)
    _raise_for_status(res)
    return res.json()["id"]


def post_image(image_url: str, caption: str) -> str:
    access_token = os.environ["IG_ACCESS_TOKEN"]
    base = _base_url()

    creation_id = _create_container(base, access_token, image_url, caption=caption)
    return _publish_container(base, access_token, creation_id)


def post_story(image_url: str) -> str:
    """同じ画像をストーリーとして投稿する（media_type=STORIES はキャプション非対応）。"""
    access_token = os.environ["IG_ACCESS_TOKEN"]
    base = _base_url()

    creation_id = _create_container(base, access_token, image_url, media_type="STORIES")
    return _publish_container(base, access_token, creation_id)


def _raise_for_status(res: requests.Response) -> None:
    if not res.ok:
        raise RuntimeError(f"Instagram API error ({res.status_code}): {res.text}")
