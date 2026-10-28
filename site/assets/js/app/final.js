// Финал «/final/» (docs/01 §8–9, docs/04, FORMATS §4, §7):
// доступ с последнего этапа → предупреждение → вопросы по одному (финальные,
// бонус последним), ответ фиксируется без оценки → после последнего ответа
// проверка и finalFinish → finale.json (только теперь, F9) → итоги со штампом
// ранга и разбором → развязка: признание → второй протокол (если есть) → письмо → судьбы,
// «Дальше»,
// «Вернуться к делу».

import { h, clear, announce } from "./dom.js";
import { T, signed } from "./texts.js";
import { createStamp } from "./stamp.js";
import { renderScoreLog } from "./scorelog.js";
import { makeLabelFor } from "./labels.js";
import { renderQuestion, formatMessage, displayValue } from "./questions.js";
import { renderDocument } from "./docview.js";
import { renderHeader } from "./header.js";
import { confirmDialog } from "./modal.js";
import { restartFlow } from "./menu.js";
import { initPage, loadProgress, renderLoadError, renderShell, renderFatal, rulesCfg } from "./context.js";
import * as S from "../core/state.js";
import {
  openPack,
  openFinale,
  finalQuestions,
  mandatory,
  earlierBonusPaths,
  normalizeQuestion,
  checkQuestionNormalized,
  rankFor,
} from "../core/game.js";
import { finalReady } from "../core/flow.js";

const ctx = await initPage();
let game = null;
let header = null;
let main = null;


async function verify(s) {
  try {
    await openPack(s.stage, s.keys[s.stage]);
    return true;
  } catch {
    return false;
  }
}

const lastStage = () => ctx.pub.stages;

/** Текущий вопрос финала и его незаконченный ввод — переживают перерисовку по storage. */
let current = null;
let finalDraft = null;

async function start() {
  const kept = current?.view.el.isConnected ? current.view.getInputs?.() : null;
  if (kept !== null && kept !== undefined) finalDraft = { path: current.path, value: kept };
  const res = await loadProgress(ctx);
  if (!res.ok) {
    if (res.code === "none") {
      renderFatal(ctx, { title: T.final.title, text: T.errors.notStarted });
      ctx.mount.querySelector(".q__actions")?.appendChild(h("a", { class: "btn btn--primary", href: "/" }, T.errors.toStart));
      return;
    }
    return renderLoadError(ctx, res.code);
  }
  game = res;
  header = renderHeader(ctx, game.state, { onChange: () => start(), verify, rulesCfg: rulesCfg(ctx.pub) });
  const shell = renderShell(ctx, header.el);
  main = shell.main;
  shell.side.appendChild(renderScoreLog(game.state, { labelFor: makeLabelFor(game.packs) }));
  await route();
}

function commit(fn) {
  game.state = ctx.store.update(fn);
  header.update(game.state);
  return game.state;
}

async function route() {
  const { state } = game;
  if (state.stage < lastStage()) return renderLocked();
  if (!finalReady(game.packs[lastStage()], state)) return renderLocked(T.final.lockedMandatory(lastStage()));
  if (state.finished) return renderResults();
  if (!state.final.started) return renderWarning();
  const qs = finalQuestions(game.packs[lastStage()]);
  if (state.final.index < qs.length) return renderQuestionStep(qs);
  return finish(qs);
}

function sheet(title, ...children) {
  clear(main);
  const el = h(
    "section",
    { class: "sheet final-sheet", "aria-labelledby": "final-title" },
    h("div", { class: "stage-head" }, h("h1", { class: "stage-head__title", id: "final-title", tabindex: "-1" }, title)),
    ...children,
  );
  main.appendChild(el);
  return el;
}

// ------------------------------------------------------------------ шаги

function renderLocked(text = T.final.locked(lastStage() - 1)) {
  sheet(
    T.final.title,
    h("div", { class: "q" }, h("p", null, text), h("div", { class: "q__actions" }, h("a", { class: "btn btn--primary", href: "/" }, T.back))),
  );
}

function renderWarning() {
  const openBonus = earlierBonusPaths(game.packs, lastStage()).some((p) => !game.state.units[p]);
  const btn = h("button", { type: "button", class: "btn btn--primary" }, T.final.start);
  btn.addEventListener("click", async () => {
    if (openBonus) {
      const ok = await confirmDialog({ title: T.final.start, text: T.final.startConfirm, ok: T.final.start });
      if (!ok) return;
    }
    commit((s) => S.finalStart(s, earlierBonusPaths(game.packs, lastStage())));
    await route();
  });
  sheet(
    T.final.title,
    h(
      "div",
      { class: "q" },
      h("p", { class: "final-warn" }, T.final.warn),
      openBonus ? h("p", { class: "q__help" }, T.final.warnBonus) : null,
      h("div", { class: "q__actions" }, btn, h("a", { class: "btn btn--secondary", href: "/" }, T.back)),
    ),
  );
  btn.focus();
}

