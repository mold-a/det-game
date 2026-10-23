// Тексты интерфейса: согласование чисел, знак, причины журнала (docs/01 §11).
import { test } from "node:test";
import assert from "node:assert/strict";
import { T, signed, pointsWord, describeLogEntry } from "../../site/assets/js/app/texts.js";

test("знак: типографский минус, плюс у начислений", () => {
  assert.equal(signed(15), "+15");
  assert.equal(signed(-5), "−5");
  assert.equal(signed(0), "0");
});

test("баллы: 1 балл, 2 балла, 5 баллов, 11 баллов, 21 балл", () => {
  assert.deepEqual([1, 2, 5, 11, 21, 40, -20].map(pointsWord), ["балл", "балла", "баллов", "баллов", "балл", "баллов", "баллов"]);
});

test("правила: числа из настроек и родительный падеж после «после»", () => {
  const cfg = { wrongPenalty: -5, hintCosts: [10, 20, 40], autoAfter: 3, bonus: 15, final: 30 };
  const lines = T.rules(cfg);
  assert.ok(lines.length >= 5 && lines.length <= 6);
  assert.match(lines.join(" "), /−5 баллов/);
  assert.match(lines.join(" "), /−10, −20, −40/);
  assert.match(lines.join(" "), /После 3 неверных попыток/);
  assert.match(T.rules({ ...cfg, autoAfter: 1 }).join(" "), /После 1 неверной попытки/);
  assert.match(lines.join(" "), /\+15/);
  assert.match(lines.join(" "), /\+30/);
});

test("подтверждение подсказки и примеры формата — по docs/01, docs/02", () => {
  assert.equal(T.question.hintConfirm(2, 20), "Подсказка 2 уровня: −20 баллов. Открыть?");
  assert.equal(T.result.wrong, "Ответ не подтверждается материалами дела.");
  assert.equal(T.result.repeat, "Этот ответ уже проверяли.");
  // Лаборатория — docs/01 §7 (переработка 21.10.2026).
  assert.equal(T.lab.none, "Сейчас этот предмет нельзя передать в лабораторию.");
  assert.equal(T.lab.nothing, "Экспертиза ничего не выявила.");
  assert.match(T.lab.repeat, /^Такая заявка уже выполнялась/);
  assert.equal(T.lab.ambiguous(["А", "Б"]), "Уточните, какой предмет вы передаёте: «А» или «Б».");
  assert.equal(T.lab.ambiguous(["А", "Б", "В"]), "Уточните, какой предмет вы передаёте: «А», «Б» или «В».");
  assert.match(T.lab.terms(-5), /−5 баллов/);
  assert.equal(T.placeholder.time, "08:15");
  assert.equal(T.placeholder.date, "05.03");
});

test("причины журнала: wrong, hint, bonus, final, lab", () => {
  const label = (p) => `вопрос ${p}`;
  assert.equal(describeLogEntry({ r: "wrong:s1.q2:0a1b2c3d" }, label), "Неверный ответ: вопрос s1.q2");
  assert.equal(describeLogEntry({ r: "wrong:s1.q2" }, label), "Неверный ответ: вопрос s1.q2", "старый формат");
  assert.equal(describeLogEntry({ r: "hint:s1.q2:3" }, label), "Подсказка 3 уровня: вопрос s1.q2");
  assert.equal(describeLogEntry({ r: "bonus:s4.fb" }, label), "Бонус: вопрос s4.fb");
  assert.equal(describeLogEntry({ r: "final:s4.f1" }, label), "Финал: вопрос s4.f1");
  assert.equal(describeLogEntry({ r: "lab:abc" }, label), "Экспертиза ничего не выявила");
});

test("лаборатория: подписи фотографий центра", () => {
  assert.equal(T.lab.photoOpen(""), "Открыть фото крупно");
  assert.equal(T.lab.photoOpen("Вход со двора"), "Открыть фото крупно: Вход со двора");
  assert.ok(T.lab.photos && T.lab.photoAlt);
});
