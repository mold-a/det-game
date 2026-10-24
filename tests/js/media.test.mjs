import { test } from "node:test";
import assert from "node:assert/strict";
import { hydrateMedia, mediaUrl, formatSize, whenNear, revokeAll } from "../../site/assets/js/core/media.js";
import { sealMedia, b64uEncode, randomBytes } from "../../site/assets/js/core/crypto.js";

function fakeNode(tag, attrs = {}) {
  const a = { ...attrs };
  return {
    tagName: tag,
    src: "",
    style: {},
    classList: { add() {}, contains: () => false },
    getAttribute: (k) => (k in a ? a[k] : null),
    setAttribute: (k, v) => (a[k] = String(v)),
    removeAttribute: (k) => delete a[k],
  };
}

async function sealedRef(src, plain) {
  const key = randomBytes(32);
  const aad = `media/${src}`;
  const blob = await sealMedia(key, plain, aad);
  return { ref: { src, mime: "video/mp4", size: blob.length, key: b64uEncode(key), aad }, blob };
}

function fakeFetch(files) {
  const calls = [];
  const fn = async (url) => {
    calls.push(url);
    const body = files[url];
    return { ok: true, headers: { get: () => null }, arrayBuffer: async () => body.buffer.slice(body.byteOffset, body.byteOffset + body.length) };
  };
  fn.calls = calls;
  return fn;
}

test("mediaUrl: открытый файл — прямой src, зашифрованный — Blob URL с исходным MIME", async () => {
  assert.equal(await mediaUrl({ src: "/m/a.jpg" }), "/m/a.jpg");
  assert.equal(await mediaUrl({ src: null, missing: true }), null);
  const plain = new Uint8Array([1, 2, 3, 4, 5]);
  const { ref, blob } = await sealedRef("/m/v.bin", plain);
  const fetchFn = fakeFetch({ "/m/v.bin": blob });
  const url = await mediaUrl(ref, { fetchFn });
  assert.match(url, /^blob:/);
  assert.equal(await mediaUrl(ref, { fetchFn }), url); // повторно не качается
  assert.equal(fetchFn.calls.length, 1);
  await revokeAll();
});

test("whenNear: без IntersectionObserver — сразу; с ним — когда узел подошёл к экрану, один раз", () => {
  let n = 0;
  whenNear({}, () => n++);
  assert.equal(n, 1);
  const observers = [];
  globalThis.IntersectionObserver = class {
    constructor(cb, opts) {
      this.cb = cb;
      this.opts = opts;
      this.disconnected = false;
      observers.push(this);
    }
    observe() {}
    disconnect() {
      this.disconnected = true;
    }
  };
  try {
    let m = 0;
    whenNear({}, () => m++);
    const [io] = observers;
    assert.match(io.opts.rootMargin, /px/);
    io.cb([{ isIntersecting: false }]);
    assert.equal(m, 0);
    io.cb([{ isIntersecting: true }]);
    assert.equal(m, 1);
    assert.ok(io.disconnected);
  } finally {
    delete globalThis.IntersectionObserver;
  }
});

test("hydrateMedia: зашифрованные lazy-фото ждут экрана, остальное — сразу", async () => {
  const photo = await sealedRef("/m/p1.bin", new Uint8Array([9, 9, 9]));
  const photo2 = await sealedRef("/m/p2.bin", new Uint8Array([8, 8, 8]));
  const refs = [photo.ref, photo2.ref, { src: "/m/open.jpg", mime: "image/jpeg" }];
  const lazy = fakeNode("IMG", { "data-media": "0", loading: "lazy" });
  const eager = fakeNode("IMG", { "data-media": "1", loading: "eager" });
  const open = fakeNode("IMG", { "data-media": "2", loading: "lazy" });
  const root = { querySelectorAll: () => [lazy, eager, open] };
  const fetchFn = fakeFetch({ "/m/p1.bin": photo.blob, "/m/p2.bin": photo2.blob });
  const observers = [];
  globalThis.IntersectionObserver = class {
    constructor(cb) {
      this.cb = cb;
      observers.push(this);
    }
    observe() {}
    disconnect() {}
  };
  try {
    await hydrateMedia(root, refs, { fetchFn });
    assert.equal(lazy.src, "", "lazy-фото вне экрана не расшифровано");
    assert.deepEqual(fetchFn.calls, ["/m/p2.bin"], "скачано только eager-фото");
    assert.match(eager.src, /^blob:/);
    assert.equal(open.src, "/m/open.jpg"); // открытый файл — прямой src, ждать нечего
    assert.equal(observers.length, 1);
    observers[0].cb([{ isIntersecting: true }]);
    await new Promise((r) => setTimeout(r, 20));
    assert.match(lazy.src, /^blob:/);
    assert.equal(fetchFn.calls.length, 2);
  } finally {
    delete globalThis.IntersectionObserver;
    await revokeAll();
  }
});

test("formatSize: КБ и МБ по-русски", () => {
  assert.equal(formatSize(0), "");
  assert.equal(formatSize(512000), "512 КБ");
  assert.equal(formatSize(5_500_000), "5,5 МБ");
  assert.equal(formatSize(24_000_000), "24 МБ");
  // видео из content/pages/video: 1 376 492 Б → «1,4 МБ» (как в «Свойствах файла»)
  assert.equal(formatSize(1_376_492), "1,4 МБ");
});
