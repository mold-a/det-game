// Медиа — docs/02 §4а, docs/FORMATS.md §5.
// mediaUrl(ref): открытый файл — прямой src; зашифрованный — fetch → openMedia →
// Blob URL с исходным MIME. У зашифрованного файла src с версией (`/m/<hash>.bin?v=…`, меняется с каждой
// сборкой); если файл всё же не расшифровался — один повтор мимо кеша (cache: "reload").
// hydrateMedia(root, refs): подставить src во все [data-media="<i>"] фрагмента.

import { b64uDecode, openMedia } from "./crypto.js";

/** Размер файла по-русски, десятичные единицы (1 МБ = 1 000 000 байт): 24000000 → «24 МБ», 512000 → «512 КБ». */
export function formatSize(bytes) {
  if (!(bytes > 0)) return "";
  const kb = bytes / 1000;
  if (kb < 1000) return `${Math.round(kb)} КБ`;
  const mb = kb / 1000;
  return `${mb < 10 ? mb.toFixed(1).replace(".", ",") : Math.round(mb)} МБ`;
}

const blobUrls = new Map(); // src → Promise<string> (один файл расшифровывается один раз)

/**
 * → Promise<string|null>. null — файла нет (ref.missing / src null).
 * onProgress(loaded, total) — для видео: по ReadableStream и ref.size.
 */
export function mediaUrl(ref, { fetchFn = globalThis.fetch, onProgress } = {}) {
  if (!ref || !ref.src || ref.missing) return Promise.resolve(null);
  if (!ref.key) return Promise.resolve(ref.src);
  if (!blobUrls.has(ref.src)) {
    const p = (async () => {
      const key = b64uDecode(ref.key);
      let pt;
      try {
        pt = await openMedia(key, await download(fetchFn, ref, onProgress), ref.aad);
      } catch (e) {
        if (e?.http) throw e;
        // Не расшифровалось — почти всегда это старая копия файла из кеша браузера или прокси: /m/* отдаются
        // как immutable, а ключ закрытого файла новый в каждой сборке. Один раз качаем заново мимо кеша.
        pt = await openMedia(key, await download(fetchFn, ref, onProgress, { cache: "reload" }), ref.aad);
      }
      return URL.createObjectURL(new Blob([pt], { type: ref.mime }));
    })();
    p.catch(() => blobUrls.delete(ref.src));
    blobUrls.set(ref.src, p);
  }
  return blobUrls.get(ref.src);
}

async function download(fetchFn, ref, onProgress, init) {
  const res = init ? await fetchFn(ref.src, init) : await fetchFn(ref.src);
  if (!res.ok) throw Object.assign(new Error(`${ref.src}: HTTP ${res.status}`), { http: res.status });
  return readAll(res, ref.size, onProgress);
}

async function readAll(res, size, onProgress) {
  const total = Number(res.headers?.get?.("content-length")) || size || 0;
  if (!onProgress || !res.body?.getReader) return new Uint8Array(await res.arrayBuffer());
  const reader = res.body.getReader();
  const chunks = [];
  let loaded = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.length;
    onProgress(loaded, total);
  }
  const out = new Uint8Array(loaded);
  let off = 0;
  for (const c of chunks) {
    out.set(c, off);
    off += c.length;
  }
  return out;
}

/** Освободить все Blob URL (при уходе со страницы, «Начать заново»). */
export async function revokeAll() {
  const list = [...blobUrls.values()];
  blobUrls.clear();
  for (const p of list) {
    try {
      URL.revokeObjectURL(await p);
    } catch {
      /* файл не расшифровался — нечего освобождать */
    }
  }
}

const NEAR_MARGIN = "600px 0px"; // расшифровывать фото чуть заранее, до входа в экран

/** Вызвать fn один раз, когда node окажется рядом с видимой областью (без IntersectionObserver — сразу). */
export function whenNear(node, fn) {
  if (typeof IntersectionObserver === "undefined") {
    fn();
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      io.disconnect();
      fn();
    },
    { rootMargin: NEAR_MARGIN },
  );
  io.observe(node);
}

/**
 * Подставить медиа во фрагмент: для каждого [data-media="i"] — refs[i].
 * img/video/audio/source получают src; отсутствующий файл — класс media-missing
 * и подпись alt (CSS рисует серую заглушку «Здесь будет …»).
 * Зашифрованные <img loading="lazy"> не расшифровываются сразу: только когда подошли к экрану
 * (десятки фото в ленте не должны ждать друг друга). Промис не ждёт такие картинки.
 * missingText(alt) — текст заглушки (из texts.js). Ошибки отдельных файлов не роняют страницу.
 */
export async function hydrateMedia(root, refs, { missingText = (alt) => alt, onProgress, fetchFn } = {}) {
  const nodes = Array.from(root.querySelectorAll("[data-media]"));

  async function hydrateOne(node, ref) {
    if (ref?.alt && node.tagName === "IMG" && !node.getAttribute("alt")) node.setAttribute("alt", ref.alt);
    let url = null;
    try {
      url = await mediaUrl(ref, { fetchFn, onProgress: onProgress && ((l, t) => onProgress(node, l, t)) });
    } catch {
      url = null;
    }
    if (!url) {
      markMissing(node, missingText(ref?.alt ?? ""));
      return;
    }
    if (node.tagName === "VIDEO" || node.tagName === "AUDIO") {
      node.setAttribute("playsinline", "");
      node.src = url;
    } else if ("src" in node) {
      node.src = url;
    } else {
      node.style.backgroundImage = `url("${url}")`;
    }
  }

  await Promise.all(
    nodes.map((node) => {
      const ref = refs?.[Number(node.getAttribute("data-media"))];
      if (node.tagName === "IMG" && node.getAttribute("loading") === "lazy" && ref?.key) {
        whenNear(node, () => hydrateOne(node, ref));
        return null;
      }
      return hydrateOne(node, ref);
    }),
  );
}

function markMissing(node, text) {
  node.classList.add("media-missing");
  node.setAttribute("data-missing", "1");
  if (node.tagName === "IMG") {
    node.removeAttribute("src");
    node.setAttribute("alt", text);
  }
  node.setAttribute("title", text);
}
