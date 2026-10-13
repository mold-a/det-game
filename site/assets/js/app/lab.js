// Лаборатория «/lab/» (docs/04, docs/01 §7, FORMATS §3): форма запроса
// (объект, вид, основание, параметры объекта), предупреждение о штрафе,
// результат-бланк с печатью, архив запросов (lab.log, F15).

import { h, clear, announce } from "./dom.js";
import { T } from "./texts.js";
import { renderScoreLog } from "./scorelog.js";
import { renderDocsPanel } from "./docs-panel.js";
import { renderDocument } from "./docview.js";
import { createInput } from "./questions.js";
import { renderHeader } from "./header.js";
import { initPage, loadProgress, renderLoadError, renderShell, renderFatal, rulesCfg } from "./context.js";
import * as S from "../core/state.js";
import { openPack, receivedDocuments } from "../core/game.js";
import { labCatalog, normalizeParams, labFingerprint, labRequest, labDocTitles } from "../core/lab.js";
import { formatTime } from "./dom.js";

const ctx = await initPage();
let game = null;
let header = null;
let els = {};

if (ctx) {
  ctx.store.onExternalChange(() => start());
  await start();
}

async function verify(s) {
  try {
    await openPack(s.stage, s.keys[s.stage]);
    return true;
  } catch {
    return false;
  }
}

async function start() {
  const res = await loadProgress(ctx);
  if (!res.ok) {
    if (res.code === "none") {
      renderFatal(ctx, { title: T.lab.title, text: T.errors.notStarted });
      ctx.mount.querySelector(".q__actions")?.appendChild(h("a", { class: "btn btn--primary", href: "/" }, T.errors.toStart));
      return;
    }
    return renderLoadError(ctx, res.code);
  }
  game = res;
  render();
}

function labCtx() {
  return { stage: game.state.stage, keys: game.state.keys, packs: game.packs };
}

function render() {
  const { state, packs } = game;
  header = renderHeader(ctx, state, { onChange: () => start(), verify, rulesCfg: rulesCfg(ctx.pub) });
  const { main, side } = renderShell(ctx, header.el);
  const catalog = labCatalog(packs);

  const objectSel = select(T.lab.object, catalog.objects.map((o) => [o.id, o.title]));
  const typeSel = select(T.lab.type, catalog.types.map((t) => [t.id, t.title]));
  const basisSel = select(T.lab.basis, []);
  fillBasis(basisSel.select);
  const paramsBox = h("div", { class: "lab-params" });
  const msg = h("p", { class: "q__msg", role: "status", "aria-live": "polite" });
  const submit = h("button", { type: "submit", class: "btn btn--primary" }, T.lab.submit);
  const result = h("section", { class: "lab-result", "aria-live": "polite", "aria-label": T.lab.result });

  let paramWidgets = [];
  objectSel.select.addEventListener("change", () => {
    clear(paramsBox);
    paramWidgets = [];
    const obj = catalog.objects.find((o) => o.id === objectSel.select.value);
    if (!obj?.params?.length) return;
    const group = h("fieldset", { class: "lab-params__group" }, h("legend", { class: "field__label" }, T.lab.params));
    const row = h("div", { class: "fields-inline" });
    for (const p of obj.params) {
      const w = createInput({ id: p.id, path: `lab.${p.id}`, type: p.type }, { label: p.label });
      paramWidgets.push({ def: p, w });
      row.appendChild(h("label", { class: "field" }, h("span", { class: "field__label", "aria-hidden": "true" }, p.label), w.el));
    }
    group.appendChild(row);
    paramsBox.appendChild(group);
  });

  const form = h(
    "form",
    { class: "lab-form no-print", novalidate: true },
    h("div", { class: "lab-form__grid" }, objectSel.el, typeSel.el, basisSel.el),
    paramsBox,
    h("p", { class: "lab-form__warn" }, T.lab.warn(ctx.pub.penalties.labNoBasis)),
    msg,
    h("div", { class: "q__actions" }, submit),
  );

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.className = "q__msg";
    msg.textContent = "";
    const object = objectSel.select.value;
    const type = typeSel.select.value;
    const basis = basisSel.select.value;
    if (!object || !type || !basis) {
      showMsg(msg, T.lab.required, "format");
      return;
    }
    const obj = catalog.objects.find((o) => o.id === object);
    const raw = paramWidgets.map(({ w }) => w.getValue());
    const norm = normalizeParams(obj, raw, { defaultYear: ctx.pub.defaultYear });
    paramWidgets.forEach(({ def, w }) => w.setInvalid(norm.invalid.includes(def.id)));
    if (norm.params === null) {
      const def = obj.params.find((p) => p.id === norm.invalid[0]);
      const empty = String(raw[obj.params.indexOf(def)] ?? "").trim() === "";
      showMsg(msg, empty ? T.format.form : T.format[def.type] ?? T.format.form, "format");
      return;
    }
    const req = { object, type, basis, params: norm.params };
    submit.disabled = true;
    submit.textContent = T.checking;
    try {
      const fp = await labFingerprint(req);
      const found = await labRequest(req, labCtx());
      const logReq = { ...req, stage: game.state.stage };
      if (found) {
        game.state = ctx.store.update((s) => S.labDone(s, fp, found.entry.doc, logReq));
        game.labResults[fp] = found;
        if (found.entry.doc) game.labEntries[found.entry.doc] = found.entry;
        game.docs = receivedDocuments(game.packs, game.state, labDocTitles(game.labResults));
        showResult(result, found.entry);
        showMsg(msg, found.entry.doc ? T.lab.doneDoc(found.entry.doc) : T.lab.done, "info");
        fillBasis(basisSel.select);
      } else {
        const seen = S.labSeen(game.state, fp);
        game.state = ctx.store.update((s) => S.labRejected(s, fp, ctx.pub.penalties.labNoBasis, logReq));
        clear(result);
        showMsg(msg, seen ? T.lab.noBasisRepeat : T.lab.noBasis, "error");
      }
      announce(msg.textContent);
      updateSide();
    } finally {
      submit.disabled = false;
      submit.textContent = T.lab.submit;
    }
  });

  const archive = h("section", { class: "lab-archive no-print", "aria-labelledby": "lab-archive-title" });
  els = { side, archive, result, basisSel: basisSel.select };

  main.append(
    h(
      "section",
      { class: "sheet lab-sheet", "aria-labelledby": "lab-title" },
      h("div", { class: "stage-head no-print" }, h("h1", { class: "stage-head__title", id: "lab-title" }, T.lab.title), h("a", { href: "/" }, T.lab.back)),
      h("div", { class: "q no-print" }, h("p", { class: "q__help" }, T.lab.intro), form),
      result,
    ),
    archive,
  );
  renderArchive();
  updateSide();
}

