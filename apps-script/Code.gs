/**
 * ============================================================================
 *  WEEKLY DEAL DIGEST — Google Apps Script  (copy this whole file)
 *  Site: https://ramanpreett77.github.io/scunthorpe-investment-live-map-v4/
 *
 *  WHAT THIS DOES
 *    doPost(e)          receives the website's alert form, stores the
 *                       subscriber in a "Subscribers" sheet, rejects spam.
 *    doGet(e)           handles the ?unsub=TOKEN link at the foot of every
 *                       email and marks that subscriber Unsubscribed.
 *    sendTest()         emails the digest to YOU only — run this first.
 *    sendNewsletter()   emails the digest to every Active subscriber.
 *                       Put this on a weekly trigger (Monday 8am).
 *
 *  SETUP (short version — full click-by-click steps are in
 *  NEWSLETTER-SETUP.md in the website repository)
 *    1. Create a Google Sheet. Extensions -> Apps Script. Paste this file in.
 *    2. Project Settings -> Script Properties -> add OPENAI_API_KEY with a
 *       NEW OpenAI key. Never put a key in the website files.
 *    3. Fill in BUSINESS_FOOTER below (your identity + address for emails).
 *    4. Deploy -> New deployment -> Web app.
 *       Execute as: Me.  Who has access: Anyone.  Copy the /exec URL.
 *    5. Paste that URL into config.js as alertEndpoint and commit.
 *    6. Triggers -> Add trigger -> sendNewsletter, Week timer, Monday 8am.
 *
 *  NOTES
 *    * No secret is stored in this file. The OpenAI key is read from Script
 *      Properties at run time and never written anywhere.
 *    * Subscriber personal data is NEVER sent to OpenAI. The digest is written
 *      from public deal data only, then the same body is sent to everyone.
 *    * Sheet columns: Timestamp | Name | Email | Phone | Strategy | BudgetMin |
 *      BudgetMax | Areas | Consent | Token | Status | Source
 *      ('Source' is 'blog' or 'deal-map'; added automatically at the END of
 *      existing sheets so old rows stay intact.)
 *    * Free Gmail sends about 100 emails/day; Google Workspace about 1,500.
 *      Above roughly 100 subscribers, move to a proper email platform
 *      (e.g. ConvertKit/Mailchimp) — see NEWSLETTER-SETUP.md.
 * ============================================================================
 */

// ----------------------------------------------------------------- constants
// REQUIRED: the deploy-time URL of this web app, used to build unsubscribe
// links. Leave empty and the script reads it from the deployment automatically;
// set it only if your unsubscribe links ever come out wrong.
var WEB_APP_URL = '';

// REQUIRED: your business identity — emails must say who they are from.
// Replace every part of this. It is the footer of every email sent.
var BUSINESS_FOOTER =
  'PASTE YOUR BUSINESS DETAILS HERE — e.g. "SGJM Property Investment Insights, ' +
  'operated by YOUR NAME (sole trader), YOUR BUSINESS ADDRESS, email YOUR EMAIL.' +
  ' You are receiving this because you registered for deal alerts on the ' +
  'Scunthorpe Deal Map. This is sourcing information, not financial advice."';

// Public site + the deals file the digest is written from.
var SITE_URL   = 'https://ramanpreett77.github.io/scunthorpe-investment-live-map-v4/';
var DATA_URL   = SITE_URL + 'data/auction-stock.json';
var FEED_URL   = SITE_URL + 'blog/feed.xml';   // fallback when the auctions are quiet
var MAP_URL    = SITE_URL;

// Sheet + AI settings
var SHEET_NAME      = 'Subscribers';
var OPENAI_MODEL    = 'gpt-4o-mini';
var OPENAI_TEMPERATURE = 0.3;
var EMAIL_SUBJECT   = 'Your weekly Scunthorpe deal digest';
var MAX_LOTS_IN_PROMPT = 12;   // trimmed before sending to the AI
var MAX_POSTS_IN_PROMPT = 5;   // blog fallback: newest posts only
var EMAIL_BATCH_BUFFER = 5;    // stop this many emails short of the daily quota

// ============================================================================
//  FORM ENDPOINT
// ============================================================================

