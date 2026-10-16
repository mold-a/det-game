// Главный экран «/» (docs/04): первый запуск, текущий этап, вопросы, подсказки,
// переход этапа с окном «Откройте конверт №N» (envelopeAck, F14), пройденные
// этапы свёрнуты, панель документов, журнал баллов, меню, состояния ошибок.

import { h, clear, announce, insertTrustedHtml } from "./dom.js";
import { T } from "./texts.js";
import { openModal } from "./modal.js";
import { createStamp } from "./stamp.js";
import { renderScoreLog } from "./scorelog.js";
import { renderQuestion, formatMessage } from "./questions.js";
import { renderHints, hintButton } from "./hints.js";
import { renderDocsPanel } from "./docs-panel.js";
import { renderHeader } from "./header.js";
import { initPage, loadProgress, renderLoadError, renderShell, renderFatal, rulesCfg, safeLocalStorage } from "./context.js";
import * as S from "../core/state.js";
import {
  startKey,
  openPack,
  checkQuestion,
  wrongHash,
  isStageComplete,
  nextStageKey,
  bonuses,
} from "../core/game.js";
import { b64uEncode } from "../core/crypto.js";
import { makeLabelFor } from "./labels.js";

const ctx = await initPage();

/** Проверка файла прогресса при загрузке: ключ текущего этапа открывает его пакет. */
async function verify(s) {
  try {
    await openPack(s.stage, s.keys[s.stage]);
    return true;
  } catch {
    return false;
  }
}

let game = null; // { state, packs, labEntries, docs }
let header = null;
let views = new Map(); // qpath → { q, n, idx, view }
/** Черновики: незаконченный ввод по пути вопроса, переживает перерисовку страницы. */
const drafts = new Map();
let envelopeShown = false;

/** Запомнить ввод всех открытых вопросов перед перерисовкой. */
function saveDrafts() {
  for (const [path, { view }] of views) {
    const v = view.getInputs?.();
    if (v !== null && v !== undefined) drafts.set(path, v);
  }
}

let running = null;
let again = false;

/**
 * Запуск и перерисовка (в т. ч. по событию storage из другой вкладки).
 * Вызовы не перекрываются: пока идёт загрузка, новые просьбы копятся в один
 * повтор. Рисуем только состояние, которое не изменилось за время загрузки пакетов.
 */
function start() {
  if (running) {
    again = true;
    return running;
  }
  running = (async () => {
    try {
      do {
        again = false;
        await startOnce();
      } while (again);
    } finally {
      running = null;
    }
  })();
  return running;
}

async function startOnce() {
  const state = ctx.store.get();
  if (!state && !ctx.store.corrupt) return renderIntro();
  const res = await loadProgress(ctx, state);
  if (!res.ok) return renderLoadError(ctx, res.code);
  const latest = ctx.store.get();
  if (!latest || S.canonicalJson(latest) !== S.canonicalJson(res.state)) {
    again = true; // за время загрузки прогресс изменился — загрузить ещё раз
    return;
  }
  game = res;
  renderGame();
  await showPendingEnvelope();
}

/** Перечитать прогресс и пакеты после перехода этапа или внешнего изменения. */
async function reload({ focusMain = false } = {}) {
  saveDrafts();
  const res = await loadProgress(ctx);
  if (!res.ok) return renderLoadError(ctx, res.code);
  game = res;
  renderGame();
  if (focusMain) document.getElementById("main")?.focus();
}

// ================================================================== первый запуск

