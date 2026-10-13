// Хронология (тип order, docs/04): перетаскивание карточек мышью и пальцем
// (Pointer Events) плюс кнопки «Выше»/«Ниже» для клавиатуры и экранных дикторов.
// Карточки приходят уже перемешанными сборщиком (FORMATS §2.2) — показываем как есть.

import { h, announce } from "./dom.js";
import { T } from "./texts.js";

/**
 * createOrder(items, { labelledBy, disabled }) → { el, getValue(), setDisabled(b) }
 *   items: [{ id, text }]; getValue() → массив ID в текущем порядке.
 */
export function createOrder(items, { labelledBy = null, disabled = false } = {}) {
  const list = h("ol", { class: "order", "aria-labelledby": labelledBy });
  let isDisabled = disabled;

  for (const it of items) list.appendChild(makeItem(it));
  refresh();

  function makeItem(it) {
    const up = h("button", { type: "button", class: "order__move", "aria-label": `${T.question.moveUp}: ${it.text}` }, "↑");
    const down = h("button", { type: "button", class: "order__move", "aria-label": `${T.question.moveDown}: ${it.text}` }, "↓");
    const li = h(
      "li",
      { class: "order__item", dataset: { id: it.id } },
      h("span", { class: "order__text" }, it.text),
      h("span", { class: "order__moves" }, up, down),
    );
    up.addEventListener("click", () => move(li, -1, up));
    down.addEventListener("click", () => move(li, +1, down));
    li.addEventListener("pointerdown", (e) => startDrag(e, li));
    return li;
  }

  function move(li, dir, btn) {
    if (isDisabled) return;
    const sib = dir < 0 ? li.previousElementSibling : li.nextElementSibling;
    if (!sib) return;
    if (dir < 0) list.insertBefore(li, sib);
    else list.insertBefore(sib, li);
    refresh();
    const items = Array.from(list.children);
    announce(T.question.moved(items.indexOf(li) + 1, items.length));
    // Фокус остаётся на той же кнопке; если она стала недоступна — на соседней.
    if (btn.disabled) btn.parentElement.querySelector("button:not(:disabled)")?.focus();
    else btn.focus();
  }

  function refresh() {
    const all = Array.from(list.children);
    all.forEach((li, i) => {
      const [up, down] = li.querySelectorAll(".order__move");
      up.disabled = isDisabled || i === 0;
      down.disabled = isDisabled || i === all.length - 1;
    });
    list.classList.toggle("is-disabled", isDisabled);
  }

  // --- перетаскивание: карточка следует за указателем, соседи раздвигаются
  function startDrag(e, li) {
    if (isDisabled || e.button > 0 || e.target.closest("button")) return;
    e.preventDefault();
    li.setPointerCapture?.(e.pointerId);
    li.classList.add("is-dragging");
    const startY = e.clientY;
    const startTop = li.offsetTop;
    const follow = (y) => {
      // Видимое положение = положение в раскладке + сдвиг: карточка остаётся под указателем.
      li.style.transform = `translateY(${y - startY - (li.offsetTop - startTop)}px)`;
    };

    function onMove(ev) {
      const y = ev.clientY;
      const siblings = Array.from(list.children).filter((n) => n !== li);
      const before = siblings.find((n) => {
        const r = n.getBoundingClientRect();
        return y < r.top + r.height / 2;
      });
      if (before) {
        if (before !== li.nextElementSibling) list.insertBefore(li, before);
      } else if (li !== list.lastElementChild) {
        list.appendChild(li);
      }
      follow(y);
    }
    function onUp() {
      li.classList.remove("is-dragging");
      li.style.transform = "";
      li.removeEventListener("pointermove", onMove);
      li.removeEventListener("pointerup", onUp);
      li.removeEventListener("pointercancel", onUp);
      refresh();
      const all = Array.from(list.children);
      announce(T.question.moved(all.indexOf(li) + 1, all.length));
    }
    li.addEventListener("pointermove", onMove);
    li.addEventListener("pointerup", onUp);
    li.addEventListener("pointercancel", onUp);
  }

  return {
    el: list,
    getValue: () => Array.from(list.children).map((li) => li.dataset.id),
    setDisabled(b) {
      isDisabled = b;
      refresh();
    },
  };
}
