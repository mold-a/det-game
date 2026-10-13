// QA: прогон site/assets/js/core/normalize.js по списку входов (для tests/qa/test_qa_normalize_fuzz.py).
// stdin: JSON {"defaultYear": 2026, "cases": [[type, value], …]} → stdout: JSON [result | null | {"error": "…"}, …]
import { normalize } from "../../site/assets/js/core/normalize.js";

let raw = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) raw += chunk;
const { defaultYear, cases } = JSON.parse(raw);
const out = cases.map(([type, value]) => {
  try {
    return normalize(type, value, { defaultYear });
  } catch (e) {
    return { error: String(e && e.message ? e.message : e) };
  }
});
process.stdout.write(JSON.stringify(out));
