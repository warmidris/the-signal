#!/usr/bin/env python3
"""Generate artwork for The Signal podcast."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Color palette
BG = (13, 17, 23)          # #0D1117
AMBER = (245, 158, 11)     # #F59E0B - Bitcoin orange/amber
TEXT_PRIMARY = (230, 237, 243)   # #E6EDF3
TEXT_MUTED = (139, 148, 158)     # #8B949E


def draw_signal_arcs(draw, cx, cy, radii, color, width, facing="right"):
    """Draw concentric broadcast arcs."""
    arc_span = 65  # degrees on each side of center
    for i, r in enumerate(radii):
        # Fade with distance
        opacity = max(60, int(255 * (1.0 - i * 0.15)))
        c = color[:3] + (opacity,)
        bbox = [cx - r, cy - r, cx + r, cy + r]
        if facing == "right":
            draw.arc(bbox, -arc_span, arc_span, fill=c, width=width)
        else:
            draw.arc(bbox, 180 - arc_span, 180 + arc_span, fill=c, width=width)


def draw_btc_b(draw, cx, cy, height, color, stroke_width):
    """Draw a clean Bitcoin B — spine, two bumps, two hash bars through the top/bottom."""
    h = height
    sw = stroke_width
    # The B is narrower than tall; keep proportions tight
    half_h = h / 2
    # Spine sits left of center
    spine_x = cx - h * 0.18

    top = cy - half_h
    mid = cy
    bot = cy + half_h

    # --- Right-side bumps (the defining shape of the B) ---
    # Top bump: semicircle from top-line to mid-line
    bump_top_r = half_h * 0.5  # radius = quarter of total height
    bump_top_cx = spine_x + h * 0.08  # bump center x (slightly right of spine)
    bump_top_bbox = [
        bump_top_cx, top,
        bump_top_cx + bump_top_r * 2, mid
    ]
    draw.arc(bump_top_bbox, -90, 90, fill=color, width=sw)

    # Bottom bump: slightly wider semicircle from mid-line to bot-line
    bump_bot_r = half_h * 0.55
    bump_bot_cx = spine_x + h * 0.08
    bump_bot_bbox = [
        bump_bot_cx, mid,
        bump_bot_cx + bump_bot_r * 2, bot
    ]
    draw.arc(bump_bot_bbox, -90, 90, fill=color, width=sw)

    # --- Spine and horizontals ---
    # Left vertical spine — runs from top to bottom
    draw.line([(spine_x, top), (spine_x, bot)], fill=color, width=sw)
    # Top horizontal — connects spine to top of bump
    draw.line([(spine_x, top), (bump_top_cx + bump_top_r, top)], fill=color, width=sw)
    # Middle horizontal — connects spine to widest point
    draw.line([(spine_x, mid), (bump_bot_cx + bump_bot_r, mid)], fill=color, width=sw)
    # Bottom horizontal — connects spine to bottom of bump
    draw.line([(spine_x, bot), (bump_bot_cx + bump_bot_r, bot)], fill=color, width=sw)

    # --- Vertical hash bars (Bitcoin's signature) ---
    # Two short bars that extend above and below the B, spaced evenly
    bar_extend = h * 0.12
    bar1_x = spine_x + h * 0.12
    bar2_x = spine_x + h * 0.26
    draw.line([(bar1_x, top - bar_extend), (bar1_x, bot + bar_extend)],
              fill=color, width=sw)
    draw.line([(bar2_x, top - bar_extend), (bar2_x, bot + bar_extend)],
              fill=color, width=sw)


def generate_cover(size=3000):
    """Generate the main podcast cover art (3000x3000)."""
    img = Image.new('RGBA', (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)

    cx, cy_icon = size // 2, int(size * 0.40)

    # Subtle radial glow — use a composited layer to avoid alpha stacking
    glow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_r = int(size * 0.28)
    # Single soft glow ellipse, then blur-approximate with a few concentric rings
    for i in range(20):
        r = glow_r - i * (glow_r // 20)
        if r <= 0:
            break
        t = i / 20
        a = int(30 * t)  # peak alpha 30 at center — very subtle amber tint
        glow_draw.ellipse(
            [cx - r, cy_icon - r, cx + r, cy_icon + r],
            fill=AMBER[:3] + (a,)
        )
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Outer ring
    outer_r = int(size * 0.22)
    ring_w = max(int(size * 0.004), 3)
    draw.ellipse(
        [cx - outer_r, cy_icon - outer_r, cx + outer_r, cy_icon + outer_r],
        outline=AMBER[:3] + (100,), width=ring_w
    )

    # Bitcoin B in center
    btc_h = int(size * 0.18)
    btc_sw = max(int(size * 0.007), 4)
    draw_btc_b(draw, cx, cy_icon, btc_h, AMBER + (255,), btc_sw)

    # Signal arcs broadcasting outward from the ring
    arc_radii = [outer_r + int(size * (0.04 + 0.04 * i)) for i in range(6)]
    arc_w = max(int(size * 0.005), 3)
    draw_signal_arcs(draw, cx, cy_icon, arc_radii, AMBER + (255,), arc_w, facing="right")
    # Mirror arcs on left
    draw_signal_arcs(draw, cx, cy_icon, arc_radii, AMBER + (255,), arc_w, facing="left")

    # Title: THE SIGNAL
    title_size = int(size * 0.09)
    subtitle_size = int(size * 0.03)
    credit_size = int(size * 0.02)

    title_font = _load_font("Bold", title_size)
    subtitle_font = _load_font("Regular", subtitle_size)
    credit_font = _load_font("Regular", credit_size)

    title_text = "THE SIGNAL"
    title_y = int(size * 0.70)
    _draw_centered_text(draw, cx, title_y, title_text, title_font, TEXT_PRIMARY + (255,), size,
                        shadow=True)

    # Accent line
    line_w = int(size * 0.25)
    line_y = title_y + title_size + int(size * 0.012)
    draw.line(
        [(cx - line_w // 2, line_y), (cx + line_w // 2, line_y)],
        fill=AMBER[:3] + (140,), width=max(int(size * 0.002), 2)
    )

    # Subtitle
    sub_text = "Daily AI-Bitcoin Intelligence"
    sub_y = line_y + int(size * 0.02)
    _draw_centered_text(draw, cx, sub_y, sub_text, subtitle_font, TEXT_MUTED + (255,), size)

    # Credit at bottom
    credit_text = "Produced by Warm Idris  •  Powered by aibtc.news"
    credit_y = int(size * 0.93)
    _draw_centered_text(draw, cx, credit_y, credit_text, credit_font, TEXT_MUTED + (140,), size)

    return img


def generate_favicon(size=512):
    """Generate icon — just the symbol + arcs, no text."""
    img = Image.new('RGBA', (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2

    # Subtle glow via composited layer
    glow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_r = int(size * 0.32)
    for i in range(15):
        r = glow_r - i * (glow_r // 15)
        if r <= 0:
            break
        a = int(25 * (i / 15))
        glow_draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AMBER[:3] + (a,))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Ring
    outer_r = int(size * 0.28)
    ring_w = max(int(size * 0.006), 2)
    draw.ellipse(
        [cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r],
        outline=AMBER[:3] + (120,), width=ring_w
    )

    # Bitcoin B
    btc_h = int(size * 0.26)
    btc_sw = max(int(size * 0.012), 3)
    draw_btc_b(draw, cx, cy, btc_h, AMBER + (255,), btc_sw)

    # Signal arcs
    arc_radii = [outer_r + int(size * (0.05 + 0.05 * i)) for i in range(3)]
    arc_w = max(int(size * 0.008), 2)
    draw_signal_arcs(draw, cx, cy, arc_radii, AMBER + (255,), arc_w, facing="right")
    draw_signal_arcs(draw, cx, cy, arc_radii, AMBER + (255,), arc_w, facing="left")

    return img


def generate_svg_logo():
    """SVG logo for website header."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 80" fill="none">
  <g transform="translate(36, 40)">
    <!-- Outer ring -->
    <circle cx="0" cy="0" r="26" stroke="#F59E0B" stroke-width="1.5" fill="none" opacity="0.5"/>
    <!-- Broadcast arcs right -->
    <path d="M 28 -14 A 32 32 0 0 1 28 14" stroke="#F59E0B" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.8"/>
    <path d="M 32 -20 A 38 38 0 0 1 32 20" stroke="#F59E0B" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.5"/>
    <!-- Broadcast arcs left -->
    <path d="M -28 -14 A 32 32 0 0 0 -28 14" stroke="#F59E0B" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.8"/>
    <path d="M -32 -20 A 38 38 0 0 0 -32 20" stroke="#F59E0B" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.5"/>
    <!-- Bitcoin B simplified -->
    <g stroke="#F59E0B" stroke-width="2.2" fill="none" stroke-linecap="round">
      <!-- Spine -->
      <line x1="-8" y1="-12" x2="-8" y2="12"/>
      <!-- Horizontals -->
      <line x1="-8" y1="-12" x2="4" y2="-12"/>
      <line x1="-8" y1="0" x2="5" y2="0"/>
      <line x1="-8" y1="12" x2="4" y2="12"/>
      <!-- Top bump -->
      <path d="M 4 -12 A 6 6 0 0 1 4 0"/>
      <!-- Bottom bump -->
      <path d="M 5 0 A 6.5 6.5 0 0 1 5 12"/>
      <!-- Hash bars -->
      <line x1="-3" y1="-15" x2="-3" y2="15"/>
      <line x1="2" y1="-15" x2="2" y2="15"/>
    </g>
  </g>
  <!-- Title -->
  <text x="82" y="33" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-weight="700" font-size="30" fill="#E6EDF3" letter-spacing="4">THE SIGNAL</text>
  <line x1="82" y1="44" x2="240" y2="44" stroke="#F59E0B" stroke-width="1.2" opacity="0.5"/>
  <text x="82" y="58" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="12" fill="#8B949E" letter-spacing="1.5">Daily AI-Bitcoin Intelligence</text>
