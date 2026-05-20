---
description: receiptsフォルダの新しいレシート画像を解析・分類し、ダッシュボードを更新する
allowed-tools: Read, Write, Edit, Bash, Glob
---

# レシート自動取り込み・分類

Google Drive の `receipt` フォルダからレシート画像を取得し、支出データに追加してダッシュボードを更新する。
作業はすべて日本語で報告すること。

## 手順

### 0. Google Drive からダウンロード
**依存パッケージのインストール（クラウド環境では毎回必要）:**
```
pip install --ignore-installed cryptography google-auth google-api-python-client google-auth-httplib2 -q
```

- `GDRIVE_CLIENT_ID` 環境変数が設定されているか確認する
  - 未設定なら「Google Drive 認証情報が設定されていません。`GDRIVE_CLIENT_ID` / `GDRIVE_CLIENT_SECRET` / `GDRIVE_REFRESH_TOKEN` をプロジェクト設定で追加してください。」と伝えて終了する
- `python tools/gdrive_download.py` を実行する
  - スクリプトは Google Drive の `receipt` フォルダにある画像をローカルの `receipts/` へダウンロードし、GDrive 上のファイルを `Read receipt(仮)` フォルダへ自動移動する
  - 出力の `downloaded` リストが空なら「新しい画像がありませんでした」と伝えて終了する
  - `errors` リストに項目があれば、その画像をスキップしてユーザーへ報告する

### 1. データの読み込み
**`data/expenses.json` が存在しない場合（クラウド環境）:**
- `DASHBOARD_PASSWORD` 環境変数が設定されているか確認する
  - 未設定なら「`DASHBOARD_PASSWORD` 環境変数が必要です。プロジェクト設定で追加してください。」と伝えて終了する
- `python tools/decrypt.py` を実行して `docs/expenses.enc` から `data/expenses.json` を復号する
- 失敗した場合はエラーを報告して終了する

- `data/processed.json` を読み、処理済み画像ファイル名の一覧を取得する
- `data/categories.json` を読み、現在のカテゴリツリー（大分類→小分類）を把握する
- `data/expenses.json` を読み、既存レシートとID採番状況を把握する

### 2. 未処理画像の特定
- `receipts/` フォルダにある画像ファイル（.jpg .jpeg .png）を Glob で一覧する
- `processed.json` の一覧に無いファイルが「未処理画像」
- 未処理が0件なら、その旨を伝えて終了する
- HEIC形式の画像があれば、iPhoneのカメラ設定を「互換性優先（JPEG保存）」にするようユーザーへ案内する

### 3. 各画像の解析（1枚ずつ Read で画像を開く）
各レシート画像から以下を抽出する:
- **日付**: `YYYY-MM-DD` 形式に正規化する（「2026/5/19」「令和8年5月19日」等も変換）
- **店名**: レシート上部の店舗名
- **支払方法**: 現金 / クレジットカード / 電子マネー / QR決済 / その他 のいずれか（記載から判断、不明なら「不明」）
- **商品明細**: 各商品の「商品名」と「値段」（整数・円）
  - 値引き・割引行は直前の商品の値段に反映する
  - 小計・消費税・合計・お預り・お釣り・ポイントは商品として登録しない
  - 軽減税率対象を示す記号（※ 等）は商品名から除く

抽出のコツ:
- 読み取れない項目は推測せず「不明」とし、ユーザーに報告する
- 画像が不鮮明で解析不能な場合は、その画像をスキップして報告する（処理済みにしない）

### 4. 商品の分類
各商品を `categories.json` の大分類→小分類に分類する:
- 商品名から中身を判断する（例: おかめ納豆→食料品/豆類、JOY→日用品/洗剤）
- 既存の小分類に当てはまればそれを使う
- 当てはまる小分類が無いが大分類は合う場合、新しい小分類を作って `categories.json` に追記してよい
- 当てはまる大分類が無い場合は「その他/その他」にする（新しい大分類は安易に作らない）

### 5. ユーザーへ確認
データに書き込む前に、抽出・分類結果をレシートごとの表で提示する
（日付 / 店名 / 支払方法 / 商品名 / 値段 / 大分類 / 小分類）。
「この内容で登録してよいか、修正点はあるか」をユーザーに確認する。
修正指示があれば反映してから次へ進む。

### 6. データへの反映（ユーザー確認・修正後）
- 各レシートに `id` を採番する（`YYYYMMDD-NNN` 形式、同一日付内で001から連番）
- `image` に元画像のファイル名を記録する
- `data/expenses.json` の `receipts` 配列へ追加する（順序は問わない。ダッシュボード側でソートする）
- 新しい小分類を作った場合は `data/categories.json` を更新する
- 処理した画像ファイル名を `data/processed.json` の `processed` 配列へ追加する
- スキップした画像は `processed.json` に追加しない

### 7. 暗号化
- `config.json` が存在する場合: `python tools/encrypt.py` を実行する
- `config.json` が存在しない場合（クラウド環境）: `python tools/encrypt.py $DASHBOARD_PASSWORD` を実行する
- コマンドが成功したことを確認する

### 8. GitHubへ公開（commit & push）
- 変更ファイルをステージする:
  `git add docs/expenses.enc data/categories.json data/processed.json`
  （`config.json` と `data/expenses.json` は .gitignore 済みのためコミットされない）
- 取り込んだ内容が分かるコミットメッセージでコミットする
  （例: 「レシート3件を追加（2026-05-20〜2026-05-22）」）
- **push する前に、必ずユーザーへ「公開サイトに反映してよいか」を確認する**
- 確認が取れたら `git push` する。GitHub Pages への反映には数分かかる
- ユーザーが今は公開しないと答えた場合は、コミットだけ済ませて push は保留する

### 9. 結果報告
取り込んだレシート数・商品数・合計金額、スキップした画像、追加した小分類、
公開状況（push済みか保留か）を日本語でまとめて報告する。

## 注意事項
- 破壊的操作はしない。`expenses.json` は追記のみ行う
- I/Oエラー時は分かりやすい日本語で報告し、途中まででも安全に中断する
- 同じ画像を二重登録しないため、`processed.json` のチェックを必ず行う
- 1枚のレシートに複数の商品がある場合、すべて `items` 配列に入れる
