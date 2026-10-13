// Панель «Документы дела» (docs/04): полученные документы — ID, название,
// отметка «бумага» / «онлайн» / «экспертиза». Онлайн-документы — ссылка на
// страницу, результаты экспертиз — открываются в окне. Кнопка «Лаборатория».

import { h, clear } from "./dom.js";
import { T } from "./texts.js";
import { openDocument } from "./docview.js";
import { alertDialog } from "./modal.js";

export const LAB_HREF = "/lab/";

/**
 * renderDocsPanel({ docs, labEntries, labHref, showLab }) → <section class="panel">
 *   docs       — receivedDocuments(...) из core/game.js;
 *   labEntries — { docId: entry } восстановленные результаты экспертиз.
 */
export function renderDocsPanel({ docs, labEntries = {}, labHref = LAB_HREF, showLab = true }) {
  const titleId = "docs-panel-title";
  const list = h("ul", { class: "docs" });
  fill(list, docs, labEntries);
  return h(
    "section",
    { class: "panel docs-panel", "aria-labelledby": titleId },
    h("h2", { class: "panel__title", id: titleId }, T.docs.title),
    list,
    showLab ? h("a", { class: "btn btn--secondary btn--block", href: labHref }, T.docs.lab) : null,
  );
}

function fill(list, docs, labEntries) {
  clear(list);
  if (!docs.length) {
    list.appendChild(h("li", { class: "docs__empty" }, T.docs.empty));
    return;
  }
  for (const d of docs) {
    const parts = [
      h("span", { class: "docs__id" }, d.id),
      h("span", { class: "docs__title" }, d.title),
      h("span", { class: "docs__kind" }, T.docs.kind[d.kind] ?? ""),
    ];
    let row;
    if (d.kind === "online" && d.link) {
      row = h("a", { class: "docs__link", href: d.link, target: "_blank", rel: "noopener" }, parts);
    } else if (d.kind === "lab") {
      row = h("button", { type: "button", class: "docs__link", "aria-label": `${T.docs.open(d.id)}: ${d.title}` }, parts);
      row.addEventListener("click", () => {
        const entry = labEntries[d.id];
        if (entry) openDocument(entry);
        else alertDialog({ title: d.title, text: T.docs.notRestored });
      });
    } else {
      row = h("div", { class: "docs__row", title: T.docs.paperHint }, parts);
    }
    list.appendChild(h("li", { class: "docs__item" }, row));
  }
}
