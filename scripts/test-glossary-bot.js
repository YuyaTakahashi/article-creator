// 用語くん（GAS）のロジックの動作確認。用語照合（表記ゆれ吸収）と、Markdown→HTML変換（ルビ）を見る。
// GASの外でロジックだけ動かすので `node scripts/test-glossary-bot.js` で走る。
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'pipeline', 'glossary-bot', 'code.js'), 'utf8');
const ctx = {
  console,
  SpreadsheetApp: {}, PropertiesService: {}, UrlFetchApp: {}, CacheService: {},
  Utilities: {}, ContentService: {}, DocumentApp: {}, HtmlService: {}, Session: {},
};
vm.createContext(ctx);
vm.runInContext(src, ctx);

// セクション7でSlackコマンドを通すために publishRowToWpDraft_ を差し替えるので、本物を控えておく
const realPublishRowToWpDraft = ctx.publishRowToWpDraft_;

// A:ID B:用語 C:英語名 ... の22列を持つ行を作る
function makeRow(id, term, termEn) {
  const r = new Array(22).fill('');
  r[0] = id; r[1] = term; r[2] = termEn;
  return r;
}
function makeSheet(rows) {
  return {
    getLastRow: function () { return rows.length + 1; },
    getRange: function (row, col, nRows, nCols) {
      const rs = nRows === undefined ? 1 : nRows;
      const cs = nCols === undefined ? 1 : nCols;
      return {
        getValues: function () {
          const out = [];
          for (let i = 0; i < rs; i++) {
            const src = rows[row - 2 + i] || new Array(22).fill('');
            out.push(src.slice(col - 1, col - 1 + cs));
          }
          return out;
        },
        getValue: function () { return (rows[row - 2] || [])[col - 1]; },
        setValue: function (v) { (rows[row - 2] || [])[col - 1] = v; return this; },
      };
    },
  };
}

const sheet = makeSheet([
  makeRow('G-001', 'モーダル', 'Modal'),
  makeRow('G-002', '情報アーキテクチャ（IA）', 'Information Architecture / IA'),
  makeRow('G-003', 'IaC', 'Infrastructure as Code'),
  makeRow('G-004', 'ユーザビリティ', 'Usability'),
  makeRow('G-005', 'ヤーキーズ・ドッドソンの法則', 'Yerkes-Dodson Law'),
  makeRow('G-006', 'ダークパターン', 'Deceptive Pattern, Dark Pattern'),
  makeRow('G-007', 'モーダル（旧称）', ''), // 別の行の別名とかぶる表記
]);

let fail = 0;
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) fail++;
  console.log((ok ? 'ok   ' : 'FAIL ') + label + ' → ' + JSON.stringify(actual) +
    (ok ? '' : ' (expected ' + JSON.stringify(expected) + ')'));
}
const idOf = function (q) {
  const r = ctx.lookupTermRow_(sheet, q);
  return r.row === -1
    ? { row: -1, cand: r.candidates.map(function (c) { return c.id; }) }
    : { id: String(sheet.getRange(r.row, 1).getValue()) };
};

// 1. これまでも通っていた引き方は変わらない
check('完全一致', idOf('モーダル'), { id: 'G-001' });
check('完全一致は別名より優先', idOf('モーダル（旧称）'), { id: 'G-007' });
check('記号・空白ゆれ', idOf('情報アーキテクチャ (IA)'), { id: 'G-002' });

// 2. 今回直したところ
check('英語名で引く', idOf('Modal'), { id: 'G-001' });
check('英語名の併記の片方', idOf('Deceptive Pattern'), { id: 'G-006' });
check('括弧の外だけ', idOf('情報アーキテクチャ'), { id: 'G-002' });
check('括弧の中だけ', idOf('IA'), { id: 'G-002' });
check('全角英字', idOf('ＩａＣ'), { id: 'G-003' });
check('大文字小文字', idOf('iac'), { id: 'G-003' });
check('l と I の取り違え', idOf('laC'), { id: 'G-003' });
check('長音の有無', idOf('ユーザービリティ'), { id: 'G-004' });
check('ひらがな', idOf('ゆーざびりてぃ'), { id: 'G-004' });
check('中黒なし', idOf('ヤーキーズドッドソンの法則'), { id: 'G-005' });

// 3. 決められないときは確定せず候補を出す
check('長音の抜け（確定できる）', idOf('ダークパタン'), { id: 'G-006' });
check('1文字違い（候補どまり）', idOf('モータル'), { row: -1, cand: ['G-001', 'G-007'] });
check('部分一致', idOf('ドッドソンの法則'), { row: -1, cand: ['G-005'] });
check('無関係な語', idOf('カルーセル'), { row: -1, cand: [] });
check('空文字', idOf(''), { row: -1, cand: [] });

// 4. G-ID経由（resolveTermRow_）
check('G-ID', (function () { const r = ctx.resolveTermRow_(sheet, 'G-003'); return { row: r.row }; })(), { row: 4 });
check('G-IDの桁埋め', (function () { const r = ctx.resolveTermRow_(sheet, 'G-3'); return { row: r.row }; })(), { row: 4 });
check('G-IDなし＋用語名', (function () { const r = ctx.resolveTermRow_(sheet, 'Modal'); return { row: r.row }; })(), { row: 2 });

