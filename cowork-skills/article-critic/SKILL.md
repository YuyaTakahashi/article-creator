---
name: article-critic
description: article-creatorが生成・リライトした記事を、テンプレ準拠Critic（UX TIMES用語集形式の構造遵守）・文章スタイルCritic（体言止め禁止・受動態回避・主語明示・OPENLOGI表記・一人称回数）・読み手目線Critic（difficulty/itパラメータ整合・専門用語の言い換え・具体性・冗長性）・読みやすさCritic（本多勝一『日本語の作文技術』軸：一文の長さ・修飾語順序・読点・接続詞・語の経済性）の4軸でレビューするスキル。以下のすべてで必ず使用する - article-creatorのStep 3末尾（リライト後のセルフチェック時）、article-creatorのStep 6直前（MDファイル保存前の最終ゲート）、yuyaから「この記事をCriticかけて」「記事レビューして」「品質チェックして」と明示的に依頼されたとき。各Criticは5項目×3点のルーブリックで評価し、合計11点以上で通過する（4軸AND判定）。10点以下のCriticがあれば呼び出し元エージェント（article-creator）に再生成を指示し、最大2回まで往復する。3回目で通過しない場合は「要人間判断」フラグつきで通過させる。スコアと判定はAGENT_REPORTS/article-critic-logs/にJSONで残し、将来のリグレッションデータとして蓄積する。yuyaのレビュー負荷を下げ、UX TIMESに投稿する前の品質ゲートとして機能する。article-creatorと併せて常にこのCriticを通す前提で動かす。
---

# article-critic スキル

## このスキルの目的

article-creatorが生成・リライトした記事を、UX TIMESに投稿する前の品質ゲートとして評価する。yuyaのレビュー負荷を下げ、「呼び出し元が書き直す → Criticが再評価する」のループでレビューなしに品質が上がっていく状態をつくる。

このスキルは記事を**書き直さない**。評価して「通過 / 再生成 / 要人間判断」の3択を返すことに責任を絞る。書き直しは呼び出し元のarticle-creatorが担う。これは責任分離と、Criticの判断ログを純粋に保ち将来のリグレッションテストに使うためである。

agent-critic（PRD・ロードマップ等の判断系成果物用）と同じパターンを踏襲しており、記事系コンテンツ用にCritic軸を4つに差し替えたものに当たる。

---

## ステップ1：4つのCriticを順番に呼ぶ

article-criticは常に4軸すべてを評価する（AND判定）。途中で1軸でも10点以下なら、残り軸の評価は行わずに「再生成」判定を返してよい（短絡評価）。4軸すべて11点以上で初めて「通過」を返す。

4つのCriticは次のとおり。それぞれ詳細な5項目ルーブリックは references/{name}-critic.md を Read で読み込んで評価する。

**テンプレ準拠Critic** — UX TIMES用語集記事の構造遵守を問う。タイトル形式・最小限の説明の文字数と位置・H2の並び・禁止見出しの不在・導入リード文の形式。詳細は `references/template-critic.md` を読む。

**文章スタイルCritic** — yuyaの個人スタイルガイド遵守を問う。体言止め・受動態・主語の曖昧さ・OPENLOGI表記・一人称回数。詳細は `references/style-critic.md` を読む。

**読み手目線Critic** — 呼び出し元が指定した difficulty / it パラメータとの整合と、読者がつまずかずに読めるかを問う。難易度整合・IT前提整合・専門用語の言い換え・具体例の効果・冗長性。詳細は `references/reader-critic.md` を読む。

**読みやすさCritic** — 本多勝一『日本語の作文技術』軸での文章リズム評価。一文の長さ（平均60字/最大80字目安）・修飾語順序（長→短）・読点の論理性・接続詞のリズム（「〜が、」の弱い逆接乱用回避）・語の経済性。詳細は `references/readability-critic.md` を読む。

---

## ステップ2：各Criticでルーブリック評価する

該当する `references/{critic名}-critic.md` を読み、5項目ルーブリックで評価する。各項目を1〜3点でスコアリングし、合計15点満点を出す。

スコアの意味は agent-critic と統一する。

- **3点**：問いに対して明確に応えている（合格水準）
- **2点**：応えてはいるが不十分・曖昧
- **1点**：応えていない、見落としている、誤っている

スコアリングの根拠は必ず1〜2文で書く。「2点」だけでは後でレビューできないため、なぜ2点なのかを記録する。具体的に違反している該当箇所（行番号・該当文）を引用する。

---

## ステップ3：判定を出す

各Criticの合計スコアに基づいて、次の3択から判定する。

