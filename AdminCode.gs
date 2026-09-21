/**
 * PRIVATE ADMIN APP — Google Apps Script
 *
 * Script Properties required:
 *   SPREADSHEET_ID       the ID of the Google Sheet used for admin data
 *
 * Optional Script Properties:
 *   DEALS_SHEET_NAME     defaults to Deals
 *   ALERTS_SHEET_NAME    defaults to Alerts
 *   PIPELINE_SHEET_NAME  defaults to Pipeline
 *   SELLERS_SHEET_NAME   defaults to Sellers
 *   SEND_LOG_SHEET_NAME  defaults to SendLog
 *   VIEWINGS_SHEET_NAME  defaults to Viewings
 *   VIEWING_DRIVE_FOLDER_ID  Drive folder ID used for viewing photos
 *   PUBLIC_SITE_URL      optional public URL used by the refurb hand-off link
 *
 * Deploy this project as a web app with Execute as: Me and access: Only myself.
 * The Sheet ID is deliberately read from Script Properties, not stored here.
 */

var PIPELINE_STAGES_ = ['Lead', 'Viewed', 'Offered', 'Agreed', 'Packaged', 'Sent', 'Reserved', 'Completed', 'Lost'];

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Admin')
    .setTitle('Private property sourcing admin');
}

function getDashboardData() {
  return {
    deals: readTable_(sheetName_('DEALS_SHEET_NAME', 'Deals')),
    alerts: readTable_(sheetName_('ALERTS_SHEET_NAME', 'Alerts')),
    pipeline: readTable_(sheetName_('PIPELINE_SHEET_NAME', 'Pipeline')),
    sellers: readTable_(sheetName_('SELLERS_SHEET_NAME', 'Sellers')),
    sendLog: readTable_(sheetName_('SEND_LOG_SHEET_NAME', 'SendLog'), 100),
    viewings: readTable_(sheetName_('VIEWINGS_SHEET_NAME', 'Viewings'), 50),
    publicSiteUrl: PropertiesService.getScriptProperties().getProperty('PUBLIC_SITE_URL') || ''
  };
}

/* ----------------------------- Deals ---------------------------------- */

function saveDeal(deal) {
  if (!deal || typeof deal !== 'object') throw new Error('Deal data is missing.');
  var headers = dealHeaders_();
  var clean = {};
  headers.forEach(function (header) { clean[header] = cleanCell_(deal[header]); });
  if (!clean.slug || !clean.addr) throw new Error('Slug and address are required.');
  if (!/^[a-z0-9-]{1,120}$/.test(String(clean.slug))) {
    throw new Error('Slug must contain lower-case letters, numbers and hyphens only.');
  }
  var sheet = getSheet_(sheetName_('DEALS_SHEET_NAME', 'Deals'));
  headers.forEach(function (header) { ensureHeader_(sheet, header); });
  writeRow_(sheet, headers, clean, deal._rowNumber);
  return {ok: true};
}

function deleteDeal(rowNumber) {
  deleteRow_(sheetName_('DEALS_SHEET_NAME', 'Deals'), rowNumber);
  return {ok: true};
}

function dealHeaders_() {
  return ['slug', 'addr', 'status', 'guide', 'fee', 'refurb', 'rent', 'gdv', 'comp_price', 'data_confidence', 'beds', 'type', 'strategy', 'zone', 'lat', 'lon', 'blurb', 'note', 'source', 'source_url', 'auction_date', 'image', 'hide_address'];
}

/* -------------------------- Alert investors ---------------------------- */

function updateAlertStatus(rowNumber, status) {
  var sheet = getSheet_(sheetName_('ALERTS_SHEET_NAME', 'Alerts'));
  var n = validRow_(sheet, rowNumber);
  var column = ensureHeader_(sheet, 'status');
  var allowed = ['new', 'contacted', 'opted_out'];
  sheet.getRange(n, column).setValue(allowed.indexOf(status) >= 0 ? status : 'new');
  return {ok: true};
}