function renderIntro() {
  clear(ctx.mount);
  const input = h("input", { class: "input", type: "text", id: "team", autocomplete: "off", maxlength: "60", placeholder: T.start.teamPlaceholder });
  const msg = h("p", { class: "q__msg q__msg--error", role: "status" });
  const btn = h("button", { type: "submit", class: "btn btn--primary" }, T.start.submit);
  const form = h(
    "form",
    { class: "intro__form", novalidate: true },
    h("label", { class: "field" }, h("span", { class: "field__label" }, T.start.teamLabel), input),
    msg,
    btn,
  );
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const team = input.value.trim();
    if (!team) {
      msg.textContent = T.start.teamRequired;
      input.setAttribute("aria-invalid", "true");
      input.focus();
      return;
    }
    btn.disabled = true;
    btn.textContent = T.envelope.opening;
    try {
      const k1 = b64uEncode(await startKey(ctx.pub));
      ctx.store.update(() =>
        S.newState({
          gameId: ctx.pub.gameId,
          saltsId: ctx.pub.saltsId,
          buildId: ctx.pub.buildId,
          team,
          startedAt: new Date().toISOString(),
          keys: { 1: k1 },
        }),
      );
    } catch {
      renderFatal(ctx, { text: T.errors.pack, reload: true });
      return;
    }
    await start();
    await envelopeModal({ title: T.envelope.first, envelope: 1, ack: false });
  });

  ctx.mount.append(
    h(
      "main",
      { class: "intro", id: "main" },
      h("h1", { class: "intro__title" }, ctx.pub.title),
      ctx.chrome.system ? h("p", { class: "intro__system" }, `${ctx.chrome.system}. ${T.header.caseNo(ctx.chrome.caseNo)}`) : null,
      h("h2", { class: "intro__subtitle" }, T.start.rulesTitle),
      h("ol", { class: "rules" }, T.rules(rulesCfg(ctx.pub)).map((l) => h("li", null, l))),
      ctx.store.persistent ? null : h("p", { class: "notice" }, T.errors.storage),
      form,
    ),
  );
  input.focus();
}

// ================================================================== экран игры

function renderGame() {
  saveDrafts();
  const { state, packs } = game;
  header = renderHeader(ctx, state, { onChange: () => start(), verify, rulesCfg: rulesCfg(ctx.pub) });
  const { main, side } = renderShell(ctx, header.el);
  views = new Map();

  if (!ctx.store.persistent) main.appendChild(h("p", { class: "notice", role: "status" }, T.errors.storage));
  if (state.finished) {
    main.appendChild(h("p", { class: "notice" }, T.final.finished, " ", h("a", { href: "/final/" }, T.final.toResults)));
  }

  const n = state.stage;
  const pack = packs[n];
  const last = n === ctx.pub.stages;
  const titleId = "stage-title";
  const sheet = h(
    "section",
    { class: "sheet", "aria-labelledby": titleId },
    h(
      "div",
      { class: "stage-head" },
      h("h2", { class: "stage-head__title", id: titleId }, T.stage.title(n)),
      h("span", { class: "stage-head__meta" }, T.stage.envelopeOpened(pack.envelope)),
    ),
    renderLetter(pack),
  );

  if (last) {
    sheet.appendChild(
      h(
        "div",
        { class: "q q--final-link" },
        h("p", null, T.final.finalStageText),
        h("div", { class: "q__actions" }, h("a", { class: "btn btn--primary", href: "/final/" }, state.finished ? T.final.toResults : T.final.toFinal)),
      ),
    );
  } else {
    const mand = pack.questions.filter((q) => q.kind === "mandatory");
    sheet.appendChild(h("h3", { class: "group-title" }, T.stage.mandatory));
    for (const q of mand) sheet.appendChild(questionView(pack, q).el);
  }

  // Бонусы: текущего этапа (кроме финального) и неотвеченные прошлых — пока не начат финал.
  const openBonuses = [];
  for (let k = 1; k <= n; k++) {
    if (k === ctx.pub.stages) continue;
    for (const q of bonuses(packs[k])) {
      if (k === n || (!state.units[q.path] && !state.final.started)) openBonuses.push([packs[k], q]);
    }
  }
  if (openBonuses.length) {
    sheet.appendChild(h("h3", { class: "group-title" }, T.stage.bonus));
    for (const [p, q] of openBonuses) sheet.appendChild(questionView(p, q).el);
  }
  main.appendChild(sheet);

  // Пройденные этапы — свёрнуты, с ответами команды.
  for (let k = n - 1; k >= 1; k--) main.appendChild(renderPassed(packs[k]));

  side.appendChild(renderDocsPanel({ docs: game.docs, labEntries: game.labEntries }));
  side.appendChild(renderScoreLog(state, { labelFor }));
}

/** Подпись вопроса для журнала: «вопрос 2.3» (тот же вид на /lab/ и /final/). */
const labelFor = (path) => makeLabelFor(game?.packs)(path);

