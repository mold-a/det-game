// Состояние игры: чистая логика прогресса без DOM.
// Контракт формата — docs/FORMATS.md §7 (уточняет docs/02 §4); правила — docs/01 §4–8, §10.
//
// Хранилище внедряется извне (localStorage в браузере, заглушка в тестах).
// Все числа — штрафы, цены подсказок, баллы, порог автоподсказки — приходят
// параметрами из public.json; здесь констант правил нет.
//
// Редьюсеры чистые: принимают состояние и возвращают НОВОЕ состояние.
// Если действие не применимо (повтор, неверный порядок, вопрос уже закрыт),
// редьюсер возвращает тот же объект — вызывающий код сравнивает `next === s`.
//
// Время `t` в записях журнала (log, lab.log) ставит store.update() по внедрённым
// часам `now`, поэтому сами редьюсеры от времени не зависят.
//
// Причины в журнале log[].r (FORMATS F16, §7.2), log содержит только d ≠ 0.
// Причина уникальна для события — по ней сливаются вкладки (одно событие = одна запись):
//   wrong:<qpath>:<hash8>   новый неверный ответ на обязательный вопрос (8 hex wrongHash)
//   hint:<qpath>:<level>    покупка подсказки (бесплатная автоподсказка не пишется)
//   bonus:<qpath>           верный бонус (этапы 1–3 сразу, этап 4 — в finalFinish)
//   final:<qpath>           верный финальный ответ (только в finalFinish)
//   lab:<fp>                новый отклонённый запрос в лабораторию

export const STATE_VERSION = 1;
export const STORAGE_PREFIX = "detgame:";
const PROBE_SUFFIX = ":probe";
const UNIT_RANK = { closed: 1, solved: 2 };

// ---------------------------------------------------------------- утилиты

const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isInt = (v) => Number.isInteger(v);
const neg = (n) => -Math.abs(num(n));
const pos = (n) => Math.abs(num(n));

function num(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) {
    throw new TypeError(`Ожидалось число из настроек, получено: ${String(n)}`);
  }
  return n;
}

function toIso(value) {
  const d = value instanceof Date ? value : new Date(value);
  return d.toISOString();
}

function addLog(s, d, r) {
  if (d !== 0) s.log.push({ d, r });
}

export class StateError extends Error {
  constructor(code, message) {
    super(message || code);
    this.name = "StateError";
    this.code = code; // "parse" | "shape" | "version"
  }
}

// ---------------------------------------------------------------- создание и проверка формы

/** Новое состояние первого запуска (FORMATS §7). keys — { "1": K1 } при старте. */
export function newState({ gameId, saltsId, buildId = "", team = "", startedAt, stage = 1, keys = {} }) {
  return {
    v: STATE_VERSION,
    gameId,
    saltsId,
    buildId,
    team,
    startedAt,
    stage,
    envelopeAck: stage, // конверт №1 вскрывается на экране первого запуска
    finished: false,
    keys: { ...keys },
    units: {},
    wrong: {},
    hints: {},
    lab: { done: {}, rejected: [], log: [] },
    docs: [],
    final: { started: false, index: 0, answers: {}, correct: null },
    log: [],
  };
}

/**
 * Проверяет форму объекта и дополняет отсутствующие необязательные разделы.
 * Бросает StateError("shape" | "version"). Возвращает новый объект.
 */
