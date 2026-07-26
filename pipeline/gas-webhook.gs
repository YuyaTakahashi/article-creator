/**
 * 用語くん — UX TIMES 用語DB 連携 GAS（Phase 1: Webhook骨格）
 *
 * デプロイ手順:
 * 1. スプレッドシート「UX TIMES 用語DB」→ 拡張機能 → Apps Script にこのファイルを貼る
 * 2. SECRET_TOKEN を適当な長いランダム文字列に変える
 * 3. SLACK_WEBHOOK_URL に UX DAYS TOKYO側Slackの Incoming Webhook URL を入れる
 *    （Slack App管理画面 → Incoming Webhooks → 投稿先チャンネルを選んで発行）
 * 4. デプロイ → 新しいデプロイ → 種類「ウェブアプリ」→ 実行ユーザー「自分」→
 *    アクセス「全員」→ デプロイし、Web App URL を article-creator/.env の GAS_WEBAPP_URL へ
 * 5. weeklyDigest を使う場合は トリガー → 時間主導型 → 週タイマーで登録する
 */

const CONFIG = {
  SECRET_TOKEN: 'CHANGE_ME_RANDOM_STRING',
  SLACK_WEBHOOK_URL: '', // 空ならSlack通知をスキップする
  SHEET_NAME: 'UX TIMES 用語DB', // CSV取込時のシート名。異なる場合は実際のタブ名に合わせる
  SETTINGS_SHEET_NAME: '設定', // WP認証などをセル入力→スクリプトプロパティへ移すタブ
  BOT_NAME: '用語くん',
};

// 列番号（1始まり）: A:ID B:用語 C:英語名 D:補足・文脈 E:提案元 F:提案日 G:生成する H:ステータス I:記事Doc J:WP URL K:生成日 L:備考
//   M:slug N:excerpt O:category_id P:featured_media Q:wp_post_id （公開OK→WP下書き作成に使う。生成時にupdate_rowで埋める）
const COL = {
  ID: 1, TERM: 2, TERM_EN: 3, CONTEXT: 4, PROPOSER: 5, PROPOSED_AT: 6, FLAG: 7, STATUS: 8,
  DOC_URL: 9, WP_URL: 10, GENERATED_AT: 11, NOTE: 12,
  SLUG: 13, EXCERPT: 14, CATEGORY_ID: 15, FEATURED_MEDIA: 16, WP_POST_ID: 17,
};

/**
 * Webhook入口。
 * action:
 *   add_term   … 用語の提案を1行追加する {term, term_en?, context?, proposer?}
 *   update_row … パイプラインからの書き戻し {id, status?, doc_url?, wp_url?, generated_at?, note?}
 */
function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.token !== CONFIG.SECRET_TOKEN) {
      return jsonOut({ ok: false, error: 'invalid token' });
    }
    if (body.action === 'add_term') return addTerm(body);
    if (body.action === 'update_row') return updateRow(body);
    return jsonOut({ ok: false, error: 'unknown action' });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err) });
  }
}

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName(CONFIG.SHEET_NAME) || ss.getSheets()[0];
}

function addTerm(body) {
  const sheet = getSheet();
  const nextId = 'G-' + String(sheet.getLastRow()).padStart(3, '0');
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  sheet.appendRow([
    nextId, body.term, body.term_en || '', body.context || '',
    body.proposer || CONFIG.BOT_NAME, today, false, '提案中', '', '', '', body.note || '',
  ]);
  // silent:true のときはSlack通知を出さない（候補の一括インポートでの通知連打を防ぐ）
  if (!body.silent) {
    notifySlack(`:bulb: ${CONFIG.BOT_NAME}が用語を提案しました: *${body.term}*` +
      (body.context ? `\n> ${body.context}` : '') +
      `\n生成してほしいときはシートの「生成する」にチェックを入れてください`);
  }
  return jsonOut({ ok: true, id: nextId });
}

