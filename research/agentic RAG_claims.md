# 出典台帳：agentic RAG（エージェンティックRAG）

収集日: 2026-10-10 ／ 収集方法: WebSearch + WebFetch（ディープリサーチ未実施のため WebSearch で代替）

## 定義・構成

C01 | エージェンティックRAGは、RAGの工程に自律的なAIエージェントを埋め込んだものである | https://arxiv.org/abs/2501.09136 | "Agentic Retrieval-Augmented Generation (Agentic RAG) transcends these limitations by embedding autonomous AI agents into the RAG pipeline."

C02 | そのエージェントは、省察・計画・道具の利用・複数エージェントの協調という設計パターンを使い、検索の進め方を動的に決め、文脈の理解を繰り返し磨き、工程を組み替える | https://arxiv.org/abs/2501.09136 | "These agents leverage agentic design patterns reflection, planning, tool use, and multi-agent collaboration to dynamically manage retrieval strategies, iteratively refine contextual understanding, and adapt workflows through operational structures ranging from sequential steps to adaptive collaboration."

C03 | 従来のRAGは固定された工程に縛られ、多段階の推論や複雑なタスク管理に必要な適応性を欠く | https://arxiv.org/abs/2501.09136 | "Despite its promise, traditional RAG systems are constrained by static workflows and lack the adaptability required for multi-step reasoning and complex task management."

C04 | このサーベイは、エージェントの数・制御構造・自律性・知識表現にもとづく分類を与えた | https://arxiv.org/abs/2501.09136 | "introduces a principled taxonomy of Agentic RAG architectures based on agent cardinality, control structure, autonomy, and knowledge representation"

C05 | サーベイの著者はAditi Singhら5名で、2025年1月15日に投稿された | https://arxiv.org/abs/2501.09136 | "Authors:Aditi Singh, Abul Ehtesham, Saket Kumar, Tala Talaei Khoei, Athanasios V. Vasilakos" / "[Submitted on 15 Jan 2025 (v1), last revised 1 Apr 2026 (this version, v4)]"

C06 | エージェンティックRAGは、AIエージェントによるRAGの実装を指す | https://weaviate.io/blog/what-is-agentic-rag | "Agentic RAG describes an AI agent-based implementation of RAG."

C07 | 素のRAGの工程は、外部の知識源を1つしか考えない | https://weaviate.io/blog/what-is-agentic-rag | "The naive RAG pipeline only considers one external knowledge source."

C08 | 素のRAGは一度きりの解であり、文脈は一度しか取得されない | https://weaviate.io/blog/what-is-agentic-rag | "They are a one-shot solution, which means that context is retrieved once."

C09 | エージェントは、検索するかどうか・どの道具で引くか・問い合わせ文そのものをどう作るか・引いた文脈を評価して引き直すかを決める | https://weaviate.io/blog/what-is-agentic-rag | "Decide whether to retrieve information or not" / "Decide which tool to use to retrieve relevant information" / "Formulate the query itself" / "Evaluate the retrieved context and decide whether it needs to re-retrieve."

C10 | もっとも単純な形のエージェンティックRAGは、振り分け役（ルーター）である | https://weaviate.io/blog/what-is-agentic-rag | "In its simplest form, agentic RAG is a router."

C11 | 複数のエージェントをつないだ形にする利点がある | https://weaviate.io/blog/what-is-agentic-rag | "Therefore, it is beneficial to chain multiple agents into a multi-agent RAG application."

C12 | エージェンティックRAGには、LLMを使うことに伴う制約（遅延の増加と信頼性の低さ）が付いてくる | https://weaviate.io/blog/what-is-agentic-rag | "This comes with the limitations of using LLMs in any application, such as added latency and unreliability."

C29 | エージェンティックRAGは1回の検索を多段の工程に置き換える。LLMが検索エージェントとして中間の思考と下位の問い合わせを生成し、検索系と繰り返しやり取りする | https://arxiv.org/abs/2605.06285 | "Agentic RAG extends this paradigm by replacing single-step retrieval with a multi-step process, in which the large language model (LLM) acts as a search agent that generates intermediate thoughts and subqueries to iteratively interact with the retrieval system."

C30 | この繰り返しの工程は、長い思考と下位の問い合わせを1語ずつ生成するため、大きな遅延を生む | https://arxiv.org/abs/2605.06285 | "This iterative process incurs substantial latency due to the autoregressive generation of lengthy thoughts and subqueries."

