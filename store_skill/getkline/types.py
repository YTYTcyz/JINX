from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillResult:
    ok: bool
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "meta": self.meta,
        }
