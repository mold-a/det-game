// Оболочка закрытой вымышленной страницы (docs/02 §3.8–3.9, FORMATS §6.3–6.4, F13).
//
// Ключ по QR (access = "key"):
//   1. Ключ — из #k=<b64u> или из sessionStorage["detgame:page:<slug>"].
//   2. Фрагмент сразу убирается из адреса (history.replaceState), ключ сохраняется в
//      sessionStorage — перезагрузка и выгрузка вкладки на iOS не дают «Ссылка повреждена».
//   3. fetch("/p/<slug>/payload.json") → open(K_p, box, "page/<slug>") → JSON {v, slug, title, html, media}.
//   4. html вставляется в #page-content, подключается модуль интерактива страницы,
//      затем hydrateMedia (зашифрованные медиа → Blob URL).
//   Нет ключа или неверный → «Ссылка повреждена. Отсканируйте QR-код ещё раз».
//
// Облако (access = "password"): payload = {salt, iter, box}. Ключ — cloudKey(normalize("password",
//   ввод), salt, iter); неверный → «Неверный пароль», без блокировок и штрафов. После входа в
//   sessionStorage кладётся b64u выведенного ключа, а не пароль (F13).

import { open, b64uDecode, b64uEncode, utf8Decode, cloudKey, KEY_LEN } from "../core/crypto.js";
import { normalize } from "../core/normalize.js";
import { hydrateMedia } from "../core/media.js";
import { PAGE_MODULES } from "./page-modules.js"; // модули интерактива по типу страницы: init(root, payload)
import { init as initUi } from "./page-ui.js"; // окна сервиса, вкладки, фото крупно — для всех типов

const STORAGE_PREFIX = "detgame:page:";
const PAYLOAD_VERSION = 1;


const TEXT = {
  checking: "Проверяем пароль…",
  emptyPassword: "Введите пароль",
  wrongPassword: "Неверный пароль",
  mediaFailed: "Файл не загрузился",
};

class BrokenLink extends Error {}
class LoadFailed extends Error {}

const $ = (id) => document.getElementById(id);

function storageGet(name) {
  try {
    return sessionStorage.getItem(name);
  } catch {
    return null; // приватный режим / запрет хранилища
  }
}

function storageSet(name, value) {
  try {
    if (value === null) sessionStorage.removeItem(name);
    else sessionStorage.setItem(name, value);
  } catch {
    /* без хранилища страница всё равно работает до перезагрузки */
  }
}

/** Ключ из фрагмента #k=…; фрагмент убирается из адреса в любом случае. */
export function takeHashKey(loc = location, hist = history) {
  const hash = loc.hash || "";
  if (!hash || hash === "#") return null;
  const params = new URLSearchParams(hash.slice(1));
  const k = params.get("k");
  try {
    hist.replaceState(hist.state, "", loc.pathname + loc.search);
  } catch {
    /* старые браузеры: фрагмент останется в адресе, это не ошибка */
  }
  return k;
}

function keyFromB64(s) {
  if (!s) return null;
  try {
    const k = b64uDecode(s);
    return k.length === KEY_LEN ? k : null;
  } catch {
    return null;
  }
}

async function fetchPayload(slug) {
  let res;
  try {
    res = await fetch(`/p/${slug}/payload.json`, { cache: "no-cache" });
  } catch {
    throw new LoadFailed("network");
  }
  if (!res.ok) throw new LoadFailed(`HTTP ${res.status}`);
  try {
    return await res.json();
  } catch {
    throw new LoadFailed("json");
  }
}

/** Расшифровать Box страницы → внутренний JSON; неверный ключ → BrokenLink. */
export async function openPage(key, box, slug) {
  let inner;
  try {
    inner = JSON.parse(utf8Decode(await open(key, box, `page/${slug}`)));
  } catch {
    throw new BrokenLink("decrypt");
  }
  if (!inner || inner.v !== PAYLOAD_VERSION || inner.slug !== slug || typeof inner.html !== "string") {
    throw new BrokenLink("payload");
  }
  return inner;
}

function show(id) {
  for (const el of ["shell-status", "shell-login", "shell-broken", "shell-failed"]) {
    const node = $(el);
    if (node) node.hidden = el !== id;
  }
}