function select(label, options) {
  const sel = h("select", { class: "select" }, h("option", { value: "" }, T.lab.choose), options.map(([v, t]) => h("option", { value: v }, t)));
  return { select: sel, el: h("label", { class: "field" }, h("span", { class: "field__label" }, label), sel) };
}

/** Основание — только полученные документы (docs/01 §7). Выбор сохраняется. */
function fillBasis(sel) {
  const cur = sel.value;
  clear(sel);
  sel.appendChild(h("option", { value: "" }, T.lab.choose));
  for (const d of game.docs) sel.appendChild(h("option", { value: d.id }, `${d.id} — ${d.title}`));
  sel.value = cur;
}

function showMsg(el, text, kind) {
  el.className = ["q__msg", kind === "error" && "q__msg--error", kind === "format" && "q__msg--format"].filter(Boolean).join(" ");
  el.textContent = text;
}

function showResult(container, entry) {
  clear(container);
  container.append(h("h2", { class: "lab-result__title" }, entry.title), renderDocument(entry));
  container.scrollIntoView({ block: "start", behavior: "smooth" });
}

function updateSide() {
  const { side } = els;
  clear(side);
  side.append(
    renderDocsPanel({ docs: game.docs, labEntries: game.labEntries, showLab: false }),
    renderScoreLog(game.state, { labelFor: (p) => p }),
  );
  header.update(game.state);
  renderArchive();
}

function renderArchive() {
  const { archive } = els;
  clear(archive);
  archive.appendChild(h("h2", { class: "panel__title", id: "lab-archive-title" }, T.lab.archive));
  const log = game.state.lab.log ?? [];
  if (!log.length) {
    archive.appendChild(h("p", { class: "docs__empty" }, T.lab.archiveEmpty));
    return;
  }
  const catalog = labCatalog(game.packs);
  const title = (list, id) => list.find((x) => x.id === id)?.title ?? id;
  const list = h("ol", { class: "lab-archive__list", reversed: true });
  for (const e of [...log].reverse()) {
    const params = e.params?.length ? ` (${e.params.join(", ")})` : "";
    const res = game.labResults[e.fp];
    const open = e.ok && res ? h("button", { type: "button", class: "btn btn--quiet" }, T.lab.archiveOpen) : null;
    open?.addEventListener("click", () => showResult(els.result, res.entry));
    list.appendChild(
      h(
        "li",
        { class: ["lab-archive__item", e.ok ? "is-done" : "is-rejected"] },
        h("span", { class: "lab-archive__time" }, formatTime(e.t)),
        h(
          "span",
          { class: "lab-archive__what" },
          `${title(catalog.objects, e.object)} — ${title(catalog.types, e.type).toLowerCase()}; ${T.lab.basis.toLowerCase()} ${e.basis}${params}`,
        ),
        h("span", { class: "lab-archive__status" }, e.ok ? (e.doc ? `${T.lab.archiveDone}: ${e.doc}` : T.lab.archiveDone) : T.lab.archiveRejected),
        open,
      ),
    );
  }
  archive.appendChild(list);
}
