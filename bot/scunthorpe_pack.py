#!/usr/bin/env python3
"""
Scunthorpe Auction Watch — data-driven weekly article.

Reads data/auction-stock.json (produced by scripts/scrape_auctions.py) and
writes/refreshes this week's "Auction Watch" article into bot/_posts.
The daily scrape workflow runs this after every stock refresh, so the
numbers in the live article are never more than a day old.

Pure stdlib. Safe to re-run: one file per ISO week (Monday-dated slug).
"""
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "auction-stock.json")
OUT_DIR = os.path.join(HERE, "_posts")


def money(x):
    return f"£{int(x):,}"


def monday_of(d):
    return d - datetime.timedelta(days=d.weekday())


def extract_district(addr):
    m = re.search(r"\bDN\s*(\d{2})\b", (addr or "").upper())
    return "DN" + m.group(1) if m else None


def load_stock():
    try:
        with open(DATA, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"updated_uk": "unknown", "sources": {}, "lots": []}


def build_article(stock, today):
    lots = stock.get("lots", []) or []
    avail = [l for l in lots if l.get("status") != "sold"]
    sold = [l for l in lots if l.get("status") == "sold"]
    guides = [float(l.get("guide") or 0) for l in avail if float(l.get("guide") or 0) > 0]

    # postcode district counts
    districts = {}
    for l in avail:
        d = extract_district(l.get("addr", ""))
        if d:
            districts[d] = districts.get(d, 0) + 1

    # category counts
    cats = {}
    for l in avail:
        c = (l.get("category") or "Other").strip() or "Other"
        cats[c] = cats.get(c, 0) + 1

    src = stock.get("sources", {})
    src_line = ", ".join(
        f"{name.upper()}: {info.get('lots', 0)} lot(s)" for name, info in sorted(src.items())
    ) or "no sources reported"

    mon = monday_of(today)
    week_label = mon.strftime("%d %B %Y")

    if avail:
        gmin, gmax = min(guides), max(guides) if guides else 0
        gavg = sum(guides) / len(guides) if guides else 0
        price_bit = (
            f"guides from {money(gmin)} to {money(gmax)}"
            + (f" (average {money(gavg)})" if guides else " (guides TBC)")
        )
        title = f"Scunthorpe Auction Watch: {len(avail)} Live Lot{'s' if len(avail) != 1 else ''} This Week"
        excerpt = (
            f"Week of {week_label}: {len(avail)} unsold auction lot(s) tracked across DN15-DN20, "
            f"{price_bit}. Full breakdown, district hotspots and what to check before you bid."
        )
    else:
        title = "Scunthorpe Auction Watch: A Quiet Week — and What That Means for Buyers"
        excerpt = (
            f"Week of {week_label}: no unsold DN15-DN20 auction lots tracked right now. "
            f"Why quiet catalogues are an opportunity, and how to be first in line when stock returns."
        )

    L = []
    L.append("---")
    L.append("layout: post")
    L.append(f'title: "{title}"')
    L.append(f"date: {today.isoformat()}")
    L.append('categories: Scunthorpe Auction Watch')
    L.append(f'excerpt: "{excerpt}"')
    L.append("---")
    L.append("")
    L.append(
        f"*Updated automatically from live auction data on {stock.get('updated_uk', 'an unknown date')} "
        f"({src_line}). This page refreshes every day the data refreshes.*"
    )
    L.append("")
    L.append(
        "Every week we track the auction catalogues covering Scunthorpe and the wider DN15-DN20 "
        "area - the same data that powers our [live auction stock map](../index.html). "
        "Here is this week's picture."
    )
    L.append("")

    if avail:
        L.append("## The numbers at a glance")
        L.append("")
        L.append(f"- **Live unsold lots:** {len(avail)}")
        if sold:
            L.append(f"- **Sold/withdrawn lots still showing:** {len(sold)}")
        if guides:
            L.append(f"- **Guide prices:** {money(min(guides))} - {money(max(guides))}"
                     + (f" (average {money(gavg)})" if len(guides) > 1 else ""))
        else:
            L.append("- **Guide prices:** TBC at the auctioneer's pages")
        if districts:
            top = ", ".join(f"**{d}** ({n})" for d, n in sorted(districts.items()))
            L.append(f"- **Districts represented:** {top}")
        if cats:
            catline = ", ".join(f"{c} ({n})" for c, n in sorted(cats.items()))
            L.append(f"- **Stock types:** {catline}")
        L.append("")
        L.append("## This week's lots")
        L.append("")
        for l in avail:
            addr = (l.get("addr") or "Address TBC").strip()
            label = l.get("price_label") or "Guide TBC"
            beds = l.get("beds") or 0
            cat = (l.get("category") or "").strip()
            head = f"### {addr} — {label}"
            L.append(head)
            L.append("")
            bits = []
            if beds:
                bits.append(f"{beds} bedroom{'s' if beds != 1 else ''}")
            if cat:
                bits.append(cat)
            dist = extract_district(addr)
            if dist:
                bits.append(dist)
            if bits:
                L.append("*" + " | ".join(bits) + "*")
                L.append("")
            blurb = (l.get("blurb") or "").strip()
            if blurb:
                L.append(blurb[:400])
                L.append("")
            note = (l.get("note") or "").strip()
            if note:
                L.append(f"> {note}")
                L.append("")
    else:
        L.append("## Why the board is empty this week")
        L.append("")
        L.append(
            "Right now our tracker shows **no unsold auction lots with a DN15-DN20 postcode**. "
            "That happens regularly - auction stock moves in waves around catalogue dates, and between "
            "catalogues the board can empty completely. It does not mean deals have stopped existing; "
            "it means the next batch is still being assembled."
        )
        L.append("")
        L.append(
            "For buyers, quiet weeks are quietly useful: they're when you get your financing lined up, "
            "your solicitor briefed and your viewing checklist sharpened - so when the next catalogue "
            "drops, you can move in days rather than weeks. The investors who win auction property "
            "consistently are almost always the ones who were ready *before* the lot appeared."
        )
        L.append("")
        L.append("## How to be first in line when stock returns")
        L.append("")
        L.append(
            "1. **Bookmark the [live auction map](../index.html)** - it updates automatically every morning."
        )
        L.append(
            "2. **Tell us your buying criteria** via the [contact page](contact.html) - we're building an "
            "investor waitlist and will flag lots that match."
        )
        L.append(
            "3. **Read our [postcode guide](2026-10-01-scunthorpe-postcode-guide.html)** so you know which "
            "districts fit your strategy when stock appears."
        )
        L.append("")

    L.append("## What to verify before you bid")
    L.append("")
    L.append(
        "Guide prices are marketing numbers, not valuations. Before committing: read the legal pack "
        "(special conditions, searches, tenure), get your own refurb quotes, check comparable sold "
        "prices on the street, and confirm the buyer's premium and any extra fees with the auctioneer. "
        "Everything on this page is information, not financial advice."
    )
    L.append("")
    L.append(
        "*Want these updates in your inbox the moment stock appears? Use the form on our "
        "[contact page](contact.html) and we'll keep you posted.*"
    )
    L.append("")
    return "\n".join(L), mon


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.date.today()
    stock = load_stock()
    if not stock.get("lots"):
        # Quiet week: publish nothing rather than an empty "quiet week" post.
        # Existing posts are left untouched.
        print("Auction Watch skipped: data/auction-stock.json holds 0 lots")
        return
    body, mon = build_article(stock, today)
    slug = f"{mon.isoformat()}-scunthorpe-auction-watch"
    path = os.path.join(OUT_DIR, slug + ".md")
    old = None
    if os.path.exists(path):
        old = open(path, encoding="utf-8").read()
    if old == body:
        print(f"Auction Watch unchanged ({slug})")
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    lots = len([l for l in stock.get("lots", []) if l.get("status") != "sold"])
    print(f"Auction Watch written: {slug} ({lots} live lots)")


if __name__ == "__main__":
    main()
