/**
 * O-musubi_調整額生成ツール に追加する呼び出し口。
 *
 * 目的は2つ。
 *   1. カスタムメニューを人が押さなくても、外部から更新〜CSV生成を実行できるようにする
 *   2. 生成した調整額CSVを Drive に月次で保存し、あとから誰でも追えるようにする
 *
 * 設計上の約束
 *   - このエンドポイントは「実行のトリガー」だけを行い、荷主データを返さない。
 *     返すのは件数・対象日・実行結果といったメタ情報のみ。
 *     請求データそのものは、利用者の Google 認証を通る経路（Drive / スプレッドシート）から読む。
 *   - 破壊的な操作（調整額の登録、シートの削除）は一切行わない。
 *
 * 設置手順は references/gas-endpoint.md を参照。
 */

// ---------------------------------------------------------------------------
// 設定：既存のプロジェクトに合わせて書き換える
// ---------------------------------------------------------------------------

/**
 * カスタムメニューの各項目が呼んでいる関数名をここに書く。
 * 既存プロジェクトの onOpen() を開き、addItem(表示名, 関数名) の第2引数をそのまま写す。
 */
var ACTION_FUNCTIONS = {
  refresh_master: 'updateMultiChannelData',   // カスタムメニュー＞マルチチャネルデータを更新
  refresh_bq: 'updateBigQueryData',           // カスタムメニュー＞BigQueryデータを更新
  create_csv: 'createAdjustmentCsv',          // カスタムメニュー＞調整額CSV生成
  fetch_bill_adjustments: 'fetchBillAdjustments' // カスタムメニュー＞調整額登録結果を取得
};

/** シート名。既存プロジェクトに合わせる。 */
var SHEETS = {
  master: 'master',
  targetData: 'Target_data',
  createCsv: 'create_csv',
  billAdjustments: 'bill_adjustments'
};

/** create_csv シートの、実際の列名が入っている行番号（1始まり）。 */
var CREATE_CSV_HEADER_ROW = 2;

/** スナップショットを保存する Drive フォルダの ID。空なら保存しない。 */
var SNAPSHOT_FOLDER_ID = '';

// ---------------------------------------------------------------------------
// エンドポイント
// ---------------------------------------------------------------------------

