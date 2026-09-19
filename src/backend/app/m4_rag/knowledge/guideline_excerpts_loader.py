"""Loader for the guideline-excerpt knowledge base (Module M4).

Loads knowledge/guideline_excerpts.json into a simple section_id -> record
lookup. Kept intentionally lightweight (no pydantic model) since these
records are consumed as plain dicts by guideline_grounded_checker.py.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

DEFAULT_PATH = Path(__file__).parent / "guideline_excerpts.json"


def load_guideline_excerpts(path: Optional[Path] = None) -> Dict[str, dict]:
    """Loads guideline_excerpts.json into a {section_id: record} dict.

    Returns an empty dict (never raises) if the file is missing or malformed
    — the guideline-grounded checker treats "no excerpt for this section_id"
    as a normal, silent skip condition, so a missing/corrupt KB file should
    degrade the same way rather than crashing the pipeline.
    """
    target = path or DEFAULT_PATH
    if not target.exists():
        return {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    records = data.get("excerpts", []) if isinstance(data, dict) else (data or [])
    by_section_id: Dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        section_id = str(record.get("section_id", "")).strip()
        # Skip placeholder/cross-reference entries that don't carry real
        # excerpt_text and aren't a real gated section_id (see the
        # 3.2.S.4_Q4B_NOTE entry).
        if not section_id or not (record.get("excerpt_text") or "").strip():
            continue
        by_section_id[section_id.upper()] = record
    return by_section_id


@lru_cache(maxsize=1)
def get_guideline_excerpts() -> Dict[str, dict]:
    """Process-wide cached load of the default guideline excerpt corpus."""
    return load_guideline_excerpts()
