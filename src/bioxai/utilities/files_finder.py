import inspect
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from fnmatch import fnmatch
from pathlib import Path
from types import MethodType
from typing import Any

from bioxai.logger.log import setup_logger
from bioxai.models.data_model import FindFilesArgs, FindFilesResult

logger = setup_logger()


# --- Helper predicates (top-level) to keep cyclomatic complexity low in find_files ---
def _ext_ok(p: Path, file_format: str | None) -> bool:
    if file_format is None:
        return True
    return p.suffix.lower() == f".{file_format.lower()}"


def _prefix_suffix_ok(p: Path, prefix: str | None, suffix: str | None) -> bool:
    name = p.name
    stem = p.stem
    if prefix is not None and not name.startswith(prefix):
        return False
    if suffix is None:
        return True
    base_no_ext = name.removesuffix(p.suffix)
    return stem.endswith(suffix) or base_no_ext.endswith(suffix)


def _patterns_ok(
    name: str, include_patterns: list[str] | None, exclude_patterns: list[str] | None
) -> bool:
    if include_patterns and not any(fnmatch(name, pat) for pat in include_patterns):
        return False
    if exclude_patterns and any(fnmatch(name, pat) for pat in exclude_patterns):
        return False
    return True


def _size_ok(p: Path, min_size_bytes: int | None) -> bool:
    if min_size_bytes is None:
        return True
    try:
        return p.stat().st_size >= min_size_bytes
    except OSError:
        return False


def _file_passes(
    p: Path,
    *,
    file_format: str | None,
    prefix: str | None,
    suffix: str | None,
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
    min_size_bytes: int | None,
) -> bool:
    name = p.name
    return (
        _ext_ok(p, file_format)
        and _prefix_suffix_ok(p, prefix, suffix)
        and _patterns_ok(name, include_patterns, exclude_patterns)
        and _size_ok(p, min_size_bytes)
    )


def _extract_year_from_filename(name: str) -> int | None:
    """
    Extract a 4-digit year (1900-2099) from a filename, with priority on specific patterns.

    Priority order:
    - 'pubmed_sorted_YYYY'
    - 'pubmed_YYYY'
    - any 4-digit year in 1900-2099 range
    """
    for pat in (
        r"pubmed_sorted_(?P<year>\d{4})",
        r"pubmed_(?P<year>\d{4})",
        r"(?P<year>19\d{2}|20\d{2})",
    ):
        m = re.search(pat, name)
        if m:
            try:
                y = int(m.group("year"))
                if 1900 <= y <= 2099:
                    return y
            except Exception:  # noqa: S112
                continue
    return None


def _build_sort_key(sort_by: str) -> Callable[[Path], Any]:
    """Return a key function for sorting paths by name, mtime, or size with OSError safety."""

    def sort_key(p: Path) -> Any:
        try:
            if sort_by == "name":
                return p.name
            elif sort_by == "mtime":
                return p.stat().st_mtime
            else:  # size
                return p.stat().st_size
        except OSError:
            return float("inf")

    return sort_key


def _validate_sort_by(sort_by: str) -> None:
    """Validate sort_by option for file sorting."""
    if sort_by not in {"name", "mtime", "size"}:
        raise ValueError("sort_by must be one of: 'name', 'mtime', 'size'")


def find_files(
    dir: str | Path,
    prefix: str | None = None,
    suffix: str | None = None,
    file_format: str | None = None,
    recursive: bool = False,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    min_size_bytes: int | None = None,
    max_files: int | None = None,
    sort_by: str = "name",  # one of: name, mtime, size
    reverse: bool = False,
) -> FindFilesResult:
    """
    Find files in a directory with flexible filtering and sorting.

    Args:
        dir: Directory to search.
        prefix: Filename should start with this value (case-sensitive). If None, ignored.
        suffix: Filename should end with this value (before extension). If None, ignored.
        file_format: Required extension without dot (e.g., "parquet"). If None, any extension allowed.
        recursive: If True, search subdirectories.
        include_patterns: Additional fnmatch-style patterns (match if any). Applied on basename.
        exclude_patterns: Fnmatch patterns to exclude (exclude if any matches). Applied on basename.
        min_size_bytes: Keep files whose size >= this value.
        max_files: If set, return at most this many files after sorting.
        sort_by: Sort key: "name" (default), "mtime" (modification time), or "size" (bytes).
        reverse: Reverse the sort order.

    Returns:
        List[Path]: Matching file paths.

    Raises:
        FileNotFoundError: If the directory does not exist.
        NotADirectoryError: If the path is not a directory.
        ValueError: If sort_by is invalid.
    """
    if not isinstance(dir, Path):
        dir = Path(dir)

    base = dir
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base}")
    if not base.is_dir():
        raise NotADirectoryError(f"Not a directory: {base}")

    pattern = "**/*" if recursive else "*"
    candidates = [p for p in base.glob(pattern) if p.is_file()]

    filtered = [
        Path(p).resolve()
        for p in candidates
        if _file_passes(
            p,
            file_format=file_format,
            prefix=prefix,
            suffix=suffix,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            min_size_bytes=min_size_bytes,
        )
    ]

    # sorting
    _validate_sort_by(sort_by)
    filtered.sort(key=_build_sort_key(sort_by), reverse=reverse)

    if max_files is not None and max_files >= 0:
        filtered = filtered[:max_files]

    logger.debug(f"find_files: dir={base}, recursive={recursive}, total_matched={len(filtered)}")

    args_obj = FindFilesArgs(
        dir=base,
        prefix=prefix,
        suffix=suffix,
        file_format=file_format,
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        min_size_bytes=min_size_bytes,
        max_files=max_files,
        sort_by=sort_by,
        reverse=reverse,
    )

    result = FindFilesResult(
        searched_dir=base,
        args=args_obj,
        files=filtered,
        total_matched=len(filtered),
        recursive=recursive,
        notes=None,
    )

    return result


