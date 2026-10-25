// Профили закрытых этапов на вымышленных страницах (docs/04 «Профили закрытых этапов»; логика — core/gate.js).
//
//   a[data-gate="<slug>"]   ссылка-заглушка (href="/p/<заглушка>/#to=<slug>"): если этап профиля открыт
//                           в прогрессе этого браузера — href меняется на настоящий адрес с ключом;
//   [data-people-search]    поиск «Круга»: профили из пакетов открытых этапов добавляются в список
//                           (и «Профиль закрыт» у уже известных имён меняется на должность и ссылку);
//   заглушка с #to=<slug>   если профиль уже открыт — переход на него (location.replace).
//
// Когда всё сделано (или делать нечего) — body[data-gate-ready="1"] (для сквозных тестов).

import { unlockedPages, gateTarget, profileHref, mergeDirectory } from "../core/gate.js";

function storage(name) {
  try {
    return globalThis[name] ?? null;
  } catch {
    return null; // доступ к хранилищу запрещён
  }
}

function personItem(doc) {
  const li = doc.createElement("li");
  li.className = "kr-person";
  li.hidden = true;
  const a = doc.createElement("a");
  a.className = "kr-person__link";
  const ava = doc.createElement("span");
  ava.className = "kr-person__ava";
  ava.setAttribute("aria-hidden", "true");
  const text = doc.createElement("span");
  text.className = "kr-person__text";
  const name = doc.createElement("b");
  name.className = "kr-person__name";
  text.append(name);
  a.append(ava, text);
  li.append(a);
  return li;
}

/** Обновить список поиска людей по слитому индексу (порядок — по имени, как у сборки). */
export function applyDirectory(box, index) {
  const doc = box.ownerDocument;
  let list = box.querySelector('[data-role="list"]');
  const items = Array.from(box.querySelectorAll(".kr-person"));
  const existing = items.map((li) => ({
    slug: li.dataset.slug || "",
    name: li.dataset.name || "",
    closed: !!li.querySelector(".kr-person__pos--closed"),
  }));
  const merged = mergeDirectory(existing, index);
  if (merged.every((e) => e.href === undefined)) return false; // ничего не открылось
  if (!list) {
    list = doc.createElement("ul");
    list.className = "kr-people";
    list.setAttribute("role", "list");
    list.dataset.role = "list";
    box.append(list);
  }
  const bySlug = new Map(items.map((li) => [li.dataset.slug, li]));
  for (const e of merged) {
    let li = bySlug.get(e.slug);
    if (!li) li = personItem(doc);
    if (e.href !== undefined) {
      li.dataset.name = e.name;
      li.dataset.slug = e.slug;
      const a = li.querySelector("a");
      a.setAttribute("href", e.href);
      a.removeAttribute("data-gate");
      li.querySelector(".kr-person__ava").textContent = e.name.slice(0, 1);
      li.querySelector(".kr-person__name").textContent = e.name;
      let pos = li.querySelector(".kr-person__pos");
      if (e.position) {
        if (!pos) {
          pos = doc.createElement("span");
          li.querySelector(".kr-person__text").append(pos);
        }
        pos.className = "kr-person__pos";
        pos.textContent = e.position;
      } else pos?.remove();
    }
    list.append(li); // перенос существующего узла в нужное место
  }
  // пересчитать результаты текущего запроса (page-ui.js читает список заново)
  box.querySelector('[data-role="q"]')?.dispatchEvent(new Event("input", { bubbles: true }));
  return true;
}

export async function init(root = document) {
  const doc = root.ownerDocument || root;
  const body = doc.body;
  try {
    const links = Array.from(root.querySelectorAll("a[data-gate]"));
    const search = root.querySelector("[data-people-search]");
    const target = gateTarget(globalThis.location?.hash);
    if (!links.length && !search && !target) return;
    const index = await unlockedPages({ storage: storage("localStorage"), session: storage("sessionStorage") });
    if (!index.size) return;
    if (target && index.has(target)) {
      globalThis.location.replace(profileHref(index.get(target)));
      return;
    }
    for (const a of links) {
      const e = index.get(a.dataset.gate);
      if (!e) continue;
      a.setAttribute("href", profileHref(e));
      a.dataset.gateOpen = "1";
    }
    if (search) applyDirectory(search, index);
  } catch (e) {
    console.error(e); // ссылки остаются заглушками
  } finally {
    if (body) body.dataset.gateReady = "1";
  }
}
