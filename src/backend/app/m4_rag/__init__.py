"""Module M4: CTD / ICH M4 RAG Checker Package."""

from app.m4_rag.schema import (
    DossierSectionInput,
    DossierOutlineInput,
    ICHSectionRequirement,
    GapStatus,
    CriticalityLevel,
    MatchMethod,
    MatchEvidence,
    GapItem,
    ModuleCompleteness,
    GapReportOutput,
)
from app.m4_rag.pdf_extractor import CTDPDFExtractor
from app.m4_rag.gemini_reasoner import GeminiGroundedReasoner
from app.m4_rag.pipeline import CTDRagCheckerPipeline, check_ctd_dossier, check_ctd_pdf

__all__ = [
    "DossierSectionInput",
    "DossierOutlineInput",
    "ICHSectionRequirement",
    "GapStatus",
    "CriticalityLevel",
    "MatchMethod",
    "MatchEvidence",
    "GapItem",
    "ModuleCompleteness",
    "GapReportOutput",
    "CTDPDFExtractor",
    "GeminiGroundedReasoner",
    "CTDRagCheckerPipeline",
    "check_ctd_dossier",
    "check_ctd_pdf",
]
