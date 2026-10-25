// Почтовый ящик (type: mail, pages/mail.js): переключение папок и цепочек, «К списку писем», адрес #mt-<id>.
// Состояние проверяется без DOM; init — на минимальных заглушках DOM (как в video.test.mjs).
import test from "node:test";
import assert from "node:assert/strict";

import { createMailState, threadFromHash, init, THREAD_HASH } from "../../site/assets/js/pages/mail.js";

const THREADS = [
  { id: "personal", folder: "0" },
  { id: "work", folder: "0" },
  { id: "odd", folder: "2" },
];

test("threadFromHash: только известная цепочка из #mt-<id>", () => {
  const ids = THREADS.map((t) => t.id);
  assert.equal(THREAD_HASH, "#mt-");
  assert.equal(threadFromHash("#mt-work", ids), "work");
  assert.equal(threadFromHash("#mt-nope", ids), null);
  assert.equal(threadFromHash("#k=abc", ids), null); // ключ страницы — не цепочка
  assert.equal(threadFromHash("", ids), null);
  assert.equal(threadFromHash("#mt-%E0%A4%A", ids), null); // битая кодировка не ломает
  assert.equal(threadFromHash(undefined, ids), null);
});

test("createMailState: первая папка, без цепочки; открыть — перейти в папку цепочки; назад — к списку", () => {
  const st = createMailState(["0", "1", "2"], THREADS);
  assert.deepEqual(st.get(), { folder: "0", thread: null });
  assert.deepEqual(st.threadsIn("0"), ["personal", "work"]);
  assert.deepEqual(st.threadsIn("1"), []);
  assert.deepEqual(st.open("work"), { folder: "0", thread: "work" });
  assert.deepEqual(st.open("odd"), { folder: "2", thread: "odd" }); // другая папка — переключается сама
  assert.deepEqual(st.back(), { folder: "2", thread: null });
  assert.deepEqual(st.open("missing"), { folder: "2", thread: null }); // неизвестная — без изменений
});

test("createMailState: смена папки закрывает цепочку, неизвестная папка — без изменений", () => {
  const st = createMailState([0, 1, 2], THREADS);
  st.open("personal");
  assert.deepEqual(st.folder(1), { folder: "1", thread: null });
  assert.deepEqual(st.folder("9"), { folder: "1", thread: null });
});

// ---- минимальный DOM

function el(cls, data = {}, attrs = {}) {
  const a = new Map(Object.entries(attrs));
  const listeners = {};
  const classes = new Set(cls.split(" ").filter(Boolean));
  return {
    dataset: { ...data },
    hidden: false,
    focused: 0,
    classList: {
      add: (c) => classes.add(c),
      toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)),
      contains: (c) => classes.has(c),
    },
    getAttribute: (k) => (a.has(k) ? a.get(k) : null),
    setAttribute: (k, v) => a.set(k, String(v)),
    removeAttribute: (k) => a.delete(k),
    addEventListener: (type, fn) => ((listeners[type] ||= []).push(fn)),
    fire(type, target) {
      const ev = { target: target ?? this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
      for (const fn of listeners[type] || []) fn(ev);
      return ev;
    },
    focus() {
      this.focused += 1;
    },
    scrollIntoView() {},
    closest: () => null,
  };
}

function makePage() {
  const folders = ["0", "1", "2"].map((f) => el("ml-folder", { folderLink: f }));
  const lists = ["0", "1", "2"].map((f) => el("ml-box", { folder: f }));
  const rows = THREADS.map((t) => el("ml-row", { threadLink: t.id }));
  const arts = THREADS.map((t) => el("ml-thread", { thread: t.id, folder: t.folder }));
  const backs = arts.map(() => el("ml-back", {}, { "data-act": "back" }));
  backs.forEach((b) => (b.closest = (sel) => (sel === '[data-act="back"]' ? b : null)));
  const empty = el("ml-read__empty");
  const box = el("ml");
  box.querySelectorAll = (sel) =>
    ({
      "[data-folder-link]": folders,
      ".ml-box[data-folder]": lists,
      "[data-thread-link]": rows,
      ".ml-thread[data-thread]": arts,
    })[sel] || [];
  box.querySelector = (sel) => (sel === '[data-role="empty"]' ? empty : null);
  const root = { querySelector: (sel) => (sel === "[data-mail]" ? box : null) };
  return { root, box, folders, lists, rows, arts, backs, empty };
}

