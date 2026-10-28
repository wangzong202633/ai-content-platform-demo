# -*- coding: utf-8 -*-
"""Poster compositor — AI paints the background, code typesets the text.

Design doc §5: diffusion models must not render text (Chinese glyphs will
break). We generate/craft a background, then deterministically overlay
title / subtitle / CTA / brand mark at exact channel specs, always obeying
the light brand palette.
"""
import os
import math

from PIL import Image, ImageDraw, ImageFont

FONTS = {
    "regular": "C:/Windows/Fonts/msyh.ttc",
    "bold": "C:/Windows/Fonts/msyhbd.ttc",
}
_FALLBACK = "C:/Windows/Fonts/simsun.ttc"

MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "media")   # demo/backend/media
os.makedirs(MEDIA_DIR, exist_ok=True)

# AI background request sizes per target spec (crop-to-fill afterwards)
BG_SIZES = {
    (900, 383): "1440x720", (1920, 600): "1440x720", (1080, 1920): "720x1440",
    (1080, 1080): "1024x1024", (1200, 628): "1152x864",
}


def _font(kind: str, size: int):
    path = FONTS.get(kind, FONTS["regular"])
    if not os.path.exists(path):
        path = _FALLBACK
    return ImageFont.truetype(path, size)


def _hex_rgb(h: str, default=(47, 127, 168)):
    h = (h or "").lstrip("#")
    if len(h) != 6:
        return default
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def template_background(w: int, h: int, design_hint: dict) -> Image.Image:
    """Deterministic brand background (image-API fallback): light gradient +
    soft accent circles. Always light, always decent."""
    bg = _hex_rgb(design_hint.get("bg"), (234, 243, 248))
    accent = _hex_rgb(design_hint.get("accent"), (47, 127, 168))
    img = Image.new("RGB", (w, h), bg)
    dr = ImageDraw.Draw(img, "RGBA")
    # vertical light gradient
    top = tuple(min(255, c + 10) for c in bg)
    bottom = tuple(max(0, c - 14) for c in bg)
    for y in range(h):
        t = y / max(1, h - 1)
        dr.line([(0, y), (w, y)],
                fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    # soft accent circles (large, low alpha, right side)
    for (cx, cy, r, a) in ((int(w * 0.88), int(h * 0.2), int(h * 0.42), 26),
                           (int(w * 0.97), int(h * 0.75), int(h * 0.30), 20),
                           (int(w * 0.72), int(h * 0.9), int(h * 0.22), 14)):
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (a,))
    # thin diagonal line detail
    dr.line([(0, h), (w, int(h * 0.55))], fill=accent + (30,), width=max(2, h // 300))
    return img


def _cover_crop(bg: Image.Image, w: int, h: int) -> Image.Image:
    """Crop-to-fill target spec while preserving aspect."""
    sw, sh = bg.size
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale) + 1, int(sh * scale) + 1
    bg = bg.resize((nw, nh))
    x, y = (nw - w) // 2, (nh - h) // 2
    return bg.crop((x, y, x + w, y + h))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int):
    lines, line = [], ""
    for ch in text:
        if draw.textlength(line + ch, font=font) > max_w and line:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def compose_poster(bg: Image.Image, spec: dict, title: str, subtitle: str,
                   cta: str, design_hint: dict, platform_label: str,
                   out_name: str) -> str:
    """bg (any size) + programmatic text layer -> exact-spec poster PNG in /media."""
    w, h = spec["w"], spec["h"]
    img = _cover_crop(bg.convert("RGB"), w, h)
    dr = ImageDraw.Draw(img, "RGBA")

    accent = _hex_rgb(design_hint.get("accent"), (47, 127, 168))
    ink = _hex_rgb(design_hint.get("text"), (31, 51, 64))
    vertical = h > w
    pad = int(min(w, h) * 0.075)

    # readability panel behind text (light glass)
    panel_h = int(h * (0.42 if not vertical else 0.30))
    panel = Image.new("RGBA", (w, panel_h), (255, 255, 255, 0))
    pdr = ImageDraw.Draw(panel)
    pdr.rectangle([0, 0, w, panel_h], fill=(255, 255, 255, 150))
    img.paste(Image.alpha_composite(img.crop((0, h - panel_h, w, h)).convert("RGBA"),
                                    panel).convert("RGB"), (0, h - panel_h))
    dr = ImageDraw.Draw(img, "RGBA")

    # accent bar
    dr.rectangle([0, h - panel_h, int(w * 0.28) or 8, h - panel_h + max(4, h // 150)],
                 fill=accent + (235,))

    # platform label (top-left of panel)
    label_font = _font("bold", max(16, int(h * 0.026)))
    dr.text((pad, h - panel_h + int(panel_h * 0.16)), platform_label,
            font=label_font, fill=accent + (255,))

    # title (wrapped, bold)
    title_font = _font("bold", max(28, int(min(w, h) * (0.095 if not vertical else 0.062))))
    max_w = w - pad * 2
    lines = _wrap(dr, title, title_font, max_w)[:2]
    ty = h - panel_h + int(panel_h * 0.36)
    for ln in lines:
        dr.text((pad, ty), ln, font=title_font, fill=ink + (255,))
        ty += int(title_font.size * 1.25)

    # subtitle (smaller, single clip)
    if subtitle:
        sub_font = _font("regular", max(15, int(min(w, h) * 0.033)))
        sub = _wrap(dr, subtitle, sub_font, max_w)[0]
        dr.text((pad, min(ty + 6, h - int(panel_h * 0.22))), sub,
                font=sub_font, fill=ink + (200,))

    # CTA pill (bottom-right)
    if cta:
        cta_font = _font("bold", max(15, int(min(w, h) * 0.036)))
        tw = dr.textlength(cta, font=cta_font)
        bh = int(cta_font.size * 1.9)
        bx, by = w - pad - int(tw + cta_font.size * 1.6), h - pad - bh
        dr.rounded_rectangle([bx, by, bx + int(tw + cta_font.size * 1.6), by + bh],
                             radius=bh // 2, fill=accent + (255,))
        dr.text((bx + int(cta_font.size * 0.8), by + int(bh * 0.22)), cta,
                font=cta_font, fill=(255, 255, 255, 255))

    path = os.path.join(MEDIA_DIR, out_name)
    img.save(path, "PNG")
    return path
