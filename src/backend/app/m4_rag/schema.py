"""Pydantic Schemas for CTD / ICH M4 RAG Checker (Module M4).

Defines strict, validated data structures for dossier inputs,
ICH requirements, match results, completeness scores, and gap reports.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class GapStatus(str, Enum):
    """Classification status for a CTD section requirement."""
    PRESENT = "PRESENT"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CriticalityLevel(str, Enum):
    """Regulatory criticality level of an ICH M4 section."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    STANDARD = "STANDARD"
    OPTIONAL = "OPTIONAL"


class MatchMethod(str, Enum):
    """Method utilized to evaluate the dossier section against ICH requirements."""
    EXACT = "EXACT"
    SEMANTIC = "SEMANTIC"
    HYBRID = "HYBRID"
    NONE = "NONE"


class DossierSectionInput(BaseModel):
    """A single section entry parsed from a candidate CTD dossier outline."""
    section_id: str = Field(..., description="Section identifier, e.g., '2.5', '3.2.S.1', 'Module 4.2.1'")
    title: str = Field(..., description="Section heading or title")
    description: Optional[str] = Field(default="", description="Summary or description of section contents")
    content_summary: Optional[str] = Field(default=None, description="Detailed text or outline notes")
    status_hint: Optional[str] = Field(default=None, description="Self-reported status (e.g., Draft, Complete)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary metadata")

    @field_validator("section_id", "title", mode="before")
    @classmethod
    def clean_strings(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()


class DossierOutlineInput(BaseModel):
    """A collection of candidate CTD dossier sections submitted for readiness verification."""
    submission_title: Optional[str] = Field(default="Candidate Dossier", description="Submission or product title")
    drug_name: Optional[str] = Field(default="", description="Investigational / commercial drug substance name")
    target_region: Optional[str] = Field(default="Global / ICH", description="Target regulatory agency/region (FDA/EMA/PMDA)")
    sections: List[DossierSectionInput] = Field(default_factory=list, description="List of parsed dossier sections")


class ICHSectionRequirement(BaseModel):
    """Authoritative ICH M4 requirement specification record."""
    section_id: str = Field(..., description="Official ICH M4 section ID, e.g., '2.5', '3.2.S.1'")
    module_id: int = Field(..., ge=1, le=5, description="CTD Module number (1-5)")
    module_name: str = Field(..., description="Full Module Name, e.g. 'Module 2: CTD Summaries'")
    title: str = Field(..., description="Official ICH section title")
    requirement_text: str = Field(..., description="Detailed ICH guideline requirement summary")
    criticality: CriticalityLevel = Field(default=CriticalityLevel.MAJOR, description="Regulatory criticality")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Weight factor for completeness calculation")
    source: str = Field(default="ICH M4", description="Authoritative reference (ICH M4, M4Q, M4S, M4E)")
    keywords: List[str] = Field(default_factory=list, description="Domain keywords for retrieval indexing")


class MatchEvidence(BaseModel):
    """Evidence and reasoning supporting section match classification."""
    match_method: MatchMethod = Field(..., description="Matching strategy applied")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    matched_dossier_section_id: Optional[str] = Field(default=None, description="ID of matching dossier item")
    matched_dossier_title: Optional[str] = Field(default=None, description="Title of matching dossier item")
    evidence_reasoning: str = Field(..., description="Transparent factual reasoning grounding the result")


class GapItem(BaseModel):
    """Detailed gap analysis for a single ICH M4 requirement."""
    section_id: str
    module_id: int = Field(..., ge=1, le=5)
    module_name: str
    title: str
    status: GapStatus
    criticality: CriticalityLevel
    match_evidence: MatchEvidence
    action_item: Optional[str] = Field(default=None, description="Recommended remediation action for regulatory readiness")
    source_reference: str = Field(default="ICH M4 Guideline")
    requires_safety_update: bool = Field(
        default=False,
        description="True when this section is flagged for mandatory safety review due to an active FAERS/PRR CONFIRMED_SIGNAL for the drug.",
    )
    safety_update_reason: Optional[str] = Field(
        default=None,
        description="Explanation of the confirmed signal driving the mandatory safety review flag.",
    )


class ModuleCompleteness(BaseModel):
    """Completeness metrics and section tallies for an individual CTD module."""
    module_id: int = Field(..., ge=1, le=5)
    module_name: str
    total_required: int = Field(..., ge=0)
    present_count: int = Field(..., ge=0)
    partial_count: int = Field(..., ge=0)
    missing_count: int = Field(..., ge=0)
    critical_missing_count: int = Field(..., ge=0)
    completeness_percentage: float = Field(..., ge=0.0, le=100.0)


class GapReportOutput(BaseModel):
    """Full structured gap analysis and regulatory readiness report."""
    submission_title: str
    drug_name: Optional[str] = ""
    target_region: Optional[str] = "Global / ICH"
    overall_completeness: float = Field(..., ge=0.0, le=100.0, description="Deterministic readiness percentage (0-100%)")
    total_sections_evaluated: int
    present_total: int
    partial_total: int
    missing_total: int
    critical_gaps_count: int
    modules: Dict[str, ModuleCompleteness]
    present_sections: List[GapItem] = Field(default_factory=list)
    partial_sections: List[GapItem] = Field(default_factory=list)
    missing_sections: List[GapItem] = Field(default_factory=list)
    priority_gaps: List[GapItem] = Field(default_factory=list, description="Critical and Major missing/partial sections")
    recommended_actions: List[str] = Field(default_factory=list, description="Ordered actionable remediation steps")
    limitations: List[str] = Field(default_factory=list, description="Known assessment scope and boundaries")
    timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")
    safety_signal_linkage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cross-link to Mode 1 (M2 PRR) signal detection: whether this drug has an active CONFIRMED_SIGNAL and which CTD sections are flagged for mandatory safety review as a result.",
    )
