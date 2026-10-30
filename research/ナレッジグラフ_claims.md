# 出典台帳：ナレッジグラフ（Knowledge Graph）

収集日: 2026-10-26 ／ 収集方法: WebSearch + WebFetch（ディープリサーチ未実施のため WebSearch で代替）。Hogan et al. は arXiv PDF をテキスト化して原文を確認した。

## 定義・構成

C01 | ナレッジグラフは、現実世界の知識をためて伝えるためのデータのグラフで、ノードが対象となる実体を、エッジが実体どうしの関係を表す（広くとった定義） | https://arxiv.org/abs/2003.02320 | "Herein we adopt an inclusive definition, where we view a knowledge graph as a graph of data intended to accumulate and convey knowledge of the real world, whose nodes represent entities of interest and whose edges represent relations between these entities."

C02 | ナレッジグラフの定義はまだ定まっておらず、複数の（ときに食い違う）定義がある | https://arxiv.org/abs/2003.02320 | "The definition of a “knowledge graph” remains contentious [40, 57, 141], where a number of (sometimes conflicting) definitions have emerged"

C03 | 知識は「サンティアゴはチリの首都である」のような単純な文の形をとり、単純な文はデータのグラフのエッジとしてためられる | https://arxiv.org/abs/2003.02320 | "Knowledge may be composed of simple statements, such as “Santiago is the capital of Chile”, or quantified statements, such as “all capitals are cities”. Simple statements can be accumulated as edges in the data graph."

C04 | 「すべての首都は都市である」のような一般化した知識をためるには、オントロジーや規則のような表現が要り、そこから「サンティアゴは都市である」のような新しい知識を導ける | https://arxiv.org/abs/2003.02320 | "If the knowledge graph intends to accumulate quantified statements, a more expressive way to represent knowledge – such as ontologies or rules – is required. Deductive methods can then be used to entail and accumulate further knowledge (e.g., “Santiago is a city”)."

C05 | （働き）ラベル付き有向グラフは、サンティアゴやアリカのようなノードと、そのあいだのラベル付きの矢印（エッジ）の集まりで、ナレッジグラフではノードが実体を、エッジが実体間の関係を表す | https://arxiv.org/abs/2003.02320 | "A directed edge-labelled graph (also known as a multi-relational graph [29, 63, 386]) is defined as a set of nodes – like Santiago , Arica , EID16 , 2018-03-22 12:00 – and a set of directed labelled edges between those nodes" / "In the case of knowledge graphs, nodes are used to represent entities and edges are used to represent (binary) relations between those entities."

C06 | （働き）グラフでは、先に表の設計（スキーマ）を決めなくても、どの実体の組にもいつでも関係を足せる | https://arxiv.org/abs/2003.02320 | "By instead adopting a graph data model from the outset, the board could forgo the need for an upfront schema, and could define any (binary) relation between any pair of entities at any time."

C07 | グラフは、表の設計を後回しにでき、データとその範囲を関係データベースより柔軟に育てられる。欠けのある知識を扱うときにとくにそうである | https://arxiv.org/abs/2003.02320 | "Graphs allow maintainers to postpone the definition of a schema, allowing the data – and its scope – to evolve in a more flexible manner than typically possible in a relational setting, particularly for capturing incomplete knowledge [3]."

C08 | グラフ用の問い合わせ言語は、任意の長さの経路でつながった実体を順にたどって見つけられる | https://arxiv.org/abs/2003.02320 | "specialised graph query languages support not only standard relational operators (joins, unions, projections, etc.), but also navigational operators for recursively finding entities connected through arbitrary-length paths [16]."

## オントロジーとの境界

C09 | オントロジーと規則は、グラフのノードとエッジに付けた語の意味を定義し、それにもとづいて推論するために使える | https://arxiv.org/abs/2003.02320 | "Standard knowledge representation formalisms – such as ontologies [70, 239, 366] and rules [254, 288] – can be employed to define and reason about the semantics of the terms used to label and describe the nodes and edges in the graph."

C10 | 計算機の文脈でのオントロジーは、ある範囲で使う語が何を意味するかを具体的・形式的に表したものである | https://arxiv.org/abs/2003.02320 | "In the context of computing, an ontology 11 is then a concrete, formal representation of what terms mean within the scope in which they are used (e.g., a given domain)."

