"""Draw the profile's WakaTime card from the last 7 days of coding time.

Writes assets/waka-dark.svg and assets/waka-light.svg in the same visual
language as the other cards. Needs WAKATIME_API_KEY, or --sample to draw
made-up numbers for previewing the layout.
"""

import base64
import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

SANS = "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "dark": dict(panel="#161b22", line="#30363d", text="#e6edf3", muted="#9198a1", other="#484f58"),
    "light": dict(panel="#f6f8fa", line="#d0d7de", text="#1f2328", muted="#59636e", other="#afb8c1"),
}

# GitHub Linguist colours, so a language looks the same here as in the repos.
COLORS = {
    "C#": "#178600", "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Go": "#00ADD8", "C": "#555555", "C++": "#f34b7d", "HTML": "#e34c26", "CSS": "#663399",
    "SCSS": "#c6538c", "PHP": "#4F5D95", "Rust": "#dea584", "Java": "#b07219", "Kotlin": "#A97BFF",
    "Lua": "#000080", "Ruby": "#701516", "Bash": "#89e051", "Shell": "#89e051",
    "PowerShell": "#012456", "SQL": "#e38c00", "Markdown": "#083fa1", "Vue.js": "#41b883",
    "TSX": "#3178c6", "JSX": "#f1e05a", "Dockerfile": "#384d54", "YAML": "#cb171e", "JSON": "#40d47e",
    "Nix": "#7e7eff", "Razor": "#512be4", "XML": "#0060ac", "TOML": "#9c4221",
}

MAX_LANGS = 5
W, H = 900, 212
PAD = 36

SAMPLE = [
    ("C#", 29520), ("Python", 16200), ("TypeScript", 7500), ("JavaScript", 3600),
    ("Bash", 1500), ("Markdown", 900), ("YAML", 400),
]


def fetch(key):
    req = urllib.request.Request(
        "https://wakatime.com/api/v1/users/current/stats/last_7_days",
        headers={"Authorization": "Basic " + base64.b64encode(key.encode()).decode()},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["data"]
    return [(l["name"], l["total_seconds"]) for l in data.get("languages", []) if l["total_seconds"] > 0]


def hm(seconds):
    h, m = divmod(round(seconds / 60), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def group(langs):
    # WakaTime reports its own "Other"; fold it into ours so it shows once, last.
    other = sum(s for n, s in langs if n == "Other")
    langs = sorted((l for l in langs if l[0] != "Other"), key=lambda l: -l[1])
    top, rest = langs[:MAX_LANGS], other + sum(s for _, s in langs[MAX_LANGS:])
    if rest:
        top.append(("Other", rest))
    return top


def card(t, langs):
    total = sum(s for _, s in langs)
    head = (
        f'<text x="{PAD}" y="58" font-family="{SANS}" font-size="22" font-weight="700" fill="{t["text"]}">Last 7 days</text>'
        f'<text x="{W - PAD}" y="58" text-anchor="end" font-family="{SANS}" font-size="20" fill="{t["muted"]}">'
        f'<tspan font-weight="700" fill="{t["text"]}">{hm(total)}</tspan> of coding</text>'
    )
    if not total:
        body = f'<text x="{PAD}" y="128" font-family="{SANS}" font-size="18" fill="{t["muted"]}">Nothing tracked this week.</text>'
        return svg(t, head + body, 168)

    # One bar split by language, small gaps between segments like GitHub's own language bar.
    bar_w, gap, x, segs = W - 2 * PAD, 3, PAD, ""
    usable = bar_w - gap * (len(langs) - 1)
    for i, (name, s) in enumerate(langs):
        w = max(usable * s / total, 2)
        if i == len(langs) - 1:
            w = PAD + bar_w - x
        segs += f'<rect x="{x:.1f}" y="86" width="{w:.1f}" height="12" fill="{color(t, name)}"/>'
        x += w + gap
    bar = (
        f'<defs><clipPath id="bar"><rect x="{PAD}" y="86" width="{bar_w}" height="12" rx="6"/></clipPath></defs>'
        f'<g clip-path="url(#bar)">{segs}</g>'
    )

    cols, col_w, legend = 3, (W - 2 * PAD) / 3, ""
    for i, (name, s) in enumerate(langs):
        cx, cy = PAD + (i % cols) * col_w, 140 + (i // cols) * 34
        legend += (
            f'<circle cx="{cx + 6:.1f}" cy="{cy - 6}" r="6" fill="{color(t, name)}"/>'
            f'<text x="{cx + 22:.1f}" y="{cy}" font-family="{SANS}" font-size="18" fill="{t["text"]}">{escape(name)}'
            f'<tspan dx="8" fill="{t["muted"]}">{hm(s)}</tspan></text>'
        )
    rows = (len(langs) + cols - 1) // cols
    return svg(t, head + bar + legend, 140 + (rows - 1) * 34 + 38)


def color(t, name):
    c = t["other"] if name == "Other" else COLORS.get(name, t["other"])
    return lift(c) if t is THEMES["dark"] else c


def lift(hex_color):
    # Some Linguist colours (Lua, Markdown) are near-black navy and vanish on the
    # dark panel; mix those towards white until they read.
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    if lum >= 0.25:
        return hex_color
    k = 0.45
    return "#{:02x}{:02x}{:02x}".format(*(round(v + (255 - v) * k) for v in (r, g, b)))


def svg(t, inner, h):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">\n'
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>\n'
        f"  {inner}\n</svg>\n"
    )


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("assets")
    langs = SAMPLE if "--sample" in sys.argv else fetch(os.environ["WAKATIME_API_KEY"])
    langs = group(langs)
    out.mkdir(parents=True, exist_ok=True)
    for mode, t in THEMES.items():
        (out / f"waka-{mode}.svg").write_text(card(t, langs))


if __name__ == "__main__":
    main()