</svg>'''


def _load_font(style, size):
    """Try to load a DejaVu font, fall back to default."""
    paths = {
        "Bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "Regular": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
    }
    for p in paths.get(style, paths["Regular"]):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _draw_centered_text(draw, cx, y, text, font, fill, canvas_w, shadow=False):
    """Draw horizontally centered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (canvas_w - tw) // 2
    if shadow:
        draw.text((x + 3, y + 3), text, fill=(0, 0, 0, 160), font=font)
    draw.text((x, y), text, fill=fill, font=font)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating podcast cover art (3000x3000)...")
    cover = generate_cover(3000)
    cover_path = os.path.join(OUTPUT_DIR, "cover-3000.png")
    cover.save(cover_path, "PNG", optimize=True)
    print(f"  -> {cover_path}")

    cover_1400 = cover.resize((1400, 1400), Image.LANCZOS)
    cover_1400_path = os.path.join(OUTPUT_DIR, "cover-1400.png")
    cover_1400.save(cover_1400_path, "PNG", optimize=True)
    print(f"  -> {cover_1400_path}")

    print("Generating favicon (512x512)...")
    favicon = generate_favicon(512)
    favicon_path = os.path.join(OUTPUT_DIR, "icon-512.png")
    favicon.save(favicon_path, "PNG", optimize=True)
    print(f"  -> {favicon_path}")

    icon_192 = favicon.resize((192, 192), Image.LANCZOS)
    os.path.join(OUTPUT_DIR, "icon-192.png")
    icon_192.save(os.path.join(OUTPUT_DIR, "icon-192.png"), "PNG", optimize=True)
    print(f"  -> icon-192.png")

    icon_32 = favicon.resize((32, 32), Image.LANCZOS)
    icon_32.save(os.path.join(OUTPUT_DIR, "favicon.png"), "PNG", optimize=True)
    print(f"  -> favicon.png")

    print("Generating SVG logo...")
    svg = generate_svg_logo()
    with open(os.path.join(OUTPUT_DIR, "logo.svg"), "w") as f:
        f.write(svg)
    print(f"  -> logo.svg")

    print("\nGenerated artwork:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith(('.png', '.svg')):
            fpath = os.path.join(OUTPUT_DIR, f)
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  {f:20s} {size_kb:>8.1f} KB")
