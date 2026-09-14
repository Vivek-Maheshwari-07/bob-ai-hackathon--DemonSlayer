"""Knowledge base loader for authoritative ICH M4 guidelines.

Loads, validates, and indexes official ICH M4 requirements across
Modules 1 to 5 from the structured registry.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

from app.m4_rag.schema import ICHSectionRequirement, CriticalityLevel


class KnowledgeBaseLoader:
    """Manages verified ICH M4 requirements knowledge base."""

    def __init__(self, json_path: Optional[Path] = None):
        if json_path is None:
            json_path = Path(__file__).parent / "ich_m4_sections.json"
        self.json_path = Path(json_path)
        self._requirements: List[ICHSectionRequirement] = []
        self._by_id: Dict[str, ICHSectionRequirement] = {}
        self._by_module: Dict[int, List[ICHSectionRequirement]] = {
            1: [], 2: [], 3: [], 4: [], 5: []
        }
        self.load()

    def load(self) -> None:
        """Loads and parses JSON data into validated Pydantic models."""
        if not self.json_path.exists():
            raise FileNotFoundError(f"ICH M4 knowledge base file not found at {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        self._requirements.clear()
        self._by_id.clear()
        for m in range(1, 6):
            self._by_module[m].clear()

        for item in raw_data:
            req = ICHSectionRequirement(
                section_id=item["section_id"].strip(),
                module_id=int(item["module_id"]),
                module_name=item["module_name"].strip(),
                title=item["title"].strip(),
                requirement_text=item["requirement_text"].strip(),
                criticality=CriticalityLevel(item.get("criticality", "MAJOR")),
                weight=float(item.get("weight", 1.0)),
                source=item.get("source", "ICH M4"),
                keywords=item.get("keywords", []),
            )
            self._requirements.append(req)
            self._by_id[req.section_id.upper()] = req
            self._by_module[req.module_id].append(req)

    def get_all(self) -> List[ICHSectionRequirement]:
        """Returns all verified ICH requirements."""
        return list(self._requirements)

    def get_by_id(self, section_id: str) -> Optional[ICHSectionRequirement]:
        """Look up requirement by exact section ID (case-insensitive, normalized)."""
        normalized = section_id.strip().upper()
        return self._by_id.get(normalized)

    def get_by_module(self, module_id: int) -> List[ICHSectionRequirement]:
        """Returns all requirements belonging to a specific CTD module (1-5)."""
        return list(self._by_module.get(module_id, []))

    @property
    def total_count(self) -> int:
        return len(self._requirements)


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBaseLoader:
    """Singleton getter for the global ICH M4 knowledge base."""
    return KnowledgeBaseLoader()
