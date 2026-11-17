/* Общая логика для index.html и cm.html: загрузка данных, сортировка героев
   по атрибуту, сетка, скоринг и строка выдачи. */
(function(){
  "use strict";

  const D = window.DOTA_DATA;
  const H = D.heroes;
  const N = H.length;

  const CDN = "img/";
  const MIN_POS = 10;                                   // % игр, чтобы считать позицию рабочей
  const POSN = ["", "керри", "мид", "оффлейн", "софт-саппорт", "фулл-саппорт"];
  const POS_W = [1.15, 1.15, 1.0, 0.9, 0.9];            // вес контры врага по его позиции

  // порядок групп в сетке
  const ATTRS = [["str", "Сила"], ["agi", "Ловкость"], ["int", "Интеллект"], ["all", "Универсальные"]];
  const ATTR_RANK = { str: 0, agi: 1, int: 2, all: 3 };

  const img = i => CDN + H[i].slug + ".webp";
  const byName = new Map(H.map((h, i) => [h.name.toLowerCase(), i]));

  const bestPosList = i => D.pos[i]
    .map((v, k) => ({ p: k + 1, v }))
    .filter(x => x.v >= MIN_POS)
    .sort((a, b) => b.v - a.v);

  const TOP2 = H.map((h, i) => bestPosList(i).slice(0, 2).map(x => x.p));
  const canPlay = (i, p) => TOP2[i].includes(p);

  const topPos = i => {
    const p = D.pos[i];
    let b = 0;
    for (let k = 1; k < 5; k++) if (p[k] > p[b]) b = k;
    return b + 1;
  };

  // индексы героев в порядке сетки: сначала по атрибуту, внутри — по имени
  const ORDER = H.map((h, i) => i).sort((a, b) => {
    const ra = ATTR_RANK[H[a].attr] === undefined ? 9 : ATTR_RANK[H[a].attr];
    const rb = ATTR_RANK[H[b].attr] === undefined ? 9 : ATTR_RANK[H[b].attr];
    if (ra !== rb) return ra - rb;
    return H[a].name.localeCompare(H[b].name, "en");
  });

  const attrLabel = a => {
    for (const [key, label] of ATTRS) if (key === a) return label;
    return "Прочие";
  };

  /* cfg: { q, pos, taken:Set, onPick(i) } */
  function grid(el, cfg){
    const q = ((cfg && cfg.q) || "").trim().toLowerCase();
    const taken = (cfg && cfg.taken) || new Set();
    const pos = (cfg && cfg.pos) || 0;

    el.innerHTML = "";
    const frag = document.createDocumentFragment();
    let lastAttr = null;
    let shown = 0;

    for (const i of ORDER){
      const h = H[i];
      if (q && h.name.toLowerCase().indexOf(q) === -1) continue;
      if (pos && !canPlay(i, pos)) continue;

      if (h.attr !== lastAttr){
        const head = document.createElement("div");
        head.className = "agroup " + (h.attr || "all");
        head.textContent = attrLabel(h.attr);
        frag.appendChild(head);
        lastAttr = h.attr;
      }

      const item = document.createElement("div");
      item.className = "hero attr-" + (h.attr || "all") + (taken.has(i) ? " picked" : "");
      const bp = bestPosList(i).slice(0, 2).map(x => "P" + x.p + " " + x.v + "%").join(" · ");
      item.title = h.name + (bp ? " — " + bp : "");
      item.innerHTML =
        '<img loading="lazy" src="' + img(i) + '" alt="' + h.name + '"' +
        ' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'grid\'">' +
        '<div class="fallback">' + h.name[0] + '</div>' +
        '<div class="pbadge">P' + topPos(i) + '</div>' +
        '<div class="nm">' + h.name + '</div>';
      item.onclick = () => cfg.onPick(i);
      frag.appendChild(item);
      shown++;
    }

    if (!shown){
      const e = document.createElement("div");
      e.className = "empty";
      e.style.gridColumn = "1/-1";
      e.textContent = "Никого не нашлось";
      frag.appendChild(e);
    }
    el.appendChild(frag);
  }

  /* насколько герой ci хорош против списка heroes.
     posList — позиции врагов (для веса), либо null для равных весов. */
  function score(ci, list, posList){
    let s = 0, minGames = Infinity;
    const parts = [];
    for (let k = 0; k < list.length; k++){
      const e = list[k];
      const w = posList ? POS_W[posList[k] - 1] : 1;
      const v = D.mu[ci][e] * 25 * w;
      s += v;
      minGames = Math.min(minGames, D.games[ci][e]);
      parts.push({ e: e, v: v });
    }
    return { c: ci, s: s, parts: parts, minGames: minGames };
  }

  /* строка результата. opts: { ban:bool, hint:string } */
  function rowEl(r, opts){
    opts = opts || {};
    const h = H[r.c];
    const el = document.createElement("div");
    el.className = "row";

    const rel = (opts.ban || r.minGames === Infinity)
      ? ""
      : (r.minGames >= 500 ? "надёжно"
         : r.minGames >= 200 ? "средне"
         : "мало данных (" + r.minGames + " игр)");

    const parts = r.parts.slice().sort((a, b) => b.v - a.v)
      .map(p => '<span class="part ' + (p.v >= 0 ? "pos" : "neg") + '">' +
                H[p.e].name.slice(0, 11) + ' <b>' + (p.v >= 0 ? "+" : "") +
                p.v.toFixed(1) + '</b></span>').join("");

    const mine = bestPosList(r.c).slice(0, 2)
      .map(x => "P" + x.p + " " + x.v + "%").join(" · ");

    const cls = opts.ban ? "bad" : (r.s < 0 ? "low" : "");
    el.innerHTML =
      '<img class="ico" loading="lazy" src="' + img(r.c) + '" alt="">' +
      '<div class="body">' +
        '<div class="top"><span class="name">' + h.name + '</span>' +
        '<span class="score ' + cls + '">' +
          (r.s >= 0 ? "+" : "") + r.s.toFixed(1) + (opts.ban ? "" : " п.п.") + '</span></div>' +
        '<div class="parts">' +
          (parts || '<span class="part">' + (opts.hint || "") + '</span>') +
        '</div>' +
        (mine ? '<div class="rel">играется: <i>' + mine + '</i>' +
                (rel ? " · " + rel : "") + '</div>' : '') +
      '</div>';
    return el;
  }

  window.DOTA = {
    D: D, H: H, N: N,
    POSN: POSN, POS_W: POS_W, MIN_POS: MIN_POS,
    img: img, byName: byName,
    bestPosList: bestPosList, TOP2: TOP2, canPlay: canPlay, topPos: topPos,
    ORDER: ORDER, grid: grid, score: score, rowEl: rowEl
  };
})();