export function normalizeState(raw) {
  if (!isObj(raw)) throw new StateError("shape", "Прогресс — не объект");
  if (raw.v !== STATE_VERSION) throw new StateError("version", `Версия прогресса ${raw.v}`);
  if (typeof raw.saltsId !== "string" || !raw.saltsId) {
    throw new StateError("shape", "Нет saltsId");
  }
  const s = clone(raw);
  for (const k of ["gameId", "buildId", "team", "startedAt"]) {
    s[k] = typeof s[k] === "string" ? s[k] : "";
  }
  if (!isInt(s.stage) || s.stage < 1) throw new StateError("shape", "Неверный этап");
  s.envelopeAck = isInt(s.envelopeAck) ? s.envelopeAck : s.stage;
  s.finished = s.finished === true;
  for (const k of ["keys", "units", "wrong", "hints"]) {
    if (s[k] === undefined) s[k] = {};
    if (!isObj(s[k])) throw new StateError("shape", `Раздел ${k} — не объект`);
  }
  for (const [p, u] of Object.entries(s.units)) {
    if (!isObj(u) || !(u.status in UNIT_RANK)) throw new StateError("shape", `units.${p}`);
    if (u.canon === undefined) u.canon = null;
    if (u.given === undefined) u.given = null;
  }
  for (const [p, list] of Object.entries(s.wrong)) {
    if (!Array.isArray(list) || !list.every((x) => typeof x === "string")) {
      throw new StateError("shape", `wrong.${p}`);
    }
  }
  for (const [p, lvl] of Object.entries(s.hints)) {
    if (!isInt(lvl) || lvl < 0) throw new StateError("shape", `hints.${p}`);
  }
  s.lab = isObj(s.lab) ? s.lab : {};
  s.lab.done = isObj(s.lab.done) ? s.lab.done : {};
  s.lab.rejected = Array.isArray(s.lab.rejected) ? s.lab.rejected : [];
  s.lab.log = Array.isArray(s.lab.log) ? s.lab.log.filter(isObj) : [];
  s.docs = Array.isArray(s.docs) ? s.docs : [];
  s.final = isObj(s.final) ? s.final : {};
  s.final.started = s.final.started === true;
  s.final.index = isInt(s.final.index) ? s.final.index : 0;
  s.final.answers = isObj(s.final.answers) ? s.final.answers : {};
  s.final.correct = isObj(s.final.correct) ? s.final.correct : null;
  if (!Array.isArray(s.log)) throw new StateError("shape", "Журнал — не список");
  for (const e of s.log) {
    if (!isObj(e) || typeof e.d !== "number" || !Number.isFinite(e.d) || typeof e.r !== "string") {
      throw new StateError("shape", "Запись журнала повреждена");
    }
  }
  return s;
}

/** Разбор JSON прогресса (файл или localStorage). Бросает StateError. */
export function parseState(text) {
  let raw;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new StateError("parse", "Файл прогресса не читается");
  }
  return normalizeState(raw);
}

/**
 * Совместимость прогресса со сборкой (синхронная часть): версия, gameId, saltsId.
 * Вторая часть — keys[stage] открывает pack-<stage> — асинхронная, в core/game.js.
 */
export function isCompatible(s, pub) {
  if (!s || !pub) return false;
  if (s.v !== STATE_VERSION || s.saltsId !== pub.saltsId) return false;
  return !s.gameId || !pub.gameId || s.gameId === pub.gameId;
}

/** Имя файла экспорта: detgame-<gameId>-<YYYYMMDD-HHMM>.json (местное время). */
export function exportFileName(gameId, date = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  const stamp =
    `${date.getFullYear()}${p(date.getMonth() + 1)}${p(date.getDate())}` +
    `-${p(date.getHours())}${p(date.getMinutes())}`;
  return `detgame-${gameId}-${stamp}.json`;
}

// ---------------------------------------------------------------- чтение

export const score = (s) => s.log.reduce((sum, e) => sum + e.d, 0);
export const unitStatus = (s, qpath) => s.units[qpath]?.status ?? "open";
export const isSolved = (s, qpath) => unitStatus(s, qpath) === "solved";
export const isClosed = (s, qpath) => unitStatus(s, qpath) !== "open";
export const wrongCount = (s, qpath) => (s.wrong[qpath] ?? []).length;
export const wasTried = (s, qpath, hash) => (s.wrong[qpath] ?? []).includes(hash);
export const hintLevel = (s, qpath) => s.hints[qpath] ?? 0;
export const labSeen = (s, fp) => fp in s.lab.done || s.lab.rejected.includes(fp);
/** Номер конверта, для которого нужно показать окно «Откройте конверт №N», или null (F14). */
export const pendingEnvelope = (s) => (s.stage > s.envelopeAck ? s.stage : null);

