/**
 * UX DAYS TOKYO 用語サジェストBot - メインエントリポイント
 *
 * Slack Events API のメンションを受け、Claude Haiku を介してスタッフを支援する。
 * 担う機能：用語サジェスト／既存有無確認／URL照会／用語DB追加（既存WP照合つき）。
 *
 * 既存記事リストは WordPress REST API から都度取得し、10分間キャッシュする。
 *
 * 必要なスクリプトプロパティ（用語DBの「設定」タブに入れて saveBotSettings で保存）：
 *   - ANTHROPIC_API_KEY   : Anthropic APIキー
 *   - SLACK_BOT_TOKEN     : Slack Bot User OAuth Token（xoxb-で始まる）
 *   - WORDPRESS_BASE_URL  : UX DAYS TOKYO のWordPress URL（例: https://uxdaystokyo.com）
 */

const CLAUDE_MODEL = 'claude-haiku-4-5-20251001';
const WP_POST_TYPE = 'glossary';
const CACHE_KEY_EXISTING = 'existing_articles_v1';
const CACHE_SECONDS = 600;

// 用語DB（UX TIMES 用語DB）の固定ID。「◯◯ 追加して」でここへ addTerm 相当の追記を行う。
const GLOSSARY_SHEET_ID = '1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY';
const GLOSSARY_TAB = 'UX TIMES 用語DB';
const BOT_NAME = '用語くん';

// デプロイ時にコミットSHAへ置き換わる（GitHub Actionsの「ビルド識別子を埋め込む」ステップ）。
// 版の文字列（下の version 応答）を手で上げ忘れても、いま動いているコードがどれか分かるようにする。
const BUILD_REV = '__BUILD_REV__';
const REPORT_CHANNEL = 'C024GJ0H3LG'; // 週末レポートの投稿先チャンネル

// 用語DBの列番号（1始まり）。webhook（add_term / update_row）で使う。
// A:ID B:用語 C:英語名 D:補足・文脈 E:提案元 F:提案日 G:生成する H:ステータス I:記事Doc J:WP URL K:生成日 L:備考
// M:slug N:excerpt O:category_id P:featured_media Q:wp_post_id R:eyecatch_prompt
// S:生成バージョン T:レシピhash U:作り直し V:作り直しメモ
const COL = {
  ID: 1, TERM: 2, TERM_EN: 3, CONTEXT: 4, PROPOSER: 5, PROPOSED_AT: 6, FLAG: 7, STATUS: 8,
  DOC_URL: 9, WP_URL: 10, GENERATED_AT: 11, NOTE: 12,
  SLUG: 13, EXCERPT: 14, CATEGORY_ID: 15, FEATURED_MEDIA: 16, WP_POST_ID: 17,
  EYECATCH_PROMPT: 18,
  // レシピ版管理。S=どのレシピ版で作った記事か、T=そのときのハッシュ、U=作り直しリクエスト、V=依頼の経緯
  CREATOR_VERSION: 19, RECIPE_HASH: 20, REGEN: 21, REGEN_NOTE: 22,
};

// ============================================================
// Slack Events エントリポイント
// ============================================================

/**
 * Slack Events APIからのPOSTを受ける。
 */
function doPost(e) {
  const data = JSON.parse(e.postData.contents);

  // --- Slack: URL Verification ---
  if (data.type === 'url_verification') {
    return ContentService.createTextOutput(data.challenge);
  }

  // --- 内部API（Coworkバッチ）: action があれば webhook 扱い。WEBHOOK_SECRET で認証 ---
  if (data.action) {
    if (data.token !== getSecretToken_()) return jsonOut({ ok: false, error: 'invalid token' });
    if (data.action === 'add_term') return addTerm(data);
    if (data.action === 'update_row') return updateRow(data);
    if (data.action === 'notify') return notifyAction_(data);
    if (data.action === 'set_recipe_version') return setRecipeVersion_(data);
    return jsonOut({ ok: false, error: 'unknown action' });
  }

  // --- Slack: メンションイベント ---
  // Slackは3秒以内に応答が返らないと同じイベントを再送してくる。WP下書き作成のように
  // Doc取得→HTML変換→WP POST と十数秒かかる処理では毎回これに当たり、再送のぶんだけ
  // 記事が二重三重に作られる。event_id だけでなくメッセージ自体（channel:ts）でも弾く。
  const ev0 = data.event || {};
  const msgKey = (ev0.channel && ev0.ts) ? 'msg_' + ev0.channel + '_' + ev0.ts : '';
  if (data.event_id && isAlreadyProcessed(data.event_id)) {
    return ackOk();
  }
  if (msgKey && isAlreadyProcessed(msgKey)) {
    return ackOk();
  }
  if (data.event && data.event.type === 'app_mention' && !data.event.bot_id) {
    try {
      handleMention(data.event);
    } catch (err) {
      console.error('handleMention failed: ' + err);
      postToSlack(data.event.channel,
        'あれ？内部エラーが起きちゃった💦 GASのログを確認してほしい！',
        data.event.thread_ts || data.event.ts);
    }
  }

  return ackOk();
}

/**
 * メンションを処理する。ユーザーの意図を判定して各ハンドラへ振り分ける。
 */
function handleMention(event) {
  const userMessage = (event.text || '').replace(/<@[^>]+>/g, '').trim();

  // バージョン確認（どのコード／デプロイが応答しているか特定するデバッグ用）。完全一致のみ。
  if (/^(version|ping|バージョン|でばっぐ|デバッグ|debug)$/i.test(userMessage)) {
    postToSlack(event.channel,
      ':large_green_circle: 1q0O 用語くん v37（ルビの全角￥・WP更新先の作り直し）が応答してるよ ✨\n' + buildLabel_(),
      event.thread_ts || event.ts);
    return;
  }

  // WP下書き作成（「G-023 をWP下書きに」「人工的希少性をWP下書きに」「モーダルをWPに移行して」）。
  // 対象（G-ID／用語名）がメッセージ内で明確な明示コマンドなので、スレッド内でも実行できるよう
  // 会話分岐（handleThreadReply_）より前で拾う。生成リクエストと衝突しないよう表現を絞る。
  if (/WP\s*下書き|下書きに(移行|して|する|送|化)|下書き化|(WP|WordPress|ワードプレス)(に|へ)?\s*(下書き|移行|反映|投稿)/i.test(userMessage)) {
    handleWpDraftCommand(event, userMessage);
    return;
  }

  // アイキャッチプロンプト照会（用語DBのR列を逐語で返す）。対象が明確な明示コマンドなのでスレッド内でも動かす。
  if (/アイキャッチ|eyecatch/i.test(userMessage) && /プロンプト|prompt/i.test(userMessage)) {
    handleEyecatchPrompt_(event, userMessage);
    return;
  }

  // スレッド内リプライは履歴を読んで応答する
  if (event.thread_ts) {
    handleThreadReply_(event);
    return;
  }

  // ヘルプ依頼（「使い方」「ヘルプ」「何ができる」など）
  if (/(使い方|ヘルプ|何ができる|なに(が|を)できる|機能.{0,2}教え|help)/i.test(userMessage)) {
    handleHelp(event);
    return;
  }

  // 作り直しリクエスト（「◯◯ を最新版で作り直して」）。レシピ（記事の書き方）を直したあと、
  // 古い書き方のままの記事を最新レシピで書き直す。新規生成（下書きの無い用語）とは別物なので先に拾う。
  if (/(作り直|作りなお|つくり直|つくりなお|作り替|つくり替|書き直|書きなお|リライト|再生成)/.test(userMessage) ||
      (/最新版/.test(userMessage) && /(作|つく|直|更新|反映)/.test(userMessage))) {
    handleRegenRequest_(event, userMessage);
    return;
  }

  // 旧版レシピの記事一覧（「古い記事教えて」「旧版どれ？」「レシピのバージョン教えて」）
  if (/(古い|旧版|前の書き方|レシピ)/.test(userMessage) &&
      /(記事|下書き|ドラフト|一覧|どれ|教え|確認|バージョン|版)/.test(userMessage)) {
    handleStaleList_(event);
    return;
  }

  // 用語DB追加依頼（「◯◯ 追加して」「◯◯を登録」）。用語名の中の「追加」等では誤爆させない。
  if (isAddCommand(userMessage) && !/(教えて|提案|サジェスト|おすすめ)/.test(userMessage)) {
    handleAddToGlossary(event, userMessage);
    return;
  }

  // 生成リクエスト（「◯◯ の下書き作って」「G-023 生成して」）。下書きの無い用語を、月曜（毎週）／金曜
  // （リクエストがある時だけ）の生成バッチ対象にする。WP下書き化（上で処理済み）とは別物。
  if (!/WP下書き/i.test(userMessage) &&
      (/(下書き|ドラフト).{0,10}(作|つく|生成)/.test(userMessage) || /生成\s*して/.test(userMessage))) {
    handleGenerateRequest(event, userMessage);
    return;
  }

  // 通常処理（サジェスト・既存有無確認・URL照会）
  handleDefault(event, userMessage);
}

/**
 * いま動いているコードがどれかを示す1行。
 * 置き換え前の値と比べたいが、その文字列自体もデプロイ時の置換に巻き込まれるので、
 * 実行時に組み立てて sed の対象にならないようにしている。
 */
function buildLabel_() {
  const placeholder = '__BUILD' + '_REV__';
  return BUILD_REV === placeholder ? '（まだデプロイされていない手元のコードだよ）' : 'ビルド ' + BUILD_REV;
}

// ============================================================
// ハンドラ：ヘルプ
// ============================================================

function handleHelp(event) {
  const message =
    'はーい、用語くんだよ ✨ よく使うのはこのあたり！\n' +
    '\n' +
    '`@用語くん 用語教えて` → 書けそうな用語を3つ提案（軽め/中/重め）\n' +
    '`@用語くん ◯◯ある？` → 既存チェック＆URL照会\n' +
    '`@用語くん ◯◯ 追加して` → 候補リスト（用語DB）に積む\n' +
    '`@用語くん ◯◯ の下書き作って` → 下書きが無い用語を生成リクエスト（月／金に作ってここで知らせるよ）\n' +
    '`@用語くん 人工的希少性 をWP下書きに` → WordPressの下書きにする（用語名でもG-IDでもOK）\n' +
    '`@用語くん ◯◯ を最新版で作り直して` → 記事の書き方を直したあと、古い書き方の記事を書き直す\n' +
    '`@用語くん 古い記事教えて` → いまの書き方より前に作った記事を一覧する\n' +
    '\n' +
    '*【使い方の詳しい説明】* 追加→生成→レビュー→WP下書き→画像→公開の全部と、Claudeが無い人向けのやり方（生成リクエスト・R列のアイキャッチプロンプトで自作）は、READMEにまとめてあるよ 📘\n' +
    '・使い方ガイド（README上部）→ https://github.com/YuyaTakahashi/article-creator\n' +
    '・用語DB（閲覧）→ https://docs.google.com/spreadsheets/d/1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY/edit\n' +
    '・記事ドラフト（閲覧）→ https://drive.google.com/drive/folders/1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS\n' +
    '\n' +
    'なんでも聞いて！書きたい用語を見つけたら `追加して` で積んでおいてね 🌟';
  postToSlack(event.channel, message, event.ts);
}

// ============================================================
// ハンドラ：通常処理（サジェスト・確認・URL照会）
// ============================================================

function handleDefault(event, userMessage) {
  const articles = getExistingArticles();
  // 既存WP記事に加えて用語DB（作業状況）も渡し、ステータス・Doc有無・slug・候補一覧などDBの質問に答えられるようにする。
  const sys = buildDefaultSystemPrompt() +
    '\n\n【用語DBの参照】渡される「用語DB」は各用語の作業状況（提案中／レビュー待ち／下書き作成済み／公開済み／見送り）と、記事Docの有無・slug・定義（最小限の説明）。' +
    'ステータス照会・作業状況・候補一覧・Doc有無・slug・定義などDBに関する質問には、この用語DBを根拠に正確に答える。値が無いものは推測せず「まだ無い」と正直に言う。' +
    actionMarkerInstructions_();
  const usr = buildDefaultUserPrompt(userMessage, articles, getGlossaryDbSnapshot_());
  const response = applyActionMarkers_(event, callClaude(sys, usr));
  postToSlack(event.channel, response, event.thread_ts || event.ts);
}

/** 用語DBの作業状況を簡潔なスナップショットにする（LLMに渡す。長文のR列アイキャッチプロンプトは含めない）。 */
function getGlossaryDbSnapshot_() {
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const data = sheet.getRange(2, 1, last - 1, COL.EXCERPT).getValues(); // A..N
  return data.map(function (r) {
    const term = String(r[COL.TERM - 1] || '').trim();
    if (!term) return null;
    return {
      id: String(r[COL.ID - 1] || ''),
      term: term,
      term_en: String(r[COL.TERM_EN - 1] || '').trim(),
      status: String(r[COL.STATUS - 1] || '').trim(),
      hasDoc: String(r[COL.DOC_URL - 1] || '').trim() !== '',
      slug: String(r[COL.SLUG - 1] || '').trim(),
      excerpt: String(r[COL.EXCERPT - 1] || '').trim(),
    };
  }).filter(Boolean);
}