function showBroken() {
  show("shell-broken");
}

async function render(slug, inner) {
  const root = $("page-content");
  if (inner.title) document.title = inner.title;
  root.innerHTML = inner.html; // HTML отрендерил и экранировал сборщик (FORMATS §0)
  const shell = $("shell");
  if (shell.dataset.keepHead) shell.querySelector(".shell__body").hidden = true; // video: шапка системы остаётся
  else shell.hidden = true;
  document.body.classList.add("is-open");

  try {
    initUi(root);
  } catch (e) {
    console.error(e);
  }
  const modPath = PAGE_MODULES[inner.type || slug];
  let mod = null;
  if (modPath) {
    try {
      mod = await import(modPath);
      await mod.init?.(root, inner);
    } catch (e) {
      console.error(e); // интерактив не должен прятать содержимое
    }
  }
  await hydrateMedia(root, inner.media || [], {
    missingText: () => TEXT.mediaFailed,
    onProgress: (node, loaded, total) =>
      node.dispatchEvent(new CustomEvent("media-progress", { detail: { loaded, total }, bubbles: true })),
  });
  try {
    mod?.afterMedia?.(root, inner);
  } catch (e) {
    console.error(e);
  }
  document.body.dataset.ready = "1";
}

async function runKey(slug, storageName) {
  const fromHash = takeHashKey();
  const raw = fromHash ?? storageGet(storageName);
  const key = keyFromB64(raw);
  if (!key) {
    if (fromHash !== null) storageSet(storageName, null);
    throw new BrokenLink("no key");
  }
  const payload = await fetchPayload(slug);
  let inner;
  try {
    inner = await openPage(key, payload, slug);
  } catch (e) {
    // Неверный ключ из хранилища (например, после пересоздания солей) — забыть его.
    storageSet(storageName, null);
    throw e;
  }
  storageSet(storageName, raw);
  await render(slug, inner);
}

async function runPassword(slug, storageName) {
  takeHashKey(); // на облаке фрагмента быть не должно; если есть — убрать
  const payload = await fetchPayload(slug);
  if (!payload || !payload.box || !payload.salt || !(payload.iter >= 1)) throw new LoadFailed("cloud payload");
  const salt = b64uDecode(payload.salt);

  const stored = keyFromB64(storageGet(storageName));
  if (stored) {
    try {
      await render(slug, await openPage(stored, payload.box, slug));
      return;
    } catch {
      storageSet(storageName, null);
    }
  }

  const form = $("shell-login");
  const input = form.elements.password;
  const error = $("shell-error");
  const submit = form.querySelector('[type="submit"]');
  const submitText = submit.textContent;
  show("shell-login");

  const fail = (text) => {
    error.textContent = text;
    error.hidden = false;
    input.setAttribute("aria-invalid", "true");
    input.focus();
    input.select?.();
  };

  input.addEventListener("input", () => {
    error.hidden = true;
    input.removeAttribute("aria-invalid");
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (submit.disabled) return;
    const norm = normalize("password", input.value);
    if (!norm) {
      fail(TEXT.emptyPassword);
      return;
    }
    submit.disabled = true;
    submit.textContent = TEXT.checking;
    error.hidden = true;
    try {
      const key = await cloudKey(norm, salt, payload.iter);
      let inner;
      try {
        inner = await openPage(key, payload.box, slug);
      } catch {
        fail(TEXT.wrongPassword);
        return;
      }
      storageSet(storageName, b64uEncode(key));
      input.value = "";
      await render(slug, inner);
    } finally {
      submit.disabled = false;
      submit.textContent = submitText;
    }
  });
}

async function main() {
  if (window.DETGAME_BOOT && !window.DETGAME_BOOT.ok) return; // boot.js уже показал экран
  const body = document.body;
  const slug = body.dataset.slug;
  const access = body.dataset.access;
  if (!slug || !$("page-content")) return;
  const storageName = STORAGE_PREFIX + slug;
  try {
    if (access === "password") await runPassword(slug, storageName);
    else await runKey(slug, storageName);
  } catch (e) {
    if (e instanceof LoadFailed) show("shell-failed");
    else showBroken();
    if (!(e instanceof BrokenLink) && !(e instanceof LoadFailed)) console.error(e);
  }
}

main();
