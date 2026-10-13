// Облако «Тучка» (страница cloud): переключение папок и сортировка реестра по колонкам.
// Значения для сортировки — data-sort ячеек (сырые строки контента: ISO-даты сортируются
// как строки, суммы с пробелами между разрядами — как числа). Повторное нажатие на заголовок меняет
// направление; пустые значения всегда внизу. Плашка публикации статична — здесь её нет.

const RE_NUMBER = /^-?[\d\s ]+(?:[.,]\d+)?$/;

export function parseNumber(s) {
  return Number(String(s).replace(/[\s ]/g, "").replace(",", "."));
}

/** Сравнение значений колонки: числа — как числа, остальное — по-русски с учётом цифр. */
export function makeComparator(values, collator = new Intl.Collator("ru", { numeric: true, sensitivity: "base" })) {
  const filled = values.filter((v) => v.trim() !== "");
  const numeric = filled.length > 0 && filled.every((v) => RE_NUMBER.test(v.trim()));
  return (a, b) => {
    const ea = a.trim() === "";
    const eb = b.trim() === "";
    if (ea || eb) return ea === eb ? 0 : ea ? 1 : -1;
    return numeric ? parseNumber(a) - parseNumber(b) : collator.compare(a, b);
  };
}

function setupTable(table) {
  const tbody = table.tBodies[0];
  if (!tbody) return;
  const rows = Array.from(tbody.rows).map((tr, i) => ({ tr, i }));
  const headers = Array.from(table.querySelectorAll("thead th"));
  let state = { col: -1, dir: 1 };

  const cellValue = (row, col) => row.tr.cells[col]?.dataset.sort ?? row.tr.cells[col]?.textContent ?? "";

  function sortBy(col) {
    const dir = state.col === col ? -state.dir : 1;
    state = { col, dir };
    const cmp = makeComparator(rows.map((r) => cellValue(r, col)));
    const sorted = [...rows].sort((a, b) => {
      const va = cellValue(a, col);
      const vb = cellValue(b, col);
      const emptyA = va.trim() === "";
      const emptyB = vb.trim() === "";
      if (emptyA || emptyB) return cmp(va, vb) || a.i - b.i; // пустые — внизу при любом направлении
      return dir * cmp(va, vb) || a.i - b.i;
    });
    tbody.append(...sorted.map((r) => r.tr));
    headers.forEach((th, i) => th.setAttribute("aria-sort", i === col ? (dir > 0 ? "ascending" : "descending") : "none"));
  }

  headers.forEach((th, i) => {
    th.querySelector("button")?.addEventListener("click", () => sortBy(i));
  });
}

function setupFolders(root) {
  const links = Array.from(root.querySelectorAll("[data-folder-link]"));
  const panels = new Map(Array.from(root.querySelectorAll(".tc-panel[data-folder]")).map((p) => [p.dataset.folder, p]));
  if (!links.length || !panels.size) return;
  root.querySelector(".tc")?.classList.add("has-tabs");

  function select(id, { focus = false } = {}) {
    for (const [pid, panel] of panels) panel.hidden = pid !== id;
    for (const a of links) {
      if (a.dataset.folderLink === id) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    }
    if (focus) {
      const panel = panels.get(id);
      panel?.focus({ preventScroll: true });
      // На телефоне список папок над панелью — показать начало открытой папки.
      if (panel && window.matchMedia?.("(max-width: 899px)").matches) panel.scrollIntoView({ block: "start" });
    }
  }

  for (const a of links) {
    a.addEventListener("click", (ev) => {
      ev.preventDefault(); // без смены #фрагмента
      select(a.dataset.folderLink, { focus: true });
    });
  }
  select(links[0].dataset.folderLink);
}

export function init(root = document) {
  root.querySelectorAll("table[data-sortable]").forEach(setupTable);
  setupFolders(root);
}
