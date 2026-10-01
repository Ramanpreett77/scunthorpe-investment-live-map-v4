#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static blog site builder for GitHub Pages (no Jekyll required)
==============================================================
Reads the generated Markdown articles in _posts/ and builds a complete,
branded, static website into docs/ (set GitHub Pages source to /docs):

  * Home page with hero, featured articles and strategy sections
  * Individual article pages with free share buttons (LinkedIn/Facebook/X)
  * About + Contact pages with lead-capture form
  * 24/7 chat assistant widget (sales + customer service, works offline)
  * RSS feed, 404, SEO/OG tags, branded styling

Usage:
  python3 build_site.py                     # build into ./docs
  python3 build_site.py --out docs --site-url https://mysite
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blog_generator import md_to_html_body  # noqa: E402

BRAND = "SGJM"
TAGLINE = "Practical UK property investing: HMOs, BRR, buy-to-let and real deal numbers."

# ------------------------------------------------------------------ styles ---
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1c2430;background:#f7f8fa;line-height:1.65}
a{color:#0f2a43}
header.top{background:#0f2a43;color:#fff;position:sticky;top:0;z-index:50;box-shadow:0 2px 10px rgba(0,0,0,.25)}
nav{max-width:1080px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:14px 22px}
nav .logo{font-weight:800;font-size:1.15rem;color:#fff;text-decoration:none;letter-spacing:.3px}
nav .logo span{color:#d9b45b}
nav .links a{color:#cfd9e4;text-decoration:none;margin-left:22px;font-size:.95rem}
nav .links a:hover{color:#d9b45b}
.hero{background:linear-gradient(160deg,#0f2a43 0%,#123a5e 60%,#0f2a43 100%);color:#fff;padding:78px 22px 88px;text-align:center}
.hero h1{font-size:2.6rem;line-height:1.2;max-width:820px;margin:0 auto 16px}
.hero h1 em{color:#d9b45b;font-style:normal}
.hero p{max-width:640px;margin:0 auto 30px;color:#b8c7d6;font-size:1.08rem}
.btn{display:inline-block;background:#d9b45b;color:#0f2a43;font-weight:700;padding:13px 28px;border-radius:6px;text-decoration:none;border:none;cursor:pointer;font-size:1rem}
.btn.ghost{background:transparent;color:#d9b45b;border:2px solid #d9b45b;margin-left:12px}
.wrap{max-width:1080px;margin:0 auto;padding:52px 22px}
h2.sec{font-size:1.6rem;color:#0f2a43;margin-bottom:8px}
h2.sec:after{content:"";display:block;width:56px;height:3px;background:#d9b45b;margin-top:6px}
.sub{color:#66707c;margin-bottom:26px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:22px}
.card{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(15,42,67,.08);text-decoration:none;color:inherit;display:flex;flex-direction:column;transition:transform .15s}
.card:hover{transform:translateY(-3px)}
.card .band{height:6px;background:linear-gradient(90deg,#d9b45b,#0f2a43)}
.card .in{padding:20px 22px 24px}
.card h3{font-size:1.12rem;color:#0f2a43;margin-bottom:8px;line-height:1.35}
.card p{font-size:.92rem;color:#5b6673}
.chip{display:inline-block;background:#eef3f8;color:#0f2a43;border-radius:20px;font-size:.74rem;font-weight:700;padding:3px 12px;margin:0 6px 10px 0;text-transform:uppercase;letter-spacing:.4px}
.meta{color:#8a94a1;font-size:.8rem;margin-top:14px}
article.post{max-width:760px;margin:0 auto;background:#fff;padding:46px 48px;border-radius:10px;box-shadow:0 2px 14px rgba(15,42,67,.08)}
article.post h1{color:#0f2a43;font-size:2rem;line-height:1.25;margin:10px 0 6px}
article.post h2{color:#0f2a43;margin-top:1.9em;border-bottom:2px solid #eef2f6;padding-bottom:.25em}
article.post ul{margin:12px 0 12px 22px}
article.post li{margin:.4em 0}
article.post hr{border:none;border-top:1px solid #e6ebf1;margin:2.2em 0}
.share{margin-top:26px;padding-top:18px;border-top:1px solid #eef2f6;font-size:.9rem}
.share a{display:inline-block;margin-right:10px;padding:7px 16px;border-radius:20px;text-decoration:none;color:#fff;font-weight:600}
.share .li{background:#0a66c2}.share .fb{background:#1877f2}.share .x{background:#111}
aside.ctabox{max-width:760px;margin:26px auto 0;background:#0f2a43;color:#fff;border-radius:10px;padding:26px 30px;text-align:center}
aside.ctabox p{color:#b8c7d6;margin:6px 0 16px}
footer{background:#0b2136;color:#8fa3b8;margin-top:60px;padding:36px 22px;font-size:.85rem;text-align:center}
footer b{color:#d9b45b}
form input,form textarea{width:100%;padding:11px 13px;margin:6px 0;border:1px solid #cfd6de;border-radius:6px;font:inherit}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
@media(max-width:640px){.two{grid-template-columns:1fr}.hero h1{font-size:1.9rem}article.post{padding:30px 22px}}
"""

# ------------------------------------------------------------- chat widget ---
CHAT_JS = r"""
(function () {
  var A = window.PB_ARTICLES || [];
  function find(re) { for (var i = 0; i < A.length; i++) if (re.test(A[i].title + A[i].cat)) return A[i]; return null; }
  var box = document.createElement('div');
  box.innerHTML =
    '<button id="pbFab" style="position:fixed;right:22px;bottom:22px;z-index:99;width:58px;height:58px;border-radius:50%;background:#d9b45b;border:none;font-size:26px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.3)">&#128172;</button>' +
    '<div id="pbChat" style="display:none;position:fixed;right:22px;bottom:92px;z-index:99;width:340px;max-width:calc(100vw - 32px);height:460px;max-height:70vh;background:#fff;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.35);display:none;flex-direction:column;overflow:hidden;font-family:inherit">' +
    '<div style="background:#0f2a43;color:#fff;padding:14px 16px"><b>Property Assistant</b><div style="font-size:.78rem;color:#9fd6a4">&#9679; Online 24/7</div></div>' +
    '<div id="pbMsgs" style="flex:1;overflow-y:auto;padding:14px;background:#f4f6f9"></div>' +
    '<div id="pbChips" style="padding:8px 12px;background:#f4f6f9;display:flex;flex-wrap:wrap;gap:6px"></div>' +
    '<form id="pbForm" style="display:flex;border-top:1px solid #e2e7ee"><input id="pbIn" placeholder="Type a message..." style="flex:1;border:none;padding:12px;font:inherit;outline:none"><button style="background:#0f2a43;color:#fff;border:none;padding:0 16px;cursor:pointer">&#10148;</button></form>' +
    '</div>';
  document.body.appendChild(box);
  var msgs = box.querySelector('#pbMsgs'), chips = box.querySelector('#pbChips');
  var fab = box.querySelector('#pbFab'), panel = box.querySelector('#pbChat');
  var waitingForEmail = false;
  fab.onclick = function () {
    var open = panel.style.display === 'flex';
    panel.style.display = open ? 'none' : 'flex';
    if (!open && !msgs.childElementCount) {
      bot("Hi there! I'm the assistant for this property blog - here 24/7 for questions about our articles, strategies (HMO, BRR, buy-to-let) or how to book a free chat. How can I help?");
      showChips(["What is BRR?", "HMO basics", "First buy-to-let", "Book a free chat"]);
    }
  };
  function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}
  function add(who, html) {
    var m = document.createElement('div');
    m.style.cssText = 'max-width:85%;margin:6px 0;padding:10px 13px;border-radius:12px;font-size:.9rem;line-height:1.45;' +
      (who === 'bot' ? 'background:#fff;border:1px solid #e2e7ee;' : 'background:#0f2a43;color:#fff;margin-left:auto;');
    m.innerHTML = html;
    msgs.appendChild(m); msgs.scrollTop = msgs.scrollHeight;
  }
  function bot(t) { setTimeout(function(){ add('bot', t); }, 350); }
  function showChips(list) {
    chips.innerHTML = '';
    list.forEach(function (c) {
      var b = document.createElement('button');
      b.textContent = c;
      b.style.cssText = 'background:#eef3f8;border:none;border-radius:16px;padding:6px 12px;font-size:.78rem;cursor:pointer';
      b.onclick = function () { user(c); };
      chips.appendChild(b);
    });
  }
  function articleLink(a) {
    return a ? '<br><a href="' + a.slug + '.html" style="color:#0a66c2;font-weight:600">Read: ' + esc(a.title) + ' &rarr;</a>' : '';
  }
  function answer(q) {
    var t = q.toLowerCase();
    if (waitingForEmail) {
      var m = t.match(/[\w.+-]+@[\w-]+\.[\w.]+/);
      if (m) {
        waitingForEmail = false;
        var leads = []; try { leads = JSON.parse(localStorage.pb_leads || '[]'); } catch (e) {}
        leads.push({ email: m[0], when: new Date().toISOString() });
        localStorage.pb_leads = JSON.stringify(leads);
        try {
          var fk = document.querySelector('form[data-w3f]');
          if (fk) fetch('https://api.web3forms.com/submit', { method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accesskey: fk.dataset.w3f, subject: 'New chat lead - SGJM blog',
              email: m[0], message: 'Chat visitor left their email on ' + location.href }) });
          var su = fk.dataset.sheet;
          if (su) fetch(su, { method: 'POST', mode: 'no-cors',
            headers: { 'Content-Type': 'text/plain;charset=utf-8' },
            body: JSON.stringify({ source: 'chat assistant', email: m[0] }) });
        } catch (e) {}
        return "Perfect - thanks! I've noted <b>" + esc(m[0]) + "</b> and we'll be in touch shortly. Meanwhile, browse the articles above or email us any time. \u{1F3E0}";
      }
      waitingForEmail = false;
    }
    if (/\b(hi|hello|hey)\b/.test(t)) return "Hello! Ask me about BRR, HMOs, buy-to-let, or how to book a free chat.";
    if (/brr|refurbish|refinance/.test(t)) { var a = find(/BRR/i); return "BRR = <b>Buy, Refurbish, Refinance</b>: buy below market value, add value through refurbishment, then refinance on the new valuation to recycle your capital into the next deal." + articleLink(a); }
    if (/hmo|licen|room/.test(t)) { var b = find(/HMO/i); return "An HMO rents by the room, which can lift yields well above single lets - but licensing (mandatory, additional, selective) and setup costs are the key details." + articleLink(b); }
    if (/first|start|begin|new/.test(t)) { var c = find(/First|Buy-to-Let/i); return "For your first buy-to-let: sort your structure (personal vs company), budget ~25% deposit plus the extra SDLT surcharge, and buy for the tenant - not for yourself." + articleLink(c); }
    if (/mortgage|finance|refinan|equity/.test(t)) { var d = find(/Refinanc|Finance/i); return "Refinancing releases equity from existing properties - typically up to ~75% LTV on the new valuation - to fund your next purchase. Timing and costs (ERCs, fees) decide whether it's worth it." + articleLink(d); }
    if (/deal|sourc|find/.test(t)) { var e = find(/Sourc|Deal/i); return "The best deals come from auctions, direct-to-vendor, probate and networking - and a genuine bargain always has evidence: comps, real quotes, a proven exit." + articleLink(e); }
    if (/contact|talk|human|call|email|work|service|help me|invest with|advert|book|chat|consult/.test(t)) {
      waitingForEmail = true;
      return "Of course! For sales, partnerships or support we reply within one working day. What's the best <b>email address</b> for us to reach you?";
    }
    if (/sourc|deal for me|find me a|off-market/.test(t)) return "SGJM's sourcing service launches as soon as our registrations complete - meanwhile we're building the <b>investor waitlist</b>. Type 'book a free chat' to leave your buying criteria and you'll be first in line (plus I'll send you the free sourcing checklist today).";
    if (/dubai/.test(t)) return "For Dubai I introduce investors to vetted, RERA-licensed partners - plain-English market education, and any referral fee is always disclosed. Want the Dubai intro pack? Type 'book a free chat'.";
    if (/yield|return|profit/.test(t)) return "Yields vary by strategy: well-run HMOs in strong areas can reach double-digit gross yields, while single lets typically land lower with less effort. The articles include worked examples.";
    return "I can help with: <b>BRR</b>, <b>HMOs</b>, <b>first buy-to-let</b>, <b>refinancing</b>, <b>deal sourcing</b> - or type 'book a free chat' to leave your details.";
  }
  function user(t) { add('user', esc(t)); setTimeout(function () { add('bot', answer(t)); }, 500); }
  box.querySelector('#pbForm').onsubmit = function (e) {
    e.preventDefault();
    var v = box.querySelector('#pbIn').value.trim();
    if (!v) return;
    box.querySelector('#pbIn').value = '';
    user(v);
  };
})();
"""

# --------------------------------------------------------------- templates ---
SHELL = """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="assets/og-image.jpg">
<meta property="og:type" content="website">
<link rel="stylesheet" href="assets/css/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#127968;</text></svg>">
</head>
<body>
<header class="top"><nav>
  <a class="logo" href="index.html">Property<span>Investment</span>Insights</a>
  <span class="links"><a href="index.html">Articles</a><a href="about.html">About</a><a href="contact.html">Contact</a></span>
</nav></header>
{body}
<footer>
  <b>SGJM</b> &middot; UK property education, not financial advice.<br>
  Tax treatment, licensing and lending criteria change - always confirm with your local council and qualified professionals.<br>
  &copy; 2026 &middot; Built with the Property Blog Bot &middot; <a href="privacy.html" style="color:#8fa3b8">Privacy</a>
</footer>
<script>
/* Resilient forms: Web3Forms -> FormSubmit -> prefilled email. */
document.addEventListener('submit', function (e) {{
  var f = e.target;
  if (!f.dataset || (!f.dataset.fallback && !f.dataset.w3f)) return;
  e.preventDefault();
  var d = new FormData(f);
  /* Log the lead to the private Google Sheet (fire-and-forget) */
  if (f.dataset.sheet) {{
    try {{
      var pl = {{}};
      d.forEach(function (v, k) {{ if (k.charAt(0) !== '_') pl[k] = v; }});
      pl.source = f.dataset.sheetsrc || 'website form';
      fetch(f.dataset.sheet, {{ method: 'POST', mode: 'no-cors',
        headers: {{ 'Content-Type': 'text/plain;charset=utf-8' }},
        body: JSON.stringify(pl) }});
    }} catch (e2) {{}}
  }}
  function ok() {{ f.innerHTML = '<p style="color:#0f7a3d;font-weight:700;padding:12px 0">&#10004; Sent - thank you! We reply within one working day.</p>'; }}
  function mailto() {{
    location.href = 'mailto:' + f.dataset.fallback +
      '?subject=' + encodeURIComponent(d.get('_subject') || 'SGJM enquiry') +
      '&body=' + encodeURIComponent('Name: ' + (d.get('name') || '') +
        '\\nEmail: ' + (d.get('email') || '') +
        '\\nSubject: ' + (d.get('subject') || '') +
        '\\n\\n' + (d.get('message') || d.get('email') || ''));
  }}
  function tryFS() {{
    var body = new URLSearchParams();
    d.forEach(function (v, k) {{ body.append(k, v); }});
    fetch(f.action, {{ method: 'POST', headers: {{ 'Accept': 'application/json' }}, body: body }})
      .then(function (r) {{ if (!r.ok) throw 0; ok(); }})
      .catch(mailto);
  }}
  if (f.dataset.w3f) {{
    var payload = {{ access_key: f.dataset.w3f, subject: d.get('_subject') || 'SGJM enquiry' }};
    d.forEach(function (v, k) {{ if (k.charAt(0) !== '_') payload[k] = v; }});
    fetch('https://api.web3forms.com/submit', {{ method: 'POST',
        headers: {{ 'Content-Type': 'application/json', 'Accept': 'application/json' }},
        body: JSON.stringify(payload) }})
      .then(function (r) {{ return r.json(); }})
      .then(function (j) {{ if (j && j.success) ok(); else tryFS(); }})
      .catch(tryFS);
  }} else {{ tryFS(); }}
}});
</script>
<script>window.PB_ARTICLES = {articles_json};</script>
<script src="assets/js/chat.js"></script>
</body>
</html>
"""

HOME = """
<section class="hero">
  <h1>UK Property Investing, <em>Without the Fluff</em></h1>
  <p>Practical breakdowns of HMOs, BRR, buy-to-let and deal sourcing - with real numbers, a Scunthorpe &amp; Humber focus, and zero hype.</p>
  <a class="btn" href="#latest">Read the latest</a><a class="btn ghost" href="contact.html">Book a Free Chat</a>
</section>
<section class="wrap" id="latest">
  <h2 class="sec">Featured articles</h2>
  <p class="sub">Fresh from the blog - one new breakdown every week.</p>
  <div class="grid">{featured}</div>
</section>
{strategy_sections}
<section class="wrap">
  <aside class="ctabox" style="max-width:none;margin:0">
    <h2 style="color:#fff">Get every new breakdown first</h2>
    <p>One email a week: HMO yields, BRR case studies and lending updates. No spam.</p>
    <form action="{newsletter_action}" method="POST" data-fallback="{fb_email}" data-w3f="{w3f_key}" data-sheet="{sheet_url}" data-sheetsrc="homepage newsletter" style="max-width:460px;margin:0 auto;display:flex;gap:10px">
      <input type="hidden" name="_subject" value="New SGJM newsletter signup">
      <input type="hidden" name="_captcha" value="false">
      <input type="email" name="email" required placeholder="you@example.com" style="flex:1;border-radius:6px;border:none;padding:12px">
      <button class="btn" type="submit">Subscribe</button>
    </form>
    <p style="font-size:.75rem;color:#c8d4e2;margin-top:8px">By subscribing you agree to our <a href="privacy.html" style="color:#fff">privacy policy</a>. Unsubscribe any time.</p>
  </aside>
</section>
"""

CARD = """<a class="card" href="{href}"><div class="band"></div><div class="in">
  <div>@CHIPS@</div><h3>{title}</h3><p>{excerpt}</p>
  <div class="meta">@DATE@</div>
</div></a>"""

POST_PAGE = """
<section class="wrap" style="padding-top:34px">
  <article class="post">
    <div>@CHIPS@</div>
    <h1>@TITLE@</h1>
    <div class="meta">@DATE@</div>
    @CONTENT@
    <div class="share">Share this article:
      <a class="li" data-net="linkedin" href="#">LinkedIn</a>
      <a class="fb" data-net="facebook" href="#">Facebook</a>
      <a class="x" data-net="x" href="#">X</a>
    </div>
  </article>
  <aside class="ctabox"><h3 style="color:#fff">Enjoyed this?</h3>
  <p>A new practical breakdown lands every week - ask the assistant (bottom right) anything.</p>
  <a class="btn" href="index.html">More articles</a></aside>
</section>
<script>
document.querySelectorAll('.share a').forEach(function(a){
  var u = encodeURIComponent(location.href), t = encodeURIComponent(document.title);
  a.href = {linkedin:'https://www.linkedin.com/sharing/share-offsite/?url='+u,
            facebook:'https://www.facebook.com/sharer/sharer.php?u='+u,
            x:'https://twitter.com/intent/tweet?text='+t+'&url='+u}[a.dataset.net];
});
</script>
"""

ABOUT = """
<section class="wrap" style="max-width:820px">
  <h2 class="sec">About this site</h2>
  <p style="margin:18px 0">SGJM is a UK property education blog with a Scunthorpe and North Lincolnshire
  heart. We publish practical, numbers-first breakdowns of the strategies real investors use -
  HMOs, BRR, buy-to-let, refinancing and deal sourcing - written to be actionable, not aspirational.</p>
  <p style="margin:18px 0">Everything here is general information, not financial advice: rules, taxes and lending
  criteria change, and every deal is different. Always verify with your local council, lender and
  qualified professionals.</p>
  <p style="margin:18px 0">Want to collaborate, advertise or invest alongside us? <a href="contact.html">Get in touch</a> -
  or ask the assistant in the corner, available 24/7.</p>
</section>
"""

CONTACT = """
<section class="wrap" style="max-width:760px">
  <h2 class="sec">Contact & enquiries</h2>
  <p class="sub">Sales, partnerships, advertising or reader questions - we reply within one working day.</p>
  <form action="{contact_action}" method="POST" data-fallback="{contact_email}" data-w3f="{w3f_key}" data-sheet="{sheet_url}" data-sheetsrc="contact form">
    <input type="hidden" name="_subject" value="New SGJM website enquiry">
    <input type="hidden" name="_captcha" value="false">
    <div class="two">
      <input name="name" placeholder="Your name" required>
      <input name="email" type="email" placeholder="Email address" required>
    </div>
    <input name="subject" placeholder="Subject (e.g. joint venture, advertising, question)">
    <textarea name="message" rows="6" placeholder="How can we help?" required></textarea>
    <button class="btn" type="submit">Send message</button>
    <p style="font-size:.78rem;color:#66707c;margin:10px 0 0">By submitting you agree to our <a href="privacy.html">privacy policy</a>.</p>
  </form>
  <p style="margin-top:22px;font-size:.9rem;color:#66707c">Prefer email? Use the form above, or the chat assistant
  (bottom right) can take your details - we reply within one working day.</p>
</section>
"""

PRIVACY = """
<section class="wrap" style="max-width:760px">
  <h2 class="sec">Privacy Policy</h2>
  <p class="sub">Last updated: September 2026</p>
  <p style="margin:14px 0"><b>What we collect.</b> If you use the contact form or the chat assistant's
  lead capture, we receive the name, email address and message you choose to share.
  Newsletter sign-ups collect your email address only.</p>
  <p style="margin:14px 0"><b>How we use it.</b> Solely to respond to your enquiry or send the
  newsletter you requested. We never sell your data. Forms are processed by our email
  form-delivery providers (Web3Forms and FormSubmit) on our behalf. Leads are also logged to a
  private spreadsheet so no enquiry is ever lost.</p>
  <p style="margin:14px 0"><b>Cookies & storage.</b> This site sets no advertising or tracking
  cookies. When you leave details with the chat assistant they are passed to us (via our form
  provider) so we can respond, and a copy is kept in your own browser's local storage
  so nothing is lost if the page reloads.</p>
  <p style="margin:14px 0"><b>Your rights.</b> You may request a copy or deletion of any details
  you've sent us at any time by emailing <a href="mailto:{contact_email}">{contact_email}</a>.</p>
  <p style="margin:14px 0"><b>Third-party links.</b> Articles link to external sites (e.g. social
  networks); their own privacy policies apply once you leave this site.</p>
</section>
"""


def parse_post(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2)


def main():
    ap = argparse.ArgumentParser(description="Build the static blog website.")
    ap.add_argument("--posts", default="_posts")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    ap.add_argument("--newsletter-action", default=None,
                    help="Form endpoint (default: https://formsubmit.co/<contact-email>)")
    ap.add_argument("--contact-action", default=None,
                    help="Form endpoint (default: https://formsubmit.co/<contact-email>)")
    ap.add_argument("--contact-email", default="hello@example.com")
    ap.add_argument("--w3f-key", default="7d7560e5-c7f8-41fb-865d-9bbdd3dfb159",
                    help="Web3Forms access key for on-page form delivery")
    ap.add_argument("--sheet-url", default="https://script.google.com/macros/s/AKfycbyEU1RcmAaQOIGZF01Jk_bBJvm8XmlvjSgS16iR-nfJ9WEqcPL8pF7ne29Asm6lYCg0fA/exec",
                    help="Google Apps Script web-app URL that logs leads to a spreadsheet")
    args = ap.parse_args()

    posts = []
    if os.path.isdir(args.posts):
        for f in sorted(os.listdir(args.posts), reverse=True):
            if f.endswith(".md"):
                parsed = parse_post(os.path.join(args.posts, f))
                if parsed:
                    meta, body = parsed
                    meta["slug"] = f[11:-3] if len(f) > 14 else f[:-3]
                    meta["body"] = body
                    posts.append(meta)
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    articles_json = "[{}]".format(", ".join(
        '{{"slug":"{}","title":"{}","cat":"{}","excerpt":"{}"}}'.format(
            p["slug"], p["title"].replace('"', "'"), p.get("category", p.get("categories", "")),
            p.get("excerpt", "").replace('"', "'")) for p in posts))

    out = args.out
    for d in ("", "assets/css", "assets/js", "posts"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    open(os.path.join(out, "assets/css/style.css"), "w").write(CSS)
    open(os.path.join(out, "assets/js/chat.js"), "w").write(CHAT_JS)
    if os.path.exists("assets/og-image.jpg"):
        shutil.copy("assets/og-image.jpg", os.path.join(out, "assets/og-image.jpg"))
    if os.path.isdir("output/slides"):
        dst = os.path.join(out, "assets/slides")
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir("output/slides"):
            shutil.copy(os.path.join("output/slides", f), os.path.join(dst, f))

    def shell(title, desc, body):
        return SHELL.format(title=title, desc=desc, body=body, articles_json=articles_json)

    def card(p):
        chips = "".join('<span class="chip">%s</span>' % c for c in
                        p.get("categories", p.get("category", "Property")).split())
        return CARD.format(href="posts/%s.html" % p["slug"], chips=chips, title=p["title"],
                           excerpt=p.get("excerpt", ""), date=p.get("date", ""))

    # home
    featured = "".join(card(p) for p in posts[:3]) or "<p>No articles yet.</p>"
    cats = {}
    for p in posts:
        for c in p.get("categories", "Property").split():
            cats.setdefault(c, []).append(p)
    sec_html = ""
    for c, plist in cats.items():
        sec_html += ('<section class="wrap" id="%s" style="padding-top:0">'
                     '<h2 class="sec">%s</h2><p class="sub">%d article%s</p>'
                     '<div class="grid">%s</div></section>') % (
            c.lower(), c, len(plist), "s" if len(plist) != 1 else "",
            "".join(card(p) for p in plist))
    home = HOME.format(featured=featured, strategy_sections=sec_html,
                       newsletter_action=(args.newsletter_action or
                                          "https://formsubmit.co/" + args.contact_email),
                       fb_email=args.contact_email, w3f_key=args.w3f_key,
                       sheet_url=args.sheet_url)
    open(os.path.join(out, "index.html"), "w").write(
        shell(BRAND + " - " + "UK Property Investment Blog", TAGLINE, home))

    # article pages
    for p in posts:
        chips = "".join('<span class="chip">%s</span>' % c for c in
                        p.get("categories", p.get("category", "Property")).split())
        body_html = md_to_html_body(p["body"])
        page = (POST_PAGE.replace("@CHIPS@", chips).replace("@TITLE@", p["title"])
                .replace("@DATE@", p.get("date", "")).replace("@CONTENT@", body_html))
        open(os.path.join(out, "posts/%s.html" % p["slug"]), "w").write(
            shell(p["title"] + " - " + BRAND, p.get("excerpt", ""), page))

    # static pages
    open(os.path.join(out, "about.html"), "w").write(shell("About - " + BRAND, TAGLINE, ABOUT))
    open(os.path.join(out, "contact.html"), "w").write(shell(
        "Contact - " + BRAND, "Get in touch",
        CONTACT.format(contact_action=(args.contact_action or
                                       "https://formsubmit.co/" + args.contact_email),
                       contact_email=args.contact_email, w3f_key=args.w3f_key,
                       sheet_url=args.sheet_url)))
    open(os.path.join(out, "privacy.html"), "w").write(shell(
        "Privacy Policy - " + BRAND, "How we handle your data",
        PRIVACY.format(contact_email=args.contact_email)))
    open(os.path.join(out, "404.html"), "w").write(shell(
        "Page not found", "404",
        '<section class="wrap"><h2 class="sec">404 - page not found</h2>'
        '<p style="margin:16px 0">The page you wanted has moved or never existed. '
        '<a href="index.html">Back to the latest articles</a>.</p></section>'))

    # RSS
    items = ""
    for p in posts[:10]:
        items += ("<item><title>%s</title><link>%s/posts/%s.html</link>"
                  "<description>%s</description><pubDate>%s</pubDate></item>") % (
            p["title"].replace("&", "&amp;"), args.site_url.rstrip("/"), p["slug"],
            p.get("excerpt", "").replace("&", "&amp;"), p.get("date", ""))
    open(os.path.join(out, "feed.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        '<title>%s</title><link>%s</link><description>%s</description>%s'
        '</channel></rss>' % (BRAND, args.site_url or "/", TAGLINE, items))

    print("Site built into %s/ : %d article page(s) + home/about/contact/404/RSS." % (out, len(posts)))
    print("Preview locally:  python3 -m http.server 8000 -d %s" % out)
    print("GitHub Pages:     repo Settings > Pages > source: deploy from branch, folder /docs")


if __name__ == "__main__":
    main()
