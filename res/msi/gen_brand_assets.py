#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate branding BMP assets for WiX MSI installer.

Outputs (relative to this script's directory):
  Package/Resources/WixUIBannerBmp.bmp  - 493x58  - top banner
  Package/Resources/WixUIDialogBmp.bmp  - 493x312 - welcome/exit left panel
"""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
LOGO_PATH = SCRIPT_DIR / "../../flutter/assets/logo.png"
OUT_DIR = SCRIPT_DIR / "Package/Resources"

# Brand colors matching app UI (#24252B dark background, blue accent)
COLOR_DARK_BG = (36, 37, 43)
COLOR_ACCENT = (0, 120, 212)
COLOR_WHITE = (255, 255, 255)
COLOR_LIGHT_GRAY = (240, 240, 240)
COLOR_SEPARATOR = (200, 200, 200)


def load_logo():
    if not LOGO_PATH.exists():
        print(f"Warning: logo not found at {LOGO_PATH}")
        return None
    return Image.open(LOGO_PATH).convert("RGBA")


def paste_logo_on(img, logo, target_h, x, y_center):
    """Paste logo scaled to target_h, centered at y_center, starting at x."""
    if logo is None:
        return
    ratio = target_h / logo.height
    target_w = int(logo.width * ratio)
    scaled = logo.resize((target_w, target_h), Image.LANCZOS)
    y = y_center - target_h // 2
    # Composite onto background
    bg_patch = Image.new("RGBA", (target_w, target_h), img.getpixel((x, y_center)) + (255,))
    if scaled.mode == "RGBA":
        bg_patch.paste(scaled, mask=scaled.split()[3])
    else:
        bg_patch.paste(scaled)
    img.paste(bg_patch.convert("RGB"), (x, y))
    return target_w


def generate_banner():
    """WixUIBannerBmp: 493x58 — top banner strip shown on most dialogs."""
    w, h = 493, 58
    img = Image.new("RGB", (w, h), COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    logo = load_logo()
    logo_w = paste_logo_on(img, logo, target_h=38, x=10, y_center=h // 2) or 0

    # Vertical separator after logo
    if logo_w:
        sep_x = 10 + logo_w + 12
        draw.line([(sep_x, 10), (sep_x, h - 10)], fill=COLOR_SEPARATOR, width=1)
        # Right-side tagline
        tag_x = sep_x + 14
        tag_text = "Удалённый доступ"
        draw.text((tag_x, h // 2 - 8), tag_text, fill=(80, 80, 80))

    # Bottom accent line
    draw.rectangle([0, h - 2, w, h - 1], fill=COLOR_ACCENT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "WixUIBannerBmp.bmp"
    img.save(str(out), "BMP")
    print(f"Generated {out.name} ({w}x{h})")


def generate_dialog():
    """WixUIDialogBmp: 493x312 — left panel on Welcome / Exit dialogs."""
    w, h = 493, 312
    img = Image.new("RGB", (w, h), COLOR_DARK_BG)
    draw = ImageDraw.Draw(img)

    # Subtle gradient: slightly lighter at top
    for y in range(h):
        factor = 1.0 - (y / h) * 0.2
        c = tuple(min(255, int(ch * factor)) for ch in COLOR_DARK_BG)
        draw.line([(0, y), (w, y)], fill=c)

    logo = load_logo()
    logo_w = paste_logo_on(img, logo, target_h=48, x=(w - 200) // 2, y_center=h // 3) or 0

    # "TechSupport" label below logo
    label_y = h // 3 + 34
    label = "out-techsupport.ru"
    draw.text(((w - len(label) * 6) // 2, label_y), label, fill=(160, 160, 170))

    # Bottom accent bar
    draw.rectangle([0, h - 6, w, h], fill=COLOR_ACCENT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "WixUIDialogBmp.bmp"
    img.save(str(out), "BMP")
    print(f"Generated {out.name} ({w}x{h})")


if __name__ == "__main__":
    generate_banner()
    generate_dialog()
    print("Brand assets generated.")
