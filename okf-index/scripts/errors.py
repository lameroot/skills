"""Skill errors with semantic exit codes (Agent Surface convention).

Exit codes: 0 success · 1 failure · 2 usage · 3 not found · 4 permission · 5 conflict.
"""
from __future__ import annotations


class SkillError(Exception):
    """Base error. Carries a stable `code`, `retriable` flag, semantic `exit_code`, optional `hint`."""

    code: str = "skill"
    retriable: bool = False
    exit_code: int = 1
    hint: str | None = None

    def __init__(
        self,
        message: str = "",
        *,
        code: str | None = None,
        hint: str | None = None,
        retriable: bool | None = None,
        exit_code: int | None = None,
    ) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        if hint is not None:
            self.hint = hint
        if retriable is not None:
            self.retriable = retriable
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(SkillError):
    code = "usage"
    exit_code = 2


class NotFoundError(SkillError):
    code = "not_found"
    exit_code = 3


class PermissionDeniedError(SkillError):
    code = "permission_denied"
    exit_code = 4


class ConflictError(SkillError):
    code = "conflict"
    exit_code = 5
