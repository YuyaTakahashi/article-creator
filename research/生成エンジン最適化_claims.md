# 出典台帳：生成エンジン最適化（Generative Engine Optimization）

このセッションで実際に読めたページの文章だけを引用している。1行1事実。

## S1. Aggarwal, P. et al. "GEO: Generative Engine Optimization", KDD '24
URL: https://arxiv.org/abs/2311.09735 ／ PDF: https://arxiv.org/pdf/2311.09735 （v3, 28 Jun 2024。PDFを pdftotext でテキスト化して読んだ）

| # | 事実 | 原文の引用 |
|---|---|---|
| S1-1 | 提唱者は Pranjal Aggarwal ら6名。KDD '24（2024年8月、バルセロナ）で発表 | "Pranjal Aggarwal, Vishvak Murahari, Tanmay Rajpurohit, Ashwin Kalyan, Karthik Narasimhan, and Ameet Deshpande. 2024. GEO: Generative Engine Optimization. In Proceedings of the 30th ACM SIGKDD Conference ... (KDD '24), August 25–29, 2024, Barcelona, Spain." |
| S1-2 | arXiv初出は2023年11月（2311.09735） | "arXiv:2311.09735v3 [cs.LG] 28 Jun 2024"（arXiv ID の 2311 が2023年11月の投稿を示す） |
| S1-3 | 生成エンジンは、検索して複数のソースから回答を作り、引用を添える仕組み | "generative engines (Figure 2) retrieve relevant documents from a database (like the internet) and use large neural models to generate a response grounded on the sources, ensuring attribution and a way for the user to verify the information." |
| S1-4 | 内部では、質問を細かい問いに分解 → 検索 → 各ソースを要約 → 回答生成、の順で動く | "This workflow breaks down the input query into a set of simpler queries ... which are then passed to the search engine SE to retrieve a set of ranked sources ... The sets of sources S are passed to a summarizing model ... The summary set is passed to a response-generating model ... which generates a cumulative response r backed by sources S." |
| S1-5 | 提唱の動機：回答だけで用が足り、サイトへの訪問が減る | "Generative Engines, in contrast to traditional search engines, remove the need to navigate to websites by directly providing a precise and comprehensive response, potentially reducing organic traffic to websites and impacting their visibility" |
| S1-6 | 提唱の動機：小規模事業者・個人の生計に関わる | "With millions of small businesses and individuals relying on online traffic and visibility for their livelihood, generative engines will significantly disrupt the creator economy." |
| S1-7 | 提唱の動機：黒箱で、扱われ方が作り手から見えない | "the black-box and proprietary nature of generative engines makes it difficult for content creators to control and understand how their content is ingested and portrayed." |
| S1-8 | 狙い：作り手側から打てる手を用意する最初の枠組み | "we propose the first general creator-centric framework to optimize content for generative engines, which we dub Generative Engine Optimization (GEO), to empower content creators to navigate this new search paradigm." |
| S1-9 | 従来のSEOはそのままでは通用しない。理由は、語の一致ではなく文章の意味を読むから | "traditional SEO methods are not directly applicable to Generative Engines. This is because, unlike traditional search engines, the generative model in generative engines is not limited to keyword matching, and the use of language models in ingesting source documents and response generation results in a more nuanced understanding of text documents and user query." |
| S1-10 | GEO-bench は1万件の質問 | "we propose GEO-bench, a benchmark consisting of 10000 queries from diverse domains and sources, adapted for generative engines." |
| S1-11 | 検証した書き換えは9種（Authoritative / Statistics Addition / Keyword Stuffing / Cite Sources / Quotation Addition / Easy-to-Understand / Fluency Optimization / Unique Words / Technical Terms） | "1: Authoritative ... 2. Statistics Addition ... 3. Keyword Stuffing ... 4. Cite Sources & 5. Quotation Addition ... 6. Easy-to-Understand ... 7. Fluency Optimization ... 8. Unique Words & 9. Technical Terms" |
| S1-12 | 上位3手法（出典・引用・統計）で30〜40%改善 | "our top-performing methods, Cite Sources, Quotation Addition, and Statistics Addition, achieved a relative improvement of 30-40% on the Position-Adjusted Word Count metric and 15-30% on the Subjective Impression metric." |
| S1-13 | 読みやすさの改善も15〜30%効いた | "stylistic changes such as improving fluency and readability of the source text (Fluency Optimization and Easy-to-Understand) also resulted in a significant visibility boost of 15-30%." |
| S1-14 | 断定的・説得的な調子への書き換えは効かなかった | "one would expect a more persuasive and authoritative tone in website content to boost visibility. However, we find no significant improvement, demonstrating that Generative Engines are already somewhat robust to such changes." |
| S1-15 | キーワードの詰め込みはほぼ効かない | "we evaluate keyword stuffing, i.e., adding more relevant keywords to website content. While widely used for Search Engine Optimization, we find such methods offer little to no improvement" |
| S1-16 | 効き方は元の検索順位で逆転する。5位は Cite Sources で +115.1%、1位は -30.3% | Table 2（Cite Sources 行）: Rank-1 "-30.3"、Rank-5 "115.1"。表の説明 "Table 2: Visibility changes through GEO methods for sources with different Rankings in Search Engine. GEO is especially helpful for lower ranked websites." |
| S1-17 | 全体の改善幅は最大40% | "we demonstrate that GEO can boost visibility by up to 40% in generative engine responses." |
| S1-18 | 実在の生成エンジン（Perplexity.ai）でも最大37% | "We also demonstrate the efficacy of Generative Engine Optimization on Perplexity.ai, a real-world generative engine and demonstrate visibility improvements up to 37%." |
| S1-19 | 効き方は分野で変わる（出典添付は事実を問う質問に、統計は法律・行政や意見を問う質問に効く） | "the addition of citations through Cite Sources is particularly beneficial for factual questions ... domains such as 'Law & Government' and question types like 'Opinion' benefit significantly from the addition of relevant statistics" |

