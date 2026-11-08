from __future__ import annotations

from functools import lru_cache

from .registry import UnifiedRegistry
from .defaults import create_default_capabilities

@lru_cache(maxsize=1)
def get_capabilities() -> UnifiedRegistry:
    """
    Возвращает единый реестр возможностей приложения.

    Реестр создаётся один раз на время работы процесса.
    """
    return create_default_capabilities()

def reset_capabilities() -> None:
    """
    Сбрасывает кэш реестра.

    Нужен для тестов и повторной инициализации.
    """
    get_capabilities.cache_clear()
