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

    img_dir = os.path.join(HERE, "img")
    bad = []
    total = 0
    for slug in slugs:
        p = os.path.join(img_dir, slug + ".webp")
        if not os.path.exists(p):
            bad.append((slug, "файла нет"))
        elif os.path.getsize(p) < 500:
            bad.append((slug, "подозрительно маленький: %d б" % os.path.getsize(p)))
        else:
            total += os.path.getsize(p)
    if bad:
        print("ПРОБЛЕМНЫЕ ИКОНКИ:")
        for slug, res in bad:
            print(f"  {slug}: {res}")
    else:
        print(f"все на месте, {total / 1024 / 1024:.2f} МБ" +
              (f" ({total / len(slugs) / 1024:.1f} КБ на иконку)" if slugs else ""))

    # лишние файлы в папке
    extra = sorted(set(f[:-5] for f in os.listdir(img_dir) if f.endswith(".webp"))
                   - set(slugs)) if os.path.isdir(img_dir) else []
    if extra:
        print("лишние файлы:", ", ".join(extra[:10]))

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
