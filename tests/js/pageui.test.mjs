import { test } from "node:test";
import assert from "node:assert/strict";
import { nextTabIndex, sectionFromHash, filterNames, labPhotos, LAB_PHOTOS_MAX } from "../../site/assets/js/core/pageui.js";

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

test("labPhotos: только открытые адреса /m/, не больше трёх, подпись и запасной alt", () => {
  const list = [
    { src: "/m/0123456789abcdef0123456789abcdef.jpg", caption: "  Вход со двора  " },
    { src: "/m/fedcba9876543210fedcba9876543210.png" }, // без подписи — запасной alt
    { src: "https://example.invalid/x.jpg", caption: "чужой адрес" }, // не из /m/ — отбрасывается
    { src: "", caption: "пусто" },
    null,
    { src: "/m/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg", caption: "TODO(content): подпись" }, // заглушка = нет подписи
    { src: "/m/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.jpg", caption: "Четвёртый" }, // сверх лимита
  ];
  const out = labPhotos(list, "Фото центра");
  assert.equal(out.length, LAB_PHOTOS_MAX);
  assert.deepEqual(out[0], { src: "/m/0123456789abcdef0123456789abcdef.jpg", caption: "Вход со двора", alt: "Вход со двора" });
  assert.deepEqual(out[1], { src: "/m/fedcba9876543210fedcba9876543210.png", caption: "", alt: "Фото центра" });
  assert.deepEqual(out[2], { src: "/m/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg", caption: "", alt: "Фото центра" });
  assert.deepEqual(labPhotos(undefined), []);
  assert.deepEqual(labPhotos("не список"), []);
});
