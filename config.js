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
  // Deal-score weights must total 100. These are display weights, not investment advice.
  dealScoreWeights: Object.freeze({
    discountToComps: 25,
    grossYield: 20,
    refurbRisk: 15,
    demand: 15,
    hmoDensityArticle4: 15,
    dataConfidence: 10
  }),
  // Optional cookieless Plausible analytics. Disabled until you set your own domain.
  analytics: Object.freeze({
    enabled: false,
    provider: 'plausible',
    scriptUrl: 'https://plausible.io/js/script.js',
    domain: ''
  }),
  areaCovered: '[AREA COVERED]',
  feeStructure: Object.freeze({
    title: 'Fee structure',
    intro: '[INSERT A SHORT DESCRIPTION OF YOUR FEES]',
    items: Object.freeze([
      {label: 'Sourcing fee', value: '[INSERT £X OR %]'},
      {label: 'When payable', value: '[INSERT PAYMENT TRIGGER]'},
      {label: 'VAT / other terms', value: '[INSERT VAT AND OTHER TERMS]'}
    ]),
    note: '[INSERT ANY REFUND, RESERVATION OR CANCELLATION TERMS]'
  }),
  // Leave these empty until you have real, permissioned entries to publish.
  // Track record fields: title, text, date. Testimonial fields: quote, author.
  trackRecord: Object.freeze([]),
  testimonials: Object.freeze([]),
  dataAsOf: 'Sep 2026'
});
