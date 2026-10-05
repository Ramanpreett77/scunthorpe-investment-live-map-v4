Status: live setup in progress.
Weekly deal digest — setup guide
This connects the existing "Get deals before they hit the market" form on your site to a
Google Sheet of subscribers and a weekly AI-written email. Nothing in this guide costs money
except the OpenAI usage (a few pence per week at this scale).
How it fits together
```
Visitor fills the form on your site
      │  (JSON, no preflight)
      ▼
Google Apps Script  ──►  "Subscribers" tab in your Google Sheet
      │                         Timestamp | Name | Email | Phone | Strategy |
      │                         BudgetMin | BudgetMax | Areas | Consent | Token | Status
      ▼  every Monday 8am
OpenAI writes the digest from PUBLIC deal data only  ──►  Gmail sends it to every
(never your subscribers' details)                          Active subscriber, each with
                                                           their own unsubscribe link
```
Time needed: about 15 minutes. Do the steps in order — step 5 (pasting the URL) is what
switches the form on.
---
Step 1 — Create the Google Sheet and the script
Go to sheets.new and name the spreadsheet Deal digest subscribers.
In the menu bar click Extensions → Apps Script. A code editor opens in a new tab.
Delete the placeholder code (`function myFunction() { … }`).
Open `apps-script/Code.gs` from this repo, copy the whole file, and paste it in.
Click the 💾 Save icon (or Ctrl/Cmd+S). Name the project Deal digest if asked.
> You don't need to create the "Subscribers" tab by hand or type the column headings —
> the script creates the tab and the headings the first time it runs.
Step 2 — Add the OpenAI key as a Script Property
In the Apps Script editor, click ⚙️ Project Settings in the left sidebar.
Scroll to Script Properties → Add script property.
Property: `OPENAI_API_KEY`  ·  Value: your new OpenAI key (`sk-...`).
Click Save script properties.
> **Create a brand-new key for this** at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
> and revoke any older key you have been using elsewhere. The key lives only here — it is never
> written into the website files, which are public.
>
> Optional: if you ever move this script to a different spreadsheet, add a property
> `SPREADSHEET_ID` with that spreadsheet's ID. Not needed if you stay inside this sheet.
Step 3 — Fill in your business details and check the data URL
Still in Code.gs, near the top:
`BUSINESS_FOOTER` — replace the placeholder text with your real identity. UK email rules
require a genuine business identity and a postal address, e.g.:
`'SGJM Property Investment Insights, operated by Ramanpreett Singh Chhabra (sole trader), 12 Example Street, Scunthorpe DN15 6AA. Email ramanpreettsinghchhabra@gmail.com. You are receiving this because you registered for deal alerts on the Scunthorpe Deal Map. This is sourcing information, not financial advice.'`
`DATA_URL` — already set to your live deals file
`https://ramanpreett77.github.io/scunthorpe-investment-live-map-v4/data/auction-stock.json`.
Leave it as it is unless you rename that file.
`EMAIL_SUBJECT` — change the email subject line if you like.
💾 Save.
Step 4 — Deploy it as a web app
Top-right: Deploy → New deployment.
Click the ⚙️ gear next to "Select type" → choose Web app.
Fill in:
Description: `Deal digest endpoint`
Execute as: Me (must be Me — it writes to your sheet)
Who has access: Anyone (required: the form is public. It only appends rows.)
Click Deploy. Approve the permissions when Google asks — click Advanced → Go to Deal digest (unsafe) if it warns; that warning is normal for your own script.
Copy the Web app URL (it ends in `/exec`). You'll need it in the next step.
Step 5 — Paste the URL into the website (this switches the form on)
Open `config.js` in the repo:
https://github.com/Ramanpreett77/scunthorpe-investment-live-map-v4/edit/main/config.js
Find `alertEndpoint: 'PASTE_APPS_SCRIPT_WEB_APP_URL_HERE'` and paste your URL between the quotes.
Commit changes. GitHub Pages redeploys in about a minute.
Open your site, scroll to the deals area, and check the form no longer says "Alerts are not live yet".
> **If you change the script later** you must make a **new deployment** (or use *Manage deployments
> → edit → Deploy*), otherwise the URL stays on the old code.
Step 6 — Test the form yourself
On your live site, register with your own email address (tick the consent box).
Within a few seconds you should see "You're registered — check your inbox weekly."
Back in your Google Sheet, the Subscribers tab should have a new row: your name, email,
budgets, areas, `Yes` under Consent, a UUID Token and Status `Active`.
Nothing? See Troubleshooting below.
Step 7 — Send yourself a test digest
In the Apps Script editor, choose `sendTest` from the function dropdown at the top.
Click ▶ Run. Approve permissions if asked.
Open your inbox. You should have an email subject starting `[TEST] Your weekly Scunthorpe deal digest`.
Read it carefully. Check the addresses, prices and wording are right. The AI is instructed
to use only the data in `data/auction-stock.json` and never to invent figures — if anything looks
made up, tell me and I'll tighten the prompt.
Step 8 — Put it on a weekly schedule
In the Apps Script editor, left sidebar → ⏰ Triggers.
+ Add Trigger, and set:
Function: `sendNewsletter`
Event source: Time-driven
Type: Week timer
Day: Monday · Time: 8am–9am
Save. Approve permissions if asked.
> The trigger runs in your Google account's timezone (check **Project Settings → Time zone** —
> set it to **(GMT+00:00) London**).
---
Known limits (worth knowing before you grow)
Limit	Detail
~100 emails/day	A free Gmail account can send about 100 emails a day. At one digest a week that's roughly 100 subscribers.
~1,500 emails/day	A paid Google Workspace account raises this to about 1,500/day.
Quota safety	The script checks the remaining quota before sending and stops a few emails short, so a big list can never silently burn your account. It logs how many were sent.
Above ~100 subscribers	Move to a proper email platform (ConvertKit, Mailchimp, Buttondown). They handle deliverability, bounces and unsubscribe rules properly — worth it before you get anywhere near the limit. I can wire that up when you're ready.
Gmail sending	Sending from `@gmail.com` is fine to start. A custom domain later will improve deliverability.
---
Troubleshooting
Symptom	Fix
Form says "Alerts are not live yet"	`config.js` still has the placeholder — do Step 5.
Form says "Registration failed"	The deployment isn't on Anyone access, or you edited the script without redeploying (Step 4). Check the URL ends in `/exec`.
Form says "Sorry — that did not go through" with a message	The script ran and refused it — the message tells you why (usually consent or email format).
No row appears in the Sheet	Open Executions in the Apps Script sidebar — it shows every run and any error. Also confirm you're looking at the Subscribers tab.
Test digest never arrives	Check Executions for the error. The usual cause is a missing/incorrect `OPENAI_API_KEY`, or the key having no credit.
Unsubscribe link says "not recognised"	The token in the email doesn't match the sheet row — usually because the row was edited by hand. Delete the token cell and re-register.
Nobody gets the Monday email	Check Triggers exists and the function is `sendNewsletter`, then check Executions for Monday.
---
What changed on the website side
`config.js` — `alertEndpoint` is now the placeholder you replace in Step 5. The seller form keeps
its own separate endpoint (`sellerEndpoint`), so seller enquiries are unaffected.
`index.html` — the alert form posts JSON with no Content-Type header, shows the new consent
wording, shows "Alerts are not live yet" until Step 5, disables the button while sending, and
still blocks submissions without consent and silently absorbs honeypot spam.
`privacy-policy.html` — new "Weekly deal digest emails" section covering Google Sheets storage,
Gmail sending, OpenAI using public deal data only, unsubscribe links and deletion requests.
