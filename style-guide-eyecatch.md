# UX TIMES 用語集 アイキャッチ スタイルガイド

7枚のアイキャッチ（FDE / 努力ヒューリスティック / ネットワーク効果 / 神経可塑性 / プロプライエタリ・テクノロジー / プロテジェ効果 / Chain-of-Thought）から抽出した共通要素。

## 共通フォーマット

| 要素 | 仕様 |
|---|---|
| アスペクト比 | 1:1（正方形） |
| 解像度 | 1024×1024 を基準（1000〜2000まで許容） |
| 背景色 | ベージュ／クリーム `#F5EFE0` 〜 `#EBE5D5` |
| タイトル位置 | **画像中央上寄り**（上から25〜40%の帯）。**上端から少なくとも200px（≒20%）の余白を取る** |
| タイトルフォント | 太字日本語サンセリフ（Noto Sans JP相当）、色 `#1A1A1A` |
| メインイラスト位置 | 中央〜中央下（上から40〜80%の帯） |
| 上下マージン | **各20%以上**の空白を確保 |

## アイキャッチ生成の注意（指摘反映・必ず守る）

- タイトル文字：フロントマター `title` の括弧前の日本語呼称を使う。**日本語呼称が無い英語句の用語は、英語フルネームをそのまま入れる**（例：`HMW（How Might We）` → アイキャッチには「How might we」）。余計な引用符（`' '`）は付けない。
- タイトルは**縦の中央付近に置き、サイズは大きめ**で読みやすく。上端に貼り付けない。
- 背景は**クリームベージュ1色を全面（端まで）一体で描かせる**。**外部の余白追加（`add_eyecatch_padding.py`）は使わない**——後付け余白は色が本体と微妙に違い継ぎ目が出るため、`generate_eyecatch.py` のプロンプト側で余白込みのレイアウトをまとめて描かせる。
- 画像生成は遅いので、複数枚作るときは**並列実行**する。

## OGPセーフエリア（重要）

Twitter/Xの大判カード（`summary_large_image`）は元画像を **1.91:1** にクロップして表示する。1024×1024 の元画像なら、上下それぞれ約 **244px**（≒24%）が見切れる。

**タイトルとメインイラスト**は、クロップ後も見える縦帯 **y=240〜780px**（中央540px）に必ず収める。上下の余白部分も**白には絶対しない、クリームベージュ`#F5EFE0`を保つ**。プロンプトでは具体的なピクセル位置を明示する。

| 領域 | 位置（1024×1024 基準） | 内容 |
|---|---|---|
| 上部セーフ余白 | 0 〜 240px | クリームベージュ背景のみ。OGPで切れてOK。**白にしない** |
| タイトル帯（OGP内） | 240 〜 380px | 日本語太字タイトル（OGPでも見える） |
| イラスト帯（OGP内） | 380 〜 780px | メインビジュアル（OGPでも見える） |
| 下部セーフ余白 | 780 〜 1024px | クリームベージュ背景のみ。OGPで切れてOK。**白にしない** |

## 配色（共通パレット）

| 役割 | 色 | 用途 |
|---|---|---|
| 背景 | `#F5EFE0` | カード地、メインキャンバス |
| メイン線・テキスト | `#1A1A1A` | アウトライン、文字 |
| 主要塗り | `#7A8DA0`（ブルーグレー） | 人物・主要オブジェクト |
| アクセント1 | `#C9A35E`（マスタード） | 一部の強調 |
| アクセント2 | `#8FA68C`（モスグリーン） | 一部の強調 |
| サブ淡色 | `#D8C8A8`（ベージュ濃） | 補助要素 |

色数は **3〜4色** に抑える。グラデーション・写実的シェーディングは使わない。

## イラストの型（A〜C のいずれか）

**A. 人物対話型**（FDE / プロテジェ効果）
- 2〜3人のシルエットまたは線画キャラクター
- 吹き出し・思考バルーンで概念を表現
- 用途：人と人の関係性、対話、共同作業を扱う用語

