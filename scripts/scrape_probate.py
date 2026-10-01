#!/usr/bin/env python3
"""
Gazette Probate Watch (PRIVATE pipeline).

Fetches Deceased Estates notices for North Lincolnshire / North East
Lincolnshire from The Gazette's official open API, filters to DN15-DN20
postcodes, and logs NEW notices to the owner's private Google Sheet
(probate stream).

PRIVACY-BY-DESIGN:
  * Personal data (names/addresses) is NEVER written to the public repo,
    never published, and only lands in the owner's private spreadsheet.
  * The only file committed to the repo is data/probate-seen.json, which
    stores anonymous notice IDs (no personal data) purely for de-duplication.
  * The watch is a research/pipeline-preparation tool: no one is contacted
    from it while the business remains pre-registration.

Data source: The Gazette (Crown copyright, Open Government Licence).
"""
import json
import os
import re
import sys
from datetime import date, timedelta

try:
    import requests
except ImportError:  # pragma: no cover
    print("requests missing"); sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(HERE, "..", "data", "probate-seen.json")
SHEET_URL = os.environ.get(
    "SHEET_URL",
    "https://script.google.com/macros/s/AKfycbyEU1RcmAaQOIGZF01Jk_bBJvm8XmlvjSgS16iR-nfJ9WEqcPL8pF7ne29Asm6lYCg0fA/exec",
)
DN = re.compile(r"\bDN\s*(1[5-9]|20)\s*\d\s*[A-Z]{2}\b", re.I)
API = "https://www.thegazette.co.uk/wills-and-probate/notice/data.json"
HEADERS = {"User-Agent": "SGJM-research/1.0 (private probate watch)"}


def fetch_feed(days=45):
    params = {
        "location-local-authority-1": "North Lincolnshire",
        "location-local-authority-2": "North East Lincolnshire",
        "start-publish-date": (date.today() - timedelta(days=days)).isoformat(),
        "results-page-size": 200,
        "sort-by": "latest-date",
    }
    r = requests.get(API, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def parse_fields(html):
    out = {}
    for k, v in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", html or "", re.S):
        out[re.sub(r"\s+", " ", k).strip().lower()] = re.sub(
            r"<[^>]+>", "", re.sub(r"\s+", " ", v)
        ).strip()
    return out


def main():
    feed = fetch_feed()
    entries = feed.get("entry", []) or []
    seen = set()
    if os.path.exists(SEEN):
        seen = set(json.load(open(SEEN)))

    new_ids, logged = [], 0
    for e in entries:
        nid = (e.get("id") or "").rsplit("/", 1)[-1]
        if not nid or nid in seen:
            continue
        fields = parse_fields(e.get("content", ""))
        addr = fields.get("address of deceased", "") or e.get("title", "")
        m = DN.search(addr + " " + json.dumps(fields))
        if not m:
            continue  # outside DN15-DN20
        new_ids.append(nid)
        dod = fields.get("date of death", "")
        occ = fields.get("occupation of deceased", "")
        pr = fields.get("personal representative", "") or fields.get("executor", "")
        sol = fields.get("address of personal representative", "") or ""
        claim = fields.get("claim expires", "") or fields.get("last date for claims", "")
        url = "https://www.thegazette.co.uk/notice/" + nid
        message = " | ".join(
            x for x in [
                "Address: " + addr if addr else "",
                "DoD: " + dod if dod else "",
                "Occupation: " + occ if occ else "",
                "PR/Executor: " + pr if pr else "",
                "PR addr: " + sol if sol else "",
                "Claims by: " + claim if claim else "",
                "Published: " + (e.get("published") or "")[:10],
                url,
            ] if x
        )
        payload = {
            "source": "probate watch",
            "name": (e.get("title") or "").strip(),
            "email": "",
            "phone": "",
            "postcode": (m.group(0) or "").upper(),
            "message": message,
        }
        if SHEET_URL:
            try:
                requests.post(
                    SHEET_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "text/plain;charset=utf-8"},
                    timeout=60,
                )
                logged += 1
                print("  + logged:", payload["name"], payload["postcode"])
            except Exception as ex:
                print("  ! sheet post failed:", str(ex)[:100])
        else:
            print("  (dry-run)", payload["name"], payload["postcode"])

    if new_ids:
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        json.dump(sorted(seen | set(new_ids)), open(SEEN, "w"), indent=1)

    total = feed.get("f:total", len(entries))
    print(f"Probate watch: {total} notices in area window, "
          f"{len(new_ids)} new DN15-DN20, {logged} logged to sheet.")


if __name__ == "__main__":
    main()
