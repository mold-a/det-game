// Фотосеть «Кадр» (страница inna): просмотр снимка крупно — фото целиком (без обрезки),
// подпись, дата, отметки; листание ‹ › и стрелками, закрытие × / Esc / нажатием на фон.
// Данные берутся из DOM фрагмента (FORMATS §6.1): плитки .kd-tile и их скрытые .kd-tile__meta.

export function init(root = document) {
  const dialog = root.querySelector(".kd-view");
  const tiles = Array.from(root.querySelectorAll(".kd-tile"));
  if (!dialog || !tiles.length) return;

  const mediaBox = dialog.querySelector(".kd-view__media");
  const metaBox = dialog.querySelector(".kd-view__meta");
  const prevBtn = dialog.querySelector('[data-act="prev"]');
  const nextBtn = dialog.querySelector('[data-act="next"]');
  const closeBtn = dialog.querySelector('[data-act="close"]');
  const native = typeof dialog.showModal === "function";
  let current = -1;
  let opener = null;

  function fill(i) {
    current = (i + tiles.length) % tiles.length;
    const tile = tiles[current];
    const img = tile.querySelector("img.kd-tile__img");
    const meta = tile.querySelector(".kd-tile__meta");
    mediaBox.replaceChildren();
    if (img && img.getAttribute("src") && !img.classList.contains("media-missing")) {
      const big = document.createElement("img");
      big.className = "kd-view__img";
      big.src = img.currentSrc || img.src;
      big.alt = meta?.querySelector(".kd-view__caption")?.textContent.trim() || tile.querySelector("button")?.getAttribute("aria-label") || "";
      mediaBox.append(big);
    } else {
      const ph = tile.querySelector(".ph, img")?.cloneNode(true);
      if (ph) {
        ph.classList.remove("kd-tile__img");
        ph.classList.add("kd-view__ph");
        mediaBox.append(ph);
      }
    }
    metaBox.replaceChildren(...Array.from(meta?.children ?? []).map((n) => n.cloneNode(true)));
    const single = tiles.length < 2;
    prevBtn.hidden = single;
    nextBtn.hidden = single;
  }

  function openAt(i, from) {
    opener = from || null;
    fill(i);
    if (native) {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
      dialog.classList.add("is-fallback-open");
    }
    document.documentElement.classList.add("kd-lock");
    closeBtn.focus();
  }

  function close() {
    if (native && dialog.open) dialog.close();
    else {
      dialog.removeAttribute("open");
      dialog.classList.remove("is-fallback-open");
      onClosed();
    }
  }

  function onClosed() {
    document.documentElement.classList.remove("kd-lock");
    mediaBox.replaceChildren();
    if (opener && document.contains(opener)) opener.focus();
    opener = null;
  }

  tiles.forEach((tile, i) => {
    tile.querySelector(".kd-tile__btn")?.addEventListener("click", (ev) => openAt(i, ev.currentTarget));
  });
  prevBtn.addEventListener("click", () => fill(current - 1));
  nextBtn.addEventListener("click", () => fill(current + 1));
  closeBtn.addEventListener("click", close);
  dialog.addEventListener("close", onClosed);
  dialog.addEventListener("click", (ev) => {
    if (ev.target === dialog) close(); // нажатие на затемнение вокруг окна
  });
  dialog.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowLeft") fill(current - 1);
    else if (ev.key === "ArrowRight") fill(current + 1);
    else if (ev.key === "Escape" && !native) close();
  });
}
