#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Midweek post - keeps LinkedIn from going quiet between Monday articles.

Picks ONE already-published article (the oldest one that has not been re-shared
yet), writes a fresh hook for it (OpenAI when a key is available, otherwise a
templated hook) and posts a link update to LinkedIn, plus Facebook/Instagram
when those credentials are configured.

Rotation state: bot/output/midweek-shared.json (slug -> date last shared).
The daily "scunthorpe-auction-watch" post and anything published in the last
--min-age-days (default 14) is never chosen.

Usage:
  python3 midweek_post.py                       # preview (no posting)
  python3 midweek_post.py --post                # publish
  python3 midweek_post.py --post --slug hmo-investing   # force a specific one

Credentials (env): LINKEDIN_ACCESS_TOKEN, FACEBOOK_PAGE_ID,
FACEBOOK_PAGE_ACCESS_TOKEN, OPENAI_API_KEY (optional).
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "_posts")
OUT_DIR = os.path.join(HERE, "output")
STATE_FILE = os.path.join(OUT_DIR, "midweek-shared.json")
LATEST_FILE = os.path.join(OUT_DIR, "midweek-latest.json")
CAPTION_FILE = os.path.join(OUT_DIR, "midweek-caption.txt")

DEFAULT_SITE = ("https://ramanpreett77.github.io/"
                "scunthorpe-investment-live-map-v4/blog")
SKIP_SLUGS = {"scunthorpe-auction-watch"}

FALLBACK_HOOKS = [
    "A question that keeps coming up with investors this week:",
    "One from the archive - still the most useful thing we have written on this:",
    "Worth re-reading before your next viewing:",
    "The bit most buyers skip - and regret:",
]

CATEGORY_TAGS = [
    ("dubai", "#DubaiProperty"),
    ("hmo", "#HMO"),
    ("brr", "#BRRR"),
    ("auction", "#PropertyAuction"),
    ("buy-to-let", "#BuyToLet"),
    ("sourcing", "#PropertySourcing"),
]


# --------------------------------------------------------------- article pick ---
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
    name = os.path.basename(path)
    meta["slug"] = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)[:-3]
    meta["_file"] = path
    meta["_body"] = m.group(2)
    return meta


def load_posts():
    out = []
    if os.path.isdir(POSTS_DIR):
        for f in sorted(os.listdir(POSTS_DIR)):
            if f.endswith(".md"):
                p = parse_post(os.path.join(POSTS_DIR, f))
                if p and p.get("slug"):
                    out.append(p)
    return out


def choose_post(posts, state, min_age_days, force_slug=None):
    today = date.today()
    if force_slug:
        for p in posts:
            if p["slug"] == force_slug:
                return p
        sys.exit("No post with slug '%s' in _posts." % force_slug)

    def age_days(p):
        try:
            return (today - date.fromisoformat(p.get("date", "2000-01-01"))).days
        except ValueError:
            return 9999

    candidates = [p for p in posts
                  if p["slug"] not in SKIP_SLUGS and age_days(p) >= min_age_days]
    if not candidates:
        return None
    never = [p for p in candidates if p["slug"] not in state]
    if never:
        return sorted(never, key=lambda p: p.get("date", ""))[0]
    return sorted(candidates, key=lambda p: (state.get(p["slug"], ""), p.get("date", "")))[0]


# ------------------------------------------------------------------- writing ---
def takeaway_lines(body, n=3):
    """Use the article's own H2/H3 headings as the bullets."""
    heads = re.findall(r"^#{2,3}\s+(.+?)\s*$", body, re.M)
    heads = [re.sub(r"[*_`]", "", h) for h in heads]
    heads = [h for h in heads if not re.match(r"key takeaways?$", h, re.I)]
    return heads[:n]


def hashtags_for(post):
    blob = (post.get("categories", "") + " " + post["slug"]).lower()
    tags = ["#PropertyInvestment", "#UKProperty"]
    for needle, tag in CATEGORY_TAGS:
        if needle in blob and tag not in tags:
            tags.append(tag)
    return tags[:5]