function getMatchedInvestors(deal) {
  var rows = readTable_(sheetName_('ALERTS_SHEET_NAME', 'Alerts'));
  var matches = [];
  var consented = 0;
  rows.forEach(function (investor) {
    if (String(investor.consent).toLowerCase() !== 'true' || String(investor.status).toLowerCase() === 'opted_out') return;
    consented++;
    var match = investorMatch_(deal || {}, investor);
    if (match.matched) {
      matches.push({
        rowNumber: investor._rowNumber,
        name: investor.name || 'Contact',
        email: investor.email || '',
        phone: investor.phone || '',
        strategy: investor.strategy || '',
        areas: investor.areas || '',
        reason: match.reason
      });
    }
  });
  return {matches: matches, consented: consented};
}

function prepareInvestorMessage(deal, rowNumber) {
  var investor = alertByRow_(rowNumber);
  assertCanContact_(investor);
  var message = buildInvestorMessage_(deal || {}, investor);
  return {
    rowNumber: investor._rowNumber,
    name: investor.name || 'Contact',
    email: investor.email || '',
    phone: investor.phone || '',
    subject: message.subject,
    body: message.body,
    whatsappUrl: investor.phone ? whatsappUrl_(investor.phone, message.body) : ''
  };
}

function sendInvestorEmail(deal, rowNumber) {
  var investor = alertByRow_(rowNumber);
  assertCanContact_(investor);
  var message = buildInvestorMessage_(deal || {}, investor);
  MailApp.sendEmail({to: investor.email, subject: message.subject, body: message.body});
  appendSendLog_('email', deal || {}, investor, message.subject, 'sent');
  return {ok: true, email: investor.email};
}

function logWhatsAppClick(deal, rowNumber) {
  var investor = alertByRow_(rowNumber);
  assertCanContact_(investor);
  appendSendLog_('whatsapp_click', deal || {}, investor, 'WhatsApp click-to-chat opened', 'clicked');
  return {ok: true};
}

function investorMatch_(deal, investor) {
  var reasons = [];
  var strategy = normaliseStrategy_(deal.strategy);
  var investorStrategy = normaliseStrategy_(investor.strategy);
  var strategyOk = investorStrategy === 'any' || (strategy && investorStrategy && (strategy === investorStrategy || strategy.indexOf(investorStrategy) >= 0 || investorStrategy.indexOf(strategy) >= 0));
  if (strategyOk) reasons.push('strategy matches (' + (investor.strategy || 'any') + ')');
  else return {matched: false, reason: ''};

  var price = numeric_(deal.guide);
  var min = numeric_(investor.budgetMin);
  var max = numeric_(investor.budgetMax);
  var budgetOk = price !== null && (min === null || price >= min) && (max === null || price <= max);
  if (budgetOk) reasons.push('price ' + money_(price) + ' is within budget');
  else return {matched: false, reason: ''};

  var searchText = String((deal.addr || '') + ' ' + (deal.zone || '')).toUpperCase();
  var areas = String(investor.areas || '').split(',').map(function (x) { return x.trim().toUpperCase(); }).filter(Boolean);
  var areaOk = areas.length > 0 && areas.some(function (area) { return searchText.indexOf(area) >= 0; });
  if (areaOk) reasons.push('area matches ' + areas.join(', '));
  else return {matched: false, reason: ''};
  return {matched: true, reason: reasons.join('; ') + '.'};
}

function normaliseStrategy_(value) {
  var text = String(value || '').toLowerCase();
  if (!text || text === 'any') return text ? 'any' : '';
  if (text.indexOf('hmo') >= 0) return 'hmo';
  if (text.indexOf('brrr') >= 0) return 'brrr';
  if (text.indexOf('r2sa') >= 0 || text.indexOf('sa') >= 0) return 'r2sa';
  if (text.indexOf('flip') >= 0) return 'flip';
  if (text.indexOf('buy to rent') >= 0 || text.indexOf('btl') >= 0) return 'btl';
  return text;
}

