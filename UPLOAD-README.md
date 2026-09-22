Live-site update package
The live site is serving an older `config.js` and older `privacy-policy.html`, and the private Apps Script source is not yet in the repository. Upload these files/folders to the repository root, preserving the paths:
replace `index.html`
replace `config.js`
replace `privacy-policy.html`
replace `APPS-SCRIPT-DEPLOYMENT.md`
upload `apps-script/Admin.html`
upload `apps-script/AdminCode.gs`
upload `apps-script/AlertEndpointCode.gs`
replace `data/auction-stock.json`
upload `.github/workflows/scrape-auctions.yml`
upload `scripts/scrape_auctions.py`
Then delete this old public file if it exists:
```text
Investor-Criteria-Form.html
```
Do not enter Sheet IDs, Drive folder IDs, API keys, or personal data into `config.js`.
After committing, wait for GitHub Pages to redeploy, then test:
`/config.js`
`/privacy-policy.html`
`/?deal=pugh-9191`
the homepage fee placeholders
the alert button and tools button