/** 「◯◯のアイキャッチプロンプト教えて」→ 用語DBのR列(アイキャッチプロンプト)を逐語で返す。 */
function handleEyecatchPrompt_(event, userMessage) {
  const sheet = getGlossarySheet_();
  const reply = event.thread_ts || event.ts;
  let row = -1;
  let specified = ''; // 指定された用語名／G-ID（見つからなかった時の明示メッセージ用）
  let candidates = [];
  const idMatch = userMessage.match(/G-?\s*(\d+)/i);
  if (idMatch) {
    specified = 'G-' + idMatch[1].padStart(3, '0');
    const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
    const idx = ids.indexOf(specified);
    if (idx !== -1) row = idx + 2;
  } else {
    // 「〜のアイキャッチ…」より前が用語名
    specified = userMessage
      .replace(/[「」『』]/g, ' ')
      .replace(/[\s　の]*(アイキャッチ|eyecatch)[\s\S]*$/i, '')
      .replace(/\s+/g, ' ').trim();
    if (specified) {
      const found = lookupTermRow_(sheet, specified);
      row = found.row;
      candidates = found.candidates;
    }
  }
  if (row === -1) {
    if (!specified) {
      // 用語が読み取れなかった → 聞き返す
      postToSlack(event.channel, 'どの用語のアイキャッチプロンプト？「@用語くん 人工的希少性のアイキャッチプロンプト教えて」みたいに用語名（かG-ID）を入れてね！', reply);
    } else if (candidates.length) {
      // 近い用語はある → 取り違えないように候補を出して聞き返す
      postToSlack(event.channel, termNotFoundMessage_(specified, candidates), reply);
    } else {
      // 用語は指定されたがDBに無い → 「無い」と明示する
      postToSlack(event.channel, '「*' + specified + '*」は用語DBに登録が無いから、アイキャッチプロンプトも記録されてないよ💦（この仕組みで生成した用語だけ記録してるんだ）', reply);
    }
    return;
  }
  const name = String(sheet.getRange(row, COL.TERM).getValue());
  const prompt = String(sheet.getRange(row, COL.EYECATCH_PROMPT).getValue() || '').trim();
  if (!prompt) {
    postToSlack(event.channel, '*' + name + '* のアイキャッチプロンプトはまだ記録されてないみたい💦（記事を生成するとR列に入るよ）', reply);
    return;
  }
  postToSlack(event.channel, '*' + name + '* のアイキャッチプロンプトだよ ✨\n```\n' + prompt + '\n```', reply);
}

// ============================================================
// 会話LLMからの実アクション実行（合図行 [[...]] を拾って実行する）
//   正規表現ルーティングを外れた言い回しでも、LLMが意図を汲んで合図を出せば実際に処理する。
// ============================================================

/** 会話LLMに渡す「合図でアクションを実行できる」ことの説明。default／thread 双方の system に足す。 */
function actionMarkerInstructions_() {
  return '\n\n【アクションの実行（重要）】返信の最後に「合図行」を出すと、コードが実際にその操作を実行する。' +
    'スタッフが操作を依頼したら必ず対応する合図を単独行で出す。あなたは実際に実行できるので、「手配します」「少々お待ちください」のような空約束や、「私はDBを参照できない」という断りは禁止：' +
    '\n- 用語をリスト（用語DB）に追加 → [[ADD: 正式な用語名]]' +
    '\n- WordPressの下書きに移行・作成 → [[WP_DRAFT: 用語名またはG-ID]]' +
    '\n- アイキャッチ（eyecatch）プロンプトを教えて → [[EYECATCH: 用語名またはG-ID]]' +
    '\n- 記事を最新の書き方（レシピ）で作り直す・書き直す → [[REGEN: 用語名またはG-ID]]' +
    '\n「↑」「これ」「この用語」などの指示語は、文脈から実際の用語名に解決して合図に書く。操作の依頼でなければ合図は出さず普通に会話する。合図行はコードが処理して結果に差し替えるので、合図に加えて自分でも同じ内容を書かない。';
}

/** 「G-023」や用語名を { row, candidates } に解決する。見つからなければ row: -1。 */
function resolveTermRow_(sheet, idOrTerm) {
  const s = String(idOrTerm).trim();
  const m = s.match(/G-?\s*(\d+)/i);
  if (m) {
    const gid = 'G-' + m[1].padStart(3, '0');
    const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
    const idx = ids.indexOf(gid);
    if (idx !== -1) return { row: idx + 2, candidates: [] };
  }
  const term = s.replace(/G-?\s*\d+/i, '').trim();
  return lookupTermRow_(sheet, term || s);
}

/** LLM返信に含まれる合図 [[ADD:]] [[WP_DRAFT:]] [[EYECATCH:]] を実行し、合図を結果テキストに差し替えて返す。 */
function applyActionMarkers_(event, reply) {
  let out = String(reply);
  const results = [];
  const sheet = getGlossarySheet_();

  const addM = out.match(/\[\[ADD:\s*(.+?)\]\]/);
  if (addM) {
    const term = addM[1].trim();
    try {
      const r = addToGlossaryIfNew(term, 'Slackから追加', '会話で追加依頼');
      results.push(r.status === 'exists'
        ? '（*' + (r.term || term) + '*（' + r.id + '）はもう候補リストに入ってたよ ✨）'
        : '（用語DBに *' + term + '*（' + r.id + '）を積んでおいたよ！🌟）');
    } catch (e) { results.push('（DB追加でエラーが出ちゃった💦: ' + e + '）'); }
  }

  const wpM = out.match(/\[\[WP_DRAFT:\s*(.+?)\]\]/);
  if (wpM) {
    const key = wpM[1].trim();
    const found = resolveTermRow_(sheet, key);
    const row = found.row;
    if (row === -1) {
      results.push('（WP下書き: ' + termNotFoundMessage_(key, found.candidates) + '）');
    } else {
      try {
        const res = publishRowToWpDraft_(sheet, row);
        results.push(':outbox_tray: WP下書きを作成したよ ✨ *' + res.term + '*\n' + res.link + '\nWP管理画面で確認・公開してね' +
          (res.note ? '\n（' + res.note + '）' : ''));
      } catch (e) { results.push('（WP下書き作成に失敗しちゃった💦 ' + e + '）'); }
    }
  }

  const ecM = out.match(/\[\[EYECATCH:\s*(.+?)\]\]/);
  if (ecM) {
    const key = ecM[1].trim();
    const found = resolveTermRow_(sheet, key);
    const row = found.row;
    if (row === -1) {
      results.push('（アイキャッチプロンプト: ' + termNotFoundMessage_(key, found.candidates) + '）');
    } else {
      const p = String(sheet.getRange(row, COL.EYECATCH_PROMPT).getValue() || '').trim();
      const nm = String(sheet.getRange(row, COL.TERM).getValue());
      results.push(p
        ? '*' + nm + '* のアイキャッチプロンプトだよ ✨\n```\n' + p + '\n```'
        : '*' + nm + '* のアイキャッチプロンプトはまだ記録されてないみたい💦（記事を生成するとR列に入るよ）');
    }
  }

  const regenM = out.match(/\[\[REGEN:\s*(.+?)\]\]/);
  if (regenM) {
    const key = regenM[1].trim();
    const found = resolveTermRow_(sheet, key);
    const row = found.row;
    if (row === -1) {
      results.push('（作り直し: ' + termNotFoundMessage_(key, found.candidates) + '）');
    } else {
      try {
        results.push(requestRegen_(sheet, row, event.user, false).message);
      } catch (e) { results.push('（作り直しリクエストでエラーが出ちゃった💦: ' + e + '）'); }
    }
  }

  out = out.replace(/\n*\[\[(ADD|WP_DRAFT|EYECATCH|REGEN):[^\]]*\]\]\s*/g, '').trim();
  if (results.length) out = (out ? out + '\n\n' : '') + results.join('\n\n');
  return out;
}

// ============================================================
// ハンドラ：スレッド内応答（会話履歴を踏まえて返す）
// ============================================================

function handleThreadReply_(event) {
  const token = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
  const url = 'https://slack.com/api/conversations.replies?channel=' +
    encodeURIComponent(event.channel) + '&ts=' + encodeURIComponent(event.thread_ts) + '&limit=30';
  const resp = UrlFetchApp.fetch(url, { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true });
  let j = {};
  try { j = JSON.parse(resp.getContentText()); } catch (e) { j = {}; }
  if (!j.ok || !j.messages || j.messages.length === 0) {
    // 履歴取得不可（channels:history / groups:history 権限不足など）→ 固定メッセージにフォールバック
    postToSlack(event.channel,
      'ごめん、スレッドの履歴が読めなかった💦 新規メッセージで `@用語くん ◯◯` と投げ直してくれると確実だよ！',
      event.thread_ts);
    return;
  }
  const history = j.messages.map(function (m) {
    const who = m.bot_id ? '用語くん' : 'スタッフ';
    return who + ': ' + String(m.text || '').replace(/<@[^>]+>/g, '').trim();
  }).filter(function (l) { return l.length > 6; }).join('\n');

  const articles = getExistingArticles();
  // スレッドでもDB参照＋実アクション（追加・WP下書き・アイキャッチ照会）を合図行経由で実行する。
  const sys = buildThreadSystemPrompt() +
    '\n\n【用語DBの参照】渡される「用語DB」は各用語の作業状況（提案中／レビュー待ち／下書き作成済み／公開済み／見送り）とDoc有無・slug・定義。' +
    'ステータス・作業状況・候補一覧・Doc有無・slug・定義などDBに関する質問にはこの用語DBを根拠に正確に答える。値が無いものは推測せず「まだ無い」と正直に言う。' +
    actionMarkerInstructions_();
  const reply = applyActionMarkers_(event, callClaude(sys, buildThreadUserPrompt(history, articles, getGlossaryDbSnapshot_())));
  postToSlack(event.channel, reply, event.thread_ts);
}

function buildThreadSystemPrompt() {
  const fromSheet = getPrompt('thread_system');
  if (fromSheet) return fromSheet;
  return '' +
    'あなたは「用語くん」。UX DAYS TOKYOのUX用語集キュレーター。いまSlackスレッド内で会話の続きが来ている。過去のやり取りを踏まえて、最後のスタッフの発言に応答する。\n' +
    '- 用語サジェスト・既存有無確認・URL照会・関連用語提案・軽い相談を続ける。文脈を維持し、前回の自分の発言と矛盾しない\n' +
    '- 前回の自分が誤っていたら「さっき間違えた、ごめん！」と素直に訂正する\n' +
    '【既存記事リスト】WordPress REST APIから取得した実在の全記事タイトル＋URL一覧。「無い」と自己否定しない\n' +
    '- リスト上に該当があれば必ずURLを併記。無ければ「現在のリストには見当たらないね」と正直に\n' +
    '- 表記揺れ・日英・略称・記号差は同一とみなす。記憶や推測で「ある/ない」を答えない\n' +
    '【URL出力】必ず `<URL|表示名>` のSlackリンク形式。裸のURL禁止、URL直後に句読点・日本語を続けない\n' +
    '【キャラクター】明るくポジティブ、Slackらしい口調、絵文字1〜3個。ただし厳格ルールを破ってまで褒めない';
}

function buildThreadUserPrompt(history, articles, dbRows) {
  const list = articles.length > 0
    ? articles.map(function (a) { return '- ' + a.title + (a.url ? ' — ' + a.url : ''); }).join('\n')
    : '(まだ取得できていない)';
  const db = (dbRows && dbRows.length)
    ? dbRows.map(function (r) {
      return '- ' + r.id + ' ' + r.term + (r.term_en ? '（' + r.term_en + '）' : '') +
        ' [' + (r.status || '?') + ']' + (r.hasDoc ? ' Doc有' : '') +
        (r.slug ? ' slug:' + r.slug : '') + (r.excerpt ? ' ・定義:' + r.excerpt : '');
    }).join('\n')
    : '(まだ取得できていない)';
  return '' +
    '【このスレッドのやり取り（古い順。最後がスタッフの最新発言）】\n' + history + '\n\n' +
    '【既存記事リスト（WordPress公開済み。タイトル — URL）】\n' + list + '\n\n' +
    '【用語DB（作業状況。ID 用語 [ステータス] Doc有無 slug ・定義）】\n' + db + '\n\n' +
    '最後のスタッフの発言に、スレッドの文脈を踏まえて応答してください。';
}

// ============================================================
// ハンドラ：用語DBへ追加（openlogiアカウント所有のため直接追記）＋既存WP照合
// ============================================================

function handleAddToGlossary(event, userMessage) {
  const term = extractAddTerm(userMessage);
  if (!term) {
    postToSlack(event.channel,
      'あれ、どの用語を追加する？「@用語くん ダークパターン 追加して」みたいに用語名を入れてみて！✨',
      event.ts);
    return;
  }

  // 用語DBに積む（重複はスキップ）
  const r = addToGlossaryIfNew(term, 'Slackメンションから追加', 'Slackで用語くんに追加依頼');

  // 既存WP記事との照合（Claudeで意味ベース。失敗しても追加結果は返す）
  let check = '';
  try {
    const articles = getExistingArticles();
    check = callClaude(buildAddCheckSystemPrompt(), buildAddCheckUserPrompt(term, articles));
  } catch (e) {
    console.warn('add check failed: ' + e);
  }

  const head = (r.status === 'exists')
    ? '「*' + (r.term || term) + '*」（' + r.id + '）はもう候補リストに入ってるよ ✨'
    : '用語DBに追加したよ ✨ *' + term + '*（' + r.id + '）。生成待ちに並べておいた！🌟';
  postToSlack(event.channel, check ? (head + '\n\n' + check) : head, event.ts);
}

