#!/usr/bin/env python3
"""Render the app icon: રામ over કબીર, gold rings on maroon.

Drawn at 4x and downsampled, so the ring strokes and the Gujarati matras stay
smooth at the 192px launcher size. Pillow is built with raqm here, so the text
is shaped by HarfBuzz rather than laid out glyph-by-glyph."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
FONT = "/System/Library/Fonts/Supplemental/GujaratiMT.ttc"
PAPER, MAROON, GOLD, SAFFRON = "#f6efe3", "#8c2f1b", "#c9a86a", "#c96f2a"

def icon(size):
    S, k = size * 4, size * 4 / 512      # supersample, then reduce
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=112 * k, fill=MAROON)
    for r, w in ((176, 10), (156, 3)):
        d.ellipse([S/2 - r*k, S/2 - r*k, S/2 + r*k, S/2 + r*k],
                  outline=GOLD, width=max(1, round(w * k)))
    for text, px, baseline in (("રામ", 126, 248), ("કબીર", 94, 366)):
        f = ImageFont.truetype(FONT, round(px * k))
        d.text((S/2, baseline * k), text, font=f, fill=PAPER,
               anchor="ms", language="gu")
    d.line([S/2 - 58*k, 286*k, S/2 + 58*k, 286*k], fill=SAFFRON,
           width=max(1, round(3 * k)))
    return img.resize((size, size), Image.LANCZOS)

if __name__ == "__main__":
    out = BASE / "app" / "icons"
    for s in (192, 512):
        p = out / f"icon-{s}.png"
        icon(s).save(p)
        print("wrote", p.relative_to(BASE), p.stat().st_size, "bytes")
