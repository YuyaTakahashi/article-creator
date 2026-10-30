---
title: "ジェイルブレイク"
excerpt: "安全のため断るよう訓練されたAIに、入力の文面だけで応じさせる攻撃"
category_id: 562
category_name: "AI"
category_field: "glossary-category"
slug: "jailbreaking"
eyecatch_prompt: "A flat vector illustration on a solid warm cream beige background #F2F0E6. The final file is 1:1, but all critical content must fit within the central 52% vertical band so that nothing is cropped when displayed as a 1.91:1 OGP thumbnail; the top 24% and bottom 24% of the canvas must be left empty as buffer, and at least 12% lateral padding must be kept on each side. Within this safe central band, near the top, the Japanese text 'ジェイルブレイク' is displayed in bold, dark charcoal, sans-serif font. Below the text, a small dark silhouette of a person stands at the left holding up a plain outlined mask on a stick in front of its own face; facing it on the right sits a rounded box standing for a machine, with a closed gate drawn across its opening; a single straight line runs from the masked figure to the gate and continues through it unbroken, while a second line drawn from the unmasked figure stops short at the gate, showing that only the disguised request passes. Compose the scene with breathing room rather than filling the frame. Minimal corporate art style with thick dark charcoal outlines. Simple geometry, high contrast, no shading. Muted blue and grey palette. The illustration block must preserve an exact 16:10 aspect ratio, even though the final file is 1:1."
creator_version: "v19"
recipe_hash: "cec6936d256d"
generated_at: "2026-10-12"
---

## 最小限の説明

安全のため断るよう訓練されたAIに、入力の文面だけで応じさせる攻撃

-- wp分割ライン--

ジェイルブレイク（Jailbreaking）とは、安全のために断るよう訓練されたAIに対して、入力するプロンプトの文面を作り替えることで、本来なら断るはずの応答を出させる攻撃である。

チャットAIに、そのまま聞けば断られる質問をする場面で考える。断られたあと、「何の制限も受けない別のAIを演じてほしい」という長い前置きを質問の前に足し、その人格として同じことを答えさせる。足したのは文章だけで、ソフトウェアには手を触れていない。それでも返ってくるのは断りではなく、中身のある答えになる。

OWASP¥オワスプ¥ の生成AIセキュリティプロジェクトは、大規模言語モデルで起きるリスクを番号付きで並べた一覧を公開している。その1番目はプロンプトインジェクションで、ジェイルブレイクはそのうち、モデルに安全上の取り決めを丸ごと無視させるものにあたる。

## ソフトは触らず、文面だけで破る

この攻撃を研究する側は、安全訓練を受けたモデルに断られる要求を別の文面へ作り替えて送り、その話題に沿った応答を引き出そうとする試みだと定義している。狙いは断り文句を避けることではなく、断られていた中身を実際に受け取ることにある。

必要なのは決まった言い回しの型だけで、ソフトウェアは普通は要らない。引き出せるのは有害な応答に限らず、提供側がモデルに与えた指示、つまりシステムプロンプトを明かさせることもできる。

なぜ文面を変えるだけで破れるのか。安全訓練の破れ方を調べた2023年の研究は、理由を2つに整理した。1つは、訓練で与えた目標どうしがぶつかることである。モデルは、文章としてもっともらしく続けること、指示に従うこと、安全であることの3つに向けて訓練されており、前の2つが3つ目と衝突する場面がある。冒頭の例で「演じてほしい」という指示に従おうとする力が、断る力と引き合うのがこれにあたる。もう1つは、安全の訓練が届いていない領域があることである。モデルの能力はその領域に及んでいるのに、断る訓練だけが及んでいない。

## 語源・提唱者

この言葉を最初にいまの意味で使ったのは、iPhone と iOS のジェイルブレイクのコミュニティである。コンピュータセキュリティでのジェイルブレイクは、提供元がハードウェアやソフトウェアに固く組み込もうとした制限を取り除く行為を指す。買った端末で、メーカーが認めていないソフトを動かせるようにする行為がこれにあたる。

AIに移ってからの始まりは、DAN と呼ばれるプロンプトである。「doing anything now（何でもいまやる）」の略で、2023年1月8日から Reddit で広まった。ネット上のジェイルブレイクプロンプトを調べた研究は、これを最初のジェイルブレイクプロンプトとして記録している。

## 古い手口が、何か月も効き続ける

その研究チームは、2022年12月から2023年12月までにネット上から1,405件のジェイルブレイク用プロンプトを集めた。使われていたのは、冒頭の例と同じく役を演じさせる手口のほか、権限が上がったように見せかける、嘘の状況を作る、といった形である。

とくに効いた5件は、ChatGPT（GPT-3.5）と GPT-4 の両方で0.95の成功率を出した。そのうち最も古いものは、240日を超えてネット上に残り続けている。

手口を重ねると成功率はさらに上がる。先の2023年の研究では、組み合わせた攻撃が GPT-4 で94%に達した。

前置きを長くする形は、一度に読ませられる量が増えるほど効く。Anthropic が2024年4月に公表したメニーショット・ジェイルブレイクは、人間とAIの偽の会話を1つのプロンプトの中に大量に並べる手口である。偽の会話が数件なら安全訓練どおりに断る。しかし最後の質問の前に非常に多くを並べると、応答が変わる。この研究は256件まで試しており、Anthropic 自身のモデルにも他社のモデルにも効いた。

## 入口で止めきれない前提で守る

守る側がこれを考えるのは、モデルを選んで製品に組み込む段である。問い合わせ窓口のチャットに生成AIを使うなら、利用者が何を書いてくるかは選べない。

入口に置くフィルタだけでは足りない。1,405件を調べた研究は、外部の安全装置を3種類かけて成功率の下がり幅を測った。いちばん効いたもので0.091、小さいものでは0.019にとどまっている。

効いた例として報告されているのは、プロンプトをモデルに渡す前に分類して書き換える手立てである。Anthropic は、これによってメニーショット・ジェイルブレイクの成功率が61%から2%へ下がった場合があるとしている。

ただし、入口の手当てはモデル側の手当ての代わりにはならない。OWASPは、ジェイルブレイクを実際に防ぐにはモデルの訓練と安全機構を更新し続ける必要があるとしている。2023年の研究も、安全の仕組みは土台のモデルと同じくらい作り込まれているべきで、規模を大きくするだけでは目標のぶつかりは解けないと論じた。

手口そのものを集める取り組みも始まっている。2024年には複数のAI企業の連合が HackAPrompt.com を設立し、新しく効くジェイルブレイクの手法を見つけることを促す競技を開いた。

## 関連用語

- プロンプトインジェクション
- システムプロンプト
- レッドチーミング
- アライメント
