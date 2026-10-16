// Подписи вопросов для журнала баллов — одинаковые на «/», «/lab/» и «/final/»:
// «вопрос 2.3» = этап 2, третий вопрос пакета по порядку content/.

/** labelFor(path) по открытым пакетам; путь единицы (s1.q1.time) — по вопросу. */
export function makeLabelFor(packs) {
  return (path) => {
    const m = /^s(\d+)\.([^.:]+)/.exec(String(path));
    if (!m) return path;
    const pack = packs?.[Number(m[1])];
    const idx = pack ? pack.questions.findIndex((q) => q.path === `s${m[1]}.${m[2]}`) : -1;
    return idx >= 0 ? `вопрос ${m[1]}.${idx + 1}` : path;
  };
}
