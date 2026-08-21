"""Structured diagnostics for ezplot.

The renderer is deliberately forgiving: malformed values should produce a useful
chart where possible instead of taking down a notebook or web application.
This module makes those recoveries observable without forcing applications to
parse console output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class Severity(str, Enum):
    """Diagnostic importance, ordered from least to most severe."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_ORDER = {level: index for index, level in enumerate(Severity)}


@dataclass(frozen=True)
class Diagnostic:
    """One human- and machine-readable ezplot event."""

    severity: Severity
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exception_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "context": dict(self.context),
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.exception_type,
        }

    def __str__(self) -> str:
        suffix = ""
        if self.context:
            suffix = " (" + ", ".join(
                "%s=%r" % (key, value) for key, value in sorted(self.context.items())
            ) + ")"
        return "[%s] %s: %s%s" % (self.severity.value.upper(), self.code, self.message, suffix)


class DiagnosticLog:
    """An in-memory, bounded collection of :class:`Diagnostic` objects.

    A log is attached to every ``Plot``. A process-wide log is also available
    through :func:`get_diagnostics` for configuration and factory-level events.
    """

    def __init__(self, max_entries: int = 200) -> None:
        self.max_entries = max(1, int(max_entries))
        self._entries: List[Diagnostic] = []

    def emit(
        self,
        severity: Severity | str,
        code: str,
        message: str,
        exception_type: Optional[str] = None,
        **context: Any,
    ) -> Diagnostic:
        if not isinstance(severity, Severity):
            severity = Severity(str(severity).lower())
        diagnostic = Diagnostic(
            severity, str(code), str(message), dict(context), exception_type=exception_type
        )
        self._entries.append(diagnostic)
        overflow = len(self._entries) - self.max_entries
        if overflow > 0:
            del self._entries[:overflow]
        return diagnostic

    def exception(
        self, exc: BaseException, *, phase: str = "operation", **context: Any
    ) -> Diagnostic:
        """Interpret an exception as a stable diagnostic code."""
        severity = Severity.ERROR
        if isinstance(exc, (MemoryError, RecursionError, SystemError)):
            severity = Severity.CRITICAL
        code = "ezplot.%s.failed" % phase.replace(" ", "_").lower()
        return self.emit(
            severity,
            code,
            str(exc) or exc.__class__.__name__,
            exception_type=exc.__class__.__name__,
            **context,
        )

    def entries(self, minimum: Severity | str | None = None) -> List[Diagnostic]:
        """Return a snapshot, optionally filtered by minimum severity."""
        if minimum is None:
            return list(self._entries)
        if not isinstance(minimum, Severity):
            minimum = Severity(str(minimum).lower())
        return [item for item in self._entries if _ORDER[item.severity] >= _ORDER[minimum]]

    def clear(self) -> None:
        self._entries.clear()

    def has_errors(self) -> bool:
        return bool(self.entries(Severity.ERROR))

    def report(self, minimum: Severity | str | None = None) -> str:
        """Format diagnostics for logs, terminals, or bug reports."""
        entries = self.entries(minimum)
        return "\n".join(str(item) for item in entries) if entries else "No ezplot diagnostics."

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterable[Diagnostic]:
        return iter(self.entries())


_GLOBAL_DIAGNOSTICS = DiagnosticLog()


def get_diagnostics() -> DiagnosticLog:
    """Return ezplot's process-wide diagnostic log."""
    return _GLOBAL_DIAGNOSTICS


def interpret_exception(exc: BaseException, *, phase: str = "operation", **context: Any) -> Diagnostic:
    """Record an exception in the global log and return its interpretation."""
    return _GLOBAL_DIAGNOSTICS.exception(exc, phase=phase, **context)
