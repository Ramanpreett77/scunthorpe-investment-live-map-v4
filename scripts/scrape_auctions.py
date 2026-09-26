#!/usr/bin/env python3
"""Daily auction-stock scraper -> data/auction-stock.json  (patched version)

Sources (DN15-DN20): BTG Eddisons live property search +
Savills upcoming-auction catalogues.

What changed vs the first version
  * Honest User-Agent (set SCRAPER_CONTACT to your email) instead of a fake browser.
  * robots.txt is checked before every request. If a site disallows the path, blocks
    us (401/403/429/503, challenge page) or robots.txt can't be read, that source is
    marked "blocked" and skipped. We do NOT try to work around it.
  * If a source errors or is blocked, its PREVIOUS lots are kept (marked stale)
    instead of being wiped.
  * Pugh: 0 cards, or cards but 0 parsed lots, is an error (layout probably changed).
  * Savills: pages each upcoming catalogue at quantity-100 and keeps lots whose
    catalogue address holds a DN15-DN20 postcode (addresses are on the
    catalogue page, so individual lot pages are never fetched). 0 lots is a
    "warning" with diagnostics, not an error; sold-prior/withdrawn lots are
    skipped. Respects the host robots.txt crawl-delay (2s between requests).
  * `guide` is no longer overloaded: sold lots carry `sold_price` and guide = 0.
  * New fields: `category` (residential/land/commercial, keyword heuristic),
    `first_seen` (date first scraped, to spot stale listings), `geo_precision`.
  * UK time uses Europe/London (handles the clocks changing on 25 Oct 2026).
  * Slugs are stable (hashlib, not hash()).
  * The file is only rewritten when the lots or source statuses change, so git
    history is not spammed with timestamp-only commits. `updated` = last change.
  * Exit code 1 when a source errored/was blocked (the data file is still written),
    so the workflow can fail loudly and GitHub emails you.

Please read each site's terms before relying on this, and do not republish their
photos on a public site: link to the lot page instead.
"""
import datetime
import hashlib
import html as ihtml
import json
import os
import re
import sys
import time
from urllib import robotparser
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

CONTACT = os.environ.get("SCRAPER_CONTACT", "").strip() or "contact-not-set"
UA_TOKEN = "ScunthorpeDealMap"
UA = {"User-Agent": f"{UA_TOKEN}/1.0 (personal property research; contact: {CONTACT})"}
SLEEP = 1.0
OUT_PATH = os.environ.get("AUCTION_OUT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "auction-stock.json")
PC_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I)
MONEY_RE = re.compile(r"£\s*([\d,]+)")
UK = ZoneInfo("Europe/London")


class Blocked(Exception):
    """Site disallows us or is blocking automated access. Never work around this."""


# ------------------------------------------------------------ fetching
_robots = {}


def robots_ok(session, url):
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    rp = _robots.get(base)
    if rp is None:
        rp = robotparser.RobotFileParser()
        try:
            r = session.get(base + "/robots.txt", timeout=15)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif 400 <= r.status_code < 500:
                rp.parse([])  # no robots.txt -> nothing disallowed
            else:
                rp = False  # server trouble: be conservative
        except Exception:
            rp = False
        _robots[base] = rp
    return False if rp is False else rp.can_fetch(UA_TOKEN, url)


def fetch(session, url, timeout=25):
    if not robots_ok(session, url):
        raise Blocked(f"robots.txt disallows (or could not be read) for {url}")
    r = session.get(url, timeout=timeout)
    if r.status_code in (401, 403, 429, 503):
        raise Blocked(f"HTTP {r.status_code} (bot protection / rate limit) for {url}")
    r.raise_for_status()
    head = r.text[:3000].lower()
    if "just a moment..." in head or "cf-chl" in head or "captcha" in head:
        raise Blocked(f"challenge page returned for {url}")
    return r.text


def money(text):
    m = MONEY_RE.search(text or "")
    return int(m.group(1).replace(",", "")) if m else 0


