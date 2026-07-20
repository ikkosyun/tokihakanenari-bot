"""毎日の投稿本文に載せる「時間にまつわる小話」をGeminiのテキスト生成で作る。

画像生成モデルと違い、テキスト専用モデルは無料枠が使えるため追加コストはかからない。
"""
import os
import random
import time

from season import SeasonTheme

import requests

DEFAULT_MODEL = os.environ.get("GEMINI_TEXT_MODEL") or "gemini-flash-latest"
FALLBACK_MODEL = os.environ.get("GEMINI_TEXT_FALLBACK_MODEL") or "gemini-flash-lite-latest"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MAX_LENGTH = 100

# 「季節の自然描写→教訓」という同じ型に毎回落ち着かないよう、切り口を日替わりでランダムに指定する。
# いずれも「海・波・光」のような抽象的な自然詩ではなく、日常生活の中の一コマが軸。
_ANGLES = [
    "家事の合間（洗濯物をたたむ、お湯を沸かす、皿を洗うなど）にふと訪れる短い時間を描写する",
    "通勤・通学中や、駅・信号待ちなど、移動の途中にある小さな時間の隙間を描写する",
    "一日の中の切り替わりの瞬間（起きた直後、仕事帰り、寝る前など）を描写する",
    "読者に直接語りかける短い問いかけを使う（例: 「〜したのはいつだった？」のような、答えを迫らない軽い問い）",
    "何かを『待っている』時間（お湯が沸く、電車が来る、返信が来るなど）に目を向ける",
]


def build_prompt(theme: SeasonTheme, max_length: int) -> str:
    angle = random.choice(_ANGLES)
    target = max(max_length - 15, 30)  # 「〜程度」の目安は上限より少し余裕を持たせる
    return (
        "あなたはInstagramで「時間の大切さ」を伝えるbotです。"
        f"今は{theme.label}の時期です。"
        "時間の使い方・一日の尊さ・一瞬の大切さについて、読んだ人がハッとするような"
        "詩的な小話や気づきの一言を1つ書いてください。\n\n"
        f"今回の切り口: {angle}\n\n"
        "厳守すること:\n"
        "- 海・波・風・光・季節の移ろいといった、抽象的な自然の詩的表現だけに頼らない。"
        "誰もが経験する日常生活の具体的なワンシーン（家事・通勤・待ち時間など）を必ず情景として描く。\n"
        "- ただし、ブランド名・アプリ名・正確な秒数のような、やたら生々しい実用的情報を並べる"
        "現実的すぎる文章にもしない。あくまで詩的な情景描写として自然に読めるようにする。\n"
        "- 比喩は使うとしても1つまで。何重にも重ねない。\n"
        "- 「二度と戻らない」「かけがえのない」「気づけば」「ふと」「そっと」「静かに」"
        "「寄せては返す」「儚い」「切なさ」など、いかにもAIが書く定型的な表現は使わない。\n"
        "- 説教くさい断定や「〜しましょう」という呼びかけで終わらせない。\n"
        "- 季節の言葉を入れる場合も一言程度に留め、話の中心にはしない。\n\n"
        f"文字数は日本語で{target}文字程度、長くても{max_length}文字以内に必ず収めてください。"
        "前置きや挨拶、鍵括弧などの装飾は一切つけず、本文だけを出力してください。"
    )


def _call_gemini(model: str, prompt: str, api_key: str, retry_delays: list[int]):
    """503(混雑中)なら指定回数リトライする。それ以外のエラー、またはリトライを
    使い切ってもダメだった場合はNoneを返す(例外は投げない)。"""
    url = f"{API_BASE}/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    last_res = None
    for attempt, delay in enumerate([0, *retry_delays]):
        if delay:
            time.sleep(delay)
        res = requests.post(url, params={"key": api_key}, json=body, timeout=60)
        if res.ok:
            return res
        last_res = res
        if res.status_code != 503:
            break
    return None if last_res is None or not last_res.ok else last_res


def generate_time_story(theme: SeasonTheme, max_length: int = DEFAULT_MAX_LENGTH,
                         model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    prompt = build_prompt(theme, max_length)

    # Geminiの一時的な混雑(503)は数十秒待てば直ることが多いため、まず本命モデルで
    # リトライする。それでもダメなら、別モデル(lite版)へ1回だけフォールバックする。
    res = _call_gemini(model, prompt, api_key, retry_delays=[10, 30])
    if res is None and model != FALLBACK_MODEL:
        res = _call_gemini(FALLBACK_MODEL, prompt, api_key, retry_delays=[])
    if res is None:
        raise RuntimeError(f"Gemini API error: {model}/{FALLBACK_MODEL} ともに失敗しました")

    data = res.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.strip("「」\"' \n")
    if len(text) > max_length:
        text = text[:max_length].rstrip() + "…"
    return text
