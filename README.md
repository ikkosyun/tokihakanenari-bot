# tokihakanenari bot

毎日0時に「今年の残り日数」をテキスト＋Gemini生成イラスト＋棒グラフの画像でInstagramに投稿するbot。
フィード投稿・ストーリーに加えて、同じ内容をナレーション付きの動画にしたリールも投稿する。
月ごとに配色テーマが変わり、季節感を表現する。すべて無料サービスの組み合わせ＋わずかなGemini課金で動く。

## 仕組み（全体像）

```
GitHub Actions（毎日JST 0:00に自動実行・無料）
  → Gemini APIで砂時計イラストを生成
  → Pillow（Python画像処理）で棒グラフと日付を正確に描いて合成
  → Gemini TTSでナレーション音声を生成し、ffmpegでリール動画(mp4)を作成
  → GitHub Pages（無料の公開ホスティング）に画像/動画を置く
  → Instagram Graph APIで、その公開URLを指定してフィード・ストーリー・リールに投稿
```

**リール機能にはffmpegが必要。** GitHub Actions(ubuntu-latest)には標準で入っているため追加設定不要。
ローカルのWindowsで`--dry-run`を試す場合だけ、`winget install Gyan.FFmpeg`等で別途インストールすること。

**なぜGitHub Pagesが必要か:** Instagramへの自動投稿APIは「どこかに公開されている画像のURL」を渡す方式で、ファイルを直接アップロードする方式ではない。そのため、生成した画像を一時的にでも公開の場所に置く必要があり、無料で使えるGitHub Pagesを使っている。

**注意（トレードオフ）:** GitHub Pagesを無料で使うには、リポジトリを **public（誰でも閲覧可能）** にする必要がある。生成画像やコードは公開されるが、個人情報は扱わない設計にしている。

---

## 事前準備（あなたが手動で行う部分）

アカウント作成やパスワード入力を伴う操作はClaudeが代わりに行えないため、以下は手動でお願いします。詰まったら都度聞いてください。

### 1. GitHubアカウント作成 & リポジトリ作成
1. https://github.com で無料アカウントを作成
2. 新規リポジトリを作成（例: `tokihakanenari-bot`）。**Public** を選択
3. このフォルダの中身をそのリポジトリにpush（やり方はここで一緒に進められます）

### 2. GitHub Pagesを有効化
1. リポジトリの `Settings` → `Pages`
2. 「Source」を `Deploy from a branch` にし、ブランチ `main`、フォルダ `/docs` を選択して保存
3. しばらくすると `https://あなたのユーザー名.github.io/tokihakanenari-bot/` が使えるようになる

### 3. Instagramアカウントを「ビジネス/クリエイターアカウント」にする
1. Instagramアプリ → プロフィール編集 → 「プロアカウントに切り替える」
2. カテゴリを選び、ビジネス（またはクリエイター）を選択
   - ※個人情報の公開設定などは自分の判断で選んでください
   - Facebookページとの連携は、この後の認証方式では**不要**（Instagram単体でOK）

### 4. Meta for Developersでアプリを作成し、Instagram側のAPI設定を行う

実際に動作確認できた手順（2026年7月時点、Meta側の仕様変更で今後も変わりうる）:

1. https://developers.facebook.com/apps でアプリを新規作成（タイプ: 「ビジネス」）
2. ダッシュボードで「Instagramでメッセージとコンテンツを管理」のようなユースケースを追加・カスタマイズ
3. 左メニュー「Instagram」→「API setup with Instagram login」を開き、そこに表示される
   **Instagram app ID** と **Instagram app secret**（※メインのアプリID/Secretとは別物）を控える
4. 同じページの「Instagramビジネスログインを設定する」→「ビジネスログイン設定」で、
   「OAuthリダイレクトURI」に `https://あなたのユーザー名.github.io/tokihakanenari-bot/` を追加
5. 左メニュー「アプリの役割」→「役割」→ 人を追加 → 役割「**Instagramテスター**」を選び、
   投稿に使うInstagramのユーザーネームでは検索できないことがあるので、その場合は
   自分の**Facebookプロフィール名**で検索して選ぶ
