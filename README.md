# tokihakanenari bot

毎日0時に「今年の残り日数」をテキスト＋Gemini生成イラスト＋棒グラフの画像でInstagramに投稿するbot。
月ごとに配色テーマが変わり、季節感を表現する。すべて無料サービスの組み合わせで動く。

## 仕組み（全体像）

```
GitHub Actions（毎日JST 0:00に自動実行・無料）
  → Gemini APIで砂時計イラストを生成
  → Pillow（Python画像処理）で棒グラフと日付を正確に描いて合成
  → GitHub Pages（無料の公開ホスティング）に画像を置く
  → Instagram Graph APIで、その公開URLを指定して投稿
```

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

### 4. Facebookページを作成し、Instagramアカウントとリンク
1. https://www.facebook.com/pages/create でページを新規作成（無料。フォロワーがいなくてもOK、API連携用の器として使う）
2. Instagramアプリの「プロアカウント設定」→「Facebookとの連携」から、作成したページとリンク

### 5. Meta for Developersでアプリを作成
1. https://developers.facebook.com/apps でアプリを新規作成（タイプ: 「ビジネス」）
2. 作成したアプリに「Instagram Graph API」の製品を追加
3. 「Graph APIエクスプローラー」またはAPIセットアップ画面から、以下を取得:
   - `IG_USER_ID`（あなたのInstagramビジネスアカウントの数値ID）
   - アクセストークン（`instagram_basic`, `instagram_content_publish` 権限を含むもの）
4. 取得した短期トークンは、Meta公式ドキュメントの手順に沿って **長期トークン（60日間有効）** に交換しておく
5. アプリが「開発モード」の場合、あなた自身のアカウントが「テスター」として使えるようになっているか確認する（Instagramアプリの「アプリとウェブサイト」からテスター招待を承認）。もし投稿時に権限エラーが出る場合は、Meta側の「App Review」申請（無料）が必要になることがある

> ⚠️ Meta側のAPI仕様・画面は変更されることがあります。手順通りに進まない箇所があれば、そのままエラーメッセージを教えてください。一緒に対処します。

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
