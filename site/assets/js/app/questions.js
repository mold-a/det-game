// Вопросы всех типов docs/01 §3 (FORMATS §2.2): поля ввода, участок бланка,
// показ ответа команды. Проверку выполняет вызывающий (main.js / final.js)
// через onCheck — здесь только DOM.

import { h, uid } from "./dom.js";
import { T } from "./texts.js";
import { createOrder } from "./order.js";
import { stampAccepted } from "./stamp.js";
import { mediaUrl } from "../core/media.js";

const TEXT_TYPES = new Set(["text", "time", "date", "number"]);
const INPUT_MODE = { time: "decimal", date: "decimal", number: "numeric", text: "text" };

/**
 * Поле ввода по типу единицы.
 *   spec — вопрос или поле формы: { id, path, type, options?, pool?, items? };
 *   ctx  — { characters: {id: Character}, documents: [{id,title}], labelledBy };
 * → { el, getValue(), setDisabled(b), setInvalid(b), focus() }.
 * getValue(): строка для text/time/date/number/choice/person/document,
 *             массив ID для multi/persons/order.
 */
export function createInput(spec, ctx = {}) {
  const { labelledBy = null, label = null } = ctx;
  if (TEXT_TYPES.has(spec.type)) {
    const input = h("input", {
      class: ["input", spec.type !== "text" && "input--short"],
      type: "text",
      inputmode: INPUT_MODE[spec.type],
      autocomplete: "off",
      autocapitalize: spec.type === "text" ? "off" : null,
      spellcheck: "false",
      placeholder: T.placeholder[spec.type] || null,
      "aria-labelledby": label ? null : labelledBy,
      "aria-label": label,
      id: uid("in"),
    });
    return {
      el: input,
      getValue: () => input.value,
      setDisabled: (b) => (input.disabled = b),
      setInvalid: (b) => input.setAttribute("aria-invalid", b ? "true" : "false"),
      focus: () => input.focus(),
      input,
    };
  }

  if (spec.type === "choice" || spec.type === "multi") {
    return choiceList(spec.options ?? [], spec.type === "multi", spec.path, labelledBy);
  }

  if (spec.type === "person" || spec.type === "persons") {
    return personGrid(spec.pool ?? [], ctx.characters ?? {}, spec.type === "persons", spec.path, labelledBy);
  }

  if (spec.type === "document") {
    const docs = ctx.documents ?? [];
    const select = h(
      "select",
      { class: "select", "aria-labelledby": labelledBy, id: uid("sel") },
      h("option", { value: "" }, docs.length ? T.question.chooseDocument : T.question.noDocuments),
      docs.map((d) => h("option", { value: d.id }, `${d.id} — ${d.title}`)),
    );
    return {
      el: select,
      getValue: () => select.value,
      setDisabled: (b) => (select.disabled = b),
      setInvalid: (b) => select.setAttribute("aria-invalid", b ? "true" : "false"),
      focus: () => select.focus(),
    };
  }

  if (spec.type === "order") {
    const o = createOrder(spec.items ?? [], { labelledBy });
    return { ...o, setInvalid: () => {}, focus: () => o.el.querySelector("button:not(:disabled)")?.focus() };
  }

  throw new Error(`Неизвестный тип ввода: ${spec.type}`);
}

function choiceList(options, multi, name, labelledBy) {
  const inputs = [];
  const list = h(
    "ul",
    { class: "options", role: multi ? "group" : "radiogroup", "aria-labelledby": labelledBy },
    options.map((o) => {
      const input = h("input", { type: multi ? "checkbox" : "radio", name: `opt-${name}`, value: o.id });
      inputs.push(input);
      return h("li", null, h("label", { class: "option" }, input, h("span", null, o.text)));
    }),
  );
  return {
    el: list,
    getValue: () => (multi ? inputs.filter((i) => i.checked).map((i) => i.value) : inputs.find((i) => i.checked)?.value ?? ""),
    setDisabled: (b) => inputs.forEach((i) => (i.disabled = b)),
    setInvalid: (b) => list.setAttribute("aria-invalid", b ? "true" : "false"),
    focus: () => inputs[0]?.focus(),
  };
}