function questionNumber(pack, q) {
  return T.question.number(pack.n, pack.questions.indexOf(q) + 1);
}

// ------------------------------------------------------------------ письмо

const uiKey = (n) => `detgame:${ctx.pub.gameId}:ui:letter-collapsed:${n}`;

function renderLetter(pack) {
  let collapsed = false;
  try {
    collapsed = safeLocalStorage()?.getItem(uiKey(pack.n)) === "1";
  } catch {
    collapsed = false;
  }
  const body = h("div", { class: "letter__body doc-text" });
  insertTrustedHtml(body, pack.introHtml);
  const toggle = h("span", { class: "letter__toggle-text" }, collapsed ? T.stage.letterShow : T.stage.letterHide);
  const det = h("details", { class: "letter", open: !collapsed }, h("summary", null, T.stage.letter, toggle), body);
  det.addEventListener("toggle", () => {
    toggle.textContent = det.open ? T.stage.letterHide : T.stage.letterShow;
    try {
      safeLocalStorage()?.setItem(uiKey(pack.n), det.open ? "0" : "1");
    } catch {
      /* удобство, не прогресс */
    }
  });
  return det;
}

// ------------------------------------------------------------------ пройденные этапы

function renderPassed(pack) {
  const { state } = game;
  const body = h("div", { class: "passed__body" });
  for (const q of pack.questions) {
    const unit = state.units[q.path];
    if (!unit && q.kind === "bonus") continue; // открытый бонус показан выше
    const v = renderQuestion(q, {
      number: questionNumber(pack, q),
      unit: unit ?? { status: "open" },
      readOnlyValue: unit ? undefined : null,
      characters: pack.characters,
      documents: game.docs,
      stamp: false,
      hintsEl: renderHints(q, state),
    });
    body.appendChild(v.el);
  }
  return h("details", { class: "passed" }, h("summary", null, `${T.stage.passed(pack.n)} — ${T.stage.passedAnswers.toLowerCase()}`), body);
}

// ------------------------------------------------------------------ вопрос

function questionView(pack, q, { animate = false, note = null } = {}) {
  const { state } = game;
  const unit = state.units[q.path];
  const v = renderQuestion(q, {
    number: questionNumber(pack, q),
    unit,
    wrongCount: q.kind === "mandatory" ? S.wrongCount(state, q.path) : 0,
    characters: pack.characters,
    documents: game.docs,
    hintsEl: renderHints(q, state),
    hintButton: hintButton(q, state, ctx.pub.hints.cost, (level, cost) => buyHint(pack, q, level, cost)),
    animateStamp: animate,
    draft: unit ? undefined : drafts.get(q.path),
    onCheck: (inputs) => onCheck(pack, q, inputs),
  });
  if (unit) drafts.delete(q.path);
  if (note) {
    if (unit) v.el.querySelector(".q__body")?.prepend(h("p", { class: ["q__msg", note.kind === "error" && "q__msg--error"], role: "status" }, note.text));
    else v.showMessage(note.text, note.kind);
  }
  views.set(q.path, { pack, q, view: v });
  return v;
}

/** Перерисовать один вопрос, шапку и боковую панель (ввод в других вопросах сохраняется). */
function refresh(pack, q, opts) {
  const prev = views.get(q.path)?.view;
  const kept = prev?.getInputs?.();
  if (kept !== null && kept !== undefined) drafts.set(q.path, kept); // после неверного ответа ввод остаётся
  const old = prev?.el;
  const v = questionView(pack, q, opts);
  if (old?.isConnected) old.replaceWith(v.el);
  header.update(game.state);
  const side = document.querySelector(".side");
  if (side) {
    side.querySelector(".scorelog")?.replaceWith(renderScoreLog(game.state, { labelFor, open: side.querySelector(".scorelog")?.open }));
  }
  return v;
}

function commit(fn) {
  game.state = ctx.store.update(fn);
  return game.state;
}

function buyHint(pack, q, level, cost) {
  commit((s) => S.buyHint(s, q.path, level, cost));
  refresh(pack, q);
  announce(T.question.hintLevel(level));
}

