#!/usr/bin/env python3
"""Build the encrypted static reader site for GitHub Pages into deploy/static/.

The page images are AES-256-GCM encrypted (see encrypt.mjs); the browser asks for
the username/password and decrypts client-side. The plain JPEGs are never published.

Usage (credentials are NOT stored in this repo):
    SITE_USER=... SITE_PASS=... python3 deploy/build.py
"""
import html
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent
WORKSPACE = DEPLOY.parent
PAGES_SRC = WORKSPACE / "library" / "pages"
STATIC = DEPLOY / "static"

SITE_TITLE = "Renal Unit Guidelines"
SITE_SUB = "Private clinical reference"

# group → [(slug, title, blurb, sections)]
# sections: [(capture page number, label)] — rendered as a jump-to list.
MANIFEST = [
    ("Acute & emergencies", [
        ("aki", "Acute Kidney Injury",
         "Risk assessment on admission, recognition and staging, initial management bundle.", []),
        ("hyperkalaemia", "Hyperkalaemia",
         "ECG changes, severity grading and the inpatient treatment algorithm.", []),
        ("contrast-aki", "Contrast-associated AKI",
         "Risk factors and prevention around iodinated contrast imaging — never delay emergency scans.", []),
        ("hus", "Atypical HUS",
         "One-page pathway: MAHA → TTP protocol → ADAMTS13 → aHUS checklist → eculizumab.", []),
    ]),
    ("CKD & complications", [
        ("ckd", "Management of CKD",
         "Stages 1–5 (not on dialysis): BP targets, ACEi/ARB, SGLT2 inhibitors, finerenone, monitoring, ultrasound criteria.",
         [(4, "Management flowchart"), (13, "SGLT2 inhibitors & finerenone")]),
        ("hyperphosphataemia", "Hyperphosphataemia in CKD",
         "Diet and dialysis adequacy first, then calcium-based vs non-calcium phosphate binders.", []),
    ]),
    ("Glomerular disease", [
        ("iga-nephropathy", "IgA Nephropathy",
         "Supportive care (BP 120/80, ACEi/ARB, SGLT2i), disease-modifying therapy and the GN MDT.", []),
        ("anca-vasculitis", "ANCA-associated Vasculitis",
         "Induction and maintenance immunosuppression; counselling on cyclophosphamide, rituximab and steroid risks.", []),
    ]),
    ("Haemodialysis", [
        ("hd-anticoagulation", "HD Circuit Anticoagulation",
         "Enoxaparin as standard, UFH, heparin-free dialysis and alternative LMWHs.",
         [(9, "Heparin-free HD & alternatives")]),
        ("vascular-access", "Vascular Access",
         "Acute thrombosis pathway and management of tunnelled lines with poor flow (urokinase).",
         [(1, "Acute thrombosis"), (6, "Tunnelled CVC with poor flow")]),
    ]),
    ("Transplantation", [
        ("transplant", "Kidney Transplant Protocols",
         "Six protocols: ABO-incompatible, alemtuzumab induction, bone health, CMV, imlifidase, sirolimus switch.",
         [(1, "ABO-incompatible transplantation"),
          (10, "Alemtuzumab induction"),
          (20, "Post-transplant bone health"),
          (30, "CMV management"),
          (42, "Imlifidase (Idefirix) desensitisation"),
          (55, "Sirolimus switch")]),
    ]),
    ("Prescribing", [
        ("anticoagulants", "Anticoagulation for VTE",
         "PE/DVT: contraindications, DOAC vs warfarin vs dalteparin, duration, antiplatelets, HIT, cancer VTE.",
         [(8, "Duration & antiplatelets")]),
        ("analgesics", "Analgesia in Advanced Kidney Disease",
         "The renally-adapted three-step ladder: paracetamol → tramadol → oxycodone/patches.", []),
    ]),
]

