/**
 * PUBLIC ALERT REGISTRATION ENDPOINT — Google Apps Script
 *
 * This project only appends validated alert registrations. It does not read
 * the Sheet and every response body is blank. Set this Script Property:
 *   SPREADSHEET_ID       the ID of the Google Sheet used for alert rows
 *   ALERTS_SHEET_NAME    optional; defaults to Alerts
 *
 * Deploy as a web app with Execute as: Me and Who has access: Anyone.
 * Keep this project separate from the private admin project.
 */

function doGet() {
  return blank_();
}

function doPost(e) {
  try {
    var raw = e && e.postData && e.postData.contents ? e.postData.contents : '';
    var data = JSON.parse(raw || '{}');
    if (!valid_(data)) return blank_();
    var email = String(data.email).trim().toLowerCase();
    var key = 'alert_' + sha256_(email);
    var cache = CacheService.getScriptCache();
    if (cache.get(key)) return blank_();
    cache.put(key, '1', 60);

    var lock = LockService.getScriptLock();
    lock.waitLock(5000);
    try {
      var sheet = getAlertsSheet_();
      sheet.appendRow([
        new Date(),
        clean_(data.name, 100),
        clean_(email, 254),
        clean_(data.phone, 40),
        clean_(data.strategy, 30),
        Number(data.budgetMin),
        Number(data.budgetMax),
        clean_(data.areas, 200),
        clean_(data.deal, 300),
        true,
        'new'
      ]);
    } finally {
      lock.releaseLock();
    }
  } catch (err) {
    // Do not disclose validation, Sheet or server details to the public client.
  }
  return blank_();
}

function valid_(data) {
  if (!data || data.website) return false;
  var name = String(data.name || '').trim();
  var email = String(data.email || '').trim();
  var phone = String(data.phone || '').trim();
  var areas = String(data.areas || '').trim();
  var strategy = String(data.strategy || '').trim();
  var min = Number(data.budgetMin);
  var max = Number(data.budgetMax);
  var strategies = ['Any', 'HMO Small', 'BRRR', 'Buy to Rent', 'Flip', 'R2SA'];
  return name.length >= 2 && name.length <= 100 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254 &&
    phone.length <= 40 && areas.length >= 1 && areas.length <= 200 &&
    strategies.indexOf(strategy) !== -1 && Number.isFinite(min) && Number.isFinite(max) &&
    min >= 0 && max >= min && max <= 100000000 && data.consent === true;
}

function getAlertsSheet_() {
  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured.');
  var ss = SpreadsheetApp.openById(id);
  var name = PropertiesService.getScriptProperties().getProperty('ALERTS_SHEET_NAME') || 'Alerts';
  var sheet = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, 11).setValues([['timestamp', 'name', 'email', 'phone', 'strategy', 'budgetMin', 'budgetMax', 'areas', 'deal', 'consent', 'status']]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function clean_(value, limit) {
  var text = String(value || '').trim().slice(0, limit);
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function sha256_(value) {
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, value, Utilities.Charset.UTF_8);
  return bytes.map(function (b) { var v = b < 0 ? b + 256 : b; return ('0' + v.toString(16)).slice(-2); }).join('');
}

function blank_() {
  return ContentService.createTextOutput('');
}