function updateRow(body) {
  const sheet = getSheet();
  const ids = sheet.getRange(2, COL.ID, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
  const idx = ids.indexOf(body.id);
  if (idx === -1) return jsonOut({ ok: false, error: 'id not found: ' + body.id });
  const row = idx + 2;

  const set = (col, val) => { if (val !== undefined && val !== null && val !== '') sheet.getRange(row, col).setValue(val); };
  set(COL.STATUS, body.status);
  set(COL.DOC_URL, body.doc_url);
  set(COL.WP_URL, body.wp_url);
  set(COL.GENERATED_AT, body.generated_at);
  set(COL.NOTE, body.note);
  // 公開OK→WP下書き作成に使う項目（生成時にローカルバッチがフロントマターから送る）
  set(COL.SLUG, body.slug);
  set(COL.EXCERPT, body.excerpt);
  set(COL.CATEGORY_ID, body.category_id);
  set(COL.FEATURED_MEDIA, body.featured_media);
  set(COL.WP_POST_ID, body.wp_post_id);

  if (body.status === 'レビュー待ち') {
    const term = sheet.getRange(row, COL.TERM).getValue();
    notifySlack(`:memo: 記事ドラフトができました: *${term}*\nGoogleドキュメントでレビューをお願いします → ${body.doc_url}\nレビューが終わったらシートのステータスを「公開OK」にしてください`);
  }
  return jsonOut({ ok: true, row: row });
}

/** 週次ダイジェスト（時間主導トリガーで呼ぶ）: レビュー待ち・提案中を一覧でSlackに流す */
function weeklyDigest() {
  const sheet = getSheet();
  if (sheet.getLastRow() < 2) return;
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, COL.NOTE).getValues();
  const waiting = data.filter((r) => r[COL.STATUS - 1] === 'レビュー待ち');
  const proposed = data.filter((r) => r[COL.STATUS - 1] === '提案中');
  let msg = `:newspaper: ${CONFIG.BOT_NAME}の週次まとめ\n`;
  msg += `レビュー待ち: ${waiting.length}件` +
    waiting.map((r) => `\n• ${r[COL.TERM - 1]} → ${r[COL.DOC_URL - 1]}`).join('') + '\n';
  msg += `提案中（チェック待ち）: ${proposed.length}件` +
    proposed.map((r) => `\n• ${r[COL.TERM - 1]}`).join('');
  notifySlack(msg);
}

function notifySlack(text) {
  if (!CONFIG.SLACK_WEBHOOK_URL) return;
  UrlFetchApp.fetch(CONFIG.SLACK_WEBHOOK_URL, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ username: CONFIG.BOT_NAME, icon_emoji: ':books:', text: text }),
    muteHttpExceptions: true,
  });
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/* ============================================================
 * 公開OK → WP下書き作成（スプシのカスタムメニューから手動実行）
 *   使い方: 対象の1行を選択 → メニュー「用語くん」→「▶ 選択行をWP下書きに送る」
 *   必要な列: I:記事Doc（必須）, M:slug, N:excerpt, O:category_id, P:featured_media(任意), Q:wp_post_id(任意)
 *   WP認証はスクリプトプロパティに置く: WP_SITE_URL / WP_USER / WP_APP_PASS / WP_POST_TYPE / WP_CATEGORY_FIELD
 *   status は常に draft。公開はWP管理画面で人間が行う。
 * ============================================================ */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('用語くん')
    .addItem('▶ 選択行をWP下書きに送る', 'publishSelectedRowToWpDraft')
    .addSeparator()
    .addItem('⚙ WP設定を保存（設定シート→保存）', 'saveWpSettings')
    .addToUi();
}

