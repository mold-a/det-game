// Почтовый ящик (type: mail): папки, список цепочек, открытая цепочка (docs/04: «mail»).
//
// Состояние — {folder, thread}: открытая папка (индекс) и открытая цепочка (id или null). Телефон (< 900 px)
// показывает либо список, либо цепочку (класс .is-reading); ноутбук — всё сразу, без цепочки — «Выберите письмо».
// Открытие цепочки кладёт в историю адрес #mt-<id>: системная кнопка «Назад» возвращает к списку; кнопка
// «К списку писем» делает то же. Статус «не прочитано» — часть выгрузки и при открытии не меняется.
// Без JS всё видно подряд (ссылки — обычные якоря), этот модуль только переключает видимость.

export const THREAD_HASH = "#mt-";

/** Цепочка из адреса «#mt-<id>»: известный id или null (ключ страницы, раздел, мусор — null). */
export function threadFromHash(hash, ids) {
  if (typeof hash !== "string" || !hash.startsWith(THREAD_HASH)) return null;
  let id = hash.slice(THREAD_HASH.length);
  try {
    id = decodeURIComponent(id);
  } catch {
    return null;
  }
  return ids.includes(id) ? id : null;
}

/**
 * Состояние ящика без DOM. folders — индексы папок (строки, как в data-folder), threads — [{id, folder}]
 * в порядке списка. Открыть цепочку — значит перейти и в её папку; сменить папку — закрыть цепочку.
 */
export function createMailState(folders, threads) {
  const folderIds = folders.map(String);
  const byId = new Map(threads.map((t) => [t.id, String(t.folder)]));
  let state = { folder: folderIds[0] ?? null, thread: null };
  return {
    get: () => ({ ...state }),
    threadsIn: (folder) => threads.filter((t) => String(t.folder) === String(folder)).map((t) => t.id),
    folder(id) {
      if (folderIds.includes(String(id))) state = { folder: String(id), thread: null };
      return { ...state };
    },
    open(id) {
      if (byId.has(id)) state = { folder: byId.get(id), thread: id };
      return { ...state };
    },
    back() {
      state = { ...state, thread: null };
      return { ...state };
    },
  };
}

const narrow = () => window.matchMedia?.("(max-width: 899px)").matches ?? false;

export function init(root = document) {
  const box = root.querySelector("[data-mail]");
  if (!box) return null;
  const folderLinks = Array.from(box.querySelectorAll("[data-folder-link]"));
  const lists = Array.from(box.querySelectorAll(".ml-box[data-folder]"));
  const rows = Array.from(box.querySelectorAll("[data-thread-link]"));
  const threads = Array.from(box.querySelectorAll(".ml-thread[data-thread]"));
  const empty = box.querySelector('[data-role="empty"]');
  if (!folderLinks.length || !lists.length) return null;

  const st = createMailState(
    folderLinks.map((a) => a.dataset.folderLink),
    threads.map((t) => ({ id: t.dataset.thread, folder: t.dataset.folder })),
  );
  const ids = threads.map((t) => t.dataset.thread);
  box.classList.add("has-js");

  function render({ focus = false, from = null } = {}) {
    const s = st.get();
    for (const a of folderLinks) {
      if (a.dataset.folderLink === s.folder) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    }
    for (const l of lists) l.hidden = l.dataset.folder !== s.folder;
    for (const r of rows) {
      if (r.dataset.threadLink === s.thread) r.setAttribute("aria-current", "true");
      else r.removeAttribute("aria-current");
    }
    for (const t of threads) t.hidden = t.dataset.thread !== s.thread;
    if (empty) empty.hidden = Boolean(s.thread);
    box.classList.toggle("is-reading", Boolean(s.thread));
    if (!focus) return;
    if (s.thread) {
      const art = threads.find((t) => t.dataset.thread === s.thread);
      art?.focus({ preventScroll: true });
      if (narrow()) box.scrollIntoView({ block: "start" });
    } else if (from) {
      // назад к списку: фокус — на строку той цепочки, из которой вышли
      const row = rows.find((r) => r.dataset.threadLink === from);
      row?.focus({ preventScroll: true });
      row?.scrollIntoView({ block: "nearest" });
    }
  }

  const clearHash = () => {
    if (location.hash.startsWith(THREAD_HASH)) {
      try {
        history.replaceState(null, "", location.pathname + location.search);
      } catch {
        /* без истории — не страшно */
      }
    }
  };

  for (const a of folderLinks) {
    a.addEventListener("click", (ev) => {
      ev.preventDefault(); // без смены #фрагмента
      st.folder(a.dataset.folderLink);
      clearHash();
      render();
    });
  }

  for (const r of rows) {
    r.addEventListener("click", (ev) => {
      ev.preventDefault();
      const id = r.dataset.threadLink;
      const was = st.get().thread;
      st.open(id);
      try {
        const url = location.pathname + location.search + THREAD_HASH + encodeURIComponent(id);
        // из одной открытой цепочки в другую (ноутбук) — без новой записи в истории
        if (was) history.replaceState({ mailThread: id }, "", url);
        else history.pushState({ mailThread: id }, "", url);
      } catch {
        /* без истории — только видимость */
      }
      render({ focus: true });
    });
  }

  box.addEventListener("click", (ev) => {
    const btn = ev.target instanceof Element ? ev.target.closest('[data-act="back"]') : null;
    if (!btn) return;
    const from = st.get().thread;
    if (history.state && history.state.mailThread) {
      history.back(); // popstate вернёт к списку
      return;
    }
    st.back();
    clearHash();
    render({ focus: true, from });
  });

  window.addEventListener("popstate", () => {
    const from = st.get().thread;
    const id = threadFromHash(location.hash, ids);
    if (id) st.open(id);
    else st.back();
    render({ focus: true, from: id ? null : from });
  });

  const initial = threadFromHash(location.hash, ids);
  if (initial) st.open(initial);
  render();
  return st;
}
