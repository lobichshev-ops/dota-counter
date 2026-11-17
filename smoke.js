// Проверка app.js и данных без браузера (node)
const path = require("path");
global.window = {};
require(path.join(__dirname, "data.js"));
require(path.join(__dirname, "app.js"));
const A = window.DOTA;

console.log("героев:", A.N, "| данных:", A.D.meta.built);

// --- сортировка по атрибуту ---
const groups = [];
for (const i of A.ORDER) {
  const a = A.H[i].attr;
  if (groups[groups.length - 1] !== a) groups.push(a);
}
console.log("порядок групп:", groups.join(" → "));

const counts = {};
for (const i of A.ORDER) counts[A.H[i].attr] = (counts[A.H[i].attr] || 0) + 1;
console.log("по атрибутам:", Object.entries(counts).map(([k, v]) => k + "=" + v).join(", "));

const contiguous = new Set(groups).size === groups.length;
console.log("группы не перемешаны:", contiguous ? "да" : "НЕТ");

const first = A.ORDER.slice(0, 3).map(i => A.H[i].name + " (" + A.H[i].attr + ")");
console.log("первые в сетке:", first.join(", "));

// --- позиции ---
const avail = [1, 2, 3, 4, 5].map(p => A.TOP2.filter(t => t.includes(p)).length);
console.log("героев на позициях 1-5:", avail.join(" / "));

// --- скоринг на примере ---
const byName = A.byName;
const enemies = ["Axe", "Sniper", "Lifestealer"].map(n => byName.get(n.toLowerCase()));
const rows = [];
for (let c = 0; c < A.N; c++) {
  if (enemies.includes(c)) continue;
  rows.push(A.score(c, enemies, null));
}
rows.sort((a, b) => b.s - a.s);
console.log("\nтоп-5 против Axe + Sniper + Lifestealer:");
rows.slice(0, 5).forEach(r => console.log("  " + A.H[r.c].name.padEnd(20) +
  (r.s >= 0 ? "+" : "") + r.s.toFixed(1) + " п.п."));

// --- бан: кто контрит наш пик ---
const own = [byName.get("anti-mage")];
const ban = [];
for (let c = 0; c < A.N; c++) {
  if (own.includes(c)) continue;
  ban.push(A.score(c, own, null));
}
ban.sort((a, b) => b.s - a.s);
console.log("\nкого банить против нашего Anti-Mage (топ-5):");
ban.slice(0, 5).forEach(r => console.log("  " + A.H[r.c].name.padEnd(20) +
  "+" + r.s.toFixed(1)));

// --- отрисовка сетки на минимальном DOM-заглушке: проверяем группы по атрибуту ---
const created = [];
function mkEl() {
  const el = {
    className: "", textContent: "", title: "", innerHTML: "", style: {},
    children: [],
    appendChild(c) {
      if (c && c.__frag) this.children.push(...c.children);
      else this.children.push(c);
    },
    querySelector() { return null; }
  };
  created.push(el);
  return el;
}
global.document = {
  createElement: mkEl,
  createDocumentFragment() {
    return { __frag: true, children: [], appendChild(c) { this.children.push(c); } };
  }
};

function drawGrid(cfg) {
  created.length = 0;
  const root = mkEl();
  A.grid(root, Object.assign({ q: "", pos: 0, taken: new Set(), onPick() {} }, cfg));
  return {
    total: created.filter(e => e.className.indexOf("hero") === 0).length,
    heads: created.filter(e => e.className.indexOf("agroup") === 0)
      .map(e => e.className.replace("agroup ", "") + ":" + e.textContent)
  };
}

const full = drawGrid({});
console.log("\nсетка без фильтров: героев " + full.total);
console.log("  заголовки: " + full.heads.join(" | "));

const onlyStr = drawGrid({ q: "axe" });
console.log("поиск 'axe': героев " + onlyStr.total + ", заголовки: " + onlyStr.heads.join(" | "));

const pos5 = drawGrid({ pos: 5 });
console.log("фильтр позиции 5: героев " + pos5.total + ", заголовки: " + pos5.heads.join(" | "));

