#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-platform social media publisher
=====================================
Publishes the latest generated article to LinkedIn, your Facebook Page and/or
Instagram - using ONLY the official APIs (no risky third-party automation).

Usage:
  python3 social_media_poster.py --dry-run                        # preview everything
  python3 social_media_poster.py --platforms linkedin,facebook --post
  python3 social_media_poster.py --platforms all --post

Credentials (environment variables):
  LinkedIn:   LINKEDIN_ACCESS_TOKEN
  Facebook:   FACEBOOK_PAGE_ID + FACEBOOK_PAGE_ACCESS_TOKEN
  Instagram:  reuses the Facebook token; the account must be Business/Creator
              and linked to the Page. INSTAGRAM_USER_ID optional (auto-detected).
              Requires an image: pass --image URL or set the OG_IMAGE env var.

Note on X (Twitter): since Feb 2026 its API is pay-per-use (~$0.20 per post
that contains a link). It is deliberately not included here - see README.md.
"""
import argparse
import json
import os
import sys

GRAPH = "https://graph.facebook.com/v23.0"


# ---------------------------------------------------------------- content ---
def load_latest(path="output/latest.json"):
    if not os.path.exists(path):
        sys.exit("No article metadata found at %s - run blog_generator.py first." % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_caption(meta, site_url):
    """Shorter caption for Facebook/Instagram (LinkedIn uses the fuller post)."""
    link = site_url.rstrip("/") + meta["url_path"]
    tags = " ".join(meta["hashtags"][:5])
    return (
        meta["hook"] + " \U0001F447\n\n"
        + meta["excerpt"] + "\n\n"
        + "Full article \U0001F449 " + link + "\n\n"
        + tags
    )


# --------------------------------------------------------------- platforms ---
def post_linkedin(text, token):
    import linkedin_poster
    return linkedin_poster.post_to_linkedin(text, token)


def post_facebook(page_id, token, message, link):
    import requests
    r = requests.post(
        GRAPH + "/" + page_id + "/feed",
        data={"message": message, "link": link, "access_token": token},
        timeout=60,
    )
    if r.status_code != 200:
        sys.exit("Facebook rejected the post (%s): %s" % (r.status_code, r.text[:300]))
    return r.json().get("id")


def get_instagram_user_id(page_id, token):
    import requests
    r = requests.get(
        GRAPH + "/" + page_id,
        params={"fields": "instagram_business_account", "access_token": token},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    return (r.json().get("instagram_business_account") or {}).get("id")


def post_instagram(page_id, token, caption, image_url, ig_user_id=None):
    """Two-step official flow: create a media container, then publish it."""
    import requests
    ig = ig_user_id or os.environ.get("INSTAGRAM_USER_ID") or get_instagram_user_id(page_id, token)
    if not ig:
        sys.exit(
            "No Instagram Business/Creator account is linked to this Facebook Page.\n"
            "Switch Instagram to a Professional account, link it to the Page, then retry."
        )
    r = requests.post(
        GRAPH + "/" + ig + "/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    if r.status_code != 200:
        sys.exit("Instagram container failed (%s): %s" % (r.status_code, r.text[:300]))
    container_id = r.json()["id"]
    r = requests.post(
        GRAPH + "/" + ig + "/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=60,
    )
    if r.status_code != 200:
        sys.exit("Instagram publish failed (%s): %s" % (r.status_code, r.text[:300]))
    return r.json().get("id")


# ------------------------------------------------------- carousel posting ---
def post_linkedin_article(token, caption, link, title, description):
    """LinkedIn link-card post - the reliable rich format on the default app tier.
    (PDF/image carousels are not permitted by the default Share-on-LinkedIn tier.)"""
    import requests
    import linkedin_poster
    person = linkedin_poster.get_person_id(token)
    body = {"author": "urn:li:person:" + person, "commentary": caption,
            "visibility": "PUBLIC", "lifecycleState": "PUBLISHED",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                             "thirdPartyDistributionChannels": []},
            "content": {"article": {"source": link, "title": title[:200],
                                    "description": description[:300]}}}
    h = {"Authorization": "Bearer " + token, "LinkedIn-Version": LINKEDIN_VERSION,
         "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}
    r = requests.post("https://api.linkedin.com/rest/posts", json=body, headers=h, timeout=30)
    if r.status_code not in (200, 201):
        sys.exit("LinkedIn article post failed (%s): %s" % (r.status_code, r.text[:300]))
    return r.headers.get("x-restli-id") or "(published)"


def post_facebook_carousel(page_id, token, caption, link, image_urls):
    """Attach several (unpublished) photos to one feed post = carousel-style post."""
    import requests
    ids = []
    for u in image_urls:
        r = requests.post(GRAPH + "/" + page_id + "/photos",
                          data={"url": u, "published": "false", "access_token": token},
                          timeout=60)
        if r.status_code != 200:
            sys.exit("Facebook photo upload failed (%s): %s" % (r.status_code, r.text[:200]))
        ids.append(r.json()["id"])
    data = {"message": caption, "access_token": token,
            "attached_media": json.dumps([{"media_fkey": i} for i in ids])}
    if link:
        data["link"] = link
    r = requests.post(GRAPH + "/" + page_id + "/feed", data=data, timeout=60)
    if r.status_code != 200:
        sys.exit("Facebook carousel post failed (%s): %s" % (r.status_code, r.text[:300]))
    return r.json().get("id")


def post_instagram_carousel(page_id, token, caption, image_urls, ig_user_id=None):
    """Official IG flow: one container per image, then a CAROUSEL container, then publish."""
    import requests
    ig = ig_user_id or os.environ.get("INSTAGRAM_USER_ID") or get_instagram_user_id(page_id, token)
    if not ig:
        sys.exit("No Instagram Business account linked to this Facebook Page.")
    children = []
    for u in image_urls:
        r = requests.post(GRAPH + "/" + ig + "/media",
                          data={"image_url": u, "is_carousel_item": "true",
                                "access_token": token}, timeout=60)
        if r.status_code != 200:
            sys.exit("Instagram slide container failed (%s): %s" % (r.status_code, r.text[:200]))
        children.append(str(r.json()["id"]))
    r = requests.post(GRAPH + "/" + ig + "/media",
                      data={"media_type": "CAROUSEL", "children": ",".join(children),
                            "caption": caption, "access_token": token}, timeout=60)
    if r.status_code != 200:
        sys.exit("Instagram carousel container failed (%s): %s" % (r.status_code, r.text[:200]))
    r = requests.post(GRAPH + "/" + ig + "/media_publish",
                      data={"creation_id": r.json()["id"], "access_token": token}, timeout=60)
    if r.status_code != 200:
        sys.exit("Instagram carousel publish failed (%s): %s" % (r.status_code, r.text[:200]))
    return r.json().get("id")


# -------------------------------------------------------------------- main ---


def main():
    ap = argparse.ArgumentParser(description="Publish the latest article to social media.")
    ap.add_argument("--platforms", default="all",
                    help="Comma list: linkedin,facebook,instagram (default: all)")
    ap.add_argument("--meta", default="output/latest.json")
    ap.add_argument("--site-url", default=None)
    ap.add_argument("--image", default=None,
                    help="Image URL for Instagram (defaults to the OG_IMAGE env var)")
    ap.add_argument("--carousel", action="store_true",
                    help="Post as swipeable carousels (build slides first with carousel_builder.py)")
    ap.add_argument("--slides", default="output/slides", help="Slides directory")
    ap.add_argument("--post", action="store_true", help="Actually publish (default: dry run)")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (this is the default)")
    args = ap.parse_args()

    meta = load_latest(args.meta)
    site_url = args.site_url or meta.get("site_url") or os.environ.get("SITE_URL", "")
    link = site_url.rstrip("/") + meta["url_path"]

    slides = None
    if args.carousel:
        sp = os.path.join(args.slides, "slides.json")
        if not os.path.exists(sp):
            sys.exit("No slides found at %s - run carousel_builder.py --url-prefix ... first." % sp)
        with open(sp, encoding="utf-8") as f:
            slides = json.load(f)
        if args.post and not slides.get("urls"):
            sys.exit("Carousels for Facebook/Instagram need public slide URLs: "
                     "rebuild slides with --url-prefix https://yoursite/assets/slides/")

    wanted = set(args.platforms.replace(" ", "").split(","))
    if "all" in wanted:
        wanted = {"linkedin", "facebook", "instagram"}

    import linkedin_poster
    results = []
    cap = None
    if slides:
        cap = slides["caption"] + "\n\n" + " ".join(meta["hashtags"])

    li_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")
    fb_token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")

    # --- LinkedIn ---------------------------------------------------------
    if "linkedin" in wanted:
        if slides:
            if args.post:
                results.append(("LinkedIn", "SKIPPED - set LINKEDIN_ACCESS_TOKEN" if not li_token
                                else "Link-card published (%s)" %
                                post_linkedin_article(li_token, cap, link, meta["title"], meta["excerpt"])))
            else:
                results.append(("LinkedIn", "WOULD POST LINK-CARD (%s)\n%s" % (link, cap)))
        else:
            li_text = linkedin_poster.build_post(meta, site_url)
            if args.post:
                results.append(("LinkedIn", "SKIPPED - set LINKEDIN_ACCESS_TOKEN" if not li_token
                                else "Published (id %s)" % post_linkedin(li_text, li_token)))
            else:
                results.append(("LinkedIn", "WOULD POST:\n" + li_text))

    # --- Facebook Page ------------------------------------------------------
    if "facebook" in wanted:
        caption = cap if slides else build_caption(meta, site_url)
        if args.post:
            if not (page_id and fb_token):
                results.append(("Facebook", "SKIPPED - set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN"))
            elif slides:
                results.append(("Facebook", "Carousel published (post id %s)" %
                                post_facebook_carousel(page_id, fb_token, caption, link, slides["urls"])))
            else:
                results.append(("Facebook", "Published (post id %s)" % post_facebook(page_id, fb_token, caption, link)))
        else:
            kind = "CAROUSEL (%d slides)" % len(slides["urls"]) if slides else "POST"
            results.append(("Facebook", "WOULD POST %s:\n%s" % (kind, caption)))

    # --- Instagram ----------------------------------------------------------
    if "instagram" in wanted:
        caption = cap if slides else build_caption(meta, site_url)
        image = args.image or os.environ.get("OG_IMAGE")
        if args.post:
            if not (page_id and fb_token):
                results.append(("Instagram", "SKIPPED - needs the Facebook Page token (see README)"))
            elif slides:
                results.append(("Instagram", "Carousel published (media id %s)" %
                                post_instagram_carousel(page_id, fb_token, caption, slides["urls"])))
            elif not image:
                results.append(("Instagram", "SKIPPED - pass --image URL or set OG_IMAGE"))
            else:
                results.append(("Instagram", "Published (media id %s)" % post_instagram(page_id, fb_token, caption, image)))
        else:
            if slides:
                results.append(("Instagram", "WOULD POST CAROUSEL (%d slides):\n%s" % (len(slides["urls"]), caption)))
            else:
                results.append(("Instagram", "WOULD POST with image %s:\n%s" % (image or "(no image set)", caption)))

    for name, detail in results:
        print("=" * 62)
        print(name.upper())
        print("-" * 62)
        print(detail)
        print()
    if not args.post:
        print("(dry run - add --post to publish)")


if __name__ == "__main__":
    main()
