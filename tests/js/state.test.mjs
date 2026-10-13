// Правила начисления и списания (docs/01 §4–6, §8, §10) и хранилище (docs/02 §4).
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  STATE_VERSION,
  StateError,
  newState,
  parseState,
  isCompatible,
  score,
  wrongCount,
  hintLevel,
  unitStatus,
  recordWrong,
  buyHint,
  maybeAutoHint,
  solve,
  bonusAnswer,
  advanceStage,
  labDone,
  labRejected,
  finalSubmit,
  finalFinish,
  createStore,
} from "../../site/assets/js/core/state.js";

// Те же значения, что в content/settings.yaml → public.json. Код их не знает:
// они приходят параметрами (часть тестов гоняется и на других числах).
const PUB = {
  gameId: "testgame",
  saltsId: "salts-A",
  points: { bonus: 15, final: 30 },
  penalties: { wrongAttempt: -5, labNoBasis: -5 },
  hints: { cost: [10, 20, 40], autoAfterWrong: 3 },
};

const fresh = () =>
  newState({
    gameId: PUB.gameId,
    saltsId: PUB.saltsId,
    buildId: "b1",
    team: "Команда",
    startedAt: "2026-11-12T10:00:00.000Z",
    keys: { 1: "k1" },
  });

class MemoryStorage {
  constructor() {
    this.map = new Map();
  }
  getItem(k) {
    return this.map.has(k) ? this.map.get(k) : null;
  }
  setItem(k, v) {
    this.map.set(k, String(v));
  }
  removeItem(k) {
    this.map.delete(k);
  }
}

class ThrowingStorage {
  getItem() {
    throw new Error("SecurityError");
  }
  setItem() {
    throw new Error("SecurityError");
  }
  removeItem() {
    throw new Error("SecurityError");
  }
}

function clock(start = Date.parse("2026-11-12T10:00:00Z")) {
  let t = start;
  return () => (t += 1000);
}

// ---------------------------------------------------------------------------
describe("§4 попытки и штрафы", () => {
  test("неверная попытка обязательного вопроса — штраф из настроек", () => {
    let s = fresh();
    s = recordWrong(s, "s1.q2", "h1", PUB.penalties.wrongAttempt);
    assert.equal(score(s), -5);
    assert.deepEqual(s.log, [{ d: -5, r: "wrong:s1.q2" }]);
    assert.equal(wrongCount(s, "s1.q2"), 1);
    s = recordWrong(s, "s1.q2", "h2", PUB.penalties.wrongAttempt);
    assert.equal(score(s), -10);
  });

  test("попыток сколько угодно: каждая новая неверная штрафуется", () => {
    let s = fresh();
    for (let i = 0; i < 10; i++) s = recordWrong(s, "s1.q2", `h${i}`, -5);
    assert.equal(score(s), -50);
    assert.equal(wrongCount(s, "s1.q2"), 10);
  });

  test("повтор уже отправленного неверного ответа (тот же хеш) — без штрафа", () => {
    const s1 = recordWrong(fresh(), "s1.q2", "same", -5);
    const s2 = recordWrong(s1, "s1.q2", "same", -5);
    assert.equal(s2, s1, "тот же объект — действие не применилось");
    assert.equal(score(s2), -5);
    assert.equal(wrongCount(s2, "s1.q2"), 1);
  });

  test("одинаковый хеш у разных вопросов штрафуется отдельно", () => {
    let s = recordWrong(fresh(), "s1.q1", "x", -5);
    s = recordWrong(s, "s1.q2", "x", -5);
    assert.equal(score(s), -10);
  });

  test("штраф берётся из параметра, знак нормализуется", () => {
    assert.equal(score(recordWrong(fresh(), "p", "h", -7)), -7);
    assert.equal(score(recordWrong(fresh(), "p", "h", 7)), -7);
    assert.throws(() => recordWrong(fresh(), "p", "h", undefined), TypeError);
  });

  test("после решения вопроса неверная попытка не записывается", () => {
    const s = solve(fresh(), "s1.q2", ["k3"]);
    assert.equal(recordWrong(s, "s1.q2", "h", -5), s);
  });

  test("решение обязательного вопроса баллов не даёт и не меняет статус повторно", () => {
    const s = solve(fresh(), "s1.q1", { time: "21:18" });
    assert.equal(score(s), 0);
    assert.equal(unitStatus(s, "s1.q1"), "solved");
    assert.deepEqual(s.units["s1.q1"].canon, { time: "21:18" });
    assert.equal(solve(s, "s1.q1", { time: "00:00" }), s);
  });

  test(`автоподсказка уровня 1 бесплатно после ${PUB.hints.autoAfterWrong} ошибок`, () => {
    const N = PUB.hints.autoAfterWrong;
    let s = fresh();
    for (let i = 0; i < N - 1; i++) {
      s = recordWrong(s, "s1.q2", `h${i}`, -5);
      s = maybeAutoHint(s, "s1.q2", N);
      assert.equal(hintLevel(s, "s1.q2"), 0, `после ${i + 1} ошибок ещё нет`);
    }
    s = recordWrong(s, "s1.q2", "last", -5);
    const before = score(s);
    s = maybeAutoHint(s, "s1.q2", N);
    assert.equal(hintLevel(s, "s1.q2"), 1);
    assert.equal(score(s), before, "бесплатно");
    assert.equal(score(s), -5 * N);
  });

  test("повторы неверного ответа не приближают автоподсказку", () => {
    let s = fresh();
    for (let i = 0; i < 5; i++) s = maybeAutoHint(recordWrong(s, "q", "same", -5), "q", 3);
    assert.equal(hintLevel(s, "q"), 0);
  });

  test("автоподсказка не срабатывает, если уровень 1 уже куплен, и не отнимает уровни", () => {
    let s = buyHint(fresh(), "q", 1, 10);
    s = buyHint(s, "q", 2, 20);
    for (let i = 0; i < 3; i++) s = recordWrong(s, "q", `h${i}`, -5);
    const t = maybeAutoHint(s, "q", 3);
    assert.equal(t, s);
    assert.equal(hintLevel(t, "q"), 2);
  });

  test("порог автоподсказки — параметр", () => {
    let s = recordWrong(fresh(), "q", "a", -5);
    assert.equal(hintLevel(maybeAutoHint(s, "q", 1), "q"), 1);
    assert.equal(hintLevel(maybeAutoHint(s, "q", 2), "q"), 0);
  });
});

