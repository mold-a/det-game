// Модули интерактива вымышленных страниц по типу страницы (page.type, по умолчанию = slug).
// Каждый экспортирует init(root, payload). Общий интерактив (окна, вкладки, фото крупно) — page-ui.js.
// Типы без записи (social, site, …) обходятся общим page-ui.js.

export const PAGE_MODULES = {
  call: "./audio-player.js",
  inna: "./gallery.js",
  pharma: "./pharma.js",
  cloud: "./cloud.js",
  video: "./video.js",
};
