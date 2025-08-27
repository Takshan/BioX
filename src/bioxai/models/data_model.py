from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FindFilesArgs:
    """
    Configuration for `vectorsage_data.utils.find_files`.

    Mirrors the function signature to make it easy to pass around and persist.
    """

    dir: str | Path
    prefix: str | None = None
    suffix: str | None = None
    file_format: str | None = None  # extension without dot, e.g. "parquet"
    recursive: bool = False
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    min_size_bytes: int | None = None
    max_files: int | None = None
    sort_by: str = "name"  # one of: name, mtime, size
    reverse: bool = False

    def __post_init__(self) -> None:
        # normalize dir
        self.dir = Path(self.dir)
        # validate sort_by
        if self.sort_by not in {"name", "mtime", "size"}:
            raise ValueError("sort_by must be one of: 'name', 'mtime', 'size'")
        # sanitize file_format
        if self.file_format:
            self.file_format = self.file_format.lstrip(".")
        # ensure lists for patterns if provided
        if self.include_patterns is not None and not isinstance(self.include_patterns, list):
            self.include_patterns = [str(self.include_patterns)]
        if self.exclude_patterns is not None and not isinstance(self.exclude_patterns, list):
            self.exclude_patterns = [str(self.exclude_patterns)]

    def as_kwargs(self) -> dict[str, Any]:
        """Return a kwargs dict matching utils.find_files signature."""
        return {
            "dir": self.dir,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "file_format": self.file_format,
            "recursive": self.recursive,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "min_size_bytes": self.min_size_bytes,
            "max_files": self.max_files,
            "sort_by": self.sort_by,
            "reverse": self.reverse,
        }


@dataclass
class FindFilesResult:
    """Result object for utils.find_files() including context and summary."""

    searched_dir: str | Path
    args: FindFilesArgs
    files: list[Path]
    total_matched: int
    recursive: bool
    notes: str | None = None
    db_file_paths: dict[int, list[Path]] | None = None

    def __post_init__(self) -> None:
        self.db_file_paths = self.group_by_year()

    def __str__(self) -> str:
        return f"""
        Search Directory: {self.searched_dir}
        Args: {self.args}
        Files: {self.files}
        Total Matched: {self.total_matched}
        Recursive: {self.recursive}
        Notes: {self.notes}
        """

    def __repr__(self) -> str:
        return f"FindFilesResult(searched_dir={self.searched_dir}, args={self.args}, files={self.files}, total_matched={self.total_matched}, recursive={self.recursive},  notes={self.notes})"

    def group_by_year(self, sort_by: str = "name") -> dict[int, list[Path]] | None:
        """Group self.files by year using the shared utility to avoid duplication."""
        # Local import to avoid circular dependency at module import time
        from vectorsage_data.utils import sort_files_by_year

        self.db_file_paths = sort_files_by_year(self.files, sort_by=sort_by)
        return self.db_file_paths
