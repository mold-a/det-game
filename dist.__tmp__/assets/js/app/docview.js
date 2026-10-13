// Просмотр документа-результата (экспертиза, развязка): бланк из сборки
// (html — готовый HTML, FORMATS §0), медиа по data-media, кнопка «Печать».
// Печать: html.print-doc — print.css печатает только этот документ (A4, ч/б).

import { h, insertTrustedHtml } from "./dom.js";
import { T } from "./texts.js";
import { openModal } from "./modal.js";
import { hydrateMedia } from "../core/media.js";

/** Узел документа: { title, html, media } → <div class="doc-view">. */
export function renderDocument(entry, { withPrint = true } = {}) {
  const body = h("div", { class: "doc-view__body doc-text" });
  insertTrustedHtml(body, entry.html ?? "");
  hydrateMedia(body, entry.media ?? [], {
    missingText: T.docs.missingMedia,
    onProgress: (node, loaded, total) => {
      if (total) node.setAttribute("title", T.docs.loadingMedia(Math.round((loaded / total) * 100)));
    },
  });
  const view = h("div", { class: "doc-view" }, body);
  if (withPrint) {
    const btn = h("button", { type: "button", class: "btn btn--secondary no-print" }, T.print);
    btn.addEventListener("click", () => printDocument(view));
    view.appendChild(h("div", { class: "blank__actions no-print" }, btn));
  }
  return view;
}

/** Напечатать один документ: остальное скрывает print.css (html.print-doc). */
export function printDocument(view) {
  const root = document.documentElement;
  view.classList.add("is-printing");
  root.classList.add("print-doc");
  const done = () => {
    root.classList.remove("print-doc");
    view.classList.remove("is-printing");
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  window.print();
  // Некоторые браузеры не шлют afterprint — снимаем режим по таймеру.
  setTimeout(done, 1000);
}

/** Открыть документ в модальном окне. */
export function openDocument(entry) {
  return openModal({
    title: entry.title,
    body: renderDocument(entry),
    className: "modal--doc",
    actions: [{ id: "ok", label: T.close, primary: true }],
  });
}