/** Receives the website form. Returns JSON: {ok:true} or {ok:false,error}. */
function doPost(e) {
  try {
    var data = parseBody_(e);

    // Honeypot: a real visitor never fills this in. Accept silently, store nothing.
    if (String(data.website || data.url || '').trim() !== '') {
      return json_({ ok: true });
    }

    var email = String(data.email || '').trim();
    var name  = String(data.name || '').trim();
    var consent = data.consent === true || String(data.consent).toLowerCase() === 'true';

    if (!isEmail_(email)) return json_({ ok: false, error: 'Please enter a valid email address.' });
    if (!consent)         return json_({ ok: false, error: 'Please tick the consent box so we can email you.' });
    if (name.length > 100) name = name.substring(0, 100);   // name is optional (blog form)

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      var sheet = getSubscribersSheet_();
      var found = findRowByEmail_(sheet, email);

      if (found.row > 0) {
        // Already on the list: do not duplicate. If they had unsubscribed,
        // submitting the form again is fresh consent, so reactivate.
        if (String(sheet.getRange(found.row, 11).getValue()).toLowerCase() === 'unsubscribed') {
          sheet.getRange(found.row, 11).setValue('Active');
          sheet.getRange(found.row, 1).setValue(new Date());
          return json_({ ok: true });
        }
        return json_({ ok: true });
      }

      sheet.appendRow([
        new Date(),                                            // 1 Timestamp
        name.substring(0, 100),                                // 2 Name
        email.substring(0, 254),                               // 3 Email
        String(data.phone || '').substring(0, 40),             // 4 Phone
        String(data.strategy || '').substring(0, 40),          // 5 Strategy
        numberOrBlank_(data.budgetMin),                        // 6 BudgetMin
        numberOrBlank_(data.budgetMax),                        // 7 BudgetMax
        String(data.areas || '').substring(0, 200),            // 8 Areas
        'Yes',                                                 // 9 Consent
        Utilities.getUuid(),                                   // 10 Token
        'Active',                                              // 11 Status
        String(data.source || '').substring(0, 40)             // 12 Source
      ]);
      return json_({ ok: true });
    } finally {
      lock.releaseLock();
    }
  } catch (err) {
    return json_({ ok: false, error: 'The registration service had a problem — please try again.' });
  }
}

/** Handles the unsubscribe link: ?unsub=TOKEN */
function doGet(e) {
  var token = String((e && e.parameter && e.parameter.unsub) || '').trim();
  if (!token) {
    return html_('<h2>Scunthorpe Deal Map</h2><p>This address is used by the weekly ' +
                 'deal digest emails. Nothing to see here.</p>');
  }
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sheet = getSubscribersSheet_();
    var row = findRowByToken_(sheet, token);
    if (row > 0) {
      sheet.getRange(row, 11).setValue('Unsubscribed');
      return html_('<h2>You have been unsubscribed</h2><p>You will not receive any more ' +
                   'deal digest emails. Sorry to see you go.</p><p><a href="' + MAP_URL +
                   '">Back to the Scunthorpe Deal Map</a></p>');
    }
    return html_('<h2>Link not recognised</h2><p>This unsubscribe link has already been ' +
                 'used, or it is not valid. If you are still getting emails, reply to one ' +
                 'and I will remove you by hand.</p>');
  } finally {
    lock.releaseLock();
  }
}

// ============================================================================
//  NEWSLETTER
// ============================================================================

/**
 * Builds the digest body from the public deals file using OpenAI.
 * Only public deal/blog data is sent — never subscriber details.
 * When the auctions hold zero usable lots it falls back to the newest blog
 * posts instead. Returns the inner HTML, or null when BOTH sources are empty
 * (callers must then skip sending and log why).
 */
