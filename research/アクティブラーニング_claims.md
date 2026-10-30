# 出典台帳：アクティブラーニング（機械学習）

収集日: 2026-10-11 / 収集方法: WebSearch + WebFetch（PDFはローカルで pdftotext 済み）

主な出典
- S = Burr Settles, "Active Learning Literature Survey", Computer Sciences Technical Report 1648, University of Wisconsin–Madison, 2009（Updated 2010-01-26） https://sfu-db.github.io/cmpt884-fall16/Papers/settles.activelearning.pdf
- LG = David D. Lewis and William A. Gale, "A Sequential Algorithm for Training Text Classifiers", SIGIR '94, pp.3-12 https://arxiv.org/pdf/cmp-lg/9407020
- AWS = Amazon SageMaker AI 開発者ガイド「Automate data labeling」 https://docs.aws.amazon.com/sagemaker/latest/dg/sms-automated-labeling.html
- ERIC = ERIC Digest ED340272（Bonwell & Eison 1991 の要約） https://eric.ed.gov/?id=ED340272

---

C01 | アクティブラーニングの中心にある考えは、学習アルゴリズムが自分の学ぶデータを選べるなら、より少ない教師ラベルで高い精度に届くというものである | S | "The key idea behind active learning is that a machine learning algorithm can achieve greater accuracy with fewer training labels if it is allowed to choose the data from which it learns."

C02 | 学習側はラベルなしデータの形で質問を出し、人間の注釈者などのオラクルがそれにラベルを付ける | S | "An active learner may pose queries, usually in the form of unlabeled data instances to be labeled by an oracle (e.g., a human annotator)."

C03 | ラベルなしデータは大量に手に入るのに、ラベルを得るのは難しい・時間がかかる・高くつく、という場面でアクティブラーニングが動機づけられる | S | "Active learning is well-motivated in many modern machine learning problems, where unlabeled data may be abundant or easily obtained, but labels are difficult, time-consuming, or expensive to obtain."

C04 | 教師あり学習がうまく動くには、数百から数千のラベル付き事例で学習させる必要があることが多い | S | "Consider that, for any supervised learning system to perform well, it must often be trained on hundreds (even thousands) of labeled instances."

C05 | 音声の書き起こしでは、単語の単位で注釈を付ける作業が実際の音声の10倍（1分の音声に10分）、音素の単位では400倍（1分に7時間近く）かかる | S | "Zhu (2005a) reports that annotation at the word level can take ten times longer than the actual audio (e.g., one minute of speech takes ten minutes to label), and annotating phonemes can take 400 times as long (e.g., nearly seven hours). The problem is compounded for rare languages or dialects."

C06 | 情報抽出では、簡単なニュース記事でも人名・組織名や関係の箇所を見つけるのに30分以上かかることがあり、遺伝子や疾患の注釈には博士号を持つ生物学者が必要になる | S | "Locating entities and relations can take a half-hour or more for even simple newswire stories (Settles et al., 2008a). Annotations for other knowledge domains may require additional expertise, e.g., annotating gene and disease mentions for biomedical information extraction usually requires PhD-level biologists."

C07 | 機械学習のアクティブラーニングは、教育分野にある同名の指導法と精神的には通じるが、混同してはならない | S | "Note that this kind of active learning is related in spirit, though not to be confused, with the family of instructional techniques by the same name in the education literature (Bonwell and Eison, 1991)."

C08 | 教育分野の active learning は、学生が何かを行い、自分が行っていることについて考えることを伴う指導方略と定義されている（受け身で講義を聞くことの対義） | ERIC | "instructional strategies that involve students in doing things and thinking about what they are doing, as opposed to passive listening to a lecture."

C09 | プールベースのサンプリングでは、少数のラベル付きデータ L と大量のラベルなしデータ U があり、質問はプールから選ばれる | S | "This motivates pool-based sampling (Lewis and Gale, 1994), which assumes that there is a small set of labeled data L and a large pool of unlabeled data U available. Queries are selectively drawn from the pool"

C10 | 不確実性サンプリングは、ラベルの付け方が最も分からない事例を学習側が質問する枠組みで、おそらく最も単純でよく使われる | S | "Perhaps the simplest and most commonly used query framework is uncertainty sampling (Lewis and Gale, 1994). In this framework, an active learner queries the instances about which it is least certain how to label."

