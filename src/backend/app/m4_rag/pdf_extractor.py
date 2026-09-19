"""Local PDF Extractor and Document Chunker for Module M4.

Extracts text, section headings, and structured candidate CTD outlines
from PDF dossiers using pdfplumber and pypdfium2 without external cloud dependencies.
"""

import io
import re
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdfium2
except ImportError:
    pypdfium2 = None

from app.m4_rag.dossier_parser import DossierParser
from app.m4_rag.schema import DossierOutlineInput, DossierSectionInput


class CTDPDFExtractor:
    """Extracts text and identifies CTD sections from PDF documents."""

    # Regex matching CTD section headers in PDF text
    SECTION_HEADER_REGEX = re.compile(
        r"^(?:(?:Module|Mod|Sec|Section|M)\s*)?([1-5](?:\.[0-9A-Za-z]+)+|\b[1-5]\b)(?:[:\-\s\t]+)(.+)$",
        re.MULTILINE | re.IGNORECASE,
    )

    @classmethod
    def extract_text_from_pdf(
        cls,
        pdf_source: Union[str, bytes, BinaryIO],
        max_pages: Optional[int] = 300,
    ) -> str:
        """Extracts text content page-by-page from a PDF source.

        Supports file path, bytes, or file-like binary stream.
        """
        text, _ = cls._extract_text_and_page_count(pdf_source, max_pages=max_pages)
        return text

    @classmethod
    def _extract_text_and_page_count(
        cls,
        pdf_source: Union[str, bytes, BinaryIO],
        max_pages: Optional[int] = 300,
    ) -> Tuple[str, int]:
        """Extracts text content page-by-page, alongside the source's total physical page count.

        The page count (independent of `max_pages` truncation) feeds the Tier
        0 document-scale sanity check — a 5-page file cannot plausibly
        contain genuine Module 5 clinical study report content, regardless of
        how much of it we bothered to text-extract.
        """
        extracted_pages: List[str] = []
        total_pages = 0

        # Strategy 1: pdfplumber (highest fidelity for layout & tables)
        if pdfplumber is not None:
            try:
                stream = io.BytesIO(pdf_source) if isinstance(pdf_source, bytes) else pdf_source
                with pdfplumber.open(stream) as pdf:
                    total_pages = len(pdf.pages)
                    limit = min(total_pages, max_pages) if max_pages is not None else total_pages
                    for i in range(limit):
                        # Scoped per-page so one malformed page (bad font/table)
                        # only drops that page instead of discarding every
                        # page already extracted before it.
                        try:
                            text = pdf.pages[i].extract_text()
                            if text:
                                extracted_pages.append(text)
                        except Exception:
                            continue
                if extracted_pages:
                    return "\n\n".join(extracted_pages), total_pages
            except Exception:
                pass

        # Strategy 2: pypdfium2 fallback
        if pypdfium2 is not None:
            try:
                doc = pypdfium2.PdfDocument(pdf_source)
                total_pages = len(doc)
                limit = min(total_pages, max_pages) if max_pages is not None else total_pages
                for i in range(limit):
                    try:
                        textpage = doc[i].get_textpage()
                        text = textpage.get_text_range()
                        if text:
                            extracted_pages.append(text)
                    except Exception:
                        continue
                if extracted_pages:
                    return "\n\n".join(extracted_pages), total_pages
            except Exception:
                pass

        return "\n\n".join(extracted_pages), total_pages

    @classmethod
    def extract_outline_from_pdf(
        cls,
        pdf_source: Union[str, bytes, BinaryIO],
        submission_title: str = "Candidate CTD Dossier (PDF)",
        max_pages: Optional[int] = 300,
    ) -> DossierOutlineInput:
        """Extracts text and structures it into a normalized DossierOutlineInput."""
        raw_text, total_pages = cls._extract_text_and_page_count(pdf_source, max_pages=max_pages)
        if not raw_text:
            return DossierOutlineInput(
                submission_title=submission_title,
                sections=[],
                source_page_count=total_pages or None,
                source_total_word_count=0,
            )
        total_word_count = len(raw_text.split())

        # Parse sections identified in text
        sections: List[DossierSectionInput] = []
        lines = raw_text.splitlines()

        current_sec_id: Optional[str] = None
        current_title: Optional[str] = None
        current_desc_chunks: List[str] = []
        # Uncapped accumulation of every qualifying line between this
        # section's heading and the next — the ground truth the Tier 0
        # substance gate checks word count against. `current_desc_chunks`
        # above stays capped/truncated; it's a display preview, not evidence.
        current_body_chunks: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = cls.SECTION_HEADER_REGEX.match(line_str)
            if match:
                # Save previous section if exists
                if current_sec_id and current_title:
                    sections.append(
                        DossierSectionInput(
                            section_id=current_sec_id,
                            title=current_title,
                            description=" ".join(current_desc_chunks).strip()[:1000],
                            body_text=" ".join(current_body_chunks).strip(),
                        )
                    )
                    current_desc_chunks = []
                    current_body_chunks = []

                raw_id = match.group(1).strip()
                rest = match.group(2).strip()
                parts = re.split(r"\s*[\-–—:]\s*", rest, maxsplit=1)
                current_sec_id = raw_id
                current_title = parts[0].strip()
                if len(parts) > 1 and parts[1].strip():
                    current_desc_chunks.append(parts[1].strip())
                    current_body_chunks.append(parts[1].strip())
            else:
                if current_sec_id and len(line_str) > 5 and not line_str.startswith("Page "):
                    current_body_chunks.append(line_str)
                    if len(current_desc_chunks) < 5:
                        current_desc_chunks.append(line_str)

        # Flush final section
        if current_sec_id and current_title:
            sections.append(
                DossierSectionInput(
                    section_id=current_sec_id,
                    title=current_title,
                    description=" ".join(current_desc_chunks).strip()[:1000],
                    body_text=" ".join(current_body_chunks).strip(),
                )
            )

        # If regex matching found structured sections, normalize and return
        if sections:
            outline = DossierParser.parse_input(
                DossierOutlineInput(
                    submission_title=submission_title,
                    sections=sections,
                )
            )
        else:
            # Heuristic fallback: pass full raw text into universal parser
            outline = DossierParser.parse_input(raw_text)

        outline.source_page_count = total_pages
        outline.source_total_word_count = total_word_count
        return outline