function buildInvestorMessage_(deal, investor) {
  var address = deal.addr || 'this property';
  var strategy = deal.strategy || 'property investment';
  var price = numeric_(deal.guide);
  var priceLine = price === null ? '' : '\nGuide price: ' + money_(price);
  var source = deal.source_url ? '\nSource/details: ' + deal.source_url : '';
  var body = 'Hi ' + (investor.name || 'there') + ',\n\n' +
    'I have a ' + strategy + ' opportunity that may fit your stated criteria.\n' +
    'Address: ' + address + priceLine + source + '\n\n' +
    'Please carry out your own due diligence. Figures are illustrative and this is sourcing information only, not financial or investment advice.\n\n' +
    'If you no longer want deal alerts, reply STOP and I will update your preferences.\n\n' +
    'Regards';
  return {subject: 'Property opportunity: ' + address, body: body};
}

function assertCanContact_(investor) {
  if (!investor || String(investor.consent).toLowerCase() !== 'true') throw new Error('This contact has not given consent.');
  if (String(investor.status).toLowerCase() === 'opted_out') throw new Error('This contact has opted out.');
  if (!investor.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(investor.email))) throw new Error('This contact has no valid email.');
}

function alertByRow_(rowNumber) {
  var sheet = getSheet_(sheetName_('ALERTS_SHEET_NAME', 'Alerts'));
  var n = validRow_(sheet, rowNumber);
  var values = sheet.getRange(n, 1, 1, sheet.getLastColumn()).getDisplayValues()[0];
  var headers = headerRow_(sheet);
  var item = {_rowNumber: n};
  headers.forEach(function (header, i) { if (header) item[header] = values[i] || ''; });
  return item;
}

function whatsappUrl_(phone, body) {
  var digits = String(phone || '').replace(/[^0-9+]/g, '');
  if (digits.charAt(0) === '+') digits = digits.slice(1);
  if (digits.indexOf('0') === 0) digits = '44' + digits.slice(1);
  if (digits.length < 10) return '';
  return 'https://wa.me/' + digits + '?text=' + encodeURIComponent(body);
}

function appendSendLog_(channel, deal, investor, subject, result) {
  var sheet = getSheet_(sheetName_('SEND_LOG_SHEET_NAME', 'SendLog'));
  sheet.appendRow([new Date(), channel, cleanCell_(deal.slug || ''), cleanCell_(deal.addr || ''), investor._rowNumber || '', cleanCell_(investor.email || ''), cleanCell_(subject || ''), result]);
}

/* --------------------------- Pipeline --------------------------------- */

function savePipelineItem(item) {
  if (!item || !item.address) throw new Error('Pipeline address is required.');
  if (PIPELINE_STAGES_.indexOf(String(item.stage)) < 0) throw new Error('Invalid pipeline stage.');
  var headers = pipelineHeaders_();
  var clean = {};
  headers.forEach(function (header) { clean[header] = cleanCell_(item[header]); });
  writeRow_(getSheet_(sheetName_('PIPELINE_SHEET_NAME', 'Pipeline')), headers, clean, item._rowNumber);
  return {ok: true};
}

function updatePipelineStage(rowNumber, stage) {
  if (PIPELINE_STAGES_.indexOf(String(stage)) < 0) throw new Error('Invalid pipeline stage.');
  var sheet = getSheet_(sheetName_('PIPELINE_SHEET_NAME', 'Pipeline'));
  var row = validRow_(sheet, rowNumber);
  sheet.getRange(row, ensureHeader_(sheet, 'stage')).setValue(stage);
  return {ok: true};
}

function deletePipelineItem(rowNumber) {
  deleteRow_(sheetName_('PIPELINE_SHEET_NAME', 'Pipeline'), rowNumber);
  return {ok: true};
}

function pipelineHeaders_() {
  return ['stage', 'address', 'lead_source', 'seller_motive', 'asking_price', 'agreed_price', 'fee', 'follow_up_date', 'notes'];
}

/* ----------------------- Motivated sellers ---------------------------- */

function saveSeller(item) {
  if (!item || !item.address) throw new Error('Seller address is required.');
  var headers = sellerHeaders_();
  var clean = {};
  headers.forEach(function (header) { clean[header] = cleanCell_(item[header]); });
  writeRow_(getSheet_(sheetName_('SELLERS_SHEET_NAME', 'Sellers')), headers, clean, item._rowNumber);
  return {ok: true};
}