// ---------------------------------------------------------------- вопросы

/** Причина журнала для неверного ответа: уникальна для пары (вопрос, ответ). */
export const wrongReason = (qpath, hash) => `wrong:${qpath}:${String(hash).slice(0, 8)}`;

/**
 * Неверная попытка обязательного вопроса. Тот же хеш (FORMATS §7.1) повторно
 * не штрафуется (docs/01 §4) — возвращается то же состояние.
 */
export function recordWrong(s, qpath, hash, penalty) {
  const d = neg(penalty);
  if (isClosed(s, qpath) || wasTried(s, qpath, hash)) return s;
  const n = clone(s);
  (n.wrong[qpath] ??= []).push(hash);
  addLog(n, d, wrongReason(qpath, hash));
  return n;
}

/**
 * Покупка подсказки: строго следующий уровень (1 → 2 → 3), цена — из настроек
 * (hints.cost[level-1]). После решения вопроса подсказки не продаются.
 */
export function buyHint(s, qpath, level, cost) {
  const d = neg(cost);
  if (isSolved(s, qpath) || level !== hintLevel(s, qpath) + 1) return s;
  const n = clone(s);
  n.hints[qpath] = level;
  addLog(n, d, `hint:${qpath}:${level}`);
  return n;
}

/**
 * Автоподсказка: после `threshold` неверных попыток уровень 1 открывается
 * бесплатно, если ещё не открыт. В журнал не пишется (F16).
 */
export function maybeAutoHint(s, qpath, threshold) {
  num(threshold);
  if (isSolved(s, qpath) || hintLevel(s, qpath) >= 1 || wrongCount(s, qpath) < threshold) return s;
  const n = clone(s);
  n.hints[qpath] = 1;
  return n;
}

/** Обязательный вопрос решён. Баллов не даёт (docs/01 §6). canon — строка или {fieldId: canon}. */
export function solve(s, qpath, canon) {
  if (isClosed(s, qpath)) return s;
  const n = clone(s);
  n.units[qpath] = { status: "solved", canon: clone(canon), given: null };
  return n;
}

/**
 * Бонусный вопрос этапов 1–3: одна попытка (docs/01 §4). Верно — +points,
 * неверно — 0 и вопрос закрывается; нормализованный ответ команды — в `given`.
 * После начала финала бонусы прошлых этапов закрыты (docs/01 §2).
 */
export function bonusAnswer(s, qpath, { correct, canon = null, given = null, points }) {
  const p = pos(points);
  if (isClosed(s, qpath) || s.final.started || s.finished) return s;
  const n = clone(s);
  n.units[qpath] = correct
    ? { status: "solved", canon: clone(canon), given: null }
    : { status: "closed", canon: null, given: clone(given) };
  if (correct) addLog(n, p, `bonus:${qpath}`);
  return n;
}

// ---------------------------------------------------------------- этапы

/** Переход на этап n: сохраняется ключ этапа (b64u). Этап назад не откатывается. */
export function advanceStage(s, n, keyB64) {
  if (!isInt(n) || n < 1) throw new TypeError("Номер этапа");
  if (s.keys[n] === keyB64 && s.stage >= n) return s;
  const next = clone(s);
  next.keys[n] = keyB64;
  next.stage = Math.max(next.stage, n);
  return next;
}

/** Нажато «Конверт вскрыт» для этапа n (F14). */
export function ackEnvelope(s, n) {
  if (s.envelopeAck >= n) return s;
  const next = clone(s);
  next.envelopeAck = Math.min(n, next.stage);
  return next;
}

// ---------------------------------------------------------------- лаборатория

function pushLabLog(n, fp, req, ok, doc) {
  if (!req) return;
  n.lab.log.push({
    fp,
    object: req.object,
    type: req.type,
    basis: req.basis,
    params: clone(req.params ?? []),
    stage: req.stage ?? n.stage,
    ok,
    doc,
  });
}

/**
 * Экспертиза выполнена. docId — документ результата или null (атмосферный
 * результат, F8). Ранее отклонённый запрос может сработать после перехода
 * этапа — его fp переносится в done. Без штрафа.
 * req (необязательно) — { object, type, basis, params, stage } для архива lab.log (F15).
 */