C11 | 「イベント」の意味の決め方はオントロジーごとに違い、どのオントロジーを使うかでグラフのデータの作り方が変わる（会場が2つあるイベントを2つに分けるか1つのままにするか） | https://arxiv.org/abs/2003.02320 | "Likewise ontologies can guide how graph data are modelled. Under the first ontology we may split EID16 into two events. Under the second, we may elect to keep EID16 as one event with two venues."

## 語源・提唱

C12 | 「ナレッジグラフ」という語は少なくとも1972年から文献にあるが、現在の意味は2012年のGoogle Knowledge Graphの発表に由来し、その後Airbnb・Amazon・eBay・Facebook・IBM・LinkedIn・Microsoft・Uberなども開発を発表した | https://arxiv.org/abs/2003.02320 | "Though the phrase “knowledge graph” has been used in the literature since at least 1972 [465], the modern incarnation of the phrase stems from the 2012 announcement of the Google Knowledge Graph [484], followed by further announcements of the development of knowledge graphs by Airbnb [87], Amazon [298], eBay [417], Facebook [387], IBM [128], LinkedIn [224], Microsoft [482], Uber [214], and more besides."

C13 | 産業界での広がりを受けて、ナレッジグラフを扱う学術文献が増えた | https://arxiv.org/abs/2003.02320 | "The growing industrial uptake of the concept proved difficult for academia to ignore: more and more scientific literature is being published on knowledge graphs"

C14 | 現在の意味に通じる最初の用例は、Schneider（1973）の教育用システムの論文で、学習者が身につける知識の単位をノード、単位どうしの依存をエッジとした有向グラフだった | https://arxiv.org/abs/2003.02320 | "the first reference to a “knowledge graph” of relevance to the modern meaning was in a paper by Schneider (1973) [465] in the area of computerised instructional systems for education, where a knowledge graph – in his case a directed graph whose nodes are units of knowledge (concepts) that a student should acquire, and whose edges denote dependencies between such units of knowledge"

C15 | GoogleのKnowledge Graphは、2012年5月16日にエンジニアリング担当上級副社長Amit Singhalがブログで発表した | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "Amit Singhal, SVP, Engineering" / "May 16, 2012"（WebFetch で著者表記と日付を確認）

C16 | 当時の検索は40年以上、問い合わせの文字列とキーワードを照合することが中心だった | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "For more than four decades, search has essentially been about matching keywords to queries."

C17 | 言葉はあいまいで、「taj mahal」が建造物のタージ・マハルか音楽家のタージ・マハルか区別できない | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "Language can be ambiguous—do you mean Taj Mahal the monument, or Taj Mahal the musician?"

C18 | Knowledge Graphにより、Googleは人・物・場所を検索できるようになった（発表時の副題は「文字列ではなくモノ」） | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "The Knowledge Graph enables you to search for things, people or places that Google knows about" / 題名 "Introducing the Knowledge Graph: things, not strings"

C19 | 発表時点で、5億を超える対象と、35億を超える事実を含んでいた | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "It currently contains more than 500 million objects, as well as more than 3.5 billion facts"

C20 | Knowledge GraphはFreebase・Wikipedia・CIA World Factbookなどの公開情報だけに頼っていない | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "Google’s Knowledge Graph isn’t just rooted in public sources such as Freebase, Wikipedia and the CIA World Factbook."

C21 | 人々が何を検索するかと、Web上で分かったことにもとづいて調整されている | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "And it’s tuned based on what people search for, and what we find out on the web."

## 効果・現れ方（検索の例）

C22 | 実体を区別できるので、検索結果を利用者が意図したほうに絞れる | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "Now Google understands the difference, and can narrow your search results just to the one you mean"

C23 | 話題についての要点を、利用者が必要としそうな主な事実も含めてまとめて見せられる | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "we can summarize relevant content around that topic, including key facts you’re likely to need"

C24 | 例の筋：マリ・キュリーを調べると生没年が出る。キュリーはKnowledge Graph上の「人」で、子が2人いて1人もノーベル賞を受け、夫ピエール・キュリーも受賞した | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "For example, if you’re looking for Marie Curie, you’ll see when she was born and died" / "Marie Curie is a person in the Knowledge Graph, and she had two children, one of whom also won a Nobel Prize," / "as well as a husband, Pierre Curie, who claimed a third Nobel Prize for the family."

