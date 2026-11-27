from multi_agent_framework.response_charts import build_response_chart


METRIC_LABELS = {
    "delinquency_rate_amount": "Tasa de morosidad (monto)",
    "delinquency_rate_accounts": "Tasa de morosidad (cuentas)",
    "gross_chargeoff_rate": "Tasa de castigo bruto",
    "net_chargeoff_rate": "Tasa de castigo neto",
    "recovery_rate": "Tasa de recuperación",
    "utilization_rate": "Tasa de utilización",
    "operating_margin": "Margen operativo",
    "operating_margin_rate": "Tasa de margen operativo",
    "efficiency_ratio": "Índice de eficiencia",
    "acquisition_cost_per_account": "Costo de adquisición por cuenta",
}
NON_PERCENTAGE_METRICS = {"operating_margin", "acquisition_cost_per_account"}


def test_cohort_curve_selects_requested_metric_and_scales_percentages():
    chart = build_response_chart(
        [
            {
                "tool": "cohort_curve",
                "result": [
                    {
                        "vintage": 2024,
                        "mob": 3,
                        "metrics": {
                            "delinquency_rate_accounts": 0.125,
                            "delinquency_rate_amount": 0.2,
                        },
                    }
                ],
            }
        ],
        "Compara la morosidad por cuenta",
        METRIC_LABELS,
        NON_PERCENTAGE_METRICS,
    )

    assert chart is not None
    assert chart["kind"] == "line"
    assert chart["data"] == [
        {
            "MOB": 3,
            "Cosecha": "2024",
            "Tasa de morosidad (cuentas)": 12.5,
        }
    ]


def test_segment_ranking_uses_group_label_and_skips_missing_metrics():
    chart = build_response_chart(
        [
            {
                "tool": "segment_ranking",
                "result": [
                    {
                        "strategy": "A",
                        "metrics": {"operating_margin": 1250.5},
                    },
                    {
                        "strategy": "B",
                        "metrics": {"operating_margin": None},
                    },
                ],
            }
        ],
        "Margen operativo por estrategia",
        METRIC_LABELS,
        NON_PERCENTAGE_METRICS,
    )

    assert chart is not None
    assert chart["kind"] == "bar"
    assert chart["data"] == [{"Estrategia": "A", "Margen operativo": 1250.5}]


def test_portfolio_kpis_without_a_dimension_do_not_create_a_chart():
    chart = build_response_chart(
        [
            {
                "tool": "portfolio_kpis",
                "result": {"metrics": {"delinquency_rate_amount": 0.1}},
            }
        ],
        "Tasa de morosidad",
        METRIC_LABELS,
        NON_PERCENTAGE_METRICS,
    )

    assert chart is None


def test_vintage_comparison_builds_a_two_bar_chart():
    chart = build_response_chart(
        [
            {
                "tool": "vintage_comparison",
                "result": {
                    "baseline_vintage": 2023,
                    "comparison_vintage": 2024,
                    "metric_delta": {"delinquency_rate_amount": 0.02},
                    "baseline": {"metrics": {"delinquency_rate_amount": 0.1}},
                    "comparison": {"metrics": {"delinquency_rate_amount": 0.12}},
                },
            }
        ],
        "Compara tasa de morosidad",
        METRIC_LABELS,
        NON_PERCENTAGE_METRICS,
    )

    assert chart is not None
    assert chart["data"] == [
        {"Cosecha": "2023", "Tasa de morosidad (monto)": 10.0},
        {"Cosecha": "2024", "Tasa de morosidad (monto)": 12.0},
    ]


if __name__ == "__main__":
    test_cohort_curve_selects_requested_metric_and_scales_percentages()
    test_segment_ranking_uses_group_label_and_skips_missing_metrics()
    test_portfolio_kpis_without_a_dimension_do_not_create_a_chart()
    test_vintage_comparison_builds_a_two_bar_chart()
    print("All response chart tests passed.")
