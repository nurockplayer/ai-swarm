from __future__ import annotations

from typing import Any

class BaseSettings:
    def __init__(self, **kwargs: Any) -> None: ...


def SettingsConfigDict(**kwargs: Any) -> dict[str, Any]: ...