def sort_files_by_year(files: list[Path], sort_by: str = "name") -> dict[int, list[Path]]:
    """
    Group files by 4-digit year inferred from filename and return a dict mapping year->list[Path].

    Extraction priority:
    - 'pubmed_sorted_YYYY'
    - 'pubmed_YYYY'
    - any 4-digit year (1900-2099) in the basename

    Args:
        files: List of Path-like items.
        sort_by: How to sort files within each year: 'name' | 'mtime' | 'size'.

    Returns:
        dict[int, list[Path]]: mapping from year to list of files.
    """
    if sort_by not in {"name", "mtime", "size"}:
        raise ValueError("sort_by must be one of: 'name', 'mtime', 'size'")

    buckets: dict[int, list[Path]] = defaultdict(list)
    for f in files:
        p = Path(f)
        y = _extract_year_from_filename(p.name)
        if y is not None:
            buckets[y].append(p)

    # Sort files inside each year bucket
    sort_key = _build_sort_key(sort_by)
    for y in buckets:
        buckets[y].sort(key=sort_key)

    # Return a normal dict sorted by year ascending
    return dict(sorted(buckets.items(), key=lambda kv: kv[0]))


def attach_function_as_method(
    target: Any,
    func: Callable[..., Any],
    name: str | None = None,
    method_kind: str = "instance",
) -> str:
    """
    Attach a standalone function to an object or class as a method at runtime.

    Args:
        target: An instance or a class to which the function will be attached.
        func: The function to attach.
        name: The attribute name under which to attach the function. Defaults to func.__name__.
        method_kind: One of {"instance", "class", "static"}.

    Behavior:
        - instance: binds to a single instance (if target is an instance) using MethodType;
                   if target is a class, sets an unbound function on the class so future
                   instances receive it as a normal method.
        - class: attaches as a classmethod on the class.
        - static: attaches as a staticmethod on the class.

    Returns:
        The final attribute name used.
    """
    if not callable(func):
        raise TypeError("func must be callable")

    if method_kind not in {"instance", "class", "static"}:
        raise ValueError("method_kind must be one of: 'instance', 'class', 'static'")

    attr_name = name or getattr(func, "__name__", None)
    if not attr_name:
        raise ValueError("name must be provided when func has no __name__")

    # Determine class vs instance
    if inspect.isclass(target):
        cls = target
        instance = None
    else:
        cls = target.__class__
        instance = target

    if method_kind == "instance":
        if instance is not None:
            # Bind to single instance only
            setattr(instance, attr_name, MethodType(func, instance))
        else:
            # Attach to class so it becomes a descriptor for all future instances
            setattr(cls, attr_name, func)
    elif method_kind == "class":
        setattr(cls, attr_name, classmethod(func))
    else:  # static
        setattr(cls, attr_name, staticmethod(func))

    return attr_name


def attach_methods_bulk(
    target: Any,
    funcs: dict[str, Callable[..., Any]] | list[Callable[..., Any]],
    method_kind: str = "instance",
) -> list[str]:
    """
    Attach multiple functions to a target as methods.

    Args:
        target: instance or class.
        funcs: mapping of name->callable or list of callables (names from __name__).
        method_kind: 'instance' | 'class' | 'static'.

    Returns:
        List of attribute names attached.
    """
    names: list[str] = []
    if isinstance(funcs, dict):
        for name, f in funcs.items():
            names.append(attach_function_as_method(target, f, name=name, method_kind=method_kind))
    else:
        for f in funcs:
            names.append(attach_function_as_method(target, f, name=None, method_kind=method_kind))
    return names


def search_files(
    root: str | Path,
    pattern: str | None = None,  # e.g. "*.h5", "*2024*.parquet"
    regex: str | None = None,  # e.g. r".*emb_\\d{4}_.*\\.h5$"
    case_insensitive: bool = True,
    max_results: int | None = None,
) -> list[Path]:
    """
    Recursively search for files under 'root'.
    - pattern: glob pattern (fast). If provided, uses rglob.
    - regex: match against full path string.
    - If both provided, results must satisfy BOTH.
    """
    root = Path(root)
    if not root.exists():
        return []

    # Start set via pattern (fast) or all files
    if pattern:
        candidates: Iterable[Path] = root.rglob(pattern)
    else:
        candidates = (p for p in root.rglob("*") if p.is_file())

    flags = re.IGNORECASE if case_insensitive else 0
    rx = re.compile(regex, flags) if regex else None

    out: list[Path] = []
    for p in candidates:
        s = str(p)
        if rx and not rx.search(s):
            continue
        out.append(p)
        if max_results and len(out) >= max_results:
            break
    return out


def find_one(
    root: str | Path,
    pattern: str | None = None,
    regex: str | None = None,
    case_insensitive: bool = True,
) -> Path | None:
    res = search_files(
        root, pattern=pattern, regex=regex, case_insensitive=case_insensitive, max_results=1
    )
    return res[0] if res else None