/** 追加コマンドらしい形か判定する（用語名の中の「追加」等では誤爆させない）。 */
function isAddCommand(message) {
  return /(追加|登録)(して|しといて|しておいて|お願い|よろしく)/.test(message) || // 「追加して」等
    /[をに]\s*(追加|登録)\s*[！!。.]*$/.test(message) ||                          // 「〜を追加」で終わる
    /\s(追加|登録)\s*[！!。.]*$/.test(message);                                    // 「〜 追加」で終わる（前に空白）
}

/**
 * 「◯◯ 追加して／登録」から用語名を抜き出す。
 * 用語の途中の「追加」は残し、末尾の指示語だけを落とす。
 */
function extractAddTerm(message) {
  return String(message)
    .replace(/[「」『』]/g, ' ')
    .replace(/^\s*用語集?に\s*/, '')
    .replace(/[\s　、,]*[をに]?\s*(追加|登録)(して(おいて|下さい|ください)?|しといて|しておいて|お願いします?|よろしく)?[\s　！!。.]*$/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * 用語DBに1行追記する。同じ用語が既にあればスキップ（重複防止）。
 * IDは既存「G-数字」の最大+1（行削除があっても衝突しない）。M〜Q列は生成時に埋めるので空のまま。
 * 戻り値: { status: 'added', id } または { status: 'exists' }
 */
function addToGlossaryIfNew(term, context, note) {
  const ss = SpreadsheetApp.openById(GLOSSARY_SHEET_ID);
  const sheet = ss.getSheetByName(GLOSSARY_TAB) || ss.getSheets()[0];
  const last = sheet.getLastRow();
  const t = String(term).trim();
  let maxNum = 0;
  if (last >= 2) {
    const ids = sheet.getRange(2, COL.ID, last - 1, 1).getValues().flat();
    for (let i = 0; i < ids.length; i++) {
      const m = String(ids[i]).match(/^G-(\d+)$/);
      if (m) maxNum = Math.max(maxNum, parseInt(m[1], 10));
    }
    // 重複判定も照合と同じ物差しにする（全角半角・英語名違いで同じ用語を二重に積まない）
    const found = lookupTermRow_(sheet, t);
    if (found.row !== -1) {
      return {
        status: 'exists',
        id: String(sheet.getRange(found.row, COL.ID).getValue()).trim(),
        term: String(sheet.getRange(found.row, COL.TERM).getValue()).trim(),
        row: found.row,
      };
    }
  }
  const nextId = 'G-' + String(maxNum + 1).padStart(3, '0');
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  // A:ID B:用語 C:英語名 D:補足・文脈 E:提案元 F:提案日 G:生成する H:ステータス I:記事Doc J:WP URL K:生成日 L:備考
  sheet.appendRow([
    nextId, t, '', context || 'Slackから追加', 'Slack(用語くん)', today, false, '提案中', '', '', '', note || ''
  ]);
  return { status: 'added', id: nextId };
}

// ============================================================
// ハンドラ：生成リクエスト（「◯◯ の下書き作って」「G-023 生成して」）
//   下書きの無い用語を、月曜（毎週）／金曜（リクエストがある時だけ）の生成バッチ対象にする。
//   実体：用語DBに載せ（無ければ追加）、G列（生成する）=TRUE を立てる。バッチが拾って生成→告知する。
// ============================================================

function handleGenerateRequest(event, userMessage) {
  const sheet = getGlossarySheet_();
  const idMatch = userMessage.match(/G-?\s*(\d+)/i);

  let row = -1, gid = '', term = '', status = '';
  if (idMatch) {
    gid = 'G-' + idMatch[1].padStart(3, '0');
    const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
    const idx = ids.indexOf(gid);
    if (idx === -1) {
      postToSlack(event.channel, gid + ' が用語DBに見つからなかった…IDを確認してね', event.ts);
      return;
    }
    row = idx + 2;
    term = sheet.getRange(row, COL.TERM).getValue();
    status = String(sheet.getRange(row, COL.STATUS).getValue() || '').trim();
  } else {
    term = extractGenerateTerm(userMessage);
    if (!term) {
      postToSlack(event.channel, 'どの用語の下書きを作る？「@用語くん ダークパターン の下書き作って」みたいに用語名を入れてね！✨', event.ts);
      return;
    }
    // 表記ゆれ・英語名でも既存行に当てる（当たらないと同じ用語を二重に積んでしまう）
    const found = lookupTermRow_(sheet, term);
    if (found.row !== -1) {
      row = found.row;
      gid = String(sheet.getRange(row, COL.ID).getValue());
      term = String(sheet.getRange(row, COL.TERM).getValue());
      status = String(sheet.getRange(row, COL.STATUS).getValue() || '').trim();
    } else if (found.candidates.length) {
      // 近い用語がある → 二重登録を避けて聞き返す
      postToSlack(event.channel,
        termNotFoundMessage_(term, found.candidates) +
        '\n別の用語なら「@' + BOT_NAME + ' ' + term + ' 追加して」で新しく積むよ ✨',
        event.ts);
      return;
    }
    if (row === -1) {
      const r = addToGlossaryIfNew(term, 'Slackから生成リクエスト', 'Slackで下書き作成を依頼');
      gid = r.id;
      if (r.row) {
        row = r.row;
        term = r.term || term;
        status = String(sheet.getRange(row, COL.STATUS).getValue() || '').trim();
      } else {
        const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
        row = ids.indexOf(gid) + 2;
        status = '提案中';
      }
    }
  }

  // 既に下書きがある用語は対象外（下書きの無い用語向けの機能）
  if (status === '公開済み') {
    postToSlack(event.channel, '*' + term + '*（' + gid + '）はもう公開済みだよ 📚 生成リクエストは不要！', event.ts);
    return;
  }
  if (status === 'レビュー待ち' || status === '公開OK' || status === '下書き作成済み') {
    postToSlack(event.channel, '*' + term + '*（' + gid + '）はもう下書きができてるよ（' + status + '）。レビュー→WP下書き→公開に進めてね ✨', event.ts);
    return;
  }

  // 生成リクエストのフラグ（G列）を立てる。バッチが最優先で拾い、生成後に flag:false で消化する。
  sheet.getRange(row, COL.FLAG).setValue(true);
  if (status !== '提案中') sheet.getRange(row, COL.STATUS).setValue('提案中');

  postToSlack(event.channel,
    '了解！*' + term + '*（' + gid + '）を生成リクエストに入れたよ 📝\n' +
    '次の生成タイミング（毎週月曜の朝／金曜はリクエストがある時だけ）で下書きを作って、このチャンネルで知らせるね ✨',
    event.ts);
}

/** 「◯◯ の下書き作って／生成して」から用語名を抜き出す。末尾の依頼表現だけを落とす。 */
function extractGenerateTerm(message) {
  return String(message)
    .replace(/[「」『』]/g, ' ')
    .replace(/^\s*用語集?の?\s*/, '')
    .replace(/\s*[のを]?\s*(下書き|ドラフト|記事)?\s*(を)?\s*(作成|作って|つくって|生成)\s*(して(おいて|下さい|ください)?|しといて|しておいて|お願いします?|よろしく)?[\s　！!。.]*$/, '')
    .replace(/\s*(下書き|ドラフト)\s*(が)?\s*(ない|無い|欲しい|ほしい)[\s　！!。.]*$/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// ============================================================
// レシピ版管理と作り直しリクエスト
//   article-creator のプロンプト群（レシピ）は日々直すので、記事ごとに「どの版で作ったか」を
//   用語DBのS列に残す。Macの生成バッチが set_recipe_version で最新版を知らせてくるので、
//   ここではそれと突き合わせて「旧版の記事」を数え、作り直しリクエスト（U列）を積む。
// ============================================================

/** Macの生成バッチが知らせてくる現行レシピ版。未通知なら空文字。 */
function getRecipeVersion_() {
  const props = PropertiesService.getScriptProperties();
  return {
    version: String(props.getProperty('RECIPE_VERSION') || '').trim(),
    hash: String(props.getProperty('RECIPE_HASH') || '').trim(),
    updatedAt: String(props.getProperty('RECIPE_UPDATED_AT') || '').trim(),
  };
}

/** webhook: 生成バッチが走るたびに現行レシピ版を知らせてくる。版が変わったらチャンネルに一報を入れる。 */
function setRecipeVersion_(body) {
  if (!body.version) return jsonOut({ ok: false, error: 'version required' });
  const props = PropertiesService.getScriptProperties();
  const prev = String(props.getProperty('RECIPE_VERSION') || '').trim();
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  props.setProperty('RECIPE_VERSION', String(body.version));
  props.setProperty('RECIPE_HASH', String(body.hash || ''));
  props.setProperty('RECIPE_UPDATED_AT', today);

  const changed = prev !== '' && prev !== String(body.version);
  if (changed && body.announce) {
    let stale = { total: 0 };
    try { stale = countStale_(); } catch (e) {}
    const note = body.note ? '\n> ' + body.note : '';
    postToSlack(REPORT_CHANNEL,
      ':sparkles: 記事の書き方（レシピ）を *' + prev + ' → ' + body.version + '* に更新したよ！' + note +
      (stale.total > 0
        ? '\nこれで前の書き方のままの記事が *' + stale.total + '件* になったよ。作り直したいものがあれば「@' +
          BOT_NAME + ' ◯◯ を最新版で作り直して」って言ってね ✨'
        : '\n手持ちの記事はぜんぶ最新版だよ ✨'));
  }
  return jsonOut({ ok: true, version: String(body.version), previous: prev, changed: changed });
}

/** 用語DBのS〜V列に見出しが無ければ入れる。列を手で用意しなくても動くようにするための保険。 */
function ensureVersionColumns_(sheet) {
  const sh = sheet || getGlossarySheet_();
  const head = sh.getRange(1, COL.CREATOR_VERSION, 1, 4).getValues()[0];
  const want = ['生成バージョン', 'レシピhash', '作り直し', '作り直しメモ'];
  for (let i = 0; i < want.length; i++) {
    if (String(head[i] || '').trim() === '') sh.getRange(1, COL.CREATOR_VERSION + i).setValue(want[i]);
  }
  return sh;
}

/** 生成済みの記事のうち、現行レシピ版より前に作られたものを数える。 */
function countStale_() {
  const sheet = ensureVersionColumns_();
  const cur = getRecipeVersion_().version;
  const out = { total: 0, rows: [], current: cur };
  const last = sheet.getLastRow();
  if (last < 2) return out;
  const DONE = ['レビュー待ち', '公開OK', '下書き作成済み', '公開済み', '作り直し済み'];
  const data = sheet.getRange(2, 1, last - 1, COL.REGEN_NOTE).getValues();
  data.forEach(function (r) {
    const status = String(r[COL.STATUS - 1] || '').trim();
    if (DONE.indexOf(status) === -1) return;           // まだ作っていない用語は対象外
    const v = String(r[COL.CREATOR_VERSION - 1] || '').trim();
    if (cur && v === cur) return;                       // 最新版で作られている
    out.rows.push({
      id: String(r[COL.ID - 1] || ''),
      term: String(r[COL.TERM - 1] || ''),
      status: status,
      version: v || '版の記録なし',
      regen: r[COL.REGEN - 1] === true,
      docUrl: String(r[COL.DOC_URL - 1] || '').trim(),
    });
  });
  out.total = out.rows.length;
  return out;
}

/** 指定行に作り直しリクエスト（U列）を立てる。Slackコマンドと会話合図の両方から呼ぶ。 */
function requestRegen_(sheet, row, slackUserId, force) {
  ensureVersionColumns_(sheet);
  const term = String(sheet.getRange(row, COL.TERM).getValue());
  const gid = String(sheet.getRange(row, COL.ID).getValue());
  const status = String(sheet.getRange(row, COL.STATUS).getValue() || '').trim();
  const made = String(sheet.getRange(row, COL.CREATOR_VERSION).getValue() || '').trim();
  const cur = getRecipeVersion_().version;
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  const who = slackUserId ? '<@' + slackUserId + '>' : 'Slack';

  // まだ一度も作っていない用語は「作り直し」ではなく新規生成のリクエストにする
  if (status === '' || status === '提案中' || status === '見送り') {
    sheet.getRange(row, COL.FLAG).setValue(true);
    if (status !== '提案中') sheet.getRange(row, COL.STATUS).setValue('提案中');
    return { ok: true, message: '*' + term + '*（' + gid + '）はまだ下書きが無いから、作り直しじゃなくて新規生成のリクエストに入れたよ 📝\n次の生成タイミング（月曜の朝／金曜はリクエストがある時だけ）で最新レシピで作るね ✨' };
  }

  if (cur && made === cur && !force) {
    return { ok: false, message: '*' + term + '*（' + gid + '）はもう最新レシピ *' + cur + '* で作られてるよ ✨\nそれでも作り直すなら「@' + BOT_NAME + ' ' + term + ' を強制で作り直して」って言ってね！' };
  }

  sheet.getRange(row, COL.REGEN).setValue(true);
  sheet.getRange(row, COL.REGEN_NOTE).setValue(
    today + ' ' + who + ' 依頼 / ' + (made || '版の記録なし') + ' → ' + (cur || '最新'));

  const from = made || '版の記録なし';
  const to = cur || '最新レシピ';
  return {
    ok: true,
    message: '了解！*' + term + '*（' + gid + '）を作り直しリクエストに入れたよ 🔁\n' +
      '*' + from + '* → *' + to + '* で書き直して、新しいドキュメントを作って知らせるね（元のDocはそのまま残すよ）。\n' +
      '次の生成タイミング（月曜の朝／金曜はリクエストがある時だけ）で作るね ✨' +
      (status === '公開済み' ? '\n公開済みの記事だから、WordPressへの反映は中身を確認したあと「@' + BOT_NAME + ' ' + term + ' をWP下書きに」で進めてね。' : ''),
  };
}

/** Slackコマンド：「◯◯ を最新版で作り直して」 */
function handleRegenRequest_(event, userMessage) {
  const sheet = getGlossarySheet_();
  const reply = event.thread_ts || event.ts;
  const key = extractRegenTerm_(userMessage);
  if (!key) {
    postToSlack(event.channel, 'どれを作り直す？「@' + BOT_NAME + ' モーダル を最新版で作り直して」みたいに用語名（かG-ID）を入れてね！✨', reply);
    return;
  }
  const found = resolveTermRow_(sheet, key);
  const row = found.row;
  if (row === -1) {
    postToSlack(event.channel, termNotFoundMessage_(key, found.candidates), reply);
    return;
  }
  const force = /(強制|それでも|とにかく|もう一度|もういちど)/.test(userMessage);
  const res = requestRegen_(sheet, row, event.user, force);
  postToSlack(event.channel, res.message, reply);
}

/** 「◯◯ を最新版で作り直して」から用語名を抜き出す。 */
function extractRegenTerm_(message) {
  return String(message)
    .replace(/[「」『』]/g, ' ')
    .replace(/(最新|いま|今|新しい)の?\s*(レシピ|バージョン|版|書き方|プロンプト)\s*(で|に)?/g, ' ')
    .replace(/最新版\s*(で|に)?/g, ' ')
    .replace(/(強制|それでも|とにかく|もう一度|もういちど)\s*(で|に)?/g, ' ')
    .replace(/^\s*用語集?の?\s*/, '')
    .replace(/\s*[のをは]?\s*(記事|下書き|ドラフト)?\s*(を)?\s*(作り直|作りなお|つくり直|つくりなお|作り替|つくり替|書き直|書きなお|リライト|再生成)[^\s]*$/, '')
    .replace(/\s+/g, ' ')
    .replace(/\s*[をのはで]\s*$/, '')
    .trim();
}

/** Slackコマンド：「古い記事教えて」「旧版の記事どれ？」 */
function handleStaleList_(event) {
  const reply = event.thread_ts || event.ts;
  const st = countStale_();
  const cur = st.current || '（バッチからまだ知らされてない）';
  if (!st.current) {
    postToSlack(event.channel,
      'いまのレシピ版がまだ分からないんだ💦 Macの生成バッチが動くと教えてくれる仕組みだから、次のバッチのあとにもう一度聞いてみて！', reply);
    return;
  }
  if (st.total === 0) {
    postToSlack(event.channel, '手持ちの記事はぜんぶ最新レシピ *' + cur + '* で作られてるよ ✨ 作り直しが要るものは無し！', reply);
    return;
  }
  const lines = st.rows.slice(0, 12).map(function (r) {
    return '・*' + r.term + '*（' + r.id + '・' + r.status + '）… ' + r.version + (r.regen ? ' ← 作り直し予約済み' : '');
  }).join('\n');
  postToSlack(event.channel,
    'いまのレシピは *' + cur + '* だよ 📚\nそれより前の書き方のままの記事が *' + st.total + '件* あるね：\n' + lines +
    (st.total > 12 ? '\n（ほか ' + (st.total - 12) + '件）' : '') +
    '\n\n作り直したいものがあれば「@' + BOT_NAME + ' ' + st.rows[0].term + ' を最新版で作り直して」って言ってね ✨', reply);
}


// ============================================================
// Claude API 呼び出し（汎用ラッパー）
// ============================================================

/**
 * Anthropic Claude Haiku を呼ぶ汎用関数。
 * systemPrompt と userPrompt は呼び出し元で組み立てる。
 */
function callClaude(systemPrompt, userPrompt) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY が未設定');
  }

  const payload = {
    model: CLAUDE_MODEL,
    max_tokens: 1024,
    system: systemPrompt,
    messages: [
      { role: 'user', content: userPrompt }
    ]
  };

  const response = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const code = response.getResponseCode();
  const body = response.getContentText();
  if (code !== 200) {
    throw new Error('Claude API failed: ' + code + ' ' + body);
  }

  const json = JSON.parse(body);
  const text = json.content && json.content[0] && json.content[0].text;
  if (!text) {
    throw new Error('Claude API returned empty content: ' + body);
  }
  return text;
}

// ============================================================
// システムプロンプト構築
// ============================================================

/**
 * 通常処理（サジェスト・確認・URL照会）用のシステムプロンプト。
 */
function buildDefaultSystemPrompt() {
  const fromSheet = getPrompt('default_system');
  if (fromSheet) return fromSheet;
  return '' +
    'あなたはUX DAYS TOKYOというUX用語集サイトのキュレーター「用語くん」である。\n' +
    'スタッフチームを支援する役割を持つ。\n' +
    '\n' +
    '【担う役割】\n' +
    '1. 用語サジェスト：まだ書かれていないUX用語を3つ提案する（基本機能）\n' +
    '2. 既存用語の有無確認：「○○は書かれてる？」に対し、既存記事リストを意味ベースで照合して答える。存在する場合は必ずURLも併記する\n' +
    '3. URL照会：「○○のURL教えて」に対し、既存記事リストのURLを正確に返す\n' +
    '4. 関連用語の提案：特定用語の関連語や派生語を提案する\n' +
    '5. その他、用語集まわりの軽い相談に応じる\n' +
    '\n' +
    '【既存リスト照合の仕方（重要）】\n' +
    '- 完全一致を求めず、以下の揺らぎを考慮する：\n' +
    '  - 表記揺れ（例：「ヤーキーズ・ドットソン」「ヤーキズ＝ドッドソン」は同一）\n' +
    '  - 日本語名 ↔ 英語名（例：「ピークエンドの法則」と「Peak-End Rule」は同一）\n' +
    '  - 略称 ↔ 正式名（例：「XAI」と「Explainable AI」は同一）\n' +
    '  - 助詞・記号の有無\n' +
    '- 照合結果を以下の3パターンで返す。**リスト上に該当エントリ（完全一致／同一概念／近い概念）がある場合は必ずURLを併記する**：\n' +
    '  - 完全一致または同一概念：「あるよ！」と明言し、URLを必ず併記する\n' +
    '  - 完全一致はないが、近い／関連する概念がリストにある：「完全一致は見当たらないけど、近い概念で◯◯があるよ」と必ずURLを併記する。複数あれば列挙してよい\n' +
    '  - どちらもない：「現在のリストには見当たらないね。新規に書く価値あるかも！」（URLは出さない）\n' +
    '\n' +
    '【サジェスト時のルール】\n' +
    '- 既存記事リストの用語（揺らぎを含む同一概念）は新規サジェストの対象から外す\n' +
    '- 3用語の難易度・所要時間をあえてバラす：「軽め（30分〜1時間）」「中（1〜2時間）」「重め（2時間以上）」を意識して混ぜる\n' +
    '- 各用語に【軽め】【中】【重め】のラベルを必ず付ける\n' +
    '- ユーザーが難易度を指定した場合（例「軽めの用語教えて」）はそれに沿う\n' +
    '- 対象領域：心理学/認知バイアス、UIパターン、リサーチ手法、IA、アクセシビリティ、ライティング、インタラクション、デザインシステム、AI/LLM時代のUX（Prompt UX、ハルシネーション対応、Human-in-the-loop、XAI、AI Disclosure、Trust Calibration等）\n' +
    '\n' +
    '【絶対に守る厳格ルール】\n' +
    '- 既存記事リストはあなたが参照できる唯一の情報源。記憶や推測で「ある／ない」を答えてはならない\n' +
    '- URLはリスト上の文字列をそのまま使う。記憶や推測で生成しない\n' +
    '- 完全一致と「近い概念」を混同せず、別物を無理にこじつけない\n' +
    '- 自分が前の発話で誤ったら素直に「さっき間違えた、ごめん！」と訂正する\n' +
    '\n' +
    '【キャラクター】\n' +
    '- 明るく、ポジティブで、スタッフをよく褒める\n' +
    '- リクエストの視点や着眼点を一言肯定してから本題に入る\n' +
    '- 各用語の魅力を強めに伝える（「これは絶対書く価値ある」「読者が喜ぶ」など）\n' +
    '- 締めも前向きに一押しする\n' +
    '- 形式ばらず、Slackらしい親しみやすい口調\n' +
    '- 絵文字は1〜3個に抑える（✨🌟💡📚🎉など）\n' +
    '- ただし、厳格ルールを破ってまでポジティブに振る舞うのは絶対NG\n' +
    '\n' +
    '【出力ルール】\n' +
    '- リクエスト種別（サジェスト／確認／URL照会）をまず正しく見分けてから応答する\n' +
    '- サジェスト依頼の場合、英語名と日本語名を併記し、各用語に1〜2行で魅力を添え、3用語を *太字* で見出し化し、【軽め】【中】【重め】ラベルを必ず付ける\n' +
    '- 確認・照会依頼の場合は、リスト照合の結果を簡潔に答える（勝手にサジェストを始めない）\n' +
    '- 過剰なお世辞や定型挨拶の連発は避ける';
}

function buildDefaultUserPrompt(userMessage, articles, dbRows) {
  const list = articles.length > 0
    ? articles.map(function (a) { return '- ' + a.title + (a.url ? ' — ' + a.url : ''); }).join('\n')
    : '(まだ取得できていない)';

  const db = (dbRows && dbRows.length)
    ? dbRows.map(function (r) {
      return '- ' + r.id + ' ' + r.term + (r.term_en ? '（' + r.term_en + '）' : '') +
        ' [' + (r.status || '?') + ']' + (r.hasDoc ? ' Doc有' : '') +
        (r.slug ? ' slug:' + r.slug : '') + (r.excerpt ? ' ・定義:' + r.excerpt : '');
    }).join('\n')
    : '(まだ取得できていない)';

  return '' +
    '【既存記事リスト（WordPress公開済み。タイトル — URL）】\n' +
    list +
    '\n\n' +
    '【用語DB（作業状況。ID 用語 [ステータス] Doc有無 slug ・定義）】\n' +
    db +
    '\n\n' +
    '【スタッフからのリクエスト】\n' +
    (userMessage || '（指定なし。多様な領域から3つサジェストしてほしい）');
}

/**
 * 追加時の既存WP照合用システムプロンプト。用語DBに積んだ用語が既に書かれているかを短く伝える。
 */
function buildAddCheckSystemPrompt() {
  const fromSheet = getPrompt('add_check_system');
  if (fromSheet) return fromSheet;
  return '' +
    'あなたはUX DAYS TOKYOのキュレーター「用語くん」。スタッフがある用語を記事の候補リストに追加した。\n' +
    '既存記事リストと意味ベースで照合し、その用語が既に書かれているかを短く伝える。\n' +
    '\n' +
    '【返す3パターン】\n' +
    '1. 完全一致/同一概念がリストにある：「ただ、これはもう書かれてるよ 📚 *◯◯* → URL。新しい切り口なら別角度で攻めよう！」（URL必須）\n' +
    '2. 近い概念がリストにある：「近い概念で *◯◯* があるよ → URL。差別化できると良さそう！」（URL必須。複数あれば列挙可）\n' +
    '3. どちらも無い：「まだ無い用語だね、書く価値ありそう ✨」（URLなし）\n' +
    '\n' +
    '【厳格ルール】\n' +
    '- リスト上のタイトル/URLだけを根拠にする。記憶や推測で「ある/ない」を言わない\n' +
    '- URLはリスト上の文字列をそのまま使う\n' +
    '- 表記揺れ・日英・略称・記号の有無は同一とみなす。別物を無理にこじつけない\n' +
    '- 1〜3文で簡潔に。絵文字は1〜2個';
}

function buildAddCheckUserPrompt(term, articles) {
  const list = articles.length > 0
    ? articles.map(function (a) { return '- ' + a.title + (a.url ? ' — ' + a.url : ''); }).join('\n')
    : '(まだ取得できていない)';

  return '' +
    '【既存記事リスト（タイトル — URL）】\n' +
    list +
    '\n\n' +
    '【候補リストに追加された用語】\n' +
    term;
}

// ============================================================
// WordPress REST API（既存記事取得）
// ============================================================

function getExistingArticles() {
  const cache = CacheService.getScriptCache();
  const cached = cache.get(CACHE_KEY_EXISTING);
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch (e) {
      // キャッシュ破損時は再取得
    }
  }

  const baseUrl = PropertiesService.getScriptProperties().getProperty('WORDPRESS_BASE_URL');
  if (!baseUrl) {
    console.warn('WORDPRESS_BASE_URL が未設定。既存記事リストは空で返す。');
    return [];
  }

  const articles = fetchAllArticlesFromWordPress(baseUrl);

  try {
    cache.put(CACHE_KEY_EXISTING, JSON.stringify(articles), CACHE_SECONDS);
  } catch (e) {
    console.warn('cache put failed: ' + e);
  }

  return articles;
}

function fetchAllArticlesFromWordPress(baseUrl) {
  const all = [];
  const PER_PAGE = 100;
  const MAX_PAGES = 50;

  for (let page = 1; page <= MAX_PAGES; page++) {
    const url = baseUrl.replace(/\/$/, '') +
      '/wp-json/wp/v2/' + WP_POST_TYPE +
      '?per_page=' + PER_PAGE +
      '&page=' + page +
      '&_fields=id,title,link,author,date';

    const response = UrlFetchApp.fetch(url, {
      method: 'get',
      muteHttpExceptions: true
    });

    const code = response.getResponseCode();
    if (code === 400 || code === 404) break;
    if (code !== 200) {
      throw new Error('WordPress API failed: ' + code + ' ' + response.getContentText());
    }

    // 空ボディ・非JSON（範囲外ページや一時応答）で落ちないよう保護し、その場合は打ち切る
    const body = response.getContentText();
    if (!body) break;
    let items;
    try {
      items = JSON.parse(body);
    } catch (e) {
      break;
    }
    if (!Array.isArray(items) || items.length === 0) break;

    items.forEach(function (item) {
      all.push({
        id: item.id,
        title: decodeHtmlEntities(item.title && item.title.rendered),
        url: item.link,
        author: item.author,
        date: item.date
      });
    });

    if (items.length < PER_PAGE) break;
  }
  return all;
}

function decodeHtmlEntities(raw) {
  if (!raw) return '';
  return raw
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'")
    .replace(/&nbsp;/g, ' ');
}

// ============================================================
// Slack 投稿
// ============================================================

function postToSlack(channel, text, threadTs) {
  const token = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
  if (!token) {
    throw new Error('SLACK_BOT_TOKEN が未設定');
  }

  const payload = {
    channel: channel,
    text: text
  };
  if (threadTs) payload.thread_ts = threadTs;

  const response = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const json = JSON.parse(response.getContentText());
  if (!json.ok) {
    console.error('chat.postMessage failed: ' + response.getContentText());
  }
}

// ============================================================
// ユーティリティ
// ============================================================

function isAlreadyProcessed(eventId) {
  const cache = CacheService.getScriptCache();
  const key = 'event_' + eventId;
  if (cache.get(key)) return true;
  cache.put(key, '1', 600);
  return false;
}

function ackOk() {
  return ContentService.createTextOutput('OK');
}

// ============================================================
// 内部API（Coworkバッチ）: add_term / update_row と補助
// ============================================================

function getSecretToken_() {
  return PropertiesService.getScriptProperties().getProperty('WEBHOOK_SECRET') || '';
}

function getGlossarySheet_() {
  const ss = SpreadsheetApp.openById(GLOSSARY_SHEET_ID);
  return ss.getSheetByName(GLOSSARY_TAB) || ss.getSheets()[0];
}

/** 用語を1行追記する（IDは既存G番号の最大+1）。{term, term_en?, context?, proposer?, note?, silent?} */
function addTerm(body) {
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  let maxNum = 0;
  if (last >= 2) {
    const ids = sheet.getRange(2, 1, last - 1, 1).getValues();
    ids.forEach(function (r) {
      const m = String(r[0]).match(/^G-(\d+)$/);
      if (m) maxNum = Math.max(maxNum, parseInt(m[1], 10));
    });
  }
  const nextId = 'G-' + String(maxNum + 1).padStart(3, '0');
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  sheet.appendRow([
    nextId, body.term, body.term_en || '', body.context || '',
    body.proposer || BOT_NAME, today, false, '提案中', '', '', '', body.note || '',
  ]);
  if (!body.silent) {
    notifySlack(':bulb: ' + BOT_NAME + 'が用語を提案しました: *' + body.term + '*' +
      (body.context ? '\n> ' + body.context : ''));
  }
  return jsonOut({ ok: true, id: nextId });
}

/** パイプラインからの書き戻し。{id, status?, doc_url?, wp_url?, generated_at?, note?, slug?, excerpt?, category_id?, featured_media?, wp_post_id?} */
function updateRow(body) {
  const sheet = getGlossarySheet_();
  const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
  const idx = ids.indexOf(body.id);
  if (idx === -1) return jsonOut({ ok: false, error: 'id not found: ' + body.id });
  const row = idx + 2;

  const set = function (col, val) { if (val !== undefined && val !== null && val !== '') sheet.getRange(row, col).setValue(val); };
  // レシピ版まわりの値が来ているときは、S〜V列の見出しを先に用意しておく
  if (body.creator_version || body.recipe_hash || body.regen !== undefined || body.regen_note) ensureVersionColumns_(sheet);
  set(COL.STATUS, body.status);
  set(COL.DOC_URL, body.doc_url);
  set(COL.WP_URL, body.wp_url);
  set(COL.GENERATED_AT, body.generated_at);
  set(COL.NOTE, body.note);
  set(COL.SLUG, body.slug);
  set(COL.EXCERPT, body.excerpt);
  set(COL.CATEGORY_ID, body.category_id);
  set(COL.FEATURED_MEDIA, body.featured_media);
  set(COL.WP_POST_ID, body.wp_post_id);
  set(COL.EYECATCH_PROMPT, body.eyecatch_prompt);
  set(COL.CREATOR_VERSION, body.creator_version);
  set(COL.RECIPE_HASH, body.recipe_hash);
  set(COL.REGEN_NOTE, body.regen_note);
  // 作り直しリクエスト（U列）。バッチが作り直し完了時に regen:false を送って消化する。false も明示的に書く。
  if (body.regen !== undefined && body.regen !== null && body.regen !== '') {
    sheet.getRange(row, COL.REGEN).setValue(body.regen);
  }
  // 生成リクエストのフラグ（G列）。バッチが生成完了時に flag:false を送って消化する。false も明示的に書く。
  if (body.flag !== undefined && body.flag !== null && body.flag !== '') sheet.getRange(row, COL.FLAG).setValue(body.flag);

  if (body.status === 'レビュー待ち') {
    const term = sheet.getRange(row, COL.TERM).getValue();
    notifySlack(':memo: 記事ドラフトができました: *' + term + '*\nレビューをお願いします → ' + (body.doc_url || ''));
  }
  return jsonOut({ ok: true, row: row });
}

/** 任意のSlack Incoming Webhook（SLACK_WEBHOOK_URL プロパティ）へ通知。未設定ならスキップ。 */
function notifySlack(text) {
  const url = PropertiesService.getScriptProperties().getProperty('SLACK_WEBHOOK_URL');
  if (!url) return;
  UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ username: BOT_NAME, icon_emoji: ':books:', text: text }),
    muteHttpExceptions: true,
  });
}

