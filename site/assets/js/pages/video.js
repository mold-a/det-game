// Изъятый видеофайл (страница video, «Электронное дело»): плеер и «Свойства файла».
// Зашифрованное видео (до 25 МБ) не скачивается само при открытии страницы: shell.js
// вызывает init() до hydrateMedia, и init снимает с <video> атрибут data-media. Загрузка —
// по кнопке «Загрузить видео», с прогрессом по ref.size (FORMATS §5); потом — обычный
// <video controls playsinline> из Blob URL. Открытый файл (без key) подключается сразу.

import { mediaUrl } from "../core/media.js";

const TEXT = {
  load: "Загрузить видео",
  loading: "Загрузка видео",
  decrypting: "Подготовка видео…",
  failed: "Видео не загрузилось. Проверьте подключение и попробуйте ещё раз.",
  retry: "Повторить загрузку",
};

/** 24117248 → «23 МБ», 512000 → «500 КБ». */
export function formatSize(bytes) {
  if (!(bytes > 0)) return "";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} КБ`;
  const mb = kb / 1024;
  return `${mb < 10 ? mb.toFixed(1).replace(".", ",") : Math.round(mb)} МБ`;
}

function setupProps(root) {
  const btn = root.querySelector('[data-act="props"]');
  const panel = root.querySelector('[data-role="props"]');
  if (!btn || !panel) return;
  panel.hidden = true;
  btn.addEventListener("click", () => {
    const open = panel.hidden;
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    if (open) panel.scrollIntoView({ block: "nearest" });
  });
}

function setupPlayer(root, refs) {
  const player = root.querySelector('[data-player="video"]');
  if (!player || player.dataset.missing) return;
  const video = player.querySelector("video");
  const idx = video?.getAttribute("data-media");
  const ref = idx != null ? refs?.[Number(idx)] : null;
  if (!video || !ref || !ref.key) return; // открытый файл — подставит hydrateMedia

  video.removeAttribute("data-media"); // hydrateMedia пропустит — загрузка по кнопке
  video.removeAttribute("controls");
  const box = player.querySelector('[data-role="load"]');
  const btn = player.querySelector('[data-act="load"]');
  const progress = player.querySelector('[data-role="progress"]');
  const bar = player.querySelector('[data-role="bar"]');
  const ptext = player.querySelector('[data-role="ptext"]');
  const size = formatSize(ref.size);
  const label = size ? `${TEXT.load} (${size})` : TEXT.load;
  btn.textContent = label;
  box.hidden = false;
  player.classList.add("is-lazy");

  btn.addEventListener("click", async () => {
    player.querySelector(".ev-player__error")?.remove();
    btn.hidden = true;
    progress.hidden = false;
    bar.style.width = "0%";
    ptext.textContent = `${TEXT.loading}…`;
    try {
      const url = await mediaUrl(ref, {
        onProgress: (loaded, total) => {
          const t = total || ref.size || 0;
          if (!t) return;
          const p = Math.min(100, Math.round((loaded / t) * 100));
          bar.style.width = `${p}%`;
          ptext.textContent = p >= 100 ? TEXT.decrypting : `${TEXT.loading}: ${p} %`;
        },
      });
      if (!url) throw new Error("no media");
      video.setAttribute("playsinline", "");
      video.setAttribute("controls", "");
      video.src = url;
      box.hidden = true;
      player.classList.remove("is-lazy");
      player.classList.add("is-ready");
      video.focus({ preventScroll: true });
    } catch {
      progress.hidden = true;
      btn.hidden = false;
      btn.textContent = TEXT.retry;
      ptext.textContent = "";
      const err = document.createElement("p");
      err.className = "ev-player__error";
      err.setAttribute("role", "alert");
      err.textContent = TEXT.failed;
      box.append(err);
    }
  });
}

export function init(root = document, payload = null) {
  setupProps(root);
  setupPlayer(root, payload?.media || []);
}