C11 | 二値分類で確率モデルを使う場合、不確実性サンプリングは陽性である事後確率が0.5に最も近い事例を質問する | S | "when using a probabilistic model for binary classification, uncertainty sampling simply queries the instance whose posterior probability of being positive is nearest 0.5 (Lewis and Gale, 1994; Lewis and Catlett, 1994)."

C12 | 3クラス以上では、最も確からしいラベルの確率が低い事例を選ぶ方法、1位と2位の確率の差が小さい事例を選ぶ方法（マージンサンプリング）、エントロピーを使う方法がある | S | "a more general uncertainty sampling variant might query the instance whose prediction is the least confident" / "margin sampling (Scheffer et al., 2001)" / "A more general uncertainty sampling strategy (and possibly the most popular) uses entropy (Shannon, 1948) as an uncertainty measure"

C13 | 2つのガウス分布から作った400件の二次元データで、無作為に選んだ30件で学習したロジスティック回帰は正解率70%、不確実性サンプリングで選んだ30件では90%だった | S | "(b) A logistic regression model trained with 30 labeled instances randomly drawn from the problem domain. The line represents the decision boundary of the classifier (70% accuracy). (c) A logistic regression model trained with 30 actively queried instances using uncertainty sampling (90%)."

C14 | 20 Newsgroups の野球とホッケーの文書2,000件を見分ける課題で、30件を新たにラベル付けした時点の正解率は不確実性サンプリングが81%、無作為が73%だった | S | "After labeling 30 new instances, the accuracy of uncertainty sampling is 81%, while the random baseline is only 73%."

C15 | 最初期の場面はメンバーシップクエリ学習（Angluin 1988）で、学習側は入力空間の任意の事例のラベルを要求でき、典型的には自分で事例を新しく作り出す | S | "One of the first active learning scenarios to be investigated is learning with membership queries (Angluin, 1988). In this setting, the learner may request labels for any unlabeled instance in the input space, including (and typically assuming) queries that the learner generates de novo, rather than those sampled from some underlying natural distribution."

C16 | Lang と Baum は1992年に手書き文字を分類するニューラルネットの学習でメンバーシップクエリを人に答えさせたが、学習側が生成した質問画像の多くは認識できる記号を含まず、自然な意味を持たない人工的な合成文字だった | S | "For example, Lang and Baum (1992) employed membership query learning with human oracles to train a neural network to classify handwritten characters. They encountered an unexpected problem: many of the query images generated by the learner contained no recognizable symbols, only artificial hybrid characters that had no natural semantic meaning."

C17 | 任意の事例を人が答えにくいという限界に対処するため、ストリームベースとプールベースの場面が提案された | S | "The stream-based and pool-based scenarios (described in the next sections) have been proposed to address these limitations."

C18 | ストリームベースの選択的サンプリング（Cohn et al., 1990, 1994）は、ラベルなし事例を1件ずつ実際の分布から取り出し、学習側が質問するか捨てるかを決める | S | "An alternative to synthesizing queries is selective sampling (Cohn et al., 1990, 1994). ... each unlabeled instance is typically drawn one at a time from the data source, and the learner must decide whether to query or discard it."

C19 | ストリームベースは順に走査して1件ずつ質問するかを決め、プールベースは集合全体を評価して順位を付けてから最良の質問を選ぶ | S | "The main difference between stream-based and pool-based active learning is that the former scans through the data sequentially and makes query decisions individually, whereas the latter evaluates and ranks the entire collection before selecting the best query."

C20 | Lewis と Gale は1994年に不確実性サンプリングを提案し、一定の性能に届くまでに人手で分類する学習データの量を最大500分の1に減らした | LG | "An algorithm for sequential sampling during machine learning of statistical classifiers was developed and tested on a newswire text categorization task. This method, which we call uncertainty sampling, reduced by as much as 500-fold the amount of training data that would have to be manually classified to achieve a given level of effectiveness."