/** 「設定」シートのB列に入れた値をスクリプトプロパティへ移す。保存できたセルは空にする（パスワードを残さない）。 */
function saveWpSettings() {
  const ui = SpreadsheetApp.getUi();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.SETTINGS_SHEET_NAME);
  if (!sheet) { ui.alert('「' + CONFIG.SETTINGS_SHEET_NAME + '」シートが見つかりません'); return; }
  const KNOWN = ['WP_SITE_URL', 'WP_USER', 'WP_APP_PASS', 'WP_POST_TYPE', 'WP_CATEGORY_FIELD'];
  const props = PropertiesService.getScriptProperties();
  const rows = sheet.getRange(1, 1, sheet.getLastRow(), 2).getValues(); // A:B
  const saved = [];
  for (let i = 0; i < rows.length; i++) {
    const key = String(rows[i][0] || '').trim();
    const val = String(rows[i][1] || '').trim();
    if (KNOWN.indexOf(key) === -1 || val === '') continue;
    props.setProperty(key, val);
    saved.push(key);
    sheet.getRange(i + 1, 2).setValue(''); // 保存できた値のセルを空にする
  }
  const status = KNOWN.map((k) => k + ': ' + (props.getProperty(k) ? '✓設定済み' : '—未設定')).join('\n');
  ui.alert('保存: ' + (saved.length ? saved.join(', ') : '（新規なし）') + '\n\n現在の設定:\n' + status);
}

function publishSelectedRowToWpDraft() {
  const ui = SpreadsheetApp.getUi();
  const sheet = getSheet();
  const range = SpreadsheetApp.getActiveRange();
  if (!range || range.getSheet().getName() !== sheet.getName() || range.getRow() < 2) {
    ui.alert('用語DBのデータ行を1つ選んでから実行してください');
    return;
  }
  try {
    const res = publishRowToWpDraft_(sheet, range.getRow());
    ui.alert('WP下書きを作成しました\n\n用語: ' + res.term + '\nWP: ' + res.link);
  } catch (err) {
    ui.alert('WP下書き作成に失敗しました\n\n' + err);
  }
}

function wpConfig_() {
  const p = PropertiesService.getScriptProperties();
  const site = (p.getProperty('WP_SITE_URL') || '').replace(/\/+$/, '');
  const user = p.getProperty('WP_USER') || '';
  const pass = (p.getProperty('WP_APP_PASS') || '').replace(/\s/g, '');
  if (!site || !user || !pass) {
    throw new Error('WP認証が未設定です（スクリプトプロパティ WP_SITE_URL / WP_USER / WP_APP_PASS を設定してください）');
  }
  return {
    site: site, user: user, pass: pass,
    postType: p.getProperty('WP_POST_TYPE') || 'posts',
    categoryField: p.getProperty('WP_CATEGORY_FIELD') || 'glossary-category',
    auth: Utilities.base64Encode(user + ':' + pass),
  };
}

function publishRowToWpDraft_(sheet, row) {
  const cfg = wpConfig_();
  const get = (col) => sheet.getRange(row, col).getValue();
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
  const html = mdToHtml_(stripTitle_(md));

  const payload = { title: title, content: html, status: 'draft' };
  if (excerpt) payload.excerpt = excerpt;
  if (slug) payload.slug = slug;
  if (categoryId !== '' && categoryId != null) payload[cfg.categoryField] = [Number(categoryId)];
  if (featuredMedia !== '' && featuredMedia != null) payload.featured_media = Number(featuredMedia);

  let endpoint = cfg.site + '/wp-json/wp/v2/' + cfg.postType;
  if (wpPostId) { endpoint += '/' + wpPostId; delete payload.status; } // 更新時はWP側の公開状態を保持する

  const resp = UrlFetchApp.fetch(endpoint, {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { Authorization: 'Basic ' + cfg.auth },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error('WP応答 ' + code + ': ' + resp.getContentText().slice(0, 300));
  }
  const j = JSON.parse(resp.getContentText());
  // 下書きは未公開で公開パーマリンクは開けないため、WP管理画面の編集URL（下書きを開いて公開する用）を記録する
  const editUrl = cfg.site + '/wp-admin/post.php?post=' + j.id + '&action=edit';

  sheet.getRange(row, COL.WP_URL).setValue(editUrl);
  sheet.getRange(row, COL.WP_POST_ID).setValue(j.id);
  sheet.getRange(row, COL.STATUS).setValue('下書き作成済み');
  // WP下書き化したDocのファイル名頭に「【WP移行済み】」を付け、他の人が間違って着手しないようにする。
  try { markDocMigrated_(docUrl); } catch (e) { /* Docタイトル更新失敗（WP下書きは成功済み） */ }
  notifySlack(':outbox_tray: WP下書きを作成しました: *' + term + '*\n' + editUrl + '\nWP管理画面で確認・公開してください');
  return { term: term, link: editUrl, id: j.id };
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

/**
 * GoogleドキュメントをGAS内蔵の DocumentApp で読み、Markdown相当のテキストにする。
 * Drive REST API（プロジェクトでのAPI有効化が必要）を使わないので、内蔵サービスの documents スコープだけで動く。
 * 見出し→#、リスト→-、太字→**、リンク→[text](url) に変換。ルビ(¥…¥)・wp分割ラインは素のテキストなので保持される。
 */
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
    // TABLE等は用語記事では通常使わないためスキップ
  }
  return out.join('\n\n');
}