**B. 概念図型**（努力ヒューリスティック / プロプライエタリ・テクノロジー / Chain-of-Thought）
- 1〜3個の主要シンボル（人・物体・鍵・電球・チェーンなど）
- 矢印・点線・関係線で概念を可視化
- 用途：因果関係・構造を扱う用語

**C. インフォグラフィック型**（ネットワーク効果 / 神経可塑性）
- ネットワーク図・脳図など、概念そのものを抽象化した図
- 用途：複雑な仕組み・現象を扱う用語

## 制約

- 写実的なフォトイラストは使わない
- 派手なグラデーション、ドロップシャドウ強調は使わない
- 画像内に英語の追加テキスト（ラベル等）は最小限。タイトル日本語のみ前提
- Gemini透かし「✦」は気にしない（自動で入る、本文挿入時にトリミング可）

## プロンプトテンプレート（Gemini 2.5 Flash Image / Nano Banana 用）

下の英語テンプレを使い、`{TITLE_JP}` / `{CORE_METAPHOR}` / `{KEY_OBJECTS}` / `{ILLUSTRATION_TYPE}` のみ用語ごとに差し替える。

```text
Create a square (1:1) editorial illustration for a Japanese UX glossary article.

STYLE — strict:
- Background: warm cream beige (#F5EFE0), flat, no texture
- Composition type: {ILLUSTRATION_TYPE}  # one of: "two-person dialogue", "conceptual diagram with arrows", "abstract infographic"
- Color palette: limited to 3–4 colors — beige background (#F5EFE0), black outlines (#1A1A1A), soft blue-gray fills (#7A8DA0), and optionally one accent of muted mustard (#C9A35E) or moss green (#8FA68C)
- Style: flat, minimalist, line-art with subtle fills, modern editorial, generous whitespace
- No gradients, no drop shadows, no photorealism, no neon, no harsh colors
- Text: ONLY the title "{TITLE_JP}" in bold Japanese sans-serif (Noto Sans JP style), centered horizontally, black color, about 6–8% of the canvas height
- No other text, labels, watermarks, captions, or signatures anywhere

LAYOUT — generous margins on ALL four sides (CRITICAL):
All content (title AND illustration) MUST be confined to the inner 60% × 60% rectangle of the canvas. For a 1024×1024 image, that rectangle is x=205 to x=820, y=205 to y=820. The outer 20% on every side — top, bottom, LEFT, and RIGHT — is empty cream-beige margin. This serves two purposes: (a) Twitter/X OGP large cards crop to 1.91:1 (center crop) and would chop the title if it sits near the top edge, and (b) the brand style requires generous breathing room on all sides.

- 0–240px (top edge): cream beige background (#F5EFE0) only. NO content here. This is the OGP-clipped safe margin. CRITICAL: keep this area filled with the SAME cream beige color #F5EFE0, NOT white, NOT a different shade.
- 240–380px: title text "{TITLE_JP}" centered horizontally — this must sit INSIDE the OGP visible band so it shows on Twitter.
- 380–780px: the main illustration, centered inside the OGP visible band.
- 780–1024px (bottom edge): cream beige background (#F5EFE0) only. NO content here. CRITICAL: keep this area filled with the SAME cream beige color #F5EFE0, NOT white.

The ENTIRE canvas — including the top and bottom OGP-clipped margins — must be one continuous cream beige background. Do NOT switch to white or any other color in the margins. The cream beige extends edge-to-edge.

SUBJECT:
{CORE_METAPHOR}

KEY VISUAL ELEMENTS:
{KEY_OBJECTS}

OUTPUT: 1024x1024 PNG. Keep the title and illustration vertically centered within the middle 60% of the canvas. Avoid placing any content in the top or bottom 20% bands.
```

### プロンプト要素の決め方