## S2. Wikipedia "Generative engine optimization"（英語版・2026年10月4日に取得）
URL: https://en.wikipedia.org/wiki/Generative_engine_optimization

| # | 事実 | 原文の引用 |
|---|---|---|
| S2-1 | 定義 | "Generative engine optimization (GEO), also known as answer engine optimization (AEO) and artificial intelligence optimization (AIO), is the practice of improving visibility in responses generated by generative artificial intelligence (AI) systems." |
| S2-2 | 呼び名が定まっていない（AEO / LLMO / AIO / AI SEO） | "Other designations include answer engine optimization (AEO), large language model optimization (LLMO), artificial intelligence optimization (AIO), and AI SEO."／"no consensus definition" |
| S2-3 | 用語の出どころは2023年の Aggarwal らの論文、KDD 2024で発表 | "The term 'generative engine optimization' was introduced in a 2023 paper by Pranjal Aggarwal and co-authors, later presented at the KDD 2024 conference." |
| S2-4 | Googleの2026年の見解 | "optimizing for generative AI search is optimizing for the search experience, and thus still SEO." |
| S2-5 | Forrester のアナリスト Nikhil Lai の見解 | "answer engine optimization (and related terms) are 'significantly, but not fundamentally, different from SEO.'" |
| S2-6 | 計測ツールは無料のものから third-party まであり、効果は議論中 | "Free tools like the AI Performance report in Bing Webmaster Tools"／"The efficacy of third-party tools is debated within the overall GEO and SEO industries" |

## S3. Martinez, O. "Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023-2026)"
URL: https://arxiv.org/abs/2607.14035 ／ PDF: https://arxiv.org/pdf/2607.14035 （2026年7月15日版。PDFを pdftotext でテキスト化して読んだ）

