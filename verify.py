# -*- coding: utf-8 -*-
"""Проверки перед публикацией: иконки, синтаксис JS, корректность порядка CM."""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = os.environ.get("NODE_BIN", "node")


def load():
    raw = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def check_icons(d):
    slugs = [h["slug"] for h in d["heroes"]]
    img_dir = os.path.join(HERE, "img")
    bad, total = [], 0
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
        print(f"иконки: {len(slugs)} шт, все на месте, "
              f"{total / 1024 / 1024:.2f} МБ")
    return not bad


def check_js():
    ok = True
    files = ["app.js"]
    for name in files:
        p = os.path.join(HERE, name)
        r = subprocess.run([NODE, "--check", p], capture_output=True, text=True)
        print(f"{name}: " + ("OK" if r.returncode == 0 else "ОШИБКА\n" + r.stderr[:800]))
        ok = ok and r.returncode == 0

    tmp = os.path.join(HERE, "_syntax_check.js")
    for page in ("index.html", "cm.html", "patch.html"):
        p = os.path.join(HERE, page)
        if not os.path.exists(p):
            print(f"{page}: файла нет")
            ok = False
            continue
        html = open(p, encoding="utf-8").read()
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
        for i, b in enumerate(blocks):
            open(tmp, "w", encoding="utf-8").write(b)
            r = subprocess.run([NODE, "--check", tmp], capture_output=True, text=True)
            print(f"{page} (скрипт #{i + 1}): " +
                  ("OK" if r.returncode == 0 else "ОШИБКА\n" + r.stderr[:800]))
            ok = ok and r.returncode == 0
    if os.path.exists(tmp):
        os.remove(tmp)
    return ok


def check_cm_order():
    """24 шага: по 7 банов и по 5 пиков каждой команде, порядок как в 7.41f."""
    html = open(os.path.join(HERE, "cm.html"), encoding="utf-8").read()
    m = re.search(r"const CM_ORDER = \[(.*?)\n  \];", html, re.S)
    if not m:
        print("CM_ORDER: не найден в cm.html")
        return False
    pairs = re.findall(r'\["(first|second)","(ban|pick)"\]', m.group(1))
    seq = [(a, b) for a, b in pairs]

    expected = ([("first", "ban"), ("first", "ban"), ("second", "ban"), ("second", "ban"),
                 ("first", "ban"), ("second", "ban"), ("second", "ban"),
                 ("first", "pick"), ("second", "pick"),
                 ("first", "ban"), ("first", "ban"), ("second", "ban"),
                 ("second", "pick"), ("first", "pick"), ("first", "pick"), ("second", "pick"),
                 ("second", "pick"), ("first", "pick"),
                 ("first", "ban"), ("second", "ban"), ("first", "ban"), ("second", "ban"),
                 ("first", "pick"), ("second", "pick")])

    problems = []
    if seq != expected:
        problems.append("последовательность не совпадает с эталоном 7.41f")
    bans = [s for s in seq if s[1] == "ban"]
    picks = [s for s in seq if s[1] == "pick"]
    if len(seq) != 24:
        problems.append(f"шагов {len(seq)}, ожидалось 24")
    if len(bans) != 14 or len(picks) != 10:
        problems.append(f"банов {len(bans)}, пиков {len(picks)} (нужно 14 и 10)")
    for team in ("first", "second"):
        tb = sum(1 for s in bans if s[0] == team)
        tp = sum(1 for s in picks if s[0] == team)
        if tb != 7 or tp != 5:
            problems.append(f"{team}: банов {tb}, пиков {tp} (нужно 7 и 5)")

    if problems:
        print("CM_ORDER: ПРОБЛЕМЫ — " + "; ".join(problems))
        return False
    print("CM_ORDER: 24 шага, 14 банов, 10 пиков, по 7 и 5 каждой команде — OK")
    return True


def main():
    d = load()
    ok = check_icons(d)
    ok = check_js() and ok
    ok = check_cm_order() and ok
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