/** Лица: сетка карточек с портретом, если хоть у кого-то есть фото; иначе — список. */
function personGrid(pool, characters, multi, name, labelledBy) {
  const withPhotos = pool.some((id) => characters[id]?.photo?.src);
  if (!withPhotos) {
    const options = pool.map((id) => ({ id, text: characters[id]?.full ?? id }));
    return choiceList(options, multi, name, labelledBy);
  }
  const inputs = [];
  const grid = h(
    "ul",
    { class: "persons", role: multi ? "group" : "radiogroup", "aria-labelledby": labelledBy },
    pool.map((id) => {
      const c = characters[id] ?? { full: id };
      const input = h("input", { type: multi ? "checkbox" : "radio", name: `per-${name}`, value: id, "aria-label": c.full });
      inputs.push(input);
      const photo = h("img", { class: "person__photo", alt: "", loading: "lazy", decoding: "async" });
      if (c.photo?.src) {
        mediaUrl(c.photo).then((url) => {
          if (url) photo.src = url;
          else photo.classList.add("media-missing");
        }, () => photo.classList.add("media-missing"));
      } else {
        photo.classList.add("media-missing");
      }
      return h("li", null, h("label", { class: "person" }, input, photo, h("span", { class: "person__name", "aria-hidden": "true" }, c.full)));
    }),
  );
  return {
    el: grid,
    getValue: () => (multi ? inputs.filter((i) => i.checked).map((i) => i.value) : inputs.find((i) => i.checked)?.value ?? ""),
    setDisabled: (b) => inputs.forEach((i) => (i.disabled = b)),
    setInvalid: (b) => grid.setAttribute("aria-invalid", b ? "true" : "false"),
    focus: () => inputs[0]?.focus(),
  };
}

// ---------------------------------------------------------------- показ ответа

/**
 * Текст значения для разбора и пройденных этапов: канон или нормализованный
 * ответ команды → то, что видит человек (вариант, ФИО, название документа…).
 */
export function displayValue(spec, value, ctx = {}) {
  if (value === null || value === undefined || value === "") return T.final.noAnswer;
  const chars = ctx.characters ?? {};
  const docs = ctx.documents ?? [];
  const ids = (v) => (Array.isArray(v) ? v : String(v).split(",")).filter(Boolean);
  switch (spec.type) {
    case "choice":
      return spec.options?.find((o) => o.id === value)?.text ?? String(value);
    case "multi":
      return ids(value).map((id) => spec.options?.find((o) => o.id === id)?.text ?? id).join("; ");
    case "person":
      return chars[value]?.full ?? String(value);
    case "persons":
      return ids(value).map((id) => chars[id]?.full ?? id).join(", ");
    case "document": {
      const d = docs.find((x) => x.id === value);
      return d ? `${d.id} — ${d.title}` : String(value);
    }
    case "order":
      return ids(value).map((id) => spec.items?.find((i) => i.id === id)?.text ?? id).join(" → ");
    case "date": {
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
      return m ? `${m[3]}.${m[2]}.${m[1]}` : String(value);
    }
    default:
      return String(value);
  }
}

/** Ответ вопроса (канон или ответ команды) в виде списка «поле — значение». */
export function renderAnswer(q, value, ctx = {}, { title = T.question.yourAnswer } = {}) {
  const dl = h("dl", { class: "q__answer" });
  if (q.type === "form") {
    for (const f of q.fields) {
      dl.appendChild(h("dt", null, f.label));
      dl.appendChild(h("dd", null, displayValue(f, value?.[f.id], ctx)));
    }
  } else {
    dl.appendChild(h("dt", null, title));
    dl.appendChild(h("dd", null, displayValue(q, value, ctx)));
  }
  return dl;
}

// ---------------------------------------------------------------- участок бланка

/**
 * renderQuestion(q, ctx) → { el, setBusy(b), showMessage(text, kind), markInvalid(ids), getInputs() }
 *   ctx: {
 *     number,           — «Вопрос 2.1» (строка номера);
 *     unit,             — запись прогресса units[q.path] или undefined;
 *     wrongCount,       — число неверных попыток;
 *     hintsEl,          — блок подсказок (hints.js) или null;
 *     characters, documents,
 *     onCheck(inputs),  — нажата «Проверить»; inputs: raw (форма — {fieldId: raw});
 *     submitLabel,      — подпись кнопки (финал — «Зафиксировать ответ»);
 *     showStatus = true, animateStamp = false, readOnlyValue — показать вместо полей.
 *   }
 */