CSS = """/* Light-only by design — no dark-mode block, matching the workspace's lessons. */
:root {
  color-scheme: light;
  --bg: #fffdf6;
  --ink: #22242a;
  --muted: #6d7178;
  --faint: #9aa0a8;
  --accent: #0f62b7;
  --accent-ink: #0a4d92;
  --card: #faf7ee;
  --border: #e5e0d2;
  --serif: "Charter", "Iowan Old Style", "Palatino Linotype", Georgia, "Times New Roman", serif;
  --s-1: .4rem; --s-2: .75rem; --s-3: 1.1rem; --s-4: 1.6rem; --s-5: 2.4rem; --s-6: 3.4rem;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--serif); font-size: 1.05rem; line-height: 1.55;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  position: sticky; top: 0; z-index: 5;
  background: rgba(255, 253, 246, .95); border-bottom: 1px solid var(--border);
  padding: var(--s-2) var(--s-3);
  display: flex; gap: var(--s-3); align-items: baseline; flex-wrap: wrap;
}
.topbar .home { font-weight: bold; white-space: nowrap; }
.topbar .here { color: var(--muted); min-width: 0; }
.topbar .lock-link { margin-left: auto; font-size: .85rem; color: var(--faint); }
main { max-width: 50rem; margin: 0 auto; padding: var(--s-4) var(--s-3) var(--s-6); }
header.doc h1 { font-size: 1.7rem; line-height: 1.2; margin: 0 0 var(--s-1); }
header.doc .meta { color: var(--muted); margin: 0 0 var(--s-3); }
.kicker {
  color: var(--faint); text-transform: uppercase; letter-spacing: .08em;
  font-size: .8rem; margin: var(--s-5) 0 var(--s-2);
}
.toc { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: var(--s-2) var(--s-3); margin: 0 0 var(--s-4); }
.toc p { margin: 0 0 var(--s-1); color: var(--muted); font-size: .9rem; }
.toc ul { margin: 0; padding-left: 1.2rem; }
.cards { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s-2); }
.cards > * { min-width: 0; }
.cards a {
  display: block; background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: var(--s-2) var(--s-3); color: inherit;
}
.cards a:hover { border-color: var(--accent); text-decoration: none; }
.cards .t { color: var(--accent-ink); font-weight: bold; }
.cards .d { margin: .15rem 0 0; font-size: .93rem; color: var(--muted); }
.cards .n { font-size: .8rem; color: var(--faint); }
figure.page { margin: 0 0 var(--s-4); }
figure.page figcaption {
  color: var(--faint); font-size: .8rem; text-transform: uppercase;
  letter-spacing: .08em; margin-bottom: var(--s-1);
}
figure.page img {
  display: block; width: 100%; height: auto; background: #fff;
  border: 1px solid var(--border); border-radius: 4px;
}
figure.page img.pending { min-height: 55vh; }
button.load-all {
  font: inherit; font-size: .9rem; color: var(--accent-ink);
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: var(--s-1) var(--s-2); margin: 0 0 var(--s-3); cursor: pointer;
}
nav.pager {
  display: flex; justify-content: space-between; gap: var(--s-3);
  border-top: 1px solid var(--border); padding-top: var(--s-3); margin-top: var(--s-5);
}
nav.pager span { min-width: 0; }
footer.site { color: var(--faint); font-size: .85rem; margin-top: var(--s-5); }
/* ---- gate ---- */
body.locked main, body.locked nav.pager { display: none; }
#gate { display: none; }
body.locked #gate {
  display: flex; position: fixed; inset: 0; z-index: 10;
  background: var(--bg); align-items: center; justify-content: center;
  padding: var(--s-3);
}
#gate form {
  width: 100%; max-width: 22rem; background: var(--card);
  border: 1px solid var(--border); border-radius: 12px; padding: var(--s-4);
}
#gate h2 { margin: 0 0 var(--s-1); font-size: 1.2rem; }
#gate p.hint { margin: 0 0 var(--s-3); color: var(--muted); font-size: .9rem; }
#gate input {
  display: block; width: 100%; font: inherit; color: inherit;
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: var(--s-1) var(--s-2); margin: 0 0 var(--s-2);
}
#gate button {
  font: inherit; width: 100%; background: var(--accent); color: #fff;
  border: none; border-radius: 8px; padding: var(--s-1) var(--s-2); cursor: pointer;
}
#gate #gate-err { color: #a4262c; font-size: .9rem; margin: var(--s-2) 0 0; }
@media print {
  .topbar, nav.pager, button.load-all { display: none; }
  figure.page img { border: none; }
}
"""

GATE = """<div id="gate">
<form id="gate-form" autocomplete="on">
<h2>Sign in</h2>
<p class="hint">This is a private reference site. Enter the username and password you were given.</p>
<input name="u" placeholder="Username" autocomplete="username" required>
<input name="p" type="password" placeholder="Password" autocomplete="current-password" required>
<button type="submit">Open</button>
<p id="gate-err" hidden>Wrong username or password.</p>
<noscript><p>This site needs JavaScript to decrypt its content.</p></noscript>
</form>
</div>"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def page_files(slug: str):
    d = PAGES_SRC / slug
    return sorted(p.name for p in d.glob("page-*.jpg"))


def shell(title: str, body: str, root: str, here: str = "") -> str:
    crumb = f'<span class="here">{esc(here)}</span>' if here else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{root}/assets/site.css">
<link rel="icon" href="data:,">
</head>
<body class="locked">
<div class="topbar"><a class="home" href="{root}/">{esc(SITE_TITLE)}</a>{crumb}<a class="lock-link" href="#" hidden>Lock</a></div>
{GATE}
<main>
{body}
</main>
<script src="{root}/assets/app.js" data-root="{root}" defer></script>
</body>
</html>
"""


