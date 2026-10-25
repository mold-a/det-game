// Страница типа video (закрытая video и открытая archive): модуль не трогает открытый <video> и
// расшифровывает постер закрытой страницы. DOM заменён минимальными заглушками.
import test from "node:test";
import assert from "node:assert/strict";

import { init } from "../../site/assets/js/pages/video.js";

function fakeVideo(attrs) {
  const a = new Map(Object.entries(attrs));
  return {
    poster: "",
    getAttribute: (k) => (a.has(k) ? a.get(k) : null),
    removeAttribute: (k) => a.delete(k),
    setAttribute: (k, v) => a.set(k, v),
    has: (k) => a.has(k),
  };
}

function fakeRoot(video) {
  const noop = () => {};
  const player = {
    dataset: {},
    classList: { add: noop, remove: noop },
    querySelector: (sel) => (sel === "video" ? video : { hidden: true, addEventListener: noop, textContent: "", style: {} }),
  };
  return {
    querySelector: (sel) => (sel === '[data-player="video"]' ? player : null), // кнопки «Свойства файла» нет
  };
}

test("открытая страница (archive): без payload видео и постер остаются как в разметке", () => {
  const video = fakeVideo({ src: "/m/aaa.mp4", poster: "/m/bbb.jpg", controls: "" });
  init(fakeRoot(video), null);
  assert.ok(video.has("controls") && video.has("src") && video.has("poster"));
});

test("открытая страница: payload.media без ключа — тоже ничего не меняется", () => {
  const video = fakeVideo({ "data-media": "0", controls: "" });
  init(fakeRoot(video), { media: [{ src: "/m/aaa.mp4", mime: "video/mp4", size: 10 }] });
  assert.ok(video.has("data-media") && video.has("controls"));
});

test("закрытая страница: загрузка по кнопке — controls и data-media сняты", () => {
  const video = fakeVideo({ "data-media": "0", "data-poster-media": "1", controls: "" });
  const refs = [
    { src: "/m/v.bin", mime: "video/mp4", size: 100, key: "k", aad: "media/v" },
    { src: "/m/p.bin", mime: "image/jpeg", size: 10, missing: true }, // постер не найден: видео работает без него
  ];
  init(fakeRoot(video), { media: refs });
  assert.ok(!video.has("data-media") && !video.has("controls"));
  assert.equal(video.poster, "");
});
