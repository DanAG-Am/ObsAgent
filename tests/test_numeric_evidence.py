from multi_agent_framework.numeric_evidence import numeric_evidence


def test_numeric_evidence_sources_rounding_and_units():
    trace = {
        "tool_results": [
            {"tool": "portfolio_kpis", "arguments": {"filters": {"mob": 99}},
             "result": {"metrics": {"delinquency_rate_amount": 0.09579455},
                        "measures": {"accounts": 42}}},
            {"tool": "vintage_comparison",
             "result": {"metric_delta": {"delinquency_rate_amount": -0.006}}},
            {"tool": "portfolio_kpis", "result": {"error": "failed", "value": 700}},
            {"tool": "consultar_skill", "result": {"example": 800}},
        ],
        "dashboard_context": {"metric": "delinquency_rate_amount", "resumen": {"valor": 0.0958}},
    }
    claims = numeric_evidence("9.58%, -0.6 puntos porcentuales, 42 cuentas, 700 y 800; MOB 99.", trace)
    assert claims[0]["total_fuentes_posibles"] == 2
    assert "metrics.delinquency_rate_amount" in claims[0]["fuentes_posibles"][0]
    assert "metric_delta" in claims[1]["fuentes_posibles"][0]
    assert "measures.accounts" in claims[2]["fuentes_posibles"][0]
    assert all(not claim["fuentes_posibles"] for claim in claims[3:])
    assert not numeric_evidence("0.6%", trace)[0]["fuentes_posibles"]
    assert not numeric_evidence("-0.6%", trace)[0]["fuentes_posibles"]
    assert not numeric_evidence("9.58 puntos porcentuales", trace)[0]["fuentes_posibles"]
    assert not numeric_evidence("9,580%", trace)[0]["fuentes_posibles"]


if __name__ == "__main__":
    test_numeric_evidence_sources_rounding_and_units()
    print("Numeric evidence tests passed.")
