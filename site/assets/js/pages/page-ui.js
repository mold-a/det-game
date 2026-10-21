// Общий интерактив вымышленных страниц (REDESIGN-2026-10 §4.1): каждый элемент что-то делает.
//
//   [data-dialog-text]  окно сервиса: «Чтобы подписаться, войдите в «Круг»» и кнопка «Понятно»
//                       (data-dialog-title — бренд, data-dialog-heading — заголовок внутри; формы входа нет)
//   [data-zoom]         фото крупно (внутри кнопки — img или заглушка .ph; src читается в момент нажатия,
//                       поэтому работает и для зашифрованных медиа, которые подставляются позже)
//   [data-tabs]         вкладки role=tab/tabpanel со стрелками, Home/End
//   [data-toggle=id]    свернуть/развернуть блок #id (aria-expanded)
//   [data-sections]     разделы сайта по адресу #<id> (site)
//   [data-people-search] поиск людей по списку (главная соцсети)
//   [data-print], [data-top]  печать и «наверх»
//
// Подключается и открытыми страницами (open.js → init(document)), и закрытыми (shell.js → init(#page-content)).
// Окна — нативный <dialog> (фокус внутри, Esc, возврат фокуса на кнопку); без showModal — запасной вариант.

import { paragraphs, nextTabIndex, sectionFromHash, filterNames } from "../core/pageui.js";

const TEXT = {
  ok: "Понятно",
  close: "Закрыть",
  found: (n) => `Найдено: ${n}`,
};

const native = typeof HTMLDialogElement === "function" && typeof HTMLDialogElement.prototype.showModal === "function";
const reduced = () => !!globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

let dialogSeq = 0;

function makeDialog(className, label) {
  const dlg = document.createElement("dialog");
  dlg.className = className;
  if (label) dlg.setAttribute("aria-label", label);
  return dlg;
}

function showDialog(dlg, opener, focusEl) {
  dlg._opener = opener || null;
  if (native) {
    if (!dlg.open) dlg.showModal();
  } else {
    dlg.setAttribute("open", "");
    dlg.setAttribute("role", "dialog");
    dlg.setAttribute("aria-modal", "true");
    dlg.classList.add("is-fallback-open");
  }
  document.documentElement.classList.add("svc-lock");
  focusEl?.focus();
}

function closeDialog(dlg) {
  if (native && dlg.open) dlg.close();
  else if (!native) {
    dlg.removeAttribute("open");
    dlg.classList.remove("is-fallback-open");
    afterClose(dlg);
  }
}

function afterClose(dlg) {
  if (!document.querySelector("dialog[open]")) document.documentElement.classList.remove("svc-lock");
  const op = dlg._opener;
  dlg._opener = null;
  if (op && document.contains(op)) op.focus();
}

function wireDialog(dlg) {
  dlg.addEventListener("close", () => afterClose(dlg));
  dlg.addEventListener("click", (ev) => {
    if (ev.target === dlg) closeDialog(dlg); // нажатие на затемнение
  });
  dlg.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !native) closeDialog(dlg);
  });
  document.body.append(dlg);
}

/** Окно сервиса: бренд, необязательный заголовок, абзацы, «Понятно». Возвращает dialog. */
export function openServiceDialog({ title = "", heading = "", text = "", opener = null } = {}) {
  let dlg = document.querySelector("dialog.svc-dialog");
  if (!dlg) {
    dlg = makeDialog("svc-dialog");
    wireDialog(dlg);
  }
  const id = `svc-dialog-${++dialogSeq}`;
  const box = document.createElement("div");
  box.className = "svc-dialog__box";
  const brand = document.createElement("p");
  brand.className = "svc-dialog__brand";
  brand.id = `${id}-brand`;
  brand.textContent = title;
  box.append(brand);
  let labelId = brand.id;
  if (heading) {
    const h = document.createElement("h2");
    h.className = "svc-dialog__h";
    h.id = `${id}-h`;
    h.textContent = heading;
    box.append(h);
    labelId = `${brand.id} ${h.id}`;
  }
  const body = document.createElement("div");
  body.className = "svc-dialog__text";
  for (const p of paragraphs(text)) {
    const el = document.createElement("p");
    el.textContent = p;
    body.append(el);
  }
  const ok = document.createElement("button");
  ok.type = "button";
  ok.className = "svc-dialog__ok";
  ok.textContent = TEXT.ok;
  ok.addEventListener("click", () => closeDialog(dlg));
  box.append(body, ok);
  dlg.replaceChildren(box);
  dlg.setAttribute("aria-labelledby", labelId);
  showDialog(dlg, opener, ok);
  return dlg;
}

/** Фото крупно: копия изображения (или заглушки) из кнопки, подпись, «Закрыть». */
export function openZoom(button) {
  let dlg = document.querySelector("dialog.svc-zoom");
  if (!dlg) {
    dlg = makeDialog("svc-zoom", "Фото");
    wireDialog(dlg);
  }
  const frame = document.createElement("div");
  frame.className = "svc-zoom__frame";
  const media = document.createElement("div");
  media.className = "svc-zoom__media";
  const img = button.querySelector("img");
  if (img && img.getAttribute("src") && !img.classList.contains("media-missing")) {
    const big = document.createElement("img");
    big.className = "svc-zoom__img";
    big.src = img.currentSrc || img.src;
    big.alt = img.alt || button.dataset.caption || "";
    media.append(big);
  } else {
    const ph = button.querySelector(".ph")?.cloneNode(true);
    if (ph) {
      ph.classList.add("svc-zoom__ph");
      media.append(ph);
    }
  }
  const cap = document.createElement("p");
  cap.className = "svc-zoom__caption";
  cap.textContent = button.dataset.caption || "";
  cap.hidden = !cap.textContent;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "svc-zoom__close";
  close.setAttribute("aria-label", TEXT.close);
  close.textContent = "×";
  close.addEventListener("click", () => closeDialog(dlg));
  frame.append(media, cap, close);
  dlg.replaceChildren(frame);
  showDialog(dlg, button, close);
  return dlg;
}

