#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Engagement & reply bot (official APIs only)
===========================================
Fetches new comments on your recent posts (LinkedIn / Facebook / Instagram),
drafts warm, human-sounding replies, and posts them.

Reply quality:
  * With OPENAI_API_KEY set -> replies are written by an AI in YOUR brand voice
    (friendly UK property investor, never gives financial advice).
  * Without it -> a sensible rule-based reply bank.

Safety: every comment id is recorded in output/replied_comments.json so nothing
is ever answered twice. Default is dry-run: add --post to actually reply.

Env:
  LINKEDIN_ACCESS_TOKEN, FACEBOOK_PAGE_ID, FACEBOOK_PAGE_ACCESS_TOKEN
"""
import argparse
import json
import os
import sys

GRAPH = "https://graph.facebook.com/v23.0"
STATE_FILE = "output/replied_comments.json"

SAMPLE_COMMENTS = [
    ("linkedin", "urn:li:comment:700001", "Sarah Jenkins",
     "This is exactly the BRR breakdown I needed, thanks for sharing!"),
    ("linkedin", "urn:li:comment:700002", "Mark Osei",
     "Great article. What sort of yield would you expect on this in Birmingham?"),
    ("facebook", "101_202", "Priya Shah",
     "Saved! Are you covering HMO licensing next?"),
]


# ------------------------------------------------------------- fetching ---
def fetch_linkedin(token):
    import linkedin_poster
    import requests
    h = {"Authorization": "Bearer " + token}
    me = linkedin_poster.get_person_id(token)
    r = requests.get("https://api.linkedin.com/rest/posts",
                     params={"author": "urn:li:person:" + me, "count": 3},
                     headers=dict(h, **{"LinkedIn-Version": "202601",
                                        "X-Restli-Protocol-Version": "2.0.0"}), timeout=30)
    out = []
    if r.status_code != 200:
        return out
    for post in r.json().get("elements", []):
        pid = post["id"]
        c = requests.get("https://api.linkedin.com/rest/comments",
                         params={"postId": pid, "count": 20},
                         headers=dict(h, **{"LinkedIn-Version": "202601",
                                            "X-Restli-Protocol-Version": "2.0.0"}), timeout=30)
        if c.status_code == 200:
            for el in c.json().get("elements", []):
                out.append(("linkedin", el["id"],
                            el.get("author", {}).get("name", "there"),
                            el.get("message", "")))
    return out


def fetch_facebook(page_id, token):
    import requests
    r = requests.get(GRAPH + "/" + page_id + "/posts",
                     params={"access_token": token, "limit": 3}, timeout=30)
    out = []
    if r.status_code != 200:
        return out
    for post in r.json().get("data", []):
        c = requests.get(GRAPH + "/" + post["id"] + "/comments",
                         params={"access_token": token}, timeout=30)
        if c.status_code == 200:
            for el in c.json().get("data", []):
                out.append(("facebook", el["id"],
                            el.get("from", {}).get("name", "there"), el.get("message", "")))
    return out


def fetch_instagram(page_id, token):
    import requests
    r = requests.get(GRAPH + "/" + page_id,
                     params={"fields": "instagram_business_account",
                             "access_token": token}, timeout=30)
    ig = (r.json().get("instagram_business_account") or {}).get("id")
    out = []
    if not ig:
        return out
    m = requests.get(GRAPH + "/" + ig + "/media",
                     params={"access_token": token, "limit": 3}, timeout=30)
    if m.status_code != 200:
        return out
    for media in m.json().get("data", []):
        c = requests.get(GRAPH + "/" + media["id"] + "/comments",
                         params={"access_token": token}, timeout=30)
        if c.status_code == 200:
            for el in c.json().get("data", []):
                out.append(("instagram", el["id"],
                            el.get("username", "there"), el.get("text", "")))
    return out


# ------------------------------------------------------------- replying ---
def ai_reply(author, text):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        import requests
        prompt = (
            "You are a friendly, down-to-earth UK property investor who writes a blog "
            "about HMOs, BRR and buy-to-let in Scunthorpe & North Lincolnshire. Someone commented on "
            "your social post. Write a 1-2 sentence reply to this comment. Be warm and "
            "human, use their first name if natural, NEVER give financial advice, and "
            "encourage them to read the full article or ask more. No hashtags, no quotes.\n\n"
            "Comment from %s: %s" % (author, text)
        )
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                  "temperature": 0.8,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def rule_reply(text):
    t = text.lower()
    if any(w in t for w in ("thank", "great post", "love this", "helpful", "saved")):
        return ("Thanks so much! Really glad it helped - there's plenty more "
                "where this came from \U0001F642")
    if "?" in text or any(w in t for w in ("what", "how", "why", "yield", "cost", "when")):
        return ("Great question! The full article goes a bit deeper on this, and I'm "
                "covering the numbers properly in an upcoming post. Meanwhile, happy to "
                "point you the right way if you drop me a message.")
    return ("Appreciate you stopping by! If there's a topic you'd like covered next "
            "(HMO, BRR, refinancing, sourcing...), just say the word \U0001F44D")


def send_reply(platform, comment_id, reply, token, page_id):
    import requests
    if platform == "linkedin":
        import linkedin_poster
        person = linkedin_poster.get_person_id(token)
        r = requests.post(
            "https://api.linkedin.com/rest/comments",
            headers={"Authorization": "Bearer " + token, "LinkedIn-Version": "202601",
                     "X-Restli-Protocol-Version": "2.0.0",
                     "Content-Type": "application/json"},
            json={"actor": "urn:li:person:" + person,
                  "objectId": comment_id, "message": reply}, timeout=30)
        return r.status_code in (200, 201)
    if platform == "facebook":
        r = requests.post(GRAPH + "/" + comment_id + "/comments",
                          data={"message": reply, "access_token": token}, timeout=30)
        return r.status_code == 200
    if platform == "instagram":
        r = requests.post(GRAPH + "/" + comment_id + "/replies",
                          data={"message": reply, "access_token": token}, timeout=30)
        return r.status_code == 200
    return False


def main():
    ap = argparse.ArgumentParser(description="Draft and post human-like replies to comments.")
    ap.add_argument("--platforms", default="all")
    ap.add_argument("--post", action="store_true", help="Actually send replies (default: preview)")
    ap.add_argument("--sample", action="store_true",
                    help="Use sample comments (for testing without tokens)")
    args = ap.parse_args()

    wanted = set(args.platforms.replace(" ", "").split(","))
    if "all" in wanted:
        wanted = {"linkedin", "facebook", "instagram"}

    li = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    fb_id = os.environ.get("FACEBOOK_PAGE_ID")
    fb_tok = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")

    comments = []
    if args.sample:
        comments = [c for c in SAMPLE_COMMENTS if c[0] in wanted]
    else:
        if "linkedin" in wanted and li:
            comments += fetch_linkedin(li)
        if "facebook" in wanted and fb_id and fb_tok:
            comments += fetch_facebook(fb_id, fb_tok)
        if "instagram" in wanted and fb_id and fb_tok:
            comments += fetch_instagram(fb_id, fb_tok)

    if not comments:
        print("No comments found" + ("" if args.sample else
              " (add tokens, or use --sample to see a demo)."))
        return

    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)

    for platform, cid, author, text in comments:
        if cid in state:
            continue
        reply = ai_reply(author, text) or rule_reply(text)
        print("-" * 62)
        print("[%s] %s: %s" % (platform, author, text))
        print("  -> reply: " + reply)
        if args.post:
            token = li if platform == "linkedin" else fb_tok
            ok = send_reply(platform, cid, reply, token, fb_id)
            print("  " + ("sent ✓" if ok else "FAILED to send"))
            if ok:
                state[cid] = True
    os.makedirs("output", exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
    if not args.post:
        print("\n(preview only - add --post to send the replies)")


if __name__ == "__main__":
    main()