function withBrowser(fn) {
  const saved = {};
  for (const k of ["window", "location", "history", "Element"]) saved[k] = globalThis[k];
  const winListeners = {};
  const stack = [{ state: null, hash: "" }];
  const loc = { pathname: "/p/mail-sample/", search: "", hash: "" };
  const hist = {
    get state() {
      return stack.at(-1).state;
    },
    pushState(state, _t, url) {
      stack.push({ state, hash: url.includes("#") ? url.slice(url.indexOf("#")) : "" });
      loc.hash = stack.at(-1).hash;
    },
    replaceState(state, _t, url) {
      stack[stack.length - 1] = { state, hash: url.includes("#") ? url.slice(url.indexOf("#")) : "" };
      loc.hash = stack.at(-1).hash;
    },
    back() {
      stack.pop();
      loc.hash = stack.at(-1).hash;
      for (const f of winListeners.popstate || []) f({});
    },
    get length() {
      return stack.length;
    },
  };
  globalThis.window = {
    addEventListener: (t, f) => ((winListeners[t] ||= []).push(f)),
    matchMedia: () => ({ matches: true }), // телефон
  };
  globalThis.location = loc;
  globalThis.history = hist;
  globalThis.Element = Object; // любой объект-заглушка — «элемент»
  try {
    fn({ loc, hist });
  } finally {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete globalThis[k];
      else globalThis[k] = v;
    }
  }
}

const visible = (els) => els.filter((e) => !e.hidden).map((e) => e.dataset.thread ?? e.dataset.folder);

test("init: список первой папки, цепочек не видно; без страницы ящика — null", () => {
  assert.equal(init({ querySelector: () => null }), null);
  withBrowser(() => {
    const p = makePage();
    init(p.root);
    assert.ok(p.box.classList.contains("has-js"));
    assert.ok(!p.box.classList.contains("is-reading"));
    assert.deepEqual(visible(p.lists), ["0"]);
    assert.deepEqual(visible(p.arts), []);
    assert.equal(p.empty.hidden, false);
    assert.equal(p.folders[0].getAttribute("aria-current"), "true");
  });
});

test("init: строка → цепочка (адрес #mt-, история), «К списку писем» → назад, фокус на строку", () => {
  withBrowser(({ loc, hist }) => {
    const p = makePage();
    init(p.root);
    const ev = p.rows[1].fire("click");
    assert.ok(ev.defaultPrevented);
    assert.deepEqual(visible(p.arts), ["work"]);
    assert.ok(p.box.classList.contains("is-reading"));
    assert.equal(p.empty.hidden, true);
    assert.equal(p.rows[1].getAttribute("aria-current"), "true");
    assert.equal(loc.hash, "#mt-work");
    assert.equal(hist.length, 2);
    assert.equal(p.arts[1].focused, 1);

    p.box.fire("click", p.backs[1]); // «К списку писем»
    assert.equal(loc.hash, "");
    assert.equal(hist.length, 1);
    assert.deepEqual(visible(p.arts), []);
    assert.ok(!p.box.classList.contains("is-reading"));
    assert.equal(p.rows[1].focused, 1);
  });
});

test("init: цепочка другой папки переключает папку; смена папки закрывает цепочку", () => {
  withBrowser(({ loc }) => {
    const p = makePage();
    init(p.root);
    p.rows[2].fire("click"); // odd — в папке 2
    assert.deepEqual(visible(p.lists), ["2"]);
    assert.equal(p.folders[2].getAttribute("aria-current"), "true");
    assert.equal(p.folders[0].getAttribute("aria-current"), null);
    p.rows[0].fire("click"); // из цепочки в цепочку — без новой записи истории
    assert.deepEqual(visible(p.arts), ["personal"]);
    assert.deepEqual(visible(p.lists), ["0"]);
    p.folders[1].fire("click");
    assert.deepEqual(visible(p.lists), ["1"]);
    assert.deepEqual(visible(p.arts), []);
    assert.equal(loc.hash, "");
  });
});

test("init: открытие по адресу #mt-<id>", () => {
  withBrowser(({ loc }) => {
    loc.hash = "#mt-odd";
    const p = makePage();
    const st = init(p.root);
    assert.deepEqual(st.get(), { folder: "2", thread: "odd" });
    assert.deepEqual(visible(p.arts), ["odd"]);
  });
});
