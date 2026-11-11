# -*- coding: utf-8 -*-
"""Проверка устойчивости контр-эффекта: считаем mu на двух половинах истории
и смотрим, повторяется ли знак (реальный контр должен воспроизводиться)."""
import json
import math
import urllib.parse
import urllib.request

BASE = "https://api.opendota.com/api"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
    "Accept": "application/json",
}
K = 250


def api(path, timeout=600):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def agg(where):
    sql = f"""
SELECT pm1.hero_id AS a, pm2.hero_id AS b, count(*) AS g, sum((m.radiant_win)::int) AS w
FROM player_matches pm1
JOIN player_matches pm2 ON pm1.match_id = pm2.match_id
 AND pm1.player_slot < 128 AND pm2.player_slot >= 128
JOIN matches m ON m.match_id = pm1.match_id
WHERE m.duration > 600 {where}
GROUP BY 1, 2"""
    return api("/explorer?sql=" + urllib.parse.quote(sql))["rows"]


def logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def fit(rows, ids):
    ix = {h: i for i, h in enumerate(ids)}
    n = len(ids)
    G = [[0] * n for _ in range(n)]
    W = [[0.0] * n for _ in range(n)]
    for r in rows:
        a, b, g, w = r["a"], r["b"], r["g"], r["w"]
        if a not in ix or b not in ix or a == b:
            continue
        i, j = ix[a], ix[b]
        G[i][j] += g; W[i][j] += w
        G[j][i] += g; W[j][i] += g - w
    base = [0.5] * n
    for i in range(n):
        g = sum(G[i])
        if g:
            base[i] = sum(W[i]) / g
    p = [[0.5] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                p[i][j] = (W[i][j] + K * base[i]) / (G[i][j] + K)
    x = [[logit(p[i][j]) if i != j else 0.0 for j in range(n)] for i in range(n)]
    th = [0.0] * n
    for _ in range(80):
        new = [0.0] * n
        for i in range(n):
            s = sum(x[i][j] + th[j] for j in range(n) if j != i)
            new[i] = s / (n - 1)
        m = sum(new) / n
        th = [v - m for v in new]
    return ({(ids[i], ids[j]): x[i][j] - (th[i] - th[j])
             for i in range(n) for j in range(n) if i != j},
            {(ids[i], ids[j]): G[i][j]
             for i in range(n) for j in range(n) if i != j})


def main():
    heroes = sorted(api("/heroes"), key=lambda h: h["id"])
    ids = [h["id"] for h in heroes]

    # случайное разбиение: половина матчей по чётности match_id.
    # так обе половины — один и тот же период и одна мета, расхождение = чистый шум
    print("половина 1 (чётные match_id)...")
    half1 = agg("AND (m.match_id % 2) = 0")
    print("половина 2 (нечётные match_id)...")
    half2 = agg("AND (m.match_id % 2) = 1")

    (mu1, g1), (mu2, g2) = fit(half1, ids), fit(half2, ids)
    common = [k for k in mu1 if k in mu2]
    print(f"\nпар в обеих половинах: {len(common)}")

    # 1) повторяется ли знак
    both_pos = sum(1 for k in common if mu1[k] > 0 and mu2[k] > 0)
    both_neg = sum(1 for k in common if mu1[k] < 0 and mu2[k] < 0)
    agree = (both_pos + both_neg) / len(common)
    print(f"доля пар с совпавшим знаком: {agree:.1%}  (случайность = 50%)")

    # 2) корреляция
    xs = [mu1[k] for k in common]; ys = [mu2[k] for k in common]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    print(f"корреляция mu(половина1) / mu(половина2): {cov / (sx * sy):.3f}")

    # 3) есть ли сигнал на хорошо отыгранных парах
    print("\n  игр в половине | пар   | совпал знак | корреляция")
    for lo, hi in [(0, 50), (50, 150), (150, 400), (400, 10 ** 9)]:
        ks = [k for k in common if lo <= min(g1[k], g2[k]) < hi]
        if len(ks) < 20:
            continue
        a = sum(1 for k in ks if mu1[k] * mu2[k] > 0) / len(ks)
        xk = [mu1[k] for k in ks]; yk = [mu2[k] for k in ks]
        mkx, mky = sum(xk) / len(xk), sum(yk) / len(yk)
        cv = sum((p - mkx) * (q - mky) for p, q in zip(xk, yk))
        s1 = math.sqrt(sum((p - mkx) ** 2 for p in xk))
        s2 = math.sqrt(sum((q - mky) ** 2 for q in yk))
        r = cv / (s1 * s2) if s1 and s2 else 0
        print(f"  {lo:>6}-{min(hi, 10**9):<8} | {len(ks):<5} | {a:>10.1%} | {r:>10.3f}")


if __name__ == "__main__":
    main()
