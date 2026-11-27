"""Generate local, explicitly unverified PDF drafts from chat evidence."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import reportlab
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


FONT_NAME = "ObsAgentVera"
if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(
        TTFont(FONT_NAME, str(Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"))
    )


def build_draft_pdf(question: str, answer: str, trace: dict[str, Any]) -> bytes:
    """Create a test draft; no claim in it is marked as verified."""
    sections = [
        ("Pregunta", question),
        ("Respuesta del agente", answer),
        (
            "Trazabilidad",
            json.dumps(trace, ensure_ascii=False, indent=2, default=str),
        ),
    ]
    warning = (
        "BORRADOR DE PRUEBA - NO VERIFICADO. "
        "Los datos y las conclusiones no se han verificado automáticamente."
    )
    font = pdfmetrics.getFont(FONT_NAME)
    supported = font.face.charWidths
    for text in [warning, *(content for _, content in sections)]:
        unsupported = sorted({
            char for char in text
            if char not in "\n\r\t" and ord(char) not in supported
        })
        if unsupported:
            raise ValueError(
                "El PDF de prueba no admite estos caracteres: "
                + ", ".join(f"U+{ord(char):04X}" for char in unsupported)
            )

    heading = ParagraphStyle(
        "heading", fontName=FONT_NAME, fontSize=13, leading=17,
        textColor=colors.HexColor("#0B2030"), spaceAfter=6,
    )
    body = ParagraphStyle(
        "body", fontName=FONT_NAME, fontSize=9, leading=13,
        alignment=TA_LEFT, wordWrap="CJK",
    )
    alert = ParagraphStyle(
        "alert", parent=body, textColor=colors.HexColor("#A00028"), spaceAfter=12,
    )
    story = [
        Paragraph("ObsAgent - reporte de prueba", heading),
        Paragraph(escape(warning), alert),
    ]
    for title, text in sections:
        story.append(Paragraph(escape(title), heading))
        for line in text.splitlines() or [""]:
            story.append(Paragraph(escape(line) or "&#160;", body))
        story.append(Spacer(1, 4 * mm))

    buffer = BytesIO()
    SimpleDocTemplate(buffer, title="ObsAgent - reporte de prueba").build(story)
    data = buffer.getvalue()
    if not PdfReader(BytesIO(data), strict=True).pages:
        raise ValueError("No se pudo validar el PDF generado.")
    return data
