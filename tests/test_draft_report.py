from io import BytesIO

from pypdf import PdfReader

from multi_agent_framework.draft_report import build_draft_pdf


def test_draft_contains_question_answer_and_tool_error():
    pdf = build_draft_pdf(
        "¿Cuentas de la cosecha 202401?",
        "No hay resultados <verificados>.",
        {"tool_results": [{"tool": "portfolio_kpis", "result": {"error": "Sin datos"}}]},
    )
    reader = PdfReader(BytesIO(pdf), strict=True)
    text = "\n".join(page.extract_text() for page in reader.pages)

    assert "BORRADOR DE PRUEBA - NO VERIFICADO" in text
    assert "¿Cuentas de la cosecha 202401?" in text
    assert "No hay resultados <verificados>." in text
    assert "portfolio_kpis" in text
    assert "Sin datos" in text


def test_unsupported_character_is_reported():
    try:
        build_draft_pdf("📊", "Respuesta", {"tool_results": []})
    except ValueError as error:
        assert "U+1F4CA" in str(error)
    else:
        raise AssertionError("Unsupported characters must not disappear silently")


if __name__ == "__main__":
    test_draft_contains_question_answer_and_tool_error()
    test_unsupported_character_is_reported()
    print("Draft PDF tests passed.")
