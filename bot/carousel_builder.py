#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carousel slide generator
========================
Turns the latest generated article into a branded social-media carousel:
  * slide PNGs (1080x1350) - for Instagram carousels / Facebook multi-image
  * a multi-page PDF - for LinkedIn document (carousel) posts

Usage:
  python3 carousel_builder.py                          # slides -> output/slides/
  python3 carousel_builder.py --url-prefix https://mysite/assets/slides/
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
NAVY = (15, 42, 67)
GOLD = (217, 180, 91)
WHITE = (247, 248, 250)
MUTED = (176, 193, 209)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BRAND = "PROPERTY INVESTMENT INSIGHTS"


def font(size, bold=True):
    return ImageFont.truetype(FB if bold else FR, size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_center(draw, y, text, fnt, fill, max_w=None):
    if max_w:
        lines = wrap(draw, text, fnt, max_w)
    else:
        lines = [text]
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=fnt)
        draw.text(((W - w) / 2, y + i * int(fnt.size * 1.3)), line, font=fnt, fill=fill)
    return y + len(lines) * int(fnt.size * 1.3)


def base():
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([42, 42, W - 42, H - 42], outline=GOLD, width=3)
    return img, d


def skyline(d):
    pts = []
    hs = [80, 140, 65, 160, 95, 120, 75, 150, 90, 130]
    for i, hh in enumerate(hs):
        x0 = 60 + i * 97
        pts += [(x0, 1275), (x0 + 48, 1275 - hh), (x0 + 97, 1275)]
    d.line(pts, fill=GOLD, width=3)


def slide_cover(title):
    img, d = base()
    skyline(d)
    draw_center(d, 150, BRAND, font(34), GOLD)
    d.line([(W / 2 - 140, 215), (W / 2 + 140, 215)], fill=GOLD, width=2)
    f = 82
    while f > 46:
        lines = wrap(d, title, font(f), 880)
        if len(lines) <= 6:
            break
        f -= 6
    y = 420
    for line in lines:
        draw_center(d, y, line, font(f), WHITE)
        y += int(f * 1.3)
    draw_center(d, 1030, "Swipe for the key lessons  →", font(38, False), MUTED)
    return img


def slide_body(num, total, text):
    img, d = base()
    skyline(d)
    d.text((90, 120), "%02d" % num, font=font(120), fill=GOLD)
    d.text((90, 265), "/ %02d" % total, font=font(34, False), fill=MUTED)
    d.line([(90, 330), (W - 90, 330)], fill=GOLD, width=2)
    f = 56
    while f > 40:
        lines = wrap(d, text, font(f), 880)
        if len(lines) <= 9:
            break
        f -= 4
    y = 430
    for line in lines:
        d.text((90, y), line, font=font(f), fill=WHITE)
        y += int(f * 1.4)
    return img


def slide_cta(site_url, hashtags):
    img, d = base()
    skyline(d)
    draw_center(d, 320, "Want the full", font(72), WHITE)
    draw_center(d, 420, "breakdown?", font(72), WHITE)
    draw_center(d, 580, "Read the article at", font(38, False), MUTED)
    draw_center(d, 650, site_url.replace("https://", ""), font(46), GOLD)
    draw_center(d, 800, "Follow for weekly UK property insights", font(36, False), MUTED)
    draw_center(d, 1030, " ".join(hashtags[:5]), font(28, False), MUTED)
    return img


def main():
    ap = argparse.ArgumentParser(description="Build a branded carousel from the latest article.")
    ap.add_argument("--meta", default="output/latest.json")
    ap.add_argument("--out", default="output/slides")
    ap.add_argument("--url-prefix", default=None,
                    help="Public URL prefix of the slides once committed to your site "
                         "(e.g. https://mysite/assets/slides/) - written to slides.json")
    args = ap.parse_args()

    with open(args.meta, encoding="utf-8") as f:
        meta = json.load(f)

    os.makedirs(args.out, exist_ok=True)
    items = meta["takeaways"][:5]
    total = len(items)

    slides = [slide_cover(meta["title"])]
    slides += [slide_body(i + 1, total, t) for i, t in enumerate(items)]
    slides.append(slide_cta(meta.get("site_url", ""), meta["hashtags"]))

    pngs = []
    for i, im in enumerate(slides):
        p = os.path.join(args.out, "slide-%02d.png" % (i + 1))
        im.save(p, "PNG")
        pngs.append(p)

    pdf_path = os.path.join(args.out, "carousel.pdf")
    slides[0].save(pdf_path, "PDF", save_all=True, append_images=slides[1:], resolution=100)

    info = {
        "pngs": pngs,
        "pdf": pdf_path,
        "caption": meta["hook"] + " \U0001F447",
        "hashtags": meta["hashtags"],
    }
    if args.url_prefix:
        info["urls"] = [args.url_prefix.rstrip("/") + "/" + os.path.basename(p) for p in pngs]
    with open(os.path.join(args.out, "slides.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    print("Carousel built: %d slides" % len(slides))
    print("  PNGs : " + args.out + "/slide-*.png")
    print("  PDF  : " + pdf_path + "  (LinkedIn document post)")


if __name__ == "__main__":
    main()
