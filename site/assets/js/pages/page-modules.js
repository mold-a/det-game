// Модули интерактива вымышленных страниц по типу страницы (page.type, по умолчанию = slug).
// Каждый экспортирует init(root, payload). Общий интерактив (окна, вкладки, фото крупно) — page-ui.js.
// Типы без записи (site, …) обходятся общим page-ui.js.

export const PAGE_MODULES = {
  call: "./audio-player.js",
  social: "./social.js", // голосовые (посты, комментарии) и видео в постах «Круга»
  photo: "./gallery.js", // «Кадр»: профили photo (в т. ч. inna)
  pharma: "./pharma.js",
  cloud: "./cloud.js",
  video: "./video.js",
  mail: "./mail.js", // почтовый ящик: папки, список цепочек, открытая цепочка
};
