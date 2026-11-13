#!/usr/bin/env python3
"""Build dark_mode.svg and light_mode.svg for the GitHub profile README.

    python tools/ascii_portrait.py avatar.png --rows 46 --tone value --eq 0 --gamma 1.25 --edges 0.2 --out .
    python tools/build_cards.py                    # reads ascii.txt, writes the two SVGs
    python tools/build_cards.py --born YYYY-MM-DD  # also refreshes the Uptime (age) line

The birth date is only used to work out the age on the machine running the
script; only "N years, M months" ends up in the SVG, never the date itself.

Edit the PROFILE block below to change the text on the right-hand side.
"""
import argparse
import datetime
import html
import os

# ----------------------------------------------------------------------------
# Content (everything here comes from the resume / GitHub profile)
# ----------------------------------------------------------------------------
HANDLE = "shiven@kumar"
UPTIME_FALLBACK = "22 years, 4 months"   # used when --born is not passed

PROFILE = [
    ("kv", "Uptime", "{uptime}"),
    ("kv", "Host", "Freelance Full Stack Developer (Remote)"),
    ("kv", "Kernel", "B.E. Computer Science, SIT Tumakuru"),
    ("kv", "Batch", "Class of 2028 | CGPA 8.7"),
    ("kv", "Role", "Full Stack & Backend Developer"),
    ("blank",),
    ("kv", "Languages.Programming", "Python, C++, C, JS, TS"),
    ("kv", "Languages.Computer", "SQL (MySQL, PostgreSQL)"),
    ("kv", "Backend", "FastAPI, Node.js, Express, Socket.IO"),
    ("kv", "Frontend", "React, Next.js, React Native / Expo"),
    ("kv", "Databases", "MongoDB, PostgreSQL, MySQL, Redis"),
    ("kv", "Cloud.DevOps", "Docker, AWS (ECS Fargate, S3), Git"),
    ("section", "Projects"),
    ("kv", "ACSBIO", "NEET mock-test platform (client work)"),
    ("kv", "mini_vercel", "GitHub URL -> live app on AWS Fargate"),
    ("kv", "Telvara", "Traffic ML, 46.4% RMSE gain, 1,329 sites"),
    ("kv", "Imagify", "AI image platform, JWT + Razorpay credits"),
    ("kv", "gossipmesh", "Gossip protocol on scalable systems"),
    ("section", "Highlights"),
    ("kv", "Winner", "Rob the Job, Thinkathon 2025"),
    ("kv", "Rank 16", "IIIT Hyderabad All India Online Hackathon"),
    ("kv", "Top 5", "Build for Bengaluru Hackathon"),
    ("kv", "Hosted", "Full-day AI hackathon, 40+ participants"),
    ("kv", "DSA", "200+ problems solved"),
    ("section", "Contact"),
    ("kv", "Email", "manscientificks@gmail.com"),
    ("kv", "LinkedIn", "shiven-kumar-1549b327a"),
    ("kv", "GitHub", "shiven-devs"),
    ("section", "GitHub Stats"),
    ("kv2", ("Repos", "53"), ("Followers", "5")),
    ("kv2", ("Contributions", "236"), ("Following", "13")),
]
STATS_NOTE = "Stats are a snapshot from 13 Nov 2026."  # kept in <desc>, not drawn

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
ASCII_FS, ASCII_CW, ASCII_LH = 12, 7.2, 14        # left sketch
PANEL_FS, PANEL_CW, PANEL_LH = 15, 9.0, 20        # right-hand text
PANEL_CHARS = 58                                  # characters per line on the right
PAD_X, PAD_Y, GAP = 26, 24, 28

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", ascii="#c9d1d9", key="#ffa657", val="#a5d6ff",
                 dots="#6e7681", sec="#e6edf3", head="#ff7b72"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", ascii="#24292f", key="#953800", val="#0a3069",
                  dots="#8c959f", sec="#1f2328", head="#cf222e"),
}


def age_text(born):
    today = datetime.date.today()
    months = (today.year - born.year) * 12 + (today.month - born.month) - (1 if today.day < born.day else 0)
    y, m = divmod(months, 12)
    return f"{y} year{'s' if y != 1 else ''}, {m} month{'s' if m != 1 else ''}"


def esc(s):
    return html.escape(s, quote=False)


def seg(cls, text):
    return (cls, text)


def line_kv(key, value, width):
    n = width - len(key) - len(value) - 5
    if n < 3:
        raise SystemExit(f"Line too long for the card ({width} chars): {key}: {value}")
    return [seg("d", ". "), seg("k", key + ":"), seg("d", " " + "." * n + " "), seg("v", value)]


def half_kv(key, value, width):
    n = width - len(key) - len(value) - 5
    if n < 3:
        raise SystemExit(f"Stat line too long: {key}: {value}")
    return [seg("d", ". "), seg("k", key + ":"), seg("d", " " + "." * n + " "), seg("v", value)]


