"""Project scanner (F2).

Walks a project folder and uses ``tree_sitter_language_pack`` to parse symbols
(functions, classes, structs, ...), imports, and per-file metrics across the
PRD's seven languages. On top of the structural parse it applies lightweight
heuristics to detect *services* (deployable units), *API endpoints* (HTTP route
declarations), and *databases* (engines referenced in config/infra files).

The public surface — ``scan_project(root_path, max_files=...) -> ScanMetadata``
and ``ScanMetadata.to_dict()`` — is unchanged from the original stub, so the
scan API and tests keep working; the data behind it is now real.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from app.scanner.languages import (
    IGNORE_DIRS,
    language_for_path,
    parse_id_for_path,
)

# How many bytes we are willing to read+parse from a single file. Guards against
# pathological generated files blowing the scan-time budget (PRD: <5 min/100k).
_MAX_PARSE_BYTES = 1_000_000

# Cap the number of enriched file/symbol records we retain in memory; counts are
# always exact, but we don't keep every symbol of a 500k-LOC repo around.
_MAX_FILE_RECORDS = 5_000
_MAX_SYMBOLS_PER_FILE = 200


# --- Endpoint detection -----------------------------------------------------
# Route declarations differ per framework but share recognisable shapes. These
# patterns are deliberately broad: a false positive costs one phantom endpoint
# in a count, while structural parsing (above) carries the precise symbols.
_ENDPOINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # FastAPI / Flask: @app.get("/x"), @router.post('/y')
    re.compile(r"@\w+\.(get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    # Express / Nest: app.get('/x'), router.post("/y")
    re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    # Spring: @GetMapping, @RequestMapping(...)
    re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\b"),
    # Go nethttp / chi / gin: r.GET("/x"), mux.HandleFunc("/y", ...)
    re.compile(r"\.(GET|POST|PUT|PATCH|DELETE|HandleFunc)\s*\("),
    # ASP.NET: [HttpGet], [HttpPost("x")]
    re.compile(r"\[Http(Get|Post|Put|Patch|Delete)\b"),
)

# Infra/config tokens that imply a backing database engine.
_DB_TOKENS: dict[str, re.Pattern[str]] = {
    "PostgreSQL": re.compile(r"postgres|postgresql|psycopg", re.IGNORECASE),
    "MySQL": re.compile(r"\bmysql\b|mariadb", re.IGNORECASE),
    "MongoDB": re.compile(r"mongodb|mongo:", re.IGNORECASE),
    "Redis": re.compile(r"\bredis\b", re.IGNORECASE),
    "SQLite": re.compile(r"sqlite", re.IGNORECASE),
    "Qdrant": re.compile(r"\bqdrant\b", re.IGNORECASE),
    "Neo4j": re.compile(r"\bneo4j\b", re.IGNORECASE),
    "Elasticsearch": re.compile(r"elasticsearch|opensearch", re.IGNORECASE),
    "Cassandra": re.compile(r"\bcassandra\b", re.IGNORECASE),
}

# Files that mark a directory as a deployable service, and the regexes used to
# pull a database engine out of infra files.
_SERVICE_MARKERS: frozenset[str] = frozenset(
    {
        "dockerfile",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "cargo.toml",
        "requirements.txt",
        "*.csproj",  # handled by suffix check below
    }
)
_INFRA_FILES: frozenset[str] = frozenset(
    {"docker-compose.yml", "docker-compose.yaml", ".env", ".env.example"}
)


@dataclass
class Symbol:
    name: str
    kind: str  # function, class, method, struct, interface, enum, ...
    line: int


@dataclass
class FileRecord:
    path: str
    language: str | None
    size: int
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "size": self.size,
            "symbols": [{"name": s.name, "kind": s.kind, "line": s.line} for s in self.symbols],
            "imports": self.imports,
        }


@dataclass
class ScanMetadata:
    file_count: int = 0
    total_bytes: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    files: list[FileRecord] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    endpoint_count: int = 0
    symbol_count: int = 0
    code_lines: int = 0
    parse_errors: int = 0

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "languages": self.languages,
            "service_count": len(self.services),
            "database_count": len(self.databases),
            "endpoint_count": self.endpoint_count,
            "symbol_count": self.symbol_count,
            "code_lines": self.code_lines,
            "parse_errors": self.parse_errors,
            "services": self.services,
            "databases": sorted(self.databases),
            "note": "tree-sitter scan: symbols, imports, services, endpoints, databases",
        }


def _read_text(path: str, limit: int = _MAX_PARSE_BYTES) -> str | None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(limit + 1)
    except OSError:
        return None
    if b"\x00" in raw[:1024]:  # binary file — skip
        return None
    return raw[:limit].decode("utf-8", errors="replace")


def _detect_endpoints(text: str) -> int:
    """Count HTTP route declarations, de-duplicating overlapping matches.

    Different framework patterns can match the same declaration (e.g. the
    decorator pattern and the call pattern both fire on ``@app.get(``). We merge
    overlapping match spans so each route is counted once.
    """
    spans: list[tuple[int, int]] = []
    for pat in _ENDPOINT_PATTERNS:
        spans.extend((m.start(), m.end()) for m in pat.finditer(text))
    if not spans:
        return 0
    spans.sort()
    count = 0
    cur_end = -1
    for start, end in spans:
        if start >= cur_end:  # disjoint from the previous match -> new endpoint
            count += 1
            cur_end = end
        else:
            cur_end = max(cur_end, end)
    return count


def _detect_databases(text: str) -> set[str]:
    return {name for name, pat in _DB_TOKENS.items() if pat.search(text)}


def _is_service_marker(fname: str) -> bool:
    low = fname.lower()
    return low in _SERVICE_MARKERS or low.endswith(".csproj")


def _parse_symbols(text: str, parse_id: str) -> tuple[list[Symbol], list[str], int, int]:
    """Return (symbols, imports, code_lines, parse_errors) for ``text``.

    Imports come back from the parser as raw source fragments; we keep them as
    strings for the code graph's dependency edges. Failure to parse degrades to
    empty results rather than aborting the scan.
    """
    # Imported lazily so a missing optional dependency doesn't break a bare
    # ``import app`` at startup; the scanner is the only caller.
    from tree_sitter_language_pack import ProcessConfig, process

    try:
        result = process(
            text,
            ProcessConfig(
                language=parse_id,
                structure=True,
                imports=True,
                diagnostics=True,
            ),
        )
    except Exception:  # noqa: BLE001 - any parse failure degrades gracefully
        return [], [], 0, 1

    symbols: list[Symbol] = []

    def walk(items: list, depth: int = 0) -> None:
        for item in items:
            if len(symbols) >= _MAX_SYMBOLS_PER_FILE:
                return
            symbols.append(
                Symbol(
                    name=item.name or "<anonymous>",
                    kind=str(item.kind).lower(),
                    line=item.span.start_line + 1,
                )
            )
            if item.children:
                walk(item.children, depth + 1)

    walk(list(result.structure))

    imports = [imp.source for imp in result.imports if imp.source]
    metrics = result.metrics
    code_lines = getattr(metrics, "code_lines", 0)
    parse_errors = 1 if getattr(metrics, "error_count", 0) else 0
    return symbols, imports, code_lines, parse_errors


def scan_project(root_path: str, max_files: int = 50_000) -> ScanMetadata:
    """Walk ``root_path`` and return structural + heuristic metadata."""
    meta = ScanMetadata()
    if not os.path.isdir(root_path):
        raise FileNotFoundError(f"Project path does not exist: {root_path}")

    databases: set[str] = set()
    # Set of dir relpaths flagged as services by a build marker.
    service_dirs: set[str] = set()
    # dir relpath -> {languages seen}, tracked for every dir so a service's
    # language is correct regardless of file-walk order within the dir.
    dir_langs: dict[str, set[str]] = {}

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = os.path.relpath(dirpath, root_path)

        for fname in filenames:
            if meta.file_count >= max_files:
                _finalise(meta, databases, service_dirs, dir_langs, root_path)
                return meta

            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root_path)
            lang = language_for_path(fname)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0

            meta.file_count += 1
            meta.total_bytes += size
            if lang:
                meta.languages[lang] = meta.languages.get(lang, 0) + 1
                dir_langs.setdefault(rel_dir, set()).add(lang)

            # Service detection: a marker file flags its directory as a service.
            if _is_service_marker(fname):
                service_dirs.add(rel_dir)

            # Infra / config files contribute database detection only.
            if fname.lower() in _INFRA_FILES:
                text = _read_text(full)
                if text:
                    databases |= _detect_databases(text)

            parse_id = parse_id_for_path(fname)
            record = FileRecord(path=rel, language=lang, size=size)

            if parse_id and size <= _MAX_PARSE_BYTES:
                text = _read_text(full)
                if text is not None:
                    symbols, imports, code_lines, perr = _parse_symbols(text, parse_id)
                    record.symbols = symbols
                    record.imports = imports
                    meta.symbol_count += len(symbols)
                    meta.code_lines += code_lines
                    meta.parse_errors += perr
                    meta.endpoint_count += _detect_endpoints(text)
                    databases |= _detect_databases(text)

            if len(meta.files) < _MAX_FILE_RECORDS:
                meta.files.append(record)

    _finalise(meta, databases, service_dirs, dir_langs, root_path)
    return meta


# Languages we don't treat as a service's "primary" language (data/config only).
_NON_PRIMARY_LANGS = {"Markdown", "reStructuredText", "JSON", "YAML", "TOML"}


def _primary_language(langs: set[str]) -> str | None:
    """Pick a service's primary language, preferring real code over config."""
    code = sorted(langs - _NON_PRIMARY_LANGS)
    return code[0] if code else (sorted(langs)[0] if langs else None)


def _finalise(
    meta: ScanMetadata,
    databases: set[str],
    service_dirs: set[str],
    dir_langs: dict[str, set[str]],
    root_path: str,
) -> None:
    """Fold accumulated detections into the metadata object."""
    meta.databases = sorted(databases)

    project_name = os.path.basename(os.path.normpath(root_path)) or "project"

    # Fallback: a flat repo with code but no build markers is itself one
    # service rooted at the project directory.
    if not service_dirs and any(meta.languages):
        service_dirs.add(".")

    services: list[dict] = []
    for rel_dir in sorted(service_dirs):
        # Aggregate languages from the service dir and everything under it.
        langs: set[str] = set()
        for d, ls in dir_langs.items():
            if rel_dir in (".", "") or d == rel_dir or d.startswith(rel_dir.rstrip("/") + "/"):
                langs |= ls
        if rel_dir in (".", ""):
            name, path = project_name, "."
        else:
            name, path = os.path.basename(rel_dir), rel_dir
        services.append({"name": name, "path": path, "language": _primary_language(langs)})
    meta.services = services
