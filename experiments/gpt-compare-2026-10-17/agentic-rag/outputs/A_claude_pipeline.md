---
title: "エージェンティックRAG"
excerpt: "AIが資料の探し方と回数を自分で決めて答える仕組み"
category_id: 418
category_name: "テクノロジー・技術"
category_field: "glossary-category"
slug: "agentic-rag"
eyecatch_prompt: "A flat vector illustration on a solid warm cream beige background #F2F0E6. The final file is 1:1, but all critical content must fit within the central 52% vertical band so that nothing is cropped when displayed as a 1.91:1 OGP thumbnail; the top 24% and bottom 24% of the canvas must be left empty as buffer, and at least 12% lateral padding must be kept on each side. Within this safe central band, near the top, the Japanese text 'エージェンティックRAG' is displayed in bold, dark charcoal, sans-serif font. Below the text, on the left a single straight arrow runs from a question mark through one document box into an answer box, while on the right a small simple robot figure stands inside a circular arrow loop that passes through three different document boxes and reaches toward a fourth one, so that one side shows a single pass and the other shows a repeated search the figure steers itself. Compose the scene with breathing room rather than filling the frame. Minimal corporate art style with thick dark charcoal outlines. Simple geometry, high contrast, no shading. Muted blue and grey palette. The illustration block must preserve an exact 16:10 aspect ratio, even though the final file is 1:1."
creator_version: "v19"
recipe_hash: "cec6936d256d"
generated_at: "2026-10-10"
regenerated_from: "v3"
---

## 最小限の説明

AIが資料の探し方と回数を自分で決めて答える仕組み

-- wp分割ライン--

エージェンティックRAGとは、資料をどう探すかの判断をAI自身に任せることで、一度の検索では答えの出ない問いにも答えられるようにする仕組みである。土台にあるRAG（Retrieval-Augmented Generation、検索拡張生成）は、AIが学習で覚えた知識だけで答えず、外部の資料を引いてから答えを作る技術を指す。

社内の規程を検索して答える質問応答システムに、「育児休業の申請期限は、去年の規程と今年の規程でどう変わったか」と尋ねる場面を考える。去年の版と今年の版は別の文書なので、質問文に似た文書を数件引くだけでは片方しか手元に来ないことがある。エージェンティックRAGでは、AIがまず去年の版を引き、次に今年の版を引き、申請期限の記載が出てこなければ言葉を変えてもう一度引く。

土台のRAGは知識源を1つ決めて一度引く形が基本で、エージェンティックRAGは、その一度きりの検索を何度でも組み直せる工程に変えたものにあたる。

## 探し方そのものをAIに任せる

上の例でAIが手元に持っているのは、社内文書を引く検索のほかに、Web検索や業務システムの呼び出しといった道具である。どれをどの順で使うかは、問いを読んだ時点では決まっていない。

