#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Property Blog Auto-Generator
============================
Generates UK property-investment blog articles (HMO, BRR, buy-to-let,
refinancing, deal sourcing) as ready-to-publish files for a GitHub Pages site.

Two writing engines:
  1. Built-in template engine (default) - no API key, no cost, works offline.
  2. Optional AI engine - set the OPENAI_API_KEY env var and pass --ai to get
     unique, natural-language articles via the OpenAI API.

Usage:
  python3 blog_generator.py                  # random topic -> ./_posts (Jekyll)
  python3 blog_generator.py --topic brr      # specific topic
  python3 blog_generator.py --list           # show all available topics
  python3 blog_generator.py --format html    # standalone HTML instead of Markdown
  python3 blog_generator.py --ai             # use OpenAI when a key is available
"""
import argparse
import datetime as _dt
import json
import os
import random
import re
import sys

REGION_DEFAULT = "Scunthorpe & North Lincolnshire"

DISCLAIMER = (
    "This article is for general information only and is not financial, tax or "
    "legal advice. Tax treatment, licensing rules and lending criteria change "
    "frequently - always confirm current requirements with your local council and "
    "a qualified professional before acting. Any example figures are illustrative only."
)

CTAS = [
    "**Enjoyed this breakdown?** I publish practical UK property investment "
    "articles like this every week - covering HMOs, BRR, buy-to-let and real deal "
    "numbers. Follow along and never miss one.",
    "**Building a portfolio in {region}?** Save this article and check back soon - "
    "the next practical breakdown is already on the way.",
]

# ---------------------------------------------------------------------------
# TOPIC BANK - edit/extend freely. Placeholders available: {year} {region}
# ---------------------------------------------------------------------------
TOPICS = [
    {
        "slug": "brr-strategy",
        "topic_short": "BRR",
        "category": "BRR",
        "categories": ["BRR", "Strategy"],
        "hashtags": ["#UKProperty", "#PropertyInvestment", "#BRR", "#BuyToLet", "#Scunthorpe"],
        "titles": [
            "The BRR Strategy in {year}: How UK Investors Keep Recycling the Same Capital",
            "BRR Investing Explained: Buy, Refurbish, Refinance - Then Go Again",
        ],
        "hook": "Most investors think every new property needs a fresh deposit. The best BRR investors keep reusing the same capital. Here's how",
        "excerpt": "How the Buy-Refurbish-Refinance strategy works, a worked example of capital recycling, and the risks to stress-test before your first project.",
        "intros": [
            "Ask most people how to build a property portfolio and they'll say the same thing: save a deposit, buy, save the next deposit, repeat. It works - until your savings run out. The BRR strategy is how investors break that limit: instead of parking capital in each deal, they pull it back out and deploy it again. In this article I'll break down how BRR works in {year}, walk through a realistic set of numbers, and highlight the risks that trip up first-timers.",
            "BRR - Buy, Refurbish, Refinance - has become one of the most talked-about strategies in UK property investing, and for good reason: done properly, one pot of capital can fund several deals. But the gap between a BRR that works on a spreadsheet and one that works in real life comes down to a handful of details. Let's go through them.",
        ],
        "sections": [
            {
                "heading": "What BRR actually means",
                "paragraphs": [
                    "**Buy** a property below its true market value - usually something that needs work, which keeps most retail buyers away. **Refurbish** it to a standard that lifts the value (and the rent). **Refinance** with a buy-to-let lender on the new, higher valuation.",
                    "The magic is in the refinance. If the improved value is high enough, a new mortgage at around 75% loan-to-value can repay most - sometimes all - of the cash you put in. That cash is then free to fund the next deal. This is why BRR investors talk about *recycling* capital rather than *spending* it.",
                ],
            },
            {
                "heading": "Step 1 - Find a genuine below-market-value purchase",
                "paragraphs": [
                    "Every successful BRR starts at the purchase. The discount you secure is both your profit and your safety margin - you can't manufacture it later with a clever refurbishment.",
                ],
                "bullets": [
                    "**Auctions** - still one of the best places to find properties with issues that scare off the crowd. Always do your due diligence before you bid.",
                    "**Long-listed properties** - listings that have sat on the market for months, where the seller is tired and the price is stale.",
                    "**Direct-to-vendor** - leafleting, local networking and word-of-mouth with landlords wanting to exit.",
                    "**Probate and motivated sellers** - situations where speed and certainty matter more to the seller than the last five thousand pounds.",
                    "Rule of thumb: if everyone can see it's a bargain on Rightmove, it probably isn't one anymore.",
                ],
            },
            {
                "heading": "Step 2 - Control the refurbishment",
                "paragraphs": [
                    "Refurbishment overrun is the number one BRR killer. Projects go wrong when investors price the works in their head instead of on paper.",
                ],
                "bullets": [
                    "Get fixed-price quotes from at least two contractors before you exchange.",
                    "Hold a **10-20% contingency** on top of the budget - always.",
                    "Spend where value is created: kitchen, bathroom, layout, light, EPC rating. Don't over-spec for the area.",
                    "Agree a written schedule of works with stage payments.",
                ],
            },
            {
                "heading": "Step 3 - Refinance at the new value",
                "paragraphs": [
                    "Once the works are done - ideally with tenants in place - a broker or lender will arrange a new valuation. Most BTL lenders will go up to around 75% LTV, but only if the valuer can *see* the improvements. Photographic evidence of the before-state, receipts, and comparable sales all help.",
                    "Important: line the refinance up **before you buy**. Some lenders have minimum ownership periods (often six months), while others will lend sooner if you can prove the purchase was genuinely below market value. A good BTL broker will know exactly which is which in {year}.",
                ],
            },
            {
                "heading": "A worked example (illustrative)",
                "paragraphs": [
                    "Here's how a typical BRR can stack up on a Midlands terrace. All figures are illustrative examples, not a real deal:",
                ],
                "bullets": [
                    "Purchase price (below market value): **£128,000**",
                    "Refurbishment budget: **£26,000** (with a £6,500 contingency held back)",
                    "Fees (SDLT, legal, brokerage): **~£7,500**",
                    "Total capital deployed: **~£161,500**",
                    "End value after works: **£190,000**",
                    "Refinance at 75% LTV: **£142,500**",
                    "Capital left in: **~£19,000** - roughly 12% of total cost, while you keep the equity gain",
                    "Now take that recycled £142,500 and put it towards deal number two. That's the BRR loop.",
                ],
            },
            {
                "heading": "The risks to stress-test",
                "paragraphs": [
                    "BRR fails when one assumption breaks. Before you commit, stress-test these:",
                ],
                "bullets": [
                    "**Valuation risk** - if the valuer comes in £15k under your end value, the refinance shortfall comes out of your pocket.",
                    "**Interest rate risk** - check the rent still covers the mortgage at a stressed rate of 7-8%. Lenders will do this anyway.",
                    "**Time risk** - every extra month of refurb is extra bridging interest or lost rent. Build in slack.",
                    "**Planning and licensing** - if you're changing use (for example, converting to an HMO), check Article 4 directions and licensing with the local council first.",
                ],
            },
        ],
        "takeaways": [
            "BRR recycles capital - the goal is to pull your money back out, not to sell.",
            "Profit is made at the purchase. No refurb rescues a bad buy.",
            "Line up the refinance before you buy, and know the lender's ownership rules.",
            "Always hold a 10-20% refurb contingency.",
            "Stress-test the rent at 7-8% interest before you commit.",
        ],
    },
    {
        "slug": "hmo-investing",
        "topic_short": "HMO investing",
        "category": "HMO",
        "categories": ["HMO", "Strategy"],
        "hashtags": ["#HMO", "#UKProperty", "#PropertyInvestment", "#BuyToLet", "#Scunthorpe"],
        "titles": [
            "HMO Investing in {year}: Yields, Licensing and What It Really Costs to Start",
            "Is an HMO Right for Your Portfolio? Yields, Licensing and Setup Costs Explained",
        ],
        "hook": "Single-let yields of 5-6% are fine. HMOs in the right area can genuinely deliver double digits gross. But there's work behind those numbers",
        "excerpt": "Why HMOs deliver some of the strongest yields in UK property, what licensing and setup cost, and a worked example from Scunthorpe.",
        "intros": [
            "If you want the strongest rental yields in UK property, Houses in Multiple Occupation keep coming up - and for good reason. Renting by the room instead of the property can push gross yields into double digits in areas like {region}. But HMOs aren't passive income: they come with licensing, higher setup costs and more hands-on management. Here's an honest breakdown for {year}.",
            "Walk through any investor meet-up in {region} and someone will be talking HMOs. The maths is genuinely attractive - but so is the fine print. Licensing rules, room sizes, fire doors, management intensity. This guide covers what you actually need to know before you convert your first property.",
        ],
        "sections": [
            {
                "heading": "Why HMOs outperform single lets",
                "paragraphs": [
                    "A standard buy-to-let rents to one household at one rent. An HMO rents to several unrelated tenants, each paying for their own room. The total of those room rents is usually well above what the same property would earn as a family home.",
                    "Demand is strong where there are young professionals, students, key workers and contractors - which is exactly why HMOs work well in cities and commuter towns across {region}.",
                ],
            },
            {
                "heading": "Licensing: the part you cannot skip",
                "paragraphs": [
                    "HMO rules exist for good reasons, and they're enforced. Getting them wrong can mean fines and - worse for a portfolio - rent repayment orders.",
                ],
                "bullets": [
                    "**Mandatory HMO licence** - required in England when five or more people from two or more households share facilities (always check the exact current thresholds).",
                    "**Additional licensing** - many councils run schemes that catch smaller HMOs too. These vary street by street, borough by borough.",
                    "**Article 4 directions** - in some areas, permitted development rights to convert a house (C3) to a small HMO (C4) have been removed, so you'll need planning permission.",
                    "**Selective licensing** - some councils licence even ordinary single lets in certain wards.",
                    "Golden rule: before you buy, check licensing with the local council for that exact address. Not next door - that address.",
                ],
            },
            {
                "heading": "What it costs to set up",
                "paragraphs": [
                    "Converting a family home into a compliant HMO means real capital work, not just buying more beds.",
                ],
                "bullets": [
                    "Fire doors, alarm systems and escape routes to current standards",
                    "Kitchen and bathroom capacity for the tenant count",
                    "Room sizes that meet national minimum space standards",
                    "Furnishing every room to a professional standard",
                    "As a very rough guide, investors budget **£15,000-£45,000** for a typical 4-6 bed conversion depending on condition - always price the actual property with contractor quotes.",
                ],
            },
            {
                "heading": "A worked example (illustrative)",
                "paragraphs": [
                    "Here's how a typical small HMO can stack up in {region} - illustrative figures only:",
                ],
                "bullets": [
                    "Purchase price: **£185,000**",
                    "Conversion and compliance works: **£35,000**",
                    "Total cost: **£220,000**",
                    "Five rooms at an average of **£550 pcm** (bills included) = **£2,750 pcm**, or £33,000 per year",
                    "Gross yield on total cost: **~15%** - but remember HMO running costs are higher: bills, per-room voids, more wear, and often management at 10-15% of rent",
                    "Net of those extras, many well-run HMOs land in the 9-12% range - still well above a typical single let",
                ],
            },
            {
                "heading": "Managing an HMO is a job",
                "paragraphs": [
                    "Five tenants means five times the comings and goings: moves, deposits, disputes, and the day-to-day of shared living. Most investors either self-manage with solid systems (house rules, cleaning rota, proper maintenance process) or pay a specialist HMO agent.",
                    "Budget for it either way. An HMO that's badly managed will underperform a well-managed single let every time.",
                ],
            },
        ],
        "takeaways": [
            "HMOs trade higher yields for more complexity - licensing, cost, management.",
            "Check mandatory, additional and selective licensing for the exact address before buying.",
            "Budget £15k-£45k for a typical conversion and price it with real quotes.",
            "Gross yields of 10%+ are realistic; judge deals on the net figure after bills and management.",
            "Self-manage with systems, or pay a specialist HMO agent - don't wing it.",
        ],
    },
    {
        "slug": "first-buy-to-let",
        "topic_short": "buy-to-let",
        "category": "Buy-to-Let",
        "categories": ["BuyToLet", "Guides"],
        "hashtags": ["#BuyToLet", "#UKProperty", "#PropertyInvestment", "#Landlord"],
        "titles": [
            "Your First Buy-to-Let in {year}: A Step-by-Step UK Guide",
            "How to Buy Your First Buy-to-Let Property in {year} (Without Costly Mistakes)",
        ],
        "hook": "Thinking about your first buy-to-let? These are the steps - and the expensive mistakes - every new investor should know before offer #1",
        "excerpt": "The practical route to a first UK buy-to-let: ownership structure, deposits, SDLT, mortgages and the numbers that actually matter.",
        "intros": [
            "Buying your first buy-to-let isn't hard - but it is different from buying a home to live in. The taxes are different, the mortgages are different, and the way you judge the property is completely different. Here's the process in plain English, as it stands in {year}.",
            "Most first-time landlord mistakes happen before the offer is even accepted: wrong structure, underestimated tax, or a property chosen with the heart instead of a spreadsheet. Let's build your first buy-to-let properly.",
        ],
        "sections": [
            {
                "heading": "Step 1 - Choose your ownership structure",
                "paragraphs": [
                    "You can buy in your personal name or through a limited company (an SPV). There's no universal right answer: personal ownership is simpler, while company ownership can be more tax-efficient at scale because mortgage interest relief for individuals is restricted to a basic-rate tax credit.",
                    "Speak to a property-specialist accountant before you buy - it's much easier to get this right up front than to transfer a property into a company later, which triggers its own tax considerations.",
                ],
            },
            {
                "heading": "Step 2 - Know the true cost of entry",
                "bullets": [
                    "**Deposit** - typically 25% for buy-to-let, occasionally 20% with strong numbers.",
                    "**SDLT** - an additional **5% surcharge** applies on top of standard rates when buying an additional dwelling (the rules were tightened in April 2025 - budget on current tables).",
                    "**Fees** - mortgage arrangement, broker, legal, survey. Budget a few thousand pounds, not a few hundred.",
                    "**Works and furnishing** - make the property rentable on day one.",
                ],
            },
            {
                "heading": "Step 3 - Get the mortgage right",
                "paragraphs": [
                    "Buy-to-let mortgages are a specialist product. Lenders stress-test the rent - typically requiring the rent to cover around **125-145% of the monthly mortgage payment at a stressed rate** - and most deals are interest-only, which keeps monthly costs predictable while the tenant's rent does the work.",
                    "A whole-of-market BTL broker is worth their fee here: coverage ratios, minimum incomes and product availability shift constantly.",
                ],
            },
            {
                "heading": "Step 4 - Buy for the tenant, not for yourself",
                "paragraphs": [
                    "Pick an area you know (or will learn properly) - for many investors that's their own region, like {region}. Research tenant demand, transport links, employment and comparable rents, then buy what those tenants actually want, not the house you'd personally live in.",
                ],
            },
            {
                "heading": "Step 5 - Make the numbers work",
                "paragraphs": [
                    "Before you offer, run the full monthly cost stack:",
                ],
                "bullets": [
                    "Mortgage payment (stress-tested at a higher rate)",
                    "Insurance, ground rent and service charge where applicable",
                    "A maintenance reserve of **5-10% of rent**",
                    "Voids - one empty month a year is roughly an 8% hit",
                    "Agent and management fees if you're not self-managing",
                    "If the property doesn't cash-flow after all of that, it's not an investment yet - it's a bet on house prices.",
                ],
            },
            {
                "heading": "First-timer mistakes to avoid",
                "bullets": [
                    "Buying a property you like instead of one the target tenant wants",
                    "Under-budgeting the refurb and furnishing",
                    "Ignoring licensing, EPC and safety requirements (the rules keep tightening - check the current standards)",
                    "Skipping the stress test and discovering the mortgage eats the rent when rates move",
                ],
            },
        ],
        "takeaways": [
            "Structure first: personal name vs limited company is a decision to make before you shop.",
            "Budget the true entry cost - 25% deposit plus the 5% additional-dwelling SDLT surcharge.",
            "Aim for positive cash flow after every cost, with the rent stress-tested.",
            "Buy for the tenant profile of the area, not your own taste.",
            "Check licensing, EPC and safety rules before exchange.",
        ],
    },
    {
        "slug": "refinancing-portfolio",
        "topic_short": "refinancing",
        "category": "Finance",
        "categories": ["Finance", "Strategy"],
        "hashtags": ["#UKProperty", "#Refinance", "#PropertyInvestment", "#Landlord"],
        "titles": [
            "Property Refinancing in {year}: When to Remortgage and How Much You Can Release",
            "Refinancing Your Rental Property: A Practical Guide for UK Landlords",
        ],
        "hook": "The cheapest deposit for your next deal might already be sitting in your existing portfolio. Here's how refinancing unlocks it",
        "excerpt": "When refinancing makes sense, how lenders value your property, and how to release equity without stretching yourself too thin.",
        "intros": [
            "Equity that sits idle in a property isn't working. Refinancing - remortgaging to a new deal on a fresh valuation - is how experienced landlords wake that equity up and put it into the next deal. Here's how to judge if it's your moment in {year}.",
            "Every portfolio eventually hits the same question: do you save for the next purchase, or release equity from what you already own? For most investors, the answer is refinancing - but only when the numbers justify it. Let's walk through the decision.",
        ],
        "sections": [
            {
                "heading": "Why landlords refinance",
                "bullets": [
                    "To **release equity** after value has grown - through market movement, refurbishment or conversion",
                    "To **escape an expiring fixed rate** before rolling onto an expensive standard variable rate",
                    "To **consolidate** several mortgages onto better overall terms",
                    "To **fund the next deal** without years of saving",
                ],
            },
            {
                "heading": "How much can you release?",
                "paragraphs": [
                    "Most buy-to-let lenders cap loans at around **75% loan-to-value**. So the releasable amount is roughly the gap between your current balance and 75% of today's valuation.",
                    "Valuation is everything. Gather evidence of improvements - receipts, photos, planning consents - and make sure your broker knows the strongest comparable sales. Two lenders can value the same property tens of thousands apart.",
                ],
            },
            {
                "heading": "The costs that change the maths",
                "bullets": [
                    "Early repayment charges on your current deal (often the biggest number - check your redemption statement)",
                    "New arrangement, legal and valuation fees",
                    "Higher rate vs lower rate: work out the break-even point, not just the headline cash",
                    "If the costs eat three years of benefit, maybe you wait.",
                ],
            },
            {
                "heading": "What to do with the money",
                "paragraphs": [
                    "The classic use is the next acquisition - released equity as the deposit for deal number two, with each property working harder. Others use it to fund value-adding works on existing stock.",
                    "One note of caution: releasing equity to fund lifestyle spending turns your portfolio into a piggy bank and shrinks your safety margin. Treat it like the investor capital it is.",
                ],
            },
            {
                "heading": "Stress-test before you sign",
                "paragraphs": [
                    "Rates in {year} are very different from the 2020-21 lows. Before you commit, check that the rent still covers the new mortgage at a stressed rate of 7-8%, and keep a reserve of **3-6 months of mortgage payments** as a portfolio buffer. Leverage is wonderful on the way up and unforgiving on the way down.",
                ],
            },
        ],
        "takeaways": [
            "Refinance when the valuation has grown or your fixed deal is ending - not on autopilot.",
            "Release is typically capped around 75% LTV; evidence your improvements.",
            "Add up ERCs and fees before you celebrate the headline release.",
            "Point released equity at the next deal or value-adding works.",
            "Keep a multi-month payment buffer after the switch.",
        ],
    },
    {
        "slug": "sourcing-deals",
        "topic_short": "deal sourcing",
        "category": "Sourcing",
        "categories": ["Sourcing", "Strategy"],
        "hashtags": ["#PropertyDeals", "#UKProperty", "#PropertyInvestment", "#Sourcing"],
        "titles": [
            "Finding Below-Market Deals: How UK Investors Source Property Before the Crowd Does",
            "Deal Sourcing in {year}: Where the Best Property Deals Actually Come From",
        ],
        "hook": "The best deals rarely make it to page one of Rightmove. Here's where serious investors actually find them",
        "excerpt": "The channels that produce genuine below-market-value property, and how to tell a real deal from a deal-shaped illusion.",
        "intros": [
            "Every successful investor you meet will tell you the same secret: they didn't get rich on rising prices, they got rich on buying well. Sourcing - finding properties before the wider market sees them - is a learnable skill. Here's where to look in {year}.",
            "Great deals are the moat in property investing. Anyone can buy a nice house at full price; the investors who build portfolios quickly are the ones with deal flow. These are the channels that actually work in the UK market.",
        ],
        "sections": [
            {
                "heading": "Why the purchase decides everything",
                "paragraphs": [
                    "You make money three ways in property: income, capital growth, and forced appreciation. Only the third is fully under your control - and it starts with buying below the property's improved value. Everything else (refinancing, yield, your next deal) stands on the purchase.",
                ],
            },
            {
                "heading": "Where real deals come from",
                "bullets": [
                    "**Auctions** - the traditional home of the below-market purchase. Read the legal pack, view the property, set your bid ceiling and stick to it.",
                    "**Direct-to-vendor** - leafleting, local advertising and relationships with sellers who never list publicly.",
                    "**Probate and inheritance** - where speed and sensitivity beat the highest offer.",
                    "**Tired landlords** - portfolio sellers and landlords exiting the market, often found through networking.",
                    "**Long-listed properties** - stale Rightmove listings with motivated sellers behind them.",
                    "**Reputable sourcing agents** - but do your due diligence on their track record and compliance.",
                ],
            },
            {
                "heading": "How to spot a genuine deal",
                "paragraphs": [
                    "Everyone's property is 'priced to sell'. A real below-market-value deal has evidence:",
                ],
                "bullets": [
                    "Comparable sales proving the gap between asking and true market value",
                    "A refurbishment budget from a real contractor quote, not a guess",
                    "A proven exit: refinance route or resale demand, checked before you commit",
                    "Numbers that work at today's interest rates - not 2021's",
                ],
            },
            {
                "heading": "Build the machine, not just the deal",
                "paragraphs": [
                    "Deal flow compounds like interest. Investors who move fast, keep their word, pay fair fees to sourcers and communicate clearly with agents get the *next* deal offered first. Show up to local property events in {region}, stay visible online, and be the buyer people remember.",
                ],
            },
            {
                "heading": "A note on compliance",
                "paragraphs": [
                    "If you ever source deals for others in England, know the rules: anti-money-laundering registration, ICO registration and (where you act as an agent) redress scheme membership are expected. Stay on the right side of them - serious investors always check.",
                ],
            },
        ],
        "takeaways": [
            "Buying well is the only part of the deal fully in your control.",
            "Work several channels: auctions, direct-to-vendor, probate and networking.",
            "Demand evidence for every bargain: comps, quotes and a proven exit.",
            "Your reputation is your deal pipeline - be the buyer people call first.",
        ],
    },
    {
        "slug": "choose-a-property-sourcer",
        "topic_short": "property sourcing",
        "category": "Sourcing",
        "categories": ["Sourcing", "Compliance"],
        "hashtags": ["#PropertySourcing", "#UKProperty", "#PropertyInvestment", "#DueDiligence"],
        "titles": [
            "How to Choose a Property Sourcer in the UK: The Compliance Checklist Investors Should Demand",
            "Property Sourcing Explained: What a Good Sourcer Does (and Must Never Do)",
        ],
        "hook": "A good sourcer can transform your portfolio. A bad one can quietly cost you everything. Here's the exact checklist smart investors use",
        "excerpt": "What UK property sourcers do, what they typically charge, and the compliance checklist - AML, ICO, redress scheme - to demand before working with anyone.",
        "intros": [
            "Property sourcing is one of the fastest-growing corners of UK investing - and one of the least understood. Done by a professional, it's a genuine service that saves investors hundreds of hours. Done by a cowboy, it's how people overpay for 'deals' that were never deals. Here's how to tell the difference in {year}.",
            "Every week, investors hand over thousands of pounds in sourcing fees. Some get genuine below-market-value purchases with clean paperwork. Some get a Rightmove link with the price inflated. The difference between the two is almost always compliance and transparency - and both are easy to check.",
        ],
        "sections": [
            {
                "heading": "What a sourcer actually does",
                "paragraphs": [
                    "A professional sourcer finds, negotiates and packages below-market-value or off-market property for investors: running the numbers, arranging viewings, gathering quotes and due diligence, and handing over a deal that's ready to transact. The investor always makes the final decision and instructs their own solicitor.",
                ],
            },
            {
                "heading": "What sourcing normally costs",
                "bullets": [
                    "Typical UK sourcing fees run **£1,500-£5,000** per deal (sometimes 1-3% on larger purchases), agreed in writing before any work starts.",
                    "Fees must be **disclosed up front** - that's a legal obligation for anyone doing estate agency work.",
                    "Beware anyone making money twice: hidden markups from contractors, lenders or 'refurbishment packages' are the classic red flag.",
                    "A good sourcer is paid by the investor, openly - and can show you their terms before you sign anything.",
                ],
            },
            {
                "heading": "The compliance checklist to demand",
                "paragraphs": [
                    "In England, property sourcing is regulated estate agency work. Before paying anyone a fee, ask for:",
                ],
                "bullets": [
                    "**HMRC anti-money-laundering registration** number (verify it on gov.uk)",
                    "**ICO registration** for data protection",
                    "**Redress scheme membership** - The Property Ombudsman or the Property Redress Scheme",
                    "**Professional indemnity insurance**",
                    "**Written terms of business** with the fee clearly stated",
                    "**ID and source-of-funds procedures** - they should check *you*, too; that's the law working properly",
                    "**Evidence of the deal**: comparable sales, real contractor quotes, a proven exit",
                ],
            },
            {
                "heading": "Why this protects you",
                "paragraphs": [
                    "Compliance isn't bureaucracy - it's your audit trail. If a deal ever goes wrong, a compliant sourcer leaves a paper trail that protects you; a non-compliant one leaves you exposed. Missing any single item on that list is a reason to walk away, however good the 'deal' looks.",
                ],
            },
            {
                "heading": "The standard we publish to",
                "paragraphs": [
                    "At SGJM we believe the sourcing industry's best asset is transparency - so we publish to the checklist above and complete every registration before acting for clients. Education first, fees second. That's the whole brand.",
                ],
            },
        ],
        "takeaways": [
            "Sourcing is regulated estate agency work - compliance is not optional.",
            "Demand the AML number, ICO, redress scheme, PI insurance and written terms.",
            "Fees are typically £1.5k-£5k and must be disclosed before you sign.",
            "Hidden double-dipping (contractor markups, secret commissions) is the biggest red flag.",
            "No paperwork, no payment - however good the deal sounds.",
        ],
    },
    {
        "slug": "uk-vs-dubai-property",
        "topic_short": "UK vs Dubai",
        "category": "Strategy",
        "categories": ["Strategy", "Dubai"],
        "hashtags": ["#DubaiProperty", "#UKProperty", "#PropertyInvestment", "#OffPlan"],
        "titles": [
            "UK vs Dubai Property in {year}: Where Does Each Investor Win?",
            "Dubai or UK Property? An Honest Comparison for {year}",
        ],
        "hook": "UK or Dubai? It's not 'which is better' - it's 'which investor wins where'. Here's the honest comparison",
        "excerpt": "Yields, tax, leverage and risk: a balanced UK vs Dubai property comparison, and the type of investor each market actually suits.",
        "intros": [
            "Half of UK property Twitter says Dubai is the future; the other half says it's a bubble. Both are missing the point. The two markets do different jobs for different investors - and the smart money increasingly holds both. Here's a balanced comparison, as it stands in {year}.",
            "I get asked constantly: 'should I buy in the UK or Dubai?' The honest answer is: they're different tools. One is a leveraged, regulated income machine; the other is a cash-based, tax-efficient growth market. Let's compare them properly.",
        ],
        "sections": [
            {
                "heading": "The UK case",
                "bullets": [
                    "**Leverage** - a 25% deposit controls 100% of the asset; mortgages are the UK's superpower",
                    "**Rule of law** - deep, predictable legal protections for owners and tenants",
                    "**Value-add culture** - HMOs and BRR let you manufacture equity",
                    "**Costs** - SDLT surcharges, income tax on rent and CGT all bite; yields are earned, not given",
                ],
            },
            {
                "heading": "The Dubai case",
                "bullets": [
                    "**No property or rental tax locally** and no annual ground taxes in most communities",
                    "**Gross yields** of roughly 6-8% are common in established rental districts",
                    "**Off-plan capital growth** in strong cycles, with developer payment plans",
                    "**Golden Visa** routes from AED 2m of property ownership",
                    "**Risks** - oversupply cycles, developer delivery risk, and a shorter price history than the UK",
                ],
            },
            {
                "heading": "The tax reality check",
                "paragraphs": [
                    "One caveat that changes everything: **UK residents are taxed on worldwide income**. 'Tax-free Dubai' only becomes personally tax-free if your residency genuinely changes - which is a life decision, not a property decision. Take professional advice before any numbers assume otherwise.",
                ],
            },
            {
                "heading": "Who wins where",
                "bullets": [
                    "**UK suits** income-focused investors who want leverage, regulated protections and value-add strategies",
                    "**Dubai suits** cash buyers with higher risk tolerance seeking diversification and (with advice) tax-efficient structuring",
                    "**Many serious investors hold both** - UK for leveraged income, Dubai for cash growth and currency spread",
                ],
            },
            {
                "heading": "How introductions should work",
                "paragraphs": [
                    "If anyone introduces you to Dubai opportunities, they should disclose their referral fee, work only with RERA-licensed partners, and stick to education rather than advice. Transparency first - always. That's the standard we hold ourselves to at SGJM.",
                ],
            },
        ],
        "takeaways": [
            "UK = leverage + regulated income; Dubai = cash + tax-efficient growth. Different tools.",
            "UK residents pay UK tax on worldwide income - residency, not property, decides that.",
            "Dubai risks are real: oversupply cycles and developer delivery.",
            "Only work with RERA-licensed partners and disclosed referral fees.",
            "The sophisticated answer is often 'both', sized to your risk tolerance.",
        ],
    },
]


def fmt(text, year, region):
    return text.format(year=year, region=region)


def build_markdown(topic, date, region):
    """Assemble a full article in Jekyll-ready Markdown."""
    year = date.year
    title = fmt(random.choice(topic["titles"]), year, region)
    intro = fmt(random.choice(topic["intros"]), year, region)
    cta = fmt(random.choice(CTAS), year, region)

    lines = [
        "---",
        "layout: post",
        'title: "' + title.replace('"', "'") + '"',
        "date: " + date.isoformat(),
        "categories: " + " ".join(topic["categories"]),
        'excerpt: "' + topic["excerpt"].replace('"', "'") + '"',
        "---",
        "",
        intro,
    ]
    for sec in topic["sections"]:
        lines += ["", "## " + sec["heading"]]
        for p in sec.get("paragraphs", []):
            lines += ["", fmt(p, year, region)]
        if sec.get("bullets"):
            lines.append("")
            lines += ["- " + fmt(b, year, region) for b in sec["bullets"]]
    lines += ["", "## Key Takeaways"]
    lines += ["- " + t for t in topic["takeaways"]]
    lines += ["", "---", "", "*" + DISCLAIMER + "*", "", cta]
    return title, "\n".join(lines) + "\n"


def ai_body(title, topic, year, region):
    """Optional AI engine. Returns Markdown body (no front matter) or None."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    try:
        import requests
        outline = "\n".join("- " + s["heading"] for s in topic["sections"])
        prompt = (
            "You write for a UK property investment blog aimed at investors in "
            f"{region}. Write a 700-900 word article titled: {title}.\n"
            f"Cover these sections:\n{outline}\n"
            "Tone: practical, plain English, credible, lightly conversational. "
            "Use realistic but clearly illustrative example figures and state they "
            "are illustrative. End with a '## Key Takeaways' bullet list and a "
            "one-sentence disclaimer that this is not financial advice. "
            "Return Markdown only (no title heading, no front matter)."
        )
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
        body = r.json()["choices"][0]["message"]["content"].strip()
        return body if body else None
    except Exception as e:  # fall back to template engine silently
        print("  ! AI engine unavailable (" + str(e)[:120] + ") - using template engine.")
        return None


