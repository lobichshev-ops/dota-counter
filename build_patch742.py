# -*- coding: utf-8 -*-
"""Собирает patch742.js: все герои патча 7.42 с полным списком изменений.

Источники:
  _patch742_ru.json — официальный datafeed Valve (частично переведён на русский),
  _ability_ids.json — id способностей,
  data.js           — имена героев.
Английские строки (Valve не успел локализовать) переводятся через Google и кешируются
в _tr_cache.json, чтобы повторный запуск не дёргал сеть.
"""
import json, re, html, os, ssl, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "_patch742_ru.json")
A = os.path.join(HERE, "_ability_ids.json")
CACHE = os.path.join(HERE, "_tr_cache.json")

patch = json.load(open(P, encoding="utf-8"))
ab_ids = json.load(open(A, encoding="utf-8"))

raw_data = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
DOTA = json.loads(raw_data[raw_data.index("{"): raw_data.rindex("}") + 1])
by_id = {h["id"]: h for h in DOTA["heroes"]}

TAG = re.compile(r"<[^>]+>")
CYR = re.compile("[А-Яа-яЁё]")


def clean(s):
    s = TAG.sub(" ", s or "")
    s = html.unescape(s).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


CTX = ssl._create_unverified_context()


def translate(text):
    q = urllib.parse.quote(text)
    url = ("https://translate.googleapis.com/translate_a/single"
           f"?client=gtx&sl=en&tl=ru&dt=t&q={q}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        d = json.loads(r.read().decode("utf-8"))
    return "".join(seg[0] for seg in d[0]).strip()


POST = [
    (re.compile(r"эффективность предмета", re.I), "Item Potency"),
    (re.compile(r"потенция предмета", re.I), "Item Potency"),
]


def ru_text(s):
    """Возвращает русскую версию строки: как есть, если уже русская, иначе перевод."""
    if not CYR.search(s):
        s = cache.get(s, s)
    for rx, rep in POST:
        s = rx.sub(rep, s)
    return s


cache = {}
if os.path.exists(CACHE):
    cache = json.load(open(CACHE, encoding="utf-8"))

# 1) собрать все английские строки
todo = []
for h in patch.get("heroes", []):
    buckets = [h.get("hero_notes"), h.get("talent_notes")]
    buckets += [ab.get("ability_notes") for ab in (h.get("abilities") or [])]
    for notes in buckets:
        for n in notes or []:
            t = clean(n.get("note"))
            if len(t) > 3 and not CYR.search(t) and t not in cache and t not in todo:
                todo.append(t)

print("к переводу:", len(todo))
fails = 0
for i, t in enumerate(todo, 1):
    for attempt in range(3):
        try:
            cache[t] = translate(t)
            break
        except Exception:
            time.sleep(0.8 * (attempt + 1))
    else:
        fails += 1
        cache[t] = t
    if i % 50 == 0:
        print(f"  {i}/{len(todo)} (ошибок: {fails})", flush=True)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
print("переведено, ошибок:", fails)

# 2) собрать файл
def title_from_id(ability_id, hero_npc):
    key = ab_ids.get(str(ability_id))
    if not key:
        return None
    name = key
    if hero_npc and name.startswith(hero_npc + "_"):
        name = name[len(hero_npc) + 1:]
    if name == "attribute_bonus":
        return "Таланты"
    return " ".join(w.capitalize() for w in name.split("_"))


def notes_to_items(notes, group_title):
    out = []
    for n in notes or []:
        txt = clean(n.get("note"))
        if not txt or txt in ("OLD:", "NEW:"):
            continue
        lead = ""
        if group_title != "Таланты":
            if n.get("aghanims") == "scepter":
                lead = "Скипетр: "
            elif n.get("aghanims") == "shard":
                lead = "Шард: "
        out.append(lead + ru_text(txt))
    return out


heroes = []
for h in patch.get("heroes", []):
    info = by_id.get(h.get("hero_id"))
    if not info:
        continue
    groups = []

    stat = notes_to_items(h.get("hero_notes"), "Характеристики")
    if stat:
        groups.append({"t": "Характеристики", "items": stat})

    tal = notes_to_items(h.get("talent_notes"), "Таланты")
    if tal:
        groups.append({"t": "Таланты", "items": tal})

    for ab in h.get("abilities", []) or []:
        items = notes_to_items(ab.get("ability_notes"), "")
        if not items:
            continue
        title = title_from_id(ab.get("ability_id"), info.get("slug")) or "Способность"
        groups.append({"t": title, "items": items})

    if not groups:
        continue
    heroes.append({"n": info["name"], "id": h["hero_id"],
                   "c": sum(len(g["items"]) for g in groups), "g": groups})

heroes.sort(key=lambda x: x["n"])
js = "window.PATCH742 = " + json.dumps(
    {"patch": patch.get("patch_number"), "heroes": heroes},
    ensure_ascii=False, separators=(",", ":")) + ";\n"
open(os.path.join(HERE, "patch742.js"), "w", encoding="utf-8").write(js)

print("героев:", len(heroes), "| правок:", sum(x["c"] for x in heroes),
      "| размер: %.0f КБ" % (len(js.encode("utf-8")) / 1024))
