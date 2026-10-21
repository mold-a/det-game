"""Распознавание объекта лаборатории по свободному тексту — docs/02 §«Распознавание объекта».

Зеркало ``site/assets/js/core/labmatch.js``: обе реализации обязаны давать одинаковый результат.
Общие векторы — ``tests/vectors/lab-match.json`` (``python -m engine vectors``).

Алгоритм (REDESIGN-2026-10 §3):

1. ``norm(s)`` — ``normalize("text", s)``: NFC, нижний регистр, «ё»→«е», не буквы и не цифры → пробел,
   пробелы схлопнуты. Пустая строка → ``[]`` токенов.
2. Алиас — одна или несколько основ через пробел. Основа ``s`` подходит токену ``t``, если ``t`` начинается
   с ``s``. Основы идут по порядку; каждая занимает самый ранний ещё не занятый подходящий токен. Не нашлось
   токена хотя бы одной основе — алиас не совпал. Иначе ``pos`` — минимальный индекс занятого токена,
   ``score`` — сумма длин основ (в символах Unicode).
3. Название объекта (``title``) тоже алиас: его основы — все токены длиной не меньше ``TITLE_STEM_MIN``, кроме
   служебных слов ``TITLE_STOPWORDS`` («Футляр для очков» → ``футляр``, ``очков``).
4. Лучшее совпадение объекта — минимум ``(pos, -score)`` по его алиасам. Из объектов с совпадением выбираются
   те, у кого этот ключ наименьший: один — ``ok``, несколько — ``ambiguous`` (в порядке ``objects``), нет — ``none``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from engine.normalize import normalize

# Длина основы (и токена названия, ставшего основой) не меньше этого числа символов — docs/02.
STEM_MIN = 3
TITLE_STEM_MIN = STEM_MIN
# Служебные слова (предлоги, союзы, частицы), которые не становятся основами названия. Список одинаков в
# ``site/assets/js/core/labmatch.js`` (``TITLE_STOPWORDS``); изменение — только вместе с векторами и docs/02 §2а.
TITLE_STOPWORDS = frozenset("для при над под без или что как это про через между".split())
# Предупреждение сборки: общая у двух объектов основа не длиннее этого числа символов.
SHARED_STEM_WARN = 4


def norm(s: str) -> str:
    """Нормализованная строка (пустая — ``""``)."""
    return normalize("text", s) or ""


def lab_tokens(s: str) -> list[str]:
    """Токены нормализованного текста; пустая строка → ``[]``."""
    n = norm(s)
    return n.split(" ") if n else []


def alias_stems(alias: str) -> list[str]:
    """Основы нормализованного алиаса (через пробел)."""
    return [x for x in alias.split(" ") if x]


def title_stems(title: str) -> list[str]:
    """Основы алиаса-названия: токены названия длиной ≥ ``TITLE_STEM_MIN`` без служебных слов."""
    return [t for t in lab_tokens(title) if len(t) >= TITLE_STEM_MIN and t not in TITLE_STOPWORDS]


def match_stems(stems: Sequence[str], tokens: Sequence[str]) -> tuple[int, int] | None:
    """``(pos, -score)`` для алиаса из ``stems`` на ``tokens`` или ``None``."""
    if not stems:
        return None
    used: set[int] = set()
    for stem in stems:
        for i, tok in enumerate(tokens):
            if i not in used and tok.startswith(stem):
                used.add(i)
                break
        else:
            return None
    return min(used), -sum(len(s) for s in stems)


def best_match(obj: Mapping[str, Any], tokens: Sequence[str]) -> tuple[int, int] | None:
    """Лучший ключ ``(pos, -score)`` объекта ``{id, title, aliases}`` на ``tokens``."""
    candidates = [alias_stems(a) for a in obj.get("aliases") or []]
    candidates.append(title_stems(obj.get("title") or ""))
    keys = [k for k in (match_stems(stems, tokens) for stems in candidates) if k is not None]
    return min(keys) if keys else None


def resolve_object(text: str, objects: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Распознать объект: ``{"status": "ok", "id"}`` | ``{"status": "ambiguous", "ids": [...]}`` |
    ``{"status": "none"}``. ``objects`` — доступные объекты в порядке expertise.yaml;
    ``aliases`` уже нормализованы."""
    tokens = lab_tokens(text)
    found: list[tuple[tuple[int, int], str]] = []
    for obj in objects:
        key = best_match(obj, tokens)
        if key is not None:
            found.append((key, obj["id"]))
    if not found:
        return {"status": "none"}
    top = min(k for k, _ in found)
    ids = [i for k, i in found if k == top]
    if len(ids) == 1:
        return {"status": "ok", "id": ids[0]}
    return {"status": "ambiguous", "ids": ids}
