# 出典台帳：勾配消失・勾配爆発

収集日: 2026-10-12 / 収集方法: WebSearch + WebFetch（ディープリサーチ未実施）／2026-10-25 に説明の材料（C32〜C46）を追加

```
C01 | 勾配消失問題とは、誤差逆伝播でニューラルネットを学習するとき、入口に近い層と出口に近い層とで勾配の大きさが大きく食い違う問題である | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "In machine learning, the vanishing gradient problem is the problem of greatly diverging gradient magnitudes between earlier and later layers encountered when training neural networks with backpropagation."
C02 | 入口に近い層の勾配が指数的に大きくなる逆向きの問題を勾配爆発問題と呼ぶ | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "The inverse problem, when weight gradients at earlier layers get exponentially larger, is called the exploding gradient problem."
C03 | 再帰重み行列のスペクトル半径 γ が1未満なら、k 歩さかのぼった時点の掛け合わせの大きさは γ の k 乗で抑えられ、k が大きくなると0に近づく。これが典型的な勾配消失である | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "So if the spectral radius of W rec is γ < 1, then at large k, the above multiplication has operator norm bounded above by γ k → 0. This is the prototypical vanishing gradient problem."
C04 | 勾配が消えると、ネットワークは長い範囲にまたがる影響を学習できない | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "The effect of a vanishing gradient is that the network cannot learn long-range effects"
C05 | Hochreiter の1991年の学位論文が、学習がうまくいかない理由を「勾配消失問題」として形式的に特定した。これは多層の順伝播型ネットだけでなく再帰型ネットにも影響する | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "Hochreiter's diplom thesis of 1991 formally identified the reason for this failure in the 'vanishing gradient problem', which not only affects many-layered feedforward networks, but also recurrent networks."
C06 | シグモイド関数の微分は絶対値が1以下である | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "Since | σ ′ | ≤ 1, the operator norm of the above multiplication is bounded above by ‖ W rec ‖ k."
C07 | LSTM はこの問題を解くために設計された | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "the long short-term memory (LSTM) network was designed to solve the problem"
C08 | 勾配クリッピングは、勾配ベクトル g の大きさが g_max を超えたとき ‖g‖/g_max で割る | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "dividing the gradient vector g by ‖g‖/g_max if ‖g‖>g_max"
C09 | バッチ正規化は勾配爆発と勾配消失の両方を解く標準的な手法である | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "a standard method for solving both the exploding and the vanishing gradient problems"
C10 | ReLU は片側にしか飽和しないので、勾配消失の影響が小さい | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "suffer less from the vanishing gradient problem, because they only saturate in one direction"
C11 | 残差接続は ∇f+I の勾配を与え、恒等行列の分は消失も爆発もしない | https://en.wikipedia.org/wiki/Vanishing_gradient_problem | "gives the gradient of ∇f+I, where the identity matrix do not suffer from the vanishing or exploding gradient"
C12 | 勾配爆発問題とは、学習中に勾配のノルムが大きく増えることを指す | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "the exploding gradients problem refers to the large increase in the norm of the gradient during training."
C13 | 勾配消失問題はその逆の振る舞いで、長期の成分が指数的に速くノルム0へ向かう | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "the vanishing gradients problem refers to the opposite behaviour, when long term components go exponentially fast to norm 0."
C14 | 再帰重み行列の最大固有値の絶対値 λ1 が 1/γ 未満であれば勾配消失には十分である | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "It is sufficient for λ1<1/γ, where λ1 is the absolute value of the largest eigenvalue of the recurrent weight matrix."
C15 | 勾配のノルムが急に増えたときの単純な対処は、しきい値を超えたときに大きさを縮めることである | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "One simple mechanism to deal with a sudden increase in the norm of the gradients is to rescale them whenever they go over a threshold."
C16 | しきい値の決め方のよい経験則は、十分な回数の更新にわたる平均ノルムの統計を見ることである | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "One good heuristic for setting this threshold is to look at statistics on the average norm over a sufficiently large number of updates."
C17 | クリッピングを加えた確率的勾配降下法は、時間順序の課題を200ステップまでの系列で成功率100%で解いた | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | "SGD-CR solved the task with a success rate of 100% for sequences up to 200 steps"
C18 | この論文は、勾配爆発・勾配消失の両方を導入した文献として Bengio et al. 1994 を引いている | https://arxiv.org/abs/1211.5063 (ar5iv版で閲覧) | 本文中の引用が "Bengio et al. 1994" を両問題の出典として示す（WebFetch の読み取り結果）
C19 | 深いネットを学習させる上での障害は、勾配消失・勾配爆発という有名な問題で、最初から収束を妨げる | https://arxiv.org/abs/1512.03385 (ar5iv版で閲覧) | "An obstacle to answering this question was the notorious problem of vanishing/exploding gradients, which hamper convergence from the beginning."
C20 | この問題は、正規化された初期化と中間の正規化層によって大きく解決され、数十層のネットが収束し始められるようになった | https://arxiv.org/abs/1512.03385 (ar5iv版で閲覧) | "This problem, however, has been largely addressed by normalized initialization and intermediate normalization layers, which enable networks with tens of layers to start converging."
C21 | 深いネットが収束し始めると劣化問題が現れた。深さが増すと精度が飽和し、その後急速に落ちる | https://arxiv.org/abs/1512.03385 (ar5iv版で閲覧) | "When deeper networks are able to start converging, a degradation problem has been exposed: with the network depth increasing, accuracy gets saturated (which might be unsurprising) and then degrades rapidly."
C22 | 残差ネットワークのアンサンブルは ImageNet のテストで3.57%の誤り率を出し、深さは最大152層でVGGの8倍である | https://arxiv.org/abs/1512.03385 (ar5iv版で閲覧) | "An ensemble of these residual nets achieves 3.57% error on the ImageNet test set" / "a depth of up to 152 layers—8×deeper than VGG nets."
C23 | 勾配爆発の兆候は、損失関数が異常に大きく振れることや NaN になること | https://deepai.org/machine-learning-glossary-and-terms/exploding-gradient-problem | "the loss function showing unusually large fluctuations or becoming NaN"
C24 | 勾配や重みの更新が想定より何桁も大きくなるのも兆候である | https://deepai.org/machine-learning-glossary-and-terms/exploding-gradient-problem | gradients/weight updates "several orders of magnitude larger than expected"
C25 | 勾配クリッピングは、しきい値を設け、勾配がそれを超えたら扱える範囲に縮める手法である | https://deepai.org/machine-learning-glossary-and-terms/exploding-gradient-problem | "Gradient Clipping: This technique involves setting a threshold value, and if the gradient exceeds this threshold, it is scaled down to keep it within a manageable range."
C26 | Xavier や He といった適切な重み初期化が対策に挙がる | https://deepai.org/machine-learning-glossary-and-terms/exploding-gradient-problem | "Weight Initialization: Using a proper weight initialization strategy, such as Xavier or He initialization"
C27 | ResNet のようにスキップ接続を持つアーキテクチャへ変えることが対策に挙がる | https://deepai.org/machine-learning-glossary-and-terms/exploding-gradient-problem | "Change of Network Architecture: Simplifying the network architecture or using architectures that are less prone to exploding gradients, such as those with skip connections like ResNet"
C28 | Hochreiter のフルネームは Josef "Sepp" Hochreiter である | https://en.wikipedia.org/wiki/Sepp_Hochreiter | "Josef \"Sepp\" Hochreiter"
C29 | Hochreiter は1991年の学位論文で LSTM のネットワーク構造を作った | https://en.wikipedia.org/wiki/Sepp_Hochreiter | "Hochreiter developed the long short-term memory (LSTM) neural network architecture in his diploma thesis in 1991"
C30 | LSTM は、長い系列から学べなくする数値の不安定さ（勾配の消失または爆発）を乗り越える | https://en.wikipedia.org/wiki/Sepp_Hochreiter | "LSTM overcomes the problem of numerical instability in training recurrent neural networks (RNNs) that prevents them from learning from long sequences (vanishing or exploding gradient)."
C31 | 学位論文はミュンヘン工科大学の情報科学科で書かれた | https://en.wikipedia.org/wiki/Sepp_Hochreiter | "Technical University of Munich, Institute of Computer Science."
C32 | （前提）ニューラルネットワークは、たくさんの見本の入力を使って学習する | https://en.wikipedia.org/wiki/Neural_network_(machine_learning) | "NNs typically require vast numbers of sample inputs"
C33 | （前提）ニューラルネットワークは、情報を処理する部品を層にまとめ、入口の層から出口の層へ信号を通す。途中に複数の層をはさむことが多い | https://en.wikipedia.org/wiki/Neural_network_(machine_learning) | "Groups of neurons are aggregated into layers." "Signals travel from the first layer (the input layer) to the last layer (the output layer), typically passing through multiple intermediate layers"
C34 | （前提）学習とは、予測と正解の差が小さくなるように、つながりの強さ（重み）を調整することである | https://en.wikipedia.org/wiki/Neural_network_(machine_learning) | "Empirical risk minimization adjusts node and link weights to minimize the difference between the predicted output and the known values in the training samples."
C35 | （前提）誤差逆伝播は、学習中に見つかった誤りを埋め合わせるように重みを調整する方法である | https://en.wikipedia.org/wiki/Neural_network_(machine_learning) | "Backpropagation is a method used to adjust the connection weights to compensate for errors found during learning."
C36 | （働き）勾配は、ニューラルネットワークの重みを直すために使う値である | https://www.educative.io/answers/what-is-the-vanishing-gradient-problem | "These gradients are used to update the weights of the neural network."
C37 | （働き）重みは、勾配に比例した量だけ直される。勾配が小さければ直す量も小さい | https://deeplizard.com/learn/video/qO_NLVjD6zE | "the weight gets updated in some way that is proportional to the gradient."
C38 | （手計算）C03・C13の仕組み：1より小さい数を掛け続けると値は小さくなる。0.5を1回・2回・3回掛けると0.5、0.25、0.125になり、10回で約0.001になる | —（計算） | 仕組みの出典: https://deeplizard.com/learn/video/qO_NLVjD6zE "the product of a bunch of numbers less than one is going to give us an even smaller number"
C39 | （手計算）C02・C12の仕組み：1より大きい数を掛け続けると値は大きくなる。2を1回・2回・3回掛けると2、4、8になり、10回で1024になる | —（計算） | 仕組みの出典: C02・C12
C40 | （結果）勾配消失が起きた層は、学習がとても遅くなるか、まったく学習しない | https://developers.google.cn/machine-learning/crash-course/neural-networks/backpropagation?hl=zh-tw | "梯度消失的圖層訓練速度非常緩慢，或完全無法訓練。"
C41 | （結果）勾配が小さいと、重みはほとんど動かず、学習が止まったような状態になる | https://deeplizard.com/learn/video/qO_NLVjD6zE | "it's just barely going to move the weight at all." "Not moving, not learning"
C42 | （結果）勾配消失は気づかれにくい。出口に近い層が学ぶので損失は下がり続けるが、入口に近い層は学習前の値に近いまま残る | https://www.ultralytics.com/glossary/vanishing-gradient | "Vanishing gradients stall learning silently" "the loss still falls, driven by the last layers" "while the early layers stay close to their random initialization"
C43 | （結果）勾配が大きすぎると、学習が落ち着かない（収束しない） | https://developers.google.cn/machine-learning/crash-course/neural-networks/backpropagation?hl=zh-tw | "梯度過大而無法收斂。"
C44 | （結果）勾配爆発では重みを大きく動かしすぎ、最適な値からどんどん離れていく | https://deeplizard.com/learn/video/qO_NLVjD6zE | "we're going to greatly move it" "continues to move further and further away from its optimal value."
C45 | （働き）ReLU は勾配消失を避けるのに役立ち、バッチ正規化や学習率（一度に直す量の目安）を下げることは勾配爆発を避けるのに役立つ | https://developers.google.cn/machine-learning/crash-course/neural-networks/backpropagation?hl=zh-tw | "ReLU 活化函式有助於避免梯度消失。" "批次正規化有助於避免梯度爆炸，降低學習率也有相同效果。"
C46 | （たとえ）勾配消失は一歩進むごとに視界が少しずつ暗くなる迷路、勾配爆発は一歩ごとに走る速さが増して止まれなくなる迷路にたとえられる。ずれ：実際の勾配は時間とともに弱るのではなく、層をさかのぼるたびに値を掛け合わせて縮む・膨らむ | https://deepgram.com/ai-glossary/vanishing-and-exploding-gradients | "Imagine trying to find your way out of a maze, but with each step, your vision dims slightly" "this would be like each step causing you to run faster, until you're moving too quickly"
```

## 読めなかった出典

- https://arxiv.org/pdf/1211.5063 （PDF直読みが不可。ar5iv の HTML 版で代替した）
- https://pdfs.semanticscholar.org/ba18/247cd3ce9f711eecc7296f1c3561dbfb6cc2.pdf （Bengio, Simard, Frasconi 1994 の本体。PDFが解析できず、原文の引用は取れなかった。1994年論文の内容は C18 のとおり他論文が引いている形でのみ使う）
- https://ar5iv.labs.arxiv.org/html/1404.7828 （Schmidhuber のサーベイ。返答が要約で、原文の引用として使える文が取れなかったため使わない）
