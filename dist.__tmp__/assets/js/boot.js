/*
 * boot.js — КЛАССИЧЕСКИЙ скрипт (не модуль), подключается первым на каждой странице:
 *   <script src="/assets/js/boot.js"></script>
 *
 * Проверяет, что браузер сможет запустить игру (docs/02 §1, PLAN R6):
 *   - сайт открыт не как файл (file:// блокирует модули и fetch);
 *   - защищённый контекст (HTTPS или localhost) — иначе нет crypto.subtle;
 *   - есть Web Crypto (crypto.subtle);
 *   - есть ES-модули.
 * Если что-то не так — показывает понятный экран вместо страницы и выставляет
 * window.DETGAME_BOOT = { ok: false, reason }. Модульный код проверяет
 * window.DETGAME_BOOT.ok перед стартом.
 *
 * Ни от чего не зависит и написан на ES5: он должен работать в браузерах,
 * где модулей нет. Поэтому его строки — исключение из правила «все тексты в
 * app/texts.js»: модуль отсюда импортировать нельзя.
 *
 * file:// и абсолютные пути (docs/FORMATS.md F18): страница ссылается на
 * /assets/js/boot.js, а на file:// это file:///assets/… — скрипт просто не
 * загрузится. Поэтому base.html держит в <body> статический блок
 *   <div class="boot-fallback">…как открыть сайт…</div>
 * который виден по умолчанию. Если boot.js выполнился и всё в порядке, он
 * ставит <html class="boot-ok"> и base.css этот блок прячет (до отрисовки
 * body — скрипт стоит в <head>). При ошибке boot.js сам показывает экран.
 *
 * Атрибуты:
 *   <script src="…boot.js" data-require="none">  — страница без шифрования
 *       (открытые вымышленные страницы): проверяется только file://.
 *   <html data-site-url="https://…">            — адрес сайта для подсказки.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var need = (script && script.getAttribute("data-require")) || "crypto";

  function detect() {
    if (location.protocol === "file:") return "file";
    if (need === "none") return null;
    if (window.isSecureContext === false) return "insecure";
    var c = window.crypto;
    if (!c || !c.subtle || typeof c.subtle.deriveBits !== "function") return "nocrypto";
    if (!("noModule" in document.createElement("script"))) return "nomodules";
    return null;
  }

  var TEXTS = {
    title: "Страница не может работать в этом режиме",
    file:
      "Сайт открыт как файл с диска. В таком режиме браузер блокирует скрипты и данные дела.",
    insecure:
      "Соединение не защищено: адрес начинается с http://, и это не localhost. " +
      "Проверка ответов шифруется в браузере, а шифрование работает только по HTTPS или на localhost.",
    nocrypto:
      "Этот браузер не поддерживает шифрование, нужное для проверки ответов. " +
      "Обновите браузер или откройте сайт в Chrome, Firefox, Safari или Edge последней версии.",
    nomodules:
      "Этот браузер устарел и не может запустить программу. " +
      "Обновите браузер или откройте сайт в Chrome, Firefox, Safari или Edge последней версии.",
    howTitle: "Как открыть",
    howSite: "Откройте сайт по адресу ",
    howSiteGeneric: "Откройте сайт по адресу, который начинается с https://.",
    howLocal1: "Для проверки на своём компьютере: запустите в папке проекта команду ",
    howLocalCmd: "python -m engine serve",
    howLocal2: " и откройте http://localhost:8000.",
    howPhone:
      "С телефона адрес вида http://192.168.… не подойдёт: нужен HTTPS (сайт на хостинге или туннель).",
  };

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.appendChild(document.createTextNode(text));
    return n;
  }

  function render(reason) {
    var root = document.documentElement;
    root.className += (root.className ? " " : "") + "boot-failed";

    var box = el("main", "boot-screen");
    box.setAttribute("role", "alert");
    box.appendChild(el("h1", "boot-screen__title", TEXTS.title));
    box.appendChild(el("p", "boot-screen__reason", TEXTS[reason]));

    if (reason === "file" || reason === "insecure") {
      box.appendChild(el("h2", "boot-screen__subtitle", TEXTS.howTitle));
      var list = el("ul", "boot-screen__list");
      var url = root.getAttribute("data-site-url");
      if (url && /^https:\/\//.test(url)) {
        var li = el("li", null, TEXTS.howSite);
        var a = el("a", null, url);
        a.href = url;
        li.appendChild(a);
        li.appendChild(document.createTextNode("."));
        list.appendChild(li);
      } else {
        list.appendChild(el("li", null, TEXTS.howSiteGeneric));
      }
      var local = el("li", null, TEXTS.howLocal1);
      local.appendChild(el("code", "boot-screen__cmd", TEXTS.howLocalCmd));
      local.appendChild(document.createTextNode(TEXTS.howLocal2));
      list.appendChild(local);
      list.appendChild(el("li", null, TEXTS.howPhone));
      box.appendChild(list);
    }

    var body = document.body;
    while (body.firstChild) body.removeChild(body.firstChild);
    body.appendChild(box);
  }

  var reason = detect();
  window.DETGAME_BOOT = { ok: !reason, reason: reason };
  if (!reason) {
    var r = document.documentElement;
    r.className += (r.className ? " " : "") + "boot-ok";
    return;
  }

  if (document.body) render(reason);
  else
    document.addEventListener("DOMContentLoaded", function () {
      render(reason);
    });
})();
