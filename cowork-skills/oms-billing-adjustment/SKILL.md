---
name: oms-billing-adjustment
description: |
  OMS課金（受注在庫一元化システム利用料）の月次調整額を、CSV生成から投入後の突合まで支援するスキル。
  請求に直結するため、投入と送信は必ず人間が行い、Claude は生成・検証・レポート作成までを担う。

  以下のリクエストで必ず使用する：
  - 「OMS課金の調整額を作って」「調整額CSVを生成して」「今月のOMS請求を回して」
  - 「OMS課金のチェックをして」「調整額の検証をして」「請求漏れがないか見て」
  - 「調整額を登録したので確認して」「投入後のチェックをして」（投入後フェーズ）
  - 「OMS課金の月次レポートを作って」「先月比を出して」
  - 「/oms-billing-adjustment」、毎月月初の定期実行
  O-musubi・調整額・OMS課金・一元管理システム利用料・請求開始日といった語が出たらほぼ確実にトリガーする。
compatibility: |
  Google Drive MCP（スプレッドシート読み取り・Drive へのファイル作成）が必要。
  GAS の実行トリガーを使う場合は、調整額生成ツールに Web App エンドポイントを設置しておくこと（references/gas-endpoint.md）。
---

# OMS課金 調整額スキル

毎月の OMS課金（受注在庫一元化システム利用料）の調整額登録を支援する。

## このスキルの絶対原則

請求業務であり、誤りは荷主への誤請求に直結する。次の3点は例外なく守る。

1. **Admin への CSV 投入は Claude が行わない。** 必ず人間が投入する。
2. **Slack への登録完了連絡は Claude が送らない。** 下書きまで作り、送信は人間が行う。
3. **BLOCKER が1件でも残っているうちは投入を勧めない。** 「たぶん大丈夫」で通さない。

金額の判断を Claude の暗算に任せない。金額の再計算・突合はすべて
`scripts/verify_oms_adjustment.py` に行わせ、その出力だけを根拠にする。

## 全体の流れ

```
[1] 生成フェーズ    Claude : データ更新 → CSV生成 → 投入前チェック → レポート/CSVをDriveへ保存
                             ↓ BLOCKER が0件になるまでここを繰り返す
[2] 投入フェーズ    人間   : Drive の CSV を Admin の 請求＞調整額＞CSVアップロード から投入
[3] 突合フェーズ    Claude : 登録結果を取得し、投入したCSVと1行ずつ突合 → レポート更新
[4] 報告フェーズ    人間   : Claude が作った下書きを確認し、Slack へ登録完了連絡
```

対象月は「前月」。9月1日に実行するなら対象月は `2026-08`、対象日は `2026-08-31`。
ユーザーが対象月を指定しなかった場合は前月と解釈し、**必ず対象月を明示して確認を取ってから進む**。

## 作業ディレクトリ

`work/oms-billing/{対象月}/` に中間ファイルを置く。前月分は前月比較に使うので消さない。

```
work/oms-billing/2026-08/
  sheets_dump.json      スプレッドシートの読み取り結果
  master.tsv            以下 parse_oms_sheets.py が生成
  target_data.tsv
  create_csv.tsv
  bill_adjustments.tsv
  report.json           投入前チェックの結果
  report_post.json      投入後チェックの結果
  monthly_report.md     月次レポート
  slack_draft.md        Slack報告文ドラフト
  oms_adjustment_2026-08.csv  Admin へ投入する CSV
```

---

## フェーズ1：生成と投入前チェック

### 1-1. 対象月を確定する

前月を既定とし、ユーザーに一言で確認する。「対象月は 2026-08（対象日 2026-08-31）で進めます」。

### 1-2. 元データを更新する

調整額生成ツールの GAS を叩き、master と Target_data を最新にする。
手順は `references/gas-endpoint.md` を読むこと。要点だけ書くと：

