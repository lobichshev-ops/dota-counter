# -*- coding: utf-8 -*-
"""Сравнение двух способов ранжировать контрпики: общая сила и 'чистый' контр."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    raw = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
    raw = raw[raw.index("{"): raw.rindex("}") + 1]
    return json.loads(raw)


def rank(d, idx, mode):
    heroes, mu, p, games = d["heroes"], d["mu"], d["p"], d["games"]
    rows = []
    for c in range(len(heroes)):
        if c in idx:
            continue
        if mode == "power":       # сколько выигрывает против этой пятёрки
            score = sum(p[c][e] / 100.0 - 50.0 for e in idx)
        else:                      # чистый контр-эффект
            score = sum(mu[c][e] * 25 for e in idx)
        rows.append((score, c))
    rows.sort(reverse=True)
    return rows


def main():
    d = load()
    heroes = d["heroes"]
    by_name = {h["name"].lower(): i for i, h in enumerate(heroes)}
    scenarios = [
        "Sniper",
        "Axe",
        "Pudge,Crystal Maiden,Sniper,Lifestealer,Axe",
        "Invoker,Phantom Assassin,Lion,Legion Commander,Crystal Maiden",
    ]
    for sc in scenarios:
        idx = [by_name[n.strip().lower()] for n in sc.split(",") if n.strip().lower() in by_name]
        print(f"\n=== против: {', '.join(heroes[i]['name'] for i in idx)}")
        rp, rc = rank(d, idx, "power"), rank(d, idx, "counter")
        print(f"  {'ПО СИЛЕ':<34} | ЧИСТЫЙ КОНТР")
        for k in range(8):
            s1, c1 = rp[k]
            s2, c2 = rc[k]
            print(f"  {heroes[c1]['name']:<20} {s1:+6.1f} п.п. | "
                  f"{heroes[c2]['name']:<20} {s2:+6.1f}")

        # насколько сильно меняется выдача от смены врагов
        top_power = [c for _, c in rp[:10]]
        print(f"  пересечение топ-10 'по силе' и 'по контру': "
              f"{len(set(top_power) & set(c for _, c in rc[:10]))}/10")


if __name__ == "__main__":
    main()