def build():
    user = os.environ.get("SITE_USER")
    password = os.environ.get("SITE_PASS")
    if not user or not password:
        sys.exit("set SITE_USER and SITE_PASS env vars (credentials are not stored in the repo)")

    if STATIC.exists():
        shutil.rmtree(STATIC)
    (STATIC / "g").mkdir(parents=True)
    (STATIC / "assets").mkdir()
    (STATIC / "assets" / "site.css").write_text(CSS)
    shutil.copy(DEPLOY / "app.js.template", STATIC / "assets" / "app.js")
    (STATIC / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (STATIC / ".nojekyll").write_text("")

    # Encrypt all page images with a key derived from user:pass.
    subprocess.run(
        ["node", str(DEPLOY / "encrypt.mjs"), str(PAGES_SRC),
         str(STATIC / "pages-enc"), str(STATIC / "assets" / "manifest.json")],
        env={**os.environ, "SITE_PASSPHRASE": f"{user}:{password}"},
        check=True,
    )

    flat = [(slug, title) for _, items in MANIFEST for slug, title, _, _ in items]

    # Index page.
    groups_html = []
    for group, items in MANIFEST:
        cards = []
        for slug, title, blurb, _ in items:
            n = len(page_files(slug))
            n_label = "1 page" if n == 1 else f"{n} pages"
            cards.append(
                f'<li><a href="g/{slug}.html"><span class="t">{esc(title)}</span>'
                f' <span class="n">· {n_label}</span>'
                f'<p class="d">{esc(blurb)}</p></a></li>'
            )
        groups_html.append(
            f'<h2 class="kicker">{esc(group)}</h2>\n<ul class="cards">\n'
            + "\n".join(cards) + "\n</ul>"
        )
    index_body = (
        f'<header class="doc"><h1>{esc(SITE_TITLE)}</h1>'
        f'<p class="meta">{esc(SITE_SUB)}</p></header>\n'
        + "\n".join(groups_html)
        + '\n<footer class="site">Photographed reference copies of internal guidelines. '
        'Not for redistribution.</footer>'
    )
    (STATIC / "index.html").write_text(shell(SITE_TITLE, index_body, root="."))

    # Viewer pages.
    for group, items in MANIFEST:
        for slug, title, blurb, sections in items:
            files = page_files(slug)
            if not files:
                sys.exit(f"no page images for {slug}")
            figures = []
            for i, name in enumerate(files, start=1):
                bin_name = name[:-len(".jpg")] + ".bin"
                figures.append(
                    f'<figure class="page" id="p-{i:02d}">'
                    f'<figcaption>Page {i} of {len(files)}</figcaption>'
                    f'<img class="pending" data-enc="../pages-enc/{slug}/{bin_name}"'
                    f' alt="{esc(title)}, page {i}"></figure>'
                )
            toc = ""
            if sections:
                links = "".join(
                    f'<li><a href="#p-{p:02d}">{esc(label)}</a> '
                    f'<span class="n">· from page {p}</span></li>'
                    for p, label in sections
                )
                toc = f'<div class="toc"><p>In this document</p><ul>{links}</ul></div>\n'

            k = [s for s, _ in flat].index(slug)
            prev_a = next_a = "<span></span>"
            if k > 0:
                s, t = flat[k - 1]
                prev_a = f'<span><a href="{s}.html">← {esc(t)}</a></span>'
            if k < len(flat) - 1:
                s, t = flat[k + 1]
                next_a = f'<span><a href="{s}.html">{esc(t)} →</a></span>'

            n_label = "1 page" if len(files) == 1 else f"{len(files)} pages"
            body = (
                f'<header class="doc"><h1>{esc(title)}</h1>'
                f'<p class="meta">{esc(group)} · {n_label} · {esc(blurb)}</p></header>\n'
                f"{toc}"
                '<button class="load-all" hidden>Load all pages (for printing)</button>\n'
                + "\n".join(figures)
                + f'\n<nav class="pager">{prev_a}{next_a}</nav>'
            )
            (STATIC / "g" / f"{slug}.html").write_text(shell(title, body, root="..", here=title))

    n_pages = sum(len(page_files(s)) for s, _ in flat)
    print(f"built {len(flat)} guideline pages, {n_pages} encrypted page images")


if __name__ == "__main__":
    build()
