// CLASPRC_JSON（clasp の認証情報）が使える形かどうかだけを判定する。
//
// 中身は Google アカウントのリフレッシュトークンそのものなので、
// このスクリプトは値を一切出力しない。出すのは「どう壊れているか」の分類だけ。
// 公開リポジトリの Actions ログに残ることを前提に書くこと。
const fs = require('fs');

let raw;
try {
  raw = fs.readFileSync(process.argv[2], 'utf8');
} catch (e) {
  console.log('読み込み失敗: ' + (e.code || e.name));
  process.exit(1);
}

let parsed;
try {
  parsed = JSON.parse(raw);
} catch (e) {
  console.log(
    'JSONとして不正: ' + (e.name || 'Error') +
    ' / 長さ' + Buffer.byteLength(raw) + 'バイト' +
    ' / 先頭が波括弧=' + raw.trimStart().startsWith('{')
  );
  process.exit(1);
}

// v3 は {"tokens":{"<user>":{...}}}、v1 は {"token":{...}} か {"access_token":...}。
// clasp は v1 形式も後方互換で読むので、どちらでも通す。
// ユーザー名はメールアドレスのことがあるので、キーの中身は出力しない。
const shape =
  parsed && parsed.tokens ? 'v3' :
  parsed && (parsed.token || parsed.access_token) ? 'v1' : null;

if (!shape) {
  console.log('JSONではあるが clasp の認証ファイルの形ではない（tokens も token も無い）');
  process.exit(1);
}

console.log('OK: ' + shape + '形式');