function generateNewsletter_() {
  var key = PropertiesService.getScriptProperties().getProperty('OPENAI_API_KEY');
  if (!key) throw new Error('OPENAI_API_KEY is not set in Script Properties.');

  var deals = fetchDeals_();
  var prompt;

  if (deals.count > 0) {
    prompt =
      'You write a short weekly property deal digest email for investors looking at ' +
      'Scunthorpe and North Lincolnshire, UK.\n\n' +
      'STRICT RULES:\n' +
      '- Use ONLY the data supplied below. Do not invent, estimate or embellish any ' +
      'price, yield, rent, address, date or figure that is not in the data.\n' +
      '- Never promise returns, guarantees or outcomes.\n' +
      '- If the data contains no opportunities, say so plainly and briefly instead of ' +
      'inventing any.\n' +
      '- Write in plain British English, second person, no hype.\n\n' +
      'OUTPUT FORMAT — return only HTML using <h2>, <p>, <ul>, <li> and <strong>. ' +
      'No <html>, <body>, <head>, <style>, <a> or markdown.\n' +
      '1. An <h2> heading.\n' +
      '2. A two-sentence intro <p>.\n' +
      '3. Up to 5 opportunities, each as: <li><strong>address</strong> — guide price, ' +
      'strategy fit, one reason to look, and one thing to check (legal pack, tenure, ' +
      'refurb condition or auction date).</li>\n' +
      '4. A final <p> saying this is sourcing information and not financial advice, ' +
      'and that figures must be verified on the lot page and legal pack.\n\n' +
      'DATA (public auction stock, checked ' + deals.checked + '):\n' + deals.text;
  } else {
    // Quiet auctions: round up the newest blog posts instead of sending an
    // empty digest or inventing content.
    var posts = fetchBlogPosts_();
    if (!posts.items.length) return null;
    var lines = posts.items.map(function (p) {
      return '- ' + p.title + '\n  URL: ' + p.link + '\n  Summary: ' + (p.desc || '(no summary)') ;
    }).join('\n');
    prompt =
      'You write a short weekly property email for investors looking at ' +
      'Scunthorpe and North Lincolnshire, UK. This week the auctions are quiet, ' +
      'so the email rounds up the newest articles from the SGJM blog instead.\n\n' +
      'STRICT RULES:\n' +
      '- Use ONLY the data supplied below. Do not invent, estimate or embellish any ' +
      'price, yield, rent, address, date or figure that is not in the data.\n' +
      '- Never promise returns, guarantees or outcomes.\n' +
      '- Write in plain British English, second person, no hype.\n\n' +
      'OUTPUT FORMAT — return only HTML using <h2>, <p>, <ul>, <li>, <strong> and <a>. ' +
      'No <html>, <body>, <head>, <style> or markdown.\n' +
      '1. An <h2> heading.\n' +
      '2. A short intro <p> saying the auctions are quiet this week so here is useful reading instead.\n' +
      '3. One <li> per article: the <strong>title</strong> linked to its URL with <a>, ' +
      'then a 1-2 sentence summary drawn only from its supplied summary.\n' +
      '4. A final <p> saying this is sourcing information and not financial advice.\n\n' +
      'DATA (newest SGJM blog posts' +
      (posts.checked ? ', feed built ' + posts.checked : '') + '):\n' + lines;
  }

  var res = UrlFetchApp.fetch('https://api.openai.com/v1/chat/completions', {
    method: 'post',
    contentType: 'application/json',
    muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + key },
    payload: JSON.stringify({
      model: OPENAI_MODEL,
      temperature: OPENAI_TEMPERATURE,
      messages: [
        { role: 'system', content: 'You write factual property sourcing emails. You never invent data.' },
        { role: 'user', content: prompt }
      ]
    })
  });

  var code = res.getResponseCode();
  if (code !== 200) {
    throw new Error('OpenAI returned HTTP ' + code + ': ' + res.getContentText().substring(0, 200));
  }
  var body = JSON.parse(res.getContentText());
  var html = body && body.choices && body.choices[0] &&
             body.choices[0].message && body.choices[0].message.content;
  if (!html) throw new Error('OpenAI returned no content.');
  return sanitise_(html);
}

/** Wraps a digest body with the header link, business footer and unsubscribe link. */
function buildEmail_(bodyHtml, token) {
  var unsub = getWebAppUrl_() + '?unsub=' + encodeURIComponent(token);
  return '' +
    '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:640px;margin:0 auto;' +
    'color:#0f172a;line-height:1.6;font-size:15px">' +
      bodyHtml +
      '<p style="margin-top:22px"><a href="' + MAP_URL + '" ' +
      'style="color:#1d4ed8;font-weight:600">See every current lot on the live ' +
      'Scunthorpe Deal Map &rarr;</a></p>' +
      '<hr style="border:none;border-top:1px solid #e2e8f0;margin:22px 0">' +
      '<div style="font-size:12px;color:#64748b">' +
        '<p style="margin:0 0 8px">' + BUSINESS_FOOTER + '</p>' +
        '<p style="margin:0"><a href="' + unsub + '" style="color:#64748b">' +
        'Unsubscribe from these emails</a></p>' +
      '</div>' +
    '</div>';
}

/** Sends one digest to the script owner only. Run this before the first real send. */
function sendTest() {
  var to = Session.getActiveUser().getEmail() || Session.getEffectiveUser().getEmail();
  if (!to) throw new Error('Could not work out your email address for the test send.');
  var body = generateNewsletter_();
  if (!body) {
    throw new Error('Nothing to send: both the auction stock and the blog feed are empty.');
  }
  MailApp.sendEmail({
    to: to,
    subject: '[TEST] ' + EMAIL_SUBJECT,
    htmlBody: buildEmail_(body, 'TEST-TOKEN')
  });
  Logger.log('Test digest sent to ' + to);
  return 'Test digest sent to ' + to;
}