function doGet(e) {
  var params = (e && e.parameter) || {};
  try {
    requireToken_(params.token);
    var action = params.action || 'status';
    return json_(dispatch_(action, params));
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function dispatch_(action, params) {
  switch (action) {
    case 'status':
      return withStatus_({ ok: true, action: action });

    case 'refresh_master':
    case 'refresh_bq':
    case 'create_csv':
    case 'fetch_bill_adjustments':
      runAction_(action);
      return withStatus_({ ok: true, action: action, ran: [action] });

    case 'refresh_all':
      // 月初の一連の流れ。master 更新 → BigQuery 更新 → CSV生成 の順に走らせる。
      var ran = [];
      ['refresh_master', 'refresh_bq', 'create_csv'].forEach(function (name) {
        runAction_(name);
        ran.push(name);
      });
      var result = withStatus_({ ok: true, action: action, ran: ran });
      if (SNAPSHOT_FOLDER_ID) {
        result.snapshot = snapshotCreateCsv_();
      }
      return result;

    case 'snapshot':
      return { ok: true, action: action, snapshot: snapshotCreateCsv_() };

    default:
      throw new Error('未知の action: ' + action);
  }
}

function runAction_(action) {
  var fnName = ACTION_FUNCTIONS[action];
  if (!fnName) {
    throw new Error('action に対応する関数が設定されていない: ' + action);
  }
  var fn = this[fnName] || globalThis[fnName];
  if (typeof fn !== 'function') {
    throw new Error('関数が見つからない: ' + fnName + '（ACTION_FUNCTIONS の設定を確認する）');
  }
  fn();
  SpreadsheetApp.flush();
}

/**
 * 実行後の状態を返す。荷主コードや金額といった中身は返さない。
 * 呼び出し側は、これを見て「意図した対象月のデータが揃ったか」だけを判断する。
 */
function withStatus_(base) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  base.spreadsheetId = ss.getId();
  base.checkedAt = new Date().toISOString();

  var target = ss.getSheetByName(SHEETS.targetData);
  if (target) {
    base.targetDataRows = Math.max(target.getLastRow() - 1, 0);
    base.targetDate = readFirstValue_(target, 'target_date', 1);
    base.targetTerm = readFirstValue_(target, 'target_term', 1);
  }

  var csv = ss.getSheetByName(SHEETS.createCsv);
  if (csv) {
    base.createCsvRows = Math.max(csv.getLastRow() - CREATE_CSV_HEADER_ROW, 0);
  }

  var master = ss.getSheetByName(SHEETS.master);
  if (master) {
    base.masterRows = Math.max(master.getLastRow() - 1, 0);
  }

  return base;
}

function readFirstValue_(sheet, columnName, headerRow) {
  var lastColumn = sheet.getLastColumn();
  if (lastColumn < 1 || sheet.getLastRow() <= headerRow) {
    return null;
  }
  var header = sheet.getRange(headerRow, 1, 1, lastColumn).getValues()[0];
  var index = header.indexOf(columnName);
  if (index < 0) {
    return null;
  }
  var value = sheet.getRange(headerRow + 1, index + 1).getDisplayValue();
  return value || null;
}

// ---------------------------------------------------------------------------
// Drive へのスナップショット保存
// ---------------------------------------------------------------------------

/**
 * create_csv シートを CSV ファイルとして Drive に保存する。
 * 保存先は SNAPSHOT_FOLDER_ID の下の「対象月」フォルダ。
 * 同名ファイルがあれば新しい版として上書きせず、連番を付けて残す（過去分を消さないため）。
 */
function snapshotCreateCsv_() {
  if (!SNAPSHOT_FOLDER_ID) {
    throw new Error('SNAPSHOT_FOLDER_ID が設定されていない');
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEETS.createCsv);
  if (!sheet) {
    throw new Error('シートが見つからない: ' + SHEETS.createCsv);
  }

  var lastRow = sheet.getLastRow();
  var lastColumn = sheet.getLastColumn();
  if (lastRow < CREATE_CSV_HEADER_ROW + 1) {
    throw new Error('create_csv にデータ行がない');
  }

  var values = sheet
    .getRange(CREATE_CSV_HEADER_ROW, 1, lastRow - CREATE_CSV_HEADER_ROW + 1, lastColumn)
    .getDisplayValues();
  var csv = values.map(function (row) { return row.map(escapeCsv_).join(','); }).join('\r\n');

  var term = termFromTargetData_();
  var folder = ensureFolder_(DriveApp.getFolderById(SNAPSHOT_FOLDER_ID), term);
  var baseName = 'oms_adjustment_' + term;
  var name = uniqueName_(folder, baseName, '.csv');

  var file = folder.createFile(Utilities.newBlob('﻿' + csv, 'text/csv', name));
  return {
    fileId: file.getId(),
    fileName: name,
    folderId: folder.getId(),
    rows: values.length - 1,
    term: term
  };
}

function escapeCsv_(value) {
  var text = value === null || value === undefined ? '' : String(value);
  if (/[",\r\n]/.test(text)) {
    return '"' + text.replace(/"/g, '""') + '"';
  }
  return text;
}

function termFromTargetData_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var target = ss.getSheetByName(SHEETS.targetData);
  var term = target ? readFirstValue_(target, 'target_term', 1) : null;
  if (term && /^\d{4}-\d{2}$/.test(term)) {
    return term;
  }
  // target_term が取れないときは、対象日（先月末）から組み立てる
  var date = target ? readFirstValue_(target, 'target_date', 1) : null;
  if (date) {
    var matched = String(date).match(/(\d{4})[-/](\d{2})/);
    if (matched) {
      return matched[1] + '-' + matched[2];
    }
  }
  throw new Error('対象月を特定できない。Target_data の target_term / target_date を確認する');
}

function ensureFolder_(parent, name) {
  var found = parent.getFoldersByName(name);
  return found.hasNext() ? found.next() : parent.createFolder(name);
}

function uniqueName_(folder, baseName, extension) {
  var name = baseName + extension;
  var suffix = 2;
  while (folder.getFilesByName(name).hasNext()) {
    name = baseName + '_' + suffix + extension;
    suffix += 1;
  }
  return name;
}

// ---------------------------------------------------------------------------
// 認証とレスポンス
// ---------------------------------------------------------------------------

function requireToken_(given) {
  var expected = PropertiesService.getScriptProperties().getProperty('OMS_ENDPOINT_TOKEN');
  if (!expected) {
    throw new Error('スクリプトプロパティ OMS_ENDPOINT_TOKEN が未設定');
  }
  if (!given || !safeEquals_(String(given), expected)) {
    throw new Error('トークンが一致しない');
  }
}

/** 比較にかかる時間から推測されないよう、長さに依存しない比較をする。 */
function safeEquals_(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  var diff = 0;
  for (var i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

function json_(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(ContentService.MimeType.JSON);
}

// ---------------------------------------------------------------------------
// 時間主導トリガー（呼び出しが失敗しても月初のデータが揃うようにする保険）
// ---------------------------------------------------------------------------

/** 一度だけ手で実行して、毎月1日の自動更新を仕掛ける。 */
function installMonthlyTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'monthlyRefresh') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  ScriptApp.newTrigger('monthlyRefresh').timeBased().onMonthDay(1).atHour(7).create();
}

function monthlyRefresh() {
  ['refresh_master', 'refresh_bq', 'create_csv'].forEach(runAction_);
  if (SNAPSHOT_FOLDER_ID) {
    snapshotCreateCsv_();
  }
}