/** 用語くん名義で任意チャンネルに投稿する（週次ダイジェスト用）。{channel, text, thread_ts?}
 *  Slack APIの結果（ok / error）をそのまま返すので、not_in_channel 等を呼び出し側で検出できる。 */
function notifyAction_(body) {
  if (!body.channel || !body.text) return jsonOut({ ok: false, error: 'channel and text required' });
  const token = PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
  if (!token) return jsonOut({ ok: false, error: 'SLACK_BOT_TOKEN not set' });
  const resp = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify({ channel: body.channel, text: body.text, thread_ts: body.thread_ts }),
    muteHttpExceptions: true,
  });
  const j = JSON.parse(resp.getContentText());
  return jsonOut({ ok: j.ok === true, error: j.error || '', ts: j.ts || '' });
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// ============================================================
// WP下書き作成（Slackコマンド: 「@用語くん G-023 をWP下書きに」）
//   対象行のDocを読み→HTML化→WP REST APIで下書き作成→J列に管理画面編集URLを記録
//   認証スコープ: documents（Doc読取）。WP認証は 設定タブ→saveBotSettings で WP_* を入れる
// ============================================================

/** Slackコマンドから G-ID を拾い、その行をWP下書きに送る。 */
function handleWpDraftCommand(event, userMessage) {
  const sheet = getGlossarySheet_();
  const reply = event.thread_ts || event.ts;

  // G-ID指定があればそれを優先。無ければ用語名で引く。
  let row = -1, label = '';
  const idMatch = userMessage.match(/G-?\s*(\d+)/i);
  if (idMatch) {
    label = 'G-' + idMatch[1].padStart(3, '0');
    const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
    const idx = ids.indexOf(label);
    if (idx === -1) {
      postToSlack(event.channel, label + ' が用語DBに見つからなかった…IDを確認してね', reply);
      return;
    }
    row = idx + 2;
  } else {
    const term = extractWpTerm_(userMessage);
    if (!term) {
      postToSlack(event.channel, 'どれをWP下書きにする？「@用語くん 人工的希少性 をWP下書きに」みたいに用語名（かG-ID）を入れてね！', reply);
      return;
    }
    const found = lookupTermRow_(sheet, term);
    row = found.row;
    if (row === -1) {
      postToSlack(event.channel, termNotFoundMessage_(term, found.candidates), reply);
      return;
    }
    label = String(sheet.getRange(row, COL.ID).getValue());
  }

  try {
    const res = publishRowToWpDraft_(sheet, row);
    postToSlack(event.channel,
      ':outbox_tray: WP下書きを作成したよ ✨ *' + res.term + '*（' + label + '）\n' + res.link + '\nWP管理画面で確認・公開してね' +
      (res.note ? '\n（' + res.note + '）' : ''),
      reply);
  } catch (e) {
    postToSlack(event.channel, 'WP下書き作成に失敗しちゃった💦 ' + e, reply);
  }
}

