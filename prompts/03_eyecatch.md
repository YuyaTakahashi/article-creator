# アイキャッチ画像プロンプト生成

## 手順

{topic} を TOPIC_JP とする。必ず日本語のままにすること。

ABSTRACT_VISUAL_EN を考案する前に、まず構図の「セーフゾーン」を意識すること。
OGP（X / Facebook / LinkedIn など）のサムネは元画像を 1.91:1 にクロップして表示するため、1:1 の画像は上下が約 24% ずつ削られる。
そのため、タイトル文字・主要シルエット・キャプション等すべての重要要素を **縦中央の高さ 52%（上下 24% は完全に余白）に収まる構図** で設計すること。
左右にも最低 12% の余白を確保し、要素を端まで広げない。

イラストは「画面いっぱいに広げる」発想ではなく、「先に余白を確保したうえで中央の枠内に必要な要素だけを置く」発想で組み立てる。完成後にスケール調整・トリミングで余白を後付けしない（要素が潰れるため）。

以下の [記事テキスト] の内容を表現する、シンプルで抽象的な視覚メタファー（比喩）を英語で考案する。
具体的なUI画面・複雑な機械そのものではなく、概念を図形や流れで表すイメージにすること。
要素は欲張らず、人物・象徴オブジェクト・少数の幾何形状の組み合わせ程度に抑える（中央 52% に収めるため）。
これを ABSTRACT_VISUAL_EN とする。

以下のフォーマットの {} 部分を埋めて、完成したプロンプトを出力する。

## プロンプトフォーマット

A flat vector illustration on a solid warm cream beige background #F2F0E6. The final file is 1:1, but all critical content must fit within the central 52% vertical band so that nothing is cropped when displayed as a 1.91:1 OGP thumbnail; the top 24% and bottom 24% of the canvas must be left empty as buffer, and at least 12% lateral padding must be kept on each side. Within this safe central band, near the top, the Japanese text '{TOPIC_JP}' is displayed in bold, dark charcoal, sans-serif font. Below the text, {ABSTRACT_VISUAL_EN}. Compose the scene with breathing room rather than filling the frame. Minimal corporate art style with thick dark charcoal outlines. Simple geometry, high contrast, no shading. Muted blue and grey palette. The illustration block must preserve an exact 16:10 aspect ratio, even though the final file is 1:1.

## 制約

- 出力は完成したプロンプトのテキストのみ
- ダブルクォーテーション（"）禁止、強調が必要な場合はシングルクォーテーション（'）を使用
- 解説・挨拶は不要
- 余白を先に確保したうえで構図を考えること。完成後にスケール調整・余白追加で帳尻を合わせるのは不可（絵が潰れるため）

## [記事テキスト]

{article}
