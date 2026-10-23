// Интерактив страниц «Круга» (type: social): голосовые сообщения (в постах и комментариях) и видео в постах.
// Голосовые — audio-player.js. Видео — здесь:
//   открытая страница: <video src poster preload="none" controls> работает сам; модуль только прячет
//     длительность на постере после запуска и подгоняет пропорции под постер;
//   закрытая: в разметке нет ни src, ни poster — только data-video-media / data-poster-media (индексы в
//     payload.media). Постер расшифровывается, когда пост подошёл к экрану; сам файл (до нескольких МБ) —
//     только по нажатию «Смотреть видео (N МБ)», с прогрессом по размеру. После расшифровки видео
//     запускается тем же нажатием; звук включает игрок (автозапуска нет).
// Подключается из open.js (init(document)) и из shell.js (init(root, payload)) до hydrateMedia.

import { init as initAudio } from "./audio-player.js";
import { mediaUrl, whenNear } from "../core/media.js";

const TEXT = {
  watch: "Смотреть видео",
  loading: "Загрузка видео",
  decrypting: "Подготовка видео…",
  failed: "Видео не загрузилось. Проверьте подключение и попробуйте ещё раз.",
  retry: "Повторить",
};

/** 24117248 → «23 МБ», 512000 → «500 КБ». */
export function formatSize(bytes) {
  if (!(bytes > 0)) return "";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} КБ`;
  const mb = kb / 1024;
  return `${mb < 10 ? mb.toFixed(1).replace(".", ",") : Math.round(mb)} МБ`;
}

function fitToPoster(box, url) {
  const probe = new Image();
  probe.onload = () => {
    if (probe.naturalWidth > 0 && probe.naturalHeight > 0) {
      box.style.setProperty("--ratio", `${probe.naturalWidth} / ${probe.naturalHeight}`);
    }
  };
  probe.src = url;
}

function setupVideo(box, refs) {
  if (box.dataset.ready) return;
  box.dataset.ready = "1";
  const video = box.querySelector("video");
  if (!video) return; // «Видео недоступно»: заглушка без кнопок

  video.addEventListener("play", () => {
    box.classList.add("is-started");
    // Играет один медиафайл: останавливаем другие видео и голосовые.
    document.querySelectorAll("video, audio").forEach((other) => {
      if (other !== video && !other.paused) other.pause();
    });
  });
  video.addEventListener("loadedmetadata", () => {
    if (video.videoWidth > 0 && video.videoHeight > 0) {
      box.style.setProperty("--ratio", `${video.videoWidth} / ${video.videoHeight}`);
    }
  });

  const posterIdx = video.getAttribute("data-poster-media");
  const videoIdx = video.getAttribute("data-video-media");
  if (video.getAttribute("poster")) fitToPoster(box, video.getAttribute("poster"));
  if (videoIdx == null) return; // открытый файл: всё в атрибутах

  const ref = refs?.[Number(videoIdx)];
  const posterRef = posterIdx != null ? refs?.[Number(posterIdx)] : null;
  if (posterRef) {
    whenNear(box, async () => {
      try {
        const url = await mediaUrl(posterRef);
        if (url) {
          video.poster = url;
          fitToPoster(box, url);
        }
      } catch {
        /* без постера видео остаётся работоспособным */
      }
    });
  }

  const load = box.querySelector('[data-role="load"]');
  const btn = box.querySelector('[data-act="load"]');
  const progress = box.querySelector('[data-role="progress"]');
  const bar = box.querySelector('[data-role="bar"]');
  const ptext = box.querySelector('[data-role="ptext"]');
  if (!ref || !ref.src || ref.missing) {
    box.classList.add("is-missing");
    return;
  }
  const size = formatSize(ref.size);
  const label = size ? `${TEXT.watch} (${size})` : TEXT.watch;
  video.removeAttribute("controls"); // до загрузки управлять нечем: вместо них — кнопка
  btn.textContent = label;
  load.hidden = false;
  box.classList.add("is-lazy");

  btn.addEventListener("click", async () => {
    ptext.textContent = "";
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
      video.src = url;
      video.setAttribute("controls", "");
      load.hidden = true;
      box.classList.remove("is-lazy");
      box.classList.add("is-ready");
      const p = video.play(); // игрок только что нажал «Смотреть»; если браузер не разрешил — есть кнопка плеера
      if (p && typeof p.catch === "function") p.catch(() => {});
    } catch {
      progress.hidden = true;
      btn.hidden = false;
      btn.textContent = TEXT.retry;
      ptext.textContent = TEXT.failed;
    }
  });
}

export function init(root = document, payload = null) {
  initAudio(root);
  root.querySelectorAll('[data-player="postvideo"]').forEach((box) => setupVideo(box, payload?.media || []));
}
