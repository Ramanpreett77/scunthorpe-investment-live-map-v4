#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persona-aware article writer.

Drop-in replacement for `blog_generator.py --ai` inside the draft workflow:

  python3 persona_writer.py --ai --persona first-time-btl --topic first-buy-to-let \
      --date 2026-10-12 --out _drafts --site-url https://...

What it adds over blog_generator:
  * the article is written FOR one specific audience (voice, objections,
    worked examples, call-to-action, closing question),
  * it ends with a genuine question (comments, not just clicks),
  * guardrails are baked into the prompt: illustrative figures labelled as such,
    no guarantees, no invented case studies, testimonials or named clients,
  * writes the same output/latest.json schema the carousel builder and the
    social poster already expect (plus a "persona" block).

Falls back to the existing template engine (blog_generator) if there is no
OPENAI_API_KEY or the API call fails - the draft always gets written.
"""
import argparse
import json
import os
import random
import re
import sys
from datetime import date as _date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import personas  # noqa: E402
from blog_generator import TOPICS, DISCLAIMER, REGION_DEFAULT, build_markdown  # noqa: E402


# ----------------------------------------------------------------- helpers ---
def slug_of(path):
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(path))[:-3]


def used_slugs():
    d = os.path.join(HERE, "_posts")
    out = set()
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".md"):
                out.add(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f)[:-3])
    return out


def unique_slug(base, used, dt):
    """Keep page URLs unique. A reused topic gets a dated variant slug
    (e.g. first-buy-to-let -> first-buy-to-let-2026) so the new article can
    never overwrite an older article's page."""
    if base not in used:
        return base
    for cand in ("%s-%d" % (base, dt.year), "%s-%d-%02d" % (base, dt.year, dt.month)):
        if cand not in used:
            return cand
    i = 2
    while "%s-%d-%d" % (base, dt.year, i) in used:
        i += 1
    return "%s-%d-%d" % (base, dt.year, i)


def resolve_topic(slug, persona):
    """Best-fit ordering: unused topic for this persona -> unused topic overall
    -> a refreshed older topic (dated slug) -> random."""
    used = used_slugs()
    if slug:
        t = next((t for t in TOPICS if t["slug"] == slug), None)
        if not t:
            sys.exit("Unknown topic '%s'. Available: %s"
                     % (slug, ", ".join(x["slug"] for x in TOPICS)))
        return t
    pick = personas.pick_topic(persona, used)
    if pick:
        t = next((t for t in TOPICS if t["slug"] == pick), None)
        if t:
            return t
    unused = [t for t in TOPICS if t["slug"] not in used]
    if unused:
        return random.choice(unused)
    # everything has been written before: refresh the persona's best fit
    t = next((t for t in TOPICS if t["slug"] == persona["topic_affinity"][0]), None)
    return t or random.choice(TOPICS)


# ------------------------------------------------------------- AI generation ---
def persona_prompt(title, topic, persona, year, region, question, cta):
    outline = "\n".join("- " + s["heading"] for s in topic["sections"])
    objections = "\n".join("- " + o for o in persona["objections"])
    examples = "\n".join("- " + e for e in persona["examples"])
    return (
        "You write for a UK property blog read by investors and homeowners in "
        f"{region}.\n\n"
        f"WRITE FOR THIS READER: {persona['audience']}.\n"
        f"They care most about: {persona['focus']}.\n"
        f"Voice/tone: {persona['voice']}.\n\n"
        "Answer these real objections somewhere in the piece:\n"
        f"{objections}\n\n"
        "Ground the article with at least one of these worked examples:\n"
        f"{examples}\n\n"
        f"Article title: {title}\n"
        f"Cover these sections (you may rename them slightly):\n{outline}\n\n"
        "STRUCTURE: open with a concrete situation this reader recognises, then the "
        "sections, then a '## Key Takeaways' bullet list, then a short call to action "
        f"({cta}) that ENDS WITH THIS QUESTION EXACTLY AS WRITTEN: \"{question}\"\n\n"
        "HARD RULES (these keep the content compliant):\n"
        "- Any figures (prices, rents, yields, costs) are ILLUSTRATIVE and must be "
        "labelled as such in the sentence that uses them.\n"
        "- Never promise, guarantee or imply a return, profit or outcome.\n"
        "- Never invent case studies, success stories, testimonials, named clients, "
        "completed deals or 'one of our clients' examples.\n"
        "- No personalised financial, tax or legal advice - signpost a professional.\n"
        "- Write 750-950 words. Plain English. Short paragraphs. UK spelling.\n"
        "- Return Markdown only: no title heading, no front matter.\n"
    )


