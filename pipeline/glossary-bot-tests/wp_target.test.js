// 用語くんの「対象行の特定」の回帰テスト。実行: node pipeline/glossary-bot-tests/wp_target.test.js
// glossary-bot/ の外に置く（clasp push の対象に入れないため）。
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync(process.argv[2] || require('path').join(__dirname, '../glossary-bot/code.js'),'utf8');
const DOC='https://docs.google.com/document/d/1fSjtckS1VUqG5IWS2beNBVoQ2G5rp66b2DHYgkwHYDk/edit';
const rows=[['ID','用語','英語名'],['G-005','ゼロショット／ワンショット',''],['G-032','システムインテグレーター','SI'],['G-033','ダミー','']];
const I={2:'',3:DOC,4:''};
const sheet={getLastRow:()=>rows.length,getRange:(r,c,n,w)=>({
  getValue:()=>c===9?I[r]:(rows[r-1]||[])[c-1]||'',
  getValues:()=>{const o=[];for(let i=0;i<(n||1);i++){const rr=r+i;const row=[];for(let j=0;j<(w||1);j++){const cc=c+j;row.push(cc===9?(I[rr]||''):((rows[rr-1]||[])[cc-1]||''));}o.push(row);}return o;}})};
const ctx={console,SpreadsheetApp:{},PropertiesService:{getScriptProperties:()=>({getProperty:()=>''})},LockService:{},Utilities:{},UrlFetchApp:{},ContentService:{},DriveApp:{},DocumentApp:{},CacheService:{},Session:{},Logger:console};
vm.createContext(ctx);vm.runInContext(src,ctx);
const out=[];ctx.postToSlack=(ch,t)=>out.push(t);
ctx.getGlossarySheet_=()=>sheet;
ctx.publishRowToWpDraft_=(sh,row)=>{if(!I[row])throw new Error('EMPTY row '+row);return{term:rows[row-1][1],link:'L'};};
ctx.glossaryTermRows_=()=>rows.slice(1).map((r,i)=>({row:i+2,term:r[1],aliases:[r[1],r[2]].filter(Boolean)}));
const cases=[
 '<@U1> システムインテグレーターを添削したよ。WPに移行して\n\n<'+DOC+'?tab=t.0>',
 '<@U1> システムインテグレーターをWP移行して',
 '<@U1> G-032 をWP下書きに',
 '<@U1> <https://docs.google.com/document/d/AAAAAAAAAAAAAAAAAAAAAAAAG5x/edit> システムインテグレーターをWPに移行して',
];
let ng=0;
for(const t of cases){out.length=0;ctx.handleMention({text:t,channel:'C',ts:'1'});const ok=/システムインテグレーター/.test(out.join())&&/WP下書きを作成/.test(out.join());if(!ok)ng++;console.log(ok?'OK':'NG',JSON.stringify(out).slice(0,140));}
// resolveTermRow_ via marker
const r=ctx.resolveTermRow_(sheet,DOC);console.log(r.row===3?'OK':'NG','marker url ->',r.row);if(r.row!==3)ng++;
process.exit(ng?1:0);
