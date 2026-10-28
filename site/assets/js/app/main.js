// Главный экран «/» (docs/04): первый запуск, текущий этап, вопросы, подсказки,
// переход этапа с окном «Откройте конверт №N» (envelopeAck, F14), пройденные
// этапы свёрнуты, карточка лаборатории, журнал баллов, меню, состояния ошибок.

import { h, clear, announce, insertTrustedHtml } from "./dom.js";
import { T } from "./texts.js";
import { openModal, confirmDialog } from "./modal.js";
import { createStamp, createSeal } from "./stamp.js";
import { renderScoreLog } from "./scorelog.js";
import { renderQuestion, formatMessage } from "./questions.js";
import { renderHints, hintButton } from "./hints.js";
import { prismMark } from "./prism.js";
import { LAB_HREF } from "./menu.js";
import { renderHeader } from "./header.js";
import { initPage, loadProgress, renderLoadError, renderShell, renderFatal, rulesCfg, safeLocalStorage } from "./context.js";
import * as S from "../core/state.js";
import { stageFlow, pendingBonuses, viewStage, finalReady } from "../core/flow.js";
import {
  startKey,
  openPack,
  checkQuestion,
  wrongHash,
  isStageComplete,
  nextStageKey,
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
/** Что показать на вопросе после перерисовки страницы: { animate, note } по пути вопроса (расходуется один раз). */
const effects = new Map();
/** Этап, на котором экран удерживается до «Конверт вскрыт» (после последнего бонуса показываем его результат). */
let holdStage = null;
/** Пройденные этапы, раскрытые пользователем. */
const openPassed = new Set();

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
  // Ярлык на обложке: «Название команды» вписывается, как на наклейке папки.
  const form = h(
    "form",
    { class: "intro__form folder__label", novalidate: true },
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

  // Обложка папки «Дело №» (docs/05 §1): картон, скрепка, тесёмки, штамп, ярлык.
  const folder = h(
    "section",
    { class: "folder", "aria-labelledby": "intro-title" },
    h("span", { class: "folder__clip", "aria-hidden": "true" }),
    h("span", { class: "folder__ties", "aria-hidden": "true" }, h("span", { class: "folder__tie" }), h("span", { class: "folder__tie folder__tie--low" })),
    h(
      "div",
      { class: "folder__head" },
      ctx.chrome.department ? h("p", { class: "folder__dept" }, ctx.chrome.department) : null,
      ctx.chrome.system ? h("p", { class: "folder__system" }, ctx.chrome.system) : null,
    ),
    h(
      "p",
      { class: "folder__case" },
      h("span", { class: "folder__case-word" }, T.cover.caseWord),
      " ",
      h("span", { class: "folder__case-no" }, ctx.chrome.caseNo),
    ),
    h("h1", { class: "folder__title intro__title", id: "intro-title" }, ctx.pub.title),
    h("div", { class: "folder__stamp" }, createStamp({ text: T.cover.dsp, variant: "dsp", seed: "dsp" })),
    h(
      "dl",
      { class: "folder__lines", "aria-hidden": "true" },
      T.cover.lines.map((l) => [h("dt", null, l), h("dd", null)]),
    ),
    form,
  );

  ctx.mount.append(
    h(
      "main",
      { class: "intro intro--cover", id: "main" },
      folder,
      h(
        "section",
        { class: "memo", "aria-labelledby": "memo-title" },
        h("h2", { class: "memo__title intro__subtitle", id: "memo-title" }, T.start.rulesTitle),
        h("ol", { class: "rules" }, T.rules(rulesCfg(ctx.pub)).map((l) => h("li", null, l))),
        ctx.store.persistent ? null : h("p", { class: "notice" }, T.errors.storage),
      ),
    ),
  );
  input.focus();
}

// ================================================================== экран игры

function renderGame() {
  saveDrafts();
  const { state, packs } = game;
  header = renderHeader(ctx, state, { onChange: () => start(), verify, rulesCfg: rulesCfg(ctx.pub), viewOf: (s) => holdStage ?? viewStage(s, game.packs) });
  const { main, side } = renderShell(ctx, header.el);
  views = new Map();

  if (!ctx.store.persistent) main.appendChild(h("p", { class: "notice", role: "status" }, T.errors.storage));
  if (state.finished) {
    main.appendChild(h("p", { class: "notice" }, T.final.finished, " ", h("a", { href: "/final/" }, T.final.toResults)));
  }

  // Экран остаётся на пройденном этапе, пока не отвечены (или не пропущены) его бонусы: до окна «Откройте конверт».
  const n = holdStage ?? viewStage(state, packs);
  const bonusPhase = n < state.stage;
  const pack = packs[n];
  const last = n === ctx.pub.stages;
  const titleId = "stage-title";
  main.appendChild(
    h(
      "div",
      { class: "stage-head stage-band" },
      h("h2", { class: "stage-head__title", id: titleId }, T.stage.title(n)),
      h("span", { class: "stage-head__meta" }, T.stage.envelopeOpened(pack.envelope)),
    ),
  );
  main.appendChild(renderLetter(pack));

  const sheet = h(
    "section",
    { class: "sheet sheet--form", "aria-labelledby": titleId },
    h("p", { class: "sheet__caption" }, h("span", null, T.stage.formTitle), h("span", { class: "sheet__caption-no" }, T.header.caseNo(ctx.chrome.caseNo))),
  );

  if (!S.questionsOpened(state, n)) {
    // Вопросы скрыты за кнопкой, пока команда не изучит документы конверта.
    sheet.appendChild(renderGate(n));
  } else {
    fillQuestions(sheet, state, packs, n, last, bonusPhase);
  }
  main.appendChild(sheet);

  // Пройденные этапы — свёрнуты, с ответами команды.
  for (let k = n - 1; k >= 1; k--) main.appendChild(renderPassed(packs[k]));

  if (!S.labClosed(state)) side.appendChild(renderLabCard(state));
  side.appendChild(renderScoreLog(state, { labelFor }));
}

/**
 * Вопросы этапа по одному (docs/01 «Поток этапа»): решённые остаются выше со штампом, текущий — с полем ввода,
 * остальные скрыты вовсе. Бонусы — после последнего обязательного, тоже по одному.
 */
function fillQuestions(sheet, state, packs, n, last, bonusPhase) {
  const pack = packs[n];
  // Последний этап: обязательные вопросы (если есть) — здесь, по обычным правилам; бонусы и финальные — на /final/.
  // «Перейти к финалу» — после последнего обязательного (как переход к конверту), без обязательных — сразу.
  const flow = stageFlow(pack, state.units, { bonuses: !last });
  if (flow.mandatory.shown.length) {
    sheet.appendChild(h("h3", { class: "group-title" }, T.stage.mandatory));
    for (const q of flow.mandatory.shown) sheet.appendChild(questionView(pack, q).el);
    if (flow.mandatory.hidden) sheet.appendChild(lockedRow());
  }
  if (flow.bonus.shown.length) {
    sheet.appendChild(h("h3", { class: "group-title" }, T.stage.bonus));
    for (const q of flow.bonus.shown) sheet.appendChild(questionView(pack, q).el);
    if (flow.bonus.hidden) sheet.appendChild(lockedRow());
  }
  if (last) {
    if (finalReady(pack, state)) sheet.appendChild(finalLink(state, flow.mandatory.shown.length > 0));
    return;
  }
  if (bonusPhase && pendingBonuses(pack, state).length) {
    const next = packs[pack.n + 1];
    const skip = h("button", { type: "button", class: "btn btn--secondary bonus-skip__btn" }, T.stage.skipBonuses(next?.envelope ?? pack.n + 1));
    skip.addEventListener("click", () => showPendingEnvelope({ skip: true }));
    sheet.appendChild(h("div", { class: "bonus-skip" }, h("p", { class: "bonus-skip__hint" }, T.stage.bonusPhase(pack.n)), skip));
  }
}

/** Блок «Перейти к финалу» последнего этапа; afterMandatory — над ним решённые обязательные вопросы этапа. */
function finalLink(state, afterMandatory) {
  return h(
    "div",
    { class: "q q--final-link" },
    h("p", null, afterMandatory && !state.finished ? T.final.finalReadyText : T.final.finalStageText),
    h("div", { class: "q__actions" }, h("a", { class: "btn btn--primary final-link__go", href: "/final/" }, state.finished ? T.final.toResults : T.final.toFinal)),
  );
}

/** Строка вместо скрытых вопросов: ни заголовка, ни числа — только напоминание о порядке. */
function lockedRow() {
  return h("p", { class: "q-locked" }, T.stage.nextLocked);
}

/** Кнопка «Перейти к вопросам» с подписью; подтверждение — окно системы. */
function renderGate(n) {
  const btn = h("button", { type: "button", class: "btn btn--primary gate__btn" }, T.stage.gate);
  btn.addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: T.stage.gateConfirmTitle(n),
      text: T.stage.gateConfirm,
      ok: T.stage.gateConfirmOk,
    });
    if (!ok) return;
    commit((s) => S.openQuestions(s, n));
    renderGame();
    announce(T.stage.gateOpened(n));
    const sheet = document.querySelector(".sheet--form");
    sheet?.setAttribute("tabindex", "-1");
    sheet?.scrollIntoView({ block: "start" });
    sheet?.focus({ preventScroll: true });
  });
  return h(
    "div",
    { class: "gate" },
    btn,
    h("p", { class: "gate__hint" }, T.stage.gateHint),
  );
}