def ai_body(title, topic, persona, year, region):
    """Returns (body_markdown, engine_label) - never raises."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None, "template (no OPENAI_API_KEY)"
    try:
        import requests
        prompt = persona_prompt(title, topic, persona, year, region,
                                persona["question"], persona["cta"])
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.8,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        body = (r.json()["choices"][0]["message"]["content"] or "").strip()
        if not body:
            return None, "template (empty AI response)"
        # make sure the closing question survived
        if persona["question"].rstrip("?").lower() not in body.lower():
            body += "\n\n" + persona["question"]
        return body, "AI (%s)" % os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    except Exception as e:
        print("  ! AI engine unavailable (%s) - using template engine." % str(e)[:120])
        return None, "template (AI error)"


def template_body(topic, dt, region, persona):
    """Deterministic fallback using the existing generator, plus the question."""
    title, md = build_markdown(topic, dt, region)
    body = md.split("---", 2)[2].strip()
    if persona["question"].rstrip("?").lower() not in body.lower():
        body += "\n\n**Over to you:** " + persona["question"]
    return title, body


# --------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser(description="Persona-aware article writer.")
    ap.add_argument("--ai", action="store_true", help="Use OpenAI when a key is set")
    ap.add_argument("--persona", help="Persona id (default: this week's rotation)")
    ap.add_argument("--topic", help="Topic slug (default: best fit for the persona)")
    ap.add_argument("--date", help="Publish date YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default="_drafts", help="Output directory")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    ap.add_argument("--region", default=os.environ.get("BLOG_REGION", REGION_DEFAULT))
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    persona = personas.get(args.persona) or personas.persona_for_date()
    if args.persona and not personas.get(args.persona):
        sys.exit("Unknown persona '%s'. Try: python3 personas.py --list" % args.persona)

    topic = resolve_topic(args.topic, persona)
    dt = _date.fromisoformat(args.date) if args.date else _date.today()
    slug = unique_slug(topic["slug"], used_slugs(), dt)

    print("Persona : %s (%s)" % (persona["name"], persona["id"]))
    print("Topic   : %s" % topic["slug"])

    if args.ai:
        body, engine = ai_body(topic["titles"][0].format(year=dt.year), topic,
                               persona, dt.year, args.region)
        if body is None:
            title, body = template_body(topic, dt, args.region, persona)
        else:
            title = topic["titles"][0].format(year=dt.year)
    else:
        title, body = template_body(topic, dt, args.region, persona)
        engine = "template (no --ai flag)"

    excerpt = topic["excerpt"]
    front = (
        "---\n"
        "layout: post\n"
        'title: "%s"\n'
        "date: %s\n"
        "categories: %s\n"
        'excerpt: "%s"\n'
        "---\n\n" % (title.replace('"', "'"), dt.isoformat(),
                      topic["category"], excerpt.replace('"', "'"))
    )

    os.makedirs(args.out, exist_ok=True)
    fname = os.path.join(args.out, "%s-%s.md" % (dt.isoformat(), slug))
    with open(fname, "w", encoding="utf-8") as f:
        f.write(front + body + "\n")

    meta = {
        "title": title,
        "slug": slug,
        "date": dt.isoformat(),
        "category": topic["category"],
        "excerpt": excerpt,
        "hook": topic["hook"],
        "takeaways": topic["takeaways"],
        "hashtags": persona["hashtags"] or topic["hashtags"],
        "url_path": "/posts/%s.html" % slug,
        "file": fname,
        "site_url": args.site_url,
        "persona": {
            "id": persona["id"],
            "name": persona["name"],
            "audience": persona["audience"],
            "focus": persona["focus"],
            "question": persona["question"],
            "cta": persona["cta"],
            "linkedin_angle": persona["linkedin_angle"],
            "social_angle": persona["social_angle"],
        },
        "engine": engine,
        "disclaimer": DISCLAIMER,
    }
    os.makedirs("output", exist_ok=True)
    with open("output/latest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("Engine  : %s" % engine)
    print("Title   : %s" % title)
    print("File    : %s" % fname)
    print("Meta    : output/latest.json")
    print("Question: %s" % persona["question"])


if __name__ == "__main__":
    main()