function deleteSeller(rowNumber) {
  deleteRow_(sheetName_('SELLERS_SHEET_NAME', 'Sellers'), rowNumber);
  return {ok: true};
}

function importSellers(rows) {
  if (!Array.isArray(rows) || rows.length > 500) throw new Error('Import must contain between 1 and 500 rows.');
  var sheet = getSheet_(sheetName_('SELLERS_SHEET_NAME', 'Sellers'));
  var headers = sellerHeaders_();
  var values = rows.map(function (item) {
    return headers.map(function (header) { return cleanCell_(item[header]); });
  }).filter(function (row) { return row[0]; });
  if (!values.length) throw new Error('No seller rows with an address were found.');
  sheet.getRange(sheet.getLastRow() + 1, 1, values.length, headers.length).setValues(values);
  return {ok: true, count: values.length};
}

function sellerHeaders_() {
  return ['address', 'postcode', 'days_on_market', 'price_reductions_count', 'price_reduction_pct', 'probate', 'vacant', 'repossession_auction', 'tired_landlord', 'notes'];
}

/* -------------------------- Mobile viewings --------------------------- */

function saveViewing(payload) {
  if (!payload || !payload.viewing || !payload.viewing.address) throw new Error('Viewing address is required.');
  var folderId = PropertiesService.getScriptProperties().getProperty('VIEWING_DRIVE_FOLDER_ID');
  var photos = Array.isArray(payload.photos) ? payload.photos.slice(0, 10) : [];
  if (photos.length && !folderId) throw new Error('VIEWING_DRIVE_FOLDER_ID is not set in Script Properties.');
  var photoUrls = [];
  if (photos.length) {
    var folder = DriveApp.getFolderById(folderId);
    photos.forEach(function (photo, index) {
      if (!photo || !photo.base64) return;
      var base64 = String(photo.base64);
      if (base64.length > 8000000) throw new Error('Photo '+(index + 1)+' is too large after compression.');
      var bytes = Utilities.base64Decode(base64);
      var mime = String(photo.mimeType || 'image/jpeg').slice(0, 80);
      var filename = safeFilename_(photo.name || ('viewing-photo-'+(index + 1)+'.jpg'));
      var file = folder.createFile(Utilities.newBlob(bytes, mime, filename));
      photoUrls.push(file.getUrl());
    });
  }
  var v = payload.viewing;
  var headers = viewingHeaders_();
  var row = {
    timestamp: new Date(),
    viewing_id: cleanCell_(v.viewing_id),
    address: cleanCell_(v.address),
    postcode: cleanCell_(v.postcode),
    viewing_date: cleanCell_(v.viewing_date),
    deal_slug: cleanCell_(v.deal_slug),
    roof: cleanCell_(v.roof),
    damp: cleanCell_(v.damp),
    wiring: cleanCell_(v.wiring),
    plumbing: cleanCell_(v.plumbing),
    heating: cleanCell_(v.heating),
    windows: cleanCell_(v.windows),
    structure: cleanCell_(v.structure),
    layout: cleanCell_(v.layout),
    access: cleanCell_(v.access),
    neighbours: cleanCell_(v.neighbours),
    notes: cleanCell_(v.notes),
    refurb_total: cleanCell_(v.refurb_total),
    photo_urls: cleanCell_(photoUrls.join('\n'))
  };
  getSheet_(sheetName_('VIEWINGS_SHEET_NAME', 'Viewings')).appendRow(headers.map(function (h) { return row[h] || ''; }));
  return {ok: true, photoCount: photoUrls.length, viewingId: v.viewing_id || ''};
}

function viewingHeaders_() {
  return ['timestamp', 'viewing_id', 'address', 'postcode', 'viewing_date', 'deal_slug', 'roof', 'damp', 'wiring', 'plumbing', 'heating', 'windows', 'structure', 'layout', 'access', 'neighbours', 'notes', 'refurb_total', 'photo_urls'];
}