/** Text要素の装飾（太字・リンク）をMarkdownに変換する。装飾なしなら素のテキストを返す。 */
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
    try { url = textEl.getLinkUrl(start); bold = textEl.isBold(start); } catch (e) { /* 装飾取得不可はそのまま */ }
    if (bold) seg = '**' + seg + '**';
    if (url) seg = '[' + seg + '](' + url + ')';
    result += seg;
  }
  return result || plain;
}

/** Doc編集後の整形: 冒頭のレビュー案内行を除去する。 */
function cleanReviewMd_(md) {
  return String(md)
    .split('\n')
    .filter((line) => !/^\s*[*_]*（レビュー用ドラフト/.test(line))
    .join('\n');
}

function extractTitle_(md) {
  const m = md.match(/^#\s+(.+?)\s*$/m);
  return m ? m[1].trim() : '';
}

function stripTitle_(md) {
  // 先頭H1（タイトル）は payload.title として送るので本文からは落とす
  return md.replace(/^#\s+.+?\r?\n/, '');
}

/**
 * 最小限のMarkdown→HTML。ルビ(英字¥カナ¥)・wp分割ライン・見出し・箇条書き・引用・強調・リンクに対応。
 * post_to_wp.py ほど枯れていないため、初回は必ず1本で実地確認してから運用に乗せる。
 */
function mdToHtml_(md) {
  const inline = (s) => s
    .replace(/([A-Za-z0-9.'’&-]+)¥([^¥]+)¥/g, '<ruby>$1<rt>$2</rt></ruby>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  const lines = String(md).replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let para = [];
  let inList = false;
  const flushPara = () => { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
  const flushList = () => { if (inList) { out.push('</ul>'); inList = false; } };

  for (let raw of lines) {
    const line = raw.replace(/\s+$/, '');
    if (/wp分割ライン/.test(line)) { flushPara(); flushList(); out.push('<!--nextpage-->'); continue; }
    if (line.trim() === '') { flushPara(); flushList(); continue; }
    if (/^\s*</.test(line)) { flushPara(); flushList(); out.push(line); continue; } // figure/img等の生HTMLは素通し
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      flushPara(); flushList();
      const lv = Math.max(2, m[1].length); // 本文見出しは h2 起点（h1はWPのタイトル）
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

/*
 * Slackメンション受付（@用語くん xx 追加して → 用語DBへ追記）は、
 * このプロジェクトではなく用語くん本体（スタンドアロンGAS: scriptId 1q0O_ffq9hHlZr-…）側に実装している。
 * 用語くんが用語DBへ addTerm 相当の追記を行うため、ここには置かない。
 */

/**
 * documents スコープの認可を通すための関数（DocumentApp 内蔵サービス。プロジェクトのAPI有効化は不要）。
 * WP下書きが認可エラーになったら、1SMSエディタでこの関数を ▶ 実行し、出る認可ダイアログを許可する。
 * UIを使わないのでエディタ実行でもエラーにならない。ログに「Docs認可OK: …」が出れば認可完了。
 */
function authorizeDocs() {
  try {
    const doc = DocumentApp.openById('1zh4n7TNtsg4UWxS2squkoGOciquQQO_IdqkSCL5e5GA'); // 人工的希少性のDoc（動作確認用）
    Logger.log('Docs認可OK: ' + doc.getName());
  } catch (e) {
    Logger.log('Docs認可エラー: ' + e);
  }
}
