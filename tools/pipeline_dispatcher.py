"""
Справочная реализация диспетчера плана для pipeline (skil.md).
Можно использовать в тестах или скриптах; оркестрация в Cursor — через скилл pipeline.
"""

from __future__ import annotations

from typing import Literal

Verdict = Literal["OK", "FAIL"]


class Dispatcher:
    def __init__(self, plan: list[str]) -> None:
        self._plan = list(plan)
        self._index = 0

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def plan(self) -> list[str]:
        return list(self._plan)

    def get_next_task(self) -> str:
        """Текущий пункт или ALL_DONE, если все пункты закрыты OK-ами."""
        if self._index >= len(self._plan):
            return "ALL_DONE"
        return self._plan[self._index]

    def receive_qa_verdict(self, verdict: Verdict) -> None:
        if verdict == "OK":
            self._index += 1
        # FAIL: индекс не меняется — повторяем тот же пункт

    def is_done(self) -> bool:
        return self._index >= len(self._plan)
