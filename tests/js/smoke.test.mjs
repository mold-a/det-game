import { test } from "node:test";
import assert from "node:assert/strict";

test("модуль normalize.js импортируется", async () => {
  const mod = await import("../../site/assets/js/core/normalize.js");
  assert.equal(typeof mod, "object");
});

test("Web Crypto доступен в Node", () => {
  assert.equal(typeof globalThis.crypto?.subtle?.deriveBits, "function");
});
