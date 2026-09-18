"""Dossier Outline Parser and Normalizer for Module M4.

Parses, normalizes, deduplicates, and validates candidate CTD dossier
outlines from structured dictionaries, JSON payloads, or raw text.
"""

import re
from typing import Any, Dict, List, Optional, Union
from app.m4_rag.schema import DossierOutlineInput, DossierSectionInput


class DossierParser:
    """Robust parser and normalizer for CTD dossier inputs."""

    # Regex patterns to normalize section IDs. The lookahead requires a digit
    # right after the prefix run, so free text that merely starts with "M"/
    # "Sec"/"Mod" (e.g. "Manufacturing", "Second Quality Attribute") is left
    # untouched instead of having its first letters silently stripped.
    PREFIX_REGEX = re.compile(
        r"^(?:module\s*|mod\s*|m\s*|sec(?:tion)?\.?\s*|#\s*)+(?=\d)",
        re.IGNORECASE,
    )

    @classmethod
    def normalize_section_id(cls, raw_id: str) -> str:
        """Normalizes section identifier strings.
        
        Examples:
            'Module 2.5' -> '2.5'
            'm3.2.s.1' -> '3.2.S.1'
            'Sec. 4.2.1' -> '4.2.1'
            ' 5.3.5 ' -> '5.3.5'
        """
        if not raw_id or not isinstance(raw_id, str):
            return ""

        cleaned = raw_id.strip()
        # Remove common prefixes like 'Module ', 'Sec ', 'M'
        cleaned = cls.PREFIX_REGEX.sub("", cleaned).strip()

        # Standardize separators (replace hyphens/underscores if used as dot substitutes)
        cleaned = re.sub(r"[_\-]+", ".", cleaned)
        # Collapse multiple dots
        cleaned = re.sub(r"\.+", ".", cleaned)
        cleaned = cleaned.strip(".")

        # Standardize ICH capitalization (e.g., '3.2.s.1' -> '3.2.S.1', '3.2.p.8' -> '3.2.P.8', '3.2.a' -> '3.2.A')
        parts = cleaned.split(".")
        normalized_parts = []
        for p in parts:
            if len(p) == 1 and p.isalpha():
                normalized_parts.append(p.upper())
            else:
                normalized_parts.append(p)

        return ".".join(normalized_parts)

    @classmethod
    def parse_input(
        cls,
        raw_data: Union[DossierOutlineInput, Dict[str, Any], List[Any], str],
    ) -> DossierOutlineInput:
        """Universal entry point to parse various input formats into a validated DossierOutlineInput."""
        if isinstance(raw_data, DossierOutlineInput):
            return cls._normalize_outline(raw_data)

        if isinstance(raw_data, dict):
            return cls._parse_dict(raw_data)

        if isinstance(raw_data, list):
            return cls._parse_list(raw_data)

        if isinstance(raw_data, str):
            return cls._parse_text(raw_data)

        # Fallback for unexpected types
        return DossierOutlineInput(
            submission_title="Candidate Dossier",
            sections=[],
        )

    @classmethod
    def _normalize_outline(cls, outline: DossierOutlineInput) -> DossierOutlineInput:
        """Deduplicates and normalizes an existing DossierOutlineInput."""
        normalized_sections: List[DossierSectionInput] = []
        seen_ids: Dict[str, int] = {}

        for sec in outline.sections:
            norm_id = cls.normalize_section_id(sec.section_id)
            title = (sec.title or "").strip()
            desc = (sec.description or "").strip()

            if not norm_id and not title:
                # Discard completely empty entry
                continue

            cleaned_sec = DossierSectionInput(
                section_id=norm_id or sec.section_id,
                title=title or (f"Section {norm_id}" if norm_id else "Untitled Section"),
                description=desc,
                content_summary=sec.content_summary,
                status_hint=sec.status_hint,
                metadata=sec.metadata or {},
            )

            # Deduplication key
            dedup_key = norm_id.upper() if norm_id else f"TITLE:{title.upper()}"

            if dedup_key in seen_ids:
                # Merge into existing item: keep richer description / metadata
                existing_idx = seen_ids[dedup_key]
                existing = normalized_sections[existing_idx]
                merged_desc = existing.description
                if len(desc) > len(existing.description or ""):
                    merged_desc = desc
                elif desc and desc not in (existing.description or ""):
                    merged_desc = f"{existing.description} | {desc}"

                normalized_sections[existing_idx] = DossierSectionInput(
                    section_id=existing.section_id,
                    title=existing.title if len(existing.title) >= len(cleaned_sec.title) else cleaned_sec.title,
                    description=merged_desc,
                    content_summary=existing.content_summary or cleaned_sec.content_summary,
                    status_hint=existing.status_hint or cleaned_sec.status_hint,
                    metadata={**existing.metadata, **cleaned_sec.metadata},
                )
            else:
                seen_ids[dedup_key] = len(normalized_sections)
                normalized_sections.append(cleaned_sec)

        return DossierOutlineInput(
            submission_title=(outline.submission_title or "Candidate Dossier").strip(),
            drug_name=(outline.drug_name or "").strip(),
            target_region=(outline.target_region or "Global / ICH").strip(),
            sections=normalized_sections,
        )

    @classmethod
    def _parse_dict(cls, data: Dict[str, Any]) -> DossierOutlineInput:
        """Parses dictionary payload."""
        title = data.get("submission_title") or data.get("title") or "Candidate Dossier"
        drug = data.get("drug_name") or data.get("drug") or ""
        region = data.get("target_region") or data.get("region") or "Global / ICH"
        raw_sections = data.get("sections") or data.get("items") or []

        parsed_sections: List[DossierSectionInput] = []
        for item in raw_sections:
            if isinstance(item, dict):
                sec_id = str(item.get("section_id") or item.get("id") or item.get("number") or "")
                sec_title = str(item.get("title") or item.get("name") or item.get("heading") or "")
                sec_desc = str(item.get("description") or item.get("summary") or item.get("content") or "")
                sec_status = item.get("status_hint") or item.get("status")
                parsed_sections.append(
                    DossierSectionInput(
                        section_id=sec_id,
                        title=sec_title,
                        description=sec_desc,
                        status_hint=str(sec_status) if sec_status else None,
                        metadata=item.get("metadata", {}),
                    )
                )
            elif isinstance(item, str):
                parsed = cls._parse_line_to_section(item)
                if parsed:
                    parsed_sections.append(parsed)

        return cls._normalize_outline(
            DossierOutlineInput(
                submission_title=title,
                drug_name=drug,
                target_region=region,
                sections=parsed_sections,
            )
        )

    @classmethod
    def _parse_list(cls, items: List[Any]) -> DossierOutlineInput:
        """Parses list of section dicts or outline strings."""
        dict_payload = {"submission_title": "Candidate Dossier", "sections": items}
        return cls._parse_dict(dict_payload)

    @classmethod
    def _parse_text(cls, text: str) -> DossierOutlineInput:
        """Parses raw text/markdown table of contents outline into structured sections."""
        lines = text.strip().splitlines()
        sections: List[DossierSectionInput] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            parsed = cls._parse_line_to_section(line_str)
            if parsed:
                sections.append(parsed)

        return cls._normalize_outline(
            DossierOutlineInput(
                submission_title="Candidate Dossier from Text Outline",
                sections=sections,
            )
        )

    @classmethod
    def _parse_line_to_section(cls, line: str) -> Optional[DossierSectionInput]:
        """Heuristically extracts section_id, title, and description from a text line.
        
        Example lines:
            "2.5 Clinical Overview - Benefit risk analysis of phase 3"
            "Module 3.2.S.1: General Information on API"
            "5.3.5 Reports of Efficacy and Safety Studies"
            "- 4.2.3 Toxicology Studies (Single and repeat dose)"
        """
        clean_line = re.sub(r"^[\s*\-#>]+", "", line).strip()
        # Look for section ID at start of cleaned line
        match = re.search(
            r"^(?:(?:Module|Mod|Sec|Section|M)\s*)?([1-5](?:\.[0-9A-Za-z]+)+|\b[1-5]\b)(?:[:\-\s\t]+)(.*)$",
            clean_line,
            re.IGNORECASE,
        )
        if match:
            raw_id = match.group(1).strip()
            rest = match.group(2).strip()
            # Split title and description if separated by '-' or ':'
            parts = re.split(r"\s*[\-–—:]\s*", rest, maxsplit=1)
            title = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            return DossierSectionInput(
                section_id=raw_id,
                title=title or f"Section {raw_id}",
                description=desc,
            )

        # If no explicit section ID was found at line start, ignore decorative banner lines
        stripped = line.strip()
        if re.match(r"^[=\-_#*]+\s*.*[=\-_#*]+$", stripped) and not re.search(r"\d", stripped):
            return None
        if re.match(r"^(?:table\s+of\s+contents|contents|index|summary|overview)\s*$", stripped, re.IGNORECASE):
            return None

        if len(stripped) > 3:
            return DossierSectionInput(
                section_id="",
                title=stripped,
                description="",
            )
        return None
