// Точка входа открытых вымышленных страниц: общий интерактив (page-ui.js) и модуль типа страницы
// (page-modules.js). Закрытые страницы подключают то же самое из shell.js после расшифровки.

import { init as initUi } from "./page-ui.js";
import { PAGE_MODULES } from "./page-modules.js";

async function main() {
  if (window.DETGAME_BOOT && !window.DETGAME_BOOT.ok) return; // boot.js уже показал экран
  const root = document.querySelector("main") || document;
  initUi(root === document ? document : root);
  const type = document.body.dataset.type || document.body.dataset.slug;
  const path = PAGE_MODULES[type];
  if (path) {
    try {
      const mod = await import(path);
      await mod.init?.(document);
    } catch (e) {
      console.error(e); // интерактив не должен прятать содержимое
    }
  }
  document.body.dataset.ready = "1";
}

main();