- Web App エンドポイントが設置済みなら `curl` で `action=refresh_all` を叩く。
- 設置されていない、または呼び出しに失敗したら、**自分で回避策を作らずユーザーにメニュー実行を依頼する**。
  依頼文: 「調整額生成ツールを開き、カスタムメニュー＞マルチチャネルデータを更新、続けて BigQuery データを更新、
  最後に 調整額CSV生成 を実行してください。終わったら『完了』と返してください」

エンドポイントは実行のトリガーだけを行い、荷主データは返さない。データは必ず
Google Drive MCP（ユーザーの認証で読む経路）から取得する。

### 1-3. シートを読み取って TSV に分解する

Google Drive MCP の `read_file_content` で調整額生成ツールを読む。
出力が大きくファイルに退避された場合は、そのファイルをそのまま入力に使ってよい。

```bash
python3 scripts/parse_oms_sheets.py \
  --input work/oms-billing/2026-08/sheets_dump.json \
  --outdir work/oms-billing/2026-08
```

`master.tsv` `target_data.tsv` `create_csv.tsv` `bill_adjustments.tsv` が揃わなければ先へ進まない。
読み取りが途中で切れている可能性があるので、その旨をユーザーに伝えて読み直す。

### 1-4. 投入前チェックを走らせる

```bash
python3 scripts/verify_oms_adjustment.py \
  --term 2026-08 \
  --master        work/oms-billing/2026-08/master.tsv \
  --target-data   work/oms-billing/2026-08/target_data.tsv \
  --create-csv    work/oms-billing/2026-08/create_csv.tsv \
  --prev-create-csv work/oms-billing/2026-07/create_csv.tsv \
  --json          work/oms-billing/2026-08/report.json
```

前月の `create_csv.tsv` が手元になければ、Drive に保存した前月の CSV を落として使う。
それも無ければ `--prev-create-csv` を外し、**前月比が取れていないことをレポートに明記する**。

チェック項目の意味と対処は `references/checks.md` にある。BLOCKER が出たら必ず参照する。

### 1-5. BLOCKER を解消する

BLOCKER の多くは Claude 側では直せない。原因ごとに誰が何をするかを整理してユーザーに渡す。

| BLOCKER | 直し方 | 直す人 |
| --- | --- | --- |
| `coverage.請求漏れ` | master の請求開始日/終了日を確認し、必要なら Admin で修正して再生成 | 人間 |
| `coverage.過剰請求` | 請求終了日の登録漏れが濃厚。Admin で登録して再生成 | 人間 |
| `coverage.master不在` | 荷主コードの誤り、または master 抽出条件から外れている。原因特定が必要 | 人間 |
| `master.請求開始日未登録` | 規約合意済みの荷主に請求開始日（合意月の1日）を登録して再生成 | 人間 |
| `amount.再計算不一致` | GAS の計算ロジックか単価表が変わっている疑い。**投入せず必ず原因を特定する** | 人間 |
| `memo.*` | 調整理由テンプレートと金額の不整合。GAS のテンプレートを確認 | 人間 |
| `csv.*` / `format.*` | CSV 生成の設定ずれ。GAS 側を直して再生成 | 人間 |

修正後は 1-2 からやり直し、BLOCKER が0件になるまで繰り返す。
**Claude が create_csv の中身を手で書き換えて BLOCKER を消すことは禁止**。
生成ロジックを直さずに出力だけ繕うと、翌月も同じ誤りが出る。

WARN は解消しなくても投入できるが、**1件ずつユーザーに提示して判断を仰ぐ**。黙って流さない。

### 1-6. 投入用 CSV とレポートを作る

`create_csv.tsv` から Admin 投入用の CSV を書き出す。列順・固定値はチェック済みのものをそのまま使う。

```bash
python3 scripts/oms_monthly_report.py \
  --term 2026-08 \
  --report        work/oms-billing/2026-08/report.json \
  --master        work/oms-billing/2026-08/master.tsv \
  --target-data   work/oms-billing/2026-08/target_data.tsv \
  --create-csv    work/oms-billing/2026-08/create_csv.tsv \
  --prev-create-csv work/oms-billing/2026-07/create_csv.tsv \
  --out-report    work/oms-billing/2026-08/monthly_report.md \
  --out-slack     work/oms-billing/2026-08/slack_draft.md
```