// ---------------------------------------------------------------------------
describe("§5 подсказки", () => {
  const cost = (lvl) => PUB.hints.cost[lvl - 1];

  test("подсказки покупаются строго по порядку, цены из настроек", () => {
    let s = fresh();
    assert.equal(buyHint(s, "q", 2, cost(2)), s, "нельзя сразу уровень 2");
    assert.equal(buyHint(s, "q", 3, cost(3)), s, "нельзя сразу уровень 3");
    s = buyHint(s, "q", 1, cost(1));
    assert.equal(score(s), -10);
    assert.equal(buyHint(s, "q", 3, cost(3)), s, "нельзя перепрыгнуть уровень");
    s = buyHint(s, "q", 2, cost(2));
    s = buyHint(s, "q", 3, cost(3));
    assert.equal(score(s), -70);
    assert.equal(hintLevel(s, "q"), 3);
    assert.deepEqual(
      s.log.map((e) => e.r),
      ["hint:q:1", "hint:q:2", "hint:q:3"],
    );
  });

  test("повторная покупка того же уровня ничего не списывает", () => {
    const s = buyHint(fresh(), "q", 1, 10);
    assert.equal(buyHint(s, "q", 1, 10), s);
  });

  test("после бесплатной автоподсказки следующая покупка — уровень 2", () => {
    let s = fresh();
    for (let i = 0; i < 3; i++) s = recordWrong(s, "q", `h${i}`, -5);
    s = maybeAutoHint(s, "q", 3);
    assert.equal(buyHint(s, "q", 1, 10), s);
    s = buyHint(s, "q", 2, 20);
    assert.equal(score(s), -15 - 20);
  });

  test("после решения вопроса подсказки не продаются", () => {
    const s = solve(fresh(), "q", "x");
    assert.equal(buyHint(s, "q", 1, 10), s);
  });

  test("цена — параметр; без цены — ошибка, а не тихий ноль", () => {
    assert.equal(score(buyHint(fresh(), "q", 1, 3)), -3);
    assert.throws(() => buyHint(fresh(), "q", 1, undefined), TypeError);
  });
});

