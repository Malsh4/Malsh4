#!/usr/bin/env python3
"""Generate projects.svg from live GitHub data (works with private repos)."""
import json, os, urllib.request, urllib.error, datetime

USER   = os.environ.get("GH_USER", "Malsh4")
TOKEN  = os.environ.get("GH_TOKEN", "")
REPOS  = [r.strip() for r in os.environ.get("REPOS", "LankaTransit-177,Battlezik").split(",") if r.strip()]

# Optional: friendly title + fallback blurb per repo (used if the repo has no description)
LABELS = {
    "LankaTransit-177": ("LankaTransit-177", "Live bus tracking and in-app ticketing app"),
    "Battlezik":        ("Battlezik",        "Real-time esports tournament platform"),
}

API = "https://api.github.com"
HDRS = {"Accept": "application/vnd.github+json", "User-Agent": "readme-projects"}
if TOKEN:
    HDRS["Authorization"] = f"Bearer {TOKEN}"


def get(url):
    req = urllib.request.Request(url, headers=HDRS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(
                f"ERROR 404 for {url}\n"
                "  -> Either the repo name is wrong (check exact spelling/case in REPOS),\n"
                "     or the token cannot see it. Token present: "
                f"{'yes' if TOKEN else 'NO - secret PROFILE_TOKEN is missing/empty'}")
        if e.code in (401, 403):
            raise SystemExit(
                f"ERROR {e.code} for {url}\n"
                "  -> Token invalid, expired, or missing the 'repo' scope.")
        raise SystemExit(f"ERROR {e.code} for {url}: {e.reason}")


def ago(iso):
    d = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    days = (datetime.datetime.utcnow() - d).days
    if days < 1:  return "today"
    if days == 1: return "yesterday"
    if days < 30: return f"{days}d ago"
    if days < 365: return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def fetch(repo):
    r = get(f"{API}/repos/{USER}/{repo}")
    langs = get(f"{API}/repos/{USER}/{repo}/languages")
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:3]
    title, fallback = LABELS.get(repo, (repo, ""))
    return {
        "repo": repo,
        "title": title,
        "desc": (r.get("description") or fallback or "")[:96],
        "stars": r.get("stargazers_count", 0),
        "updated": ago(r["pushed_at"]),
        "langs": [(n, round(v * 100 / total)) for n, v in top],
        "pct": round(top[0][1] * 100 / total) if top else 0,
    }


# ---------- rendering ----------
CW, CH, C = 574, 196, 194.8
COLORS = ["#A78BFA", "#22D3EE", "#10B981"]


def wrap(text, width=44):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur: lines.append(cur)
    return (lines + ["", "", ""])[:3]


def card(d, ring):
    o = [
        f'<rect width="{CW}" height="{CH}" rx="10" fill="#0F172A" stroke="#1E293B"/>',
        f'<rect width="{CW}" height="26" rx="10" fill="#111C33"/><rect y="16" width="{CW}" height="10" fill="#111C33"/>',
        f'<line x1="0" y1="26" x2="{CW}" y2="26" stroke="#1E293B"/>',
        '<circle cx="16" cy="13" r="3" fill="#22D3EE"/>',
        f'<text x="28" y="17" font-size="11" fill="#94A3B8">{USER}/{d["repo"]}</text>',
        f'<circle cx="{CW-18}" cy="13" r="3.5" fill="#334155"/>',
        '<rect x="18" y="44" width="44" height="44" rx="10" fill="#0A101F" stroke="#1E293B"/>',
        f'<text x="40" y="73" font-size="19" font-weight="700" text-anchor="middle" fill="#A78BFA">{d["title"][0]}</text>',
        f'<text x="74" y="64" font-size="17" font-weight="700" fill="#F8FAFC">{d["title"]}_</text>',
    ]
    for i, line in enumerate(wrap(d["desc"])):
        o.append(f'<text x="74" y="{84+i*16}" font-size="11" fill="#94A3B8">{line}</text>')
    x = 74
    o.append('<g font-size="10">')
    pal = [("#2E1065", "#4C1D95", "#C4B5FD"), ("#083344", "#155E75", "#67E8F9"), ("#022C22", "#065F46", "#6EE7B7")]
    for i, (name, pct) in enumerate(d["langs"]):
        bg, br, fg = pal[i % 3]
        w = int(len(name) * 6.3) + 22
        o.append(f'<rect x="{x}" y="140" width="{w}" height="20" rx="10" fill="{bg}" stroke="{br}"/>')
        o.append(f'<text x="{x+w//2}" y="154" text-anchor="middle" fill="{fg}">{name}</text>')
        x += w + 8
    o.append('</g>')
    o.append(f'<text x="74" y="180" font-size="10.5" fill="#64748B">★ {d["stars"]} &#160;&#160; updated {d["updated"]}</text>')
    o.append('<g font-size="10.5" fill="#94A3B8">')
    for i, (name, pct) in enumerate(d["langs"]):
        y = 64 + i * 20
        o.append(f'<circle cx="352" cy="{y}" r="4" fill="{COLORS[i%3]}"/><text x="364" y="{y+4}">{name} {pct}%</text>')
    o.append('</g>')
    a = C * d["pct"] / 100
    o.append(f'<g transform="translate(512,96)"><circle r="31" fill="none" stroke="#1E293B" stroke-width="8"/>'
             f'<circle r="31" fill="none" stroke="url(#{ring})" stroke-width="8" stroke-linecap="round" '
             f'stroke-dasharray="{a:.1f} {C-a:.1f}" transform="rotate(-90)"/>'
             f'<text y="5" font-size="14" font-weight="700" text-anchor="middle" fill="#F8FAFC">{d["pct"]}%</text></g>')
    return "\n    ".join(o)


def main():
    data = [fetch(r) for r in REPOS]
    cols = 2
    rows = (len(data) + cols - 1) // cols
    height = rows * CH + (rows - 1) * 16
    body = []
    for i, d in enumerate(data):
        x = (i % cols) * 606
        y = (i // cols) * (CH + 16)
        body.append(f'  <g transform="translate({x},{y})">\n    {card(d, "ring1" if i % 2 == 0 else "ring2")}\n  </g>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="{height}" viewBox="0 0 1180 {height}" font-family="'JetBrains Mono','Fira Code','SFMono-Regular',Consolas,monospace">
  <defs>
    <linearGradient id="ring1" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#A78BFA"/><stop offset="100%" stop-color="#22D3EE"/></linearGradient>
    <linearGradient id="ring2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#22D3EE"/><stop offset="100%" stop-color="#10B981"/></linearGradient>
  </defs>
{chr(10).join(body)}
</svg>
'''
    with open("projects.svg", "w") as f:
        f.write(svg)
    print(f"wrote projects.svg with {len(data)} cards")


if __name__ == "__main__":
    main()