/** 「◯◯ をWP下書きに／WPに移行して」等から用語名を抜き出す（末尾の指示句を落とす）。 */
function extractWpTerm_(message) {
  return String(message)
    .replace(/[「」『』]/g, ' ')
    .replace(/[\s　、,]*[をに]?\s*(WP\s*)?下書き\s*(に|へ)?\s*(移行|作成|送信|送|化|する|し)?\s*(して(ください|ね)?|しといて|しておいて|お願いします?|よろしく)?[\s　！!。.]*$/i, '')
    .replace(/[\s　、,]*[をに]?\s*WP\s*(に|へ)?\s*(移行|反映|投稿)\s*(して(ください|ね)?|お願いします?|よろしく)?[\s　！!。.]*$/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// ============================================================
// 用語名から行を引く（表記ゆれ・英語名・見分けにくい字を吸収する）
//   B列（用語）の完全一致だけで引いていたころは、C列にしか無い英語名（「IaC」など）や
//   全角／半角・大文字小文字・括弧つき表記の違い、l と I のような見分けにくい字の打ち間違いで
//   「用語DBに見つからなかった」と返してしまっていた。段階的にゆるめて照合し、
//   それでも決まらないときは「もしかして」の候補を返す。
// ============================================================

/** 全角英数・全角記号・全角スペースを半角に落とす。 */
function toHalfWidth_(s) {
  return String(s)
    .replace(/[！-～]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0xFEE0); })
    .replace(/　/g, ' ');
}

/** 照合キー：全角→半角、小文字化、記号・空白を落とす（「モーダル（Modal）」→「モーダルmodal」）。 */
function termKey_(s) {
  return toHalfWidth_(s)
    .toLowerCase()
    .replace(/[^0-9a-zぁ-ゖァ-ヺー一-鿿]/g, '');
}

/** ゆるい照合キー：長音の有無、カタカナ／ひらがな、l・1 と i、0 と o の見分けにくさを吸収する。 */
function looseTermKey_(s) {
  return termKey_(s)
    .replace(/[ァ-ヶ]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0x60); })
    .replace(/ー/g, '')
    .replace(/[l1]/g, 'i')
    .replace(/0/g, 'o');
}

/** 1行分の照合対象を集める。用語名・英語名に加えて、括弧の内と外、英語名の併記も個別に引けるようにする。 */
function termAliases_(term, termEn) {
  const out = [];
  const push = function (raw, splitList) {
    const s = toHalfWidth_(String(raw || '')).trim();
    if (!s) return;
    out.push(s);
    out.push(s.replace(/\([^)]*\)/g, ' ').trim());               // 括弧の外（情報アーキテクチャ）
    (s.match(/\(([^)]*)\)/g) || []).forEach(function (x) {       // 括弧の中（IA）
      out.push(x.slice(1, -1).trim());
    });
    if (splitList) {                                             // 「IA / Information Architecture」
      s.split(/[\/,、・]/).forEach(function (x) { out.push(x.trim()); });
    }
  };
  push(term, false);
  push(termEn, true);
  return out.filter(Boolean);
}

/** 編集距離が1以下か（1文字の打ち間違い・入れ忘れを拾う）。 */
function isNearMiss_(a, b) {
  if (Math.abs(a.length - b.length) > 1) return false;
  if (a === b) return true;
  const short = a.length <= b.length ? a : b;
  const long = a.length <= b.length ? b : a;
  let i = 0, j = 0, diff = 0;
  while (i < short.length && j < long.length) {
    if (short.charAt(i) === long.charAt(j)) { i++; j++; continue; }
    if (++diff > 1) return false;
    if (short.length === long.length) { i++; j++; } else { j++; }
  }
  return diff + (long.length - j) + (short.length - i) <= 1;
}

/** 用語DBの全行を照合用の形（行番号・G-ID・用語名・別名）で読む。 */
function glossaryTermRows_(sheet) {
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const data = sheet.getRange(2, 1, last - 1, COL.TERM_EN).getValues(); // A:ID B:用語 C:英語名
  return data.map(function (r, i) {
    return {
      row: i + 2,
      id: String(r[COL.ID - 1] || '').trim(),
      term: String(r[COL.TERM - 1] || '').trim(),
      aliases: termAliases_(r[COL.TERM - 1], r[COL.TERM_EN - 1]),
    };
  }).filter(function (r) { return r.term !== ''; });
}

