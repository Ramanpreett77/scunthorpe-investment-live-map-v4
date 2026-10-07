Status: ready to configure (all code is live; two values need pasting in).
Analytics + Search Console — setup guide
This wires up privacy-friendly analytics (GoatCounter — no cookies, no personal data),
Google Search Console, the shared subscriber list and the quiet-week newsletter fallback.
Nothing here costs money (GoatCounter is free for non-commercial use; Search Console is free).

What is already done in the code
- Every blog page and the main site load GoatCounter from one shared place — but only
  after you add your account code in Step 1. Until then nothing loads.
- The blog subscribe form posts to the SAME Google Sheet list as the main site's
  deal-alert form (`source` = `blog` vs `deal-map`).
- `blog/sitemap.xml` regenerates automatically every time the blog bot publishes.
- The newsletter uses the newest blog posts when the auctions are quiet.
- No Google Analytics, no Meta Pixel, no advertising scripts anywhere.

---
Step 1 — Create your GoatCounter account (5 minutes)
1. Go to https://www.goatcounter.com/signup and create a free account.
2. During signup it asks for a code — this becomes `https://YOUR-CODE.goatcounter.com`.
   (Example: code `ramanpreet` gives `https://ramanpreett77.github.io/scunthorpe-investment-live-map-v4/`.)
   Use lowercase letters and numbers only.
3. Skip the "add to your site" snippet page — the code is already in the site.
4. Open `config.js` in the repo:
   https://github.com/Ramanpreett77/scunthorpe-investment-live-map-v4/edit/main/config.js
5. Find `goatcounterCode: ''` and put your code between the quotes, e.g.
   `goatcounterCode: 'ramanpreet'`. Commit changes.
6. Wait a minute for GitHub Pages to redeploy, visit your site once, then check
   GoatCounter — your visit should appear within a few minutes.

Step 2 — Verify the blog in Google Search Console (10 minutes)
1. Go to https://search.google.com/search-console and sign in.
2. Add property → choose **URL prefix** (not Domain) → enter exactly:
   `https://ramanpreett77.github.io/scunthorpe-investment-live-map-v4/blog/`
3. Choose the **HTML tag** verification method. Google shows a tag like
   `<meta name="google-site-verification" content="ABC123..." />`.
   Copy ONLY the token part (`ABC123...`).
4. Open `config.js` (same link as Step 1), find `gscVerification: ''` and paste
   ONLY the token between the single quotes (no `<meta...>`, no double quotes). Commit changes.
5. The tag is baked into the blog pages the next time the blog bot builds — it rebuilds
   automatically every day, so within 24 hours at most. Wait a minute for GitHub Pages
   to redeploy, then click **Verify** in Search Console.
   (If it fails, wait 5 minutes and try again — the redeploy may still be running.
   Google reads the raw page without JavaScript, which is why the tag must be baked
   into the HTML rather than added by a script.)

Step 3 — Submit the sitemap and feed (2 minutes)
1. In Search Console (with your blog property selected) → **Sitemaps** in the left menu.
2. Enter `sitemap.xml` → Submit. Then enter `feed.xml` → Submit.
   (Google prefixes them with your blog address automatically.)
3. Both should show Success within a day or two.

Step 4 — Update the Apps Script (paste + redeploy, 5 minutes)
The subscriber sheet gained a `Source` column and the newsletter gained its
quiet-week blog fallback — your live script needs the new code:
1. Open your Apps Script project (the one from NEWSLETTER-SETUP.md).
2. Select ALL the code, delete it, then copy the whole of `apps-script/Code.gs`
   from this repo and paste it in. Save.
3. Deploy → **Manage deployments** → ✏️ Edit → Version: **New version** → Deploy.
   (This step is essential — without a new version the URL keeps running old code.)
4. The `Source` header appears in your Subscribers sheet automatically the next
   time someone registers. Old rows are untouched.

Step 5 — Test both forms (5 minutes)
1. Main site: open the live deal map, open the Deals area, register with your own
   email (tick consent). You should see "You're registered — check your inbox weekly."
2. Blog: open the blog homepage, use the Subscribe box with a *different* email
   of yours (tick consent). You should see "You are subscribed — check your inbox weekly."
3. In your Google Sheet's Subscribers tab you should see both rows, with `Source`
   = `deal-map` and `blog`.
4. In Apps Script, run `sendTest` once to confirm the digest still sends
   (right now the auctions are quiet, so the test email should round up blog posts).

---
Troubleshooting
Symptom	Fix
No visits in GoatCounter	The code in `config.js` must match your GoatCounter URL exactly. Also check you are not blocking it with an ad-blocker (blocking is fine — the site still works).
Search Console won't verify	The token must be pasted in `config.js` AND committed AND the blog rebuilt AND the site redeployed before clicking Verify. The blog rebuilds automatically every day — check the tag is live by viewing page source on any blog page and searching for `google-site-verification`.
Blog form says "not live yet"	`config.js` still needs the Apps Script URL from NEWSLETTER-SETUP.md Step 5 (both forms share it).
No `Source` column in the Sheet	Redeploy a new version (Step 4.3) and submit one test registration.
