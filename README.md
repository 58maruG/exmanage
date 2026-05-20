# Exmanage — レシート撮影で記録する支出管理アプリ

レシートを撮影すると Claude が内容を読み取って商品を分類し、暗号化したデータを
GitHub Pages で公開する家計管理アプリです。日・月・年ごとの支出を、表とグラフで
スマホからいつでも閲覧できます。**PC 不要、iPhone だけで完結します。**

公開ダッシュボード: https://58marug.github.io/exmanage/

## 仕組み

```
[iPhone]
  レシートを撮影 → Google ドライブの receipts フォルダへアップロード
       ↓
[Claude Code（iPhone アプリ または ブラウザ）]
  /process-receipts を実行
  1. expenses.enc を復号 → expenses.json を生成
  2. Google Drive から未処理画像をダウンロード
  3. Claude が画像を解析・分類
  4. 確認表を表示 → ユーザーが承認・修正
  5. expenses.json に追記 → 再暗号化 → GitHub へ push
       ↓
[GitHub Pages]
  暗号化データ (expenses.enc) + ダッシュボード (index.html) を公開
       ↓
[ブラウザ（iPhone・PC どこからでも）]
  パスワードを入力 → 復号して表・グラフを表示
```

支出データは AES-256-GCM で暗号化され、公開されるのは暗号文（`docs/expenses.enc`）だけです。
平文データ（`data/expenses.json`）と設定（`config.json`）は公開されません。

## 日々の使い方

1. **撮影**: iPhone の Google ドライブアプリで `マイドライブ/Exmanage/receipts` を開き、
   「＋」→「カメラを使用」でレシートを撮影する（何枚でも）
2. **取り込み**: Claude Code アプリ（iPhone）またはブラウザで `/process-receipts` を実行する
3. **確認**: Claude が抽出・分類した内容を表で確認 → 修正があれば指示 → 承認する
4. Claude が暗号化して GitHub へ push する（push 前に確認されます）
5. **閲覧**: ダッシュボード URL をブラウザで開き、パスワードを入力する

## ダッシュボード

- 日 / 月 / 年 の切り替え、◀ ▶ で期間を移動
- カテゴリ別の円グラフ（スライスや凡例をタップすると小分類の内訳へ drill down、「← 戻る」で復帰）
- 支出推移の棒グラフ、レシート一覧（行をタップで商品明細を展開）
- 閲覧パスワードは `DASHBOARD_PASSWORD` 環境変数（またはローカルの `config.json`）で管理

## セットアップ（初回のみ）

### iPhone

- **設定 → カメラ → フォーマット → 「互換性優先」**（写真を JPEG で保存する）
- **Google ドライブアプリ**をインストールし、Google アカウントでログインする

### code.claude.com の環境変数

[code.claude.com](https://code.claude.com) のプロジェクト設定に以下を追加する:

| 変数 | 内容 |
|---|---|
| `DASHBOARD_PASSWORD` | ダッシュボードの閲覧パスワード |
| `GDRIVE_CLIENT_ID` | Google Cloud の OAuth クライアント ID |
| `GDRIVE_CLIENT_SECRET` | OAuth クライアントシークレット |
| `GDRIVE_REFRESH_TOKEN` | OAuth リフレッシュトークン |

Google Drive の OAuth 認証情報は Google Cloud Console で取得する（Drive API を有効化し、
デスクトップアプリ用の OAuth クライアントを作成）。

### ローカル（PC）で使う場合

PC に Python 3 と依存ライブラリをインストールし、`config.json` を作成する:

```bash
python -m pip install cryptography
```

```json
{
  "receipts_folder": "Google ドライブの receipts フォルダのローカルパス",
  "dashboard_password": "閲覧用パスワード"
}
```

`config.json` は `.gitignore` 済みのため公開されません。

## ファイル構成

```
Exmanage/
├ .claude/commands/process-receipts.md  レシート取り込みコマンドの定義
├ config.json            ローカル設定（パス・パスワード）※非公開・gitignore済み
├ data/
│  ├ expenses.json       支出マスターデータ（平文）※非公開・gitignore済み
│  ├ categories.json     カテゴリ分類ツリー
│  └ processed.json      処理済み画像の記録
├ tools/
│  ├ encrypt.py          データ暗号化スクリプト（AES-256-GCM）
│  ├ decrypt.py          データ復号スクリプト（クラウド環境用）
│  └ gdrive_download.py  Google Drive から画像をダウンロードするスクリプト
└ docs/
   ├ index.html          ダッシュボード本体
   └ expenses.enc        暗号化データ（公開対象）
```

## /process-receipts コマンド

Google Drive の `receipts` フォルダ内の未処理レシート画像を解析し、支出データに追加して
ダッシュボードを更新します。処理手順は `.claude/commands/process-receipts.md` に定義しています。

- クラウド環境では `expenses.enc` を自動復号し、Google Drive から画像を取得します
- 未処理画像（`processed.json` に記録のないもの）だけを対象にします
- データ書き込み前に、抽出・分類結果の確認表が表示されます
- GitHub への push 前には必ず確認されます

## カテゴリ分類について

`data/categories.json` の「大分類 → 小分類」ツリーに従って分類します。
当てはまる小分類が無い場合は Claude が新しい小分類を追加し、ツリーが育っていきます。
分類が不適切なときは、取り込み時に修正を指示してください。

## セキュリティ

- 支出データの平文（`expenses.json`）は GitHub に上がらない
- 公開されるのは暗号文（`expenses.enc`）のみ
- 暗号化方式は AES-256-GCM（PBKDF2-SHA256、反復20万回）
- `DASHBOARD_PASSWORD` は強力なランダムパスワードを使うことを推奨
- Google Drive の OAuth リフレッシュトークンは定期的に再発行することを推奨