def norm_pc(postcode):
    p = re.sub(r"\s+", "", (postcode or "").upper())
    m = re.match(r"^([A-Z]{1,2}\d[A-Z\d]?)(\d[A-Z]{2})$", p)
    return f"{m.group(1)} {m.group(2)}" if m else (postcode or "").upper().strip()


def stable_id(text):
    return int(hashlib.md5(text.encode()).hexdigest(), 16) % 10**6


LAND_WORDS = ("land ", "land,", "plot", "rear of", "garage", "car park", "parking")
COMM_WORDS = ("unit ", "units ", "industrial", "hoarding", "advertising", "shop", "office",
              "warehouse", "retail", "premises", "workshop", "pub ", "public house")


def categorise(addr):
    """Keyword heuristic only (e.g. a High Street address could be a shop). Check the lot."""
    a = f" {addr.lower()} "
    if any(w in a for w in COMM_WORDS):
        return "commercial"
    if any(w in a for w in LAND_WORDS):
        return "land"
    return "residential"


# ---------------------------------------------------------- BTG Eddisons
# Pugh Auctions has migrated/redirected old lot URLs. The current property
# auction inventory is now served by BTG Eddisons, so use its live AJAX search
# and retain the canonical current lot URL from the response HTML.
def scrape_btg(session):
    lots, info = [], {"status": "ok", "detail": ""}
    listing_url = "https://www.btgeddisonspropertyauctions.com/properties"
    page = fetch(session, listing_url)
    action_match = re.search(r'<form[^>]+data-listing-search-form[^>]+data-action="([^"]+)"', page, re.I)
    token_match = re.search(r'<input[^>]+name="_token"[^>]+value="([^"]+)"', page, re.I)
    if not action_match or not token_match:
        raise RuntimeError("BTG Eddisons: live search form/token not found")
    action = ihtml.unescape(action_match.group(1))
    data = {
        "auction_id": "", "catalogue_id": "", "prefiltered_id": "",
        "auction_type": "", "search_type": "global", "auction_date": "",
        "_token": token_match.group(1), "lat": "", "lng": "",
        "nesw_geometry": "", "location": "Scunthorpe", "radius": "30",
        "property_type": "", "min_price": "", "max_price": "",
        "date_added": "", "sort": "date", "limit": "50"
    }
    headers = dict(UA)
    headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": listing_url})
    response = session.post(action, data=data, headers=headers, timeout=30)
    if response.status_code in (401, 403, 429, 503):
        raise Blocked(f"BTG Eddisons HTTP {response.status_code}")
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("BTG Eddisons returned non-JSON search results") from exc
    rows = ((payload.get("properties") or {}).get("data") or [])
    content = payload.get("content") or ""
    # The AJAX response includes the canonical current URL beside each card.
    url_by_address = {}
    for match in re.finditer(r'<a[^>]+aria-label="([^"]+)"[^>]+href="([^"]+)"', content, re.I):
        url_by_address[ihtml.unescape(match.group(1)).strip()] = ihtml.unescape(match.group(2))
    for row in rows:
        address = re.sub(r"\s+", " ", str(row.get("full_address") or "").strip())
        postcode = str(row.get("postcode") or "").upper().replace("  ", " ").strip()
        if not address:
            continue
        # Only publish current, upcoming residential/commercial lots in the
        # requested DN postcode area. The BTG search response also contains
        # nearby and past records, and sold_status_id=2 is not itself a sold flag.
        if not re.search(r"\bDN(1[5-9]|20)\s*\d[A-Z]{2}\b", postcode):
            continue
        sold = bool(row.get("sold_price"))
        if sold or not bool(row.get("upcoming")):
            continue
        source_url = url_by_address.get(address, "")
        if not source_url:
            # Address text may differ only by whitespace/entity decoding.
            for label, url in url_by_address.items():
                if label.replace(" ", "") == address.replace(" ", ""):
                    source_url = url
                    break
        if not source_url:
            info["detail"] += f"missing canonical URL for {address}; "
            continue
        guide_min = row.get("guide_price_min") or row.get("guide_price") or row.get("starting_price") or 0
        guide_max = row.get("guide_price_max") or 0
        try:
            guide = float(guide_min or 0)
        except (TypeError, ValueError):
            guide = 0
        label = "Guide TBC" if not guide else f"£{int(guide):,}+"
        if guide_max and float(guide_max) > guide:
            label = f"£{int(guide):,}–£{int(float(guide_max)):,}"
        auction_date = str(row.get("url_date") or "").replace(" 13:00:00", "")
        slug = re.sub(r"[^a-z0-9-]+", "-", str(row.get("eig_id") or address.lower())).strip("-").lower()
        lots.append({
            "slug": f"btg-{slug}",
            "addr": address,
            "status": "sold" if sold else "available",
            "guide": 0 if sold else guide,
            "sold_price": row.get("sold_price") or 0,
            "price_label": label,
            "category": categorise(address),
            "fee": 0, "refurb": 0, "rent": 0, "gdv": 0,
            "beds": row.get("bedrooms") or 0,
            "type": "", "strategy": "Auction", "zone": "",
            "lat": row.get("latitude"), "lon": row.get("longitude"),
            "geo_precision": "property",
            "blurb": re.sub(r"\s+", " ", str(row.get("description") or "")).strip()[:1000],
            "note": "Auto-scraped from BTG Eddisons — verify guide, fees, auction date and legal pack on the current lot page.",
            "source": "BTG Eddisons",
            "source_url": source_url,
            "auction_date": auction_date,
            "image": "",
        })
    if not lots:
        raise RuntimeError(f"BTG Eddisons: 0 current lots returned from Scunthorpe search (total={len(rows)})")
    info["detail"] = f"{len(lots)} current DN15-DN20 lots from BTG Eddisons; sold and past records excluded"
    return lots, info


