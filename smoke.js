// Проверка data.js и выдачи с учётом позиций (запускается node'ом, не в браузере)
const path = require("path");
global.window = {};
require(path.join(__dirname, "data.js"));
const D = window.DOTA_DATA;

const POSN = ["", "керри", "мид", "оффлейн", "софт-саппорт", "фулл-саппорт"];
const POS_W = [1.15, 1.15, 1.0, 0.9, 0.9];
const MIN_POS = 10;

console.log("meta:", JSON.stringify(D.meta));
console.log("heroes:", D.heroes.length, "| pos:", D.pos.length, "x", D.pos[0].length);

const byName = new Map(D.heroes.map((h, i) => [h.name.toLowerCase(), i]));
const pct = i => D.pos[i].map((v, k) => `P${k + 1}:${v}%`).join(" ");
const bestPos = i => D.pos[i].map((v, k) => ({ p: k + 1, v }))
  .filter(x => x.v >= MIN_POS).sort((a, b) => b.v - a.v);
const TOP2 = D.heroes.map((h, i) => bestPos(i).slice(0, 2).map(x => x.p));
const canPlay = (i, p) => TOP2[i].includes(p);

console.log("\nпозиции нескольких героев:");
for (const n of ["Anti-Mage", "Invoker", "Axe", "Crystal Maiden", "Pudge", "Lifestealer"]) {
  const i = byName.get(n.toLowerCase());
  console.log("  " + n.padEnd(16) + pct(i));
}

function recommend(enemies, myPos) {
  const idx = enemies.map(([n]) => byName.get(n.toLowerCase()));
  const pos = enemies.map(([, p]) => p);
  const rows = [];
  for (let c = 0; c < D.heroes.length; c++) {
    if (idx.includes(c)) continue;
    if (myPos && !canPlay(c, myPos)) continue;
    let s = 0, mg = Infinity;
    for (let k = 0; k < idx.length; k++) {
      s += D.mu[c][idx[k]] * 25 * POS_W[pos[k] - 1];
      mg = Math.min(mg, D.games[c][idx[k]]);
    }
    rows.push([s, D.heroes[c].name, mg]);
  }
  rows.sort((a, b) => b[0] - a[0]);
  return rows;
}

const comp = [["Axe", 3], ["Sniper", 1], ["Pudge", 4], ["Crystal Maiden", 5], ["Lifestealer", 1]];
console.log("\nдрафт: " + comp.map(([n, p]) => n + "(P" + p + ")").join(", "));

for (let p = 1; p <= 5; p++) {
  const rows = recommend(comp, p).slice(0, 3);
  console.log("\n  позиция " + p + " (" + POSN[p] + "):");
  rows.forEach(r => console.log("    " + r[1].padEnd(18) +
    (r[0] >= 0 ? "+" : "") + r[0].toFixed(1) + " п.п.  min " + r[2] + " игр"));
}

// сколько героев вообще доступно на каждой позиции
const avail = [1, 2, 3, 4, 5].map(p => TOP2.filter(t => t.includes(p)).length);
console.log("\nгероев с этой позицией в основных двух: " + avail.join(" / "));
