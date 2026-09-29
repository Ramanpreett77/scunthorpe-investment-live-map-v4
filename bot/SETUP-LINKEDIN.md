# LinkedIn Automation Setup — your 4 clicks + my 1 minute

Everything on the bot side is ready (launch post drafted, poster tested, weekly
workflow prepared). You only need the LinkedIn-side steps below.

## YOUR SIDE (~10 minutes, one time)

**1. Create the SGJM Page** (from your existing account)
- LinkedIn → For Business → Create a Company Page → name: **SGJM** (or SGJM Property)
- Category: Real Estate / Financial service. Logo: `assets/og-image.jpg` works.

**2. Create the developer app**
- https://www.linkedin.com/developers/ → **Create app**
- Name: *SGJM Publisher* · link the SGJM Page · upload logo · accept terms.

**3. Add products** (app → Products tab)
- ✔ **Share on LinkedIn**
- ✔ **Sign In with LinkedIn**

**4. Generate the token**
- App → Auth tab → OAuth 2.0 tools (https://www.linkedin.com/developers/tools/oauth)
- Tick scopes: `openid` `profile` `w_member_social`
- **Request access token** → authorise → **copy the token** (note the ~60-day expiry)

## MY SIDE (1 minute)
Paste the token in our chat and say "go". I will:
1. Show you the launch post via dry-run
2. Publish it to your LinkedIn
3. Hand you the weekly-automation wiring (GitHub secrets) below

## THEN — weekly automation (3 minutes)
1. Put the `property-blog-bot` folder in your GitHub Pages repo
2. Repo → Settings → Secrets & variables → Actions:
   - Secret `LINKEDIN_ACCESS_TOKEN` = the token
   - Variable `SITE_URL` = your site URL (e.g. https://yourname.github.io)
3. Actions tab → run "Auto Blog Publisher" once to test. Every Monday 07:00 after that:
   new article → site rebuilt → LinkedIn post (+ carousels when FB/IG tokens added).

## Safety notes
- Token = posting rights. Only paste it into your own tools/repo secrets.
- Revoke anytime: LinkedIn → Settings → Data privacy → Permitted services / developer apps.
- Posts go out as *you* (personal profile) — best reach. SGJM Page remains the brand home.