**通過（pass）**：4軸すべてが11点以上。呼び出し元に「保存・投稿してよい」と返す。**ただし2点項目が残っている場合は `regenerate_points` を必ず返す**。pass水準でも呼び出し元が「最小コストで満点に近づける」自動リライトを実行できるようにするため。

**再生成（regenerate）**：1軸でも10点以下。呼び出し元（article-creator）に「再生成すべき」と返し、10点以下だった軸と低スコアの項目を改善ポイントとして明示する。再生成は最大2回まで。

**要人間判断（escalate）**：2回再生成しても11点未満の軸が残る場合、または評価が判断不能（情報不足など）な場合。「要人間判断」フラグつきでyuyaに上げる。

4軸スコアは合算しない。それぞれが独立に11点閾値を満たす必要がある。テンプレ準拠が13点でも文章スタイル/読み手目線/読みやすさのいずれかが10点以下なら再生成。これにより「テンプレは整っているが文章が下手」「文章は綺麗だが一読では頭に入らない」といった偏った合格を防ぐ。

## yuyaへの直接提示はしない

article-criticの返却（スコア・指摘内容・ログパス）は**呼び出し元エージェントへの戻り値であり、yuyaへの直接的なメッセージではない**。yuyaがログを毎回読む運用は負担が大きいため、Critic単体は人間向けレポートを生成しない。

人間向けの整形（最終記事のbefore/after、Inboxカード等）は呼び出し元の責任。article-creatorは `escalate` 判定のときだけCriticの指摘をInboxに添えてyuyaに見せる。`pass` / `regenerate` のサイクルは内部で完結させる。

JSONログは監査・リグレッション分析用に `~/workspace/agentic-solution/AGENT_REPORTS/article-critic-logs/` に残す。yuyaは必要なときだけ後から見にいく。

---

## ステップ4：ログをJSONで残す

判定に関係なく、すべての評価をJSONで `~/workspace/agentic-solution/AGENT_REPORTS/article-critic-logs/{YYYY-MM-DD}/{topic-slug}_{timestamp}.json` に保存する。

ログ構造は `assets/log-template.json` を読んでテンプレートに従う。各回の評価を1ファイルに残すので、再生成2回目なら同じtopicに対して2ファイルできる。これにより「どの記事で何回再生成が必要だったか」「どのCritic軸が引っかかりやすいか」が後から追える。

ローカル環境で `~/workspace/agentic-solution/AGENT_REPORTS/` フォルダが書き込めない場合（Coworkサンドボックス等）は、フォルダ作成を試みたうえで失敗時のみ outputs/article-critic-logs/ にフォールバックする。

---

## 呼び出し方の例

article-creatorからは、次のパラメータで呼ぶ。

```
article_type: ux_glossary
topic: FDE
difficulty: 0.3
it: 0.5
proposed_article: <記事本文+フロントマター>
attempt_count: 1
```

返却フォーマットは次のとおり統一する。

```yaml
verdict: pass | regenerate | escalate
scores:
  template: 13       # /15
  style: 12          # /15
  reader: 14         # /15
  readability: 11    # /15
weakest_axis: readability
regenerate_points:
  - "{該当軸名}: {改善が必要な項目} / 根拠: {引用 or 行番号}"
log_path: "~/workspace/agentic-solution/AGENT_REPORTS/article-critic-logs/2026-05-30/fde_20260530-091523.json"
comment: "{任意の総評}"
```

---

## 設計上の注意

**Critic自身は書き直さない**。書き直しは呼び出し元の責任。Criticが「どこが・なぜ不足か」だけ返し、article-creatorが改善版を作って再評価を依頼する設計にする。これは責任分離のためと、Criticの判断ログを純粋に保つため。

**1回目で11点未満でも、改善版が出れば再評価する**。再評価時もログは別ファイルとして残し、attempt_count をインクリメントする。

**Critic同士のスコアは合算しない**。AND判定で、片方でも10点以下なら再生成。

**短絡評価を許可する**。3軸の評価コストを下げるため、1軸で10点以下が確定した時点で残り軸の評価を省略してよい。ただし「どの軸を評価できなかったか」をログに `skipped: true` として残す。3回目以降の再評価では全軸を必ず通す（合格目前で別軸が崩れていないかを確認するため）。

**ルーブリック詳細は references/ 側に書く**。SKILL.mdは「どの軸を呼ぶか・閾値・ログ形式」だけに留め、具体的なチェック観点は references/{name}-critic.md に分離する。これによりUX TIMESの編集ガイドライン変更やyuyaのスタイル更新を取り込みやすくする。

**ファクトチェックはこのCriticの責任ではない**。事実誤りの検出と修正は article-creator の Step 4「ファクトチェックと自動修正」で済ませる前提。記事Criticは「テンプレ・文章・読み手目線」の3軸だけを見る。
