import { test } from "node:test";
import assert from "node:assert/strict";
import { nextTabIndex, sectionFromHash, searchPeople, PEOPLE_MIN, PEOPLE_MAX, labPhotos, LAB_PHOTOS_MAX } from "../../site/assets/js/core/pageui.js";

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

const PEOPLE = ["Громова Елена Петровна", "Вольская Тамара", "Сазонов Глеб", "Фёдоров Артём", "Громов Игорь", "Елена Прекрасная"];

test("searchPeople: пустой запрос и короче трёх букв — ничего", () => {
  assert.equal(PEOPLE_MIN, 3);
  assert.deepEqual(searchPeople(PEOPLE, ""), { status: "idle", indices: [] });
  assert.deepEqual(searchPeople(PEOPLE, "   "), { status: "idle", indices: [] });
  assert.deepEqual(searchPeople(PEOPLE, "гр"), { status: "short", indices: [] });
  assert.deepEqual(searchPeople(PEOPLE, "г р"), { status: "short", indices: [] });
  assert.deepEqual(searchPeople(PEOPLE, "-,."), { status: "idle", indices: [] }); // одни знаки — как пустой
});

test("searchPeople: начало имени или фамилии, без регистра и «ё»", () => {
  assert.deepEqual(searchPeople(PEOPLE, "ГРОМ"), { status: "found", indices: [0, 4] });
  assert.deepEqual(searchPeople(PEOPLE, "тамар").indices, [1]); // имя
  assert.deepEqual(searchPeople(PEOPLE, "вольс").indices, [1]); // фамилия
  assert.deepEqual(searchPeople(PEOPLE, "федоров артем").indices, [3]); // «ё», два слова
  assert.deepEqual(searchPeople(PEOPLE, "елена гром").indices, [0]); // слова в любом порядке
});

test("searchPeople: подстрока внутри слова и отчество не считаются", () => {
  assert.equal(searchPeople(PEOPLE, "мова").status, "none"); // середина слова
  assert.equal(searchPeople(PEOPLE, "петров").status, "none"); // отчество
  assert.deepEqual(searchPeople(PEOPLE, "ничего"), { status: "none", indices: [] });
});

test("searchPeople: не больше пяти результатов, в порядке списка", () => {
  assert.equal(PEOPLE_MAX, 5);
  const many = Array.from({ length: 9 }, (_, i) => `Иванов Иван${i}`);
  const r = searchPeople(many, "иван");
  assert.equal(r.status, "found");
  assert.deepEqual(r.indices, [0, 1, 2, 3, 4]);
  assert.deepEqual(searchPeople(many, "иван", { max: 2 }).indices, [0, 1]);
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