export function labDone(s, fp, docId, req = null) {
  const id = docId ?? null;
  if (fp in s.lab.done && s.lab.done[fp] === id) return s;
  const n = clone(s);
  n.lab.done[fp] = id;
  n.lab.rejected = n.lab.rejected.filter((x) => x !== fp);
  if (id !== null && !n.docs.includes(id)) n.docs.push(id);
  pushLabLog(n, fp, req, true, id);
  return n;
}

/** Запрос без оснований: штраф один раз на отпечаток запроса; повтор — без штрафа. */
export function labRejected(s, fp, penalty, req = null) {
  const d = neg(penalty);
  if (labSeen(s, fp)) return s;
  const n = clone(s);
  n.lab.rejected.push(fp);
  addLog(n, d, `lab:${fp}`);
  pushLabLog(n, fp, req, false, null);
  return n;
}

// ---------------------------------------------------------------- финал

/**
 * Нажато «Начать финал». Все неотвеченные бонусы этапов 1–3 закрываются
 * (FORMATS §7). bonusPaths — пути бонусных вопросов открытых этапов 1–3.
 */
export function finalStart(s, bonusPaths = []) {
  if (s.final.started || s.finished) return s;
  const n = clone(s);
  n.final.started = true;
  for (const qpath of bonusPaths) {
    if (!(qpath in n.units)) n.units[qpath] = { status: "closed", canon: null, given: null };
  }
  return n;
}

/**
 * Ответ финала фиксируется (одна попытка, вернуться нельзя). Баллы не
 * пишутся — счёт до конца финала не меняется (docs/01 §8).
 * value — нормализованное значение (для формы — объект по полям).
 */
export function finalSubmit(s, qpath, value) {
  if (!s.final.started || s.finished || qpath in s.final.answers) return s;
  const n = clone(s);
  n.final.answers[qpath] = clone(value);
  n.final.index = Object.keys(n.final.answers).length;
  return n;
}

/**
 * Конец финала: проверка выполнена один раз, баллы за верные ответы этапа 4
 * пишутся в журнал разом, final.correct = {qpath: bool}.
 *   results: { [qpath]: { correct: boolean, kind: "final" | "bonus" } }
 *   points:  public.points — { final, bonus }.
 */
export function finalFinish(s, results, points) {
  if (s.finished) return s;
  const n = clone(s);
  n.final.correct = {};
  for (const [qpath, res] of Object.entries(results)) {
    const ok = res?.correct === true;
    n.final.correct[qpath] = ok;
    if (!ok) continue;
    const kind = res.kind === "bonus" ? "bonus" : "final";
    addLog(n, pos(points[kind]), `${kind}:${qpath}`);
  }
  n.finished = true;
  return n;
}

// ---------------------------------------------------------------- слияние вкладок (FORMATS §7.2)

/** Та же партия: одинаковые saltsId и startedAt (иначе другая вкладка начала заново). */
export function sameGame(a, b) {
  return Boolean(a && b && a.saltsId === b.saltsId && a.startedAt === b.startedAt);
}

function unionBy(a, b, keyOf) {
  const seen = new Set(a.map(keyOf));
  const out = a.slice();
  for (const x of b) {
    const k = keyOf(x);
    if (!seen.has(k)) {
      seen.add(k);
      out.push(x);
    }
  }
  return out;
}

const byTime = (x, y) => (x.t ?? "") < (y.t ?? "") ? -1 : (x.t ?? "") > (y.t ?? "") ? 1 : 0;
const union = (a, b) => unionBy(a, b, (x) => x);

/**
 * Ключ события журнала: сама причина `r` (она уникальна для события, F16/§7.2).
 * Старый формат `wrong:<qpath>` без хеша повторялся законно — для него ключ (r, t).
 */
const logKey = (e) => (/^wrong:[^:]+$/.test(e.r) ? `${e.r}|${e.t}` : e.r);