C21 | 経済的にラベル付けできる量より多くのテキストがあることが多く、無作為抽出は通常うまくいかない。1000件に1件しか該当しない場合、500件しかラベル付けできなければ無作為標本は通常500件すべてが非該当になり、該当と非該当を見分ける学習にならない | LG | "There is often more text available than can be economically labeled, so a subset or sample of the data must be chosen to label. Random sampling will usually not be effective. If only 1 in 1000 texts are class members (not atypical), and only 500 texts can be labeled, then a random sample will usually contain 500 negative examples and no positive ones. This will not support training a classifier to distinguish positive from negative examples."

C22 | 不確実性サンプリングの手順は、(1)初期分類器を作る (2)教師が答えてくれる間、現在の分類器を各ラベルなし事例に当て、クラス所属が最も不確かなb件を見つけ、そのb件に教師がラベルを付け、全ラベル付き事例で新しい分類器を学習する、の繰り返しである | LG | "1. Create an initial classifier / 2. While teacher is willing to label examples / (a) Apply the current classifier to each unlabeled example / (b) Find the b examples for which the classifier is least certain of class membership / (c) Have the teacher label the subsample of b examples / (d) Train a new classifier on all labeled examples"

C23 | 1回に選ぶ件数 b は理想的には1件だが、事例を採点して選ぶ処理が高くつく場合は大きい値が適切なことがある | LG | "Ideally b, the number of examples selected on each iteration, would be 1, but larger values may be appropriate if scoring and selecting examples is expensive."

C24 | 初期分類器は重要な役割を果たす。それが無いと、頻度の低いクラスの事例に偶然ぶつかるまで長く無作為抽出が続きかねない | LG | "Note that the initial classifier plays an important role, since without it there may be a long period of random sampling before examples of a low frequency class are stumbled upon."

C25 | 実験は1988年から1993年初頭のAP通信の見出し371,454件を使い、学習用319,463件とテスト用51,991件に無作為に分けた | LG | "The titles of 371,454 items which appeared on the AP newswire between 1988 and early 1993 were divided randomly into a training set of 319,463 titles and a test set of 51,991 titles."

C26 | 使った10カテゴリは出現頻度が低く、例えば bonds カテゴリは学習セットに470件（頻度0.0015）だった | LG | Table 1: "bonds 470 0.0015 60 0.0012" / "The categories were chosen to have relatively low frequencies, while still providing a reasonable number of positive examples in both the training and test sets."

C27 | 各試行は該当する3件から初期分類器を作り、4件ずつ249回の不確実性サンプリングを行って合計999件にした | LG | "we instead used a starting subsample of 3 positive examples of the category randomly selected from the training set. ... On each run, the 3 starting examples were used to train an initial classifier, after which 249 iterations of uncertainty sampling with a subsample size of 4 were carried out"

C28 | 多くの場合、無作為抽出では10万件以上でやっと届く性能に、不確実性サンプリングは1000件未満で届いた。1000件を無作為に選んで学習した場合の性能は大きく劣った。ある場合には、同じ性能に届くのに無作為だと500倍の件数が要った | LG | "In most cases effectiveness levels reached by random sampling only with 100,000 or more training examples are reached by uncertainty sampling with less than 1000 examples, while training on 1000 randomly selected examples gives greatly inferior results. In some cases, reaching a given level of effectiveness requires 500 times as many randomly selected examples as examples selected by uncertainty sampling."

C29 | 10カテゴリのうち6つで、999件の不確実性標本で学習した分類器の平均F値が319,463件すべてで学習したものを上回った。著者らはこれを自分たちの学習方法が大きな学習セットを活かせていない兆候とみなし、特徴選択が最も疑わしいとした | LG | "For 6 of 10 categories, the mean F=1 for a classifier trained on a uncertainty sample of 999 examples actually exceeds that from training on the full training set of 319,463 examples. This means that some aspect of our classifier training is not making effective use of large training sets. Feature selection is the most likely villain."

C30 | 10カテゴリのうち tickertalk ではどの方法もうまくいかなかった | LG | "Results for 9 categories are presented, omitting tickertalk on which no strategy worked well."

C31 | 最初の3件の選び方が悪いと初期分類器が効かず、追加の該当事例が見つかるまでにかなりの遅れが出た。最終的な分類器の質にばらつきが残った | LG | "When a subsample was badly unrepresentative of the category, the initial classifier was ineffective, and there was a considerable delay before uncertainty sampling started to find additional positive examples."