C25 | 思いがけない事実やつながりを知り、新しい調べものが始まることがある | https://blog.google/products/search/introducing-knowledge-graph-things-not/ | "You might learn a new fact or new connection that prompts a whole new line of inquiry."

C26 | Knowledge Graphの人・場所・物の情報は、検索結果のナレッジパネルに表示されることが多い | https://support.google.com/knowledgepanel/answer/9787176?hl=en | "Knowledge Graph information about people, places, or things is often presented within knowledge panels."

C27 | ナレッジパネルは、問い合わせに強く関係する情報があるとき自動で表示される | https://support.google.com/knowledgepanel/answer/9787176?hl=en | "When information is highly relevant to a user’s query, a knowledge panel will automatically appear."

## 種類・実例

C28 | 公開されたナレッジグラフ（DBpedia・Freebase・Wikidata・YAGOなど）は多分野にまたがり、Wikipediaから抽出されるか、ボランティアの共同体が作る | https://arxiv.org/abs/2003.02320 | "The most prominent examples – DBpedia [311], Freebase [55], Wikidata [543], YAGO [243], etc. – cover many domains and are either extracted from Wikipedia [243, 311], or built by communities of volunteers [55, 543]."

C29 | 企業内のナレッジグラフは、Web検索・商取引・SNS・金融などで使われ、用途は検索・推薦・広告・業務分析・リスク評価などにわたる | https://arxiv.org/abs/2003.02320 | "Enterprise knowledge graphs are typically internal to a company and applied for commercial use-cases [387]." / "Applications include search [482, 484], recommendations [87, 214, 224, 387], personal agents [417], advertising [224], business analytics [224], risk assessment [112, 522], automation [234], and more besides."

C30 | Wikidataは、構造化データを集める、無料・共同編集・多言語の知識ベースである | https://www.wikidata.org/wiki/Wikidata:Introduction | "Wikidata is a free, collaborative, multilingual, secondary knowledge base, collecting structured data"

C31 | Wikidataの項目はQと番号で一意に識別され、記述（ステートメント）はプロパティと値の組で項目の特徴を表す。例：ダグラス・アダムズ（Q42）は「出身校」（P69）がセント・ジョンズ・カレッジ（Q691283） | https://www.wikidata.org/wiki/Wikidata:Introduction | "Items are uniquely identified by a Q followed by a number" / "Statements describe detailed characteristics of an Item and consist of a property and a value." / Douglas Adams (Q42) — educated at (P69) — St John's College (Q691283)

## 応用例

C32 | Airbnbのナレッジグラフは、在庫（宿・体験・場所）と世の中の情報をグラフ構造で表す | https://www.infoq.com/news/2019/03/wei-airbnb-knowledge-graph | "Airbnb's knowledge graph encodes information about their inventory and the world in a graph structure."

C33 | Airbnbでは「サーフィン」「スポーツ」のような概念をノード、「サーフィンはスポーツである」のような関係をエッジとして表す | https://www.infoq.com/news/2019/03/wei-airbnb-knowledge-graph | "concepts (e.g., Surfing and Sport) are represented in the graph as nodes" / "and the relationships between them (e.g., Surfing is a Sport) as edges"

C34 | 「スポーツ」の付いた場所を探すと、「サーフィン」のような個別のスポーツが付いた場所も含めて見つかる | https://www.infoq.com/news/2019/03/wei-airbnb-knowledge-graph | "Airbnb searches for places tagged with Sport to include places tagged with specific types of Sport, such as Surfing."

C35 | 宿・体験・場所の属性に分類体系の概念をタグとして付け、探索画面の絞り込み・自由入力の検索と補完・フィルターで利用者が目的のものを見つけられるようにしている | https://www.infoq.com/news/2019/03/wei-airbnb-knowledge-graph | "Attributes about Airbnb's inventory of Homes, Experiences, and Places are tagged with concepts from the taxonomy." / "we classify all of this data with a universal taxonomy that helps users find what they are looking for" / "through relevant product functionalities like navigation in Explore, free-text search/autocomplete, and filters."

## 読めなかった出典

- https://medium.com/airbnb-engineering/contextualizing-airbnb-by-building-knowledge-graph-b7077e268d5a | 403 Forbidden（InfoQ の記事で代替）