def build_lines(uptime):
    lines = [[seg("h", HANDLE), seg("d", " " + "-" * (PANEL_CHARS - len(HANDLE) - 1))]]
    for item in PROFILE:
        kind = item[0]
        if kind == "blank":
            lines.append([])
        elif kind == "section":
            title = item[1]
            lines.append([seg("d", "- "), seg("s", title), seg("d", " " + "-" * (PANEL_CHARS - len(title) - 3))])
        elif kind == "kv":
            lines.append(line_kv(item[1], item[2].format(uptime=uptime), PANEL_CHARS))
        elif kind == "kv2":
            left_w = (PANEL_CHARS - 3) // 2
            right_w = PANEL_CHARS - 3 - left_w
            (k1, v1), (k2, v2) = item[1], item[2]
            lines.append(half_kv(k1, v1, left_w) + [seg("d", " | ")] + half_kv(k2, v2, right_w))
    return lines


def build_svg(theme, ascii_lines, panel_lines):
    t = THEMES[theme]
    art_w = max(len(l) for l in ascii_lines) * ASCII_CW
    art_h = len(ascii_lines) * ASCII_LH
    panel_w = PANEL_CHARS * PANEL_CW
    panel_h = len(panel_lines) * PANEL_LH
    content_h = max(art_h, panel_h)
    width = round(PAD_X * 2 + art_w + GAP + panel_w)
    height = round(PAD_Y * 2 + content_h)
    art_x = PAD_X
    art_y = PAD_Y + (content_h - art_h) / 2
    panel_x = PAD_X + art_w + GAP
    panel_y = PAD_Y + (content_h - panel_h) / 2

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" viewBox="0 0 {width} {height}" '
               f'font-family="ConsolasFallback,Consolas,monospace" role="img" aria-labelledby="t d">')
    out.append("<title id=\"t\">Shiven Kumar (shiven-devs) - GitHub profile card</title>")
    out.append("<desc id=\"d\">Shaded ASCII portrait next to a neofetch-style summary: Computer Science undergraduate at SIT Tumakuru "
               "(class of 2028), freelance full stack developer, Python / C++ / JavaScript / TypeScript, FastAPI, Node.js, "
               f"React, Next.js, MongoDB, PostgreSQL, Docker and AWS. {STATS_NOTE}</desc>")
    out.append("<style>")
    out.append('@font-face { font-family: ConsolasFallback; src: local(Consolas), local("Andale Mono WT"), local("Andale Mono"), '
               'local("Lucida Console"), local("Lucida Sans Typewriter"), local("DejaVu Sans Mono"), local("Bitstream Vera Sans Mono"), '
               'local("Liberation Mono"), local("Nimbus Mono L"), local(Monaco), local("Courier New"), local(Courier); }')
    out.append(f".a {{ fill: {t['ascii']}; font-size: {ASCII_FS}px; }}")
    out.append(f".p {{ font-size: {PANEL_FS}px; }}")
    out.append(f".k {{ fill: {t['key']}; }} .v {{ fill: {t['val']}; }} .d {{ fill: {t['dots']}; }} "
               f".s {{ fill: {t['sec']}; font-weight: bold; }} .h {{ fill: {t['head']}; font-weight: bold; }}")
    out.append("text, tspan { white-space: pre; }")
    out.append("</style>")
    out.append(f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>')

    # left: ASCII portrait
    out.append('<g class="a" aria-hidden="true">')
    for i, line in enumerate(ascii_lines):
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        lead = len(line) - len(stripped)
        x = art_x + lead * ASCII_CW
        y = art_y + ASCII_FS + i * ASCII_LH
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" textLength="{len(stripped) * ASCII_CW:.1f}" lengthAdjust="spacing" '
                   f'xml:space="preserve">{esc(stripped)}</text>')
    out.append("</g>")

    # right: neofetch-style text
    out.append('<g class="p">')
    for i, segs in enumerate(panel_lines):
        if not segs:
            continue
        n = sum(len(s[1]) for s in segs)
        y = panel_y + PANEL_FS + i * PANEL_LH
        spans = "".join(f'<tspan class="{c}">{esc(txt)}</tspan>' for c, txt in segs)
        out.append(f'<text x="{panel_x:.1f}" y="{y:.1f}" textLength="{n * PANEL_CW:.1f}" lengthAdjust="spacing" '
                   f'xml:space="preserve">{spans}</text>')
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ascii", default="ascii.txt", help="ASCII sketch from ascii_portrait.py")
    ap.add_argument("--out", default=".", help="folder for dark_mode.svg / light_mode.svg")
    ap.add_argument("--born", help="YYYY-MM-DD, only used to compute the Uptime (age) line")
    a = ap.parse_args()

    uptime = age_text(datetime.date.fromisoformat(a.born)) if a.born else UPTIME_FALLBACK
    ascii_lines = open(a.ascii, encoding="utf-8").read().rstrip("\n").split("\n")
    panel = build_lines(uptime)
    os.makedirs(a.out, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(a.out, f"{theme}_mode.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(theme, ascii_lines, panel))
        print("wrote", path)
    print("uptime line:", uptime)


if __name__ == "__main__":
    main()
