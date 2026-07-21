# 引継ぎドキュメント（tokihakanenari bot）

このプロジェクトを初めて触る人（未来の自分を含む）向けの運用ガイド。
セットアップ手順そのものは [README.md](README.md) を参照。ここでは
「今どう動いているか」「何が壊れやすいか」「壊れたらどうするか」をまとめる。

## 1. これは何か

Instagram (`@tokihakanenari365`) に毎日JST 0:00、「今年の残り日数」を
Gemini生成の砂時計写真＋Pillowで正確に描いた進捗バー・日付とともに自動投稿するbot。
フィード・ストーリーに加えて、同じ内容をナレーション付き動画にしたリールも投稿する
(2026-07-22追加)。GitHub Actionsで完全自動化されている。

## 2. 全体の流れ

```
GitHub Actions (毎日 UTC15:00 = JST0:00, .github/workflows/daily_post.yml)
  1. python main.py --generate
     - Gemini画像生成API(有料)で砂時計写真を作る
       ・季節ごとの背景(season.py)
       ・残り%に応じて砂時計内の砂の量も変える
     - Gemini text API(無料枠)で「時間にまつわる小話」を作る(story.py)
     - Pillow(chart.py)で進捗バー・カレンダータイル・日付文字を正確に合成
     - リール用: Gemini TTS(narration.py)でナレーション音声を生成し、
       chart.compose_reel_frame()で9:16フレーム(上部に正方形画像、下部に
       同じ文言の大きな字幕)を作り、ffmpeg(reel_video.py)で動画化する
     - docs/images/{日付}.jpg / _story.jpg / _reel.mp4 / .caption.txt / latest.txt を書き出す
  2. git commit & push (docs/images 配下)
  3. 60秒待機 (GitHub Pagesの再デプロイ待ち)
  4. python main.py --publish
     - docs/images/latest.txt から今日の画像ファイル名を特定
     - GitHub PagesのURL (https://ikkosyun.github.io/tokihakanenari-bot/images/...)
       を image_url / video_url として Instagram API にフィード→ストーリー→リールの順に投稿
     - リール投稿は失敗してもジョブ全体を失敗扱いにしない(Slack通知と同じ扱い。
       フィード＋ストーリーという本体投稿さえ成功していればよいという判断)
```

ローカルでも同じ関数を個別に叩ける（`main.py --dry-run` / `--generate` / `--publish`）。
GitHub Actionsが動かない・止まっている時は、ローカルでこの3ステップを手動でなぞれば
同じ結果になる（2026-07-19分は実際にこの方法で手動投稿した）。

## 3. 認証情報の在り処（値そのものはここに書かない）

| 名前 | 何に使うか | どこにある |
|---|---|---|
| `GEMINI_API_KEY` | Gemini画像・テキスト生成 | GitHub Secrets / ローカル`.env` |
| `IG_USER_ID` | 投稿先InstagramアカウントID | GitHub Secrets / ローカル`.env` |
| `IG_ACCESS_TOKEN` | Instagram投稿用トークン(60日で失効) | GitHub Secrets / ローカル`.env` |
| `IG_APP_ID` / `IG_APP_SECRET` | トークン更新(`refresh_token.py`)に必要 | ローカル`.env`のみ(Secretsには未登録、更新作業時にのみ必要) |
| `GH_PAGES_BASE_URL` | 画像公開URLのベース | GitHub Variables / ローカル`.env` |

- GitHub側: `https://github.com/ikkosyun/tokihakanenari-bot/settings/secrets/actions`
- Meta側の管理画面: `https://developers.facebook.com/apps/` → `tokihakanenari-bot` アプリ →
  左メニュー `Instagram` → `API setup with Instagram login`（IG_APP_ID/SECRETはここ。
  メインのFacebook App ID/Secretとは別物なので注意、詳細は下記5章）

## 4. 定期メンテナンス

### 60日ごと: Instagramアクセストークンの更新

```bash
cd tokihakanenari-bot
python refresh_token.py
```

出力された新しいトークンを、GitHub Secretsの `IG_ACCESS_TOKEN` に上書き登録する。
**忘れて失効すると、5章のOAuth手順を最初からやり直しになる**ので要注意。
起点: 2026-07-19に再認証済み。次回は2026-09中旬までに更新推奨。

