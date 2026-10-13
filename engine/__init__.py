"""Сборщик онлайн-части игры «За кулисами правды».

Запуск: ``python -m engine <команда>`` (см. ``python -m engine --help``).
"""

from pathlib import Path

__version__ = "0.1.0"

# Корень репозитория: engine/ лежит прямо в нём (установка — pip install -e .).
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
