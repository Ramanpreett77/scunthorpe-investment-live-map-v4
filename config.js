/* Public, non-secret site settings only.
 * Do not put API keys, Sheet IDs with write access, or personal data here.
 */
window.SITE_CONFIG = Object.freeze({
  tradingName: '[TRADING NAME]',
  yourName: '[YOUR NAME]',
  contactEmail: '[EMAIL]',
  // Leave blank until a valid ICO registration reference exists. Blank = hidden in the footer.
  icoRegistration: '',
  // Paste the deployed, anonymous alert-only Apps Script web-app URL here.
  alertEndpoint: '',
  // Optional read-only published CSV URL for the Deals tab. Never use a write-capable URL.
  liveDealsCsvUrl: '',
  dataAsOf: 'Sep 2026'
});
