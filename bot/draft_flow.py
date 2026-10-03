#!/usr/bin/env python3
"""Helpers for the blog draft -> approval -> publish flow.

Used by .github/workflows/draft-blog.yml. Read-only: changes nothing.

  python3 bot/draft_flow.py --next-monday          # -> 2026-10-05
  python3 bot/draft_flow.py --pick-topic           # -> a topic slug not used yet
  python3 bot/draft_flow.py --title bot/_drafts/2026-10-05-hmo-investing.md
"""
import argparse
import glob
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(HERE, "_posts")


def next_monday():
    """Next Monday strictly after today (Sat -> Mon in 2 days, Mon -> +7)."""
    from datetime import date, timedelta

    d = date.today()
    d += timedelta(days=(7 - d.weekday()) % 7 or 7)
    return d.isoformat()


def used_slugs():
    """Slugs already published in bot/_posts (from the YYYY-MM-DD-slug.md names)."""
    used = set()
    for f in glob.glob(os.path.join(POSTS_DIR, "*.md")):
        b = os.path.basename(f)
        used.add(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", b)[:-3])
    return used


def all_topics():
    sys.path.insert(0, HERE)
    import blog_generator as bg  # noqa: E402  (defines TOPICS, no side effects)

    return [t["slug"] for t in bg.TOPICS]


def pick_topic(exclude=None):
    used = used_slugs() | {x for x in (exclude or []) if x}
    topics = all_topics()
    unused = [t for t in topics if t not in used]
    return random.choice(unused or topics)


def title_of(path):
    text = open(path, encoding="utf-8").read()
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M)
    return m.group(1) if m else os.path.basename(path)


def main():
    ap = argparse.ArgumentParser(description="Draft/publish flow helpers.")
    ap.add_argument("--next-monday", action="store_true")
    ap.add_argument("--pick-topic", action="store_true")
    ap.add_argument("--exclude", help="Comma list of slugs to avoid")
    ap.add_argument("--title", metavar="POST_FILE")
    args = ap.parse_args()

    if args.next_monday:
        print(next_monday())
    elif args.pick_topic:
        print(pick_topic((args.exclude or "").split(",")))
    elif args.title:
        print(title_of(args.title))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