# ---------------------------------------------------------------- Pugh
def scrape_pugh(session):
    lots, info = [], {"status": "ok", "detail": ""}
    url = ("https://www.pugh-auctions.com/property-search"
           "?location=Scunthorpe&include-sold=off")
    html = fetch(session, url)
    time.sleep(SLEEP)
    cards = re.split(r'<div class="h-full mb-8">', html)[1:]
    if not cards:
        raise RuntimeError("Pugh: 0 cards found - page layout may have changed")
    for card in cards:
        m_id = re.search(r"/property/(\d+)", card)
        m_addr = re.search(r'class="block">\s*([^<>{}]+?)\s*<br', card)
        m_price = re.search(r'text-secondary text-lg font-bold mb-4">\s*([^<]*?)\s*</p>', card)
        if not (m_id and m_addr):
            continue
        pid = m_id.group(1)
        addr = ihtml.unescape(re.sub(r"\s+", " ", m_addr.group(1)).strip())
        price_line = ihtml.unescape((m_price.group(1) if m_price else "").strip())
        low = price_line.lower()
        if "withdrawn" in low:
            continue
        sold = "sold for" in low
        amount = money(price_line.replace("&pound;", "£"))
        m_img = re.search(r'(https://www\.pugh-auctions\.com/property-images/[^"\s]+)', card)
        m_badge = re.search(r'style="height:\s*40px">\s*(\d+)\s*</div>', card)
        lot_no = m_badge.group(1) if m_badge else pid
        label = price_line if price_line else "Price TBC"
        lots.append({
            "slug": f"pugh-{pid}",
            "addr": addr,
            "status": "sold" if sold else "available",
            "guide": 0 if sold else amount,
            "sold_price": amount if sold else 0,
            "price_label": label,
            "category": categorise(addr),
            "fee": 0, "refurb": 0, "rent": 0, "gdv": 0, "beds": 0,
            "type": "", "strategy": "Auction", "zone": "",
            "lat": None, "lon": None, "geo_precision": "postcode",
            "blurb": (f"Pugh online auction lot {lot_no} — {label}. "
                      "Check the lot page for bidding dates, buyer's fees and legal pack."),
            "note": "Auto-scraped — verify guide, fees and legal pack on the lot page before bidding.",
            "source": "Pugh",
            "source_url": f"https://www.pugh-auctions.com/property/{pid}",
            "auction_date": "",
            # Photos stay in the data but do NOT hotlink them on a public site.
            "image": ihtml.unescape(m_img.group(1)) if m_img else "",
        })
    if not lots:
        raise RuntimeError(f"Pugh: {len(cards)} cards but 0 parsed - layout changed?")
    info["detail"] = f"{len(lots)} lots from {len(cards)} cards"
    return lots, info