6. Instagram側（アプリまたは https://www.instagram.com/accounts/manage_access/ ）を開き、
   「アプリとウェブサイト」→「テスターへのご招待」タブで招待を承認する
7. 以下のURLをブラウザで開いてログイン・許可する（`{Instagram app ID}` と `{redirect_uri}` は自分の値に置き換え）:
   ```
   https://www.instagram.com/oauth/authorize?client_id={Instagram app ID}&redirect_uri={redirect_uri}&response_type=code&scope=instagram_business_basic,instagram_business_content_publish
   ```
8. 許可後、リダイレクト先URLの `?code=...#_` の部分（`#_`は除く）が認可コード。これを使って
   `https://api.instagram.com/oauth/access_token` に `client_id`/`client_secret`/`grant_type=authorization_code`/`redirect_uri`/`code` をPOSTすると、
   **短期アクセストークンとIG_USER_ID**が返る（認可コードは数分で失効するので手早く）
9. 短期トークンを `https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=...&access_token=...` にGETして
   **長期アクセストークン（60日間有効）**に交換する

> ⚠️ Meta側のAPI仕様・画面は変更されることがあります。手順通りに進まない箇所があれば、そのままエラーメッセージを教えてください。一緒に対処します（実際、上の手順にたどり着くまでにも何度か仕様変更に当たりました）。

### 6. GitHubリポジトリにシークレットを登録
`Settings` → `Secrets and variables` → `Actions` で以下を登録:

| 種類 | 名前 | 値 |
|---|---|---|
| Secret | `GEMINI_API_KEY` | Gemini APIキー |
| Secret | `IG_USER_ID` | InstagramビジネスアカウントID |
| Secret | `IG_ACCESS_TOKEN` | 長期アクセストークン |
| Variable | `GH_PAGES_BASE_URL` | `https://あなたのユーザー名.github.io/tokihakanenari-bot` |
| Variable | `GEMINI_IMAGE_MODEL` | （任意、省略可）`gemini-2.5-flash-image` |

---

## ローカルでの動作確認（Instagram連携前でもできる）

まず画像とキャプションの見た目だけ、手元で確認できる。

```bash
cd tokihakanenari-bot
pip install -r requirements.txt
cp .env.example .env
# .env を開いて GEMINI_API_KEY だけ埋める

python main.py --dry-run
# 別の月の配色を試したいときは:
python main.py --dry-run --date 2026-12-25
```

`preview/` フォルダに画像とキャプションが出力される。

Windowsでは日本語フォント（游ゴシック/メイリオ）が自動的に見つかるはずだが、
見つからないエラーが出た場合は教えてほしい。

## GitHub Actionsでの本番実行

事前準備がすべて終わったら、GitHubの `Actions` タブ → `Daily Post` →
`Run workflow` で手動実行し、実際にInstagramに投稿されるか1回テストする。
問題なければ、あとは毎日日本時間0時に自動投稿される。

## カスタマイズ

- 配色や季節の言葉を変えたい → `season.py` の `THEMES` を編集
- キャプション文言を変えたい → `caption.py` の `build_caption`
- 棒グラフのデザイン（ブロック数・位置・サイズ）を変えたい → `chart.py`
- Geminiのイラストの雰囲気を変えたい → `image_gen.py` の `build_prompt`
- リールのナレーション文言を変えたい → `narration.py` の `build_narration_text`
- リールのフレームレイアウト（画像/キャプションの配置）を変えたい → `chart.py` の `compose_reel_frame`
- ナレーションの声を変えたい → `.env` の `GEMINI_TTS_VOICE`（Gemini TTSのプリセット音声名）

## メンテナンス: アクセストークンの更新（60日ごと）

Instagramの長期アクセストークンは**60日で失効**する。切れる前（目安: 50日目くらい）に、
以下を実行して新しいトークンを取得し、GitHub Secretsの `IG_ACCESS_TOKEN` を更新する:

```bash
python refresh_token.py
```

期限切れに気づかず失効してしまった場合は、上の「4. Meta for Developers...」の
7〜9番をもう一度やり直す必要がある（トークン取得のやり直し）。
