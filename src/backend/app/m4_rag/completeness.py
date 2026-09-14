"""Completeness Scorer for CTD / ICH M4 RAG Checker (Module M4).

Performs deterministic, reproducible scoring of CTD dossier completeness
both overall and module-by-module (Modules 1 to 5).
"""

from typing import Dict, List, Optional, Tuple
from app.m4_rag.knowledge.loader import get_knowledge_base, KnowledgeBaseLoader
from app.m4_rag.schema import (
    CriticalityLevel,
    GapItem,
    GapStatus,
    ICHSectionRequirement,
    ModuleCompleteness,
)


class CompletenessScorer:
    """Calculates deterministic completeness metrics for CTD dossiers."""

    # Transparent scoring weights
    WEIGHT_PRESENT = 1.0
    WEIGHT_PARTIAL = 0.5
    WEIGHT_MISSING = 0.0

    MODULE_NAMES = {
        1: "Module 1: Administrative Information",
        2: "Module 2: CTD Summaries",
        3: "Module 3: Quality",
        4: "Module 4: Nonclinical Study Reports",
        5: "Module 5: Clinical Study Reports",
    }

    def __init__(self, kb: Optional[KnowledgeBaseLoader] = None):
        self.kb = kb or get_knowledge_base()

    def calculate(
        self, gap_items: List[GapItem]
    ) -> Tuple[float, Dict[str, ModuleCompleteness]]:
        """Calculates overall completeness percentage and module-wise breakdown.
        
        Formula:
            earned_points = (present_count * 1.0) + (partial_count * 0.5) + (missing_count * 0.0)
            max_points = total_required * 1.0
            completeness = (earned_points / max_points) * 100
            
        Returns:
            Tuple of (overall_completeness_percentage, module_metrics_dict)
        """
        # Group gap items by module
        module_items: Dict[int, List[GapItem]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        for item in gap_items:
            if 1 <= item.module_id <= 5:
                module_items[item.module_id].append(item)

        module_results: Dict[str, ModuleCompleteness] = {}
        total_earned = 0.0
        total_possible = 0.0

        for mod_id in range(1, 6):
            items = module_items[mod_id]
            total_req = len(items)

            present_cnt = sum(1 for i in items if i.status == GapStatus.PRESENT)
            partial_cnt = sum(1 for i in items if i.status == GapStatus.PARTIAL)
            missing_cnt = sum(1 for i in items if i.status in (GapStatus.MISSING, GapStatus.INSUFFICIENT_EVIDENCE))
            crit_missing_cnt = sum(
                1 for i in items
                if i.status != GapStatus.PRESENT and i.criticality == CriticalityLevel.CRITICAL
            )

            mod_earned = (present_cnt * self.WEIGHT_PRESENT) + (partial_cnt * self.WEIGHT_PARTIAL)
            mod_possible = total_req * self.WEIGHT_PRESENT

            mod_pct = (mod_earned / mod_possible * 100.0) if mod_possible > 0 else 0.0
            mod_pct = round(mod_pct, 2)

            total_earned += mod_earned
            total_possible += mod_possible

            mod_key = f"module_{mod_id}"
            module_results[mod_key] = ModuleCompleteness(
                module_id=mod_id,
                module_name=self.MODULE_NAMES.get(mod_id, f"Module {mod_id}"),
                total_required=total_req,
                present_count=present_cnt,
                partial_count=partial_cnt,
                missing_count=missing_cnt,
                critical_missing_count=crit_missing_cnt,
                completeness_percentage=mod_pct,
            )

        overall_pct = (total_earned / total_possible * 100.0) if total_possible > 0 else 0.0
        overall_pct = round(overall_pct, 2)

        return overall_pct, module_results
