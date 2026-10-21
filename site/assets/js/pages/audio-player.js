// Свой аудиоплеер страницы call (docs/04 «call», P06 п.3): воспроизведение/пауза,
// перемотка (ползунок и ±10 с), текущее время и длительность, громкость; «волна» статичная
// (рисует шаблон), закрашивается по мере проигрывания.
//
// iOS Safari: audio.volume только для чтения (всегда 1) — ползунок громкости там прячется,
// остаётся кнопка «Выключить звук» (muted работает). Воспроизведение запускается только
// из обработчика нажатия; playsinline; preload="metadata". Длительность до загрузки
// метаданных — из data-duration (контент), потом — из файла.
//
// Подключается из open.js (открытая страница, init(document)) и из shell.js (закрытая, init(root)).

const SKIP_SECONDS = 10;
const SEEK_STEPS = 1000; // max у ползунка перемотки
const TEXT = {
  play: "Воспроизвести",
  pause: "Пауза",
  mute: "Выключить звук",
  unmute: "Включить звук",
  failed: "Запись не загрузилась. Обновите страницу.",
  of: "из",
};

export function formatTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const s = Math.floor(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/** «М:СС» / «Ч:ММ:СС» → секунды; иначе NaN. */
export function parseTime(text) {
  const m = /^\s*(?:(\d+):)?(\d+):(\d{2})\s*$/.exec(text || "");
  if (!m) return NaN;
  return Number(m[1] || 0) * 3600 + Number(m[2]) * 60 + Number(m[3]);
}

let volumeWritable = null;
function canSetVolume() {
  if (volumeWritable === null) {
    try {
      const probe = document.createElement("audio");
      probe.volume = 0.5;
      volumeWritable = Math.abs(probe.volume - 0.5) < 0.01;
    } catch {
      volumeWritable = false;
    }
  }
  return volumeWritable;
}

function setupPlayer(box) {
  if (box.dataset.ready) return;
  box.dataset.ready = "1";
  const audio = box.querySelector("audio");
  const q = (sel) => box.querySelector(sel);
  const playBtn = q('[data-act="play"]');
  const backBtn = q('[data-act="back"]');
  const fwdBtn = q('[data-act="fwd"]');
  const muteBtn = q('[data-act="mute"]');
  const seek = q('[data-role="seek"]');
  const vol = q('[data-role="vol"]');
  const cur = q('[data-role="cur"]');
  const dur = q('[data-role="dur"]');
  const msg = q('[data-role="msg"]');

  if (!audio || box.dataset.missing) {
    // Заглушка («Здесь будет запись звонка», голосовое без файла): все кнопки неактивны.
    box.querySelectorAll("button, input").forEach((c) => (c.disabled = true));
    return;
  }

  const fallbackDuration = parseTime(box.dataset.duration);
  let seeking = false;

  const duration = () => (Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : fallbackDuration);

  const controls = [playBtn, backBtn, fwdBtn, muteBtn, seek, vol].filter(Boolean);
  controls.forEach((c) => (c.disabled = false));

  if (!canSetVolume()) {
    box.classList.add("no-volume");
    if (vol) vol.closest("label").hidden = true;
  }

  function paintProgress() {
    const d = duration();
    const t = audio.currentTime || 0;
    const p = d > 0 ? Math.min(1, t / d) : 0;
    box.style.setProperty("--p", String(p));
    box.classList.toggle("has-progress", t > 0); // голосовое: «0:03 / 0:12» вместо «0:12»
    if (cur) cur.textContent = formatTime(t);
    if (seek && !seeking) {
      seek.value = String(Math.round(p * SEEK_STEPS));
      seek.setAttribute("aria-valuetext", `${formatTime(t)} ${TEXT.of} ${formatTime(d)}`);
    }
  }

  function paintState() {
    const playing = !audio.paused && !audio.ended;
    box.classList.toggle("is-playing", playing);
    playBtn.setAttribute("aria-label", playing ? TEXT.pause : TEXT.play);
    box.classList.toggle("is-muted", audio.muted);
    if (muteBtn) {
      muteBtn.setAttribute("aria-pressed", String(audio.muted));
      muteBtn.setAttribute("aria-label", audio.muted ? TEXT.unmute : TEXT.mute);
    }
  }

  function seekTo(sec) {
    const d = duration();
    if (!(d > 0)) return;
    try {
      audio.currentTime = Math.max(0, Math.min(d, sec));
    } catch {
      /* метаданные ещё не загружены — iOS бросает InvalidStateError */
    }
    paintProgress();
  }

  playBtn.addEventListener("click", () => {
    if (audio.paused || audio.ended) {
      const p = audio.play();
      if (p && typeof p.catch === "function") p.catch(() => paintState());
    } else {
      audio.pause();
    }
  });
  backBtn?.addEventListener("click", () => seekTo((audio.currentTime || 0) - SKIP_SECONDS));
  fwdBtn?.addEventListener("click", () => seekTo((audio.currentTime || 0) + SKIP_SECONDS));
  muteBtn?.addEventListener("click", () => {
    audio.muted = !audio.muted;
    paintState();
  });

  if (seek) {
    seek.addEventListener("input", () => {
      seeking = true;
      const d = duration();
      const t = (Number(seek.value) / SEEK_STEPS) * (d || 0);
      if (cur) cur.textContent = formatTime(t);
      box.style.setProperty("--p", String(Number(seek.value) / SEEK_STEPS));
    });
    seek.addEventListener("change", () => {
      seeking = false;
      seekTo((Number(seek.value) / SEEK_STEPS) * (duration() || 0));
    });
  }

  if (vol) {
    vol.addEventListener("input", () => {
      audio.volume = Number(vol.value) / 100;
      if (audio.volume > 0 && audio.muted) audio.muted = false;
      paintState();
    });
  }

  audio.addEventListener("loadedmetadata", () => {
    if (dur) dur.textContent = formatTime(duration());
    paintProgress();
  });
  audio.addEventListener("durationchange", () => {
    if (dur && Number.isFinite(audio.duration)) dur.textContent = formatTime(audio.duration);
  });
  audio.addEventListener("timeupdate", paintProgress);
  audio.addEventListener("seeked", paintProgress);
  for (const ev of ["play", "pause", "ended", "volumechange"]) audio.addEventListener(ev, paintState);
  audio.addEventListener("play", () => {
    // На странице может быть несколько плееров (голосовые в ленте): играет один.
    document.querySelectorAll("audio").forEach((other) => {
      if (other !== audio && !other.paused) other.pause();
    });
  });
  audio.addEventListener("ended", () => {
    box.style.setProperty("--p", "1");
  });
  audio.addEventListener("error", () => {
    if (msg) msg.textContent = TEXT.failed;
    box.classList.add("is-failed");
  });

  paintState();
  paintProgress();
}

/** Подключить все плееры внутри root. */
export function init(root = document) {
  root.querySelectorAll('[data-player="audio"]').forEach(setupPlayer);
}
