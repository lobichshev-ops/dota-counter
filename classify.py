# -*- coding: utf-8 -*-
"""Ярлыки для вкладки «Все герои»: усиление / небольшое усиление / нейтрально /
небольшое ослабление / ослабление.

Считает плюсы и минусы по строкам официальных патчноутов (_patch742_en.json).
Для героев, по которым на странице есть ручной разбор (вкладки «Усиления» и
«Ослабление»), ярлык берётся из этого разбора: там я читал изменения целиком,
а не считал строки.

Результат — _labels.json: hero_id -> {l: код, p: плюсы, m: минусы}
"""
import json, re, collections

d = json.load(open("_patch742_en.json", encoding="utf-8"))

raw = open("data.js", encoding="utf-8").read()
DOTA = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
name_by_id = {h["id"]: h["name"] for h in DOTA["heroes"]}
id_by_name = {v: k for k, v in name_by_id.items()}

COST_FIELDS = [
    "cooldown", "mana cost", "health cost", "cast point", "cast time", "cost",
    "price", "recipe", "replenish", "restock", "restore time", "charge restore",
    "damage reduction", "damage taken", "penalty", "backswing",
]
DOWN = re.compile(r"\b(decreased|reduced|lowered|less|shorter|slower)\b")
UP = re.compile(r"\b(increased|raised|more|longer|higher|faster)\b")
NEG = re.compile(r"\b(no longer|removed|can no longer)\b")
POS_NOW = re.compile(r"\bnow (also )?(works|applies|provides|grants|has|can|pierces|affects|stacks|displays|summons|allows)\b")
NEUTRAL = re.compile(r"\b(replaced|reworked|renamed|swapped|rescaled)\b")


def polarity(text):
    low = text.lower()
    if NEG.search(low):
        return -1
    if DOWN.search(low) is None and UP.search(low) is None:
        return 1 if POS_NOW.search(low) else 0
    if NEUTRAL.search(low) and not (DOWN.search(low) and DOWN.search(low).start() < (UP.search(low).start() if UP.search(low) else 10**9)):
        pass
    m = DOWN.search(low)
    upm = UP.search(low)
    if m and upm:
        down = m.start() < upm.start()
        m = m if down else upm
    elif m:
        down = True
    else:
        down = False
        m = upm
    head = low[:m.start()]
    cost_like = any(f in head for f in COST_FIELDS)
    if cost_like:
        return 1 if down else -1
    return -1 if down else 1


def lines_of(h):
    out = []
    for key in ("hero_notes", "talent_notes"):
        for n in h.get(key) or []:
            out.append(n.get("note", ""))
    for ab in h.get("abilities") or []:
        for n in ab.get("ability_notes") or []:
            out.append(n.get("note", ""))
    return [re.sub(r"<[^>]+>", " ", x).strip() for x in out
            if x and x.strip() not in ("OLD:", "NEW:")]


# ручные ярлыки для героев, которые разобраны на вкладках «Усиления»/«Ослабление»
OVERRIDES = {
    # усиления
    "Chaos Knight": "up", "Pugna": "up", "Chen": "up", "Nyx Assassin": "up",
    "Dazzle": "up", "Leshrac": "up", "Templar Assassin": "up", "Visage": "up",
    "Storm Spirit": "up", "Tiny": "up", "Puck": "up",
    "Omniknight": "sup", "Lone Druid": "sup", "Huskar": "sup",
    "Treant Protector": "sup", "Troll Warlord": "sup", "Ursa": "sup",
    "Sniper": "sup", "Kunkka": "sup", "Razor": "sup", "Sand King": "sup",
    "Shadow Shaman": "sup",
    # ослабления
    "Meepo": "down", "Beastmaster": "down", "Batrider": "down",
    "Hoodwink": "down", "Death Prophet": "down", "Brewmaster": "down",
    "Lina": "down", "Enigma": "down", "Necrophos": "down",
    "Witch Doctor": "down", "Phantom Lancer": "down", "Invoker": "down",
    "Pudge": "sdown", "Zeus": "sdown", "Lion": "sdown", "Tidehunter": "sdown",
    "Lich": "sdown", "Riki": "sdown", "Tinker": "sdown",
    "Winter Wyvern": "sdown", "Windranger": "sdown", "Abaddon": "sdown",
}


def label_for(score):
    if score >= 3:
        return "up"
    if score >= 1:
        return "sup"
    if score == 0:
        return "flat"
    if score >= -2:
        return "sdown"
    return "down"


labels = {}
auto = collections.Counter()
for h in d.get("heroes", []):
    hid = h["hero_id"]
    name = name_by_id.get(hid)
    if not name:
        continue
    ls = lines_of(h)
    plus = sum(1 for x in ls if polarity(x) > 0)
    minus = sum(1 for x in ls if polarity(x) < 0)
    score = plus - minus
    code = OVERRIDES.get(name) or label_for(score)
    labels[str(hid)] = {"l": code, "p": plus, "m": minus, "s": score, "n": len(ls),
                        "o": name in OVERRIDES}
    auto[code] += 1

json.dump(labels, open("_labels.json", "w", encoding="utf-8"), ensure_ascii=False)
print("ярлыков:", len(labels), "| распределение:", dict(auto))
for n in ("Invoker", "Beastmaster", "Nyx Assassin", "Omniknight", "Meepo"):
    hid = id_by_name[n]
    print(f"  {n:16}", labels[str(hid)])