def ai_hook(post):
    """One-sentence hook via OpenAI, or None (templated fallback is used)."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        import requests
        prompt = (
            "Write ONE sentence (max 22 words) for a LinkedIn post that re-shares "
            "the article below. Sound like a UK property investor talking to "
            "other investors - specific, plain English, no hype, no hashtags, "
            "at most one emoji. Do not say 'new on the blog' or 'check out'. "
            "Reply with the sentence only.\n\n"
            "Title: %s\nSummary: %s" % (post.get("title", ""), post.get("excerpt", ""))
        )
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.8,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip().strip('"')
        return text or None
    except Exception as e:  # silent fallback, same philosophy as blog_generator
        print("  ! AI hook unavailable (%s) - using templated hook." % str(e)[:100])
        return None


def build_caption(post, site_url, index=0):
    link = site_url.rstrip("/") + "/posts/%s.html" % post["slug"]
    hook = ai_hook(post) or FALLBACK_HOOKS[index % len(FALLBACK_HOOKS)]
    bullets = takeaway_lines(post["_body"])
    parts = [hook, "", post.get("title", "").strip()]
    if bullets:
        parts += ["", "\n".join("> " + b for b in bullets)]
    parts += ["", "Read it here \U0001F449 " + link, "",
              " ".join(hashtags_for(post))]
    return "\n".join(parts)[:3000], link


# ------------------------------------------------------------------ publishing ---
def publish(caption, link, image_url):
    """Post to every platform we have credentials for. Returns (results, failures)."""
    results, failures = [], 0

    li = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if li:
        try:
            import linkedin_poster
            urn = linkedin_poster.post_to_linkedin(caption, li)
            results.append(("LinkedIn", "posted (%s)" % urn))
        except SystemExit as ex:
            results.append(("LinkedIn", "FAILED: %s" % ex))
            failures += 1
        except Exception as ex:
            results.append(("LinkedIn", "FAILED: %s" % str(ex)[:200]))
            failures += 1
    else:
        results.append(("LinkedIn", "SKIPPED - set LINKEDIN_ACCESS_TOKEN"))

    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    fb_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    if page_id and fb_token:
        try:
            import social_media_poster as smp
            fid = smp.post_facebook(page_id, fb_token, caption, link)
            results.append(("Facebook", "posted (%s)" % fid))
            if image_url:
                try:
                    iid = smp.post_instagram(page_id, fb_token, caption, image_url)
                    results.append(("Instagram", "posted (%s)" % iid))
                except SystemExit as ex:
                    results.append(("Instagram", "FAILED: %s" % ex))
                    failures += 1
            else:
                results.append(("Instagram", "SKIPPED - no image URL"))
        except SystemExit as ex:
            results.append(("Facebook", "FAILED: %s" % ex))
            failures += 1
        except Exception as ex:
            results.append(("Facebook", "FAILED: %s" % str(ex)[:200]))
            failures += 1
    else:
        results.append(("Facebook", "SKIPPED - set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN"))
        results.append(("Instagram", "SKIPPED - needs the Facebook Page token"))

    return results, failures


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    ap = argparse.ArgumentParser(description="Re-share a published article midweek.")
    ap.add_argument("--post", action="store_true", help="Actually publish (default: preview)")
    ap.add_argument("--slug", help="Force a specific article slug")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", DEFAULT_SITE))
    ap.add_argument("--min-age-days", type=int, default=5,
                    help="Never re-share anything published within this many days")
    args = ap.parse_args()

    posts = load_posts()
    if not posts:
        sys.exit("No posts found in _posts - nothing to share.")

    state = load_state()
    post = choose_post(posts, state, args.min_age_days, args.slug)
    if not post:
        print("No eligible article to re-share (all too recent or already shared).")
        return

    caption, link = build_caption(post, args.site_url, len(state) % len(FALLBACK_HOOKS))

    meta = {
        "title": post.get("title", ""),
        "slug": post["slug"],
        "date": post.get("date", ""),
        "category": post.get("categories", ""),
        "excerpt": post.get("excerpt", ""),
        "hashtags": hashtags_for(post),
        "url_path": "/posts/%s.html" % post["slug"],
        "site_url": args.site_url,
        "source_url": link,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    with open(CAPTION_FILE, "w", encoding="utf-8") as f:
        f.write(caption + "\n")

    print("Midweek pick: %s (%s)" % (post.get("title", post["slug"]), post["slug"]))
    print("-" * 62)
    print(caption)
    print("-" * 62)

    if not args.post:
        print("(preview only - add --post to publish)")
        return

    image = os.environ.get("MIDWEEK_IMAGE") or (
        args.site_url.rstrip("/") + "/assets/og-image.jpg")
    results, failures = publish(caption, link, image)
    for platform, detail in results:
        print("%-10s %s" % (platform + ":", detail))

    posted = any(d.startswith("posted") for _, d in results)
    if posted:
        state[post["slug"]] = date.today().isoformat()
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print("State updated: %s" % STATE_FILE)
    else:
        print("Nothing was posted - rotation state left unchanged (will retry).")

    if failures:
        sys.exit("%d platform(s) failed - see above." % failures)


if __name__ == "__main__":
    main()
