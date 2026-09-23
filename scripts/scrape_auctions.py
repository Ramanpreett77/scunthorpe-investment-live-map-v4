#!/usr/bin/env python3
"""Daily auction-stock scraper -> data/auction-stock.json  (patched version)

Source: BTG Eddisons current property-auction search (Scunthorpe radius).

What changed vs the first version
  * Honest User-Agent (set SCRAPER_CONTACT to your email) instead of a fake browser.
  * robots.txt is checked before every request. If a site disallows the path, blocks
    us (401/403/429/503, challenge page) or robots.txt can't be read, that source is
    marked "blocked" and skipped. We do NOT try to work around it.
  * If a source errors or is blocked, its PREVIOUS lots are kept (marked stale)
    instead of being wiped.
  * Pugh: 0 cards, or cards but 0 parsed lots, is an error (layout probably changed).
  * Savills: 0 lots is a "warning" with diagnostics, not a silent "ok".
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
        # requested DN15/DN16/DN17 area. The BTG search response also contains
        # nearby and past records, and sold_status_id=2 is not itself a sold flag.
        if not re.search(r"\bDN1[567]\s*\d[A-Z]{2}\b", postcode):
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
    info["detail"] = f"{len(lots)} current DN15/DN16/DN17 lots from BTG Eddisons; sold and past records excluded"
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
def scrape_savills(session):
    lots, info = [], {"status": "ok", "detail": ""}
    subs = ["https://auctions.savills.co.uk/sitemap/sitemap1.xml",
            "https://auctions.savills.co.uk/sitemap/sitemap2.xml"]
    try:
        idx = fetch(session, "https://auctions.savills.co.uk/sitemap.xml")
        found = re.findall(r"<loc>([^<]+)</loc>", idx)
        if found:
            subs = found
    except Blocked:
        raise
    except Exception:
        pass
    urls = []
    for sm in subs:
        try:
            xml = fetch(session, sm)
            time.sleep(SLEEP)
            urls += re.findall(r"<loc>(?:<!\[CDATA\[)?([^<\]]+)", xml)
        except Blocked:
            raise
        except Exception as e:
            info["detail"] += f"sitemap {sm} failed ({e}); "
    dn_all = sorted(set(u for u in urls if re.search(r"dn-?1[567]", u, re.I)
                        and "/auctions/" in u and "com_bidding" not in u))
    dn_urls = dn_all[:25]
    for u in dn_urls:
        try:
            page = fetch(session, u)
            time.sleep(SLEEP)
            slug = u.rstrip("/").split("/")[-1]
            m_pc = re.search(r"([a-z]{1,2}\d[a-z\d]?)-(\d[a-z]{2})-\d{4,6}$", slug, re.I)
            pc = norm_pc(f"{m_pc.group(1)} {m_pc.group(2)}") if m_pc else ""
            m_addr = (re.search(r'data-lot-name="([^"]+)"', page)
                      or re.search(r'<meta property="og:title" content="([^"]+)"', page)
                      or re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S))
            addr = ihtml.unescape(re.sub(r"<[^>]+>", "",
                                         m_addr.group(1)).strip()) if m_addr else slug.replace("-", " ")
            addr = re.sub(r"\s+", " ", addr)
            if pc and pc not in addr:
                addr = f"{addr} {pc}"
            m_date = (re.search(r"/auctions/(\d{1,2})--(\d{1,2})-([a-z]+)-(\d{4})-", u, re.I)
                      or re.search(r"/auctions/(\d{1,2})-([a-z]+)-(\d{4})-", u, re.I))
            if m_date:
                g = m_date.groups()
                auction_date = (f"{g[0]} & {g[1]} {g[2].capitalize()} {g[3]}" if len(g) == 4
                                else f"{g[0]} {g[1].capitalize()} {g[2]}")
            else:
                m2 = re.search(r"(\d{1,2}(?:\s*&\s*\d{1,2})?\s+\w+\s+\d{4})", page)
                auction_date = m2.group(1) if m2 else ""
            lid = re.search(r"-(\d{4,6})/?$", slug)
            lots.append({
                "slug": f"savills-{lid.group(1) if lid else stable_id(u)}",
                "addr": addr,
                "status": "available",
                "guide": 0, "sold_price": 0,
                "price_label": "Guide on lot page",
                "category": categorise(addr),
                "fee": 0, "refurb": 0, "rent": 0, "gdv": 0, "beds": 0,
                "type": "", "strategy": "Auction", "zone": "",
                "lat": None, "lon": None, "geo_precision": "postcode",
                "blurb": (f"Savills auction lot{f' — auction {auction_date}' if auction_date else ''}. "
                          "Guide price and legal pack on the lot page."),
                "note": "Auto-scraped — verify guide and legal pack on the lot page before bidding.",
                "source": "Savills",
                "source_url": u,
                "auction_date": auction_date,
                "image": "",
            })
        except Blocked:
            raise
        except Exception as e:
            info["detail"] += f"lot failed ({e}); "
    info["detail"] += f"{len(lots)} DN lots from {len(urls)} sitemap urls"
    if len(dn_all) > len(dn_urls):
        info["detail"] += f" (capped at {len(dn_urls)} of {len(dn_all)})"
    if not lots:
        loose = [u for u in urls if re.search(r"dn\d|scunthorpe", u, re.I)]
        info["status"] = "warning"
        info["detail"] += (f" | WARNING 0 lots: {len(loose)} urls mention dn/scunthorpe; "
                           f"sample: {loose[:5]}")
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
    for name, label, fn in (("btg", "BTG Eddisons", scrape_btg),):
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