文書を意味の近さで探す仕組みを手がけるWeaviateは、エージェントが引き受ける判断を4つに[整理している](https://weaviate.io/blog/what-is-agentic-rag)。そもそも検索が要る問いなのか、どの道具で引くのか、問い合わせ文をどう書くのか、引いた結果で答えるに足りるのか。最後のひとつがあるために、引いた中身を見てから次の一手を変えられる。

「エージェンティック（agentic）」が指しているのは、この自分で決める部分である。RAGの開発基盤を公開しているLlamaIndexは、エージェントを[自動の推論と意思決定のエンジン](https://developers.llamaindex.ai/python/framework/use_cases/agents/)と呼ぶ。挙げている働きは、複雑な問いを小さく分ける・道具を選ぶ・作業の順番を計画する・済んだ作業を覚えておく、の4つである。

分かれ目は、検索を何回まわすかではない。その回数と順番を人が設計時に固定しているか、AIがその場で決めているかにある。

## 語源・提唱者

RAGは2020年5月、Patrick¥パトリック¥ Lewis¥ルイス¥ ら12名の[論文](https://arxiv.org/abs/2005.11401)で示された。学習済みのモデルは覚えた知識を内部に抱えてはいるものの、それを正確に取り出せず、答えの出所も示せず、知識の更新もできない。そこでWikipediaの索引を引いて答えの材料にする形を作った。ただしこの原型は、引いてから答えるまでが一度きりの形だった。

一度きりの形が実務でどこに詰まるかは、オーストラリアのディーキン大学のScott¥スコット¥ Barnett¥バーネット¥ らが2024年1月に[報告している](https://arxiv.org/abs/2401.05856)。研究・教育・生物医学の3領域で動いていたシステムから7つの失敗点を挙げたもので、そのひとつが「答えのある文書が検索の上位に来ない」ことだった。冒頭の例でいえば、去年の版が上位に入らないまま答えが作られる場合がこれにあたる。バーネット氏らは、RAGの検証は運用中にしかできず、堅牢さは最初の設計ではなく運用の中で育っていくと結論づけている。

検索の進め方をAIに任せる形は、その後「Agentic RAG」という名前で呼ばれるようになった。2025年1月、Aditi¥アディティ¥ Singh¥シン¥ らの[調査論文](https://arxiv.org/abs/2501.09136)が、自律的なエージェントをRAGの工程に埋め込んだものとして定義した。あわせて、エージェントの数・制御の形・自律の度合い・知識の持ち方で分類している。

## 当たる問いと、外す問いがある

冒頭の例のように問いを小さく分けて引く形が効くかどうかは、相手にする資料で変わる。2026年6月の[比較研究](https://arxiv.org/html/2606.05658v1)は、同じ仕組みを性格の違う2つの相手に当てている。ひとつは開発と運用の社内知識ベースである。もうひとつのMuSiQueは、複数の文書をまたがないと答えが出ない問題を集めたベンチマークにあたる。

社内知識ベースでは、必要な文書が検索結果の上位5件に入った割合が0.833から1.000へ上がった。去年の版と今年の版を別々に引きにいく形が当たるのは、こちらである。

MuSiQueでは逆に、同じ割合が1.000から0.063へ落ちた。拾う話題の広さは0.609から0.859へ広がっているので、探す範囲は広がったものの、そのなかでどれが要るかの順位付けが崩れたことになる。

時間の代償も小さくない。平均の応答時間は、社内知識ベースで21.00秒から47.66秒へ、MuSiQueで21.84秒から74.87秒へ延びた。引いた結果を見直す工程まで足すと、MuSiQueでは17秒から104秒になる。この研究は、エージェント的な拡張を一律に当てず、費用を意識して選んで当てるべきだと結論づけている。

## どの問いを任せるかを先に決める

製品の問い合わせ窓口には、「保証期間は何年か」のように1回引けば答えが出る問いと、何度も引かないと答えが出ない問いが混ざって届く。2024年3月に発表された[Adaptive-RAG](https://arxiv.org/abs/2403.14403)は、この混在を出発点に置いている。仕組みをどちらか一方に寄せると、単純な問いに不要な計算の負担をかけるか、多段の問いに応えきれないかのどちらかになるからである。

そこでこの論文が前に置いたのは、質問の複雑さを予測する小さな言語モデルである。その見立てに応じて、検索しない・1回引く・繰り返し引くの3つから選ばせる。どこまでをAIの判断に回すかを、問いが届いた時点で分ける設計といえる。

任せる範囲を広げるほど、失敗の形も変わる。2026年3月の[調査論文](https://arxiv.org/abs/2603.07379)は、自律的なループに固有の危険を4つ挙げている。誤った内容が次の検索に持ち越されて膨らむこと、記憶に残った誤りが後の答えを汚すこと、検索が問いから少しずつずれること、道具の実行が連鎖して広がることである。

## 関連用語

- AIエージェント
- ハルシネーション
- ベクトル検索
- マルチエージェントシステム
- コンテキストエンジニアリング
