// DOM-хелперы системы расследования. Никакого innerHTML для данных:
// строки всегда вставляются как текст. HTML разрешён только из собственной
// сборки (расшифрованные пакеты, их целостность проверяет AES-GCM) — через
// insertTrustedHtml, который всё равно вычищает скрипты и обработчики.

/**
 * h(tag, attrs?, ...children) — создать элемент.
 *   attrs: { class, id, text, dataset: {}, style: {}, on: { click: fn }, onclick: fn,
 *            hidden: true, disabled: false, "aria-*": "…", … }
 *   children: Node | string | number | null | false | массивы из них.
 * Строки становятся текстовыми узлами. null/false/undefined пропускаются.
 */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) {
    children.unshift(attrs);
    attrs = null;
  }
  if (attrs) setAttrs(el, attrs);
  append(el, children);
  return el;
}

export function setAttrs(el, attrs) {
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class" || k === "className") el.className = Array.isArray(v) ? v.filter(Boolean).join(" ") : v;
    else if (k === "text") el.textContent = String(v);
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k === "style" && typeof v === "object") {
      for (const [p, pv] of Object.entries(v)) {
        if (p.startsWith("--")) el.style.setProperty(p, pv);
        else el.style[p] = pv;
      }
    }
    else if (k === "on") for (const [ev, fn] of Object.entries(v)) el.addEventListener(ev, fn);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "value" && "value" in el) el.value = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, String(v));
  }
  return el;
}

/** Добавить детей (строки — как текст). */
export function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false || c === true) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

/** Удалить всё содержимое. */
export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

/** Заменить содержимое текстом (безопасно). */
export function setText(el, text) {
  el.textContent = text == null ? "" : String(text);
  return el;
}

/** Заменить содержимое узлами. */
export function replace(el, ...children) {
  clear(el);
  return append(el, children);
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

let uidCounter = 0;
/** Уникальный id для связки label/aria-*. */
export function uid(prefix = "dg") {
  uidCounter += 1;
  return `${prefix}-${uidCounter}`;
}

const DROP_TAGS = new Set(["SCRIPT", "IFRAME", "OBJECT", "EMBED", "LINK", "META", "BASE", "FORM"]);

/**
 * Вставить HTML ИЗ СОБСТВЕННОЙ СБОРКИ (документы, письма из пакетов).
 * Не для ввода пользователя. Дополнительно удаляет опасные теги,
 * on*-обработчики и javascript:-ссылки.
 */
export function insertTrustedHtml(el, html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = String(html);
  const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_ELEMENT);
  const drop = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (DROP_TAGS.has(n.tagName)) {
      drop.push(n);
      continue;
    }
    for (const a of Array.from(n.attributes)) {
      const name = a.name.toLowerCase();
      const val = a.value.trim().toLowerCase();
      if (name.startsWith("on")) n.removeAttribute(a.name);
      else if ((name === "href" || name === "src" || name === "xlink:href") && val.startsWith("javascript:")) {
        n.removeAttribute(a.name);
      }
    }
  }
  for (const n of drop) n.remove();
  clear(el);
  el.appendChild(tpl.content);
  return el;
}

// ------------------------------------------------------------ живая область

let live = null;
/** Объявить сообщение для экранных дикторов (aria-live=polite). */
export function announce(message, { assertive = false } = {}) {
  if (!live || !live.isConnected) {
    live = h("div", { class: "visually-hidden", "aria-live": "polite", "aria-atomic": "true" });
    document.body.appendChild(live);
  }
  live.setAttribute("aria-live", assertive ? "assertive" : "polite");
  live.textContent = "";
  // Пауза нужна, чтобы диктор заметил замену одинакового текста.
  setTimeout(() => {
    live.textContent = message;
  }, 50);
}

/** Пользователь просит меньше движения. */
export function prefersReducedMotion() {
  return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Время из ISO-строки — «ЧЧ:ММ» по местному времени. */
export function formatTime(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Скачать текст как файл. */
export function downloadText(filename, text, mime = "application/json") {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: filename, hidden: true });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