// 5. 見つからなかったときの文面
console.log('---');
console.log(ctx.termNotFoundMessage_('laCC', ctx.lookupTermRow_(sheet, 'laCC').candidates));
console.log(ctx.termNotFoundMessage_('カルーセル', []));

// 6. 重複判定に使う照合キー
check('termKey_', ctx.termKey_('モーダル（Modal）'), 'モーダルmodal');
check('looseTermKey_', ctx.looseTermKey_('ユーザービリティ'), 'ゆざびりてぃ');
check('isNearMiss_ 1文字違い', ctx.isNearMiss_('iac', 'ia'), true);
check('isNearMiss_ 2文字違い', ctx.isNearMiss_('iac', 'i'), false);

// 7. Slackコマンドとして通しで動かす（「laC をWP下書きに」がIaCの行に当たる）
const posted = [];
ctx.postToSlack = function (channel, text) { posted.push(text); };
ctx.getGlossarySheet_ = function () { return sheet; };
ctx.publishRowToWpDraft_ = function (s, row) {
  return { term: String(s.getRange(row, 2).getValue()), link: 'https://example.com/wp-admin/post.php?post=1&action=edit' };
};
ctx.handleWpDraftCommand({ channel: 'C1', ts: '1' }, 'laC をWP下書きに');
check('WP下書きコマンド', /IaC/.test(posted[0]) && /WP下書きを作成した/.test(posted[0]), true);

posted.length = 0;
ctx.handleWpDraftCommand({ channel: 'C1', ts: '1' }, 'カルーセル をWP下書きに');
check('WP下書きコマンド（無い用語）', /見つからなかった/.test(posted[0]), true);

posted.length = 0;
ctx.handleWpDraftCommand({ channel: 'C1', ts: '1' }, 'モータル をWP下書きに');
check('WP下書きコマンド（候補を出して聞き返す）',
  /もしかしてこれ？/.test(posted[0]) && /G-001/.test(posted[0]) && !/WP下書きを作成した/.test(posted[0]), true);

// 8. Markdown→HTML：ルビの区切りは半角¥・全角￥のどちらでも変換する
//    記事によってどちらで書かれるか揺れる（実際に全角で書かれた回が素通りしていた）
const ruby = function (md) { return ctx.mdToHtml_(md); };
check('ルビ（半角¥）',
  ruby('Robert¥ロバート¥ Cialdini¥チャルディーニ¥である。'),
  '<p><ruby>Robert<rt>ロバート</rt></ruby> <ruby>Cialdini<rt>チャルディーニ</rt></ruby>である。</p>');
check('ルビ（全角￥）',
  ruby('Kief￥キーフ￥ Morris￥モリス￥が2016年に著した。'),
  '<p><ruby>Kief<rt>キーフ</rt></ruby> <ruby>Morris<rt>モリス</rt></ruby>が2016年に著した。</p>');
check('ルビ（半角と全角の混在）',
  ruby('M.¥エム¥ Yerkes￥ヤーキズ￥'),
  '<p><ruby>M.<rt>エム</rt></ruby> <ruby>Yerkes<rt>ヤーキズ</rt></ruby></p>');
check('ルビ（見出し・箇条書きの中でも変換する）',
  ruby('## Robert￥ロバート￥の法則\n\n- Amos¥エイモス¥ Tversky¥トベルスキー¥'),
  '<h2><ruby>Robert<rt>ロバート</rt></ruby>の法則</h2>\n<ul>\n<li><ruby>Amos<rt>エイモス</rt></ruby> <ruby>Tversky<rt>トベルスキー</rt></ruby></li>\n</ul>');
check('ルビ記法でない円記号はそのまま',
  ruby('価格は1￥から。'),
  '<p>価格は1￥から。</p>');

// 9. WP下書き：用語DBに記録した wp_post_id が使えないときの振る舞い
//    「WP応答 404: rest_post_invalid_id」で止まるだけだった経路。
const COL = { ID: 1, TERM: 2, STATUS: 8, DOC_URL: 9, WP_URL: 10, SLUG: 13, EXCERPT: 14, WP_POST_ID: 17 };
function makeWpRow(postId) {
  const r = new Array(22).fill('');
  r[COL.ID - 1] = 'G-013';
  r[COL.TERM - 1] = 'IaC';
  r[COL.STATUS - 1] = '下書き作成済み';
  r[COL.DOC_URL - 1] = 'https://docs.google.com/document/d/1QCqfWr9zSQKiwB5VjI0Fx5ONE4HUOfa-USUdbMU14gU/edit';
  r[COL.SLUG - 1] = 'infrastructure-as-code';
  r[COL.EXCERPT - 1] = 'インフラ構成をコードで書く仕組み';
  r[COL.WP_POST_ID - 1] = postId;
  return r;
}

