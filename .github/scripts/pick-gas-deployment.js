// `clasp list-deployments --json` の出力から、更新すべきデプロイのIDを1つ選ぶ。
//
// Slack が叩いているのはバージョン固定のデプロイ（@HEAD ではないほう）。
// clasp push はコードを置くだけなので、このデプロイを新しいバージョンに差し替えないと
// Slack 側の挙動は変わらない。
//
// 使い方: clasp list-deployments --json | node .github/scripts/pick-gas-deployment.js
// 成功すると デプロイID を1行だけ標準出力に出す。決められないときは終了コード1と理由を stderr に出す。

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  // スピナーなどが混ざっても拾えるように、JSON配列の部分だけを切り出す
  const start = raw.indexOf('[');
  const end = raw.lastIndexOf(']');
  let list;
  try {
    list = start === -1 || end === -1 ? [] : JSON.parse(raw.slice(start, end + 1));
  } catch (e) {
    console.error('clasp list-deployments の出力を JSON として読めません: ' + e.message);
    process.exit(1);
  }

  const versioned = list.filter((d) => d && d.deploymentId && d.versionNumber);
  if (versioned.length === 1) {
    console.log(versioned[0].deploymentId);
    return;
  }
  if (versioned.length === 0) {
    console.error(
      'バージョン固定のデプロイが見つかりません（@HEAD のみ）。' +
      'Apps Script の「デプロイを管理」でウェブアプリのデプロイを作るか、' +
      'リポジトリ変数 GAS_DEPLOYMENT_ID に対象のデプロイIDを設定してください。');
    process.exit(1);
  }
  console.error(
    'バージョン固定のデプロイが複数あります。どれを更新するか決められません: ' +
    versioned.map((d) => d.deploymentId + ' @' + d.versionNumber).join(', ') +
    ' / リポジトリ変数 GAS_DEPLOYMENT_ID に、Slack が叩いているデプロイのIDを設定してください。');
  process.exit(1);
});
