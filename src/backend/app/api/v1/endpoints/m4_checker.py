"""FastAPI Endpoints for Module M4: CTD / ICH M4 RAG Checker."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile, status

from app.m4_rag.knowledge.loader import get_knowledge_base
from app.m4_rag.pipeline import check_ctd_dossier, check_ctd_pdf
from app.m4_rag.schema import (
    DossierOutlineInput,
    GapReportOutput,
    ICHSectionRequirement,
)

router = APIRouter(prefix="/m4", tags=["Module M4: CTD Readiness Checker"])


@router.post(
    "/check",
    response_model=GapReportOutput,
    summary="Evaluate CTD Dossier Outline Against ICH M4",
    description=(
        "Performs automated hybrid RAG gap analysis evaluating candidate CTD dossier "
        "sections against official ICH M4 requirements across Modules 1 to 5. "
        "Returns deterministic completeness percentages, present/partial/missing "
        "classifications, priority regulatory gaps, and actionable recommendations."
    ),
)
async def evaluate_dossier(
    payload: DossierOutlineInput = Body(
        ...,
        examples=[
            {
                "submission_title": "Investigational Oncology Candidate NDA",
                "drug_name": "BOB-701",
                "target_region": "FDA / US",
                "sections": [
                    {
                        "section_id": "1.1",
                        "title": "Forms and Administrative Information",
                        "description": "FDA Form 356h and cover letter",
                    },
                    {
                        "section_id": "2.3",
                        "title": "Quality Overall Summary",
                        "description": "CMC summary discussing CQAs and batch release",
                    },
                    {
                        "section_id": "2.5",
                        "title": "Clinical Overview",
                        "description": "Comprehensive analysis of clinical development and benefit-risk balance",
                    },
                    {
                        "section_id": "3.2.S.1",
                        "title": "General Information",
                        "description": "Nomenclature, structure, and physicochemical properties",
                    },
                    {
                        "section_id": "4.2.3",
                        "title": "Toxicology Study Reports",
                        "description": "GLP repeat-dose toxicology reports",
                    },
                    {
                        "section_id": "5.3.5",
                        "title": "Reports of Efficacy and Safety Studies",
                        "description": "Phase 3 double-blind randomized clinical study reports",
                    },
                ],
            }
        ],
    ),
    enable_reasoning: bool = Query(
        default=True,
        description="Whether to generate grounded regulatory reasoning narratives",
    ),
) -> GapReportOutput:
    """Evaluates candidate CTD dossier against verified ICH M4 requirements."""
    try:
        report = check_ctd_dossier(payload, enable_reasoner=enable_reasoning)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating CTD dossier: {str(e)}",
        )


@router.post(
    "/quick-check-text",
    response_model=GapReportOutput,
    summary="Evaluate Plain-Text CTD Table of Contents",
    description="Parses plain-text or markdown dossier outline lines and performs readiness gap analysis.",
)
async def quick_check_text(
    raw_text: str = Body(
        ...,
        media_type="text/plain",
        examples=[
            (
                "1.1 Forms and Administrative Information\n"
                "2.5 Clinical Overview - Benefit-risk balance\n"
                "3.2.S.4 Control of Drug Substance - Release specifications\n"
                "4.2.3 Toxicology Study Reports - 28-day GLP toxicology\n"
                "5.3.5 Reports of Efficacy and Safety Studies - Pivotal Phase 3 CSRs"
            )
        ],
    ),
) -> GapReportOutput:
    """Quick check for plain-text dossier outlines."""
    try:
        report = check_ctd_dossier(raw_text, enable_reasoner=True)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing plain text outline: {str(e)}",
        )


@router.post(
    "/check-pdf",
    response_model=GapReportOutput,
    summary="Evaluate Uploaded CTD PDF Document",
    description="Extracts sections from an uploaded CTD PDF dossier using local PDF extraction and performs readiness gap analysis.",
)
async def evaluate_pdf_dossier(
    file: UploadFile = File(..., description="Uploaded CTD PDF document"),
    submission_title: Optional[str] = Form(default=None, description="Optional title for the submission"),
    enable_reasoning: bool = Form(default=True, description="Whether to invoke grounded Gemini reasoning"),
) -> GapReportOutput:
    """Evaluates uploaded CTD PDF dossier."""
    try:
        content_bytes = await file.read()
        title = submission_title or file.filename or "Uploaded CTD PDF Dossier"
        report = check_ctd_pdf(
            pdf_source=content_bytes,
            submission_title=title,
            enable_reasoner=enable_reasoning,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF dossier: {str(e)}",
        )


@router.get(
    "/requirements",
    response_model=List[ICHSectionRequirement],
    summary="List All Verified ICH M4 Section Requirements",
    description="Returns the authoritative indexed knowledge base of all ICH M4 section requirements across Modules 1 to 5.",
)
async def get_all_requirements() -> List[ICHSectionRequirement]:
    """Retrieves all indexed ICH M4 requirements."""
    kb = get_knowledge_base()
    return kb.get_all()


@router.get(
    "/module/{module_id}",
    response_model=List[ICHSectionRequirement],
    summary="Get ICH M4 Requirements for a Specific Module (1-5)",
)
async def get_module_requirements(
    module_id: int,
) -> List[ICHSectionRequirement]:
    """Retrieves ICH requirements for a specific module (1 to 5)."""
    if module_id < 1 or module_id > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="module_id must be between 1 and 5",
        )
    kb = get_knowledge_base()
    return kb.get_by_module(module_id)