1. **TITLE_JP**：フロントマターの `title` フィールドから括弧書きを除いた日本語名（例：「FDE」「努力ヒューリスティック」「Chain-of-Thought」）
2. **ILLUSTRATION_TYPE**：用語の性質から選ぶ
   - 人と人の関係 → `two-person dialogue`
   - 因果・構造 → `conceptual diagram with arrows`
   - 仕組み・現象 → `abstract infographic`
3. **CORE_METAPHOR**：用語の本質を1〜2文の英語で表現。記事の「最小限の説明」を英訳しつつ、視覚化しやすい表現に翻訳
4. **KEY_OBJECTS**：イラストに含める具体的なモチーフを2〜4個、英語で列挙

### 既存7枚のプロンプト要素対応例

| 用語 | TYPE | CORE_METAPHOR | KEY_OBJECTS |
|---|---|---|---|
| FDE | two-person dialogue | A casual engineer with a laptop converses with a business executive about deploying AI into a real workplace | casual engineer in hoodie with laptop, business executive in suit, two speech bubbles with dots |
| 努力ヒューリスティック | conceptual diagram | A person carrying a heavy stack of boxes is evaluated more highly, symbolized by an upward arrow leading to a glowing star | stylized human figure hunched under stacked boxes, upward arrow, sparkling star |
| ネットワーク効果 | abstract infographic | A dense network of dots and connecting lines forms a multi-faceted sphere whose value grows with each new participant | dense radial node-and-edge network, central glow, subtle upward arrows |
| 神経可塑性 | abstract infographic | A human head profile in the center, flanked by "before" and "after" panels showing rigid vs. reorganized neural circuits | human head profile silhouette, left panel with rigid circuit lines, right panel with reorganized network and small icons of light bulb, synapse, leaf |
| プロプライエタリ・テクノロジー | conceptual diagram | A central padlock symbol radiates dashed arrows to three abstract shapes representing isolated proprietary assets | padlock in the center with keyhole, three peripheral shapes (square, circle, diamond), dashed arrows |
| プロテジェ効果 | two-person dialogue | A teaching figure on the left visualizes a lightbulb of insight while explaining shapes to a listening figure on the right | two simple human silhouettes facing each other, thought bubble with lightbulb on the teacher side, speech bubble with circle/triangle/square on the explanation side |
| Chain-of-Thought | conceptual diagram | Three human head profiles in a row each with a glowing lightbulb above, connected by a heavy chain at the bottom representing linked reasoning steps | three side-view head silhouettes, three lightbulbs with rays, horizontal chain of links beneath the heads |

---

# 挿絵スタイル（NotebookLM風）— 記事本文の「章ごとの挿絵」に適用

> 上記のアイキャッチ（クリーム背景・フラット線画）とは**別ルール**。記事本文に差し込む章ごとの挿絵は、以下の NotebookLM 風スタイルで生成する。`scripts/gen_image.py` のプロンプトにこのルールを必ず反映する。アイキャッチには適用しない。

## デザインコンセプト
- スタイル：ミニマル、モダン、抽象的な幾何学形状を用いたフラットデザイン
- 配色：**白を基調**とした背景。アクセントカラーは控えめに
- 構成：中央にメインの概念図を配置し、周囲に十分なホワイトスペースを確保する。単純なアイコン1個で終わらせず、**2〜3段階の小さな図（前後・流れ・比較）＋短い日本語ラベル**で「章の内容が一目で伝わる」ようにする（ただし詰め込みすぎない）。各段階に短い注釈（数語）を添え、流れと理由まで伝わる“説明図”寄りにする（アイコンだけの飾りで終わらせない）
- テイスト：NotebookLM の動画生成で作られるような、わかりやすくキャッチーなイラストをベースにする。**ただし可愛くしすぎない**——キャラクターの顔やデフォルメは最小限（必要なら中立的なピクトグラム程度）にとどめ、**アイコン・矢印・短いラベル中心の「説明的・図解的」なトーン**にする。過度にキャラクター主体のかわいいイラストは避ける