C32 | アクティブラーナーと協調して作られた学習セットは質問を選んだモデルの種類に結びついており、ラベル付き事例は自然な分布からの独立同分布標本ではなく偏った分布になる。モデルの種類を変えると、その学習セットは新しいモデルには同じように役立たなくなりうる | S | "consider that a training set built in cooperation with an active learner is inherently tied to the model that was used to generate it (i.e., the class of the model selecting the queries). Therefore, the labeled instances are a biased distribution, not drawn i.i.d. from the underlying natural density. If one were to change model classes—as we often do in machine learning when the state of the art advances—this training set may no longer be as useful to the new model class"

C33 | Schein と Ungar は2007年に、同じモデルの種類（ロジスティック回帰）を使った場合でも、アクティブラーニングが受動的学習より多くのラベル付き事例を必要とすることがあると示した | S | "Somewhat surprisingly, Schein and Ungar (2007) showed that active learning can sometimes require more labeled instances than passive learning even when using the same model class, in their case logistic regression."

C34 | Guo と Schuurmans は2008年に、既成の質問戦略をバッチモードで近視眼的に使うと、しばしば無作為抽出よりずっと悪くなることを見つけた | S | "Guo and Schuurmans (2008) found that off-the-shelf query strategies, when myopically employed in a batch-mode setting (Section 6.1) are often much worse than random sampling."

C35 | 注釈者の熟練度によってアクティブラーニングの効き方が変わるという報告がある。領域の専門家はアクティブラーナーにうまく使われ、初心者は受動的学習のほうが向いていた | S | "Baldridge and Palmer (2009) found a curious inconsistency in how well active learning helps that seems to be correlated with the proficiency of the annotator (specifically, a domain expert was better utilized by an active learner than a domain novice, who was better suited to a passive learner)."

C36 | 大規模な注釈プロジェクトでアクティブラーニングを使った研究者の91%が期待は完全または部分的に満たされたと答えた一方、回答者の20%は「自分の場面でうまくいくと確信できない」という理由で使わないことを選んだ | S | "Tomanek and Olsson (2009) report in a survey that 91% of researchers who used active learning in large-scale annotation projects had their expectations fully or partially met. Despite these findings, the survey also states that 20% of respondents opted not to use active learning in such projects, specifically because they were 'not convinced that [it] would work well in their scenario.'"

C37 | 注釈のコストが事例ごとに大きく変わる領域があり、コストを無視するアクティブラーニングは無作為選択（受動的学習）と変わらない結果になることがある | S | "In some domains, annotation costs are not (approximately) constant across instances, and can vary considerably. ... Consequently, active learning approaches which ignore cost may perform no better than random selection (i.e., passive learning)."

C38 | 注釈のコストは事例に内在するとは限らず、誰が注釈するかで変わる | S | "The cost of annotating an instance may not be intrinsic, but may instead vary based on the person doing the annotation."

C39 | 実用的な応用での本当の止めどきは、学習側が自分で決める閾値よりずっと手前に来る、経済的その他の外部要因で決まる | S | "However, in my own experience, the real stopping criterion for practical applications is based on economic or other external factors, which likely come well before an intrinsic learner-decided threshold."

C40 | 半教師あり学習とアクティブラーニングは同じ問題に逆方向から取り組む。半教師ありは学習側が知っていると思う部分を活用し、アクティブは未知の部分を探りにいく | S | "While semi-supervised methods exploit what the learner thinks it knows about the unlabeled data, active methods attempt to explore the unknown aspects."

C41 | 自己訓練では最も自信のあるラベルなし事例を予測ラベルごと学習セットに加えるが、不確実性サンプリングは最も自信のない事例を質問に選ぶ | S | "Typically the most confident unlabeled instances, together with their predicted labels, are added to the training set, and the process repeats. A complementary technique in active learning is uncertainty sampling (see Section 3.1), where the instances about which the model is least confident are selected for querying."

