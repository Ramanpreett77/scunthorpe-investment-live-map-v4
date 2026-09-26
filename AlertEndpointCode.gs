/**
 * PUBLIC ALERT REGISTRATION ENDPOINT — Google Apps Script
 *
 * This project only appends validated rows. It does not read the Sheet and
 * every response body is blank. Handles two public forms, routed by
 * data.kind: investor deal-alert registrations (default / kind absent) and
 * seller leads (kind:'seller'). Seller leads are dual-written: full detail
 * row to the SellerLeads tab (archive) plus a mapped row to the Pipeline
 * tab (stage=Lead) so they appear in the private admin kanban immediately.
 * Set these Script Properties:
 *   SPREADSHEET_ID           the ID of the Google Sheet used for all tabs
 *   ALERTS_SHEET_NAME        optional; defaults to Alerts
 *   SELLER_LEADS_SHEET_NAME  optional; defaults to SellerLeads
 *   PIPELINE_SHEET_NAME      optional; defaults to Pipeline
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
    if (data && data.kind === 'seller') return handleSellerLead_(data);
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

function handleSellerLead_(data) {
  try {
    if (!sellerValid_(data)) return blank_();
    var email = String(data.email).trim().toLowerCase();
    var key = 'seller_' + sha256_(email);
    var cache = CacheService.getScriptCache();
    if (cache.get(key)) return blank_();
    cache.put(key, '1', 60);

    var lock = LockService.getScriptLock();
    lock.waitLock(5000);
    try {
      // 1) Full detail row -> SellerLeads tab (record of archive).
      var sheet = getSellerLeadsSheet_();
      sheet.appendRow([
        new Date(),
        clean_(data.name, 100),
        clean_(email, 254),
        clean_(data.phone, 40),
        clean_(data.address, 300),
        clean_(data.situation, 80),
        clean_(data.timeframe, 80),
        clean_(data.notes, 1000),
        true,
        'new'
      ]);
      // 2) Working copy -> Pipeline tab (stage=Lead) so the private admin
      // kanban picks it up. SellerLeads stays the record of archive.
      var pipeline = getPipelineSheet_();
      var motive = clean_(data.situation, 80) + ' (' + clean_(data.timeframe, 80) + ')';
      var contact = [clean_(data.name, 100), clean_(email, 254), clean_(data.phone, 40)]
        .filter(function (x) { return !!x; }).join(' | ');
      var pnotes = contact;
      if (String(data.notes || '').trim()) {
        pnotes += (pnotes ? ' — ' : '') + 'Notes: ' + clean_(data.notes, 1000);
      }
      pipeline.appendRow([
        'Lead',
        clean_(data.address, 300),
        'Website sell form',
        motive,
        '', '', '',
        '',
        pnotes.slice(0, 1500)
      ]);
    } finally {
      lock.releaseLock();
    }
  } catch (err) {
    // Do not disclose validation, Sheet or server details to the public client.
  }
  return blank_();
}

function sellerValid_(data) {
  if (!data || data.website) return false;
  var name = String(data.name || '').trim();
  var email = String(data.email || '').trim();
  var phone = String(data.phone || '').trim();
  var address = String(data.address || '').trim();
  var situation = String(data.situation || '').trim();
  var timeframe = String(data.timeframe || '').trim();
  var notes = String(data.notes || '');
  var situations = ['Probate / inheritance', 'Facing repossession or mortgage arrears', 'Relocating quickly',
    'Divorce or separation', 'Problem tenant / hard to manage', 'Property needs too much work to sell normally',
    'Just exploring my options', 'Other'];
  var timeframes = ['As soon as possible (within 4 weeks)', '1–3 months', '3–6 months', 'Just exploring, no fixed timeframe'];
  return name.length >= 2 && name.length <= 100 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254 &&
    phone.length <= 40 && address.length >= 8 && address.length <= 300 &&
    situations.indexOf(situation) !== -1 && timeframes.indexOf(timeframe) !== -1 &&
    notes.length <= 1000 && data.consent === true;
}

function getSellerLeadsSheet_() {
  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured.');
  var ss = SpreadsheetApp.openById(id);
  var name = PropertiesService.getScriptProperties().getProperty('SELLER_LEADS_SHEET_NAME') || 'SellerLeads';
  var sheet = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, 10).setValues([['timestamp', 'name', 'email', 'phone', 'address', 'situation', 'timeframe', 'notes', 'consent', 'status']]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getPipelineSheet_() {
  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured.');
  var ss = SpreadsheetApp.openById(id);
  var name = PropertiesService.getScriptProperties().getProperty('PIPELINE_SHEET_NAME') || 'Pipeline';
  var sheet = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, 9).setValues([['stage', 'address', 'lead_source', 'seller_motive', 'asking_price', 'agreed_price', 'fee', 'follow_up_date', 'notes']]);
    sheet.setFrozenRows(1);
  }
  return sheet;
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
