// Подсказки (docs/01 §5): три уровня, строго по порядку, цены из public.json,
// подтверждение с ценой, купленные видны до конца игры. Автоподсказка уровня 1
// открывается бесплатно после N ошибок (state.maybeAutoHint) — здесь только показ.
// У бонусных и финальных вопросов подсказок нет.

import { h } from "./dom.js";
import { T } from "./texts.js";
import { confirmDialog } from "./modal.js";
import { hintLevel } from "../core/state.js";

/** Блок открытых подсказок или null. */
export function renderHints(q, state) {
  const level = hintLevel(state, q.path);
  if (!level || !q.hints?.length) return null;
  return h(
    "ol",
    { class: "hints", "aria-label": T.question.hintsOpened },
    q.hints.slice(0, level).map((text, i) =>
      h("li", { class: "hints__item" }, h("span", { class: "hints__level" }, T.question.hintLevel(i + 1)), text),
    ),
  );
}

/**
 * Кнопка «Подсказка (−N)» следующего уровня или null (бонус, решён, все открыты).
 * onBuy(level, cost) вызывается после подтверждения.
 */
export function hintButton(q, state, costs, onBuy) {
  if (q.kind !== "mandatory" || !q.hints?.length) return null;
  if (state.units[q.path]?.status === "solved") return null;
  const level = hintLevel(state, q.path) + 1;
  if (level > q.hints.length) return h("span", { class: "q__meta" }, T.question.hintsAll);
  const cost = costs[level - 1];
  if (typeof cost !== "number") return null;
  const btn = h("button", { type: "button", class: "btn btn--secondary" }, T.question.hintButton(cost));
  btn.addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: T.question.hintConfirmTitle,
      text: T.question.hintConfirm(level, cost),
      ok: T.question.hintOpen(cost),
    });
    if (ok) onBuy(level, cost);
  });
  return btn;
}
