// Состояние игры: чистая логика прогресса без DOM (docs/02 §4, docs/01 §4–8, §10).
//
// Хранилище внедряется извне (localStorage в браузере, заглушка в тестах).
// Все числа — штрафы, цены подсказок, баллы, порог автоподсказки — приходят
// параметрами из public.json; здесь констант правил нет.
//
// Редьюсеры чистые: принимают состояние и возвращают НОВОЕ состояние.
// Если действие не применимо (повтор, неверный порядок, вопрос уже закрыт),
// редьюсер возвращает тот же объект — вызывающий код сравнивает `next === s`.
//
// Записи журнала, созданные редьюсером, получают время `t` в store.update()
// (часы внедряются через `now`), поэтому сами редьюсеры от времени не зависят.
//
// Причины в журнале (log[].r):
//   wrong:<path>            неверная попытка обязательного вопроса
//   hint:<path>:<level>     купленная подсказка
//   bonus:<path>            верный бонусный ответ (этапы 1–3 сразу, этап 4 — в finalFinish)
//   final:<path>            верный финальный ответ (только в finalFinish)
//   lab:<fp>                запрос в лабораторию без оснований
// TODO(formats): сверить причины и поля с docs/FORMATS.md, когда он появится.

export const STATE_VERSION = 1;
export const STORAGE_PREFIX = "detgame:";
const PROBE_SUFFIX = ":probe";

// ---------------------------------------------------------------- утилиты

const clone = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
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
  s.log.push({ d, r });
}

export class StateError extends Error {
  constructor(code, message) {
    super(message || code);
    this.name = "StateError";
    this.code = code; // "parse" | "shape" | "version"
  }
}

// ---------------------------------------------------------------- создание и проверка формы