C42 | 人のラベルの質は高いとは限らない。ある事例は人にも機械にも本質的に難しく、人は時間とともに気が散ったり疲れたりして注釈の質にばらつきが出る | S | "First, some instances are implicitly difficult for people and machines, and second, people can become distracted or fatigued over time, introducing variability in the quality of their annotations."

C43 | SageMaker Ground Truth の自動データラベリングは、まず入力データの無作為標本を人に回し、返ってきたラベルから学習用と検証用のデータを作って自動ラベリング用のモデルを学習・検証する | AWS | "When Ground Truth starts an automated data labeling job, it selects a random sample of input data objects and sends them to human workers. / When the labeled data is returned, it is used to create a training set and a validation set. Ground Truth uses these datasets to train and validate the model used for auto-labeling."

C44 | 検証データへの推論で出た信頼度と品質指標から信頼度の閾値を決め、閾値を満たした対象は自動でラベル付け済みとみなし、信頼度の低い対象を人に回して、そのラベルでモデルを更新する | AWS | "The auto labeling component will use these quality metrics and confidence scores to create a confidence score threshold that ensures quality labels. ... Ground Truth selects data points with low confidence scores from this dataset and sends them to human workers. / Ground Truth uses the existing human-labeled data and this additional labeled data from human workers to update the model."

C45 | この繰り返しは、データセットがすべてラベル付けされるか、人の注釈予算に達するなどの停止条件を満たすまで続く | AWS | "The process is repeated until the dataset is fully labeled or until another stopping condition is met. For example, auto-labeling stops if your human annotation budget is reached."

C46 | 画像分類とテキスト分類では、自動で付けたラベルの正確さが人の付けるラベルに対して95%以上になる信頼度の水準が使われる | AWS | "For image classification and text classification, Ground Truth uses logic to find a label-prediction confidence level that corresponds to at least 95% label accuracy. This means Ground Truth expects the accuracy of the automated labels to be at least 95% when compared to the labels that human labelers would provide for those examples."

C47 | 自動データラベリングは数千件規模のデータに向く。許容される最小の対象数は1,250件だが、5,000件以上を強く推奨している | AWS | "Automated data labeling is most appropriate when you have thousands of data objects. The minimum number of objects allowed for automated data labeling is 1,250, but we strongly suggest providing a minimum of 5,000 objects."

C48 | Settles のサーベイは University of Wisconsin–Madison の Computer Sciences Technical Report 1648 として2009年に出され、この分野で初の大規模なサーベイだと著者自身が書いている | S | "Burr Settles. Active Learning Literature Survey. Computer Sciences Technical Report 1648, University of Wisconsin–Madison. 2009." / "This is the first large-scale survey of the active learning literature."

C49 | アクティブラーニングは統計の分野では「クエリ学習」「最適実験計画」と呼ばれることもある、機械学習の一分野である | S | "Active learning (sometimes called 'query learning' or 'optimal experimental design' in the statistics literature) is a subfield of machine learning and, more generally, artificial intelligence."

---

## 読めなかった出典

- https://link.springer.com/content/pdf/10.1007/BF00993277.pdf （Cohn, Atlas, Ladner 1994 "Improving Generalization with Active Learning"）… 303リダイレクトで Springer の認証に飛び、本文を読めなかった。この論文の内容は Settles のサーベイ経由（C18）でのみ扱い、原文の引用は使わない。

---

## 追加（初稿執筆中に台帳へ足したもの）

C50 | Lewis と Gale の所属は AT&T ベル研究所（ニュージャージー州マレーヒル）である | LG | "David D. Lewis (lewis@research.att.com) and William A. Gale (gale@research.att.com) / AT&T Bell Laboratories; Murray Hill, NJ 07974; USA"

C51 | プールベースの場面は、応用を扱う論文ではストリームベースよりずっとよく見られる | S | "While the pool-based scenario appears to be much more common among application papers, one can imagine settings where the stream-based approach is more appropriate."

C52 | Settles のサーベイの著者所蔵版は burrsettles.com で公開されている（2026-10-11 に取得して同一文書であることを確認した） | https://burrsettles.com/pub/settles.activelearning.pdf | 取得したPDFの表題行が "Active Learning Literature Survey / Burr Settles / Computer Sciences Technical Report 1648 / University of Wisconsin–Madison" であることを確認