function renderQuestionStep(qs, note = null) {
  const i = game.state.final.index;
  const q = qs[i];
  const pack = game.packs[lastStage()];
  const v = renderQuestion(q, {
    number: T.final.progress(i + 1, qs.length),
    showStatus: false,
    draft: finalDraft?.path === q.path ? finalDraft.value : undefined,
    characters: pack.characters,
    documents: game.docs,
    submitLabel: T.final.submit,
    onCheck: async (inputs) => {
      const n = normalizeQuestion(q, inputs, ctx.pub);
      if (!n.valid) {
        v.showMessage(formatMessage(q, inputs, n.invalid), "format");
        v.markInvalid(n.invalid);
        return;
      }
      commit((s) => S.finalSubmit(s, q.path, n.normalized));
      announce(T.final.fixed);
      await route();
    },
  });
  current = { path: q.path, view: v };
  sheet(T.final.title, note ? h("p", { class: "q__msg final-fixed", role: "status" }, note) : null, v.el);
  if (i > 0 && !note) main.querySelector(".final-sheet .stage-head")?.after(h("p", { class: "q__msg final-fixed", role: "status" }, T.final.fixed));
  main.querySelector("input, select, .order button, .option input")?.focus();
}

async function finish(qs) {
  sheet(T.final.title, h("div", { class: "q" }, h("p", { role: "status" }, T.final.counting)));
  const answers = game.state.final.answers;
  const results = {};
  // Проверка один раз, после последнего ответа (FORMATS §7, final.correct).
  await Promise.all(
    qs.map(async (q) => {
      const correct = await checkQuestionNormalized(q, answers[q.path], ctx.pub).catch(() => false);
      results[q.path] = { correct, kind: q.kind === "bonus" ? "bonus" : "final" };
    }),
  );
  const ordered = {};
  for (const q of qs) ordered[q.path] = results[q.path];
  commit((s) => S.finalFinish(s, ordered, ctx.pub.points));
  document.querySelector(".side .scorelog")?.replaceWith(renderScoreLog(game.state, { labelFor: makeLabelFor(game.packs) }));
  await renderResults({ animate: true });
}

// ------------------------------------------------------------------ итоги и разбор

async function renderResults({ animate = false } = {}) {
  let finale;
  try {
    finale = await openFinale(game.state.keys[lastStage()]); // F9: только сейчас и не сохраняется
  } catch {
    sheet(T.final.resultTitle, h("p", { class: "notice notice--error" }, T.final.finaleError));
    return;
  }
  const total = S.score(game.state);
  const rank = rankFor(total, ctx.pub.ranks);
  const toEnding = h("button", { type: "button", class: "btn btn--primary" }, T.final.toEnding);
  toEnding.addEventListener("click", () => renderEnding(finale, 0));

  sheet(
    T.final.resultTitle,
    h(
      "div",
      { class: "q final-summary" },
      h(
        "p",
        { class: "final-summary__caption" },
        h("span", null, T.final.summaryCaption(ctx.chrome.caseNo)),
        game.state.team ? h("span", { class: "final-summary__team" }, T.header.team(game.state.team)) : null,
      ),
      h(
        "dl",
        { class: "final-score" },
        h("dt", null, T.final.score),
        h("dd", { class: ["final-score__value", total < 0 && "is-negative"] }, total === 0 ? "0" : signed(total)),
        h("dt", null, T.final.rank),
        h("dd", null, createStamp({ text: rank, variant: "rank", seed: `rank-${rank}`, animate })),
      ),
    ),
    h("div", { class: "q" }, h("h2", { class: "group-title group-title--flush" }, T.final.review), reviewTable(finale)),
    h("div", { class: "q" }, h("div", { class: "q__actions" }, toEnding)),
  );
  main.querySelector("#final-title")?.focus();
}