// ---------------------------------------------------------------------------
describe("§4 бонусные вопросы: одна попытка", () => {
  const pts = PUB.points.bonus;

  test("верно — +bonus, вопрос решён", () => {
    const s = bonusAnswer(fresh(), "s1.b1", { correct: true, canon: "северогорск", points: pts });
    assert.equal(score(s), 15);
    assert.deepEqual(s.log, [{ d: 15, r: "bonus:s1.b1" }]);
    assert.equal(unitStatus(s, "s1.b1"), "solved");
  });

  test("неверно — 0, вопрос закрыт, вторая попытка невозможна", () => {
    const s = bonusAnswer(fresh(), "s1.b1", { correct: false, canon: "москва", points: pts });
    assert.equal(score(s), 0);
    assert.equal(unitStatus(s, "s1.b1"), "closed");
    assert.equal(s.units["s1.b1"].canon, "москва", "ответ команды сохранён для разбора");
    const again = bonusAnswer(s, "s1.b1", { correct: true, canon: "северогорск", points: pts });
    assert.equal(again, s);
    assert.equal(score(again), 0);
  });

  test("после верного ответа повтор не начисляет второй раз", () => {
    const s = bonusAnswer(fresh(), "b", { correct: true, canon: "x", points: pts });
    assert.equal(bonusAnswer(s, "b", { correct: true, canon: "x", points: pts }), s);
  });

  test("после начала финала бонусы прошлых этапов закрыты", () => {
    const s = finalSubmit(fresh(), "s4.f1", { canon: "a" });
    assert.equal(bonusAnswer(s, "s2.b1", { correct: true, canon: "x", points: pts }), s);
  });
});

// ---------------------------------------------------------------------------
describe("§8 финал", () => {
  test("ответы фиксируются, счёт не меняется до finalFinish", () => {
    let s = buyHint(fresh(), "s1.q1", 1, 10); // −10 до финала
    s = advanceStage(s, 4, "k4");
    const before = score(s);
    s = finalSubmit(s, "s4.f1", { canon: "a" });
    s = finalSubmit(s, "s4.f2", { canon: "b" });
    assert.equal(score(s), before);
    assert.equal(s.final.index, 2);
    const locked = finalSubmit(s, "s4.f1", { canon: "другое" });
    assert.equal(locked, s, "ответ нельзя изменить");
    assert.deepEqual(s.final.answers["s4.f1"], { canon: "a" });
  });

  test("finalFinish пишет баллы за верные финальные и бонус этапа 4", () => {
    let s = fresh();
    for (const p of ["s4.f1", "s4.f2", "s4.f3", "s4.fb"]) s = finalSubmit(s, p, { canon: p });
    s = finalFinish(
      s,
      {
        "s4.f1": { correct: true, kind: "final" },
        "s4.f2": { correct: false, kind: "final" },
        "s4.f3": { correct: true, kind: "final" },
        "s4.fb": { correct: true, kind: "bonus" },
      },
      PUB.points,
    );
    assert.equal(score(s), 30 + 30 + 15);
    assert.deepEqual(
      s.log.map((e) => e.r),
      ["final:s4.f1", "final:s4.f3", "bonus:s4.fb"],
    );
    assert.equal(s.finished, true);
  });

  test("finalFinish один раз; после конца игры ответы не принимаются", () => {
    const s = finalFinish(fresh(), { a: { correct: true, kind: "final" } }, PUB.points);
    assert.equal(finalFinish(s, { a: { correct: true, kind: "final" } }, PUB.points), s);
    assert.equal(finalSubmit(s, "s4.f9", { canon: "x" }), s);
  });

  test("баллы финала — параметры", () => {
    const s = finalFinish(fresh(), { a: { correct: true, kind: "final" } }, { final: 1, bonus: 2 });
    assert.equal(score(s), 1);
  });
});