**2026-07-19に発生した実例:** 60日の期限切れではなく、`refresh_token.py`が
`400 Bad Request`で失敗するパターンに遭遇した。Instagram APIのエラーは
`Error validating access token: The session has been invalidated because the
user changed their password or Facebook has changed the session for security
reasons.`(code 190) — Meta側のセキュリティ判定によるセッション無効化で、
ユーザー本人はパスワード変更等の心当たりがなかった（原因不明、Meta側の
自動判定と思われる）。この場合`refresh_token.py`では復旧できず、5章の
OAuth認可フロー（`instagram.com/oauth/authorize`から）を最初からやり直す
必要がある。認可コードは`?code=...`としてリダイレクト先URLに付与される
（`redirect_uri`のページ自体は404で構わない、URLのcodeさえ取れればいい）。

## 5. 既知のハマりどころ

### Gemini画像生成は無料枠が0

`gemini-2.5-flash-image`のような画像出力モデルは、Google Cloud側で
請求先アカウントをリンクしないと1枚も生成できない（無料枠が文字通り0）。
テキスト専用モデル(`gemini-flash-latest`など)は無料枠が別にあり、
`story.py`の小話生成はそちらなので無料。画像1枚あたり約$0.04(≈6.5円)。

### Instagram連携は「Business Login for Instagram」方式

一般的なチュートリアルに多い「Facebookページ連携＋Graph API」方式ではなく、
Pageなしで完結する新しめの認証方式を使っている。ハマりやすい点:

- **App ID/Secretが2種類ある。** アプリ全体の(Facebook用)App ID/Secretと、
  Instagram専用のApp ID/Secret(`Instagram → API setup with Instagram login`ページに表示)
  は別物。認証URLには**Instagram専用の方**を使わないと `Invalid platform app` になる。
- 認証URLは `https://www.instagram.com/oauth/authorize`（`facebook.com/dialog/oauth`ではない）。
  scopeは `instagram_business_basic,instagram_business_content_publish`。
- 投稿したいInstagramアカウントを、アプリの「アプリの役割」→「役割」で
  **Instagramテスター**として追加し(検索はFacebookの実名で行う。IGのユーザー名では出てこない)、
  さらにInstagram側 (`instagram.com/accounts/manage_access/` →
  アプリとウェブサイト → テスターへのご招待) で**承認**しないと
  `Insufficient developer role` になる。
- 取得したアクセストークンでAPIを呼ぶときは **`graph.instagram.com`** 宛てにすること。
  `graph.facebook.com`に投げると `Cannot parse access token` で失敗する
  (`instagram_post.py`の`GRAPH_HOST`はこれに合わせてある)。

### GitHub Actionsの空env変数トラップ

`env: FOO: ${{ vars.FOO }}` で、リポジトリVariable `FOO` が未設定の場合、
`FOO`という環境変数自体は**空文字列**として渡ってくる（未設定にはならない）。
Pythonの `os.environ.get("FOO", "default")` は空文字列があればそれを返してしまい、
デフォルト値にフォールバックしない。`os.environ.get("FOO") or "default"` で回避している。

### 新規cronの初回スキップ

2026-07-18にワークフローを作成した直後、同日15:00 UTC(JST0:00)に予定していた
最初の定期実行が発火しなかった（作成から発火予定まで約2時間42分しかなく、
GitHubのスケジューラに反映が間に合わなかったと見られる）。ワークフロー自体は
`active`で異常なし。**新しく作ったcronの初回だけ様子を見て、鳴らなければ手動で
1回catch-upする**くらいの心構えでよい。2日目以降は正常動作している。

### リール(動画)まわりの注意点

- **コンテナのstatus_codeポーリングは、ユーザーIDの配下にネストしてはいけない。**
  `GET /{ig_user_id}/{creation_id}?fields=status_code` のように書くと、Graph API側が
  `creation_id`をユーザーノードの「フィールド/エッジ名」として解釈しようとし、
  `Tried accessing nonexisting field (数字)` という紛らわしいエラーになる
  (2026-07-22の初回本番投稿テストで遭遇)。正しくは`GET /{creation_id}?fields=status_code`
  とコンテナID自身のノードを直接叩く(`instagram_post._wait_for_container_ready`で修正済み)。
