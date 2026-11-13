#!/usr/bin/env python3
"""Turn a portrait into a shaded ASCII sketch for a GitHub profile card.

Usage:
    python ascii_portrait.py avatar.png                 # writes ascii.txt
    python ascii_portrait.py avatar.png --rows 46 --tone value --eq 0 --gamma 1.25 --edges 0.2   # settings used for the card
    python ascii_portrait.py photo.jpg --rows 38 --bg auto
    python ascii_portrait.py photo.jpg --bg none        # keep the whole frame (no background removal)

--bg auto  : flood-fills from the image border using the border's median colour,
             so it works best on plain / flat backgrounds.
--bg none  : no cut-out; the entire frame is shaded.
Like the reference profile cards, dark parts of the picture become the heavy
characters (@ % #), so the same sketch works on dark and light themes.
Use --invert for the opposite (lit parts heavy).
"""
import argparse
from collections import deque

import numpy as np
from PIL import Image, ImageFilter, ImageOps

RAMP = " .,:;-~=+*xX%#@"  # light ink -> heavy ink
EQ = 0.75             # 0 = keep original tones, 1 = fully equalised
CELL_ASPECT = 0.514   # character width / line height (7.2px / 14px) used by the SVG builder


def cut_out_background(rgb, tol=38):
    """Flood fill from the border; returns boolean mask (True = subject)."""
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(np.int32)
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb.astype(np.int32) - bg) ** 2).sum(axis=2))
    cand = dist < tol
    seen = np.zeros((h, w), bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    return ~seen


def render(img, rows, bg_mode, fade, edge_weight, gamma, invert=False, eq=EQ, tone_mode="luma"):
    rgb = np.array(img.convert("RGB"))
    mask = cut_out_background(rgb) if bg_mode == "auto" else np.ones(rgb.shape[:2], bool)

    ys, xs = np.where(mask)
    pad = 4
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgb.shape[1])
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgb.shape[0])
    rgb, mask = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    h, w = mask.shape
    cols = int(round(rows * (w / h) / CELL_ASPECT))

    if tone_mode == "value":
        # brightest colour channel: keeps saturated mid-tones (e.g. red skin in a poster-style avatar) apart from black
        gray = Image.fromarray(rgb.max(axis=2).astype(np.uint8), "L")
    else:
        gray = Image.fromarray(rgb).convert("L")
    # local contrast so the shaded face reads clearly at low resolution
    gray = ImageOps.autocontrast(gray, cutoff=2)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=110, threshold=2))  # crisper nose / mouth / jaw lines
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.8))

    def cells(im, resample=Image.BOX):
        return np.asarray(im.resize((cols, rows), resample), dtype=np.float32) / 255.0

    tone = cells(gray)
    edge = cells(edges)
    cover = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((cols, rows), Image.BOX), dtype=np.float32) / 255.0
    inside = cover > 0.5

    edge = np.clip(edge / (edge[inside].max() + 1e-6) * 2.2, 0, 1)
    # spread the tones over the whole character ramp (rank-equalise inside the subject, blended with the original)
    vals = tone[inside]
    rank = np.zeros_like(tone)
    rank[inside] = (np.argsort(np.argsort(vals)) + 0.5) / len(vals)
    bright = np.clip((eq * rank + (1 - eq) * tone) ** gamma, 0, 1)   # 1 = lit, 0 = shadow
    # taper the bottom rows so the bust fades out instead of ending on a hard curve
    taper = np.ones(rows, np.float32)
    n = max(int(rows * fade), 1)
    taper[-n:] = np.linspace(1.0, 0.0, n, endpoint=False) ** 1.2
    taper = taper[:, None]

    def to_text(ink):
        ink = np.where(inside, ink * taper, 0.0)
        idx = np.clip((ink * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
        # subject cells are never blank so the silhouette survives
        idx = np.where(inside & (taper > 0.15) & (idx == 0), 1, idx)
        return ["".join(RAMP[i] for i in row).rstrip() for row in idx]

    shade = 1 - bright                                   # dark parts of the photo -> heavy characters
    if invert:
        shade = bright                                   # lit parts -> heavy (positive look on dark themes)
    ink = np.clip(0.04 + 0.96 * shade + edge_weight * edge, 0, 1)
    return to_text(ink), cols


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--rows", type=int, default=36, help="height of the sketch in text rows")
    ap.add_argument("--bg", choices=["auto", "none"], default="auto")
    ap.add_argument("--fade", type=float, default=0.14, help="fraction of bottom rows that fade out")
    ap.add_argument("--edges", type=float, default=0.35, help="how strongly outlines are inked")
    ap.add_argument("--gamma", type=float, default=0.85, help="below 1 lifts mid-tones (skin), above 1 deepens them")
    ap.add_argument("--eq", type=float, default=EQ, help="0 = keep original tones, 1 = fully equalised")
    ap.add_argument("--tone", choices=["luma", "value"], default="luma", help="value = brightest RGB channel (good for flat, saturated illustrations)")
    ap.add_argument("--invert", action="store_true", help="heavy characters on the lit parts instead of the dark parts")
    ap.add_argument("--out", default=".", help="folder for ascii.txt")
    a = ap.parse_args()

    lines, cols = render(Image.open(a.image), a.rows, a.bg, a.fade, a.edges, a.gamma, a.invert, a.eq, a.tone)
    import os
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "ascii.txt"), "w").write("\n".join(lines) + "\n")
    print(f"wrote {cols} cols x {len(lines)} rows -> {a.out}/ascii.txt")


if __name__ == "__main__":
    main()