C32 | LlamaIndexのドキュメントは、エージェントを「自動の推論と意思決定のエンジン」と定義する | https://developers.llamaindex.ai/python/framework/use_cases/agents/ | "An 'agent' is an automated reasoning and decision engine. It takes in a user input/query and can make internal decisions for executing that query in order to return the correct result."

C33 | エージェントの働きには、複雑な問いを小さな問いに分けること、外部の道具を選び呼び出す引数を決めること、一連のタスクを計画すること、済んだタスクを記憶に置くことが含まれる | https://developers.llamaindex.ai/python/framework/use_cases/agents/ | "Breaking down a complex question into smaller ones" / "Choosing an external Tool to use + coming up with parameters for calling the Tool" / "Planning out a set of tasks" / "Storing previously completed tasks in a memory module"

## 語源・前史

C13 | RAGは2020年5月22日投稿の論文でPatrick Lewisら12名が示した。パラメータ記憶（学習済みのseq2seqモデル）と非パラメータ記憶（Wikipediaの密ベクトル索引）を組み合わせる | https://arxiv.org/abs/2005.11401 | "We introduce RAG models where the parametric memory is a pre-trained seq2seq model and the non-parametric memory is a dense vector index of Wikipedia, accessed with a pre-trained neural retriever." / "[Submitted on 22 May 2020 (v1)]" / "Authors:Patrick Lewis, Ethan Perez, ..."

C14 | 当時の課題は、学習済みモデルが知識を正確に扱えないこと、判断の出所を示すことと知識の更新が未解決だったことである | https://arxiv.org/abs/2005.11401 | "their ability to access and precisely manipulate knowledge is still limited" / "Additionally, providing provenance for their decisions and updating their world knowledge remain open research problems."

C15 | Barnettらは、研究・教育・生物医学の3領域の実運用事例から、RAGを設計するときに考えるべき7つの失敗点を報告した | https://arxiv.org/abs/2401.05856 | "we present an experience report on the failure points of RAG systems from three case studies from separate domains: research, education, and biomedical. We share the lessons learned and present 7 failure points to consider when designing a RAG system."

C16 | 2つの学びは、RAGの検証は運用中にしかできないこと、堅牢性は最初に設計されるのではなく育っていくことである | https://arxiv.org/abs/2401.05856 | "1) validation of a RAG system is only feasible during operation, and 2) the robustness of a RAG system evolves rather than designed in at the start."

C17 | Barnettらの所属はオーストラリア・ジーロングのディーキン大学 Applied Artificial Intelligence Institute | https://arxiv.org/html/2401.05856v1 | "Applied Artificial Intelligence Institute, Deakin University, Geelong, Australia"

C18 | 7つの失敗点の2番目は「上位に入らなかった文書」（答えはあるが検索の上位に来ない） | https://arxiv.org/html/2401.05856v1 | "FP2: Missed Top Ranked Documents"

C19 | 教育の事例はAI Tutorとして学生200人に提供された | https://arxiv.org/html/2401.05856v1 | "Deployed with 200 students"

C20 | 生物医学の事例はBioASQの4017件の公開文書と1000問で評価した | https://arxiv.org/html/2401.05856v1 | "4017 open access documents from the BioASQ dataset" / "1000 questions"

C34 | Cobus Greylingは2024年3月の記事で、Agentic RAGという言い回しはLlamaIndexが作ったと書いている（二次情報・本人の一次発信は403で読めず） | https://www.linkedin.com/posts/cobusgreyling_agentic-rag-context-augmented-openai-agents-activity-7174084034560409600-Tf86 | "LlamaIndex has coined the phrase Agentic RAG…"

## 効果・計測

C21 | DevOpsの社内知識ベースで、質問を小さく分けて引く形は、総合スコアを0.814→0.855、上位5件に必要な文書が入った割合（Success@5）を0.833→1.000、引用の正確さを0.750→0.917に上げた。平均応答時間は21.00秒→47.66秒 | https://arxiv.org/html/2606.05658v1 | Table III (DevOps): Overall Score 0.814→0.855 / Success@5 0.833→1.000 / Citation Accuracy 0.750→0.917 / Avg. Latency (s) 21.00→47.66 ／ 本文 "overall score rises from 0.814 to 0.855, MRR from 0.556 to 0.722" "citation accuracy climbs to 0.917"