function reviewTable(finale) {
  const { state, packs } = game;
  const rows = [];
  for (let n = 1; n <= lastStage(); n++) {
    const pack = packs[n];
    // Последний этап: обязательные (главный экран), затем финальные и бонус — в порядке финала.
    const qs = n === lastStage() ? [...mandatory(pack), ...finalQuestions(pack)] : pack.questions;
    for (const q of qs) {
      const idx = pack.questions.indexOf(q) + 1;
      const no = `${n}.${idx}`;
      const isFinal = n === lastStage() && q.kind !== "mandatory";
      const unit = state.units[q.path];
      const value = isFinal ? state.final.answers[q.path] : unit?.status === "solved" ? unit.canon : unit?.given;
      const ok = isFinal ? state.final.correct?.[q.path] === true : unit?.status === "solved";
      const specs = q.type === "form" ? q.fields.map((f) => [f, `${q.prompt} — ${f.label}`, value?.[f.id]]) : [[q, q.prompt, value]];
      specs.forEach(([spec, label, v], j) => {
        rows.push(
          h(
            "tr",
            { class: ok ? "is-right" : "is-wrong" },
            h("th", { scope: "row" }, j === 0 || q.type !== "form" ? h("span", { class: "review__no" }, no) : null, " ", label),
            h(
              "td",
              { "data-label": T.final.colTeam },
              v === undefined || v === null ? T.final.noAnswer : displayValue(spec, v, { characters: pack.characters, documents: game.docs }),
              ok ? null : h("span", { class: "review__verdict" }, ` — ${T.final.verdict[false]}`),
            ),
            h("td", { "data-label": T.final.colRight }, finale.answers?.[spec.unit.path] ?? T.final.noAnswer),
          ),
        );
      });
    }
  }
  return h(
    "div",
    { class: "review-wrap" },
    h(
      "table",
      { class: "review" },
      h("thead", null, h("tr", null, h("th", { scope: "col" }, T.final.colQuestion), h("th", { scope: "col" }, T.final.colTeam), h("th", { scope: "col" }, T.final.colRight))),
      h("tbody", null, rows),
    ),
  );
}

// ------------------------------------------------------------------ развязка

// Шаги развязки: признание, второй протокол (если confession2 есть в finale.json), письмо, судьбы
// и (если поле есть в finale.yaml) «Спасибо за игру».
function endingSteps(finale) {
  const steps = ["confession"];
  if (finale.confession2) steps.push("confession2");
  steps.push("letter", "fates");
  if (finale.thanks) steps.push("thanks");
  return steps;
}

function renderEnding(finale, part) {
  const steps = endingSteps(finale);
  const step = steps[part];
  if (step === "thanks") return renderThanks(finale);
  const last = part === steps.length - 1;
  const next = h("button", { type: "button", class: "btn btn--primary" }, T.next);
  let content;
  if (step === "fates")
    content = h(
      "ul",
      { class: "fates" },
      (finale.fates ?? []).map((f) => h("li", { class: "fates__item" }, f.name ? h("strong", { class: "fates__name" }, f.name) : null, f.name ? " " : null, f.text)),
    );
  else content = renderDocument(finale[step]);
  const actions = h("div", { class: "q__actions no-print" });
  if (!last) {
    next.addEventListener("click", () => renderEnding(finale, part + 1));
    actions.appendChild(next);
  } else {
    actions.appendChild(h("a", { class: "btn btn--primary", href: "/" }, T.back));
  }
  const back = h("button", { type: "button", class: "btn btn--secondary" }, T.final.resultTitle);
  back.addEventListener("click", () => renderResults());
  actions.appendChild(back);
  sheet(
    `${T.final.ending}. ${T.final.endingParts[step]}`,
    // Название документа — в самом бланке; у судеб — заголовок раздела.
    h("div", { class: "q ending" }, content, actions),
  );
  main.querySelector("#final-title")?.focus();
}

/** Заключительный блок: тексты из finale.thanks (content), счёт и ранг из прогресса. */
function renderThanks(finale) {
  const { title, text, signature } = finale.thanks;
  const total = S.score(game.state);
  const rank = rankFor(total, ctx.pub.ranks);
  const restart = h("button", { type: "button", class: "btn btn--secondary" }, T.final.restart);
  restart.addEventListener("click", async () => {
    if (await restartFlow(ctx.store)) location.assign("/");
  });
  const back = h("button", { type: "button", class: "btn btn--secondary" }, T.final.resultTitle);
  back.addEventListener("click", () => renderResults());
  const paragraphs = String(text)
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
  sheet(
    title,
    h(
      "div",
      { class: "q ending thanks" },
      h("div", { class: "thanks__text" }, paragraphs.map((p) => h("p", null, p))),
      signature ? h("p", { class: "thanks__signature" }, signature) : null,
      h(
        "dl",
        { class: "final-score thanks__score" },
        h("dt", null, T.final.score),
        h("dd", { class: ["final-score__value", total < 0 && "is-negative"] }, total === 0 ? "0" : signed(total)),
        h("dt", null, T.final.rank),
        h("dd", null, createStamp({ text: rank, variant: "rank", seed: `rank-${rank}` })),
      ),
      h("div", { class: "q__actions no-print" }, h("a", { class: "btn btn--primary", href: "/" }, T.back), restart, back),
    ),
  );
  main.querySelector("#final-title")?.focus();
}

// Запуск — в конце модуля: все объявления выше уже инициализированы.
if (ctx) {
  ctx.store.onExternalChange(() => start());
  await start();
}
