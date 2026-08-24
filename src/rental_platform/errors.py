from dataclasses import dataclass


class PipelineError(RuntimeError):
    """Base error for an expected pipeline failure."""


@dataclass(frozen=True)
class ValidationIssue:
    entity: str
    row_number: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.entity}[row={self.row_number}] {self.code}: {self.message}"


class DataValidationError(PipelineError):
    """Raised when a Stage 1 batch fails validation."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        preview = "; ".join(str(issue) for issue in issues[:5])
        suffix = "" if len(issues) <= 5 else f"; and {len(issues) - 5} more"
        super().__init__(f"Validation failed with {len(issues)} issue(s): {preview}{suffix}")
