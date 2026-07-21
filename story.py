"""毎日の投稿本文に載せる一言をGeminiのテキスト生成で作る。

以前は「時間の大切さ」を毎日訴える内容にしていたが、単調で説教くさく、
いかにもAIが書いた文章に見えやすかったため撤廃。代わりに、今日という日が
少しでも前向きになるようなジャンルを日替わりでランダムに選ぶ。

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

# 日替わりでランダムに1つ選ぶジャンル。「時間」縛りをやめ、読んだ人の一日が
# 少しでも前向きになる方向で、毎回違う切り口になるようにしている。10ジャンルを
# ローテーションさせ、色んな角度から「心の軽やかさ」を届ける。
_CATEGORIES = [
    {
        "name": "チャレンジの後押し",
        "instruction": (
            "何か新しいことに挑戦したくなるような、背中を押す言葉を書く。"
            "大げさな決意ではなく、今日にでもできる具体的な小さな一歩を"
            "イメージできる内容にする。"
        ),
    },
    {
        "name": "季節感",
        "instruction": (
            "今の季節や気候・行事・旬の食べ物・風物詩など、季節感のある"
            "具体的な話題を1つ取り上げ、そこから生まれる小さな気づきや"
            "味わいを描く。"
        ),
    },
    {
        "name": "偉人の言葉",
        "instruction": (
            "実在する偉人・著名人(思想家、科学者、経営者、アスリート、作家、"
            "芸術家など分野は問わない)の、実際に知られている名言を1つ紹介し、"
            "誰の言葉かを明記した上で、それに一言だけ短い感想や今日への活かし方を"
            "添える。うろ覚えの引用や創作した名言を本物として紹介しない。"
            "名言部分は必ず「」で正しく囲む(開始の「を絶対に忘れない)。"
        ),
    },
    {
        "name": "くすっと笑える話",
        "instruction": (
            "思わずふふっと笑ってしまうような、軽いユーモアのある話や"
            "「あるある」ネタを1つ書く。説教くさくせず、素直に面白がれる"
            "内容にする。"
        ),
    },
    {
        "name": "小さな「まあいっか」の視点",
        "instruction": (
            "完璧主義や悩みで重くなった心をふっと軽くする、思考の転換を書く。"
            "「失敗した時の考え方」「やらなくていいことリスト」「人間関係の"
            "程よい距離感」など、何かを手放すことで楽になるアイデアを1つ描く。"
        ),
    },
    {
        "name": "1日1分のプチセルフケア",
        "instruction": (
            "「これなら今日できるかも」と思える、心理的ハードルが極めて低い"
            "小さな自己愛行動を1つ提案する。「深呼吸を3回する」「お気に入りの"
            "靴を磨く」「空を見上げて肩を下げる」のような、今すぐできる具体的な"
            "行動にする。"
        ),
    },
    {
        "name": "世界／歴史の「へぇ〜」なお話",
        "instruction": (
            "海外の珍しい習慣、意外なものの発祥、生き物の変わった生態など、"
            "「へぇ〜」と思える雑学を1つ紹介し、そこから今日の気分転換に"
            "つなげる。実際に知られている本当の話題を扱い、事実を誇張したり"
            "創作したりしない。細部の記憶が曖昧な場合は断定を避け、伝聞的な"
            "トーンで書く。"
        ),
    },
    {
        "name": "自己肯定感を育てる問いかけ",
        "instruction": (
            "読者が自分自身と対話し、自分の頑張りにふと気づけるような、"
            "軽く答えやすい問いかけを1つ書く。「今日、自分を褒めたい小さな"
            "1つは何？」「今週、一番美味しかったものは？」のような、"
            "コメント欄で気軽に答えられる質問にする。"
        ),
    },
    {
        "name": "失敗からの意外な一発逆転劇",
        "instruction": (
            "「人生、無駄なことはない」と思わせてくれる、失敗や挫折から"
            "生まれた意外な成功のエピソードを1つ紹介する(身近な製品の開発秘話や、"
            "著名人がどん底から立ち直った話など)。実話として広く知られている"
            "ものを扱い、事実と異なる内容を創作しない。細部が不確かな場合は"
            "断定を避け、伝聞的なトーンで書く。"
        ),
    },
    {
        "name": "言葉の処方箋",
        "instruction": (
            "偉人の言葉よりも少しフランクで、感情に寄り添う言葉を1つ届ける。"
            "海外のことわざ(例:「雨が降らなければ虹は見えない」)、心が整う"
            "短歌・和歌、あるいは現代風のポジティブな造語などを紹介する。"
        ),
    },
]


def build_prompt(theme: SeasonTheme, max_length: int, avoid: list[str] | None = None) -> str:
    category = random.choice(_CATEGORIES)
    target = max(max_length - 25, 30)  # 「〜程度」の目安は上限よりしっかり余裕を持たせる
    # 季節への言及は「季節感」ジャンルの時だけ使う。他のジャンルにまで毎回
    # 季節の話を混ぜると、ジャンルを分けた意味が薄れて画一的になるため。
    season_line = f"今は{theme.label}の時期です。\n" if category["name"] == "季節感" else ""

    avoid_block = ""
    if avoid:
        recent_list = "\n".join(f"- {t}" for t in avoid)
        avoid_block = (
            "\n直近の投稿で使った内容(下記と同じ名言・モチーフ・言い回し・出だしは"
            f"絶対に繰り返さないこと):\n{recent_list}\n"
        )
    return (
        f"【最重要・絶対条件】本文は日本語で{max_length}文字以内。これを1文字でも"
        f"超えることは絶対に許されません。{target}文字程度を目安に、文章が"
        "尻切れにならないよう、言いたいことをコンパクトにまとめて完結させてから"
        "出力してください。書き終えたら自分で文字数を数え直し、"
        f"{max_length}文字を超えていたら削って書き直してから答えてください。\n\n"
        "あなたはInstagramで、読んだ人の一日が少し前向きになるような一言を"
        "届けるbotです。\n"
        f"{season_line}\n"
        f"今回のジャンル: {category['name']}\n"
        f"{category['instruction']}\n"
        f"{avoid_block}\n"
        "厳守すること:\n"
        "- 直近使った内容と重複しない、新しい切り口・話題にする。\n"
        "- 季節感ジャンルでない限り、季節や気候の話には触れない。\n"
        "- 「二度と戻らない」「かけがえのない」「気づけば」「ふと」「そっと」「静かに」"
        "「寄せては返す」「儚い」「切なさ」など、いかにもAIが書く定型的な表現は使わない。\n"
        "- 説教くさい断定や「〜しましょう」という押しつけがましい呼びかけで終わらせない。\n"
        "- 比喩は使うとしても1つまで。何重にも重ねない。\n\n"
        f"再確認: 本文は{max_length}文字以内(厳守)。前置きや挨拶、鍵括弧などの"
        "装飾は一切つけず、本文だけを出力してください。"
    )


def _strip_full_wrap(text: str) -> str:
    """Geminiが本文全体を「」や引用符でまるごと囲んでしまった場合だけ、その外側の
    1組を取り除く。文中(特に文頭)に本来含めたい「」がある場合は触らない。"""
    text = text.strip()
    for left, right in (("「", "」"), ('"', '"'), ("'", "'")):
        if len(text) > 1 and text.startswith(left) and text.endswith(right):
            return text[len(left):-len(right)].strip()
    return text


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


def generate_daily_story(theme: SeasonTheme, max_length: int = DEFAULT_MAX_LENGTH,
                         model: str = DEFAULT_MODEL, avoid: list[str] | None = None) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません")

    prompt = build_prompt(theme, max_length, avoid=avoid)

    # Geminiの一時的な混雑(503)は数十秒待てば直ることが多いため、まず本命モデルで
    # リトライする。それでもダメなら、別モデル(lite版)へ1回だけフォールバックする。
    res = _call_gemini(model, prompt, api_key, retry_delays=[10, 30])
    if res is None and model != FALLBACK_MODEL:
        res = _call_gemini(FALLBACK_MODEL, prompt, api_key, retry_delays=[])
    if res is None:
        raise RuntimeError(f"Gemini API error: {model}/{FALLBACK_MODEL} ともに失敗しました")

    data = res.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = _strip_full_wrap(text)
    if len(text) > max_length:
        text = text[:max_length - 1].rstrip() + "…"
    return text
