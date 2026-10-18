"""Draw assets/top-tech.svg: my most-used technologies as an animated terminal card.

Counts come from my CV knowledge base (65 projects, 2022-2026): the number of projects
that use each technology. Icons are from simple-icons 13.21.0 (CC0), stored in scripts/icons.

Usage: python scripts/top-tech.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "scripts" / "icons"
OUT = ROOT / "assets" / "top-tech.svg"

TOTAL_PROJECTS = 65
LIGHT = "e6edf3"  # stands in for black brand colours, which vanish on the dark card

# (name, simple-icons slug, brand hex, projects using it)
TECH = [
    ("TypeScript", "typescript", "3178C6", 28),
    ("PostgreSQL", "postgresql", "4169E1", 27),
    ("Python", "python", "3776AB", 26),
    ("Railway", "railway", LIGHT, 25),
    ("Next.js", "nextdotjs", LIGHT, 21),
    ("Tailwind CSS", "tailwindcss", "06B6D4", 21),
    ("React", "react", "61DAFB", 20),
    ("Docker", "docker", "2496ED", 18),
    ("Vercel", "vercel", LIGHT, 15),
    ("PostHog", "posthog", LIGHT, 13),
    ("FastAPI", "fastapi", "009688", 10),
    ("Redis", "redis", "FF4438", 9),
]

W, H = 560, 635
ROW_Y0, ROW_H = 112, 40
BAR_X, BAR_W, BAR_H = 168, 316, 10
GROW = 0.9  # seconds each bar takes to grow
STAGGER = 0.1


def icon_path(slug):
    svg = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    (d,) = re.findall(r'<path d="([^"]+)"', svg)
    return d


def row(i, name, slug, hex_, count, top):
    cy = ROW_Y0 + i * ROW_H
    width = round(BAR_W * count / top, 1)
    delay = 0.4 + i * STAGGER
    dur = round(delay + GROW, 2)
    t = round(delay / dur, 3)
    color = f"#{hex_}"
    return f"""  <g>
    <svg x="20" y="{cy - 9}" width="18" height="18" viewBox="0 0 24 24"><path fill="{color}" d="{icon_path(slug)}"/></svg>
    <text x="48" y="{cy + 4.5}" fill="#c9d1d9" font-size="13">{name}</text>
    <rect x="{BAR_X}" y="{cy - BAR_H / 2}" width="{BAR_W}" height="{BAR_H}" rx="5" fill="#21262d"/>
    <rect x="{BAR_X}" y="{cy - BAR_H / 2}" width="{width}" height="{BAR_H}" rx="5" fill="{color}">
      <animate attributeName="width" values="0;0;{width}" keyTimes="0;{t};1" dur="{dur}s" calcMode="spline" keySplines="0 0 1 1;0.2 0.8 0.2 1" fill="freeze"/>
    </rect>
    <text x="540" y="{cy + 4.5}" fill="#c9d1d9" font-size="13" text-anchor="end">{count}<animate attributeName="opacity" values="0;0;1" keyTimes="0;{round((delay + GROW * 0.6) / dur, 3)};1" dur="{dur}s" fill="freeze"/></text>
  </g>"""


def main():
    top = max(c for *_, c in TECH)
    label = ", ".join(f"{n} {c}" for n, _, _, c in TECH)
    rows = "\n".join(row(i, *t, top) for i, t in enumerate(TECH))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" role="img" aria-label="Top technologies by number of projects: {label}">
  <title>Top technologies by number of projects</title>
  <defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#111722"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>
  <rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="#30363d"/>
  <line x1="0" y1="30" x2="{W}" y2="30" stroke="#30363d"/>
  <circle cx="20" cy="15" r="5" fill="#ff5f56"/><circle cx="36" cy="15" r="5" fill="#ffbd2e"/><circle cx="52" cy="15" r="5" fill="#27c93f"/>
  <text x="{W / 2}" y="19" fill="#7d8590" font-size="12" text-anchor="middle">IvanFazlic@github: ~$ ./top-tech.sh</text>
  <text x="20" y="64" fill="#c9d1d9" font-size="15" font-weight="600">Top technologies</text>
  <text x="540" y="64" fill="#7d8590" font-size="12" text-anchor="end">projects</text>
  <text x="20" y="84" fill="#7d8590" font-size="11.5">How many of my {TOTAL_PROJECTS} projects (2022–2026) use each one</text>
{rows}
  <line x1="0" y1="592" x2="{W}" y2="592" stroke="#30363d"/>
  <text x="20" y="611" fill="#7d8590" font-size="13">IvanFazlic@github:~$ ls projects | wc -l <tspan fill="#c9d1d9">{TOTAL_PROJECTS}</tspan></text>
  <rect x="369" y="599" width="8" height="14" fill="#c9d1d9"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>
</svg>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(svg.encode()) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
