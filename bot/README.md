# Property Blog Bot 🏠

An automated content pipeline for a UK property-investment website on **GitHub Pages**:

1. **Generates** property-investment articles (HMO, BRR, buy-to-let, refinancing, deal sourcing)
2. **Publishes** them to your GitHub Pages site automatically
3. **Posts** the article to your LinkedIn (official API)
4. **Finds** property investors on LinkedIn (compliant toolkit: searches, templates, tracker)

```
blog_generator.py          content engine (built-in templates, optional AI)
carousel_builder.py        branded carousel slides (PNG) + PDF for LinkedIn
social_media_poster.py     multi-platform publisher (LinkedIn + Facebook + Instagram,
                           single-image or carousel posts)
engagement_bot.py          reads new comments & replies like a human (official APIs)
build_site.py              builds the complete static blog website into docs/
publish_github_pages.py    commits files to your repo via GitHub API
linkedin_poster.py         builds + publishes the LinkedIn post
assets/og-image.jpg        branded image for Instagram/Facebook posts
linkedin/investor-toolkit.md   Boolean searches, groups & outreach templates
linkedin/lead-tracker.csv  spreadsheet for managing investor leads
.github/workflows/auto-blog.yml      weekly: article + carousels + posts + replies
.github/workflows/engagement.yml     twice daily: reply to new comments
```

---

## 1. Generate an article (works instantly, no setup)

```bash
python3 blog_generator.py --list                # show all topics
python3 blog_generator.py --topic brr-strategy  # write a specific article
python3 blog_generator.py                       # random topic
python3 blog_generator.py --format html         # standalone HTML page instead
python3 blog_generator.py --ai                  # use OpenAI if OPENAI_API_KEY is set
```

Output: a Jekyll-ready post in `_posts/YYYY-MM-DD-slug.md` plus `output/latest.json`
(metadata used by the LinkedIn poster).

**AI mode (optional, better quality):** set `OPENAI_API_KEY` in your environment (or as a
GitHub Actions secret) and run with `--ai`. Falls back to the template engine automatically.

---

## 2. Wire it to your GitHub Pages site

Your site must use **Jekyll** (the GitHub Pages default) — posts in `_posts/` are then
published automatically at `/YYYY/MM/DD/slug.html`.

**Option A — manual (2 commands):**
```bash
python3 blog_generator.py
git add _posts && git commit -m "New article" && git push
```

**Option B — fully automatic (recommended):**
1. Copy this whole folder into the repository that backs your GitHub Pages site
   (so `_posts/`, `blog_generator.py` and `.github/workflows/auto-blog.yml` live at the repo root).
2. In the repo → **Settings → Secrets and variables → Actions**, optionally add:
   - `OPENAI_API_KEY` (only if you want AI-written articles; also add `--ai` to the workflow)
   - `LINKEDIN_ACCESS_TOKEN` (see section 3)
3. In **Variables**, add `SITE_URL` = your site address, e.g. `https://yourname.github.io`
4. Done. Every Monday 07:00 UTC a new article is generated, committed and published —
   and posted to LinkedIn if the token is set. You can also run it anytime via
   **Actions → Auto Blog Publisher → Run workflow**.

**Option C — repo push from anywhere** (e.g. run the generator on your laptop and push
via API instead of git):
```bash
export GITHUB_TOKEN=github_pat_xxx      # fine-grained PAT: Contents = Read & Write
export GITHUB_REPO=yourname/yourname.github.io
python3 publish_github_pages.py _posts/2026-09-28-brr-strategy.md
```

---

## 3. LinkedIn auto-posting setup (official API, ~10 minutes)

1. Go to <https://www.linkedin.com/developers/> → **Create app** (any name; add your LinkedIn page or create one).
2. In the app → **Products** → request **Share on LinkedIn**.
3. **Auth → OAuth 2.0 tools** → generate a user access token with scopes
   `openid`, `profile`, `w_member_social`.
4. Test locally:
   ```bash
   export LINKEDIN_ACCESS_TOKEN=xxxx
   python3 linkedin_poster.py --dry-run   # preview
   python3 linkedin_poster.py --post      # publish
   ```
5. For the weekly automation, add the token as the **`LINKEDIN_ACCESS_TOKEN`** repo secret.

⚠️ Tokens from the OAuth tool expire (~60 days) — refresh and update the secret when they do.
Always use the official API: unofficial auto-posting tools risk account restriction.

---

## 3b. Social media automation (Facebook + Instagram)

`social_media_poster.py` publishes each article to **LinkedIn, your Facebook Page and
Instagram** in one step — official APIs only, so your accounts stay safe.

```bash
python3 social_media_poster.py --dry-run                              # preview all platforms
python3 social_media_poster.py --platforms linkedin,facebook --post   # publish selected
```

**Facebook Page setup (free):**
1. At <https://developers.facebook.com> create an app (type: Business) and add the
   **Facebook Login for Business** + **Pages API** products.