- **ffmpegが必要。** GitHub Actions(ubuntu-latest)には標準搭載なので追加設定不要だが、
  ローカルWindowsでは別途インストールが必要(`winget install Gyan.FFmpeg`)。PATHに
  無い場合は`reel_video._find_ffmpeg()`がwingetの既定インストール先を自動探索する。
- **動画の投稿は写真と違い、Instagram側の処理に時間がかかる。** `instagram_post.post_reel()`
  は固定sleepではなく`status_code`が`FINISHED`になるまでポーリングする(最大5分)。
  `ERROR`になった場合や5分でも終わらない場合は例外を投げる。
- **Reelsタブに掲載される(＝フォロワー以外にも露出する)には9:16・5〜90秒が条件。**
  ナレーション文が極端に短くなる将来的な変更をする場合、動画の尺がこの範囲を
  下回らないか確認すること。
- **同じファイル名(URL)の動画を短時間で複数回投稿すると、Instagram側が古い内容を
  キャッシュして使い回すことがある。** 2026-07-22、レイアウト修正後に同じ
  `2026-07-22_reel.mp4`のURLへ即座に再投稿したところ、GitHub Pages側は新しい
  バイト列を正しく配信していた(Content-Lengthで確認済み)にもかかわらず、
  投稿された動画は修正前の見た目のままだった。原因はおそらくMeta側の取り込み
  パイプラインがURL単位でフェッチ結果をキャッシュしているため。**同じ内容を
  再投稿する場合でも、ファイル名を変える(例: `_v2`サフィックス)ことで
  確実に新しいバイト列を取得させられる。** また、Instagram Graph APIには
  投稿済みメディアを削除するエンドポイントが存在しない
  (`DELETE /{media-id}`は`Unsupported delete request`で失敗する)。誤投稿の
  削除は常にアプリから手動で行う必要がある。
- リールのフレーム画像・ナレーション音声は生成後に削除される一時ファイル
  (`.reel_frame-{日付}.jpg` / `.narration-{日付}.wav`)。docs/imagesに残るのは
  最終的な`{日付}_reel.mp4`だけ。

### Windows特有の環境メモ

- このPCの `python` (PATH上) は32bit版で、多くのパッケージのwheelがなくビルド絶望的。
  `py -V:3.12-arm64` （ネイティブARM64版）を使うこと。
- Git Bashから `py -V:3.12-arm64 相対パス.py` を実行すると
  `No suitable Python runtime found` で失敗することがある。
  **絶対パス**（`py -V:3.12-arm64 "C:\Users\...\script.py"`）を使えば動く。

## 6. デザインの経緯（次に見た目を触るとき用）

何度か作り直している。最終形にたどり着くまでの流れ:

1. 幻想的なイラスト風（縁をぼかして背景に馴染ませる版）→「高級感が足りない」で却下
2. 写真風（砂時計＋蝋燭、参考画像に寄せた版）→ここで方向性が固まる
3. ユーザー要望を反映して順次調整:
   - カレンダー風の日付タイル追加（バインダーリング付きに装飾）
   - 「残り%」表示を大きく光らせて目立たせる
   - 砂時計とバーの間の余白を詰める
   - 月ごとの配色を「抽象的な色」から「具体的な情景」（海、桜、紅葉など）に変更
   - 砂時計内の砂の量を実際の残り%に連動させる（強い数値指定でないとAIが従わない）

現在の実装（`image_gen.py` / `chart.py` / `season.py`）がこの到達点。
見た目をまた変える依頼が来たら、まずこの3ファイルを読むこと。

## 7. トラブルシューティング早見表

| 症状 | まず疑うところ |
|---|---|
| 投稿されていない | GitHub Actionsの実行履歴（`event: schedule`の実行があるか）を確認 |
| Gemini APIが404/quota系エラー | 課金設定が外れていないか、モデル名が deprecated になっていないか |
| Instagram投稿が401/190エラー | `IG_ACCESS_TOKEN`が60日切れていないか → `refresh_token.py` |
| Instagram投稿がその他エラー | `graph.instagram.com`宛てになっているか確認 |
| 画像のPages URLが404 | `docs/.nojekyll`があるか、push後60秒待ったか |
| リール投稿だけ失敗する | ffmpegの有無(ローカルのみ)、`_reel.mp4`のPages URLが404でないか、`post_reel`のポーリングが5分以内に`FINISHED`になっているか |
