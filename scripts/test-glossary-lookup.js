// 用語くんの用語照合（表記ゆれ吸収）の動作確認。
// GASの外でロジックだけ動かすので `node scripts/test-glossary-lookup.js` で走る。
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

console.log(fail === 0 ? '\nすべて通過' : '\n失敗 ' + fail + ' 件');
process.exit(fail === 0 ? 0 : 1);