function setupTabs(box) {
  const tabs = Array.from(box.querySelectorAll('[role="tab"]'));
  if (!tabs.length) return;
  const panels = tabs.map((t) => box.querySelector(`#${CSS.escape(t.getAttribute("aria-controls"))}`));
  const select = (i, focus) => {
    tabs.forEach((t, k) => {
      const on = k === i;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.classList.toggle("is-current", on);
      t.tabIndex = on ? 0 : -1;
      if (panels[k]) panels[k].hidden = !on;
    });
    if (focus) tabs[i].focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => select(i, false));
    t.addEventListener("keydown", (ev) => {
      const next = nextTabIndex(ev.key, i, tabs.length);
      if (next === null) return;
      ev.preventDefault();
      select(next, true);
    });
  });
  box.classList.add("is-ready");
  select(Math.max(0, tabs.findIndex((t) => t.getAttribute("aria-selected") === "true")), false);
}

function setupSections(box) {
  const secs = Array.from(box.querySelectorAll("[data-section]"));
  if (!secs.length) return;
  const ids = secs.map((s) => s.dataset.section);
  const links = Array.from(box.querySelectorAll("[data-section-link]"));
  const show = (id, moved) => {
    secs.forEach((s) => (s.hidden = s.dataset.section !== id));
    links.forEach((a) => {
      const on = a.dataset.sectionLink === id;
      a.classList.toggle("is-current", on && a.classList.contains("st-nav__link"));
      if (a.classList.contains("st-nav__link")) {
        if (on) a.setAttribute("aria-current", "page");
        else a.removeAttribute("aria-current");
      }
    });
    if (moved) {
      const sec = secs.find((s) => s.dataset.section === id);
      box.scrollIntoView({ block: "start", behavior: reduced() ? "auto" : "smooth" });
      sec?.focus({ preventScroll: true });
    }
  };
  const fromHash = () => sectionFromHash(location.hash, ids, ids[0]);
  box.classList.add("is-ready");
  show(fromHash(), false);
  window.addEventListener("hashchange", () => show(fromHash(), true));
  // Повторное нажатие на ссылку текущего раздела: адрес не меняется — вернуть наверх раздела.
  links.forEach((a) =>
    a.addEventListener("click", () => {
      if (a.dataset.sectionLink === fromHash() && (location.hash === `#${a.dataset.sectionLink}` || (!location.hash && a.dataset.sectionLink === ids[0]))) {
        show(a.dataset.sectionLink, true);
      }
    }),
  );
}

function setupPeopleSearch(box) {
  const input = box.querySelector('[data-role="q"]');
  const items = Array.from(box.querySelectorAll(".kr-person"));
  if (!input) return;
  const count = box.querySelector('[data-role="count"]');
  const empty = box.querySelector('[data-role="empty"]');
  const clear = box.querySelector('[data-role="clear"]');
  const names = items.map((el) => el.dataset.name || "");
  const apply = () => {
    const ok = filterNames(names, input.value);
    items.forEach((el, i) => (el.hidden = !ok[i]));
    const n = ok.filter(Boolean).length;
    const active = input.value.trim() !== "";
    if (count) count.textContent = active ? TEXT.found(n) : "";
    if (empty) empty.hidden = n > 0;
    if (clear) clear.hidden = !active;
  };
  input.addEventListener("input", apply);
  clear?.addEventListener("click", () => {
    input.value = "";
    apply();
    input.focus();
  });
  if (location.hash === "#search") input.focus({ preventScroll: false });
  apply();
}

/** Подключить интерактив во всём root (повторный вызов на тот же root — без эффекта). */
export function init(root = document) {
  const host = root === document ? document.body : root;
  if (!host || host.dataset.uiReady) return;
  host.dataset.uiReady = "1";

  root.addEventListener("click", (ev) => {
    const t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    const dlg = t.closest("[data-dialog-text]");
    if (dlg) {
      ev.preventDefault();
      openServiceDialog({
        title: dlg.dataset.dialogTitle || "",
        heading: dlg.dataset.dialogHeading || "",
        text: dlg.dataset.dialogText || "",
        opener: dlg,
      });
      return;
    }
    const zoom = t.closest("[data-zoom]");
    if (zoom) {
      ev.preventDefault();
      openZoom(zoom);
      return;
    }
    const tog = t.closest("[data-toggle]");
    if (tog) {
      const target = root.querySelector(`#${CSS.escape(tog.dataset.toggle)}`);
      if (target) {
        const open = tog.getAttribute("aria-expanded") !== "true";
        tog.setAttribute("aria-expanded", open ? "true" : "false");
        target.hidden = !open;
      }
      return;
    }
    if (t.closest("[data-print]")) {
      ev.preventDefault();
      globalThis.print?.();
      return;
    }
    if (t.closest("[data-top]")) {
      ev.preventDefault();
      globalThis.scrollTo({ top: 0, behavior: reduced() ? "auto" : "smooth" });
    }
  });

  root.querySelectorAll("[data-tabs]").forEach(setupTabs);
  root.querySelectorAll("[data-sections]").forEach(setupSections);
  root.querySelectorAll("[data-people-search]").forEach(setupPeopleSearch);
}