export function renderQuestion(q, ctx) {
  const promptId = uid("q-prompt");
  const status = ctx.unit?.status ?? "open";
  const solved = status === "solved";
  const closed = status === "closed";
  const isBonus = q.kind === "bonus";

  const head = h(
    "div",
    { class: "q__head" },
    ctx.number ? h("span", { class: "q__no" }, ctx.number) : null,
    isBonus ? h("span", { class: "mark-bonus" }, T.question.bonusMark) : null,
    ctx.showStatus === false ? null : h("span", { class: "q__status" }, T.question.status[status]),
  );

  const article = h(
    "article",
    { class: ["q", solved && "q--solved", closed && "q--closed"], id: `q-${q.path}`, "aria-labelledby": promptId, dataset: { path: q.path } },
    head,
    h("h4", { class: "q__prompt", id: promptId }, q.prompt),
    q.help ? h("p", { class: "q__help" }, q.help) : null,
  );

  const body = h("div", { class: "q__body" });
  article.appendChild(body);

  // Решённый или закрытый вопрос — только ответ (канон или ответ команды).
  if (solved || closed || ctx.readOnlyValue !== undefined) {
    const value = ctx.readOnlyValue !== undefined ? ctx.readOnlyValue : solved ? ctx.unit.canon : ctx.unit.given;
    body.appendChild(renderAnswer(q, value, ctx));
    if (ctx.hintsEl) body.appendChild(ctx.hintsEl);
    if (solved && ctx.stamp !== false) stampAccepted(article, { seed: q.path, animate: Boolean(ctx.animateStamp) });
    return { el: article, setBusy() {}, showMessage() {}, markInvalid() {}, getInputs: () => null };
  }

  // Поля ввода
  const widgets = {};
  if (q.type === "form") {
    const help = h("p", { class: "q__help" }, T.question.formHelp);
    body.appendChild(help);
    const inline = q.fields.every((f) => TEXT_TYPES.has(f.type) && f.type !== "text");
    const wrap = h("div", { class: inline ? "fields-inline" : "fields" });
    for (const f of q.fields) {
      const labelId = uid("f-label");
      const w = createInput(f, { ...ctx, labelledBy: labelId });
      widgets[f.id] = w;
      const isText = TEXT_TYPES.has(f.type);
      if (isText) {
        wrap.appendChild(h("label", { class: "field" }, h("span", { class: "field__label", id: labelId }, f.label), w.el));
      } else {
        wrap.appendChild(h("div", { class: "field", role: "group", "aria-labelledby": labelId }, h("span", { class: "field__label", id: labelId }, f.label), w.el));
      }
      if (f.help) wrap.lastChild.appendChild(h("span", { class: "q__help" }, f.help));
    }
    body.appendChild(wrap);
  } else {
    const w = createInput(q, { ...ctx, labelledBy: promptId });
    widgets[q.id] = w;
    body.appendChild(w.el);
  }

  const msg = h("p", { class: "q__msg", role: "status", "aria-live": "polite" });
  body.appendChild(msg);
  if (ctx.hintsEl) body.appendChild(ctx.hintsEl);

  const checkBtn = h("button", { type: "submit", class: "btn btn--primary" }, ctx.submitLabel ?? T.question.check);
  const actions = h(
    "div",
    { class: "q__actions" },
    checkBtn,
    ctx.hintButton ?? null,
    ctx.wrongCount ? h("span", { class: "q__meta" }, T.question.wrongCount(ctx.wrongCount)) : null,
  );
  // Форма — чтобы Enter в текстовом поле отправлял ответ.
  const form = h("form", { class: "q__form", novalidate: true }, actions);
  body.appendChild(form);

  const getInputs = () => {
    if (q.type === "form") {
      const out = {};
      for (const [id, w] of Object.entries(widgets)) out[id] = w.getValue();
      return out;
    }
    return widgets[q.id].getValue();
  };

  // Enter в любом поле ввода участка = «Проверить».
  body.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.matches("input.input") && !checkBtn.disabled) {
      e.preventDefault();
      checkBtn.click();
    }
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!checkBtn.disabled) ctx.onCheck?.(getInputs());
  });

  return {
    el: article,
    getInputs,
    setBusy(b) {
      checkBtn.disabled = b;
      checkBtn.setAttribute("aria-busy", b ? "true" : "false");
      checkBtn.textContent = b ? T.checking : ctx.submitLabel ?? T.question.check;
      for (const w of Object.values(widgets)) w.setDisabled(b);
    },
    showMessage(text, kind = "info") {
      msg.className = ["q__msg", kind === "error" && "q__msg--error", kind === "format" && "q__msg--format"].filter(Boolean).join(" ");
      msg.textContent = text ?? "";
    },
    markInvalid(ids = []) {
      for (const [id, w] of Object.entries(widgets)) w.setInvalid(ids.includes(id));
      const first = ids.find((id) => widgets[id]);
      if (first) widgets[first].focus();
    },
  };
}

/** Сообщение о формате для невалидного ввода (первое неверное поле). */
export function formatMessage(q, inputs, invalid) {
  if (q.type !== "form") {
    const empty = inputs === "" || inputs === null || (Array.isArray(inputs) && !inputs.length);
    return empty && TEXT_TYPES.has(q.type) ? T.format.empty : T.format[q.type] ?? T.format.empty;
  }
  const f = q.fields.find((x) => x.id === invalid[0]);
  const raw = inputs?.[f?.id];
  const empty = raw === "" || raw === null || raw === undefined || (Array.isArray(raw) && !raw.length);
  if (!f || empty) return T.format.form;
  return T.format[f.type] ?? T.format.form;
}