2. In the **Graph API Explorer**, generate a *User* token with scopes
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
3. Find your Page ID: `GET /me/accounts` in the explorer.
4. Exchange for a **Page access token** (these can be made long-lived) and set env vars
   `FACEBOOK_PAGE_ID` + `FACEBOOK_PAGE_ACCESS_TOKEN`.

**Instagram setup (free, needs an image):**
1. Switch your Instagram to a **Professional (Business/Creator) account** and link it to
   the Facebook Page above. Meta may require app review for the
   `instagram_business_content_publish` permission before public posting works.
2. Every Instagram post needs an image — this toolkit ships `assets/og-image.jpg`
   (a branded banner). Commit it to your site, then set
   `OG_IMAGE=https://yoursite/assets/og-image.jpg` (or pass `--image URL`).

**GitHub Actions (weekly, hands-off):** add the values as repo secrets/variables:
`LINKEDIN_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `OG_IMAGE`.
The workflow's social step skips any platform whose credentials are missing, so you can
enable platforms one at a time.

**Why not X (Twitter)?** Since Feb 2026 the X API is pay-per-use — roughly **$0.20 for
every post containing a link** (which blog shares always do), with no free tier. For
property marketing, LinkedIn + Facebook + Instagram deliver far better value. If you
still want X, it can be added to the poster later.

## 3c. Who is in control? (how the automation runs)

- **Everything goes through official APIs** with tokens *you* generate — the bot never
  sees passwords, and no unofficial automation is used (that's what gets accounts banned).
- **You stay the owner:** tokens can be revoked anytime in LinkedIn/Meta developer
  settings, which instantly cuts the bot off.
- **Nothing posts without credentials** — every platform must be explicitly unlocked by
  you adding its token, and `--dry-run` lets you review exact post text first.
- **Scheduling lives in your GitHub repo** (`auto-blog.yml`) — you can pause it with one
  click (Actions → disable workflow), change the day/time, or trigger it manually.
- **Token upkeep:** LinkedIn tokens last ~60 days; Meta Page tokens can be long-lived.
  When one expires you'll just re-generate it and update the GitHub secret (~2 minutes).

---

## 4. Finding property investors on LinkedIn

See **`linkedin/investor-toolkit.md`**: ready-made Boolean search strings (HMO/BRR/West Midlands),
groups to join, hashtags, 300-char connection request templates and a daily 15-minute routine.
Track everyone in **`linkedin/lead-tracker.csv`** (opens in Excel/Sheets).

---

## 5. Carousel posts (LinkedIn / Facebook / Instagram)

```bash
python3 carousel_builder.py --url-prefix https://yoursite/assets/slides/
python3 social_media_poster.py --carousel              # preview
python3 social_media_poster.py --carousel --post       # publish everywhere
```

* **LinkedIn** receives the slides as a PDF *document post* = the native swipeable carousel.
* **Instagram** receives a true CAROUSEL (needs the slide PNGs publicly hosted, hence
  `--url-prefix`; the weekly workflow commits them to `docs/assets/slides/`).
* **Facebook** receives a multi-photo carousel-style post.
Slide design lives in `carousel_builder.py` (colours, fonts, skyline).

## 6. Engagement bot — replies like a human

```bash
python3 engagement_bot.py --sample          # demo with fake comments
python3 engagement_bot.py                   # preview drafted replies for real comments
python3 engagement_bot.py --post            # send them
```

* With `OPENAI_API_KEY` set, replies are written by AI in your brand voice (friendly UK
  investor, never gives financial advice). Without it, a sensible rule-based bank is used.
* A state file prevents double-replies. `engagement.yml` runs it twice daily in Actions.
* Replies go through the official comment APIs only - safe for your accounts.

## 7. The complete blog website (GitHub Pages, no Jekyll)

```bash
python3 build_site.py --site-url https://yoursite --contact-email you@site.com
python3 -m http.server 8000 -d docs         # local preview
```

Builds a full branded site into `docs/`: home with hero & featured articles, strategy
sections, article pages with free share buttons (LinkedIn/Facebook/X), about, contact
with lead-capture form, RSS feed, 404 and SEO/OG tags. In your repo:
**Settings → Pages → deploy from branch → folder `/docs`**.

## 8. 24/7 sales & customer-service assistant

The site ships with a chat widget (`assets/js/chat.js`) - a floating assistant that is
online 24/7 with zero backend: answers BRR/HMO/buy-to-let questions, links the right
articles, and captures sales leads (name/email) into the browser + contact form.
It works on GitHub Pages as-is.

*Upgrade path when you want full AI conversations:* deploy the same prompts to a free
serverless function (Cloudflare Workers / Vercel) holding your OpenAI key, and point the
widget's `answer()` at it - the widget's structure already supports it. For Messenger/
WhatsApp-style automation at scale, pair it with ManyChat (approved by Meta) rather than
anything unofficial.

## Customising

- **Add topics:** edit the `TOPICS` list in `blog_generator.py` (copy an existing block).
- **Region:** `--region "the North West"` or env var `BLOG_REGION`.
- **Site branding:** the HTML output styling lives in `html_document()` in `blog_generator.py`.

*All generated articles include illustrative-figure disclaimers; review each post before
publishing if you want to add your own deals and numbers.*
