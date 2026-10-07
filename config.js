/* Public, non-secret site settings only.
 * Do not put API keys, Sheet IDs with write access, or personal data here.
 */
window.SITE_CONFIG = Object.freeze({
  tradingName: '',
  yourName: '',
  contactEmail: '',
  // Leave blank until a valid ICO registration reference exists. Blank = hidden in the footer.
  icoRegistration: '',
  // Paste the deployed alert + newsletter Apps Script web-app URL here.
  // See NEWSLETTER-SETUP.md step 5. Until a real URL replaces this placeholder
  // the alert form shows "Alerts are not live yet" and sends nothing.
  alertEndpoint: 'https://script.google.com/macros/s/AKfycbwQoRXvislDY2Xc_tY5u8JGcNUPErSB7Mx6LKvGHpfu2J45O-I5G6urKYtbIVTwlTnD9A/exec',
  // Seller-lead endpoint ("Sell your house fast" form). Kept separate so that
  // changing the alert/newsletter endpoint never interrupts seller enquiries.
  sellerEndpoint: 'https://script.google.com/macros/s/AKfycbzV-Z3j2lt_65uZ5ehp96eLujKVkNJQyCIAEgGPqH5ajoCxZamcEsjfQqOd13RMngTK/exec',
  // Optional read-only published CSV URL for the Deals tab. Never use a write-capable URL.
  liveDealsCsvUrl: 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSc60UY3Lni2-oUuOEWJmYu4tZtdteJEmLSOXVMcB2NREWYaaRMo2sfZ5uXyWwFvjwjQSnRSe-25uSD/pub?gid=1535144288&single=true&output=csv',
  // Deal-score weights must total 100. These are display weights, not investment advice.
  dealScoreWeights: Object.freeze({
    discountToComps: 25,
    grossYield: 20,
    refurbRisk: 15,
    demand: 15,
    hmoDensityArticle4: 15,
    dataConfidence: 10
  }),
  // Privacy-friendly, cookieless analytics (GoatCounter). Nothing loads while this is blank.
  // Your code is the first part of your GoatCounter URL: "ramanpreet" gives
  // https://ramanpreet.goatcounter.com/count   See ANALYTICS-SETUP.md.
  goatcounterCode: 'propertyinvestmentinsights',
  // Google Search Console verification token. Nothing is rendered while this is blank.
  gscVerification: '',
  areaCovered: '',
  feeStructure: Object.freeze({
    title: 'Fee structure',
    intro: 'Our sourcing fee is £3,000–£5,000 or 1%–3% of purchase price, whichever is greater, payable in three stages.',
    items: Object.freeze([
      {label: 'Sourcing fee', value: '£3,000–£5,000 or 1%–3% of purchase price (whichever is greater)'},
      {label: 'Payment stages', value: '£1,100 reservation deposit on reservation / offer acceptance, then 50% of the remaining fee due on legal instruction and 50% due on exchange'},
      {label: 'VAT', value: 'Not VAT registered — no VAT is charged on the fee'}
    ]),
    note: ''
  }),
  // Leave these empty until you have real, permissioned entries to publish.
  // Track record fields: title, text, date. Testimonial fields: quote, author.
  trackRecord: Object.freeze([]),
  testimonials: Object.freeze([]),
  dataAsOf: 'Sep 2026'
});