## テキストおよび要素の制限（最重要）
- 言語：画像内のテキストは「日本語」のみ。英語は使わない
- 文字数：長い説明文は避け、単語や短いフレーズのみを配置する
- 禁止事項：特定のサービス名（NotebookLM、Google など）・そのロゴ・アイコン・ウォーターマーク・「cite:x」等の注釈文言を、画面内のいかなる場所にも絶対に描画しない
- 英語・ラテン文字は一切描かない（「Stage」「Step」等の英単語もNG）。段階番号が必要なら **①②③** のみを使う
- 複数段階は**左→右のフロー**で統一する（原因→行動→結果のように読めると分かりやすい。段階構成にしないと意味が伝わりにくい）
- 画像生成は遅いので、複数枚は**並列実行**する

## 出力形式
- 1枚の画像にまとめず、1つの章につき1つのファイルを生成する
- ファイル名やタイトルに連番（1, 2…）を含めない（章の内容を表す名前にする）
- 保存先：`drafts/images/{topic-slug}/{章を表す名前}.png`

## gen_image.py 用プロンプト雛形（SUBJECT と日本語ラベルのみ章ごとに差し替え）

```text
Create a minimal, modern infographic illustration in the visual style of NotebookLM's video-generated illustrations — simple, friendly, catchy, easy enough for a child to understand.

BACKGROUND: clean solid white (#FFFFFF), with generous whitespace.
STYLE: flat design built from simple abstract geometric shapes, rounded friendly forms, thin clean outlines; a few muted accent colors used sparingly (soft blue, warm yellow, soft coral, soft green) on a mostly white canvas. No gradients, no 3D, no drop shadows, no photorealism.
COMPOSITION: one main concept diagram centered, surrounded by ample empty white space.
TEXT: ONLY short Japanese words or short phrases as labels (a few characters each), in a clean rounded Japanese sans-serif, spelled correctly. NO English text anywhere.
FORBIDDEN (critical): do NOT draw any brand or service names or logos (no "NotebookLM", no "Google"), no watermarks, no "cite" annotations, no signatures, no long sentences.

SUBJECT (this chapter): {CONCEPT_JP_AND_VISUAL}
JAPANESE LABELS TO INCLUDE (short): {SHORT_JP_LABELS}

OUTPUT: square PNG, white background, child-friendly, catchy, minimal.
```

---

## 追記：アイキャッチ／挿絵の運用知見（2026-06 セッション反映）

### アイキャッチ（house cream スタイルへの追加ルール）
- **タイトルは日本語のみ**。英語サブタイトル（"System of Engagement" 等）は入れない。日本語呼称が無い用語だけ英語フルネームを使う。
- **OGPで切れない上部余白**：X/Twitter 大判カードは上下各 約24% をクロップする。タイトルを上端に貼らず、キャンバスの約35〜40%（中央寄り）に置く。上部の約1/3は空ける。
- **上下の余白は均等に**。タイトル＋イラストのブロックを縦方向に中央寄せし、上下のクリーム余白をほぼ同じにする。
- **並列要素（レイヤー等）は縦積みより横並び**の方が正方形内でバランスが取りやすい。3層モデルなどは左→右の横一列を優先する。
- **配色は明るめ**。青灰の塗りは濃い slate ではなく、ライトで軽い調子にする。
- **とにかくシンプルに**。要素を詰め込まない（散らばったカードを大量に描かない）。少数の要素＋たっぷりの余白。

### 挿絵（NotebookLM風への追加ルール）
- **正方形ではなく横長（16:9）を基本**にする。章の流れ図は横長が収まりが良い。
- **子供っぽくしない**（既出の強調）：マスコット・大きな目・笑顔キャラは避け、中立のピクトグラム＋矢印＋短い日本語ラベルの「図解」トーンにする。
- **時系列でない関係に ①②③＋左→右の段階矢印を使わない**。原因→結果、入力→処理→出力のような「因果・関係」は、番号なしの関係図（中央に処理、左に入力、右に出力）で描く。左→右の番号付きフローは「本当に時系列の手順」のときだけ使う。
