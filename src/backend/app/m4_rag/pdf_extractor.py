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
        max_pages: Optional[int] = 100,
    ) -> str:
        """Extracts text content page-by-page from a PDF source.
        
        Supports file path, bytes, or file-like binary stream.
        """
        extracted_pages: List[str] = []

        # Strategy 1: pdfplumber (highest fidelity for layout & tables)
        if pdfplumber is not None:
            try:
                stream = io.BytesIO(pdf_source) if isinstance(pdf_source, bytes) else pdf_source
                with pdfplumber.open(stream) as pdf:
                    total_pages = len(pdf.pages)
                    limit = min(total_pages, max_pages) if max_pages else total_pages
                    for i in range(limit):
                        page = pdf.pages[i]
                        text = page.extract_text()
                        if text:
                            extracted_pages.append(text)
                if extracted_pages:
                    return "\n\n".join(extracted_pages)
            except Exception:
                pass

        # Strategy 2: pypdfium2 fallback
        if pypdfium2 is not None:
            try:
                doc = pypdfium2.PdfDocument(pdf_source)
                total_pages = len(doc)
                limit = min(total_pages, max_pages) if max_pages else total_pages
                for i in range(limit):
                    page = doc[i]
                    textpage = page.get_textpage()
                    text = textpage.get_text_range()
                    if text:
                        extracted_pages.append(text)
                if extracted_pages:
                    return "\n\n".join(extracted_pages)
            except Exception:
                pass

        return "\n\n".join(extracted_pages)

    @classmethod
    def extract_outline_from_pdf(
        cls,
        pdf_source: Union[str, bytes, BinaryIO],
        submission_title: str = "Candidate CTD Dossier (PDF)",
        max_pages: Optional[int] = 100,
    ) -> DossierOutlineInput:
        """Extracts text and structures it into a normalized DossierOutlineInput."""
        raw_text = cls.extract_text_from_pdf(pdf_source, max_pages=max_pages)
        if not raw_text:
            return DossierOutlineInput(
                submission_title=submission_title,
                sections=[],
            )

        # Parse sections identified in text
        sections: List[DossierSectionInput] = []
        lines = raw_text.splitlines()

        current_sec_id: Optional[str] = None
        current_title: Optional[str] = None
        current_desc_chunks: List[str] = []

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
                        )
                    )
                    current_desc_chunks = []

                raw_id = match.group(1).strip()
                rest = match.group(2).strip()
                parts = re.split(r"\s*[\-–—:]\s*", rest, maxsplit=1)
                current_sec_id = raw_id
                current_title = parts[0].strip()
                if len(parts) > 1 and parts[1].strip():
                    current_desc_chunks.append(parts[1].strip())
            else:
                if current_sec_id and len(current_desc_chunks) < 5:
                    if len(line_str) > 5 and not line_str.startswith("Page "):
                        current_desc_chunks.append(line_str)

        # Flush final section
        if current_sec_id and current_title:
            sections.append(
                DossierSectionInput(
                    section_id=current_sec_id,
                    title=current_title,
                    description=" ".join(current_desc_chunks).strip()[:1000],
                )
            )

        # If regex matching found structured sections, normalize and return
        if sections:
            return DossierParser.parse_input(
                DossierOutlineInput(
                    submission_title=submission_title,
                    sections=sections,
                )
            )

        # Heuristic fallback: pass full raw text into universal parser
        return DossierParser.parse_input(raw_text)
