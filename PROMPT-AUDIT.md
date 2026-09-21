# Prompt implementation and repository audit

Audit date: 21 September 2026

Repository checked: https://github.com/Ramanpreett77/scunthorpe-investment-live-map-v4

## Executive result

The current workspace contains the Prompt 2, Prompt 3 and Prompt 4 implementation and passes static, syntax, HTTP and mocked Apps Script checks.

The public GitHub repository is **not yet a complete deployment of the workspace**. Its current `main` branch contains the updated `index.html`, but several required supporting files are absent. The public GitHub Pages site therefore has broken/missing supporting resources and cannot provide the private-admin features from the repository alone.

## Requirement matrix: local workspace

| Area | Result | Evidence / limitation |
|---|---|---|
| Public map, calculators and deal UI | Pass | `index.html`; inline JavaScript syntax check passed |
| Deal alerts with consent, validation and privacy link | Pass | `index.html`, `AlertEndpointCode.gs`; mock validation passed |
| Private investor matching | Pass | `AdminCode.gs` and `Admin.html`; strategy, budget, area and opt-out paths are present |
| Individual email preview/confirmation | Pass | `prepareInvestorMessage` and `sendInvestorEmail`; no bulk-send action |
| WhatsApp click-to-chat and SendLog | Pass | `whatsappUrl_`, `logWhatsAppClick`, `appendSendLog_` |
| Pipeline Kanban | Pass | Pipeline CRUD and stage validation are present |
| Motivated Seller tracker/import | Pass | Seller CRUD, CSV import and filters are present |
| Mobile viewing checklist | Pass | All ten requested condition fields are present in `Admin.html` |
| Viewing notes and refurb presets | Pass | Private admin viewing form and Refurb Calculator hand-off are present |
| Viewing photo privacy | Pass in code | Photos are compressed in the browser and uploaded using server-side `DriveApp`; real Drive permissions still need production testing |
| Offline viewing queue | Pass in code | Payload is retained in browser storage until a successful Apps Script response |
| `Viewings` Sheet rows | Pass in code | `saveViewing` writes the documented 19-column row |
| Public `?deal=ID` view | Pass | Query handling and limited public deal renderer are present |
| Hidden exact address | Pass in code | `hide_address`, address withholding and explicit fee-template acknowledgement are present |
| Reserve action | Pass | Links to `Fee-Agreement-Template.html?deal=ID` |
| Anonymous deal analytics | Pass in code | Optional Plausible events; disabled by default and no PII properties are sent |
| Homepage hero and order | Pass | Hero, Deals, Tools, How it works, fee, About and FAQ sections are present |
| Four How-it-works steps | Pass | Exactly four step blocks are present |
| Config-driven fee section | Pass | `feeStructure` is read from `config.js` and contains placeholders only |
| About section | Pass | Sole trader, `[YOUR NAME]`, area covered and contact are shown from configuration |
| FAQ | Pass | FAQ uses generic due-diligence and illustrative-figures wording |
| Track record/testimonials | Pass | Both are hidden when the configuration arrays are empty; no invented entries are present |

## Tests run in the workspace

- Node syntax checks passed for all inline scripts in:
  - `index.html`
  - `privacy-policy.html`
  - `apps-script/Admin.html`
- Node syntax checks passed for:
  - `apps-script/AdminCode.gs`
  - `apps-script/AlertEndpointCode.gs`
  - `config.js`
- Prompt static assertions passed for hero buttons, page order, four steps, fee configuration, About, FAQ and hidden proof sections.
- Mocked Apps Script tests passed for:
  - alert validation and formula-injection cleaning;
  - investor strategy/budget/area matching;
  - WhatsApp URL generation;
  - safe photo filename handling;
  - one `saveViewing` row and one mocked Drive photo upload.
- Local HTTP checks passed for the homepage, `?deal=...` URL and privacy policy.
- Local relative-resource audit passed except for `data/auction-stock.json`, which is not present in the workspace; the application falls back to built-in stock.
- `git diff --check` passed.

A full browser automation test and real Google Sheet/Drive test were not possible in this environment because Chromium/Selenium is unavailable and no production Apps Script credentials or authorisation were supplied.

## Repository / GitHub Pages findings

The current public repository tree contains `index.html`, the existing templates, the auction scraper and its workflow. It does **not** currently contain these workspace files:

- `config.js` — GitHub Pages returns 404. `index.html` references it.
- `privacy-policy.html` — GitHub Pages returns 404. Public links point to it.
- `apps-script/Admin.html` — private admin source is absent.
- `apps-script/AdminCode.gs` — private server source is absent.
- `apps-script/AlertEndpointCode.gs` — public alert endpoint source is absent.
- `APPS-SCRIPT-DEPLOYMENT.md` — deployment instructions are absent.
- `data/auction-stock.json` — the scraper workflow can create it after a successful run, but it is not currently present.

The remote site also still serves `Investor-Criteria-Form.html`. That conflicts with the private-admin-only investor requirement even though the current `index.html` no longer links to it. The local workspace has deleted that file, but the deletion has not been pushed to the public repository.

The remote homepage itself returned HTTP 200 and its inline JavaScript passed syntax checking. The following remote resources returned HTTP 404 during the audit:

- `config.js`
- `privacy-policy.html`
- `data/auction-stock.json`

The remote site therefore runs with an empty fallback configuration, cannot load the privacy policy, cannot enable configured fee/about/analytics settings, and cannot use auto-stock until the workflow produces its JSON file.

## Required repository actions before calling all prompts complete

1. Commit and push `config.js`.
2. Commit and push `privacy-policy.html`.
3. Commit and push the `apps-script` sources and deployment documentation, or store them in a private deployment repository while keeping the public site links and deployment process consistent.
4. Remove `Investor-Criteria-Form.html` from the public repository and consider the historical Git cleanup already documented in `SECURITY-AUDIT.md`.
5. Run the auction scraper workflow once and confirm that `data/auction-stock.json` is committed, or deliberately leave the built-in fallback documented.
6. Configure the real Google Sheet, private Drive folder and Apps Script deployments, then test one alert registration, one individual email preview/send, one WhatsApp log, one pipeline item, one seller import, one viewing with a photo and one offline viewing sync.
7. Replace only the approved placeholders in `config.js`; do not add secrets, Sheet IDs, Drive IDs or personal data to the public repository.