/** Sends the digest to every Active subscriber. Put this on the weekly trigger. */
function sendNewsletter() {
  var sheet = getSubscribersSheet_();
  var last = sheet.getLastRow();
  if (last < 2) {
    Logger.log('No subscribers yet — nothing sent.');
    return 'No subscribers yet — nothing sent.';
  }

  var rows = sheet.getRange(2, 1, last - 1, 11).getValues();
  var recipients = [];
  for (var i = 0; i < rows.length; i++) {
    var email = String(rows[i][2] || '').trim();
    var token = String(rows[i][9] || '').trim();
    var status = String(rows[i][10] || '').trim().toLowerCase();
    if (!isEmail_(email) || status !== 'active') continue;
    if (!token) {                       // repair a missing token rather than skip
      token = Utilities.getUuid();
      sheet.getRange(i + 2, 10).setValue(token);
    }
    recipients.push({ row: i + 2, email: email, token: token });
  }

  if (!recipients.length) {
    Logger.log('No active subscribers — nothing sent.');
    return 'No active subscribers — nothing sent.';
  }

  var quota = MailApp.getRemainingDailyQuota();
  if (quota <= EMAIL_BATCH_BUFFER) {
    Logger.log('Daily email quota nearly used (' + quota + ' left). Nothing sent this run.');
    return 'Daily email quota nearly used (' + quota + ' left). Nothing sent this run.';
  }

  var body = generateNewsletter_();     // written once from public data
  if (!body) {
    Logger.log('Both the auction stock and the blog feed are empty — nothing sent this run.');
    return 'Nothing to send — both the auction stock and the blog feed are empty.';
  }
  var sent = 0, failed = 0;
  for (var j = 0; j < recipients.length; j++) {
    if (sent >= quota - EMAIL_BATCH_BUFFER) {
      Logger.log('Stopped at the daily email limit. ' + (recipients.length - j) + ' subscriber(s) will be picked up next run.');
      break;
    }
    try {
      MailApp.sendEmail({
        to: recipients[j].email,
        subject: EMAIL_SUBJECT,
        htmlBody: buildEmail_(body, recipients[j].token)
      });
      sent++;
    } catch (err) {
      failed++;
      Logger.log('Failed for row ' + recipients[j].row + ': ' + err);
    }
    Utilities.sleep(120);               // gentle on the Gmail rate limiter
  }

  Logger.log('Weekly digest sent to ' + sent + ' subscriber(s)' +
             (failed ? ', ' + failed + ' failed (see log above)' : '') +
             '. ' + MailApp.getRemainingDailyQuota() + ' email(s) left in today\'s quota.');
  return 'Sent to ' + sent + ' subscriber(s).';
}

// ============================================================================
//  HELPERS
// ============================================================================

function getSubscribersSheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty('SPREADSHEET_ID');
  var ss = id ? SpreadsheetApp.openById(id)
              : (SpreadsheetApp.getActiveSpreadsheet() || null);
  if (!ss) {
    throw new Error('No spreadsheet found. Open this script from Extensions > ' +
                    'Apps Script inside your Google Sheet, or set SPREADSHEET_ID.');
  }
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['Timestamp', 'Name', 'Email', 'Phone', 'Strategy',
                     'BudgetMin', 'BudgetMax', 'Areas', 'Consent', 'Token', 'Status', 'Source']);
    sheet.setFrozenRows(1);
  } else {
    ensureSourceColumn_(sheet);
  }
  return sheet;
}

/**
 * Adds the 'Source' header in column 12 of an existing subscriber list if it
 * is missing. Existing rows are never touched.
 */
function ensureSourceColumn_(sheet) {
  var v = '';
  if (sheet.getLastColumn() >= 12) {
    v = String(sheet.getRange(1, 12).getValue() || '').trim();
  }
  if (v === '' || v === 'Source') sheet.getRange(1, 12).setValue('Source');
}