def md_to_html_body(md):
    """Minimal Markdown -> HTML for the standalone HTML output option."""
    out, in_ul = [], False
    bold = lambda s: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    ital = lambda s: re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)

    def render(s):
        return ital(bold(s))

    for line in md.splitlines():
        s = line.strip()
        if s.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + render(s[2:]) + "</li>")
            continue
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if s.startswith("### "):
            out.append("<h3>" + render(s[4:]) + "</h3>")
        elif s.startswith("## "):
            out.append("<h2>" + render(s[3:]) + "</h2>")
        elif s == "---":
            out.append("<hr>")
        elif s:
            out.append("<p>" + render(s) + "</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def html_document(title, excerpt, body_html, date):
    return """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{excerpt}">
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #1c2430;
         background: #f7f8fa; margin: 0; }}
  header {{ background: #0f2a43; color: #fff; padding: 48px 20px; }}
  header h1 {{ max-width: 760px; margin: 0 auto; font-size: 2rem; line-height: 1.25; }}
  header p {{ max-width: 760px; margin: 12px auto 0; color: #b8c7d6; }}
  article {{ max-width: 760px; margin: -24px auto 60px; background: #fff;
             padding: 40px 44px; border-radius: 10px; box-shadow: 0 2px 14px rgba(15,42,67,.08);
             line-height: 1.7; font-size: 1.05rem; }}
  h2 {{ color: #0f2a43; margin-top: 2em; border-bottom: 2px solid #e8edf2; padding-bottom: .3em; }}
  li {{ margin: .4em 0; }}
  hr {{ border: none; border-top: 1px solid #e3e8ee; margin: 2.5em 0; }}
  footer {{ text-align: center; color: #7a8694; font-size: .85rem; padding-bottom: 40px; }}
</style>
</head>
<body>
<header><h1>{title}</h1><p>{date}</p></header>
<article>
{body}
</article>
<footer>Published automatically by Property Blog Bot</footer>
</body>
</html>
""".format(title=title, excerpt=excerpt, date=date.strftime("%d %B %Y"), body=body_html)


def main():
    ap = argparse.ArgumentParser(description="Generate UK property investment blog articles.")
    ap.add_argument("--topic", help="Topic slug (see --list); default: random")
    ap.add_argument("--list", action="store_true", help="List available topics and exit")
    ap.add_argument("--region", default=os.environ.get("BLOG_REGION", REGION_DEFAULT),
                    help="Region mentioned in articles (default: %(default)s)")
    ap.add_argument("--out", default="_posts", help="Output directory (default: _posts)")
    ap.add_argument("--format", choices=["md", "html"], default="md",
                    help="md = Jekyll post for GitHub Pages (default), html = standalone page")
    ap.add_argument("--ai", action="store_true", help="Use OpenAI if OPENAI_API_KEY is set")
    ap.add_argument("--date", help="Override publish date YYYY-MM-DD (default: today)")
    ap.add_argument("--seed", type=int, help="Random seed (reproducible output)")
    ap.add_argument("--site-url", default=os.environ.get("SITE_URL", "https://yourusername.github.io"),
                    help="Your GitHub Pages URL, used in output metadata for LinkedIn")
    args = ap.parse_args()

    if args.list:
        print("Available topics:")
        for t in TOPICS:
            print("  %-22s %s" % (t["slug"], t["titles"][0]))
        return

    if args.seed is not None:
        random.seed(args.seed)

    topic = None
    if args.topic:
        topic = next((t for t in TOPICS if t["slug"] == args.topic), None)
        if not topic:
            sys.exit("Unknown topic '%s'. Use --list to see options." % args.topic)
    else:
        topic = random.choice(TOPICS)

    date = _dt.date.fromisoformat(args.date) if args.date else _dt.date.today()
    year = date.year

    title, md = build_markdown(topic, date, args.region)
    if args.ai:
        body = ai_body(title, topic, year, args.region)
        if body:
            md_body_only = body
            print("  * Article written by AI engine.")
        else:
            md_body_only = None
    else:
        md_body_only = None

    os.makedirs(args.out, exist_ok=True)
    if args.format == "html":
        if md_body_only:
            md_for_html = md_body_only
        else:
            md_for_html = md.split("---", 2)[2]  # strip front matter
        fname = os.path.join(args.out, "%s-%s.html" % (date.isoformat(), topic["slug"]))
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html_document(title, topic["excerpt"], md_to_html_body(md_for_html), date))
    else:
        if md_body_only:
            fm = md.split("---", 2)
            md = "---" + fm[1] + "---\n\n" + md_body_only + "\n"
        fname = os.path.join(args.out, "%s-%s.md" % (date.isoformat(), topic["slug"]))
        with open(fname, "w", encoding="utf-8") as f:
            f.write(md)

    meta = {
        "title": title,
        "slug": topic["slug"],
        "date": date.isoformat(),
        "category": topic["category"],
        "excerpt": topic["excerpt"],
        "hook": topic["hook"],
        "takeaways": topic["takeaways"],
        "hashtags": topic["hashtags"],
        "url_path": "/posts/%s.html" % topic["slug"],
        "file": fname,
        "site_url": args.site_url,
    }
    os.makedirs("output", exist_ok=True)
    with open("output/latest.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("Generated article:")
    print("  Title : " + title)
    print("  Topic : " + topic["slug"])
    print("  File  : " + fname)
    print("  Meta  : output/latest.json")
    print("Next: run 'python3 linkedin_poster.py --dry-run' to preview the LinkedIn post.")


if __name__ == "__main__":
    main()