C22 | 多段推論のベンチマークMuSiQueでは、同じ分解でSuccess@5が1.000→0.063、MRRが0.469→0.102に落ちた。拾う話題の広さ（Topic Coverage）は0.609→0.859に上がり、平均応答時間は21.84秒→74.87秒になった | https://arxiv.org/html/2606.05658v1 | Table III (MuSiQue): Success@5 1.000→0.063 / MRR 0.469→0.102 / Topic Coverage 0.609→0.859 / Avg. Latency (s) 21.84→74.87 ／ 本文 "MRR falls from 0.469 to 0.102 and Success@5 from 1.0 to 0.063"

C23 | MuSiQueでは、引いた結果を見直す省察のループを足すと応答時間が約6倍（17秒→104秒）になった | https://arxiv.org/html/2606.05658v1 | "latency increases roughly sixfold, from 17 s to 104 s"

C24 | この論文の結論は、エージェント的な拡張は一律に当てず、費用を意識して選んで当てるべきだというものである | https://arxiv.org/html/2606.05658v1 | "The clear lesson is that agentic enhancements must be applied selectively and with explicit cost awareness rather than uniformly"

C24b | 質問の分解は構造のある領域では一貫して効いたが、多段推論のベンチマークでは順位付けの精度を落とした。省察の仕組みは引用の正確さを上げるが、応答時間の代償が大きい | https://arxiv.org/abs/2606.05658 | "we find that query decomposition yields consistent gains in the structured domain (overall score $+0.04$, MRR $+0.17$ on DevOps) but degrades ranking precision on the multi-hop benchmark, while the reflection mechanism improves citation accuracy at a substantial latency cost."

C28 | Search-R1は7つの質問応答データセットで、同条件のRAGのベースラインより41%（Qwen2.5-7B）・20%（Qwen2.5-3B）性能を上げた | https://arxiv.org/abs/2503.09516 | "Experiments on seven question-answering datasets show that Search-R1 improves performance by 41% (Qwen2.5-7B) and 20% (Qwen2.5-3B) over various RAG baselines under the same setting."

## 隣の手法・リスク

C25 | Adaptive-RAGは、質問の複雑さを予測する小さな言語モデルの分類器を先に通し、検索しない・1回引く・繰り返し引くを切り替える | https://arxiv.org/abs/2403.14403 | "this selection process is operationalized with a classifier, which is a smaller LM trained to predict the complexity level of incoming queries with automatically collected labels" / "seamlessly adapting between the iterative and single-step retrieval-augmented LLMs, as well as the no-retrieval methods, in response to a range of query complexities."

C26 | Self-RAGは、必要に応じて文章を引くかを自分で決め、引いた文章と自分の生成を振り返る枠組みである | https://arxiv.org/abs/2310.11511 | "Our framework trains a single arbitrary LM that adaptively retrieves passages on-demand, and generates and reflects on retrieved passages and its own generations using special tokens, called reflection tokens."

C27 | 素のRAGは、検索が必要かどうかや文章が関連するかに関係なく決まった数を無差別に引くため、役に立たない答えにつながることがある | https://arxiv.org/abs/2310.11511 | "indiscriminately retrieving and incorporating a fixed number of retrieved passages, regardless of whether retrieval is necessary, or passages are relevant, diminishes LM versatility or can lead to unhelpful response generation."

C31 | 自律的なループには、幻覚の連鎖的な伝播・記憶の汚染・検索のずれ・道具実行の連鎖的な脆弱性という深刻なリスクがある | https://arxiv.org/abs/2603.07379 | "identify severe systemic risks inherent to autonomous loops, including compounding hallucination propagation, memory poisoning, retrieval misalignment, and cascading tool-execution vulnerabilities."

## 読めなかった出典

- https://medium.com/@jerryjliu98/agentic-rag-is-a-term-coined-by-llamaindex-... … 403 Forbidden（Medium）
- https://cobusgreyling.substack.com/p/agentic-rag … 404 Not Found

## 追記（2026-10-10）

C25b | 既存の手法は、単純な問いを不要な計算の負担つきで扱うか、複雑な多段の問いに十分に応えられないかのどちらかになる | https://arxiv.org/abs/2403.14403 | "they either handle simple queries with unnecessary computational overhead or fail to adequately address complex multi-step queries; yet, not all user requests fall into only one of the simple or complex categories."

C07b | 解によっては外部の知識源が2つ要る場合や、Web検索のような外部の道具・APIが要る場合がある | https://weaviate.io/blog/what-is-agentic-rag | "However, some solutions might require two external knowledge sources, and some solutions might require external tools and APIs, such as web searches."
