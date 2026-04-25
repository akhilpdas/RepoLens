"""RepoLens export — convert a final answer + metadata to Markdown / PDF.

Markdown export is trivial; PDF uses fpdf2 with a light markdown shim.

Unicode handling:
  - If `assets/DejaVuSans.ttf` is bundled, the PDF uses it (full Unicode).
  - Otherwise, falls back to core Helvetica with latin-1 sanitization.
"""

from __future__ import annotations

import os
from pathlib import Path

DEJAVU_PATH = Path(__file__).parent / "assets" / "DejaVuSans.ttf"


def to_markdown(
    *,
    repo_name: str,
    question: str,
    user_level: str,
    style: str,
    quality_score: int | str,
    answer: str,
    indexed_files: list[str] | None = None,
) -> str:
    """Build a self-contained Markdown export string."""
    indexed_files = indexed_files or []
    sources = "\n".join(f"- {f}" for f in indexed_files) if indexed_files else "_(none)_"
    return (
        f"# RepoLens — {repo_name}\n\n"
        f"**Question:** {question}\n\n"
        f"**User level:** {user_level}  |  **Style:** {style}  |  "
        f"**Quality:** {quality_score}/10\n\n"
        f"---\n\n"
        f"{answer}\n\n"
        f"---\n\n"
        f"## Sources (Indexed Files)\n{sources}\n"
    )


def _sanitize_for_latin1(text: str) -> str:
    """Replace non-latin-1 characters so core Helvetica won't crash."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def to_pdf(
    *,
    repo_name: str,
    question: str,
    user_level: str,
    quality_score: int | str,
    answer: str,
) -> bytes:
    """Render the answer as a simple PDF.

    Uses DejaVuSans if available (Unicode safe); else falls back to core
    Helvetica with latin-1 sanitization (fine for ASCII answers).
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    use_unicode = DEJAVU_PATH.exists()
    if use_unicode:
        try:
            pdf.add_font("DejaVu", fname=str(DEJAVU_PATH), uni=True)
            font_name = "DejaVu"
        except Exception:
            font_name = "Helvetica"
            use_unicode = False
    else:
        font_name = "Helvetica"

    def _txt(s: str) -> str:
        return s if use_unicode else _sanitize_for_latin1(s)

    # Header
    pdf.set_font(font_name, "" if use_unicode else "B", 16)
    pdf.cell(0, 10, _txt(f"RepoLens — {repo_name}"), ln=1)
    pdf.set_font(font_name, "", 11)
    def _mcell(h: float, txt: str):
        """multi_cell that always starts at the left margin (avoids
        'Not enough horizontal space' when chained after another multi_cell)."""
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, h, txt)

    _mcell(6, _txt(
        f"Q: {question}\nLevel: {user_level}  |  Quality: {quality_score}/10"
    ))
    pdf.ln(4)

    # Body — light markdown shim
    in_code_block = False
    for raw in answer.splitlines():
        line = _txt(raw)
        if raw.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            pdf.set_font("Courier" if not use_unicode else font_name, "", 10)
            _mcell(5, line or " ")
            continue
        if raw.startswith("### "):
            pdf.set_font(font_name, "" if use_unicode else "B", 12)
            pdf.cell(0, 8, line[4:], ln=1)
        elif raw.startswith("## "):
            pdf.set_font(font_name, "" if use_unicode else "B", 13)
            pdf.cell(0, 9, line[3:], ln=1)
        elif raw.startswith("# "):
            pdf.set_font(font_name, "" if use_unicode else "B", 14)
            pdf.cell(0, 10, line[2:], ln=1)
        elif raw.startswith(("- ", "* ")):
            pdf.set_font(font_name, "", 11)
            _mcell(6, "- " + line[2:])
        elif not raw.strip():
            pdf.ln(3)
        else:
            pdf.set_font(font_name, "", 11)
            _mcell(6, line)

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return bytes(out)