/**
 * 用語名から行を引く。{ row, candidates } を返す（見つからなければ row: -1）。
 * 完全一致 → 記号・全角半角・大小文字を無視した一致 → 長音や見分けにくい字も無視した一致、の順にゆるめる。
 * ゆるめた段で複数に当たったときは、取り違えを避けて確定せず候補として返す。
 */
function lookupTermRow_(sheet, term) {
  const q = String(term || '').trim();
  if (!q) return { row: -1, candidates: [] };
  const rows = glossaryTermRows_(sheet);
  if (!rows.length) return { row: -1, candidates: [] };

  const matchBy = function (keyFn) {
    const k = keyFn(q);
    if (!k) return [];
    return rows.filter(function (r) {
      return r.aliases.some(function (a) { return keyFn(a) === k; });
    });
  };

  // B列（用語）そのものの完全一致が最優先。別の行の別名とかぶっても取り違えない。
  const sameTerm = rows.filter(function (r) { return r.term === q; });
  if (sameTerm.length) return { row: sameTerm[0].row, candidates: [] };

  const exact = matchBy(function (s) { return String(s).trim(); });
  if (exact.length) return { row: exact[0].row, candidates: [] };

  let hits = matchBy(termKey_);
  if (!hits.length) hits = matchBy(looseTermKey_);
  if (hits.length === 1) return { row: hits[0].row, candidates: [] };
  if (hits.length > 1) return { row: -1, candidates: hits.slice(0, 5) };

  return { row: -1, candidates: nearTermRows_(rows, q) };
}

/** 「もしかして」用に、部分一致か1文字違いの行を集める（最大5件）。 */
function nearTermRows_(rows, term) {
  const k = looseTermKey_(term);
  if (k.length < 2) return [];
  return rows.filter(function (r) {
    return r.aliases.some(function (a) {
      const ak = looseTermKey_(a);
      if (ak.length < 2) return false;
      // 部分一致は3文字以上のときだけ見る（「IA」のような短い別名があちこちに引っかかるのを避ける）
      if (ak.length >= 3 && k.length >= 3 && (ak.indexOf(k) !== -1 || k.indexOf(ak) !== -1)) return true;
      return isNearMiss_(ak, k);
    });
  }).slice(0, 5);
}

/** 見つからなかったときの案内。近い候補があれば「もしかして」を添える。 */
function termNotFoundMessage_(term, candidates) {
  const head = '「*' + term + '*」が用語DBに見つからなかった💦';
  if (!candidates || !candidates.length) return head + ' 表記を確認するか、G-IDで指定してみて！';
  return head + ' もしかしてこれ？\n' +
    candidates.map(function (c) { return '・*' + c.term + '*（' + c.id + '）'; }).join('\n') +
    '\nこの中にあれば、G-IDで言い直してくれれば進めるよ ✨';
}

function wpConfig_() {
  const p = PropertiesService.getScriptProperties();
  const site = (p.getProperty('WP_SITE_URL') || '').replace(/\/+$/, '');
  const user = p.getProperty('WP_USER') || '';
  const pass = (p.getProperty('WP_APP_PASS') || '').replace(/\s/g, '');
  if (!site || !user || !pass) {
    throw new Error('WP認証が未設定です（設定タブに WP_SITE_URL / WP_USER / WP_APP_PASS を入れて saveBotSettings を実行）');
  }
  return {
    site: site, user: user, pass: pass,
    postType: p.getProperty('WP_POST_TYPE') || 'posts',
    categoryField: p.getProperty('WP_CATEGORY_FIELD') || 'glossary-category',
    auth: Utilities.base64Encode(user + ':' + pass),
  };
}

function publishRowToWpDraft_(sheet, row) {
  // 同じ行への同時実行を直列化する。再送で二重に走っても、待たされた側はロックの中で
  // wp_post_id を読み直すので、新規作成ではなく既存投稿の更新に回る。
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(60000)) {
    throw new Error('同じ記事の処理がまだ動いていました。少し待ってからもう一度お願いします');
  }
  try {
    return publishRowToWpDraftLocked_(sheet, row);
  } finally {
    lock.releaseLock();
  }
}

