"""毎日の投稿本文に載せる「時間にまつわる小話」をGeminiのテキスト生成で作る。

画像生成モデルと違い、テキスト専用モデルは無料枠が使えるため追加コストはかからない。
"""
import os

import requests

from season import SeasonTheme

DEFAULT_MODEL = os.environ.get("GEMINI_TEXT_MODEL") or "gemini-flash-latest"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MAX_LENGTH = 200


def build_prompt(theme: SeasonTheme) -> str:
    return (
        "あなたはInstagramで「時間の大切さ」を伝えるbotです。"
        f"今は{theme.label}の時期です。"
        "時間の使い方・一日の尊さ・一瞬の大切さについて、読んだ人がハッとするような"
        "短い小話やエピソード、格言的な一言を1つ書いてください。"
        "説教くさくならず、詩的で余韻のある文章にしてください。"
        "季節の情景を軽く絡めても構いません。"
        "文字数は日本語で100〜160文字程度、長くても200文字以内。"
        "前置きや挨拶、鍵括弧などの装飾は一切つけず、本文だけを出力してください。"
    )


def generate_time_story(theme: SeasonTheme, model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    url = f"{API_BASE}/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": build_prompt(theme)}]}]}

    res = requests.post(url, params={"key": api_key}, json=body, timeout=60)
    if not res.ok:
        raise RuntimeError(f"Gemini API error ({res.status_code}): {res.text}")

    data = res.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.strip("「」\"' \n")
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH].rstrip() + "…"
    return text
