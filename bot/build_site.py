#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static blog site builder for GitHub Pages (no Jekyll required)
==============================================================
v2 - "organised blog" redesign.

Reads the generated Markdown articles in _posts/ and builds the whole static
blog into blog/ (or --out):

  * Index: hero + ONE grid of every article, each listed exactly once, with
    topic filter chips (no repeated sections, no duplicated cards).
  * Duplicate-slug protection: if the same topic was published twice, only the
    newest version is kept, so an article can never appear twice or overwrite
    an older one's page.
  * Article pages: dark hero band, readable sheet, styled headings/lists,
    "Key takeaways" callout, share buttons, reading time, related articles.
  * About / Contact / Privacy / 404, RSS feed, chat assistant, forms.

Usage:
  python3 build_site.py --posts _posts --out ../blog --site-url https://mysite/blog
"""
import argparse
import datetime
import html as html_mod
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = "SGJM"
TAGLINE = ("Practical UK property investing: HMOs, BRR, buy-to-let and real deal "
           "numbers for Scunthorpe & North Lincolnshire.")

# ------------------------------------------------------------------ topics ---
# (label, keywords) - checked in order; a post gets up to two topics.
TOPICS = [
    ("Scunthorpe",   ["scunthorpe", "lincolnshire", "dn15", "dn16", "dn17", "humber"]),
    ("Dubai",        ["dubai", "rera", "off-plan", "offplan"]),
    ("Auctions",     ["auction", "lot", "hammer"]),
    ("Buy-to-let",   ["buy-to-let", "buy to let", "first-buy", "btl", "landlord", "tenant", "rental"]),
    ("HMO",          ["hmo", "house in multiple"]),
    ("BRR & refurb", ["brr", "refurb", "flip"]),
    ("Finance",      ["refinanc", "remortgage", "mortgage", "lending", "sdlt"]),
    ("Sourcing",     ["sourcing", "sourcer", "deal sourcing", "below-market", "off-market"]),
    ("Market data",  ["market", "prices", "hpi", "comps", "data"]),
    ("Guides",       ["guide", "how to", "checklist", "explained", "education", "strategy"]),
]

TOPIC_ICON = {
    "Scunthorpe":   "\U0001F3D8\uFE0F",
    "Dubai":        "\U0001F307",
    "Auctions":     "\U0001F528",
    "Buy-to-let":   "\U0001F511",
    "HMO":          "\U0001F3E0",
    "BRR & refurb": "\U0001F527",
    "Finance":      "\U0001F4B7",
    "Sourcing":     "\U0001F9ED",
    "Market data":  "\U0001F4CA",
    "Guides":       "\U0001F4D8",
}
TOPIC_COLOUR = {
    "Scunthorpe":   "#2563eb",
    "Dubai":        "#9333ea",
    "Auctions":     "#b45309",
    "Buy-to-let":   "#15803d",
    "HMO":          "#be123c",
    "BRR & refurb": "#0369a1",
    "Finance":      "#0f766e",
    "Sourcing":     "#6d28d9",
    "Market data":  "#0e7490",
    "Guides":       "#475569",
}
DEFAULT_ACCENT = "#0b1f33"


def topics_for(post):
    """Up to two topic labels for a post (order = TOPICS order)."""
    blob = ("%s %s %s" % (post.get("categories", post.get("category", "")),
                          post.get("slug", ""), post.get("title", ""))).lower()
    out = []
    for label, keys in TOPICS:
        if any(k in blob for k in keys):
            out.append(label)
        if len(out) == 2:
            break
    return out or ["Guides"]


# ------------------------------------------------------------------ styles ---
CSS = """
:root{
  --ink:#0b1f33; --ink-2:#12365a; --gold:#e6bb62; --gold-d:#c99d3f;
  --paper:#ffffff; --soft:#f4f7fb; --line:#e4eaf2; --text:#17263a; --muted:#5f6e80;
  --radius:16px; --shadow:0 6px 24px rgba(11,31,51,.08);
  --shadow-lg:0 18px 48px rgba(11,31,51,.16); --max:1120px;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  color:var(--text);line-height:1.68;-webkit-font-smoothing:antialiased;
  background:
    radial-gradient(1100px 520px at 100% -180px,#e8f0fb 0%,transparent 60%),
    radial-gradient(900px 460px at -8% 220px,#f8f3e6 0%,transparent 55%),
    var(--soft);
}
body::before{
  content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:
    linear-gradient(rgba(11,31,51,.032) 1px,transparent 1px),
    linear-gradient(90deg,rgba(11,31,51,.032) 1px,transparent 1px);
  background-size:46px 46px;
}
a{color:#1d4ed8}
img{max-width:100%;height:auto}

/* ---------- header ---------- */
header.top{position:sticky;top:0;z-index:60;background:rgba(9,24,40,.94);
  backdrop-filter:saturate(140%) blur(10px);border-bottom:1px solid rgba(255,255,255,.07)}
nav{max-width:var(--max);margin:0 auto;display:flex;align-items:center;
  justify-content:space-between;gap:16px;padding:13px 22px}
nav .logo{font-weight:800;font-size:1.08rem;color:#fff;text-decoration:none;letter-spacing:.2px}
nav .logo span{color:var(--gold)}
nav .links{display:flex;align-items:center;gap:20px}
nav .links a{color:#cfdaea;text-decoration:none;font-size:.93rem}
nav .links a:hover{color:var(--gold)}
nav .links a.pill{border:1px solid rgba(230,187,98,.5);color:var(--gold);
  padding:7px 15px;border-radius:999px;font-weight:600}
nav .links a.pill:hover{background:var(--gold);color:var(--ink)}
@media(max-width:720px){nav .links a:not(.pill){display:none}}

/* ---------- hero ---------- */
.hero{position:relative;overflow:hidden;color:#fff;padding:86px 22px 104px;
  background:linear-gradient(140deg,#08182a 0%,#12365a 55%,#0b1f33 100%)}
.hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:
    radial-gradient(620px 320px at 86% 6%,rgba(230,187,98,.22),transparent 62%),
    radial-gradient(rgba(255,255,255,.10) 1px,transparent 1px) 0 0/24px 24px}
.hero-in{position:relative;z-index:1;max-width:var(--max);margin:0 auto}
.kicker{display:inline-block;font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;
  color:var(--gold);border:1px solid rgba(230,187,98,.45);border-radius:999px;
  padding:6px 14px;margin-bottom:20px;font-weight:700}
.hero h1{font-size:clamp(2rem,4.4vw,3rem);line-height:1.15;letter-spacing:-.5px;max-width:840px}
.hero h1 em{color:var(--gold);font-style:normal}
.hero p{max-width:660px;margin-top:18px;color:#bdcbdb;font-size:1.06rem}
.hero-cta{margin-top:30px;display:flex;flex-wrap:wrap;gap:12px}
.hero-stats{margin-top:38px;display:flex;flex-wrap:wrap;gap:26px;color:#93a7bd;font-size:.9rem}
.hero-stats b{color:#fff;font-size:1.15rem;display:block;line-height:1.2}

/* ---------- buttons ---------- */
.btn{display:inline-block;background:var(--gold);color:var(--ink);font-weight:700;
  padding:13px 26px;border-radius:999px;text-decoration:none;border:none;cursor:pointer;
  font-size:.98rem;transition:transform .15s ease,box-shadow .15s ease}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(230,187,98,.32)}
.btn.ghost{background:transparent;color:#fff;border:1.5px solid rgba(255,255,255,.35)}
.btn.ghost:hover{border-color:var(--gold);color:var(--gold);box-shadow:none}

/* ---------- layout ---------- */
.wrap{max-width:var(--max);margin:0 auto;padding:56px 22px}
.wrap.tight{padding-top:34px}
h2.sec{font-size:1.55rem;color:var(--ink);letter-spacing:-.3px;margin-bottom:6px}
h2.sec:after{content:"";display:block;width:54px;height:3px;background:var(--gold);margin-top:8px;border-radius:2px}
.sub{color:var(--muted);margin-bottom:24px}

/* ---------- filters ---------- */
.filters{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 28px}
.filters button{border:1px solid var(--line);background:#fff;color:var(--ink);
  padding:9px 16px;border-radius:999px;font-weight:600;font-size:.87rem;cursor:pointer;
  transition:border-color .15s,background .15s,color .15s;font-family:inherit}
.filters button:hover{border-color:var(--gold-d)}
.filters button.active{background:var(--ink);color:#fff;border-color:var(--ink)}
.filters .count{color:var(--muted);font-size:.87rem;align-self:center;margin-left:4px}

/* ---------- cards ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:24px}
.card{position:relative;display:flex;flex-direction:column;background:var(--paper);
  border-radius:var(--radius);overflow:hidden;text-decoration:none;color:inherit;
  box-shadow:var(--shadow);border:1px solid rgba(11,31,51,.06);
  transition:transform .18s ease,box-shadow .18s ease}
.card:hover{transform:translateY(-4px);box-shadow:var(--shadow-lg)}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--accent,#0b1f33)}
.card .in{padding:22px 24px 24px 26px;display:flex;flex-direction:column;flex:1}
.card .top{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.card .ico{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;
  font-size:1.25rem;background:var(--accent,#0b1f33);flex:0 0 auto;box-shadow:0 6px 14px rgba(11,31,51,.18)}
.card h3{font-size:1.12rem;line-height:1.35;color:var(--ink);letter-spacing:-.2px}
.card p{font-size:.92rem;color:#4d5d70;margin-top:9px}
.card .meta{margin-top:auto;padding-top:16px;color:#8a96a6;font-size:.79rem;
  display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.card .more{color:#1d4ed8;font-weight:700;font-size:.84rem}
.card.feature{grid-column:span 2}
.card.feature h3{font-size:1.6rem;line-height:1.25}
.card.feature p{font-size:1rem}
@media(max-width:760px){.card.feature{grid-column:span 1}.card.feature h3{font-size:1.25rem}}
.chip{display:inline-block;background:#eef3fa;color:var(--ink);border-radius:999px;
  font-size:.7rem;font-weight:800;padding:4px 11px;margin:0 6px 0 0;
  text-transform:uppercase;letter-spacing:.5px}
.badge{display:inline-block;background:var(--gold);color:#3b2c05;border-radius:999px;
  font-size:.7rem;font-weight:800;padding:4px 11px;text-transform:uppercase;letter-spacing:.5px}
.empty{display:none;padding:34px;text-align:center;color:var(--muted);
  background:#fff;border:1px dashed var(--line);border-radius:var(--radius)}

/* ---------- article ---------- */
.article-hero{position:relative;overflow:hidden;color:#fff;padding:60px 22px 74px;
  background:linear-gradient(140deg,#08182a 0%,#12365a 60%,#0b1f33 100%)}
.article-hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(560px 300px at 88% 0%,rgba(230,187,98,.18),transparent 60%)}
.article-hero .in{position:relative;z-index:1;max-width:860px;margin:0 auto}
.article-hero h1{font-size:clamp(1.7rem,3.6vw,2.4rem);line-height:1.22;
  letter-spacing:-.4px;margin:14px 0 16px}
.article-hero .meta{color:#a9bccf;font-size:.9rem;display:flex;gap:14px;flex-wrap:wrap}
.crumb{color:var(--gold);text-decoration:none;font-size:.85rem;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase}
.crumb:hover{text-decoration:underline}
.sheet{max-width:880px;margin:-42px auto 0;padding:0 22px;position:relative;z-index:2}
.sheet .paper{background:var(--paper);border-radius:18px;box-shadow:var(--shadow-lg);
  padding:46px 52px 40px;border:1px solid rgba(11,31,51,.05)}
.sheet .paper>p:first-of-type{font-size:1.06rem;color:#2b3f56}
.sheet h2{font-size:1.42rem;color:var(--ink);margin:2.1em 0 .55em;
  padding-bottom:.32em;border-bottom:2px solid var(--line);letter-spacing:-.2px}
.sheet h3{font-size:1.14rem;color:var(--ink-2);margin:1.7em 0 .4em}
.sheet p{margin:.95em 0;color:#22354b}
.sheet ul,.sheet ol{margin:1em 0 1.2em 1.35em}
.sheet li{margin:.42em 0}
.sheet strong{color:var(--ink)}
.sheet hr{border:none;border-top:1px solid var(--line);margin:2.4em 0}
.sheet blockquote{margin:1.2em 0;padding:14px 20px;background:#f7f9fd;
  border-left:4px solid var(--gold);border-radius:0 10px 10px 0;color:#33465c}
.sheet code{background:#f1f4f9;border-radius:5px;padding:2px 6px;font-size:.92em}
.sheet .tk{background:#f8fafc;border:1px solid var(--line);border-left:4px solid var(--gold);
  border-radius:12px;padding:16px 22px 6px 26px;margin-top:26px}
.sheet ul.tk-list{list-style:none;margin:0 0 14px 0;padding:0}
.sheet ul.tk-list li{position:relative;padding-left:26px;margin:.6em 0}
.sheet ul.tk-list li:before{content:"\\2713";position:absolute;left:0;top:0;
  color:#15803d;font-weight:800}
.share{margin-top:34px;padding-top:20px;border-top:1px solid var(--line);
  display:flex;gap:10px;flex-wrap:wrap;align-items:center;font-size:.88rem;color:var(--muted)}
.share a{display:inline-block;padding:8px 16px;border-radius:999px;text-decoration:none;
  color:#fff;font-weight:700;font-size:.83rem}
.share .li{background:#0a66c2}.share .fb{background:#1877f2}.share .x{background:#111}
@media(max-width:700px){.sheet .paper{padding:30px 22px}}
.related{max-width:var(--max);margin:52px auto 0;padding:0 22px}

/* ---------- cta + forms ---------- */
aside.ctabox{max-width:880px;margin:52px auto 0;background:linear-gradient(135deg,#0b1f33,#14395c);
  color:#fff;border-radius:18px;padding:34px 34px;text-align:center;box-shadow:var(--shadow)}
aside.ctabox h2,aside.ctabox h3{color:#fff}
aside.ctabox p{color:#bccbdc;margin:8px 0 18px}
form input,form textarea{width:100%;padding:12px 14px;margin:6px 0;border:1px solid #d3dae4;
  border-radius:9px;font:inherit;background:#fff}
form input:focus,form textarea:focus{outline:2px solid rgba(29,78,216,.35);border-color:#93b4f0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
@media(max-width:640px){.two{grid-template-columns:1fr}}

/* ---------- footer ---------- */
footer{background:#081b2e;color:#8fa3b8;margin-top:72px;padding:46px 22px 30px;font-size:.88rem}
footer .cols{max-width:var(--max);margin:0 auto;display:grid;
  grid-template-columns:1.4fr 1fr 1fr;gap:30px}
footer h4{color:#fff;font-size:.95rem;margin-bottom:12px}
footer a{color:#a9bccf;text-decoration:none}
footer a:hover{color:var(--gold)}
footer .brand{font-weight:800;color:#fff;font-size:1.05rem;margin-bottom:8px}
footer .brand span{color:var(--gold)}
footer .bar{max-width:var(--max);margin:30px auto 0;padding-top:18px;
  border-top:1px solid rgba(255,255,255,.09);font-size:.8rem;color:#74889e;text-align:center}
@media(max-width:760px){footer .cols{grid-template-columns:1fr}}
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

# ------------------------------------------------------------------- shell ---
SHELL = """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@TITLE@</title>
<meta name="description" content="@DESC@">
<meta property="og:title" content="@TITLE@">
<meta property="og:description" content="@DESC@">
<meta property="og:image" content="assets/og-image.jpg">
<meta property="og:type" content="@OGTYPE@">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="@CANON@">
<link rel="alternate" type="application/rss+xml" title="@BRAND@ - RSS" href="@FEED@">
<link rel="stylesheet" href="assets/css/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#127968;</text></svg>">
@JSONLD@
</head>
<body>
<header class="top"><nav>
  <a class="logo" href="index.html">Property<span>Investment</span>Insights</a>
  <span class="links">
    <a href="index.html#articles">Articles</a>
    <a href="about.html">About</a>
    <a href="contact.html">Contact</a>
    <a class="pill" href="contact.html">Free deal review</a>
  </span>
</nav></header>
@BODY@
<footer>
  <div class="cols">
    <div>
      <div class="brand">SGJM <span>Property Investment Insights</span></div>
      <p>Practical, numbers-first property investing for Scunthorpe, North Lincolnshire
      and beyond. Written for investors who want the workings, not the hype.</p>
    </div>
    <div>
      <h4>Read</h4>
      <p><a href="index.html#articles">All articles</a></p>
      <p><a href="about.html">About this blog</a></p>
      <p><a href="feed.xml">RSS feed</a></p>
    </div>
    <div>
      <h4>Get in touch</h4>
      <p><a href="contact.html">Contact &amp; enquiries</a></p>
      <p><a href="privacy.html">Privacy policy</a></p>
      <p>Replies within one working day.</p>
    </div>
  </div>
  <div class="bar">
    <b>SGJM</b> &middot; General information only - not financial, tax or legal advice.
    Always verify rules, licensing and lending criteria with your council and qualified professionals.<br>
    &copy; @YEAR@ &middot; Built with the Property Blog Bot
  </div>
</footer>
<script>
/* Resilient forms: Web3Forms -> FormSubmit -> prefilled email. */
document.addEventListener('submit', function (e) {
  var f = e.target;
  if (!f.dataset || (!f.dataset.fallback && !f.dataset.w3f)) return;
  e.preventDefault();
  var d = new FormData(f);
  if (f.dataset.sheet) {
    try {
      var pl = {};
      d.forEach(function (v, k) { if (k.charAt(0) !== '_') pl[k] = v; });
      pl.source = f.dataset.sheetsrc || 'website form';
      fetch(f.dataset.sheet, { method: 'POST', mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify(pl) });
    } catch (e2) {}
  }
  function ok() { f.innerHTML = '<p style="color:#0f7a3d;font-weight:700;padding:12px 0">&#10004; Sent - thank you! We reply within one working day.</p>'; }
  function mailto() {
    location.href = 'mailto:' + f.dataset.fallback +
      '?subject=' + encodeURIComponent(d.get('_subject') || 'SGJM enquiry') +
      '&body=' + encodeURIComponent('Name: ' + (d.get('name') || '') +
        '\\nEmail: ' + (d.get('email') || '') +
        '\\nSubject: ' + (d.get('subject') || '') +
        '\\n\\n' + (d.get('message') || d.get('email') || ''));
  }
  function tryFS() {
    var body = new URLSearchParams();
    d.forEach(function (v, k) { body.append(k, v); });
    fetch(f.action, { method: 'POST', headers: { 'Accept': 'application/json' }, body: body })
      .then(function (r) { if (!r.ok) throw 0; ok(); })
      .catch(mailto);
  }
  if (f.dataset.w3f) {
    var payload = { access_key: f.dataset.w3f, subject: d.get('_subject') || 'SGJM enquiry' };
    d.forEach(function (v, k) { if (k.charAt(0) !== '_') payload[k] = v; });
    fetch('https://api.web3forms.com/submit', { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload) })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (j && j.success) ok(); else tryFS(); })
      .catch(tryFS);
  } else { tryFS(); }
});
</script>
<script>window.PB_ARTICLES = @ARTICLES@;</script>
<script src="assets/js/chat.js"></script>
</body>
</html>
"""

# --------------------------------------------------------------------- home ---
HOME = """
<section class="hero">
  <div class="hero-in">
    <span class="kicker">Scunthorpe &amp; North Lincolnshire</span>
    <h1>UK property investing, <em>without the fluff</em>.</h1>
    <p>Practical breakdowns of HMOs, BRR, buy-to-let, auctions and deal sourcing -
    the real numbers, the risks, and what to check before you commit.</p>
    <div class="hero-cta">
      <a class="btn" href="#articles">Browse all articles</a>
      <a class="btn ghost" href="contact.html">Ask a question</a>
    </div>
    <div class="hero-stats">
      <div><b>@COUNT@</b>articles</div>
      <div><b>Weekly</b>new articles added</div>
      <div><b>Free</b>tools &amp; deal review</div>
    </div>
  </div>
</section>

<section class="wrap" id="articles">
  <h2 class="sec">All articles</h2>
  <p class="sub">Every article, newest first - filter by topic to find what matters to you.</p>
  <div class="filters" id="filters">
    <button class="active" data-cat="all">All</button>@FILTERS@
    <span class="count" id="count"></span>
  </div>
  <div class="grid" id="allGrid">@CARDS@</div>
  <div class="empty" id="empty">No articles in that topic yet - try another filter.</div>
</section>

<section class="wrap tight">
  <aside class="ctabox" style="max-width:none;margin:0">
    <h2>Get every new breakdown first</h2>
    <p>One email a week: HMO yields, BRR examples, auction stock and lending updates. No spam.</p>
    <form action="@NEWSLETTER_ACTION@" method="POST" data-fallback="@FB_EMAIL@" data-w3f="@W3F_KEY@" data-sheet="@SHEET_URL@" data-sheetsrc="homepage newsletter" style="max-width:480px;margin:0 auto;display:flex;gap:10px;flex-wrap:wrap">
      <input type="hidden" name="_subject" value="New SGJM newsletter signup">
      <input type="hidden" name="_captcha" value="false">
      <input type="email" name="email" required placeholder="you@example.com" style="flex:1;min-width:200px;border-radius:9px;border:none;padding:12px">
      <button class="btn" type="submit">Subscribe</button>
    </form>
    <p style="font-size:.78rem;color:#c8d4e2;margin-top:10px">By subscribing you agree to our
    <a href="privacy.html" style="color:#fff">privacy policy</a>. Unsubscribe any time.</p>
  </aside>
</section>

<script>
(function () {
  var btns = [].slice.call(document.querySelectorAll('#filters button'));
  var cards = [].slice.call(document.querySelectorAll('#allGrid .card'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  function apply(cat) {
    var n = 0;
    cards.forEach(function (c) {
      var cats = (c.getAttribute('data-cats') || '');
      var show = (cat === 'all') || cats.split('|').indexOf(cat) > -1;
      c.style.display = show ? '' : 'none';
      if (show) n++;
    });
    if (count) count.textContent = n + (n === 1 ? ' article' : ' articles');
    if (empty) empty.style.display = n ? 'none' : 'block';
  }
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      apply(b.getAttribute('data-cat'));
    });
  });
  apply('all');
})();
</script>
"""

CARD = """<a class="card@FEATURE@" href="@HREF@" style="--accent:@ACCENT@" data-cats="@CATS@">
  <div class="in">
    <div class="top"><span class="ico">@ICON@</span><span>@CHIPS@</span></div>
    <h3>@TITLE@</h3>
    <p>@EXCERPT@</p>
    <div class="meta"><span>@DATE@</span><span>&middot;</span><span>@READ@ min read</span>
      <span style="margin-left:auto" class="more">Read &rarr;</span></div>
  </div>
</a>"""

POST_PAGE = """
<section class="article-hero">
  <div class="in">
    <a class="crumb" href="../index.html">&larr; All articles</a>
    <h1>@TITLE@</h1>
    <div class="meta">
      <span>@DATE@</span><span>&middot;</span><span>@READ@ min read</span>
      <span>&middot;</span><span>@TOPICS@</span>
    </div>
  </div>
</section>

<div class="sheet">
  <div class="paper">
    @CONTENT@
    <div class="share">Share this article:
      <a class="li" data-net="linkedin" href="#">LinkedIn</a>
      <a class="fb" data-net="facebook" href="#">Facebook</a>
      <a class="x" data-net="x" href="#">X</a>
    </div>
  </div>
</div>

<section class="related">
  <h2 class="sec">Keep reading</h2>
  <p class="sub">More practical breakdowns from the blog.</p>
  <div class="grid">@RELATED@</div>
</section>

<section class="wrap tight">
  <aside class="ctabox">
    <h3>Want a second opinion on a deal?</h3>
    <p>Send over the numbers - price, refurb, rent and exit - and we will tell you what we would
    check first. No obligation, no fee for a first look.</p>
    <a class="btn" href="../contact.html">Ask a question</a>
  </aside>
</section>

<script>
document.querySelectorAll('.share a').forEach(function (a) {
  var u = encodeURIComponent(location.href), t = encodeURIComponent(document.title);
  a.href = { linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=' + u,
             facebook: 'https://www.facebook.com/sharer/sharer.php?u=' + u,
             x: 'https://twitter.com/intent/tweet?text=' + t + '&url=' + u }[a.dataset.net];
  a.target = '_blank'; a.rel = 'noopener';
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
  <form action="@CONTACT_ACTION@" method="POST" data-fallback="@EMAIL@" data-w3f="@W3F_KEY@" data-sheet="@SHEET_URL@" data-sheetsrc="contact form">
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
  you've sent us at any time by emailing <a href="mailto:@EMAIL@">@EMAIL@</a>.</p>
  <p style="margin:14px 0"><b>Third-party links.</b> Articles link to external sites (e.g. social
  networks); their own privacy policies apply once you leave this site.</p>
</section>
"""


# ------------------------------------------------------------ md -> html ---
def md_to_html(md):
    """Markdown -> HTML for article pages: headings, ordered + unordered lists,
    blockquotes, hrs, bold/italic, inline code and links, plus a styled
    'Key takeaways' callout."""
    out, list_mode = [], None
    takeaway_flag = False

    def inline(s):
        s = html_mod.escape(s, quote=False)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    def close_list():
        nonlocal list_mode
        if list_mode == "ul":
            out.append("</ul>")
        elif list_mode == "ol":
            out.append("</ol>")
        list_mode = None

    for raw in md.splitlines():
        s = raw.strip()
        if s.startswith(("- ", "* ")):
            if list_mode != "ul":
                close_list()
                cls = ' class="tk-list"' if takeaway_flag else ""
                out.append("<ul%s>" % cls)
                list_mode = "ul"
                takeaway_flag = False
            out.append("<li>" + inline(s[2:]) + "</li>")
            continue
        m_ol = re.match(r"^(\d{1,2})[.)]\s+(.*)$", s)
        if m_ol:
            if list_mode != "ol":
                close_list()
                out.append("<ol>")
                list_mode = "ol"
            out.append("<li>" + inline(m_ol.group(2)) + "</li>")
            continue
        close_list()
        if s.startswith("#### "):
            out.append("<h3>" + inline(s[5:]) + "</h3>")
        elif s.startswith("### "):
            out.append("<h3>" + inline(s[4:]) + "</h3>")
        elif s.startswith("## "):
            head = inline(s[3:])
            is_tk = bool(re.match(r"key takeaways", re.sub(r"<[^>]+>", "", head), re.I))
            out.append('<h2%s>%s</h2>' % (' class="tk"' if is_tk else "", head))
            takeaway_flag = is_tk
        elif s.startswith("> "):
            out.append("<blockquote>" + inline(s[2:]) + "</blockquote>")
        elif s == "---":
            out.append("<hr>")
        elif s.startswith("<img"):
            out.append(s)
        elif s:
            out.append("<p>" + inline(s) + "</p>")
    close_list()
    return "\n".join(out)


def reading_minutes(text):
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", text)))
    return max(1, round(words / 215))


def display_date(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        return d.strftime("%d %b %Y").lstrip("0")
    except Exception:
        return iso or ""


def rfc822(iso):
    try:
        d = datetime.datetime.fromisoformat(iso)
    except Exception:
        d = datetime.datetime.now()
    return d.strftime("%a, %d %b %Y 08:00:00 +0000")


# ------------------------------------------------------------------ parsing ---
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


def load_posts(posts_dir):
    """All posts, de-duplicated by slug: if a topic was published twice, the
    newest version wins (so nothing is listed or built twice)."""
    by_slug = {}
    if not os.path.isdir(posts_dir):
        return []
    for fname in sorted(os.listdir(posts_dir)):
        if not fname.endswith(".md"):
            continue
        parsed = parse_post(os.path.join(posts_dir, fname))
        if not parsed:
            continue
        meta, body = parsed
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", fname)[:-3]
        meta["slug"] = slug
        meta["body"] = body
        meta["_file"] = fname
        meta["_filedate"] = fname[:10]
        prev = by_slug.get(slug)
        if prev is None or max(meta.get("date", meta["_filedate"]), meta["_filedate"]) > \
                max(prev.get("date", prev["_filedate"]), prev["_filedate"]):
            if prev is not None:
                print("  dedupe: %s -> kept %s, skipped %s"
                      % (slug, meta["_file"], prev["_file"]))
            by_slug[slug] = meta
    posts = sorted(by_slug.values(),
                   key=lambda p: (p.get("date", p["_filedate"]), p["_filedate"]),
                   reverse=True)
    return posts


# --------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser(description="Build the static blog website.")
    ap.add_argument("--posts", default="_posts")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    ap.add_argument("--newsletter-action", default=None)
    ap.add_argument("--contact-action", default=None)
    ap.add_argument("--contact-email", default="hello@example.com")
    ap.add_argument("--w3f-key", default="7d7560e5-c7f8-41fb-865d-9bbdd3dfb159")
    ap.add_argument("--sheet-url", default="https://script.google.com/macros/s/AKfycbyEU1RcmAaQOIGZF01Jk_bBJvm8XmlvjSgS16iR-nfJ9WEqcPL8pF7ne29Asm6lYCg0fA/exec")
    args = ap.parse_args()

    site = args.site_url.rstrip("/")
    out = args.out
    posts = load_posts(args.posts)
    print("posts loaded: %d (unique slugs)" % len(posts))

    for d in ("", "assets/css", "assets/js", "posts"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    open(os.path.join(out, "assets/css/style.css"), "w", encoding="utf-8").write(CSS)
    open(os.path.join(out, "assets/js/chat.js"), "w", encoding="utf-8").write(CHAT_JS)

    # assets - work whether run from bot/ or the repo root
    for base in (HERE, os.getcwd()):
        og = os.path.join(base, "assets", "og-image.jpg")
        if os.path.exists(og):
            shutil.copy(og, os.path.join(out, "assets/og-image.jpg"))
            break
    for base in (HERE, os.getcwd()):
        sl = os.path.join(base, "output", "slides")
        if os.path.isdir(sl):
            dst = os.path.join(out, "assets/slides")
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(sl):
                shutil.copy(os.path.join(sl, f), os.path.join(dst, f))
            break

    articles_json = "[%s]" % ", ".join(
        '{{"slug":"{0}","title":"{1}","cat":"{2}","excerpt":"{3}"}}'.format(
            p["slug"], p.get("title", "").replace('"', "'"),
            p.get("categories", p.get("category", "")).replace('"', "'"),
            p.get("excerpt", "").replace('"', "'"))
        for p in posts)

    def shell(title, desc, body, ogtype="website", canon="", jsonld=""):
        return (SHELL.replace("@TITLE@", html_mod.escape(title))
                .replace("@DESC@", html_mod.escape(desc or TAGLINE, quote=True))
                .replace("@OGTYPE@", ogtype)
                .replace("@CANON@", canon or (site + "/index.html"))
                .replace("@FEED@", (site + "/feed.xml") if site else "feed.xml")
                .replace("@BRAND@", BRAND)
                .replace("@YEAR@", str(datetime.date.today().year))
                .replace("@JSONLD@", jsonld)
                .replace("@BODY@", body)
                .replace("@ARTICLES@", articles_json))

    def card(p, feature=False, prefix="posts/", related=False):
        tps = topics_for(p)
        icon = TOPIC_ICON.get(tps[0], "\U0001F3E1")
        accent = TOPIC_COLOUR.get(tps[0], DEFAULT_ACCENT)
        chips = "".join('<span class="chip">%s</span>' % html_mod.escape(t) for t in tps)
        rm = reading_minutes(p["body"])
        return (CARD.replace("@FEATURE@", " feature" if feature and not related else "")
                .replace("@HREF@", prefix + p["slug"] + ".html")
                .replace("@ACCENT@", accent)
                .replace("@CATS@", "|".join(tps))
                .replace("@ICON@", icon)
                .replace("@CHIPS@", chips)
                .replace("@TITLE@", html_mod.escape(p.get("title", "")))
                .replace("@EXCERPT@", html_mod.escape(p.get("excerpt", "")))
                .replace("@DATE@", display_date(p.get("date", p["_filedate"])))
                .replace("@READ@", str(rm)))

    # ---------------------------------------------------------------- index ---
    cards = []
    for i, p in enumerate(posts):
        cards.append(card(p, feature=(i == 0)))
    counts = {}
    for p in posts:
        for t in topics_for(p):
            counts[t] = counts.get(t, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], list(TOPIC_COLOUR).index(kv[0])
                                                     if kv[0] in TOPIC_COLOUR else 99))
    filters = "".join('<button data-cat="%s">%s <span style="opacity:.55">%d</span></button>'
                      % (t, t, n) for t, n in ordered)
    home = (HOME.replace("@COUNT@", str(len(posts)))
            .replace("@CADENCE@", "Weekly")
            .replace("@FILTERS@", filters)
            .replace("@CARDS@", "".join(cards) or "<p>No articles yet.</p>")
            .replace("@NEWSLETTER_ACTION@", args.newsletter_action or
                     "https://formsubmit.co/" + args.contact_email)
            .replace("@FB_EMAIL@", args.contact_email)
            .replace("@W3F_KEY@", args.w3f_key)
            .replace("@SHEET_URL@", args.sheet_url))
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(
        shell(BRAND + " - UK Property Investment Blog",
              "Practical UK property investing: HMOs, BRR, buy-to-let, auctions and "
              "deal sourcing for Scunthorpe & North Lincolnshire.", home))

    # ------------------------------------------------------------- articles ---
    for p in posts:
        tps = topics_for(p)
        icon = TOPIC_ICON.get(tps[0], "\U0001F3E1")
        accent = TOPIC_COLOUR.get(tps[0], DEFAULT_ACCENT)
        chips = "".join('<span class="chip">%s</span>' % html_mod.escape(t) for t in tps)
        body_html = md_to_html(p["body"])
        rm = reading_minutes(p["body"])
        # related: same topic first, then newest others - never the same post
        same = [q for q in posts if q["slug"] != p["slug"] and
                set(topics_for(q)) & set(tps)][:3]
        if len(same) < 3:
            for q in posts:
                if q["slug"] != p["slug"] and q not in same:
                    same.append(q)
                if len(same) == 3:
                    break
        related = "".join(card(q, prefix="", related=True) for q in same[:3])
        page = (POST_PAGE.replace("@TITLE@", html_mod.escape(p.get("title", "")))
                .replace("@DATE@", display_date(p.get("date", p["_filedate"])))
                .replace("@READ@", str(rm))
                .replace("@TOPICS@", "%s %s" % (icon, " &middot; ".join(
                    html_mod.escape(t) for t in tps)))
                .replace("@CONTENT@", body_html)
                .replace("@RELATED@", related))
        jsonld = (
            '<script type="application/ld+json">%s</script>'
            % ('{"@context":"https://schema.org","@type":"BlogPosting","headline":"%s",'
               '"datePublished":"%s","author":{"@type":"Organization","name":"%s"},'
               '"publisher":{"@type":"Organization","name":"%s"},"description":"%s"}'
               % (p.get("title", "").replace('"', "'"),
                  p.get("date", p["_filedate"]),
                  BRAND, BRAND,
                  p.get("excerpt", "").replace('"', "'")))
        )
        open(os.path.join(out, "posts/%s.html" % p["slug"]), "w", encoding="utf-8").write(
            shell(p.get("title", "") + " - " + BRAND, p.get("excerpt", ""), page,
                  ogtype="article",
                  canon=(site + "/posts/%s.html" % p["slug"]) if site else "",
                  jsonld=jsonld))

    # --------------------------------------------------------- static pages ---
    open(os.path.join(out, "about.html"), "w", encoding="utf-8").write(
        shell("About - " + BRAND, TAGLINE, ABOUT))
    open(os.path.join(out, "contact.html"), "w", encoding="utf-8").write(shell(
        "Contact - " + BRAND, "Get in touch",
        CONTACT.replace("@CONTACT_ACTION@", args.contact_action or
                        "https://formsubmit.co/" + args.contact_email)
        .replace("@EMAIL@", args.contact_email)
        .replace("@W3F_KEY@", args.w3f_key)
        .replace("@SHEET_URL@", args.sheet_url)))
    open(os.path.join(out, "privacy.html"), "w", encoding="utf-8").write(shell(
        "Privacy Policy - " + BRAND, "How we handle your data",
        PRIVACY.replace("@EMAIL@", args.contact_email)))
    open(os.path.join(out, "404.html"), "w", encoding="utf-8").write(shell(
        "Page not found - " + BRAND, "404",
        '<section class="wrap"><h2 class="sec">404 - page not found</h2>'
        '<p class="sub">That page has moved or never existed.</p>'
        '<a class="btn" href="index.html">Back to all articles</a></section>'))

    # ------------------------------------------------------------------ RSS ---
    items = "".join(
        "<item><title>%s</title><link>%s/posts/%s.html</link>"
        "<guid>%s/posts/%s.html</guid><description>%s</description>"
        "<pubDate>%s</pubDate></item>" % (
            html_mod.escape(p.get("title", "")), site, p["slug"], site, p["slug"],
            html_mod.escape(p.get("excerpt", "")), rfc822(p.get("date", p["_filedate"])))
        for p in posts[:15])
    open(os.path.join(out, "feed.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" '
        'xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        '<title>%s</title><link>%s</link><atom:link href="%s/feed.xml" rel="self" '
        'type="application/rss+xml"/><description>%s</description>'
        '<language>en-gb</language><lastBuildDate>%s</lastBuildDate>%s'
        '</channel></rss>' % (BRAND, site or "/", site, TAGLINE,
                              rfc822(datetime.date.today().isoformat()), items))

    print("Site built into %s/ : %d article page(s), index with %d filter(s), "
          "about/contact/privacy/404 + RSS." % (out, len(posts), len(ordered)))
    print("Preview locally:  python3 -m http.server 8000 -d %s" % out)


if __name__ == "__main__":
    main()
