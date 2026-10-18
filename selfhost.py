#!/usr/bin/env python3
"""Self-host fonts and chart libraries so the site stops calling Google Fonts, jsDelivr and cdnjs.

Run it once on your computer, in the folder that contains index.html:
    python3 selfhost.py
It downloads the files into ./assets, rewrites index.html (a copy is saved as index.html.bak)
and sets the privacy note on the About page accordingly. Needs only Python 3 and internet access.
"""
import os, re, sys, shutil, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_CSS = "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Noto+Color+Emoji&display=swap"
HC_MAPS = "https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.8/highmaps.js"
HC_EUROPE = "https://cdn.jsdelivr.net/npm/@highcharts/map-collection@1.1.3/custom/europe.js"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f: f.write(data)

def covers_flags(unicode_range):
    """True if a unicode-range covers the regional indicators U+1F1E6..1F1FF used by flag emoji."""
    for part in unicode_range.replace("U+", "").split(","):
        part = part.strip()
        if not part: continue
        lo, _, hi = part.partition("-")
        try:
            a = int(lo.replace("?", "0"), 16); b = int(hi, 16) if hi else int(lo.replace("?", "F"), 16)
        except ValueError: continue
        if a <= 0x1F1E6 <= b or a <= 0x1F1FF <= b or (0x1F1E6 <= a and b <= 0x1F1FF): return True
    return False

def build_fonts_css(css, fetch=get, out=os.path.join(HERE, "assets", "fonts")):
    blocks = re.findall(r"/\*[^*]*\*/\s*@font-face\s*\{[^}]*\}|@font-face\s*\{[^}]*\}", css)
    kept = []
    for b in blocks:
        fam = re.search(r"font-family:\s*'([^']+)'", b).group(1)
        rng = re.search(r"unicode-range:\s*([^;]+);", b)
        if fam == "Noto Color Emoji" and not (rng and covers_flags(rng.group(1))): continue
        url = re.search(r"url\((https://[^)]+)\)", b).group(1)
        name = re.sub(r"[^A-Za-z0-9._-]", "_", fam + "-" + os.path.basename(url.split("?")[0]))
        if not name.endswith(".woff2"): name += ".woff2"
        save(os.path.join(out, name), fetch(url))
        kept.append(b.replace(url, name))
    save(os.path.join(out, "fonts.css"), ("\n".join(kept) + "\n").encode("utf-8"))
    return len(kept)

def rewrite_html(html):
    html = re.sub(r'<link rel="preconnect"[^>]*fonts\.g[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com[^>]*>', '<link rel="stylesheet" href="assets/fonts/fonts.css">', html)
    html = html.replace(HC_MAPS, "assets/js/highmaps.js").replace(HC_EUROPE, "assets/js/europe.js")
    html = html.replace("https://unpkg.com/@highcharts/map-collection@1.1.3/custom/europe.js", "assets/js/europe.js")
    html = html.replace("const EXT_ASSETS = true;", "const EXT_ASSETS = false;")
    return html

def main():
    idx = os.path.join(HERE, "index.html")
    html = open(idx, encoding="utf-8").read()
    n = build_fonts_css(get(FONTS_CSS).decode("utf-8"))
    save(os.path.join(HERE, "assets", "js", "highmaps.js"), get(HC_MAPS))
    save(os.path.join(HERE, "assets", "js", "europe.js"), get(HC_EUROPE))
    new = rewrite_html(html)
    left = re.findall(r"https://(?:fonts\.g\w+|cdnjs|cdn\.jsdelivr|unpkg)[^\"')\s]*", new)
    shutil.copyfile(idx, idx + ".bak")
    open(idx, "w", encoding="utf-8").write(new)
    print("Font files:", n, "| external references left:", left or "none")

if __name__ == "__main__":
    main()
