// Порядок вопросов этапа (core/flow.js): по одному, следующий — после ответа на текущий.
import { test } from "node:test";
import assert from "node:assert/strict";
import { stageFlow, pendingBonuses, viewStage } from "../../site/assets/js/core/flow.js";

const pack = (n = 1, spec = "mmmbb") => ({
  n,
  questions: [...spec].map((k, i) => ({ path: `s${n}.${k === "m" ? "q" : "b"}${i + 1}`, kind: k === "m" ? "mandatory" : "bonus" })),
});
const solved = { status: "solved", canon: "x", given: null };
const closed = { status: "closed", canon: null, given: "y" };
const paths = (list) => list.map((q) => q.path);

test("stageFlow: в начале виден только первый обязательный, бонусов нет", () => {
  const f = stageFlow(pack(), {});
  assert.deepEqual(paths(f.mandatory.shown), ["s1.q1"]);
  assert.equal(f.mandatory.hidden, 2);
  assert.deepEqual(f.bonus.shown, []);
  assert.equal(f.current, "s1.q1");
  assert.equal(f.complete, false);
});

test("stageFlow: решённые остаются, следующий появляется после верного ответа", () => {
  const f = stageFlow(pack(), { "s1.q1": solved });
  assert.deepEqual(paths(f.mandatory.shown), ["s1.q1", "s1.q2"]);
  assert.equal(f.mandatory.hidden, 1);
  assert.equal(f.current, "s1.q2");
  assert.deepEqual(f.bonus.shown, []);
});

test("stageFlow: неверные попытки следующий вопрос не открывают (units не меняется)", () => {
  const f = stageFlow(pack(), {}); // wrong живёт в state.wrong, не в units
  assert.deepEqual(paths(f.mandatory.shown), ["s1.q1"]);
});

test("stageFlow: бонусы идут после последнего обязательного, по одному", () => {
  const units = { "s1.q1": solved, "s1.q2": solved, "s1.q3": solved };
  const f = stageFlow(pack(), units);
  assert.equal(f.complete, true);
  assert.equal(f.mandatory.hidden, 0);
  assert.deepEqual(paths(f.bonus.shown), ["s1.b4"]);
  assert.equal(f.bonus.hidden, 1);
  assert.equal(f.current, "s1.b4");
});

test("stageFlow: следующий бонус открывается после ответа на предыдущий, верного или нет", () => {
  const base = { "s1.q1": solved, "s1.q2": solved, "s1.q3": solved };
  const afterRight = stageFlow(pack(), { ...base, "s1.b4": solved });
  assert.deepEqual(paths(afterRight.bonus.shown), ["s1.b4", "s1.b5"]);
  assert.equal(afterRight.current, "s1.b5");
  const afterWrong = stageFlow(pack(), { ...base, "s1.b4": closed });
  assert.deepEqual(paths(afterWrong.bonus.shown), ["s1.b4", "s1.b5"]);
  const all = stageFlow(pack(), { ...base, "s1.b4": closed, "s1.b5": solved });
  assert.equal(all.bonus.hidden, 0);
  assert.equal(all.current, null);
});

test("stageFlow: этап без бонусов и пустой этап", () => {
  const f = stageFlow(pack(1, "mm"), { "s1.q1": solved, "s1.q2": solved });
  assert.deepEqual(f.bonus, { shown: [], hidden: 0 });
  assert.equal(f.current, null);
  assert.deepEqual(stageFlow({ questions: [] }, {}).mandatory, { shown: [], hidden: 0 });
  assert.equal(stageFlow(undefined, undefined).complete, true);
});

test("stageFlow: старое сохранение (ответы не по порядку) — решённые видны, ровно один текущий", () => {
  const f = stageFlow(pack(), { "s1.q1": solved, "s1.q3": solved });
  assert.deepEqual(paths(f.mandatory.shown), ["s1.q1", "s1.q2", "s1.q3"]);
  assert.equal(f.mandatory.hidden, 0);
  assert.equal(f.current, "s1.q2");
  // Бонус отвечен при неполных обязательных: он виден, но новые бонусы не открываются.
  const g = stageFlow(pack(), { "s1.q1": solved, "s1.b5": solved });
  assert.deepEqual(paths(g.bonus.shown), ["s1.b5"]);
  assert.equal(g.current, "s1.q2");
});

test("pendingBonuses: неотвеченные бонусы, пока финал не начат", () => {
  const p = pack();
  const state = { units: { "s1.b4": closed }, final: { started: false }, finished: false };
  assert.deepEqual(paths(pendingBonuses(p, state)), ["s1.b5"]);
  assert.deepEqual(pendingBonuses(p, { ...state, final: { started: true } }), []);
  assert.deepEqual(pendingBonuses(p, { ...state, finished: true }), []);
  assert.deepEqual(pendingBonuses(undefined, state), []);
});

test("viewStage: бонусы пройденного этапа показываются до окна конверта", () => {
  const packs = { 1: pack(1), 2: pack(2) };
  const st = (over) => ({ stage: 2, envelopeAck: 1, units: {}, final: { started: false }, finished: false, ...over });
  // Конверт №2 не вскрыт, бонусы этапа 1 не отвечены → экран на этапе 1.
  assert.equal(viewStage(st(), packs), 1);
  // Часть бонусов отвечена, остался один → всё ещё этап 1.
  assert.equal(viewStage(st({ units: { "s1.b4": closed } }), packs), 1);
  // Все бонусы отвечены → этап 2 (и окно конверта).
  assert.equal(viewStage(st({ units: { "s1.b4": closed, "s1.b5": solved } }), packs), 2);
  // Конверт вскрыт (пропуск бонусов) → этап 2, бонусы ждут в пройденном этапе.
  assert.equal(viewStage(st({ envelopeAck: 2 }), packs), 2);
  // Этап без бонусов, первый этап, начатый финал.
  assert.equal(viewStage(st(), { 1: pack(1, "mm"), 2: pack(2) }), 2);
  assert.equal(viewStage(st({ stage: 1, envelopeAck: 1 }), packs), 1);
  assert.equal(viewStage(st({ final: { started: true } }), packs), 2);
});
