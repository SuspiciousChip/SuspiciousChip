"""Generates header, stats card, skill radar and language radar as SVGs in assets/."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from theme import *          # noqa: E402,F401
import ghapi                 # noqa: E402

ROOT = Path(__file__).parent.parent


def wrap(w, h, body, title, bg=True):
    box = (f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="10" '
           f'fill="{BG}" stroke="{BORDER}"/>') if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">{box}'
            f'<g font-family="{FONT}">{body}</g></svg>')


def header_svg(name, tagline):
    body = (f'<text x="400" y="52" text-anchor="middle" font-size="40" '
            f'font-weight="700" fill="{ACCENT}">{esc(name)}</text>'
            f'<text x="400" y="80" text-anchor="middle" font-size="14" '
            f'fill="{MUTED}">{esc(tagline)}</text>')
    return wrap(800, 96, body, name, bg=False)


def stats_svg(items):
    w, h = 560, 190
    body = (f'<text x="24" y="36" font-size="15" font-weight="700" '
            f'fill="{TEXT}">{esc(ghapi.USER)} — stats</text>')
    for i, (val, label) in enumerate(items):
        cx, cy = 100 + (i % 3) * 180, 92 + (i // 3) * 66
        body += (f'<text x="{cx}" y="{cy}" text-anchor="middle" font-size="26" '
                 f'font-weight="700" fill="{ACCENT}">{esc(val)}</text>'
                 f'<text x="{cx}" y="{cy+20}" text-anchor="middle" font-size="12" '
                 f'fill="{MUTED}">{esc(label)}</text>')
    return wrap(w, h, body, "stats")


def radar_svg(title, axes):
    """axes: list of (label, value 0..1). Falls back to bars under 3 axes."""
    w = h = 380
    cx = cy = w / 2
    R = 110
    body = (f'<text x="{cx}" y="30" text-anchor="middle" font-size="14" '
            f'font-weight="700" fill="{TEXT}">{esc(title)}</text>')
    n = len(axes)
    if n < 3:
        for i, (label, v) in enumerate(axes):
            y = 110 + i * 60
            body += (f'<text x="40" y="{y}" font-size="12" fill="{TEXT}">{esc(label)}</text>'
                     f'<rect x="40" y="{y+8}" width="300" height="8" rx="4" fill="{RAMP[0]}"/>'
                     f'<rect x="40" y="{y+8}" width="{300*v:.0f}" height="8" rx="4" fill="{ACCENT}"/>')
        return wrap(w, h, body, title)

    def pt(i, r):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join("%.1f,%.1f" % pt(i, R * ring) for i in range(n))
        body += f'<polygon points="{pts}" fill="none" stroke="{BORDER}"/>'
    for i, (label, v) in enumerate(axes):
        x, y = pt(i, R)
        body += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{BORDER}"/>'
        lx, ly = pt(i, R + 22)
        cosv = math.cos(-math.pi / 2 + 2 * math.pi * i / n)
        anchor = "middle" if abs(cosv) < 0.3 else ("start" if cosv > 0 else "end")
        body += (f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="{anchor}" '
                 f'font-size="11" fill="{TEXT}">{esc(label)}</text>')
    pts = [pt(i, R * max(v, 0.04)) for i, (_, v) in enumerate(axes)]
    poly = " ".join("%.1f,%.1f" % p for p in pts)
    body += (f'<polygon points="{poly}" fill="{ACCENT}" fill-opacity=".25" '
             f'stroke="{ACCENT}" stroke-width="2"/>')
    for x, y in pts:
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ACCENT}"/>'
    return wrap(w, h, body, title)


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)

    user = ghapi.rest(f"/users/{ghapi.USER}")
    own = [r for r in ghapi.repos() if not r["fork"]]
    total, weeks = ghapi.calendar()
    cur, _, _ = ghapi.streaks(weeks)

    stats = [
        (user["public_repos"], "Public repos"),
        (user["followers"], "Followers"),
        (sum(r["stargazers_count"] for r in own), "Total stars"),
        (sum(r["forks_count"] for r in own), "Total forks"),
        (total, "Contributions"),
        (f"{cur}d", "Current streak"),
    ]
    (out / "header.svg").write_text(header_svg(cfg["name"], cfg.get("tagline", "")))
    (out / "stats.svg").write_text(stats_svg(stats))

    skills = [(k, min(max(v, 0), 10) / 10) for k, v in cfg["skills"].items()]
    (out / "skill-radar.svg").write_text(radar_svg("Skill Radar", skills))

    langs = {}
    for r in own:
        for k, v in ghapi.rest(r["languages_url"]).items():
            langs[k] = langs.get(k, 0) + v
    top = sorted(langs.items(), key=lambda kv: -kv[1])[: cfg.get("languages_top", 6)]
    if top:
        biggest = top[0][1]
        axes = [(f"{k} ({v})", v / biggest) for k, v in top]
        (out / "language-radar.svg").write_text(radar_svg("Language Radar", axes))
    print("wrote", sorted(p.name for p in out.glob("*.svg")))


if __name__ == "__main__":
    main()
