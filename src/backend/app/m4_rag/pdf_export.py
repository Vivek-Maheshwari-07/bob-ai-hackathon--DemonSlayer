"""PDF Export for CTD / ICH M4 Gap Reports.

Renders an already-computed GapReportOutput (the structured content produced
by report_generator.py) into a downloadable PDF for regulatory audit records.
"""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.m4_rag.schema import GapReportOutput


def _enum_value(v) -> str:
    return v.value if hasattr(v, "value") else str(v)


def generate_gap_report_pdf(report: GapReportOutput) -> bytes:
    """Renders a GapReportOutput into a formatted PDF byte string."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        title=report.submission_title,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    cell_style = ParagraphStyle("Cell", parent=normal_style, fontSize=7.5, leading=9)
    alert_style = ParagraphStyle("Alert", parent=normal_style, textColor=colors.HexColor("#b91c1c"))

    story = []

    story.append(Paragraph(escape(report.submission_title), styles["Title"]))
    story.append(Paragraph(
        f"Drug: {escape(report.drug_name or 'N/A')} &nbsp;|&nbsp; Target Region: {escape(report.target_region or 'N/A')}",
        normal_style,
    ))
    story.append(Paragraph(f"Generated: {escape(report.timestamp)}", normal_style))
    story.append(Spacer(1, 0.2 * inch))

    if report.scale_warning:
        story.append(Paragraph(f"<b>&#9888; {escape(report.scale_warning)}</b>", alert_style))
        story.append(Spacer(1, 0.2 * inch))

    linkage = report.safety_signal_linkage or {}
    if linkage.get("has_confirmed_signal"):
        msg = linkage.get("message") or "Active FAERS/PRR safety signal on file for this drug."
        story.append(Paragraph(f"<b>&#9888; SAFETY ALERT:</b> {escape(msg)}", alert_style))
        story.append(Spacer(1, 0.2 * inch))

    summary_data = [
        ["Overall Completeness", f"{report.overall_completeness:.1f}%"],
        ["Sections Evaluated", str(report.total_sections_evaluated)],
        ["Present", str(report.present_total)],
        ["Partial", str(report.partial_total)],
        ["Missing", str(report.missing_total)],
        ["Critical Gaps", str(report.critical_gaps_count)],
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 2.5 * inch])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("CTD Module Completeness", styles["Heading2"]))
    mod_rows = [["Module", "Present", "Partial", "Missing", "Completeness %"]]
    for m in report.modules.values():
        mod_rows.append([
            Paragraph(escape(f"Module {m.module_id}: {m.module_name}"), cell_style),
            str(m.present_count),
            str(m.partial_count),
            str(m.missing_count),
            f"{m.completeness_percentage:.1f}%",
        ])
    mod_table = Table(mod_rows, colWidths=[2.6 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 1.1 * inch], repeatRows=1)
    mod_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(mod_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph(f"Priority Gaps ({len(report.priority_gaps)})", styles["Heading2"]))
    if report.priority_gaps:
        gap_rows = [
            ["Section", "Title", "Status", "Criticality", "Content Adequacy", "Authenticity", "Safety", "Action Item"]
        ]
        for g in report.priority_gaps:
            adequacy_score = getattr(g, "content_adequacy_score", None)
            if adequacy_score is None:
                adequacy_cell = Paragraph("N/A", cell_style)
            else:
                adequacy_cell = Paragraph(f"{adequacy_score * 100:.0f}%", cell_style)

            verdict = getattr(g, "authenticity_verdict", None)
            if verdict is None:
                authenticity_cell = Paragraph("N/A", cell_style)
            else:
                evidence = getattr(g, "authenticity_evidence", None) or {}
                citations = evidence.get("source_citations") or []
                missing_points = evidence.get("missing_data_points") or []
                detail_lines = [f"<b>{escape(verdict)}</b>"]
                if citations:
                    detail_lines.append(f"Compared against: {escape('; '.join(citations))}")
                if missing_points:
                    detail_lines.append(f"Missing: {escape(', '.join(missing_points))}")
                authenticity_cell = Paragraph("<br/>".join(detail_lines), cell_style)

            gap_rows.append([
                Paragraph(escape(g.section_id), cell_style),
                Paragraph(escape(g.title), cell_style),
                Paragraph(escape(_enum_value(g.status)), cell_style),
                Paragraph(escape(_enum_value(g.criticality)), cell_style),
                adequacy_cell,
                authenticity_cell,
                Paragraph("&#9888; YES" if g.requires_safety_update else "-", cell_style),
                Paragraph(escape(g.action_item or ""), cell_style),
            ])
        gap_table = Table(
            gap_rows,
            colWidths=[0.45 * inch, 0.85 * inch, 0.5 * inch, 0.5 * inch, 0.65 * inch, 1.3 * inch, 0.4 * inch, 1.75 * inch],
            repeatRows=1,
        )
        gap_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(gap_table)
    else:
        story.append(Paragraph("No priority gaps detected.", normal_style))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Recommended Actions", styles["Heading2"]))
    if report.recommended_actions:
        for i, action in enumerate(report.recommended_actions, 1):
            story.append(Paragraph(f"{i}. {escape(action)}", normal_style))
    else:
        story.append(Paragraph("No outstanding recommendations.", normal_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Assessment Limitations", styles["Heading2"]))
    for lim in report.limitations:
        story.append(Paragraph(f"&bull; {escape(lim)}", normal_style))

    doc.build(story)
    return buffer.getvalue()