/** Объединение журналов по событию; из дубликатов остаётся самая ранняя запись. */
function mergeLog(a, b) {
  const byKey = new Map();
  for (const e of [...a, ...b]) {
    const k = logKey(e);
    const prev = byKey.get(k);
    if (!prev || byTime(e, prev) < 0) byKey.set(k, e);
  }
  return [...byKey.values()].sort(byTime);
}

/**
 * Слить локальную копию с внешней (из хранилища): журналы — объединение,
 * множества — объединение, словари — по ключам с «продвинутым» значением,
 * этап, конверт и индекс финала — максимум. Внешняя версия — основа.
 */
export function mergeStates(local, external) {
  const m = clone(external);
  const l = local;
  m.stage = Math.max(m.stage, l.stage);
  m.envelopeAck = Math.max(m.envelopeAck, l.envelopeAck);
  m.finished = m.finished || l.finished;
  for (const [k, v] of Object.entries(l.keys)) if (!(k in m.keys)) m.keys[k] = v;
  for (const [p, u] of Object.entries(l.units)) {
    if (!(p in m.units) || UNIT_RANK[u.status] > UNIT_RANK[m.units[p].status]) m.units[p] = clone(u);
  }
  for (const [p, list] of Object.entries(l.wrong)) m.wrong[p] = union(m.wrong[p] ?? [], list);
  for (const [p, lvl] of Object.entries(l.hints)) m.hints[p] = Math.max(m.hints[p] ?? 0, lvl);
  for (const [fp, doc] of Object.entries(l.lab.done)) {
    if (!(fp in m.lab.done) || (m.lab.done[fp] === null && doc !== null)) m.lab.done[fp] = doc;
  }
  m.lab.rejected = union(m.lab.rejected, l.lab.rejected).filter((fp) => !(fp in m.lab.done));
  m.lab.log = unionBy(m.lab.log, l.lab.log, (e) => `${e.fp}|${e.ok}`).sort(byTime);
  m.docs = union(m.docs, l.docs);
  m.final.started = m.final.started || l.final.started;
  for (const [p, v] of Object.entries(l.final.answers)) if (!(p in m.final.answers)) m.final.answers[p] = clone(v);
  m.final.index = Math.max(m.final.index, l.final.index, Object.keys(m.final.answers).length);
  m.final.correct = m.final.correct ?? clone(l.final.correct);
  m.log = mergeLog(m.log, l.log);
  return m;
}

/** Каноническая строка состояния (ключи по алфавиту) — чтобы понять, изменило ли слияние что-то. */
export function canonicalJson(v) {
  if (Array.isArray(v)) return `[${v.map(canonicalJson).join(",")}]`;
  if (isObj(v)) return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(v[k])}`).join(",")}}`;
  return JSON.stringify(v);
}

// ---------------------------------------------------------------- хранилище

/**
 * createStore({ storage, gameId, now, events })
 *   storage — объект с getItem/setItem/removeItem (localStorage) или null;
 *   gameId  — public.gameId, ключ `detgame:<gameId>`;
 *   now     — часы, () => Date | number | string (по умолчанию Date.now);
 *   events  — цель событий `storage` (по умолчанию globalThis, если умеет addEventListener).
 *
 * Если хранилища нет или оно бросает исключение, игра работает в памяти,
 * `persistent` = false (интерфейс предупреждает, что прогресс не сохранится).
 *
 * Несколько вкладок (FORMATS §7.2): update() перечитывает хранилище, сливает
 * с локальной копией той же партии, применяет изменение и записывает; событие
 * `storage` от другой вкладки вызывает onExternalChange(state).
 */