| # | 事実 | 原文の引用 |
|---|---|---|
| S3-1 | 2023年11月〜2026年7月の研究45本を対象にした批判的総説 | "This critical survey reviews 45 studies selected under a November 2023-July 2026 publication window" |
| S3-2 | 元論文の伸びは「すでに文脈に入っている」条件つきで、発見されやすさも流入も示していない | "The foundational paper's widely cited gains are valid within its experimental setting but conditional on a source already being present in a fixed context; they establish neither organic discoverability nor durable traffic effects." |
| S3-3 | 再現しやすいのは、内容の近さと文脈内の位置の2つ | "Reviewed work indicates that topical relevance and context position are the most reproducible levers, generic heuristics transfer poorly, competition can erode individual gains, and citation-oriented rewrites can impair retrieval." |
| S3-4 | 安定した因果効果を示した手法はひとつも無い | "no reviewed technique shows a stable, longitudinal, cross-platform causal effect on organic discoverability or downstream behavior." |
| S3-5 | 引用狙いの書き換えが検索側を傷める実測（SAGEO Arena, Kim et al. 2026） | "Across 171 003 documents and 2 700 queries, body-only optimization reduces average top-20 presence by approximately 9%, top-10 presence after reranking by 16%, and final citation by 6% [Kim et al., 2026]. ... A rewrite may therefore perform well once injected while making the document less retrievable or less competitive upstream." |
| S3-6 | 同じ条件でも結果が揺れる（温度0でも9〜28%の判断が変わる） | "repeated runs at temperature zero change 9–28% of decisions"／"A GEO measurement must therefore vary along at least four dimensions: run, paraphrase, date, and engine." |
| S3-7 | 測り方の推奨：言い換え3〜5通り、繰り返し7〜8回、エンジンと日付を記録 | "three to five paraphrases per information need;"／"Seven to eight repetitions constitute a reasonable starting point based on Schulte et al. [2026]"／"multiple named engines and search modes, with version and date" |
| S3-8 | 全員が最適化すると取り分が削れる | "When impression shares sum to one, GEO is at least locally redistributive. C-SEO Bench shows that gains can erode as adoption increases [Puerto et al., 2025]." |
| S3-9 | 元論文以後も残った知見3つ（キーワード詰め込みは移らない／取り出せる情報は使われやすい／効果は分野と初期順位に依存） | "First, keyword stuffing does not transfer effectively from conventional SEO. Second, directly extractable information—figures, definitions, quotations, and references—can facilitate the use of a document. Third, effects depend on the domain and initial rank. Under the Cite Sources strategy, the fifth source gains 115.1% while the first loses 30.3%" |
| S3-10 | エンジンごとに引用元が重ならない | "Kirsten et al. [2026] observe that 53% of domains cited by Google AIO do not appear in the organic top 10 and that 27% are absent from the top 100." |

## S4. Wen, Y. et al. "Position: Generative Engine Optimization Creates Underexamined Risks..."（参考・本文未使用）
URL: https://arxiv.org/abs/2606.12439 （2026年5月18日提出。abstractのみ読んだ）

| # | 事実 | 原文の引用 |
|---|---|---|
| S4-1 | GEOには影響力の集中と、開示されない商業的影響というリスクがある | "we analyze the search engine optimization (SEO) to GEO transition to identify two risks: (i) concentrated influence from low contestability and system sensitivity, and (ii) undisclosed commercial influence embedded in evidence and reasoning." |

## 読めなかった出典（事実の根拠には使わない）
- Search Engine Land「Generative engine optimization (GEO): How to win AI mentions」 https://searchengineland.com/what-is-generative-engine-optimization-geo-444418 → HTTP 403
- Contentful「What is Generative Engine Optimization (GEO)...」 https://www.contentful.com/blog/generative-engine-optimization-seo/ → HTTP 429
- Google Search Central の AI features ガイド https://developers.google.com/search/docs/essentials/get-on-google-ai-features → HTTP 404（Googleの見解は S2-4 を根拠にする）
