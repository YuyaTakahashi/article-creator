// 抜粋（最小限の説明）をDocから拾う処理の回帰テスト。実行: node pipeline/glossary-bot-tests/minimal_desc.test.js
// glossary-bot/ の外に置く（clasp push の対象に入れないため）。
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(require('path').join(__dirname,'../glossary-bot/code.js'),'utf8');
const ctx={console,SpreadsheetApp:{},PropertiesService:{getScriptProperties:()=>({getProperty:()=>''})},LockService:{},Utilities:{},UrlFetchApp:{},ContentService:{},DriveApp:{},DocumentApp:{},CacheService:{},Session:{},Logger:console};
vm.createContext(ctx);vm.runInContext(src,ctx);
const cases=[
 ['# モーダル\n\n## 最小限の説明\n\n元の画面の操作を一時的に止め、確認や入力を求める表示形式\n\n-- wp分割ライン--\n\n本文','元の画面の操作を一時的に止め、確認や入力を求める表示形式'],
 ['## 最小限の説明\n**太字**の説明。\n## 次の見出し\nx','太字の説明'],
 ['## 最小限の説明\nLarry¥ラリー¥の考え方\r\n－－ wp分割ライン－－','Larryの考え方'],
 ['# 見出しのみ\n本文',''],
];
let ng=0;
for(const [md,want] of cases){const got=ctx.extractMinimalDesc_(md);const ok=got===want;if(!ok)ng++;console.log(ok?'OK':'NG',JSON.stringify(got));}
process.exit(ng?1:0);
