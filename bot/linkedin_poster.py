#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn publishing module
==========================
Turns the latest generated article into a LinkedIn-ready post, and (optionally)
publishes it through the OFFICIAL LinkedIn API.

Usage:
  python3 linkedin_poster.py --dry-run          # preview the post text
  python3 linkedin_poster.py --post             # publish (needs access token)

Requirements for --post:
  * A LinkedIn Developer App with the "Share on LinkedIn" product.
  * An access token with the w_member_social (and openid) scope, provided via
    the LINKEDIN_ACCESS_TOKEN environment variable.
  Setup guide: see README.md, section "LinkedIn auto-posting setup".
"""
import argparse
import json
import os
import sys

LINKEDIN_VERSION = "202601"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"


def load_latest(path="output/latest.json"):
    if not os.path.exists(path):
        sys.exit("No article metadata found at %s - run blog_generator.py first." % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_post(meta, site_url):
    """Compose a LinkedIn post from article metadata (no API needed)."""
    bullets = "\n".join("> " + t for t in meta["takeaways"][:4])
    link = site_url.rstrip("/") + meta["url_path"]
    tags = " ".join(meta["hashtags"])
    post = (
        meta["hook"] + " \U0001F447\n\n"
        "New on the blog: " + meta["title"] + "\n\n"
        + bullets + "\n\n"
        "Read the full breakdown \U0001F449 " + link + "\n\n"
        + tags
    )
    # LinkedIn's commentary limit is 3000 characters.
    return post[:3000]


def get_person_id(token):
    override = os.environ.get("LINKEDIN_PERSON_ID")
    if override:
        return override
    import requests
    r = requests.get(USERINFO_URL, headers={"Authorization": "Bearer " + token}, timeout=30)
    if r.status_code != 200:
        sys.exit("Could not read your LinkedIn profile (%s): %s\n"
                 "Check the token has the 'openid profile' scope." % (r.status_code, r.text[:200]))
    return r.json()["sub"]


def post_to_linkedin(text, token):
    """Publish via the official LinkedIn REST API. Returns the post URN."""
    import requests
    person_id = get_person_id(token)
    body = {
        "author": "urn:li:person:" + person_id,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    headers = {
        "Authorization": "Bearer " + token,
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    r = requests.post(POSTS_URL, json=body, headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        sys.exit("LinkedIn rejected the post (%s): %s" % (r.status_code, r.text[:400]))
    return r.headers.get("x-restli-id") or "(published)"


def main():
    ap = argparse.ArgumentParser(description="Create / publish the LinkedIn post for the latest article.")
    ap.add_argument("--meta", default="output/latest.json", help="Path to article metadata JSON")
    ap.add_argument("--site-url", default=None, help="Override the GitHub Pages site URL")
    ap.add_argument("--dry-run", action="store_true", help="Print the post instead of publishing")
    ap.add_argument("--post", action="store_true", help="Actually publish to LinkedIn")
    ap.add_argument("--file", help="Post custom text from a file (e.g. output/launch_post.txt)")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            post = f.read().strip()
    else:
        meta = load_latest(args.meta)
        site_url = args.site_url or meta.get("site_url") or os.environ.get("SITE_URL", "")
        post = build_post(meta, site_url)

    if args.post:
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not token:
            sys.exit("Set LINKEDIN_ACCESS_TOKEN first (see README.md for setup).")
        urn = post_to_linkedin(post, token)
        print("Published to LinkedIn. Post id: " + str(urn))
    else:
        print(post)
        print("\n--- dry run (add --post to publish via the official LinkedIn API) ---")


if __name__ == "__main__":
    main()
