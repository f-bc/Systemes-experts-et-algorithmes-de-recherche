"""Shared error types and validation reports."""

from __future__ import annotations

from dataclasses import dataclass, field


class ValidationError(ValueError):
    """Invalid user or file input, carrying one or more French messages."""

    def __init__(self, messages: str | list[str]) -> None:
        if isinstance(messages, str):
            messages = [messages]
        self.messages: list[str] = list(messages)
        super().__init__("; ".join(self.messages))


@dataclass
class ValidationReport:
    """Collection of validation errors and non-blocking warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no blocking error was recorded (warnings are allowed)."""
        return not self.errors
