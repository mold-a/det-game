import { test } from "node:test";
import assert from "node:assert/strict";
import { paragraphs, nextTabIndex, sectionFromHash, filterNames } from "../../site/assets/js/core/pageui.js";

test("paragraphs: абзацы по переводу строки, пустые отброшены", () => {
  assert.deepEqual(paragraphs("Первый.\n\nВторой.\n  \nТретий."), ["Первый.", "Второй.", "Третий."]);
  assert.deepEqual(paragraphs(""), []);
  assert.deepEqual(paragraphs(null), []);
});

test("nextTabIndex: стрелки зациклены, Home/End, чужая клавиша — null", () => {
  assert.equal(nextTabIndex("ArrowRight", 2, 3), 0);
  assert.equal(nextTabIndex("ArrowLeft", 0, 3), 2);
  assert.equal(nextTabIndex("Home", 2, 3), 0);
  assert.equal(nextTabIndex("End", 0, 3), 2);
  assert.equal(nextTabIndex("Enter", 0, 3), null);
  assert.equal(nextTabIndex("ArrowRight", 0, 0), null);
});

test("sectionFromHash: известный раздел, пустой и чужой адрес — первый", () => {
  const ids = ["afisha", "troupe", "contacts"];
  assert.equal(sectionFromHash("#troupe", ids), "troupe");
  assert.equal(sectionFromHash("", ids), "afisha");
  assert.equal(sectionFromHash("#nope", ids), "afisha");
  assert.equal(sectionFromHash("#%E0%A4%A", ids), "afisha"); // битая кодировка не ломает
  assert.equal(sectionFromHash("#k=abc", ids), "afisha"); // ключ страницы — не раздел
});

test("filterNames: регистр, «ё», подстрока, пустой запрос", () => {
  const names = ["Громова Елена Петровна", "Вольская Тамара", "Сазонов Глеб"];
  assert.deepEqual(filterNames(names, "ГРОМ"), [true, false, false]);
  assert.deepEqual(filterNames(names, "елена"), [true, false, false]);
  assert.deepEqual(filterNames(["Фёдоров Артём"], "федоров артем"), [true]);
  assert.deepEqual(filterNames(names, ""), [true, true, true]);
  assert.deepEqual(filterNames(names, "ничего"), [false, false, false]);
});
