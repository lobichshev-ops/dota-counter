// Прогон cm.html в node с минимальной DOM-заглушкой: проверяем, что доска
// драфта строится и в ней правильное число слотов.
const fs = require("fs");
const path = require("path");

const DIR = __dirname;
global.window = {};
require(path.join(DIR, "data.js"));
require(path.join(DIR, "app.js"));

const els = new Map();
function mkEl() {
  const el = {
    className: "", textContent: "", title: "", innerHTML: "", style: {}, value: "",
    hidden: false, children: [], onclick: null, oninput: null, disabled: false,
    appendChild(c) {
      if (c && c.__frag) this.children.push(...c.children);
      else this.children.push(c);
    },
    querySelector() { return mkEl(); },
    querySelectorAll() { return []; }
  };
  return el;
}

global.document = {
  createElement: mkEl,
  createDocumentFragment() {
    return { __frag: true, children: [], appendChild(c) { this.children.push(c); } };
  },
  getElementById(id) {
    if (!els.has(id)) els.set(id, mkEl());
    return els.get(id);
  },
  addEventListener() {}
};
global.location = { hash: "" };
global.history = { replaceState() {} };

const html = fs.readFileSync(path.join(DIR, "cm.html"), "utf8");
const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);
if (blocks.length !== 1) {
  console.error("ожидался один инлайн-скрипт, найдено " + blocks.length);
  process.exit(1);
}

function run(hash) {
  els.clear();
  global.location.hash = hash;
  new Function("window", "document", "location", "history", blocks[0])(
    global.window, global.document, global.location, global.history
  );
  return {
    board: els.get("board").innerHTML,
    res: textOf(els.get("res"))
  };
}

function count(str, re) { return (str.match(re) || []).length; }

// заглушка не умеет innerHTML-разбор, поэтому текст выдачи собираем по дереву
function textOf(node) {
  if (!node) return "";
  let s = "";
  if (typeof node.innerHTML === "string") s += node.innerHTML;
  if (typeof node.textContent === "string") s += node.textContent;
  if (Array.isArray(node.children)) for (const c of node.children) s += textOf(c);
  return s;
}

// --- пустой драфт ---
let out = run("");
let b = out.board;
console.log("пустой драфт:");
console.log("  .dside:        " + count(b, /class="dside /g));
console.log("  слотов пиков:  " + count(b, /class="dslot/g) + " (ожидалось 10)");
console.log("  слотов банов:  " + count(b, /class="bslot/g) + " (ожидалось 14)");
console.log("  подсветка хода: " + (b.indexOf("next") !== -1 ? "есть" : "НЕТ"));
console.log("  шаг:           " + (/Шаг <b>(\d+)<\/b>/.exec(b) || [])[1] + " из 24");

// --- после 8 ходов: 7 банов + первый пик Radiant (шаги 1-7 — баны) ---
out = run("#cm,rad,0,1,2,3,4,5,6,7");
b = out.board;
console.log("\nпосле 8 ходов (7 банов + 1 пик Radiant):");
console.log("  заполнено пиков: " + count(b, /<img class="dslot"/g) + " (ожидалось 1)");
console.log("  заполнено банов: " + count(b, /<img class="bslot"/g) + " (ожидалось 7)");
console.log("  пустых слотов пиков: " + count(b, /dslot empty/g) + " (ожидалось 9)");
console.log("  пустых слотов банов: " + count(b, /bslot empty/g) + " (ожидалось 7)");
console.log("  шаг: " + (/Шаг <b>(\d+)<\/b>/.exec(b) || [])[1] + " из 24");
console.log("  совет на пик: " + (out.res.indexOf("Кого брать") !== -1 ? "да" : "НЕТ"));

// --- состояние на бане ---
out = run("#cm,rad,0,1,2");
b = out.board;
console.log("\nна бане (шаг 4):");
console.log("  совет на бан: " + (out.res.indexOf("Кого банить") !== -1 ? "да" : "НЕТ"));
console.log("  заполнено банов: " + count(b, /<img class="bslot"/g) + " (ожидалось 3)");
