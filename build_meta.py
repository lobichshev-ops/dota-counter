# -*- coding: utf-8 -*-
"""Собирает meta742.js — предполагаемую мету на данных Dota2ProTracker + правках патча.

База: рейтинг D2PT по итогам 7.41f (последний полный патч, большие выборки) —
по 7 героев на позицию. Поправка: ярлык патча из classify.py (усиление/ослабление).
Итог: по 5 героев на позицию с обоснованием.
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
grid = json.load(open(os.path.join(HERE, "_grid741.json"), encoding="utf-8"))

raw = open(os.path.join(HERE, "patch742.js"), encoding="utf-8").read()
PATCH = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
patch_by_name = {h["n"]: h for h in PATCH["heroes"]}

raw_data = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
DOTA = json.loads(raw_data[raw_data.index("{"): raw_data.rindex("}") + 1])
name_by_id = {h["id"]: h["name"] for h in DOTA["heroes"]}

BONUS = {"up": 10, "sup": 5, "flat": 0, "sdown": -5, "down": -10}
PATCH_PHRASE = {
    "up": "патч его заметно усилил",
    "sup": "патч слегка усилил",
    "flat": "патч почти не тронул",
    "sdown": "патч слегка ослабил",
    "down": "но патч его ослабил",
}
TITLES = {"Carry": "Керри", "Mid": "Мид", "Offlane": "Оффлейн",
          "Support": "Софт-саппорт", "Hard Support": "Фулл-саппорт"}
ORDER = ["Carry", "Mid", "Offlane", "Support", "Hard Support"]


BAD = ("break", "истощением", "экранный", "пипс", "отображает", "подсвеч",
       "визуал", "индикатор", "иконке", "теперь имеет")
MINOR = ("базовый урон", "базовое здоровье", "прирост ловкости", "прирост силы",
         "прирост интеллекта", "базовая броня", "базовая ловкость",
         "базовая сила", "базовый интеллект")
UP_WORDS = ("увеличен", "увеличена", "увеличено", "усилен", "усилена", "больше")
DOWN_WORDS = ("уменьшен", "уменьшена", "уменьшено", "урезан", "снижен", "сокращ", "меньше")


def headline(hero, verdict):
    """Самая содержательная строка про изменения героя, по возможности в тон ярлыку."""
    if not hero or verdict == "flat":
        return ""
    cands = []
    for g in hero.get("g", []):
        if g["t"] == "Таланты":
            continue
        ability = g["t"] not in ("Характеристики",)
        for item in g["items"]:
            text = re.sub(r"^(Скипетр|Шард):\s*", "", item).strip()
            if len(text) < 25:
                continue
            low = text.lower()
            if any(b in low for b in BAD):
                continue
            score = 0
            if ability:
                score += 3
            if re.search(r"\d", text):
                score += 2
            if any(w in low for w in UP_WORDS + DOWN_WORDS):
                score += 2
            if verdict in ("up", "sup") and any(w in low for w in UP_WORDS):
                score += 2
            if verdict in ("down", "sdown") and any(w in low for w in DOWN_WORDS):
                score += 2
            if "/" in text:
                score += 1
            if len(text) <= 110:
                score += 1
            if len(text) > 160:
                score -= 1
            if any(m in low for m in MINOR):
                score -= 3
            if re.search(r"\bна [123]\b", low):
                score -= 2
            # «расход маны увеличен» / «перезарядка увеличена» — это ухудшение
            if re.search(r"(маны|стоимость|перезарядк|кулдаун|кд)[^.]*увеличен", low):
                score -= 6
            if re.search(r"(перезарядк|кулдаун|стоимость|расход маны)[^.]*уменьшен", low):
                score += 3
            cands.append((score, text))
    if not cands:
        return ""
    cands.sort(key=lambda x: -x[0])
    need = 3 if verdict in ("up", "down") else 5
    if cands[0][0] < need:
        return ""
    text = cands[0][1].rstrip(".")
    text = text[0].lower() + text[1:]
    if len(text) > 130:
        text = text[:127].rsplit(" ", 1)[0] + "…"
    return text


all_roles = next(c for c in grid["configs"] if c["config_name"].endswith("All Roles"))
positions = {}
for cat in all_roles["categories"]:
    role = cat["category_name"]
    if role not in TITLES:
        continue
    rows = []
    for idx, hid in enumerate(cat["hero_ids"]):
        name = name_by_id.get(hid)
        if not name:
            continue
        ph = patch_by_name.get(name, {})
        verdict = ph.get("v", "flat")
        score = (8 - idx) * 2 + BONUS.get(verdict, 0)
        rank_phrase = ("Первый номер рейтинга D2PT в 7.41f" if idx == 0
                       else f"Топ-{idx + 1} рейтинга D2PT в 7.41f" if idx < 3
                       else "В топ-7 рейтинга D2PT в 7.41f")
        why = rank_phrase + ", " + PATCH_PHRASE.get(verdict, "") + "."
        head = headline(ph, verdict)
        if head:
            why += " " + head[0].upper() + head[1:] + "."
        rows.append({"n": name, "why": why, "score": score})
    rows.sort(key=lambda r: -r["score"])
    positions[str(ORDER.index(role) + 1)] = {"title": TITLES[role],
                                             "items": [[r["n"], r["why"]] for r in rows[:5]]}

note = ("<b>Как собрано.</b> База — рейтинг Dota2ProTracker по итогам 7.41f: последний патч, "
        "где есть большие выборки (по 7 героев на позицию). Дальше каждый герой сдвинут "
        "вверх или вниз по ярлыку из вкладки «Все герои»: заметное усиление +10, небольшое +5, "
        "ослабление −10 и так далее. Сам 7.42 вышел 18 ноября, и за сутки по нему есть только "
        "несколько десятков матчей на героя — такие винрейты ещё шум, поэтому в основу они не легли.")

out = {"note": note, "positions": positions}
js = "window.META742 = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(os.path.join(HERE, "meta742.js"), "w", encoding="utf-8").write(js)

print("позиций:", len(positions), "| размер: %.0f КБ" % (len(js.encode("utf-8")) / 1024))
for p in sorted(positions, key=int):
    print("\n", p, positions[p]["title"])
    for name, why in positions[p]["items"]:
        print(f"   {name:18} {why[:120]}")
