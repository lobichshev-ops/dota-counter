# -*- coding: utf-8 -*-
"""Проверки перед публикацией: иконки героев на CDN + синтаксис JS в index.html."""
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
NODE = os.environ.get("NODE_BIN", "node")


def load():
    raw = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def check_image(slug):
    url = CDN + slug + ".png"
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return slug, r.status
    except Exception as exc:  # noqa: BLE001
        return slug, str(exc)[:60]


def main():
    d = load()
    slugs = [h["slug"] for h in d["heroes"]]
    print(f"иконок к проверке: {len(slugs)}")

    bad = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for slug, res in pool.map(check_image, slugs):
            if res != 200:
                bad.append((slug, res))
    if bad:
        print("ПРОБЛЕМНЫЕ ИКОНКИ:")
        for slug, res in bad:
            print(f"  {slug}: {res}")
    else:
        print("все иконки отдаются (200)")

    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
    print(f"инлайн-скриптов в index.html: {len(blocks)}")
    tmp = os.path.join(HERE, "_syntax_check.js")
    for i, b in enumerate(blocks):
        open(tmp, "w", encoding="utf-8").write(b)
        p = subprocess.run([NODE, "--check", tmp], capture_output=True, text=True)
        print(f"  скрипт #{i + 1}: " + ("OK" if p.returncode == 0 else "ОШИБКА\n" + p.stderr[:800]))
    if os.path.exists(tmp):
        os.remove(tmp)

    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