// ---------------------------------------------------------------------------
describe("§6 счёт = сумма журнала; §7 лаборатория; этапы", () => {
  test("счёт может уйти в минус и равен сумме log[].d", () => {
    let s = recordWrong(fresh(), "a", "1", -5);
    s = buyHint(s, "a", 1, 10);
    s = labRejected(s, "fp1", PUB.penalties.labNoBasis);
    s = bonusAnswer(s, "b", { correct: true, canon: "x", points: 15 });
    assert.equal(score(s), -5);
    assert.equal(score(s), s.log.reduce((a, e) => a + e.d, 0));
  });

  test("лаборатория: отказ штрафуется один раз, повтор — без штрафа", () => {
    let s = labRejected(fresh(), "fp1", -5);
    assert.deepEqual(s.log, [{ d: -5, r: "lab:fp1" }]);
    assert.equal(labRejected(s, "fp1", -5), s);
  });

  test("лаборатория: выполненный запрос добавляет документ, повтор без штрафа", () => {
    let s = labDone(fresh(), "fp2", "2-01");
    assert.deepEqual(s.docs, ["2-01"]);
    assert.equal(labDone(s, "fp2", "2-01"), s);
    assert.equal(labRejected(s, "fp2", -5), s, "выполненный запрос не штрафуется");
    assert.equal(score(s), 0);
  });

  test("лаборатория: отклонённый раньше запрос может сработать после перехода этапа", () => {
    let s = labRejected(fresh(), "fp3", -5);
    s = labDone(s, "fp3", "3-05");
    assert.deepEqual(s.lab.rejected, []);
    assert.equal(s.lab.done.fp3, "3-05");
    assert.equal(score(s), -5, "штраф за прошлый отказ остаётся");
  });

  test("лаборатория: атмосферный результат без документа", () => {
    const s = labDone(fresh(), "fp4", null);
    assert.equal(s.lab.done.fp4, null);
    assert.deepEqual(s.docs, []);
  });

  test("переход этапа сохраняет ключ и не откатывает этап назад", () => {
    let s = advanceStage(fresh(), 2, "k2");
    assert.equal(s.stage, 2);
    assert.equal(s.keys["2"], "k2");
    assert.equal(advanceStage(s, 2, "k2"), s);
    s = advanceStage(s, 3, "k3");
    s = advanceStage(s, 2, "k2");
    assert.equal(s.stage, 3);
  });

  test("редьюсеры не мутируют исходное состояние", () => {
    const s = fresh();
    const snapshot = JSON.stringify(s);
    recordWrong(s, "a", "1", -5);
    buyHint(s, "a", 1, 10);
    solve(s, "a", "x");
    labRejected(s, "f", -5);
    finalSubmit(s, "s4.f1", {});
    finalFinish(s, {}, PUB.points);
    assert.equal(JSON.stringify(s), snapshot);
  });
});