function fetchDeals_() {
  var res = UrlFetchApp.fetch(DATA_URL + '?cb=' + new Date().getTime(),
                              { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error('Could not read ' + DATA_URL + ' (HTTP ' + res.getResponseCode() + ')');
  }
  var data = JSON.parse(res.getContentText());
  var rows = (data.lots || []).filter(function (l) {
    return l && l.addr && String(l.status || 'available').toLowerCase() !== 'sold';
  });
  var lines = rows.slice(0, MAX_LOTS_IN_PROMPT).map(function (l) {
    return '- ' + l.addr +
      ' | guide: ' + (l.price_label || (l.guide ? '£' + l.guide : 'not stated')) +
      ' | strategy: ' + (l.strategy || 'n/a') +
      ' | status: ' + (l.status || 'available') +
      (l.auction_date ? ' | auction: ' + l.auction_date : '') +
      ' | source: ' + (l.source || 'n/a');
  });
  var sources = Object.keys(data.sources || {}).map(function (k) {
    return k + ' (' + (data.sources[k].lots || 0) + ')';
  }).join(', ');

  return {
    count: rows.length,
    checked: data.checked_uk || data.updated_uk || 'recently',
    text: 'Lots (' + rows.length + ' available, showing up to ' + MAX_LOTS_IN_PROMPT + '):\n' +
          (lines.length ? lines.join('\n') : '(none — no live lots are listed right now)') +
          '\n\nAuction sources checked: ' + (sources || 'none') +
          '\nNote: zero lots means the auctions were quiet this week, not an error.'
  };
}

/**
 * Reads the newest blog posts from the public RSS feed (fallback when the
 * auctions hold zero usable lots). Never throws — returns {checked, items}.
 */
function fetchBlogPosts_() {
  try {
    var res = UrlFetchApp.fetch(FEED_URL + '?cb=' + new Date().getTime(),
                                { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return { checked: '', items: [] };
    var channel = XmlService.parse(res.getContentText()).getRootElement().getChild('channel');
    if (!channel) return { checked: '', items: [] };
    var built = '';
    try { built = channel.getChildText('lastBuildDate') || ''; } catch (e0) {}
    var items = [];
    var entries = channel.getChildren('item') || [];
    for (var i = 0; i < entries.length && items.length < MAX_POSTS_IN_PROMPT; i++) {
      var title = '', link = '', desc = '';
      try { title = entries[i].getChildText('title') || ''; } catch (e1) {}
      try { link = entries[i].getChildText('link') || ''; } catch (e2) {}
      try { desc = entries[i].getChildText('description') || ''; } catch (e3) {}
      if (title && link) items.push({ title: title, link: link, desc: desc });
    }
    return { checked: built, items: items };
  } catch (err) {
    return { checked: '', items: [] };
  }
}

function findRowByEmail_(sheet, email) {
  var last = sheet.getLastRow();
  if (last < 2) return { row: 0 };
  var values = sheet.getRange(2, 3, last - 1, 1).getValues();
  var needle = String(email).trim().toLowerCase();
  for (var i = 0; i < values.length; i++) {
    if (String(values[i][0] || '').trim().toLowerCase() === needle) return { row: i + 2 };
  }
  return { row: 0 };
}

function findRowByToken_(sheet, token) {
  var last = sheet.getLastRow();
  if (last < 2) return 0;
  var values = sheet.getRange(2, 10, last - 1, 1).getValues();
  for (var i = 0; i < values.length; i++) {
    if (String(values[i][0] || '').trim() === token) return i + 2;
  }
  return 0;
}

function parseBody_(e) {
  var raw = (e && e.postData && e.postData.contents) ? e.postData.contents : '';
  if (raw) {
    try { return JSON.parse(raw); } catch (err) { /* fall through */ }
  }
  return (e && e.parameter) ? e.parameter : {};   // form-encoded fallback
}

function getWebAppUrl_() {
  if (WEB_APP_URL) return WEB_APP_URL;
  try { return ScriptApp.getService().getUrl(); } catch (err) { return SITE_URL; }
}

function isEmail_(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v || '').trim()) &&
         String(v).length <= 254;
}

function numberOrBlank_(v) {
  var n = Number(v);
  return (isFinite(n) && n >= 0) ? n : '';
}

/**
 * Allows only h2, p, ul, li, strong and links — the tags the prompts may use.
 * Links keep an http(s) href only; every other attribute is dropped. Stray
 * closing tags left behind by dropped links are harmless in email clients.
 */
function sanitise_(html) {
  var out = String(html);
  out = out.replace(/```[a-z]*/gi, '');
  out = out.replace(/<(script|style|iframe|form|input|img)\b[^>]*>/gi, '');
  out = out.replace(/<a\b[^>]*>/gi, function (tag) {
    var m = tag.match(/href\s*=\s*("([^"]*)"|'([^']*)')/i);
    var href = m ? (m[2] || m[3] || '') : '';
    if (/^https?:\/\//i.test(href)) return '<a href="' + href + '">';
    return '';
  });
  out = out.replace(/<(h2|p|ul|li|strong)\b[^>]*>/gi, '<$1>');
  out = out.replace(/<\/?(?!\/?(?:h2|p|ul|li|strong|a)\b)[a-z][^>]*>/gi, '');
  return out.trim();
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function html_(inner) {
  return HtmlService.createHtmlOutput(
    '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:40px auto;' +
    'padding:0 20px;color:#0f172a;line-height:1.6">' + inner + '</div>');
}