Google Drive MCP の `create_file` で、`OMS課金/調整額/{対象月}/` フォルダに次を保存する。
あとから誰でも追えることが目的なので、投入した CSV そのものも必ず残す。

- `monthly_report.md`（Google ドキュメントとして保存し、URL をユーザーに渡す）
- `oms_adjustment_{対象月}.csv`（人間がここからダウンロードして投入する）
- `report.json`

### 1-7. ユーザーに引き渡す

チャットには次を短く出す。長いレポート本文をチャットに貼らない。

- 対象月、請求社数、請求総額、前月比（社数・総額）
- BLOCKER 件数（0であること）と WARN の一覧
- 月次レポートの URL、投入用 CSV の URL
- 次にやること：「Admin ＞ 請求 ＞ 調整額 ＞ CSVアップロード から投入してください。終わったら『投入した』と教えてください」

---

## フェーズ2：投入（人間）

Claude は待つ。Admin へアクセスしない。

---

## フェーズ3：投入後の突合

ユーザーから「投入した」と連絡が来たら実行する。

### 3-1. 登録結果を取得する

GAS の `action=fetch_bill_adjustments`（またはユーザーにカスタムメニュー＞調整額登録結果を取得を依頼）で
`bill_adjustments` シートを更新し、1-3 と同じ手順で読み直す。

### 3-2. 突合する

```bash
python3 scripts/verify_oms_adjustment.py \
  --term 2026-08 \
  --master           work/oms-billing/2026-08/master.tsv \
  --target-data      work/oms-billing/2026-08/target_data.tsv \
  --create-csv       work/oms-billing/2026-08/create_csv.tsv \
  --bill-adjustments work/oms-billing/2026-08/bill_adjustments.tsv \
  --json             work/oms-billing/2026-08/report_post.json
```

ここで見るのは次の4つ。1件でも出たら**登録は未完了**として扱い、Slack 報告に進まない。

- `post.登録されていない`：CSV の一部が取り込まれていない
- `post.二重登録`：同じ CSV を2回投入した
- `post.金額不一致`：登録額が CSV と違う
- `post.CSVにない登録`：手入力など想定外の登録が混ざっている

### 3-3. レポートを更新する

`report_post.json` を反映して月次レポートを作り直し、Drive の同じファイルを更新する（新規作成しない）。
「登録済み件数」「登録済み総額」が投入した CSV と一致していることをレポートに明記する。

---

## フェーズ4：Slack 報告（下書きまで）

`slack_draft.md` をユーザーに提示する。**Claude は送信しない。**

下書きには次が入っていること。

- 対象月、請求社数（前月比）、請求総額（前月比）
- 新規に請求開始した荷主、請求終了した荷主
- 月次レポートの URL
- ダブルチェック依頼の一文

ユーザーが「送っておいて」と言った場合も、Slack への投稿は請求内容の外部発信にあたるため、
送信先チャンネルと本文を確認してもらってから送る。確認なしに送らない。

運用上の締め切りは**登録完了連絡を15時まで**。時間が押している場合はそれを先に伝える。

---

## やってはいけないこと

- Admin（オープンロジ管理画面）へアクセスする
- create_csv の中身を手で編集して BLOCKER を消す
- 金額を Claude が暗算して「合っています」と報告する
- BLOCKER を WARN として報告する、件数を丸める
- 荷主名・荷主コード・金額を含むデータを article-creator リポジトリにコミットする
  （`work/` は `.gitignore` 対象。コミット前に必ず `git status` で確認する）
- 前月比が取れていないのに、取れたかのようにレポートに書く

## 参照

- `references/checks.md` — チェック項目の一覧と、それぞれの対処
- `references/gas-endpoint.md` — GAS の呼び出し口の設計と設置手順
- `references/data-sources.md` — データの出どころ、Redash 依存を外す方針
- `assets/gas_oms_endpoint.gs` — 調整額生成ツールに追加する GAS コード