/** Карточка лаборатории в правой колонке: переход на сайт центра в той же вкладке. */
function renderLabCard(state) {
  const log = state.lab.log ?? [];
  const ok = log.filter((e) => e.ok).length;
  return h(
    "section",
    { class: "labcard", "aria-labelledby": "labcard-title" },
    h(
      "div",
      { class: "labcard__head" },
      prismMark({ className: "prism-mark labcard__mark" }),
      h("h2", { class: "labcard__title", id: "labcard-title" }, T.lab.cardTitle(ctx.chrome.labName)),
    ),
    h("p", { class: "labcard__text" }, T.lab.cardText),
    h("p", { class: "labcard__stats" }, T.lab.cardStats(log.length, ok)),
    h("a", { class: "btn btn--secondary btn--block labcard__go", href: LAB_HREF }, T.lab.cardGo, h("span", { class: "labcard__arrow", "aria-hidden": "true" }, "→")),
  );
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
  const text = h("div", { class: "letter__text doc-text" });
  insertTrustedHtml(text, pack.introHtml);
  // Лист бумаги (docs/05 §1): гриф и номер экземпляра сверху, текст письма PT Serif с полями.
  const body = h(
    "div",
    { class: "letter__body" },
    h("p", { class: "letter__grif" }, h("span", { class: "letter__grif-mark" }, T.cover.dsp), h("span", null, T.stage.letterCopy(pack.n))),
    text,
  );
  const toggle = h("span", { class: "letter__toggle-text" }, collapsed ? T.stage.letterShow : T.stage.letterHide);
  const det = h(
    "details",
    { class: "letter paper", open: !collapsed },
    h("summary", null, h("span", { class: "letter__clip", "aria-hidden": "true" }), h("span", { class: "letter__label" }, T.stage.letter), toggle),
    body,
  );
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
  const flow = stageFlow(pack, state.units);
  const pending = pendingBonuses(pack, state);
  const visible = new Set([...flow.mandatory.shown, ...flow.bonus.shown].map((q) => q.path));
  const body = h("div", { class: "passed__body" });
  for (const q of pack.questions) {
    if (!visible.has(q.path)) continue;
    const unit = state.units[q.path];
    if (!unit && q.kind === "bonus") {
      // Неотвеченный бонус прошлого этапа (пропущен или остался от старого сохранения): по одному, в своём этапе.
      if (pending.includes(q)) body.appendChild(questionView(pack, q).el);
      continue;
    }
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
  if (pending.length && flow.bonus.hidden) body.appendChild(lockedRow());
  const title = `${T.stage.passed(pack.n)} — ${T.stage.passedAnswers.toLowerCase()}`;
  const det = h(
    "details",
    { class: ["passed", pending.length && "passed--bonus"], open: pending.length > 0 || openPassed.has(pack.n) },
    h("summary", null, pending.length ? `${title}, ${T.stage.passedBonus}` : title),
    body,
  );
  det.addEventListener("toggle", () => {
    if (det.open) openPassed.add(pack.n);
    else openPassed.delete(pack.n);
  });
  return det;
}

// ------------------------------------------------------------------ вопрос

function questionView(pack, q, opts = {}) {
  const fx = effects.get(q.path);
  effects.delete(q.path);
  const { animate = fx?.animate ?? false, note = fx?.note ?? null } = opts;
  const { state } = game;
  const unit = state.units[q.path];
  const v = renderQuestion(q, {
    number: questionNumber(pack, q),
    marginNo: `${pack.n}.${pack.questions.indexOf(q) + 1}`,
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
    const note = { text, kind: already ? "info" : r.correct ? "info" : "error" };
    announce(text);
    // Ответ на бонус (верный или нет) открывает следующий. Отвечен последний бонус пройденного этапа — окно конверта.
    effects.set(q.path, { animate: ok, note });
    if (game.state.stage > pack.n && S.pendingEnvelope(game.state) === pack.n + 1 && !pendingBonuses(pack, game.state).length) {
      holdStage = pack.n;
      rerender(pack, null);
      // В заголовке окна уже «Ответ принят. …» — не повторяем его в тексте окна, оставляем только баллы.
      const modalText = ok ? T.result.bonusPoints(ctx.pub.points.bonus) : text;
      await showPendingEnvelope({ note: modalText });
      return;
    }
    rerender(pack, stageFlow(pack, game.state.units).current);
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
  const accepted = { animate: true, note: { text: T.result.accepted, kind: "info" } };
  if (!isStageComplete(pack, game.state.units) || !pack.saltStage) {
    // Следующий вопрос появляется только после верного ответа на этот.
    effects.set(q.path, accepted);
    const last = !pack.saltStage;
    const next = stageFlow(pack, game.state.units, { bonuses: !last }).current;
    rerender(pack, next);
    if (last && !next && finalReady(pack, game.state)) {
      // Последний обязательный вопрос последнего этапа: дальше — финал (кнопка «Перейти к финалу»).
      announce(`${T.result.accepted} ${T.final.finalReadyText}`);
      document.querySelector(".final-link__go")?.focus();
      return;
    }
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
  effects.set(q.path, accepted);
  await reload();
  // Если у этапа есть неотвеченные бонусы — они идут первыми, окно конверта покажет showPendingEnvelope после них.
  const bonusNext = stageFlow(pack, game.state.units).current;
  if (bonusNext && viewStage(game.state, game.packs) === pack.n) focusQuestion(bonusNext);
  await showPendingEnvelope();
}

/** Перерисовать экран после изменения набора видимых вопросов и поставить фокус на следующий вопрос. */
function rerender(pack, focusPath) {
  const y = window.scrollY;
  renderGame();
  window.scrollTo(0, y);
  if (focusPath) focusQuestion(focusPath);
}

function focusQuestion(path) {
  const el = document.querySelector(`article[data-path="${CSS.escape(path)}"]`);
  el?.querySelector("input, select, button")?.focus({ preventScroll: false });
}

// ------------------------------------------------------------------ конверт

/**
 * Окно «Откройте конверт №N». Пока у пройденного этапа остаются бонусы, окно не показывается
 * (экран держит этот этап); skip — «Пропустить бонусы и перейти к конверту №N».
 */
async function showPendingEnvelope({ skip = false, note = null } = {}) {
  const n = S.pendingEnvelope(game.state);
  if (!n || envelopeShown) return;
  if (!skip && holdStage === null && viewStage(game.state, game.packs) < n) return;
  const prev = game.packs[n - 1];
  const env = game.packs[n].envelope;
  await envelopeModal({ title: prev?.onComplete || T.result.acceptedEnvelope(env), envelope: env, ack: n, note });
}

async function envelopeModal({ title, envelope, ack, note = null }) {
  envelopeShown = true;
  await openModal({
    title,
    body: [...(note ? [note] : []), T.envelope.hint],
    className: "modal--envelope",
    seal: createSeal(String(envelope), { animate: true }),
    stamp: createStamp({ text: T.stamp.envelope(envelope), variant: "envelope", seed: `env${envelope}`, animate: true }),
    actions: [{ id: "ok", label: T.envelope.opened, primary: true }],
    dismissible: false,
  });
  envelopeShown = false;
  if (ack) {
    commit((s) => S.ackEnvelope(s, ack));
    // Экран мог держаться на пройденном этапе (бонусы): после «Конверт вскрыт» показываем новый.
    holdStage = null;
    renderGame();
  }
  document.getElementById("stage-title")?.scrollIntoView({ block: "start" });
  document.getElementById("main")?.focus({ preventScroll: true });
}

// Запуск — в конце модуля: все объявления выше уже инициализированы.
if (ctx) {
  ctx.store.onExternalChange(() => start());
  await start();
}
