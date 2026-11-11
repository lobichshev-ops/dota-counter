# -*- coding: utf-8 -*-
"""
Собирает матрицу матчапов Dota 2 и считает "чистый" контрпик-эффект.

Источник: OpenDota SQL explorer (бесплатно, без ключа).
Один запрос даёт по всем парам героев: сколько раз встречались и сколько
раз выиграл "первый" (он на Radiant).

Модель:
  1. Убираем преимущество Radiant — складываем обе стороны пары.
  2. Сглаживаем винрейт пары к базовому винрейту героя (Байес, K игр).
  3. Двухфакторная модель в логитах: x(a,b) ~ theta_a - theta_b + mu(a,b).
     mu и есть "именно этот герой хорош именно против этого", без учёта того,
     что герой просто силён в патче.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.opendota.com/api"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
HERE = os.path.dirname(os.path.abspath(__file__))

# сколько игр "недоверия" подмешиваем к винрейту пары (сглаживание к базовому)
K_SHRINK = 250
# минимальная длительность матча: отсекаем абузы/заброшенные
MIN_DURATION = 600

SQL = f"""
SELECT pm1.hero_id AS a,
       pm2.hero_id AS b,
       count(*) AS g,
       sum((m.radiant_win)::int) AS w
FROM player_matches pm1
JOIN player_matches pm2
  ON pm1.match_id = pm2.match_id
 AND pm1.player_slot < 128
 AND pm2.player_slot >= 128
