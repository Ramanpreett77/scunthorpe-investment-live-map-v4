#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Native LinkedIn posting - the format that actually reaches people.

Why: LinkedIn suppresses posts that carry an outbound link. So instead of a
link card we publish the substance AS NATIVE TEXT (hook, value, genuine
question, hashtags) and put the link in the FIRST COMMENT.

  python3 linkedin_native.py                       # preview (dry run)
  python3 linkedin_native.py --post                # publish + first comment
  python3 linkedin_native.py --post --no-comment    # skip the comment step

Reads article metadata from output/latest.json (written by persona_writer.py).
Credentials: LINKEDIN_ACCESS_TOKEN (w_member_social). Uses only official APIs.
"""
import argparse
import json
import os
import sys
import urllib.parse

LINKEDIN_VERSION = "202601"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"
COMMENT_URLS = [
    "https://api.linkedin.com/rest/socialActions/{urn}/comments",
    "https://api.linkedin.com/v2/socialActions/{urn}/comments",
]
MAX_CHARS = 2800  # LinkedIn commentary limit is 3000; leave headroom

# Used when an article has no persona attached (e.g. drafts written before the
# persona system existed): every post still ends with a genuine question.
GENERIC_QUESTION = "What would you want to know before making a move like this?"


def load_meta(path="output/latest.json"):
    if not os.path.exists(path):
        sys.exit("No article metadata at %s - run persona_writer.py first." % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def persona_of(meta):
    return meta.get("persona") or {}


def build_native_text(meta, persona=None):
    """Native feed text: NO link. Ends with a genuine question, then hashtags."""
    persona = persona or persona_of(meta)
    hook = (meta.get("hook") or "").strip()
    title = (meta.get("title") or "").strip()
    excerpt = (meta.get("excerpt") or "").strip()
    takeaways = [t for t in (meta.get("takeaways") or [])][:3]
    question = (persona.get("question") or "").strip() or GENERIC_QUESTION
    tags = " ".join((meta.get("hashtags") or [])[:5])

    parts = [hook, "", title]
    if excerpt:
        parts += ["", excerpt]
    if takeaways:
        parts += ["", "\n".join("→ " + t.rstrip(".") for t in takeaways)]
    if question:
        parts += ["", question]
    if tags:
        parts += ["", tags]
    text = "\n".join(parts).strip()
    return text[:MAX_CHARS]


def build_first_comment(meta, persona=None):
    persona = persona or persona_of(meta)
    site = (meta.get("site_url") or "").rstrip("/")
    link = site + (meta.get("url_path") or "")
    cta = (persona.get("cta") or "").strip()
    lines = ["Full article here 👉 " + link]
    if cta:
        lines += ["", cta]
    return "\n".join(lines)


# ------------------------------------------------------------------- posting ---
def get_person_id(token):
    override = os.environ.get("LINKEDIN_PERSON_ID")
    if override:
        return override
    import requests
    r = requests.get(USERINFO_URL, headers={"Authorization": "Bearer " + token}, timeout=30)
    if r.status_code != 200:
        sys.exit("Could not read your LinkedIn profile (%s): %s\n"
                 "Check the token still has the 'openid profile' scope."
                 % (r.status_code, r.text[:200]))
    return r.json()["sub"]


def post_text(text, token):
    """Publish a native text post. Returns (urn, person_id)."""
    import requests
    person = get_person_id(token)
    body = {
        "author": "urn:li:person:" + person,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    headers = {"Authorization": "Bearer " + token,
               "LinkedIn-Version": LINKEDIN_VERSION,
               "X-Restli-Protocol-Version": "2.0.0",
               "Content-Type": "application/json"}
    r = requests.post(POSTS_URL, json=body, headers=headers, timeout=45)
    if r.status_code not in (200, 201):
        sys.exit("LinkedIn post failed (%s): %s" % (r.status_code, r.text[:300]))
    urn = r.headers.get("x-restli-id") or r.headers.get("X-Restli-Id")
    if not urn:
        try:
            urn = r.json().get("id") or r.json().get("urn")
        except Exception:
            urn = None
    return urn, person


def add_comment(urn, text, token, person):
    """Attach the link comment. Tries the REST then the v2 endpoint.

    Returns (ok, detail). Never raises: a failed comment must not fail a run
    that has already published the post.
    """
    import requests
    payload = {
        "actor": "urn:li:person:" + person,
        "object": urn,
        "message": {"text": text},
    }
    headers = {"Authorization": "Bearer " + token,
               "LinkedIn-Version": LINKEDIN_VERSION,
               "X-Restli-Protocol-Version": "2.0.0",
               "Content-Type": "application/json"}
    quoted = urllib.parse.quote(urn, safe="")
    last = ""
    for tpl in COMMENT_URLS:
        url = tpl.format(urn=quoted)
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=45)
        except Exception as e:
            last = "%s: %s" % (url.split("linkedin.com")[1], str(e)[:120])
            continue
        if r.status_code in (200, 201):
            return True, "comment posted via %s" % url.split("linkedin.com")[1]
        last = "%s -> HTTP %s %s" % (url.split("linkedin.com")[1], r.status_code, r.text[:160])
    return False, last


def publish(meta, token, comment=True):
    """Post natively then comment the link. Returns dict summary."""
    text = build_native_text(meta)
    urn, person = post_text(text, token)
    out = {"urn": urn, "chars": len(text), "comment": None}
    if comment and urn:
        out["comment"] = add_comment(urn, build_first_comment(meta), token, person)
    elif comment and not urn:
        out["comment"] = (False, "no post URN returned - cannot comment")
    return out


def main():
    ap = argparse.ArgumentParser(description="Post the latest article natively on LinkedIn.")
    ap.add_argument("--post", action="store_true", help="Actually publish (default: preview)")
    ap.add_argument("--no-comment", action="store_true", help="Do not add the link comment")
    ap.add_argument("--meta", default="output/latest.json")
    ap.add_argument("--site-url", default=None)
    ap.add_argument("--persona", help="Override the persona id used for the question")
    args = ap.parse_args()

    meta = load_meta(args.meta)
    if args.site_url:
        meta["site_url"] = args.site_url
    if args.persona:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import personas
        p = personas.get(args.persona)
        if p:
            meta.setdefault("persona", {})
            meta["persona"].update({"id": p["id"], "name": p["name"],
                                    "question": p["question"], "cta": p["cta"]})

    text = build_native_text(meta)
    comment = build_first_comment(meta)

    print("=" * 62)
    print("LINKEDIN - NATIVE POST (%d chars, no link in body)" % len(text))
    print("-" * 62)
    print(text)
    print()
    print("FIRST COMMENT (carries the link)")
    print("-" * 62)
    print(comment)
    print("=" * 62)

    if not args.post:
        print("(preview only - add --post to publish)")
        return

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        print("LINKEDIN: SKIPPED - set LINKEDIN_ACCESS_TOKEN")
        return

    res = publish(meta, token, comment=not args.no_comment)
    print("Posted: %s" % res["urn"])
    ok, detail = (res["comment"] or (None, "not attempted"))
    if ok:
        print("First comment: OK (%s)" % detail)
    else:
        print("::warning::Post published but the link comment failed (%s). "
              "Add the link manually as a comment." % detail)


if __name__ == "__main__":
    main()
