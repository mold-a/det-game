// Справочник «Фармаспр» (страница pharma): поиск и алфавитный указатель.
// Поиск — по торговым названиям и действующему веществу, через base() из core/normalize.js
// (без учёта регистра, «ё», знаков препинания), подстрокой. Карточки и указатель
// сортируются по-русски (Intl.Collator). Данные — только из DOM фрагмента (FORMATS §6.1).

import { base } from "../core/normalize.js";

const TEXT = {
  found: (n) => `Найдено: ${n}`,
  arrow: "→",
};

/** Подходит ли карточка под запрос (обе строки — в форме base()). */
export function matches(haystack, q) {
  return !q || haystack.some((h) => h.includes(q));
}

export function init(root = document) {
  const list = root.querySelector("#fs-list");
  const input = root.querySelector("#fs-q");
  const index = root.querySelector("#fs-index");
  const count = root.querySelector("#fs-count");
  const empty = root.querySelector("#fs-empty");
  const clear = root.querySelector('[data-act="clear"]');
  if (!list || !input) return;

  const collator = new Intl.Collator("ru", { sensitivity: "base", numeric: true });
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const cards = Array.from(list.querySelectorAll(".fs-card")).map((el) => {
    const name = el.dataset.name || "";
    const trades = (el.dataset.trade || "").split("|").filter(Boolean);
    return { el, name, trades, hay: [name, ...trades].map(base) };
  });
  cards.sort((a, b) => collator.compare(a.name, b.name));
  list.append(...cards.map((c) => c.el));

  // Указатель: действующие вещества и торговые названия вперемешку, по алфавиту, по буквам.
  const entries = [];
  for (const c of cards) {
    entries.push({ label: c.name, card: c, target: null });
    for (const t of c.trades) entries.push({ label: t, card: c, target: c.name });
  }
  entries.sort((a, b) => collator.compare(a.label, b.label));

  const groups = new Map();
  for (const e of entries) {
    const letter = (base(e.label)[0] || "#").toUpperCase();
    if (!groups.has(letter)) groups.set(letter, { items: [], node: null });
    groups.get(letter).items.push(e);
  }

  function goTo(card) {
    card.el.hidden = false;
    card.el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
    card.el.focus({ preventScroll: true });
  }

  if (index) {
    index.replaceChildren();
    for (const [letter, group] of groups) {
      const li = document.createElement("li");
      li.className = "fs-index__group";
      const l = document.createElement("span");
      l.className = "fs-index__letter";
      l.setAttribute("aria-hidden", "true");
      l.textContent = letter;
      const ul = document.createElement("ul");
      ul.className = "fs-index__items";
      ul.setAttribute("role", "list");
      for (const e of group.items) {
        const item = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "fs-index__link";
        btn.textContent = e.label;
        if (e.target) {
          const to = document.createElement("span");
          to.className = "fs-index__to";
          to.textContent = ` ${TEXT.arrow} ${e.target}`;
          btn.append(to);
        }
        btn.addEventListener("click", () => goTo(e.card));
        e.node = item;
        item.append(btn);
        ul.append(item);
      }
      li.append(l, ul);
      group.node = li;
      index.append(li);
    }
  }

  function apply() {
    const q = base(input.value);
    let n = 0;
    for (const c of cards) {
      const ok = matches(c.hay, q);
      c.el.hidden = !ok;
      if (ok) n += 1;
    }
    for (const group of groups.values()) {
      let any = false;
      for (const e of group.items) {
        const ok = !q || base(e.label).includes(q) || matches(e.card.hay, q);
        if (e.node) e.node.hidden = !ok;
        any ||= ok;
      }
      if (group.node) group.node.hidden = !any;
    }
    if (count) count.textContent = q ? TEXT.found(n) : "";
    if (empty) empty.hidden = n > 0;
    if (clear) clear.hidden = !input.value;
  }

  input.addEventListener("input", apply);
  input.addEventListener("search", apply);
  input.closest("form")?.addEventListener("submit", (ev) => ev.preventDefault());
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      const first = cards.find((c) => !c.el.hidden);
      if (first && base(input.value)) goTo(first);
    }
  });
  clear?.addEventListener("click", () => {
    input.value = "";
    apply();
    input.focus();
  });
  apply();
}
