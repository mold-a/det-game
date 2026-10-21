// Время в плеере (звонок и голосовые в «Круге»): «М:СС» ↔ секунды.
import test from "node:test";
import assert from "node:assert/strict";

import { formatTime, parseTime } from "../../site/assets/js/pages/audio-player.js";

test("formatTime: М:СС и Ч:ММ:СС, мусор — 0:00", () => {
  assert.equal(formatTime(0), "0:00");
  assert.equal(formatTime(12.9), "0:12");
  assert.equal(formatTime(75), "1:15");
  assert.equal(formatTime(3725), "1:02:05");
  for (const bad of [NaN, -1, Infinity, undefined]) assert.equal(formatTime(bad), "0:00");
});

test("parseTime: длительность из контента", () => {
  assert.equal(parseTime("0:12"), 12);
  assert.equal(parseTime(" 12:05 "), 725);
  assert.equal(parseTime("1:02:05"), 3725);
  for (const bad of ["", "12", "0:5", "—:—", null]) assert.ok(Number.isNaN(parseTime(bad)), String(bad));
});

test("formatTime(parseTime(x)) возвращает ту же строку", () => {
  for (const s of ["0:12", "0:00", "9:59", "1:02:05"]) assert.equal(formatTime(parseTime(s)), s);
});
