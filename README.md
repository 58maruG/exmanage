# Exmanage — レシート撮影で記録する支出管理アプリ

レシートを撮影すると Claude が内容を読み取って商品を分類し、暗号化したデータを
GitHub Pages で公開する家計管理アプリです。日・月・年ごとの支出を、表とグラフで
スマホからいつでも閲覧できます。

公開ダッシュボード: https://58marug.github.io/exmanage/

## 仕組み

```
[iPhone] レシート撮影 → Google ドライブの receipts フォルダへアップロード
   ↓ Google ドライブ デスクトップアプリが PC へ自動同期
[PC] /process-receipts を実行
   ↓ Claude が画像を解析・分類 → data/expenses.json に追記
   ↓ データを暗号化 → docs/expenses.enc → GitHub へ push
[GitHub Pages] 暗号化データ + ダッシュボードを公開
   ↓
[ブラウザ] パスワード入力 → 復号して表・グラフを表示
```

支出データは AES-256-GCM で暗号化され、公開されるのは暗号文（`docs/expenses.enc`）だけです。
平文データ（`data/expenses.json`）と設定（`config.json`）は公開されません。

## 日々の使い方

1. **撮影**: iPhone の Google ドライブアプリで `マイドライブ/Exmanage/receipts` を開き、
   「＋」→「カメラを使用」でレシートを撮影する（何枚でも）
2. **取り込み**: PC でこのフォルダを Claude Code で開き、`/process-receipts` を実行する
3. **確認**: Claude が抽出・分類した内容を表で確認 → 修正があれば指示 → 承認する
4. Claude が暗号化して GitHub へ push する（push 前に確認されます）
5. **閲覧**: ダッシュボード URL をブラウザで開き、パスワードを入力する

## ダッシュボード

- 日 / 月 / 年 の切り替え、◀ ▶ で期間を移動
- カテゴリ別の円グラフ（スライスや凡例をタップすると小分類の内訳へdrill down、「← 戻る」で復帰）
- 支出推移の棒グラフ、レシート一覧（行をタップで商品明細を展開）
- 閲覧パスワードは `config.json` の `dashboard_password`

## セットアップ（初回のみ）

### PC

- **Google ドライブ デスクトップアプリ**をインストールし、Google アカウントでログインする
- **Python 3** と暗号化ライブラリ: `python -m pip install cryptography`

### iPhone

- **設定 → カメラ → フォーマット → 「互換性優先」**（写真を JPEG で保存する）
- **Google ドライブアプリ**を、PC と同じ Google アカウントでログインする

### 設定ファイル（config.json）

```json
{
  "receipts_folder": "レシート画像フォルダのパス",
  "dashboard_password": "閲覧用パスワード",
  "github_pages_url": "公開URL"
}
```

`config.json` は `.gitignore` 済みのため公開されません。

## ファイル構成

```
Exmanage/
├ .claude/commands/process-receipts.md  レシート取り込みコマンドの定義
├ config.json            ローカル設定（パス・パスワード）※非公開
├ data/
│  ├ expenses.json       支出マスターデータ（平文）※非公開
│  ├ categories.json     カテゴリ分類ツリー
│  └ processed.json      処理済み画像の記録
├ tools/encrypt.py       データ暗号化スクリプト（AES-256-GCM）
└ docs/
   ├ index.html          ダッシュボード本体
   └ expenses.enc        暗号化データ（公開対象）
```

## /process-receipts コマンド

`receipts` フォルダ内の未処理レシート画像を解析し、支出データに追加して
ダッシュボードを更新します。処理手順は `.claude/commands/process-receipts.md` に定義しています。

- 未処理画像（`processed.json` に無いもの）だけを対象にします
- データ書き込み前に、抽出・分類結果の確認表が表示されます
- GitHub への push 前には必ず確認されます

## カテゴリ分類について

`data/categories.json` の「大分類 → 小分類」ツリーに従って分類します。
当てはまる小分類が無い場合は Claude が新しい小分類を追加し、ツリーが育っていきます。
分類が不適切なときは、取り込み時に修正を指示してください。
