Google Apps Script deployment
The static site deliberately contains no Sheet ID, write-capable URL, API key or personal data. The private admin remains separate from the public alert receiver. Matching, email sending, pipeline data and seller data are private-admin functions only.
1. Prepare the Google Sheet
Create or open the Google Sheet you want to use.
Create these tabs (the private admin can create them if they do not exist): `Deals`, `Alerts`, `Pipeline`, `Sellers`, `SendLog` and `Viewings`.
Do not make the spreadsheet public. Only your Google account and the Apps Script projects should have access.
In the `Deals` tab, use this first row if you create it yourself:
`slug,addr,status,guide,fee,refurb,rent,gdv,comp\_price,data\_confidence,beds,type,strategy,zone,lat,lon,blurb,note,source,source\_url,auction\_date,image,hide\_address`
The other tabs use these headers:
`Alerts`: `timestamp,name,email,phone,strategy,budgetMin,budgetMax,areas,deal,consent,status`
`Pipeline`: `stage,address,lead\_source,seller\_motive,asking\_price,agreed\_price,fee,follow\_up\_date,notes`
`Sellers`: `address,postcode,days\_on\_market,price\_reductions\_count,price\_reduction\_pct,probate,vacant,repossession\_auction,tired\_landlord,notes`
`SendLog`: `timestamp,channel,deal\_slug,address,investor\_row,investor\_email,subject,result`
`Viewings`: `timestamp,viewing\_id,address,postcode,viewing\_date,deal\_slug,roof,damp,wiring,plumbing,heating,windows,structure,layout,access,neighbours,notes,refurb\_total,photo\_urls`
2. Deploy the private admin
Go to script.google.com and create a new standalone project named `Scunthorpe private admin`.
Add a script file named `AdminCode.gs` and paste the complete contents of `apps-script/AdminCode.gs`.
Add an HTML file named `Admin` and paste the complete contents of `apps-script/Admin.html`.
In Project Settings → Script properties, add:
`SPREADSHEET\_ID` = the Sheet ID copied from the Sheet URL (store it here, not in GitHub).
`DEALS\_SHEET\_NAME` = `Deals` (optional).
`ALERTS\_SHEET\_NAME` = `Alerts` (optional).
`PIPELINE\_SHEET\_NAME` = `Pipeline` (optional).
`SELLERS\_SHEET\_NAME` = `Sellers` (optional).
`SEND\_LOG\_SHEET\_NAME` = `SendLog` (optional).
`VIEWINGS\_SHEET\_NAME` = `Viewings` (optional).
`VIEWING\_DRIVE\_FOLDER\_ID` = the private Google Drive folder ID where viewing photos should be stored.
`PUBLIC\_SITE\_URL` = the public site URL, used only for the private admin's “Feed Refurb Calculator” link.
Click Deploy → New deployment → Web app.
Set Execute as to Me and Who has access to Only myself.
Authorise the requested Sheets and Mail permissions using your own Google account. MailApp is used only after an individual preview and confirmation in the private admin.
Open the deployment URL in a private browser window while signed in as yourself. Confirm that the dashboard loads, a deal can be created/edited/deleted, and alert registrations are visible. Test matching, one confirmed email, the WhatsApp click log, one pipeline item and one seller row.
Do not paste the private admin URL into the public website.
2a. Private-admin feature checks
Matching: open a deal, confirm that only consented, non-opted-out alert contacts can match by strategy, budget and area. Preview one message, check the opt-out line, then confirm one email. There is no bulk-send action.
WhatsApp: use the prefilled click-to-chat link only after reviewing the preview. The admin logs the link opening as `whatsapp\_click`; WhatsApp itself is not sent by Apps Script.
Pipeline: create an item in each needed stage, set a date before today, and confirm that the card is highlighted as overdue.
Sellers: add a seller, try the DN15/DN16/DN17 filters, and import a CSV with the headers in section 1. Review the motivation score rather than treating it as a valuation.

3. Deploy the separate alert-only endpoint
Create another standalone Apps Script project named `Scunthorpe alert endpoint`.
Add a script file named `AlertEndpointCode.gs` and paste the complete contents of `apps-script/AlertEndpointCode.gs`.
In Project Settings → Script properties, add `SPREADSHEET\_ID` with the same Sheet ID. Add `ALERTS\_SHEET\_NAME` = `Alerts` if you use a different tab name.
Click Deploy → New deployment → Web app.
Set Execute as to Me.
Set Who has access to Anyone. This is required because GitHub Pages visitors are not signed in to your Google account.
Authorise the requested Sheets permission. Test the URL with a valid form submission; the response body is intentionally blank. Do not enable any read operation in this project.
Copy the alert endpoint URL into `config.js` as `alertEndpoint`. This URL is allowed in the public site because it can only append validated rows; it cannot read the Sheet.
If Google changes the deployment URL after a new deployment, update `config.js` and publish the site again.
4. Mobile viewing, public share links and analytics
Set `VIEWING\_DRIVE\_FOLDER\_ID` to a private Drive folder. Viewing photos are compressed in the admin browser, uploaded by Apps Script, and their private Drive URLs are stored in the Viewings sheet. Do not make the folder public.
The mobile viewing form queues complete viewing payloads in browser storage when offline and retries them on the next online event. Test by switching the device to airplane mode before saving, then reconnecting.
Set `PUBLIC\_SITE\_URL` if you want the private admin to open the public Refurb Calculator with the viewing total.
For shareable deal links, tick Hide exact address in shared public view on the private deal editor. The public URL is `?deal=ID`; the acknowledgement is stored only in that browser session. The public link reveals only the limited deal view until the fee-agreement-template acknowledgement.
Analytics is disabled by default. To enable cookieless Plausible analytics, set `analytics.enabled` to `true` and fill the public site domain in `config.js`. Do not add names, emails, phone numbers, exact addresses or deal notes to analytics event properties.
5. Optional read-only live deals feed
If you want the public Live Deals panel to load the Sheet, publish only the `Deals` tab as a read-only CSV and put that URL in `config.js` as `liveDealsCsvUrl`. Never place a Sheet URL that grants edit access in the public repository. Leave it blank to use the existing built-in/demo stock and the auto-stock fallback.
6. Retention and access checks
Turn on two-step verification for the Google account.
Review Apps Script deployments and authorised users after each change.
Delete alert rows after 24 months of inactivity, subject to any legal record-keeping need. Review matching, Pipeline, Sellers and SendLog retention separately and delete rows when no longer needed.
Test the alert endpoint with a honeypot value, an invalid email, repeated submissions, and a valid submission. Invalid and repeated requests should not add rows.
The public website cannot verify the content of a `no-cors` response, so only show the visitor a success message once the browser request completes; review the Alerts tab during initial setup.