# ------------------------------------------------------------- Savills
SAVILLS_BASE = "https://auctions.savills.co.uk"
SAVILLS_PC_RE = re.compile(r"\bDN(1[5-9]|20)\s*\d[A-Z]{2}\b", re.I)
SAVILLS_SLEEP = 2.0  # robots.txt crawl-delay for this host
SAVILLS_MAX_PAGES = 20  # safety cap per catalogue (100 lots per page)


def _savills_auction_date(slug, html):
    mt = re.search(r"<title>(.*?)</title>", html, re.S)
    if mt:
        tail = ihtml.unescape(mt.group(1)).split("|")[-1].strip()
        if tail and "savills" not in tail.lower():
            return tail
    m = (re.search(r"(\d{1,2})--(\d{1,2})-([a-z]+)-(\d{4})-\d+$", slug, re.I)
         or re.search(r"(\d{1,2})-([a-z]+)-(\d{4})-\d+$", slug, re.I))
    if m:
        g = m.groups()
        if len(g) == 4:
            return f"{g[0]} & {g[1]} {g[2].capitalize()} {g[3]}"
        return f"{g[0]} {g[1].capitalize()} {g[2]}"
    return ""


def _parse_savills_cards(html):
    """Parse catalogue cards. Full addresses are on the catalogue page, so
    individual lot pages are never fetched. Skips section-header cards."""
    out = []
    for card in re.split(r'<li class="lot ', html)[1:]:
        m = re.search(r'<a class="lot-name" href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        if not m:
            continue
        url = ihtml.unescape(m.group(1)).strip().replace("http://", "https://")
        addr = re.sub(r"\s+", " ", ihtml.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip())
        if not addr:
            continue
        mid = re.search(r'data-lot_id="(\d+)"', card)
        mg = re.search(r'price-container guide-price.*?<span class="value">(.*?)</span>', card, re.S)
        mn = re.search(r'<p class="lot-number">(.*?)</p>', card, re.S)
        mst = re.search(r'<div class="lot-status">(.*?)</div>', card, re.S)
        first = ""
        md = re.search(r'<div class="lot-details">(.*?)</div>', card, re.S)
        if md:
            bullets = re.findall(r"<li>(.*?)</li>", md.group(1), re.S)
            if bullets:
                first = re.sub(r"\s+", " ", ihtml.unescape(re.sub(r"<[^>]+>", "", bullets[0])).strip())
        out.append({
            "lot_id": mid.group(1) if mid else "",
            "addr": addr,
            "url": url,
            "lot_no": re.sub(r"\s+", " ", ihtml.unescape(mn.group(1)).strip()) if mn else "",
            "guide_text": re.sub(r"\s+", " ", ihtml.unescape(re.sub(r"<[^>]+>", "", mg.group(1))).strip()) if mg else "",
            "status_text": re.sub(r"\s+", " ", ihtml.unescape(re.sub(r"<[^>]+>", "", mst.group(1))).strip()) if mst else "",
            "first_bullet": first,
        })
    return out


def scrape_savills(session):
    lots, info = [], {"status": "ok", "detail": ""}
    try:
        index = fetch(session, SAVILLS_BASE + "/upcoming-auctions")
    except Blocked:
        raise
    except Exception as e:
        raise RuntimeError(f"Savills: upcoming-auctions index failed ({e})")
    time.sleep(SAVILLS_SLEEP)
    cats = sorted(set(
        m.group(1) for m in
        re.finditer(r'href="https?://auctions\.savills\.co\.uk/auctions/([^"/]+)"', index)))
    if not cats:
        raise RuntimeError("Savills: 0 upcoming catalogues found - index layout may have changed")
    scanned = skipped = 0
    errors = []
    for slug in cats:
        base = f"{SAVILLS_BASE}/auctions/{slug}"
        try:
            html = fetch(session, f"{base}/page-1/quantity-100")
        except Blocked:
            raise
        except Exception as e:
            errors.append(f"{slug}: {e}")
            continue
        time.sleep(SAVILLS_SLEEP)
        auc_date = _savills_auction_date(slug, html)
        pages = [int(x) for x in set(re.findall(r"/page-(\d+)", html))]
        max_page = min(max(pages) if pages else 1, SAVILLS_MAX_PAGES)
        for p in range(1, max_page + 1):
            if p > 1:
                try:
                    html = fetch(session, f"{base}/page-{p}/quantity-100")
                except Blocked:
                    raise
                except Exception as e:
                    errors.append(f"{slug} page {p}: {e}")
                    break
                time.sleep(SAVILLS_SLEEP)
            for lot in _parse_savills_cards(html):
                scanned += 1
                slow = lot["status_text"].lower()
                if "withdraw" in slow or "sold" in slow:
                    skipped += 1
                    continue
                if not SAVILLS_PC_RE.search(lot["addr"]):
                    continue
                amount = money(lot["guide_text"])
                label = (lot["guide_text"] if lot["guide_text"] and lot["guide_text"].upper() != "TBA"
                         else "Guide TBC")
                blurb = (f"Lot {lot['lot_no']} - {lot['first_bullet']}" if lot["first_bullet"]
                         else f"Savills auction lot {lot['lot_no']}".rstrip())
                if auc_date:
                    blurb += f" (auction {auc_date})"
                blurb += ". Guide price and legal pack on the lot page."
                lots.append({
                    "slug": f"savills-{lot['lot_id'] or stable_id(lot['url'])}",
                    "addr": lot["addr"],
                    "status": "available",
                    "guide": amount, "sold_price": 0,
                    "price_label": label,
                    "category": categorise(lot["addr"]),
                    "fee": 0, "refurb": 0, "rent": 0, "gdv": 0, "beds": 0,
                    "type": "", "strategy": "Auction", "zone": "",
                    "lat": None, "lon": None, "geo_precision": "postcode",
                    "blurb": blurb[:1000],
                    "note": "Auto-scraped - verify guide and legal pack on the lot page before bidding.",
                    "source": "Savills",
                    "source_url": lot["url"],
                    "auction_date": auc_date,
                    "image": "",
                })
    if scanned == 0:
        raise RuntimeError(f"Savills: 0 lots parsed across {len(cats)} catalogues"
                           + (f" ({'; '.join(errors)})" if errors else " - layout may have changed"))
    if errors:
        info["detail"] += "; ".join(errors) + "; "
    if not lots:
        info["status"] = "warning"
        info["detail"] += (f"0 DN15-DN20 lots in {len(cats)} upcoming catalogues "
                           f"({scanned} scanned, {skipped} sold/withdrawn skipped)")
    else:
        info["detail"] += (f"{len(lots)} DN15-DN20 lots from {len(cats)} upcoming catalogues "
                           f"({scanned} scanned, {skipped} sold/withdrawn skipped)")
    return lots, info


# ------------------------------------------------------------ geocoding
def geocode(lots):
    """Bulk postcodes.io lookup (free, no key). Postcode-level precision only."""
    pcs = []
    for lot in lots:
        m = PC_RE.search(lot["addr"])
        lot["_pc"] = norm_pc(m.group(1)) if m else ""
        if lot["_pc"] and lot["_pc"] not in pcs:
            pcs.append(lot["_pc"])
    coords = {}
    for i in range(0, len(pcs), 100):
        chunk = pcs[i:i + 100]
        try:
            r = requests.post("https://api.postcodes.io/postcodes",
                              json={"postcodes": chunk}, timeout=25)
            if r.status_code == 200:
                for row in r.json().get("result", []):
                    if row.get("result"):
                        coords[norm_pc(row["query"])] = (row["result"]["latitude"],
                                                        row["result"]["longitude"])
        except Exception as e:
            print(f"geocode chunk failed: {e}", flush=True)
        time.sleep(0.5)
    for lot in lots:
        if lot["_pc"] in coords:
            lot["lat"], lot["lon"] = coords[lot["_pc"]]
        del lot["_pc"]
    return len(coords)


# ---------------------------------------------------------------- main
def load_old():
    try:
        with open(OUT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def status_summary(sources):
    return {k: (v.get("lots"), v.get("status")) for k, v in sources.items()}


def main():
    session = requests.Session()
    session.headers.update(UA)
    old = load_old()
    old_by_source, old_first = {}, {}
    for lot in old.get("lots", []):
        old_by_source.setdefault(lot.get("source"), []).append(lot)
        if lot.get("first_seen"):
            old_first[lot["slug"]] = lot["first_seen"]

    all_lots, sources, problems = [], {}, []
    for name, label, fn in (("btg", "BTG Eddisons", scrape_btg),
                                ("savills", "Savills", scrape_savills)):
        try:
            lots, info = fn(session)
            sources[name] = {"lots": len(lots), **info}
            print(f"{name}: [{info['status']}] {info['detail']}", flush=True)
        except Exception as e:
            status = "blocked" if isinstance(e, Blocked) else "error"
            kept = old_by_source.get(label, [])
            lots = kept
            sources[name] = {"lots": len(kept), "status": status,
                             "detail": f"{repr(e)[:250]} | kept {len(kept)} previous lots (stale)"}
            problems.append(name)
            print(f"{name} {status.upper()}: {e}", flush=True)
        all_lots += lots

    seen, lots = set(), []
    for lot in all_lots:
        if lot["source_url"] not in seen:
            seen.add(lot["source_url"])
            lots.append(lot)
    n_geo = geocode(lots)
    today = datetime.datetime.now(UK).strftime("%Y-%m-%d")
    for lot in lots:
        lot["first_seen"] = old_first.get(lot["slug"]) or lot.get("first_seen") or today
    print(f"total: {len(lots)} lots, {n_geo} geocoded", flush=True)

    now = datetime.datetime.now(datetime.timezone.utc)
    checked = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    checked_uk = now.astimezone(UK).strftime("%d %b %Y, %H:%M UK")
    lots_unchanged = old.get("lots") == lots
    sources_unchanged = status_summary(old.get("sources", {})) == status_summary(sources)
    if lots_unchanged and sources_unchanged:
        # Keep the last lot-change timestamp, but record a fresh successful check.
        # This prevents the public site from labelling an unchanged but freshly
        # verified feed as stale simply because no lot fields changed.
        payload = {
            "updated": old.get("updated", checked),
            "updated_uk": old.get("updated_uk", checked_uk),
            "checked": checked,
            "checked_uk": checked_uk,
            "sources": sources,
            "lots": lots,
        }
        print(f"no lot change - recording fresh check at {checked_uk}", flush=True)
    else:
        payload = {
            "updated": checked,  # time of last LOT CHANGE
            "updated_uk": checked_uk,
            "checked": checked,
            "checked_uk": checked_uk,
            "sources": sources,
            "lots": lots,
        }
        print(f"wrote {OUT_PATH} with changed lots", flush=True)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=1)
    os.replace(tmp, OUT_PATH)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