function safeFilename_(name) {
  return String(name).replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 120) || 'viewing-photo.jpg';
}

/* ---------------------------- Sheets ---------------------------------- */

function readTable_(sheetName, limit) {
  var sheet = getSheet_(sheetName);
  var values = sheet.getDataRange().getDisplayValues();
  if (!values.length) return [];
  var headers = values[0].map(function (h) { return String(h).trim(); });
  var rows = values.slice(1).map(function (row, offset) {
    var item = {_rowNumber: offset + 2};
    headers.forEach(function (header, i) { if (header) item[header] = row[i] || ''; });
    return item;
  }).filter(function (item) {
    return Object.keys(item).some(function (key) { return key !== '_rowNumber' && item[key] !== ''; });
  });
  if (limit && rows.length > limit) rows = rows.slice(rows.length - limit);
  return rows;
}

function headerRow_(sheet) {
  var lastColumn = Math.max(sheet.getLastColumn(), 1);
  return sheet.getRange(1, 1, 1, lastColumn).getDisplayValues()[0].map(function (h) {
    return String(h).trim().toLowerCase();
  });
}

function getSheet_(name) {
  var spreadsheetId = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!spreadsheetId) throw new Error('SPREADSHEET_ID is not set in Script Properties.');
  var ss = SpreadsheetApp.openById(spreadsheetId);
  var sheet = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sheet.getLastRow() === 0) {
    var headers = headersForSheet_(name);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function headersForSheet_(name) {
  if (name === sheetName_('DEALS_SHEET_NAME', 'Deals')) return dealHeaders_();
  if (name === sheetName_('ALERTS_SHEET_NAME', 'Alerts')) return ['timestamp', 'name', 'email', 'phone', 'strategy', 'budgetMin', 'budgetMax', 'areas', 'deal', 'consent', 'status'];
  if (name === sheetName_('PIPELINE_SHEET_NAME', 'Pipeline')) return pipelineHeaders_();
  if (name === sheetName_('SELLERS_SHEET_NAME', 'Sellers')) return sellerHeaders_();
  if (name === sheetName_('SEND_LOG_SHEET_NAME', 'SendLog')) return ['timestamp', 'channel', 'deal_slug', 'address', 'investor_row', 'investor_email', 'subject', 'result'];
  if (name === sheetName_('VIEWINGS_SHEET_NAME', 'Viewings')) return viewingHeaders_();
  return [];
}

function sheetName_(property, fallback) {
  return PropertiesService.getScriptProperties().getProperty(property) || fallback;
}

function ensureHeader_(sheet, header) {
  var headers = headerRow_(sheet);
  var index = headers.indexOf(String(header).toLowerCase());
  if (index >= 0) return index + 1;
  var column = Math.max(sheet.getLastColumn(), 0) + 1;
  sheet.getRange(1, column).setValue(header);
  return column;
}

function writeRow_(sheet, headers, clean, rowNumber) {
  var n = Number(rowNumber || 0);
  var row = headers.map(function (header) { return clean[header] || ''; });
  if (n >= 2 && n <= sheet.getLastRow()) sheet.getRange(n, 1, 1, headers.length).setValues([row]);
  else sheet.appendRow(row);
}

function validRow_(sheet, rowNumber) {
  var n = Number(rowNumber);
  if (!Number.isInteger(n) || n < 2 || n > sheet.getLastRow()) throw new Error('Invalid Sheet row.');
  return n;
}

function deleteRow_(sheetName, rowNumber) {
  var sheet = getSheet_(sheetName);
  sheet.deleteRow(validRow_(sheet, rowNumber));
}

function numeric_(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  var n = Number(String(value).replace(/[^0-9.\-]/g, ''));
  return isNaN(n) ? null : n;
}

function money_(value) {
  return '£' + Math.round(Number(value) || 0).toLocaleString('en-GB');
}

function cleanCell_(value) {
  if (value === null || value === undefined) return '';
  var text = String(value).trim().slice(0, 2000);
  if (/^[=+\-@]/.test(text)) return "'" + text;
  return text;
}