// WPの応答を差し替えて1回分の「WP下書きに」を走らせる。responder(url, method) が {code, body} を返す。
function runWpDraft(postId, responder) {
  const rows = [makeWpRow(postId)];
  const wpSheet = makeSheet(rows);
  const calls = [];
  ctx.SpreadsheetApp = { flush: function () {} };
  ctx.LockService = { getScriptLock: function () { return { tryLock: function () { return true; }, releaseLock: function () {} }; } };
  ctx.PropertiesService = {
    getScriptProperties: function () {
      const props = {
        WP_SITE_URL: 'https://example.com', WP_USER: 'u', WP_APP_PASS: 'p',
        WP_POST_TYPE: 'glossary', WP_CATEGORY_FIELD: 'glossary-category',
      };
      return { getProperty: function (k) { return props[k] || ''; } };
    },
  };
  ctx.Utilities = { base64Encode: function () { return 'BASIC'; } };
  ctx.fetchDocMarkdown_ = function () { return '# IaC\n\n-- wp分割ライン--\n\nKief￥キーフ￥ Morris￥モリス￥が著した。'; };
  ctx.markDocMigrated_ = function () {};
  ctx.UrlFetchApp = {
    fetch: function (url, opts) {
      const method = (opts && opts.method) || 'get';
      calls.push({ url: url, method: method, payload: opts && opts.payload });
      const r = responder(url, method);
      return { getResponseCode: function () { return r.code; }, getContentText: function () { return r.body; } };
    },
  };
  let result = null, error = null;
  try { result = realPublishRowToWpDraft(wpSheet, 2); } catch (e) { error = String(e); }
  return { result: result, error: error, calls: calls, row: rows[0] };
}

const NOT_FOUND = '{"code":"rest_post_invalid_id","message":"無効な投稿 ID です。","data":{"status":404}}';

// 9-1. 記録済みIDが生きている → その投稿を更新する（statusは送らず公開状態を保つ）
const alive = runWpDraft(39245, function (url, method) {
  if (method === 'get') return { code: 200, body: '{"id":39245,"status":"draft"}' };
  return { code: 200, body: '{"id":39245,"status":"draft"}' };
});
check('WP更新（IDが生きている）', (function () {
  const post = alive.calls.filter(function (c) { return c.method === 'post'; });
  return post.length === 1 && /\/glossary\/39245$/.test(post[0].url) &&
    !('status' in JSON.parse(post[0].payload)) && !alive.result.note;
})(), true);

// 9-2. 記録済みIDがWPから消えている → 新規下書きを作り、用語DBのIDを差し替える
const gone = runWpDraft(39245, function (url, method) {
  if (method === 'get') return { code: 404, body: NOT_FOUND };
  return { code: 201, body: '{"id":40001,"status":"draft"}' };
});
check('WP更新（IDが消えている→作り直し）', (function () {
  const post = gone.calls.filter(function (c) { return c.method === 'post'; });
  return post.length === 1 && /\/wp\/v2\/glossary$/.test(post[0].url) &&
    JSON.parse(post[0].payload).status === 'draft' &&
    gone.row[COL.WP_POST_ID - 1] === 40001 && /見つからなかった/.test(gone.result.note);
})(), true);

// 9-3. 別の投稿タイプで生きている → 二重投稿を避けて止め、設定を直すよう伝える
const otherType = runWpDraft(39245, function (url, method) {
  if (method !== 'get') return { code: 201, body: '{"id":40002,"status":"draft"}' };
  return /\/posts\//.test(url) ? { code: 200, body: '{"id":39245,"status":"draft"}' } : { code: 404, body: NOT_FOUND };
});
check('WP更新（別の投稿タイプにあった→作らずに止める）',
  otherType.result === null && /posts/.test(otherType.error) && /WP_POST_TYPE/.test(otherType.error) &&
  otherType.calls.filter(function (c) { return c.method === 'post'; }).length === 0, true);

// 9-4. ゴミ箱に入っていた → 下書きに戻して更新する
const trashed = runWpDraft(39245, function (url, method) {
  if (method === 'get') return { code: 200, body: '{"id":39245,"status":"trash"}' };
  return { code: 200, body: '{"id":39245,"status":"draft"}' };
});
check('WP更新（ゴミ箱→下書きに戻す）', (function () {
  const post = trashed.calls.filter(function (c) { return c.method === 'post'; });
  return post.length === 1 && JSON.parse(post[0].payload).status === 'draft' && /ゴミ箱/.test(trashed.result.note);
})(), true);

// 9-5. 認証エラーなどは「無い」と誤判定しない（作り直すと記事が二重になる）
const denied = runWpDraft(39245, function (url, method) {
  if (method === 'get') return { code: 401, body: '{"code":"rest_not_logged_in"}' };
  return { code: 201, body: '{"id":40003,"status":"draft"}' };
});
check('WP更新（401では作り直さない）',
  denied.result === null && /401/.test(denied.error) &&
  denied.calls.filter(function (c) { return c.method === 'post'; }).length === 0, true);

console.log(fail === 0 ? '\nすべて通過' : '\n失敗 ' + fail + ' 件');
process.exit(fail === 0 ? 0 : 1);