async function onCheck(pack, q, inputs) {
  const entry = views.get(q.path);
  const v = entry.view;
  v.setBusy(true);
  v.showMessage("");
  let r;
  try {
    r = await checkQuestion(q, inputs, ctx.pub);
  } catch {
    v.setBusy(false);
    v.showMessage(T.errors.pack, "error");
    return;
  }
  if (!r.valid) {
    v.setBusy(false);
    v.showMessage(formatMessage(q, inputs, r.invalid), "format");
    v.markInvalid(r.invalid);
    return;
  }

  if (q.kind === "bonus") {
    // «Уже проверяли» решается по свежему состоянию внутри update (другая вкладка могла ответить раньше).
    let already = false;
    commit((s) => {
      already = S.isClosed(s, q.path) || s.final.started || s.finished;
      return S.bonusAnswer(s, q.path, { correct: r.correct, canon: r.canon, given: r.normalized, points: ctx.pub.points.bonus });
    });
    const text = already ? T.result.repeat : r.correct ? T.result.bonusRight(ctx.pub.points.bonus) : T.result.bonusWrong;
    const ok = !already && r.correct;
    refresh(pack, q, { animate: ok, note: { text, kind: already ? "info" : r.correct ? "info" : "error" } });
    announce(text);
    return;
  }

  if (!r.correct) {
    const hash = await wrongHash(q, r.normalized);
    let repeat = false;
    let hadHint = 0;
    commit((s) => {
      repeat = S.wasTried(s, q.path, hash) || S.isClosed(s, q.path);
      hadHint = S.hintLevel(s, q.path);
      return S.maybeAutoHint(S.recordWrong(s, q.path, hash, ctx.pub.penalties.wrongAttempt), q.path, ctx.pub.hints.autoAfterWrong);
    });
    if (repeat) {
      const nv = refresh(pack, q, { note: { text: T.result.repeat, kind: "info" } });
      announce(T.result.repeat);
      nv.el.querySelector("input, select, button")?.focus();
      return;
    }
    const auto = !hadHint && S.hintLevel(game.state, q.path) === 1;
    const text = auto ? `${T.result.wrong} ${T.result.autoHint}` : T.result.wrong;
    const nv = refresh(pack, q, { note: { text, kind: "error" } });
    announce(text);
    nv.el.querySelector("input, select, button")?.focus();
    return;
  }

  // Верно
  commit((s) => S.solve(s, q.path, r.canon));
  if (!isStageComplete(pack, game.state.units) || !pack.saltStage) {
    refresh(pack, q, { animate: true, note: { text: T.result.accepted, kind: "info" } });
    announce(T.result.accepted);
    return;
  }

  // Последний обязательный вопрос этапа: ключ следующего этапа (PBKDF2) и проверка пакета.
  refresh(pack, q, { animate: true, note: { text: T.checking, kind: "info" } });
  try {
    const key = await nextStageKey(pack, game.state.units, ctx.pub);
    await openPack(pack.n + 1, key);
    commit((s) => S.advanceStage(s, pack.n + 1, key));
  } catch {
    renderFatal(ctx, { text: T.errors.pack, reload: true, restart: true });
    return;
  }
  await reload();
  await showPendingEnvelope();
}

// ------------------------------------------------------------------ конверт

async function showPendingEnvelope() {
  const n = S.pendingEnvelope(game.state);
  if (!n || envelopeShown) return;
  const prev = game.packs[n - 1];
  const env = game.packs[n].envelope;
  await envelopeModal({ title: prev?.onComplete || T.result.acceptedEnvelope(env), envelope: env, ack: n });
}

async function envelopeModal({ title, envelope, ack }) {
  envelopeShown = true;
  await openModal({
    title,
    body: [T.envelope.hint],
    stamp: createStamp({ text: T.stamp.envelope(envelope), variant: "envelope", seed: `env${envelope}`, animate: true }),
    actions: [{ id: "ok", label: T.envelope.opened, primary: true }],
    dismissible: false,
  });
  envelopeShown = false;
  if (ack) {
    commit((s) => S.ackEnvelope(s, ack));
    header?.update(game.state);
  }
  document.getElementById("stage-title")?.scrollIntoView({ block: "start" });
  document.getElementById("main")?.focus({ preventScroll: true });
}

// Запуск — в конце модуля: все объявления выше уже инициализированы.
if (ctx) {
  ctx.store.onExternalChange(() => start());
  await start();
}