// ---------------------------------------------------------------------------
describe("§10 хранилище, экспорт, импорт, совместимость", () => {
  function playSome(store) {
    store.update(() => fresh());
    store.update((s) => recordWrong(s, "s1.q2", "h1", -5));
    store.update((s) => buyHint(s, "s1.q2", 1, 10));
    store.update((s) => solve(s, "s1.q1", { time: "21:18", conflict: "zavyalov" }));
    store.update((s) => advanceStage(s, 2, "a2V5Mg"));
    store.update((s) => labDone(s, "fp", "2-01"));
  }

  test("состояние переживает «перезагрузку» (новый store на том же хранилище)", () => {
    const storage = new MemoryStorage();
    const a = createStore({ storage, gameId: PUB.gameId, now: clock(), events: null });
    assert.equal(a.persistent, true);
    assert.equal(a.get(), null);
    playSome(a);
    const b = createStore({ storage, gameId: PUB.gameId, now: clock(), events: null });
    assert.deepEqual(b.get(), a.get());
    assert.equal(score(b.get()), -15);
    assert.ok(storage.getItem("detgame:testgame"));
  });

  test("записи журнала получают время из внедрённых часов", () => {
    const store = createStore({ storage: new MemoryStorage(), gameId: "g", now: clock(), events: null });
    store.update(() => fresh());
    const s = store.update((st) => recordWrong(st, "q", "h", -5));
    assert.equal(s.log[0].t, "2026-11-12T10:00:02.000Z");
    assert.equal(s.log[0].d, -5);
  });

  test("экспорт → импорт → то же состояние", () => {
    const a = createStore({ storage: new MemoryStorage(), gameId: "g", now: clock(), events: null });
    playSome(a);
    const json = a.exportJson();
    const b = createStore({ storage: new MemoryStorage(), gameId: "g", now: clock(), events: null });
    const imported = b.importJson(json);
    assert.deepEqual(imported, a.get());
    assert.deepEqual(b.get(), a.get());
    assert.equal(b.exportJson(), json);
  });

  test("импорт испорченного файла — StateError, состояние не меняется", () => {
    const store = createStore({ storage: new MemoryStorage(), gameId: "g", now: clock(), events: null });
    playSome(store);
    const before = store.get();
    for (const bad of ["не json", "[]", '{"v":99,"saltsId":"x"}', '{"v":1}', '{"v":1,"saltsId":"x","stage":1,"log":[{"d":"5","r":"x"}]}']) {
      assert.throws(() => store.importJson(bad), StateError, bad);
    }
    assert.deepEqual(store.get(), before);
  });

  test("начать заново — состояние удаляется из хранилища", () => {
    const storage = new MemoryStorage();
    const store = createStore({ storage, gameId: "g", now: clock(), events: null });
    playSome(store);
    store.reset();
    assert.equal(store.get(), null);
    assert.equal(storage.getItem("detgame:g"), null);
  });

  test("без localStorage (исключение при доступе) — игра идёт в памяти, persistent=false", () => {
    const store = createStore({ storage: new ThrowingStorage(), gameId: "g", now: clock(), events: null });
    assert.equal(store.persistent, false);
    playSome(store);
    assert.equal(score(store.get()), -15);
    assert.equal(store.get().stage, 2);
    const again = store.update((s) => recordWrong(s, "s1.q2", "h1", -5));
    assert.equal(score(again), -15, "дедупликация работает и в памяти");
    assert.ok(store.exportJson().includes('"saltsId"'));
  });

  test("storage = null — тоже работа в памяти", () => {
    const store = createStore({ storage: null, gameId: "g", now: clock(), events: null });
    assert.equal(store.persistent, false);
    playSome(store);
    assert.equal(score(store.get()), -15);
  });

  test("хранилище отказывает при записи (переполнено) — переход в память без потери данных", () => {
    const storage = new MemoryStorage();
    const store = createStore({ storage, gameId: "g", now: clock(), events: null });
    store.update(() => fresh());
    storage.setItem = () => {
      throw new Error("QuotaExceededError");
    };
    const s = store.update((st) => recordWrong(st, "q", "h", -5));
    assert.equal(store.persistent, false);
    assert.equal(score(s), -5);
    assert.equal(score(store.get()), -5);
  });

  test("повреждённая запись в хранилище — get() = null, флаг corrupt", () => {
    const storage = new MemoryStorage();
    storage.setItem("detgame:g", "{broken");
    const store = createStore({ storage, gameId: "g", now: clock(), events: null });
    assert.equal(store.get(), null);
    assert.equal(store.corrupt, true);
    store.reset();
    assert.equal(store.corrupt, false);
  });

  test("две вкладки: запись перечитывает хранилище и не теряет изменения соседа", () => {
    const storage = new MemoryStorage();
    const tab1 = createStore({ storage, gameId: "g", now: clock(), events: null });
    tab1.update(() => fresh());
    const tab2 = createStore({ storage, gameId: "g", now: clock(), events: null });
    tab1.update((s) => recordWrong(s, "s1.q1", "a", -5)); // tab2 об этом ещё не знает
    tab2.update((s) => labRejected(s, "fp", -5));
    const merged = tab1.update((s) => s);
    assert.deepEqual(
      merged.log.map((e) => e.r),
      ["wrong:s1.q1", "lab:fp"],
    );
    assert.equal(score(tab2.get()), -10);
  });

  test("событие storage от другой вкладки → onExternalChange(state)", () => {
    const storage = new MemoryStorage();
    const events = new EventTarget();
    const tab1 = createStore({ storage, gameId: "g", now: clock(), events });
    const tab2 = createStore({ storage, gameId: "g", now: clock(), events: null });
    tab2.update(() => fresh());
    const seen = [];
    const off = tab1.onExternalChange((s) => seen.push(s));
    tab2.update((s) => recordWrong(s, "q", "h", -5));
    const other = Object.assign(new Event("storage"), { key: "detgame:other" });
    events.dispatchEvent(other);
    assert.equal(seen.length, 0, "чужой ключ игнорируется");
    events.dispatchEvent(Object.assign(new Event("storage"), { key: "detgame:g" }));
    assert.equal(seen.length, 1);
    assert.equal(score(seen[0]), -5);
    assert.equal(score(tab1.get()), -5);
    off();
    events.dispatchEvent(Object.assign(new Event("storage"), { key: "detgame:g" }));
    assert.equal(seen.length, 1, "после отписки событий нет");
  });

  test("несовместимый saltsId — прогресс несовместим", () => {
    const s = fresh();
    assert.equal(isCompatible(s, PUB), true);
    assert.equal(isCompatible(s, { ...PUB, saltsId: "salts-B" }), false);
    assert.equal(isCompatible({ ...s, v: STATE_VERSION + 1 }, PUB), false);
    assert.equal(isCompatible(null, PUB), false);
  });

  test("импорт файла с другим saltsId разбирается, но помечается несовместимым", () => {
    const other = { ...fresh(), saltsId: "salts-OLD" };
    const parsed = parseState(JSON.stringify(other));
    assert.equal(isCompatible(parsed, PUB), false);
  });
});
