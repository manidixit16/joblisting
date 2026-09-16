"""Export generated documents to ATS-friendly PDF and DOCX.

Both formats are intentionally simple: single column, standard fonts, real
selectable text (no images or multi-column layout) so applicant-tracking
systems can parse them reliably.
"""
from __future__ import annotations

import io


def to_pdf(text: str, title: str = "Document") -> bytes:
    """Render plain text to a simple, single-column PDF with selectable text."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=18, top=18, right=18)
    pdf.add_page()
    pdf.set_title(title)

    # Core font (Helvetica) keeps the file small and ATS-parseable.
    pdf.set_font("Helvetica", size=11)
    line_height = 6

    for raw_line in (text or "").split("\n"):
        line = raw_line.rstrip()
        if not line:
            pdf.ln(line_height)
            continue
        # Bold ALL-CAPS heading lines (SUMMARY, SKILLS, ...) for readability.
        is_heading = line.isupper() and len(line) <= 40
        pdf.set_font("Helvetica", style="B" if is_heading else "", size=12 if is_heading else 11)
        # multi_cell wraps long lines; latin-1 fallback avoids font-glyph errors.
        # new_x/new_y return the cursor to the left margin on the next line so the
        # following multi_cell has the full page width available.
        pdf.multi_cell(0, line_height, _safe(line), new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()  # fpdf2 returns a bytearray
    return bytes(out)


def to_docx(text: str, title: str = "Document") -> bytes:
    """Render plain text to a simple, single-column DOCX."""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for raw_line in (text or "").split("\n"):
        line = raw_line.rstrip()
        if not line:
            doc.add_paragraph("")
            continue
        para = doc.add_paragraph()
        run = para.add_run(line)
        if line.isupper() and len(line) <= 40:
            run.bold = True
            run.font.size = Pt(12)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _safe(text: str) -> str:
    """fpdf2 core fonts are latin-1; drop characters they can't encode."""
    return text.encode("latin-1", "replace").decode("latin-1")