/** Новое состояние первого запуска. */
export function newState({ saltsId, buildId = "", team = "", startedAt, stage = 1, keys = {} }) {
  return {
    v: STATE_VERSION,
    saltsId,
    buildId,
    team,
    startedAt,
    stage,
    finished: false,
    keys: { ...keys },
    units: {},
    wrong: {},
    hints: {},
    lab: { done: {}, rejected: [] },
    docs: [],
    final: { index: 0, answers: {} },
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
  s.buildId = typeof s.buildId === "string" ? s.buildId : "";
  s.team = typeof s.team === "string" ? s.team : "";
  s.startedAt = typeof s.startedAt === "string" ? s.startedAt : "";
  if (!Number.isInteger(s.stage) || s.stage < 1) throw new StateError("shape", "Неверный этап");
  s.finished = s.finished === true;
  for (const k of ["keys", "units", "wrong", "hints"]) {
    if (s[k] === undefined) s[k] = {};
    if (!isObj(s[k])) throw new StateError("shape", `Раздел ${k} — не объект`);
  }
  for (const [p, list] of Object.entries(s.wrong)) {
    if (!Array.isArray(list) || !list.every((x) => typeof x === "string")) {
      throw new StateError("shape", `wrong.${p}`);
    }
  }
  for (const [p, lvl] of Object.entries(s.hints)) {
    if (!Number.isInteger(lvl) || lvl < 0) throw new StateError("shape", `hints.${p}`);
  }
  s.lab = isObj(s.lab) ? s.lab : {};
  s.lab.done = isObj(s.lab.done) ? s.lab.done : {};
  s.lab.rejected = Array.isArray(s.lab.rejected) ? s.lab.rejected : [];
  s.docs = Array.isArray(s.docs) ? s.docs : [];
  s.final = isObj(s.final) ? s.final : {};
  s.final.index = Number.isInteger(s.final.index) ? s.final.index : 0;
  s.final.answers = isObj(s.final.answers) ? s.final.answers : {};
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
 * Совместимость прогресса со сборкой (синхронная часть): версия и saltsId.
 * Вторая часть проверки — расшифровка пакета сохранённым ключом — асинхронная
 * и выполняется в core/game.js.
 */
export function isCompatible(s, pub) {
  return Boolean(s && pub && s.v === STATE_VERSION && s.saltsId === pub.saltsId);
}

// ---------------------------------------------------------------- чтение

export const score = (s) => s.log.reduce((sum, e) => sum + e.d, 0);
export const unitStatus = (s, path) => s.units[path]?.status ?? "open";
export const isSolved = (s, path) => unitStatus(s, path) === "solved";
export const isClosed = (s, path) => unitStatus(s, path) !== "open";
export const wrongCount = (s, path) => (s.wrong[path] ?? []).length;
export const wasTried = (s, path, hash) => (s.wrong[path] ?? []).includes(hash);
export const hintLevel = (s, path) => s.hints[path] ?? 0;
export const isFinalStarted = (s) =>
  s.final.index > 0 || Object.keys(s.final.answers).length > 0;
export const labSeen = (s, fp) => fp in s.lab.done || s.lab.rejected.includes(fp);

// ---------------------------------------------------------------- редьюсеры

/**
 * Неверная попытка обязательного вопроса. Тот же хеш нормализованного ввода
 * повторно не штрафуется (docs/01 §4) — возвращается то же состояние.
 */
export function recordWrong(s, path, hash, penalty) {
  const d = neg(penalty);
  if (isClosed(s, path) || wasTried(s, path, hash)) return s;
  const n = clone(s);
  (n.wrong[path] ??= []).push(hash);
  addLog(n, d, `wrong:${path}`);
  return n;
}

/**
 * Покупка подсказки: строго следующий уровень (1 → 2 → 3), цена — из настроек
 * (hints.cost[level-1]). После решения вопроса подсказки не продаются.
 */
export function buyHint(s, path, level, cost) {
  const d = neg(cost);
  if (isSolved(s, path) || level !== hintLevel(s, path) + 1) return s;
  const n = clone(s);
  n.hints[path] = level;
  addLog(n, d, `hint:${path}:${level}`);
  return n;
}

/**
 * Автоподсказка: после `threshold` неверных попыток уровень 1 открывается
 * бесплатно, если ещё не открыт. В журнал не пишется — баллы не меняются.
 */
export function maybeAutoHint(s, path, threshold) {
  num(threshold);
  if (isSolved(s, path) || hintLevel(s, path) >= 1 || wrongCount(s, path) < threshold) return s;
  const n = clone(s);
  n.hints[path] = 1;
  return n;
}

/** Обязательный вопрос решён. Баллов не даёт (docs/01 §6). */
export function solve(s, path, canon) {
  if (isClosed(s, path)) return s;
  const n = clone(s);
  n.units[path] = { status: "solved", canon: clone(canon) };
  return n;
}

/**
 * Бонусный вопрос этапов 1–3: одна попытка (docs/01 §4). Верно — +points,
 * неверно — 0 и вопрос закрывается. После начала финала бонусы прошлых этапов
 * закрыты (docs/01 §2). Ответ команды сохраняется для разбора.
 */
export function bonusAnswer(s, path, { correct, canon, points }) {
  const p = pos(points);
  if (isClosed(s, path) || isFinalStarted(s) || s.finished) return s;
  const n = clone(s);
  n.units[path] = { status: correct ? "solved" : "closed", canon: clone(canon) };
  if (correct) addLog(n, p, `bonus:${path}`);
  return n;
}

/** Переход на этап n: сохраняется ключ этапа (base64url). */
export function advanceStage(s, n, keyB64) {
  if (!Number.isInteger(n) || n < 1) throw new TypeError("Номер этапа");
  if (s.keys[n] === keyB64 && s.stage >= n) return s;
  const next = clone(s);
  next.keys[n] = keyB64;
  next.stage = Math.max(next.stage, n);
  return next;
}

/**
 * Экспертиза выполнена. docId — документ результата или null (атмосферный
 * результат без документа, PLAN D1). Ранее отклонённый запрос может сработать
 * после перехода этапа — тогда он убирается из отклонённых. Без штрафа.
 */
export function labDone(s, fp, docId) {
  const id = docId ?? null;
  if (fp in s.lab.done && s.lab.done[fp] === id) return s;
  const n = clone(s);
  n.lab.done[fp] = id;
  n.lab.rejected = n.lab.rejected.filter((x) => x !== fp);
  if (id !== null && !n.docs.includes(id)) n.docs.push(id);
  return n;
}

/** Запрос без оснований: штраф один раз на отпечаток запроса. */
export function labRejected(s, fp, penalty) {
  const d = neg(penalty);
  if (labSeen(s, fp)) return s;
  const n = clone(s);
  n.lab.rejected.push(fp);
  addLog(n, d, `lab:${fp}`);
  return n;
}

/**
 * Ответ финала фиксируется (одна попытка, вернуться нельзя). Баллы не
 * пишутся — счёт до конца финала не меняется (docs/01 §8).
 */
export function finalSubmit(s, path, value) {
  if (s.finished || path in s.final.answers) return s;
  const n = clone(s);
  n.final.answers[path] = clone(value);
  n.final.index = Object.keys(n.final.answers).length;
  return n;
}

/**
 * Конец финала: баллы за верные ответы этапа 4 пишутся в журнал разом.
 * results: { [path]: { correct: boolean, kind: "final" | "bonus" } }
 * points:  { final: number, bonus: number } — из public.json.
 */
export function finalFinish(s, results, points) {
  if (s.finished) return s;
  const n = clone(s);
  for (const [path, res] of Object.entries(results)) {
    if (!res?.correct) continue;
    const kind = res.kind === "bonus" ? "bonus" : "final";
    addLog(n, pos(points[kind]), `${kind}:${path}`);
  }
  n.finished = true;
  return n;
}

// ---------------------------------------------------------------- хранилище

/**
 * createStore({ storage, gameId, now, events })
 *   storage — объект с getItem/setItem/removeItem (localStorage) или null;
 *   gameId  — game_id из public.json, ключ `detgame:<gameId>`;
 *   now     — часы, () => Date | number | string (по умолчанию Date.now);
 *   events  — цель событий `storage` (по умолчанию globalThis, если умеет addEventListener).
 *
 * Если хранилища нет или оно бросает исключение, игра работает в памяти,
 * `persistent` = false (интерфейс предупреждает, что прогресс не сохранится).
 *
 * Несколько вкладок: update() перечитывает состояние из хранилища перед
 * применением изменения и записывает результат; событие `storage` от другой
 * вкладки вызывает onExternalChange(state).
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
  let memory = null; // текущее состояние (копия) — источник правды без хранилища
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

  function stamp(prevLen, s) {
    const t = toIso(now());
    for (let i = prevLen; i < s.log.length; i++) {
      if (!s.log[i].t) s.log[i] = { t, ...s.log[i] };
    }
  }

  memory = readStorage();
  const listeners = new Set();

  function onStorage(e) {
    if (e && e.key !== key && e.key !== null) return;
    memory = readStorage();
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
     * Перечитать → применить fn(state) → записать. fn получает копию
     * (или null до начала игры) и возвращает новое состояние.
     * Возвращает записанное состояние.
     */
    update(fn) {
      // Без хранилища readStorage() возвращает состояние из памяти; с хранилищем —
      // свежую запись (в т. ч. null, если другая вкладка начала заново).
      const base = readStorage();
      const prevLen = base ? base.log.length : 0;
      const next = fn(clone(base));
      if (next === undefined) throw new TypeError("update: функция должна вернуть состояние");
      if (next !== null) {
        const checked = normalizeState(next);
        stamp(Math.min(prevLen, checked.log.length), checked);
        write(checked);
      } else {
        write(null);
      }
      return clone(memory);
    },
    exportJson() {
      const s = readStorage() ?? memory;
      return JSON.stringify(s, null, 2) + "\n";
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
