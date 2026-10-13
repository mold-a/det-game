// Замер PBKDF2-HMAC-SHA256 (Web Crypto) для итераций из docs/02 §6.
// Запуск: node tests/js/bench_pbkdf2.mjs [повторов]   (по умолчанию 5; печатается медиана)
// На телефоне цель — не больше ~0,4 с на одну проверку; Node на ноутбуке заметно быстрее.
import { pbkdf2, utf8, randomBytes } from "../../site/assets/js/core/crypto.js";

const runs = Number(process.argv[2] ?? 5);
const password = utf8("detgame/answer/v1|s1.q1.time|08:15");

await pbkdf2(password, randomBytes(16), 1000); // прогрев

console.log(`PBKDF2-HMAC-SHA256, 32 байта, Node ${process.version}, медиана из ${runs}`);
for (const iterations of [100_000, 150_000, 300_000]) {
  const times = [];
  for (let i = 0; i < runs; i += 1) {
    const salt = randomBytes(16);
    const t0 = performance.now();
    await pbkdf2(password, salt, iterations);
    times.push(performance.now() - t0);
  }
  times.sort((a, b) => a - b);
  const median = times[Math.floor(times.length / 2)];
  console.log(`${String(iterations).padStart(7)} итераций: ${median.toFixed(1)} мс (мин ${times[0].toFixed(1)}, макс ${times.at(-1).toFixed(1)})`);
}