JOIN matches m ON m.match_id = pm1.match_id
WHERE m.duration > {MIN_DURATION}
GROUP BY 1, 2
"""

# Позиция 1-5 в API нигде не хранится, поэтому выводим её из линий и фарма:
# мид — всегда 2; в безопасной линии больше нетворса = 1, второй = 5;
# в сложной линии больше нетворса = 3, второй = 4.
POS_SQL = """
WITH t AS (
  SELECT match_id, hero_id, net_worth,
         CASE WHEN player_slot < 128 THEN 0 ELSE 1 END AS team,
         lane_role
  FROM player_matches
  WHERE net_worth > 0 AND lane_role IN (1, 2, 3)
), r AS (
  SELECT hero_id, lane_role,
         ROW_NUMBER() OVER (PARTITION BY match_id, team, lane_role
                            ORDER BY net_worth DESC) AS wl
  FROM t
)
SELECT hero_id, lane_role, wl, count(*) AS n FROM r GROUP BY 1, 2, 3
"""


def lane_to_pos(lane_role, wl):
    if lane_role == 2:
        return 2
    if lane_role == 1:
        return 1 if wl == 1 else 5
    if lane_role == 3:
        return 3 if wl == 1 else 4
    return None


def api(path, timeout=300, tries=3):
    url = path if path.startswith("http") else BASE + path
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
    raise last


def logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def main():
    print("[1/5] герои...")
    heroes_raw = api("/heroes")
    heroes = sorted(heroes_raw, key=lambda h: h["id"])
    n = len(heroes)
    print(f"      {n} героев")

    print("[2/5] матрица матчапов (один SQL-запрос)...")
    t0 = time.time()
    data = api("/explorer?sql=" + urllib.parse.quote(SQL), timeout=600)
    rows = data.get("rows") or []
    if not rows:
        sys.exit("explorer вернул пусто: %s" % str(data)[:500])
    print(f"      {len(rows)} пар за {time.time() - t0:.1f}s")

    ids = [h["id"] for h in heroes]
    ix = {hid: i for i, hid in enumerate(ids)}

    # radiant a -> dire b: (games, wins of a)
    raw = {}
    for r in rows:
        a, b, g, w = r["a"], r["b"], r["g"], r["w"]
        if a in ix and b in ix and a != b:
            raw[(a, b)] = (int(g), int(w))
    total_obs = sum(g for g, _ in raw.values())
    print(f"      наблюдений всего: {total_obs:,}")

    print("[3/5] позиции героев (линия + нетворс)...")
    pos_rows = api("/explorer?sql=" + urllib.parse.quote(POS_SQL), timeout=600).get("rows") or []
    pos_count = [[0] * 6 for _ in range(n)]
    for r in pos_rows:
        i = ix.get(r["hero_id"])
        if i is None:
            continue
        p = lane_to_pos(r["lane_role"], r["wl"])
        if p:
            pos_count[i][p] += r["n"]

    pos_pct = []
    for i in range(n):
        tot = sum(pos_count[i])
        if not tot:
            pos_pct.append([20, 20, 20, 20, 20])
        else:
            pos_pct.append([round(pos_count[i][p] * 100 / tot) for p in range(1, 6)])
    have = sum(1 for i in range(n) if sum(pos_count[i]))
    print(f"      героев с данными о позиции: {have}/{n}")

    # --- 1. снимаем сторону: складываем (a vs b) и (b vs a) ---
    # G2[a][b] = сколько раз пара играла, W2[a][b] = сколько из них выиграл a
    G2 = [[0] * n for _ in range(n)]
    W2 = [[0.0] * n for _ in range(n)]
    for (a, b), (g_ab, w_ab) in raw.items():
        i, j = ix[a], ix[b]
        G2[i][j] += g_ab
        W2[i][j] += w_ab
        # в матче b против a герой b проиграл, если выиграл a
        G2[j][i] += g_ab
        W2[j][i] += g_ab - w_ab

    # --- 2. байесовское сглаживание к базовому винрейту героя ---
    baseline = [0.5] * n
    for i in range(n):
        g = sum(G2[i])
        w = sum(W2[i])
        if g:
            baseline[i] = w / g

    p = [[0.5] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            g = G2[i][j]
            w = W2[i][j]
            p[i][j] = (w + K_SHRINK * baseline[i]) / (g + K_SHRINK)

    # --- 3. двухфакторная модель в логитах ---
    x = [[logit(p[i][j]) if i != j else 0.0 for j in range(n)] for i in range(n)]
    theta = [0.0] * n
    for _ in range(80):
        new = theta[:]
        for i in range(n):
            s = 0.0
            cnt = 0
            for j in range(n):
                if i == j:
                    continue
                s += x[i][j] + theta[j]
                cnt += 1
            new[i] = s / cnt
        mean = sum(new) / n
        theta = [v - mean for v in new]

    mu = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                mu[i][j] = x[i][j] - (theta[i] - theta[j])

    # --- 4. отдаём в JS ---
    heroes_out = []
    for h in heroes:
        heroes_out.append({
            "id": h["id"],
            "name": h["localized_name"],
            "attr": h.get("primary_attr"),
            "attack": h.get("attack_type"),
            "roles": h.get("roles") or [],
            "slug": h["name"].replace("npc_dota_hero_", ""),
        })

    payload = {
        "meta": {
            "source": "OpenDota SQL explorer",
            "built": time.strftime("%Y-%m-%d"),
            "heroes": n,
            "observations": total_obs,
            "pairs": len(raw),
            "shrink": K_SHRINK,
            "minDuration": MIN_DURATION,
            "note": "mu в логитах; п.п. = mu*25 при винрейте ~50%",
            "posNote": "позиции выведены из линии и нетворса по 253k матчам",
        },
        "heroes": heroes_out,
        # mu[i][j] = насколько герой i лучше своего обычного уровня против j
        "mu": [[round(mu[i][j], 4) for j in range(n)] for i in range(n)],
        # p[i][j] = винрейт i против j в сотых долях процента (5123 = 51.23%)
        "p": [[int(round(p[i][j] * 10000)) for j in range(n)] for i in range(n)],
        # games[i][j] = сколько игр в паре (обе стороны)
        "games": G2,
        # pos[i] = [P1..P5] проценты: как часто герой играется на этой позиции
        "pos": pos_pct,
        "overall": [round(baseline[i] * 100, 2) for i in range(n)],
    }

    out = os.path.join(HERE, "data.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("window.DOTA_DATA = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print(f"[4/5] записано {out} ({os.path.getsize(out) / 1024:.0f} KB)")

    # короткая сводка в консоль
    med = sorted(G2[i][j] for i in range(n) for j in range(n) if i != j)
    print(f"[5/5] игр на пару: медиана {med[len(med) // 2]}, максимум {med[-1]}")


if __name__ == "__main__":
    main()