/** 実体。必ず publishRowToWpDraft_ 経由（ロック内）で呼ぶこと。 */
function publishRowToWpDraftLocked_(sheet, row) {
  // 先行した実行の書き込みを確実に読むため、保留中の更新を吐き出してから読む
  SpreadsheetApp.flush();
  const cfg = wpConfig_();
  const get = function (col) { return sheet.getRange(row, col).getValue(); };
  const term = get(COL.TERM);
  const docUrl = String(get(COL.DOC_URL) || '');
  const slug = String(get(COL.SLUG) || '');
  const excerpt = String(get(COL.EXCERPT) || '');
  const categoryId = get(COL.CATEGORY_ID);
  const featuredMedia = get(COL.FEATURED_MEDIA);
  const wpPostId = get(COL.WP_POST_ID);
  if (!docUrl) throw new Error('記事Doc(I列)が空です。先に記事を生成してください');

  const md = cleanReviewMd_(fetchDocMarkdown_(docUrl));
  const title = extractTitle_(md) || term;
  // 「-- wp分割ライン--」より後ろだけが本文。前段（フロントマター・最小限の説明・改ページ）は本文に入れない（post_to_wp.pyと同じ）
  const html = mdToHtml_(stripToBody_(stripTitle_(md)));

  const payload = { title: title, content: html };
  if (excerpt) payload.excerpt = excerpt;
  if (slug) payload.slug = slug;
  if (categoryId !== '' && categoryId != null) payload[cfg.categoryField] = [Number(categoryId)];
  if (featuredMedia !== '' && featuredMedia != null) payload.featured_media = Number(featuredMedia);

  // 更新先が本当にあるか先に見る。無いIDへそのままPOSTすると
  // 「WP応答 404: rest_post_invalid_id」で止まるだけで、どうすればいいか分からないため。
  let targetId = wpPostId;
  let note = '';
  if (targetId) {
    const found = inspectWpPost_(cfg, targetId);
    if (found.exists && found.status === 'trash') {
      payload.status = 'draft';                    // ゴミ箱にあった記事は下書きに戻して更新する
      note = '元の投稿（ID ' + targetId + '）がゴミ箱に入っていたから、下書きに戻して更新したよ';
    } else if (!found.exists && found.otherType) {
      // 別の投稿タイプで生きている → 作り直すと二重になるので、設定を直してもらう
      throw new Error('用語DBのwp_post_id（' + targetId + '）は投稿タイプ「' + cfg.postType +
        '」では見つからず、「' + found.otherType + '」として存在します。' +
        'WP_POST_TYPEの設定か、用語DBのQ列（wp_post_id）を確認してください');
    } else if (!found.exists) {
      // WPから消えている → 新規下書きとして作り直し、用語DBのIDを差し替える
      note = '用語DBにあった投稿ID ' + targetId + ' がWPに見つからなかったから、' +
        '新しい下書きを作って用語DBのIDを差し替えたよ';
      targetId = '';
    }
  }

  let endpoint = cfg.site + '/wp-json/wp/v2/' + cfg.postType;
  if (targetId) { endpoint += '/' + targetId; }   // 更新時はWP側の公開状態を保つ（statusを送らない）
  else { payload.status = 'draft'; }

  const resp = UrlFetchApp.fetch(endpoint, {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { Authorization: 'Basic ' + cfg.auth },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) throw new Error('WP応答 ' + code + ': ' + resp.getContentText().slice(0, 300));
  const j = JSON.parse(resp.getContentText());
  // 下書きは未公開で公開パーマリンクは開けないため、WP管理画面の編集URL（下書きを開いて公開する用）を記録する
  const editUrl = cfg.site + '/wp-admin/post.php?post=' + j.id + '&action=edit';

  sheet.getRange(row, COL.WP_URL).setValue(editUrl);
  sheet.getRange(row, COL.WP_POST_ID).setValue(j.id);
  // 既存投稿の更新（公開中の記事を最新レシピの本文に差し替えた場合）は公開状態を保つ。
  // 新規下書きのときだけ「下書き作成済み」にする。
  sheet.getRange(row, COL.STATUS).setValue(j.status === 'publish' ? '公開済み' : '下書き作成済み');
  // WP下書き化したDocのファイル名頭に「【WP移行済み】」を付け、他の人が間違って着手しないようにする。
  try { markDocMigrated_(docUrl); } catch (e) { console.warn('Docタイトル更新失敗（WP下書きは成功済み）: ' + e); }
  return { term: term, link: editUrl, id: j.id, note: note };
}

/**
 * 更新先のWP投稿の状態を見る。{ exists, status, otherType } を返す。
 * 404のときだけ「無い」と判断する（401/403などを無いと誤判定して新規作成すると、記事が二重になるため）。
 * 設定と違う投稿タイプで生きている場合は otherType にその名前を入れて、呼び出し側で作り直しを止める。
 */
function inspectWpPost_(cfg, postId) {
  const fetchOne = function (type) {
    const resp = UrlFetchApp.fetch(cfg.site + '/wp-json/wp/v2/' + type + '/' + postId + '?context=edit', {
      method: 'get',
      headers: { Authorization: 'Basic ' + cfg.auth },
      muteHttpExceptions: true,
    });
    return { code: resp.getResponseCode(), text: resp.getContentText() };
  };

  const mine = fetchOne(cfg.postType);
  if (mine.code >= 200 && mine.code < 300) {
    let status = '';
    try { status = String(JSON.parse(mine.text).status || ''); } catch (e) { /* 形が読めなくても存在はしている */ }
    return { exists: true, status: status, otherType: '' };
  }
  if (mine.code !== 404) {
    throw new Error('WPの投稿ID ' + postId + ' を確認できませんでした（WP応答 ' + mine.code + '）: ' +
      mine.text.slice(0, 200));
  }

  const others = ['posts', 'pages', 'glossary'].filter(function (t) { return t !== cfg.postType; });
  for (let i = 0; i < others.length; i++) {
    const r = fetchOne(others[i]);
    if (r.code >= 200 && r.code < 300) return { exists: false, status: '', otherType: others[i] };
  }
  return { exists: false, status: '', otherType: '' };
}

/** WP下書き化したDocのファイル名の頭に「【WP移行済み】」を付ける（重複着手の防止）。documentsスコープで動く。 */
function markDocMigrated_(docUrl) {
  const m = String(docUrl).match(/[-\w]{25,}/);
  if (!m) return;
  const PREFIX = '【WP移行済み】';
  const doc = DocumentApp.openById(m[0]);
  const name = doc.getName();
  if (name.indexOf(PREFIX) === 0) return; // 既に付いていれば何もしない
  doc.setName(PREFIX + name);
}

/** GoogleドキュメントをDocumentApp（内蔵）で読み、Markdown相当にする。documentsスコープだけで動く。 */
function fetchDocMarkdown_(docUrl) {
  const m = String(docUrl).match(/[-\w]{25,}/);
  if (!m) throw new Error('Doc URLからIDを取得できません: ' + docUrl);
  const body = DocumentApp.openById(m[0]).getBody();
  const out = [];
  const n = body.getNumChildren();
  for (let i = 0; i < n; i++) {
    const el = body.getChild(i);
    const t = el.getType();
    if (t === DocumentApp.ElementType.PARAGRAPH) {
      const p = el.asParagraph();
      const md = textElementToMd_(p.editAsText(), p.getText());
      const h = p.getHeading();
      let prefix = '';
      if (h === DocumentApp.ParagraphHeading.HEADING1) prefix = '# ';
      else if (h === DocumentApp.ParagraphHeading.HEADING2) prefix = '## ';
      else if (h === DocumentApp.ParagraphHeading.HEADING3) prefix = '### ';
      else if (h === DocumentApp.ParagraphHeading.HEADING4) prefix = '#### ';
      out.push(prefix + md);
    } else if (t === DocumentApp.ElementType.LIST_ITEM) {
      const li = el.asListItem();
      out.push('- ' + textElementToMd_(li.editAsText(), li.getText()));
    }
  }
  return out.join('\n\n');
}

function textElementToMd_(textEl, plain) {
  if (!plain) return '';
  let indices;
  try { indices = textEl.getTextAttributeIndices(); } catch (e) { return plain; }
  if (!indices || indices.length === 0) return plain;
  if (indices[0] !== 0) indices.unshift(0);
  let result = '';
  for (let k = 0; k < indices.length; k++) {
    const start = indices[k];
    const end = (k + 1 < indices.length) ? indices[k + 1] : plain.length;
    if (start >= end) continue;
    let seg = plain.substring(start, end);
    let url = null, bold = false;
    try { url = textEl.getLinkUrl(start); bold = textEl.isBold(start); } catch (e) { /* そのまま */ }
    if (bold) seg = '**' + seg + '**';
    if (url) seg = '[' + seg + '](' + url + ')';
    result += seg;
  }
  return result || plain;
}

function cleanReviewMd_(md) {
  return String(md).split('\n').filter(function (line) { return !/^\s*[*_]*（レビュー用ドラフト/.test(line); }).join('\n');
}

function extractTitle_(md) {
  const m = md.match(/^#\s+(.+?)\s*$/m);
  return m ? m[1].trim() : '';
}

function stripTitle_(md) {
  return md.replace(/^#\s+.+?\r?\n/, '');
}

/**
 * 「wp分割ライン」より後ろだけを本文にする（前段のフロントマター・最小限の説明・改ページを捨てる）。
 * excerptは用語DBのK列から別途送るため、本文に最小限の説明を残さない。
 * マーカーが無いDocのフォールバックとして「## 最小限の説明」節（次の見出しまで）も除去する。
 */
function stripToBody_(md) {
  let s = String(md).replace(/\r\n/g, '\n');
  // ダッシュはDoc変換で全角化されることがあるので、コア文字列だけで判定
  const m = s.match(/^.*wp\s*分割\s*ライン.*$/m);
  if (m) {
    return s.slice(s.indexOf(m[0]) + m[0].length).replace(/^\n+/, '');
  }
  // フォールバック: 「## 最小限の説明」見出し〜次の見出し直前までを削る
  return s.replace(/^#{1,4}\s*最小限の説明[\s\S]*?(?=^#{1,4}\s)/m, '');
}

/**
 * 最小限のMarkdown→HTML。ルビ(英字¥カナ¥)・wp分割ライン・見出し・箇条書き・引用・強調・リンク対応。
 * ルビの区切りは半角¥(U+00A5)と全角￥(U+FFE5)の両方を受ける。記事によってどちらで書かれるか揺れるため、
 * 半角だけを見ていたころは全角で書かれた回だけ変換されずに素通りしていた。
 */
function mdToHtml_(md) {
  const inline = function (s) {
    return s
      .replace(/([A-Za-z0-9.'’&-]+)[¥￥]([^¥￥]+)[¥￥]/g, '<ruby>$1<rt>$2</rt></ruby>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  };
  const lines = String(md).replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let para = [];
  let inList = false;
  const flushPara = function () { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
  const flushList = function () { if (inList) { out.push('</ul>'); inList = false; } };
  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx].replace(/\s+$/, '');
    if (/wp分割ライン/.test(line)) { flushPara(); flushList(); out.push('<!--nextpage-->'); continue; }
    if (line.trim() === '') { flushPara(); flushList(); continue; }
    if (/^\s*</.test(line)) { flushPara(); flushList(); out.push(line); continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      flushPara(); flushList();
      const lv = Math.max(2, m[1].length);
      out.push('<h' + lv + '>' + inline(m[2]) + '</h' + lv + '>');
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      flushPara();
      if (!inList) { out.push('<ul>'); inList = true; }
      out.push('<li>' + inline(m[1]) + '</li>');
    } else if ((m = line.match(/^\s*>\s?(.*)$/))) {
      flushPara(); flushList();
      out.push('<blockquote>' + inline(m[1]) + '</blockquote>');
    } else {
      flushList();
      para.push(line.trim());
    }
  }
  flushPara(); flushList();
  return out.join('\n');
}

// ============================================================
// 月曜レポート（今週の用語レポート）: 公開祝い＋みんなの状況＋未公開ドラフト数＋今週できた3本Doc
//   月曜バッチ(Mac)の生成後（月曜11時トリガー）に投稿する。おすすめ用語は廃止。
// ============================================================

/** 用語DBの「prompts」タブから key の本文を返す。未設定（プレースホルダ）なら ''。 */
function getPrompt(key) {
  try {
    const sheet = SpreadsheetApp.openById(GLOSSARY_SHEET_ID).getSheetByName('prompts');
    if (!sheet || sheet.getLastRow() < 2) return '';
    const rows = sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getValues();
    for (let i = 0; i < rows.length; i++) {
      if (String(rows[i][0]).trim() === key) {
        const c = String(rows[i][1] || '').trim();
        return (c && c.charAt(0) !== '（') ? c : '';
      }
    }
  } catch (e) { /* フォールバックへ */ }
  return '';
}

/** 用語DBの「staff_list」タブを読む（slack_user_id / wordpress_author_id / display_name）。 */
function getStaffList() {
  try {
    const sheet = SpreadsheetApp.openById(GLOSSARY_SHEET_ID).getSheetByName('staff_list');
    if (!sheet || sheet.getLastRow() < 2) return [];
    const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 3).getValues();
    return values.map(function (r) {
      return {
        slack_user_id: String(r[0] || '').trim(),
        wordpress_author_id: r[1] !== '' && r[1] != null ? Number(r[1]) : null,
        display_name: String(r[2] || '').trim(),
      };
    }).filter(function (s) { return s.slack_user_id.length > 0; });
  } catch (e) { return []; }
}

/** 用語DBのステータス集計＋今週生成したドラフト（レビュー待ち＋generated_at直近7日＋doc_url）を返す。 */
function getGlossarySummary_() {
  const out = { reviewWaiting: 0, publishOk: 0, proposed: 0, published: 0, thisWeek: [], draftCreated: [] };
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  if (last < 2) return out;
  const data = sheet.getRange(2, 1, last - 1, COL.GENERATED_AT).getValues(); // A..K
  const weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 7);
  data.forEach(function (r) {
    const status = String(r[COL.STATUS - 1] || '').trim();
    if (status === 'レビュー待ち') out.reviewWaiting++;
    else if (status === '公開OK') out.publishOk++;
    else if (status === '提案中') out.proposed++;
    else if (status === '公開済み') out.published++;
    // WPに下書きのまま残っているもの（公開待ち）はリマインド対象として集める
    if (status === '下書き作成済み') {
      out.draftCreated.push({ term: String(r[COL.TERM - 1] || ''), wpUrl: String(r[COL.WP_URL - 1] || '').trim() });
    }
    const gen = String(r[COL.GENERATED_AT - 1] || '').trim();
    const doc = String(r[COL.DOC_URL - 1] || '').trim();
    if ((status === 'レビュー待ち' || status === '作り直し済み') && doc && gen) {
      const d = new Date(gen);
      if (!isNaN(d.getTime()) && d >= weekAgo) {
        out.thisWeek.push({ term: String(r[COL.TERM - 1] || ''), docUrl: doc });
      }
    }
  });
  return out;
}

/**
 * レビュー待ち／公開OK の用語のうち、既にWPで公開済みのものを Claude で照合し、
 * 該当行のステータスを「公開済み」に自動更新する（表記揺れ・日英・略称を吸収）。
 */
function reconcilePublishedStatus_(articles) {
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  if (last < 2 || !articles || articles.length === 0) return;
  const data = sheet.getRange(2, 1, last - 1, COL.STATUS).getValues();
  const candidates = [];
  data.forEach(function (r, i) {
    const status = String(r[COL.STATUS - 1] || '').trim();
    // あいまい照合は「公開OK」だけ対象。レビュー待ち＝レビュー中で未公開が前提（共通語の類似記事に誤マッチして
    // 勝手に消える害が大きい）、下書き作成済み＝reconcileDraftByWp_ がwp_post_idで正確に判定するので、ここでは扱わない。
    if (status === '公開OK') {
      candidates.push({ row: i + 2, term: String(r[COL.TERM - 1] || '').trim() });
    }
  });
  if (candidates.length === 0) return;

  const sys = 'あなたはUX用語集の照合担当。渡された「候補用語」のうち、「既存記事タイトル」に同一概念（表記揺れ・日本語↔英語・略称↔正式名・記号や助詞の差を許容）で既に存在するものだけを選ぶ。' +
    '出力は候補用語の文字列だけを要素にした JSON配列のみ。該当なしは []。前置き・説明・コードフェンスは一切書かない。推測でこじつけない。';
  const usr = '【候補用語】\n' + candidates.map(function (c) { return '- ' + c.term; }).join('\n') +
    '\n\n【既存記事タイトル】\n' + articles.map(function (a) { return '- ' + a.title; }).join('\n');

  let matched = [];
  try {
    const resp = callClaude(sys, usr);
    const m = resp.match(/\[[\s\S]*\]/);
    if (m) matched = JSON.parse(m[0]);
  } catch (e) {
    return; // 照合失敗時は何もしない（誤更新を避ける）
  }
  if (!Array.isArray(matched) || matched.length === 0) return;

  const matchedSet = {};
  matched.forEach(function (t) { matchedSet[String(t).trim()] = true; });
  candidates.forEach(function (c) {
    if (matchedSet[c.term]) sheet.getRange(c.row, COL.STATUS).setValue('公開済み');
  });
}

/**
 * 「下書き作成済み」の各行を wp_post_id でWP実体照合し、DBを実態に合わせる。
 *  - WPが publish  → 公開済み
 *  - WPが draft等  → そのまま（本当に下書き）
 *  - WPに無い(404) → Docがあればレビュー待ち／無ければ提案中に戻し、壊れたWP参照(J/Q)を消す
 *  WP認証(スクリプトプロパティ)が無い・通信失敗・その他コードのときは誤判定を避けて触らない。
 */
function reconcileDraftByWp_() {
  let cfg;
  try { cfg = wpConfig_(); } catch (e) { return; }
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  if (last < 2) return;
  const data = sheet.getRange(2, 1, last - 1, COL.WP_POST_ID).getValues();
  data.forEach(function (r, i) {
    const row = i + 2;
    if (String(r[COL.STATUS - 1] || '').trim() !== '下書き作成済み') return;
    const postId = String(r[COL.WP_POST_ID - 1] || '').trim();
    if (!postId) return; // IDが無ければ判断不能。触らない
    const hasDoc = String(r[COL.DOC_URL - 1] || '').trim() !== '';
    const url = cfg.site + '/wp-json/wp/v2/' + cfg.postType + '/' + postId + '?context=edit';
    let resp;
    try {
      resp = UrlFetchApp.fetch(url, { headers: { Authorization: 'Basic ' + cfg.auth }, muteHttpExceptions: true });
    } catch (e) { return; }
    const code = resp.getResponseCode();
    if (code === 200) {
      let st = '';
      try { st = String(JSON.parse(resp.getContentText()).status || ''); } catch (e) {}
      if (st === 'publish') sheet.getRange(row, COL.STATUS).setValue('公開済み');
      // draft/pending/future はそのまま（本当に下書き）
    } else if (code === 404) {
      sheet.getRange(row, COL.STATUS).setValue(hasDoc ? 'レビュー待ち' : '提案中');
      sheet.getRange(row, COL.WP_URL).setValue('');
      sheet.getRange(row, COL.WP_POST_ID).setValue('');
    }
    // 401/403/5xx 等は誤判定回避のため何もしない
  });
}

function filterRecentArticles(articles, days) {
  const threshold = new Date();
  threshold.setDate(threshold.getDate() - days);
  return articles.filter(function (a) { return a.date && new Date(a.date) >= threshold; });
}

function getLastPublishDate(articles, authorId) {
  if (!authorId) return null;
  let latest = null;
  articles.forEach(function (a) {
    if (a.author === authorId && a.date) {
      const d = new Date(a.date);
      if (!latest || d > latest) latest = d;
    }
  });
  return latest;
}

function daysSince(date) {
  return Math.floor((new Date().getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
}

/** 今週の用語レポートをチャンネルに投稿する（月曜トリガーから呼ぶ）。 */
function sendMondayReport() {
  const staff = getStaffList();
  const articles = getExistingArticles();
  reconcilePublishedStatus_(articles); // 既にWP公開済みの用語のステータスを自動で「公開済み」に直す
  try { reconcileDraftByWp_(); } catch (e) {} // 下書き作成済みをwp_post_idでWP実体照合（公開済み/消えた下書きを整合）
  const recent = filterRecentArticles(articles, 7);
  const staffStatus = staff.map(function (p) {
    const lastDate = getLastPublishDate(articles, p.wordpress_author_id);
    return {
      slack_mention: '<@' + p.slack_user_id + '>',
      wordpress_author_id: p.wordpress_author_id,
      days_since_last_publish: lastDate ? daysSince(lastDate) : null,
    };
  });
  const summary = getGlossarySummary_();
  try { summary.stale = countStale_(); } catch (e) { summary.stale = { total: 0, rows: [], current: '' }; }
  const report = callClaude(buildMondayReportSystemPrompt(), buildMondayReportUserPrompt(recent, staffStatus, summary, articles));
  postToSlack(REPORT_CHANNEL, report);
}

function buildMondayReportSystemPrompt() {
  const fromSheet = getPrompt('monday_report_system');
  if (fromSheet) return fromSheet;
  return '' +
    'あなたは「用語くん」。月曜朝、UX DAYS TOKYOの用語チームチャンネルに週次活動レポートを投稿する。\n' +
    '【最重要：心理設計】チャンネル全員に見える。「個人名×ネガティブ評価」は絶対NG。経過日数は事実として出してよいが表現は徹底的にポジティブに。責めた・晒したと感じる文面は厳禁。\n' +
    '【使わない言葉】「◯日も経過」「まだ書いていません」「未着手」「滞っています」「遅れています」「頑張りましょう」「努力が必要」\n' +
    '【使う言葉】「合間で」「ふと書きたくなったら」「無理せず」「待ってるよ」「歓迎」「素敵」「おめでとう」\n' +
    '【出力の構成】\n' +
    '1. ヘッダー「今週の用語レポート ✨」\n' +
    '2. 【今週新しく公開された用語】公開ごとに「🎉 <@Uxxx> が『XXX』をMM/DDに公開！おめでとう！ → <公開URL|記事を読む>」。公開URLは渡された「今週公開された記事」の公開URLをそのまま使い、勝手に組み立てない。URLが「未取得」の記事はリンク部分ごと省く。0件なら「今週は公開0件だけど来週が楽しみ ✨」\n' +
    '3. 【みんなの状況】各スタッフを一行ずつ「📝 <@Uxxx>（前回公開からN日）：[文面]」。0〜7日「先週の用語、素敵だったね ✨」／8〜21日「読書で気になった用語あったかな？」／22〜45日「みんなで応援したいね 🌟」／46日以上「ふと書きたくなったら、いつでも歓迎！」／実績なし「これから一緒に育てていこう ✨」\n' +
    '4. 【未公開ドラフト】「作成済みだけどまだ公開されてない記事が N件あるよ」と件数を伝える。Nが0なら省略\n' +
    '5. 【WPに下書きのまま眠ってる記事（公開待ち）】渡された「WP下書き一覧」を各行「・XXX → <wpUrl|WPで公開>」で列挙し「あとは公開ボタンを押すだけ！合間にぜひ ✨」と促す。0件ならこの節は省略\n' +
    '6. 【今週できたドラフト】今週生成したドラフトを列挙。各行「・XXX → <DocURL|レビューする>」。0件なら「今週の新規ドラフトはお休み。来週をお楽しみに ✨」\n' +
    '7. 【書き方が新しくなった記事】渡された「旧版レシピの記事」が1件以上のときだけ、「いまの書き方（vX）より前に作った記事が N件あるよ。作り直したいものがあれば『@用語くん ◯◯ を最新版で作り直して』って言ってね」と1〜2行で伝える。0件ならこの節は省略。急かす表現は使わない\n' +
    '8. 締めの一言（「今週も素敵な一週間を ✨」）\n' +
    '【守るルール】\n' +
    '- 個人を呼ぶときは必ず slack_mention（<@U...> 形式）をそのまま出力。display_name は使わない\n' +
    '- URLは必ず <URL|表示名> のSlackリンク形式。裸のURL禁止、URL直後に句読点・日本語を続けない（改行する）\n' +
    '- おすすめ用語のサジェストはしない（実際に生成したドラフトを載せる方針）';
}

function buildMondayReportUserPrompt(recent, staffStatus, summary, allArticles) {
  const recentLines = recent.length > 0
    ? recent.map(function (a) {
        const author = staffStatus.find(function (s) { return s.wordpress_author_id === a.author; });
        const mention = author ? author.slack_mention : ('（著者ID' + a.author + '）');
        const dateLabel = a.date ? a.date.substring(5, 10).replace('-', '/') : '?';
        const url = String(a.url || '').trim();
        return '- ' + mention + ' が「' + a.title + '」を ' + dateLabel + ' に公開' +
          '（公開URL: ' + (url || '未取得') + '）';
      }).join('\n')
    : '(今週公開された用語は0件)';
  const statusLines = staffStatus.map(function (s) {
    const days = s.days_since_last_publish === null ? 'まだなし' : s.days_since_last_publish + '日';
    return '- ' + s.slack_mention + '（前回公開から ' + days + '）';
  }).join('\n');
  const unpublished = summary.reviewWaiting + summary.publishOk + summary.draftCreated.length;
  const draftLines = summary.thisWeek.length > 0
    ? summary.thisWeek.map(function (d) { return '- ' + d.term + ' → ' + d.docUrl; }).join('\n')
    : '(今週生成したドラフトは0件)';
  const stale = summary.stale || { total: 0, rows: [], current: '' };
  const staleLine = (stale.current && stale.total > 0)
    ? '現行レシピ ' + stale.current + ' より前に作られた記事が ' + stale.total + '件（' +
      stale.rows.slice(0, 5).map(function (r) { return r.term + '：' + r.version; }).join('、') +
      (stale.total > 5 ? ' ほか' : '') + '）'
    : '(旧版レシピの記事は0件)';
  const wpDraftLines = summary.draftCreated.length > 0
    ? summary.draftCreated.map(function (d) { return '- ' + d.term + (d.wpUrl ? ' → ' + d.wpUrl : '（WP URL未記録）'); }).join('\n')
    : '(WPに下書きのまま残っている記事は0件)';

  return '' +
    '【今週公開された記事（著者 → 用語 → 公開日 → WPの公開ページURL）】\n' + recentLines + '\n\n' +
    '【スタッフ各員の状況（slack_mention と 前回公開からの経過日数）】\n' + statusLines + '\n\n' +
    '【未公開ドラフト数】未公開合計 ' + unpublished + '件（レビュー待ち ' + summary.reviewWaiting + '件／公開OK ' + summary.publishOk + '件／WP下書きのまま ' + summary.draftCreated.length + '件）\n\n' +
    '【WP下書き一覧（WPに下書きのまま眠ってる記事。用語 → WP管理画面URL）】\n' + wpDraftLines + '\n\n' +
    '【今週できたドラフト（用語 → DocのURL）】\n' + draftLines + '\n\n' +
    '【旧版レシピの記事（いまの書き方より前に作られた記事）】\n' + staleLine + '\n\n' +
    '【既存記事リスト全件（重複排除の参考、提案はしない）】\n' +
    (allArticles.length > 0 ? allArticles.slice(0, 400).map(function (a) { return '- ' + a.title; }).join('\n') : '(まだ取得できていない)');
}

/** 月曜レポートの時間主導トリガーを作る。1q0Oエディタで一度 ▶ 実行（毎週月曜11時＝生成バッチの後）。 */
function setupMondayReportTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendMondayReport') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendMondayReport')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(11)
    .inTimezone('Asia/Tokyo')
    .create();
  console.log('月曜レポートのトリガーを作成しました（毎週月曜11時）');
}

// ============================================================
// 金曜DM（週末のお供）: 用語DBの提案中から各人にDMでおすすめ（A方式）
// ============================================================

/** 用語DBの「提案中」を、Slack追加分優先 → 登場回数の多い順で返す。 */
function getProposedTerms_() {
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const data = sheet.getRange(2, 1, last - 1, COL.NOTE).getValues(); // A..L
  const items = [];
  data.forEach(function (r) {
    if (String(r[COL.STATUS - 1] || '').trim() !== '提案中') return;
    const note = String(r[COL.NOTE - 1] || '');
    const mc = note.match(/公開記事(\d+)本/);
    items.push({
      term: String(r[COL.TERM - 1] || ''),
      term_en: String(r[COL.TERM_EN - 1] || ''),
      fromSlack: /Slack/.test(String(r[COL.PROPOSER - 1] || '')),
      count: mc ? parseInt(mc[1], 10) : 0,
    });
  });
  items.sort(function (a, b) {
    if (a.fromSlack !== b.fromSlack) return a.fromSlack ? -1 : 1;
    return b.count - a.count;
  });
  return items;
}

/** レビュー待ち（Docレビュー）と下書き作成済み（WP公開待ち）のドラフトを集める。 */
function getReviewableDrafts_() {
  const sheet = getGlossarySheet_();
  const last = sheet.getLastRow();
  const out = { review: [], draft: [] };
  if (last < 2) return out;
  const data = sheet.getRange(2, 1, last - 1, COL.WP_URL).getValues(); // A..J
  data.forEach(function (r) {
    const status = String(r[COL.STATUS - 1] || '').trim();
    const term = String(r[COL.TERM - 1] || '');
    if (!term) return;
    if (status === 'レビュー待ち') {
      out.review.push({ term: term, url: String(r[COL.DOC_URL - 1] || '') });
    } else if (status === '下書き作成済み') {
      out.draft.push({ term: term, url: String(r[COL.WP_URL - 1] || '') });
    }
  });
  return out;
}

/** 金曜17時: レビュー待ち・公開待ちのドラフトをチームのチャンネルにリンク付きで告知する（週末のお供）。
 *  実データ（用語DBのステータス）だけから組むのでLLMは使わない。ドラフトが1件も無ければ投稿しない（ノイズを出さない）。 */
/** 金曜ダイジェストの本文を組む。レビュー待ち・下書き作成済みが無ければ '' を返す。 */
function buildFridayDigestMessage_() {
  const d = getReviewableDrafts_();
  if (d.review.length === 0 && d.draft.length === 0) return '';

  let msg = '週末のお供を持ってきたよ ✨\n合間にレビューして『公開OK』にしてくれると嬉しい 🌟\n';
  if (d.review.length > 0) {
    msg += '\n*【レビュー待ち（Docを見てね）】*\n';
    d.review.forEach(function (x) {
      msg += '・' + x.term + (x.url ? ' → <' + x.url + '|レビューする>' : '') + '\n';
    });
  }
  if (d.draft.length > 0) {
    msg += '\n*【下書き作成済み（あとは公開するだけ）】*\n';
    d.draft.forEach(function (x) {
      msg += '・' + x.term + (x.url ? ' → <' + x.url + '|WPで開く>' : '') + '\n';
    });
  }
  msg += '\nどれか1つでも進むと嬉しいな 😊';
  return msg;
}

function sendFridayDigest() {
  // 告知前に「下書き作成済み」だけをwp_post_idでWP実体照合（公開済みを除外／消えた下書きを戻す）。
  // レビュー待ちのあいまい照合はしない（レビュー中の記事を誤って消さないため）。
  try { reconcileDraftByWp_(); } catch (e) {}
  const msg = buildFridayDigestMessage_();
  if (msg) postToSlack(REPORT_CHANNEL, msg);
}

/** テスト用: 本番と同じ内容を yuya のDMだけに送る（チームには出さない）。1q0Oエディタで ▶ 実行。 */
function testFridayDigest() {
  try { reconcileDraftByWp_(); } catch (e) {}
  const msg = buildFridayDigestMessage_() || '（今はレビュー待ち・下書き作成済みが0件。本番なら投稿されないよ）';
  console.log('=== 金曜ダイジェスト テスト内容 ===\n' + msg);
  try {
    postToSlack('UJJEGF3HU', '🧪 金曜ダイジェストのテスト送信（DM限定・チームには出てないよ）\n\n' + msg);
    console.log('DMへ送信を試行しました。届かない場合はSlackアプリにim:write権限が必要（上のログが本文）。');
  } catch (e) {
    console.log('DM送信失敗: ' + e + ' / 上のログの内容がテスト結果です。');
  }
}

/** 週次トリガーをまとめて登録（金曜17時DM＋月曜11時レポート）。1q0Oエディタで一度 ▶ 実行する。 */
function setupWeeklyTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    const f = t.getHandlerFunction();
    if (f === 'sendFridayDigest' || f === 'sendMondayReport') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendFridayDigest').timeBased().onWeekDay(ScriptApp.WeekDay.FRIDAY).atHour(17).inTimezone('Asia/Tokyo').create();
  ScriptApp.newTrigger('sendMondayReport').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(11).inTimezone('Asia/Tokyo').create();
  console.log('週次トリガーを登録しました: 金曜17時DM ＋ 月曜11時レポート');
}

// ============================================================
// 動作確認・セットアップ用
// ============================================================

function testCallClaude() {
  const articles = getExistingArticles();
  console.log('existing articles count: ' + articles.length);
  if (articles.length > 0) {
    console.log('sample: ' + JSON.stringify(articles[0]));
  }
  const sys = buildDefaultSystemPrompt();
  const usr = buildDefaultUserPrompt('アクセシビリティの用語', articles);
  const result = callClaude(sys, usr);
  console.log('=== Claude response ===');
  console.log(result);
}

/** 認可通し用：エディタで一度これを実行して、Spreadsheet／外部Fetchの権限を承認する。 */
function authorizeOnce() {
  const ss = SpreadsheetApp.openById(GLOSSARY_SHEET_ID);
  console.log('用語DB last row: ' + ss.getSheetByName(GLOSSARY_TAB).getLastRow());
  // WP下書きのDoc読取に使う documents スコープの認可も通す（既知のDocを開く）
  try {
    const doc = DocumentApp.openById('1zh4n7TNtsg4UWxS2squkoGOciquQQO_IdqkSCL5e5GA');
    console.log('Docs認可OK: ' + doc.getName());
  } catch (e) {
    console.log('Docs認可（未認可なら実行時に権限ダイアログが出る）: ' + e);
  }
}

/**
 * 用語DBの「設定」タブのB列に入れた値を、このBotのスクリプトプロパティへ保存する。
 * 標準のプロパティ画面を触らずに設定できる。1q0Oエディタで関数 saveBotSettings を ▶ 実行して使う。
 * 保存できた値のセルは空にする（トークン等をシートに残さない）。
 */
function saveBotSettings() {
  const KNOWN = ['ANTHROPIC_API_KEY', 'SLACK_BOT_TOKEN', 'WORDPRESS_BASE_URL', 'WEBHOOK_SECRET', 'SLACK_WEBHOOK_URL',
    'WP_SITE_URL', 'WP_USER', 'WP_APP_PASS', 'WP_POST_TYPE', 'WP_CATEGORY_FIELD'];
  const sheet = SpreadsheetApp.openById(GLOSSARY_SHEET_ID).getSheetByName('設定');
  if (!sheet) { console.log('「設定」タブが見つかりません'); return; }
  const props = PropertiesService.getScriptProperties();
  const rows = sheet.getRange(1, 1, sheet.getLastRow(), 2).getValues(); // A:B
  const saved = [];
  for (let i = 0; i < rows.length; i++) {
    const key = String(rows[i][0] || '').trim();
    const val = String(rows[i][1] || '').trim();
    if (KNOWN.indexOf(key) === -1 || val === '') continue;
    props.setProperty(key, val);
    saved.push(key);
    sheet.getRange(i + 1, 2).setValue(''); // 保存後に値セルを空にする
  }
  const status = KNOWN.map(function (k) { return k + ': ' + (props.getProperty(k) ? '✓設定済み' : '—未設定'); }).join('\n');
  console.log('保存: ' + (saved.join(', ') || '（新規なし）'));
  console.log('現在の設定:\n' + status);
}
