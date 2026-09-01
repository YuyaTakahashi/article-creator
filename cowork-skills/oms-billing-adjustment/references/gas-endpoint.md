# GAS の呼び出し口（設置手順と使い方）

調整額生成ツールのカスタムメニューは、人が画面から押す前提で作られている。
Claude から実行するために、Web App のエンドポイントを1つ足す。

## なぜこの形なのか

Cowork のサンドボックスからは `script.google.com` に到達できる。一方で
Google のスプレッドシートや Drive を認証つきで読む経路は Google Drive MCP しかない。
そこで役割を分ける。

- **GAS Web App**：実行のトリガーだけを担う。荷主コード・金額・社名を一切返さない。
  返すのは「何行になったか」「対象日はいつか」といったメタ情報のみ。
- **Google Drive MCP**：請求データの取得を担う。利用者本人の Google 認証を通る。

こうしておくと、エンドポイントの URL とトークンが漏れても、
できるのは「データの再取得を走らせること」だけで、請求データは読めない。
調整額の登録や削除もエンドポイントからは行えない。

## 設置手順（一度だけ）

1. 調整額生成ツールを開き、拡張機能 ＞ Apps Script。

2. `assets/gas_oms_endpoint.gs` の内容を新しいファイルとして貼る。

3. ファイル冒頭の `ACTION_FUNCTIONS` を、既存プロジェクトの実際の関数名に書き換える。
   既存の `onOpen()` を開き、`addItem('マルチチャネルデータを更新', 'xxx')` の第2引数をそのまま写す。
   `SHEETS` と `CREATE_CSV_HEADER_ROW` も実際のシート名・行番号に合わせる。

4. スナップショットの保存先フォルダを Drive に作り、その ID を `SNAPSHOT_FOLDER_ID` に入れる。
   （例：マイドライブ ＞ OMS課金 ＞ 調整額。フォルダを開いたときの URL 末尾が ID）

5. トークンを決めてスクリプトプロパティに入れる。
   プロジェクトの設定 ＞ スクリプト プロパティ ＞ プロパティを追加。
   - プロパティ名：`OMS_ENDPOINT_TOKEN`
   - 値：推測されない十分に長い文字列（32文字以上のランダム文字列）

6. デプロイ ＞ 新しいデプロイ ＞ 種類：ウェブアプリ。
   - 次のユーザーとして実行：自分
   - アクセスできるユーザー：全員
   （「全員」にするのは、トークンを知らないと何もできない作りにしているため。
   トークンなしのアクセスはすべて `トークンが一致しない` で弾かれる）

7. 発行された URL を控える。**この URL とトークンは請求システムへの入口なので、
   リポジトリにコミットしない。**Cowork の環境変数か、ユーザーが都度貼る形で渡す。

8. Apps Script のエディタで `installMonthlyTrigger` を一度手で実行する。
   毎月1日 7時に自動でデータ更新と CSV 生成が走るようになる。
   エンドポイントの呼び出しが失敗しても、月初のデータが揃っている状態を作るための保険。

## 使い方

```bash
# 月初の一連の流れ（master更新 → BigQuery更新 → CSV生成 → Driveへスナップショット）
curl -sS "${OMS_ENDPOINT_URL}?token=${OMS_ENDPOINT_TOKEN}&action=refresh_all"

# 投入後、登録結果を取り込む
curl -sS "${OMS_ENDPOINT_URL}?token=${OMS_ENDPOINT_TOKEN}&action=fetch_bill_adjustments"

# 実行せず、いまの状態だけ見る
curl -sS "${OMS_ENDPOINT_URL}?token=${OMS_ENDPOINT_TOKEN}&action=status"
```

`action` は `status` / `refresh_master` / `refresh_bq` / `create_csv` /
`fetch_bill_adjustments` / `refresh_all` / `snapshot`。

### 応答の例

```json
{
  "ok": true,
  "action": "refresh_all",
  "ran": ["refresh_master", "refresh_bq", "create_csv"],
  "spreadsheetId": "...",
  "checkedAt": "2026-09-01T07:02:11.000Z",
  "masterRows": 102,
  "targetDataRows": 21,
  "targetDate": "2026-08-31",
  "targetTerm": "2026-08",
  "createCsvRows": 21,
  "snapshot": { "fileId": "...", "fileName": "oms_adjustment_2026-08.csv", "rows": 21, "term": "2026-08" }
}
```

呼び出したあとは必ず次を確認してから先へ進む。

- `ok` が `true`
- `targetTerm` が処理したい対象月と一致している
- `targetDate` が対象月の末日になっている
- `createCsvRows` が `targetDataRows` と一致している

ひとつでもずれていたら、**その先の検証をせずユーザーに報告する。**
特に `targetTerm` のずれは「先月分のつもりで先々月を回している」事故そのもの。

## 呼び出しに失敗したとき

回避策を自分で作らない。次の依頼文をユーザーに渡す。

> 調整額生成ツールを開いて、カスタムメニューから
> 「マルチチャネルデータを更新」→「BigQueryデータを更新」→「調整額CSV生成」
> の順に実行してください。終わったら「完了」と返してください。

`refresh_all` が途中で失敗した場合、どこまで走ったかは応答の `ran` でわかる。
`ran` に入っている処理は実行済みなので、続きから個別の `action` で再開してよい。

## Web App を置きたくない場合

エンドポイントなしでもスキルは成立する。その場合は毎回、上の依頼文でユーザーにメニュー実行を頼み、
Claude はシートの読み取りから先だけを担当する。
`installMonthlyTrigger` の時間主導トリガーだけを入れておくと、月初の実行忘れは防げる。
