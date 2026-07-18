"""長期アクセストークン(60日)の有効期限が切れる前に延長するための手動メンテナンススクリプト。

使い方:
    python refresh_token.py
    → 新しいトークンが表示されるので、GitHub Secrets の IG_ACCESS_TOKEN を
      これに更新する（.envのIG_ACCESS_TOKENも合わせて更新しておくと便利）。

60日ごと（できれば50日目くらい）に実行する。放置して期限切れになった場合は、
README「Instagramアプリの認証（初回セットアップ）」の手順をもう一度やり直す必要がある。
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    access_token = os.environ["IG_ACCESS_TOKEN"]
    res = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": access_token},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    print(f"新しいアクセストークン (あと{data['expires_in'] // 86400}日有効):")
    print(data["access_token"])


if __name__ == "__main__":
    main()