export function createStore({ storage = null, gameId, now = Date.now, events } = {}) {
  if (!gameId) throw new TypeError("gameId обязателен");
  const key = STORAGE_PREFIX + gameId;
  const target =
    events !== undefined
      ? events
      : typeof globalThis.addEventListener === "function"
        ? globalThis
        : null;

  let persistent = probe(storage, key);
  let memory = null; // последняя известная этой вкладке версия
  let corrupt = false; // в хранилище лежит нечитаемый прогресс

  function probe(st, k) {
    if (!st) return false;
    try {
      st.setItem(k + PROBE_SUFFIX, "1");
      st.removeItem(k + PROBE_SUFFIX);
      return true;
    } catch {
      return false;
    }
  }

  /** Версия из хранилища; без хранилища — из памяти. */
  function readStorage() {
    if (!persistent) return memory;
    let raw;
    try {
      raw = storage.getItem(key);
    } catch {
      persistent = false;
      return memory;
    }
    if (raw === null || raw === undefined) {
      corrupt = false;
      return null;
    }
    try {
      const s = parseState(raw);
      corrupt = false;
      return s;
    } catch {
      corrupt = true;
      return null;
    }
  }

  function write(s) {
    memory = clone(s);
    if (!persistent) return;
    try {
      if (s === null) storage.removeItem(key);
      else storage.setItem(key, JSON.stringify(s));
      corrupt = false;
    } catch {
      persistent = false; // переполнение или запрет — дальше в памяти
    }
  }

  function stampNew(s) {
    const t = toIso(now());
    for (let i = 0; i < s.log.length; i++) if (!s.log[i].t) s.log[i] = { t, ...s.log[i] };
    for (let i = 0; i < s.lab.log.length; i++) if (!s.lab.log[i].t) s.lab.log[i] = { t, ...s.lab.log[i] };
  }

  /** Актуальная основа для изменения: внешняя версия, слитая с локальной той же партии. */
  function current() {
    const ext = readStorage();
    if (!persistent) return memory;
    if (ext && memory && ext !== memory && sameGame(memory, ext)) return mergeStates(memory, ext);
    return ext; // null — другая вкладка начала заново
  }

  memory = readStorage();
  const listeners = new Set();

  /**
   * Событие storage из другой вкладки: слить внешнюю версию с локальной. Если в
   * локальной было то, чего нет во внешней (запись другой вкладки её затёрла), —
   * записать слитую обратно. Пишем только при реальном отличии канонической формы,
   * поэтому вкладки не перекидываются записями бесконечно.
   */
  function onStorage(e) {
    if (e && e.key !== key && e.key !== null) return;
    const ext = readStorage();
    if (persistent && ext && memory && sameGame(memory, ext)) {
      const merged = mergeStates(memory, ext);
      if (canonicalJson(merged) !== canonicalJson(mergeStates(ext, ext))) write(merged);
      else memory = ext;
    } else {
      memory = persistent ? ext : memory;
    }
    const snapshot = clone(memory);
    for (const cb of listeners) cb(snapshot);
  }

  return {
    key,
    get persistent() {
      return persistent;
    },
    /** В хранилище лежит повреждённый прогресс (get() вернул null). */
    get corrupt() {
      return corrupt;
    },
    /** Текущее состояние (копия) или null, если игра не начата. */
    get() {
      return clone(memory);
    },
    /**
     * Перечитать → слить → применить fn(state) → записать. fn получает копию
     * (или null до начала игры) и возвращает новое состояние или null (сброс).
     * Возвращает записанное состояние.
     */
    update(fn) {
      const base = current();
      const next = fn(clone(base));
      if (next === undefined) throw new TypeError("update: функция должна вернуть состояние");
      if (next === null) {
        write(null);
      } else {
        const checked = normalizeState(next);
        stampNew(checked);
        write(checked);
      }
      return clone(memory);
    },
    exportJson() {
      return JSON.stringify(current() ?? memory, null, 2) + "\n";
    },
    /** Импорт файла прогресса. Бросает StateError; совместимость проверяет вызывающий. */
    importJson(text) {
      const s = parseState(text);
      write(s);
      return clone(memory);
    },
    reset() {
      write(null);
      corrupt = false;
    },
    /** Подписка на изменения из другой вкладки. Возвращает функцию отписки. */
    onExternalChange(cb) {
      listeners.add(cb);
      if (listeners.size === 1 && target) target.addEventListener("storage", onStorage);
      return () => {
        listeners.delete(cb);
        if (listeners.size === 0 && target) target.removeEventListener("storage", onStorage);
      };
    },
  };
}
