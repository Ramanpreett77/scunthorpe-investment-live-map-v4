#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persona library for the SGJM content engine.

Six real audience types. Each persona steers the VOICE, the objections answered,
the worked examples, the call-to-action and the closing question of every
article and social post - so the content stops sounding like "everyone" and
starts speaking to someone.

Design rules (kept honest on purpose):
  * No fake authors, fake clients, fake testimonials or invented case studies.
  * Figures are illustrative and must be labelled as such.
  * No guarantees, no promised returns, no advice dressed as fact.

Rotation: ISO week number % number of personas - deterministic, stateless,
so Saturday's draft rotates through the six audiences week by week.
"""
import datetime
import os
import re

# --------------------------------------------------------------- personas ---
# ----------------------------------------------- pre-registration CTA gating ---
# While the site's config.js keeps PRE_REGISTRATION_MODE on, persona CTAs must
# not offer services (sourcing work, deal reviews, "no fee" first looks): new
# articles and LinkedIn first comments go through effective_cta(), which swaps
# in PREREG_CTA. Flip the flag at launch and the original CTAs restore
# automatically - no code change needed.
PREREG_CTA = (
    "I'm still pre-launch while registrations complete, so I can't take on "
    "sourcing work yet - the free tools and weekly breakdowns are the best "
    "place to start for now."
)

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "config.js")


def preregistration_mode(path=None):
    """True while config.js keeps PRE_REGISTRATION_MODE on (fail-safe: True)."""
    try:
        with open(path or _CONFIG_PATH, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return True
    m = re.search(r"PRE_REGISTRATION_MODE\s*:\s*(true|false)", text)
    if not m:
        return True
    return m.group(1) == "true"


def effective_cta(persona, prereg=None):
    """Persona CTA honouring pre-registration mode.

    `persona` may be a PERSONAS entry or a latest.json persona dict.
    """
    if prereg is None:
        prereg = preregistration_mode()
    if prereg:
        return PREREG_CTA
    return (persona.get("cta") or "").strip()


PERSONAS = [
    {
        "id": "first-time-btl",
        "name": "First-time BTL investor",
        "audience": "first-time buy-to-let investor",
        "focus": "making a first purchase without losing money",
        "voice": "reassuring, plain English, zero jargon, explains every term on first use",
        "objections": [
            "Is this the right time to buy my first rental?",
            "What if the tenant stops paying or the property sits empty?",
            "How much do I really need up front beyond the deposit?",
        ],
        "examples": [
            "a worked purchase with deposit, SDLT, legal fees and refurb broken out line by line",
            "a monthly cash-flow table showing rent minus mortgage, voids, insurance, maintenance",
        ],
        "cta": "If you want, I can talk you through what a realistic first purchase looks like in your budget.",
        "question": "What is the one thing holding you back from your first buy-to-let?",
        "linkedin_angle": "peer-to-peer and practical - like an investor two steps ahead, not a guru",
        "social_angle": "warm and simple; assume no property knowledge at all",
        "hashtags": ["#BuyToLet", "#FirstTimeInvestor", "#UKProperty"],
        "topic_affinity": ["first-buy-to-let", "brr-strategy", "choose-a-property-sourcer"],
    },
    {
        "id": "portfolio-hmo",
        "name": "Scaling portfolio landlord / HMO",
        "audience": "landlord scaling to a portfolio or HMO",
        "focus": "yield, licensing, refinancing and portfolio efficiency",
        "voice": "numbers-first, confident, treats the reader as experienced",
        "objections": [
            "Does the yield survive the refurb, the licence and the void?",
            "Will the lender refinance me out and at what rate?",
            "Is the HMO Premium / Article 4 position going to bite me?",
        ],
        "examples": [
            "a room-by-room HMO yield calculation versus a single let on the same property",
            "a refinance example showing capital recycled into the next purchase",
        ],
        "cta": "Happy to compare numbers if you already have a property in mind.",
        "question": "At what point did you decide single lets were no longer enough - and what changed?",
        "linkedin_angle": "technical and specific - lead with numbers, licensing and lender realities",
        "social_angle": "practical local landlords group tone; focus on rules and yield",
        "hashtags": ["#HMO", "#PropertyPortfolio", "#BuyToLet"],
        "topic_affinity": ["hmo-investing", "refinancing-portfolio", "brr-strategy"],
    },
    {
        "id": "cash-auction",
        "name": "Cash buyer / auction & refurb",
        "audience": "cash buyer working auctions and refurbishments",
        "focus": "deal-finding, maximum-offer maths and refurb risk",
        "voice": "direct, blunt about risk, respects the reader's time",
        "objections": [
            "What is my true maximum offer given the refurb and the exit?",
            "What am I legally committed to once the hammer falls?",
            "How do I spot a deal-shaped trap in the catalogue?",
        ],
        "examples": [
            "a maximum-offer calculation: GDV, refurb cost, fees, contingency, target profit",
            "a refurb risk checklist - structure, damp, title, tenancy, service charges",
        ],
        "cta": "If you are working a lot right now, send it over and I will sense-check the numbers.",
        "question": "What is your rule of thumb for maximum offer on an auction lot?",
        "linkedin_angle": "deal-room tone - maximum-offer maths, cat-and-mouse with the guide price",
        "social_angle": "local and concrete - auction lots, refurb costs, areas to watch",
        "hashtags": ["#PropertyAuction", "#Refurbishment", "#BRRR"],
        "topic_affinity": ["sourcing-deals", "brr-strategy", "refinancing-portfolio"],
    },
    {
        "id": "local-seller",
        "name": "Local seller needing speed",
        "audience": "homeowner who needs to sell quickly (probate, arrears, difficult tenant, heavy refurb)",
        "focus": "speed, certainty and a clean, private sale with no fees to the seller",
        "voice": "calm, respectful, no pressure, never salesy - this person may be having a hard time",
        "objections": [
            "Will this be kept private? I do not want it on Rightmove or door-knocked.",
            "What is a cash sale actually worth against an estate agent's headline price?",
            "Am I locked in? What do I pay you?",
        ],
        "examples": [
            "a side-by-side of an estate-agency route versus a cash sale: timeline, certainty, net figure",
            "what happens after an enquiry, step by step, with no obligation",
        ],
        "cta": "If you just want an honest view of your options, with no obligation, get in touch - there is no fee to you as the seller.",
        "question": "If you are dealing with a property that needs a quick, private sale - what would help most?",
        "linkedin_angle": "local and human; speak to the professional who refers these cases (solicitors, executors, agents)",
        "social_angle": "gentle, local, plain - speed without pressure, privacy first",
        "hashtags": ["#ProbateProperty", "#QuickHouseSale", "#Lincolnshire"],
        "topic_affinity": ["sourcing-deals", "choose-a-property-sourcer"],
    },
    {
        "id": "dubai-curious",
        "name": "Dubai-curious UK investor",
        "audience": "UK investor considering Dubai alongside (or instead of) the UK",
        "focus": "honest comparison, buyer protection, costs and exit - not glossy brochure talk",
        "voice": "measured and honest; equally happy recommending patience or saying no",
        "objections": [
            "How does Dubai actually compare with UK yields after all the fees?",
            "What protects my money if the developer delays or vanishes?",
            "What are the real costs - service charge, agent fees, exit - and the tax position?",
        ],
        "examples": [
            "a like-for-like comparison: same money, one UK property versus one Dubai unit, net of fees",
            "the escrow / RERA / registration steps a UK buyer should verify before paying",
        ],
        "cta": "If you want, I can walk you through what a like-for-like comparison looks like for your budget.",
        "question": "Would you rather own one UK property or one Dubai unit with the same money - and why?",
        "linkedin_angle": "counter-hype: risks, fees, protections and exits; never a developer advert",
        "social_angle": "curious but sensible; address scams and costs head-on",
        "hashtags": ["#DubaiProperty", "#UKInvestors", "#RERA"],
        "topic_affinity": ["uk-vs-dubai-property", "dubai-buyer-protection", "dubai-offplan-vs-ready"],
    },
    {
        "id": "overseas-buyer",
        "name": "Overseas buyer investing in the UK",
        "audience": "overseas or expat buyer investing in the UK from abroad",
        "focus": "buying safely at a distance: currency, tax, management and who to trust",
        "voice": "clear, patient, explains UK-specific quirks (SDLT, leasehold, licensing) from scratch",
        "objections": [
            "Can I buy without flying over, and who physically sees the property?",
            "How do SDLT, overseas buyer surcharges and the non-resident tax rules work?",
            "How is the property managed and the rent remitted if I am 5,000 miles away?",
        ],
        "examples": [
            "a cost stack for an overseas buyer: purchase taxes, surcharges, FX, legal and management",
            "the remote buying process step by step, including independent verification",
        ],
        "cta": "If you are buying from abroad, I am happy to explain how the process works remotely.",
        "question": "If you are buying UK property from overseas - what is your biggest worry about doing it remotely?",
        "linkedin_angle": "trust-building: process, verification and costs; never pressure",
        "social_angle": "welcoming and explanatory; assume zero UK knowledge",
        "hashtags": ["#UKProperty", "#OverseasInvestors", "#Expat"],
        "topic_affinity": ["uk-vs-dubai-property", "first-buy-to-let", "choose-a-property-sourcer"],
    },
]

BY_ID = {p["id"]: p for p in PERSONAS}
GENERIC_QUESTION = "What would you want to know before making a move like this?"


def get(persona_id):
    """Persona dict by id, or None."""
    return BY_ID.get((persona_id or "").strip())


# Offset so the cycle opens on the UK audiences and the two international
# personas land in the later weeks of the six-week loop (UK-first ordering):
#   week A: first-time BTL   week D: local seller
#   week B: portfolio / HMO  week E: Dubai-curious
#   week C: cash / auction   week F: overseas buyer
ROTATION_OFFSET = 2


def persona_for_date(d=None):
    """Deterministic weekly rotation: (ISO week + offset) % 6."""
    d = d or datetime.date.today()
    return PERSONAS[(d.isocalendar()[1] + ROTATION_OFFSET) % len(PERSONAS)]


def pick_topic(persona, used_slugs):
    """Prefer a topical fit for this persona that has not been published yet."""
    used = set(used_slugs or [])
    affinity = [s for s in persona["topic_affinity"] if s not in used]
    if affinity:
        return affinity[0]
    unused = [s for s in persona["topic_affinity"]]
    return unused[0] if unused else None


def issue_lines(persona):
    """The two lines shown at the top of the approval issue."""
    return [
        "**Audience:** %s" % persona["audience"],
        "**Focus:** %s" % persona["focus"],
    ]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Persona list / rotation inspector")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--for-week", action="store_true", help="persona for this ISO week")
    ap.add_argument("--show", help="show one persona by id")
    ap.add_argument("--affinity", action="store_true", help="topic affinity per persona")
    a = ap.parse_args()

    if a.show:
        p = get(a.show)
        if not p:
            print("Unknown persona. Try --list")
        else:
            for k, v in p.items():
                print("%-16s %s" % (k + ":", v))
    elif a.for_week:
        p = persona_for_date()
        print("%s  (%s)" % (p["id"], p["name"]))
    elif a.affinity:
        for p in PERSONAS:
            print("%-16s -> %s" % (p["id"], ", ".join(p["topic_affinity"])))
    else:
        for i, p in enumerate(PERSONAS, 1):
            print("%d. %-16s %s" % (i, p["id"], p["name"]))
            print("      audience: %s" % p["audience"])
            print("      question: %s" % p["question"])
