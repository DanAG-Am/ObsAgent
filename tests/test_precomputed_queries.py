from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock, call, patch

from ChromaDB.precomputed_queries import (
    _rows, _summarize, _where, anomaly_candidates, cohort_curve,
    combine_cohort_summaries, dashboard_dimension_values, iqr_fences, portfolio_alerts,
)
from multi_agent_framework.fraud_demo import analyze_synthetic_fraud


def test_combining_cohorts_preserves_weighted_metrics_and_row_counts():
    raw_rows: list[Mapping[str, Any]] = [
        {"accounts": 10, "enrolled_amount": 100, "net_chargeoff_amount": 10},
        {"accounts": 20, "enrolled_amount": 400, "net_chargeoff_amount": 20},
        {"accounts": 5, "enrolled_amount": 500, "net_chargeoff_amount": 0},
    ]
    cohorts = [_summarize(raw_rows[:2]), _summarize(raw_rows[2:])]

    combined = combine_cohort_summaries(cohorts)

    assert combined == _summarize(raw_rows)
    assert combined["metrics"]["net_chargeoff_rate"] == 0.03
    assert combine_cohort_summaries([]) == _summarize([])


def test_unfiltered_rows_fetch_metadata_by_bounded_id_batches():
    aggregates = Mock()
    aggregates.count.return_value = 2
    aggregates.get.side_effect = [
        {"ids": ["aggregate-1", "aggregate-2"]},
        {"metadatas": [{"vintage": 2024}, {"vintage": 2025}]},
    ]

    rows = _rows(aggregates)

    assert rows == [{"vintage": 2024}, {"vintage": 2025}]
    assert aggregates.get.call_args_list == [
        call(limit=2, include=[]),
        call(ids=["aggregate-1", "aggregate-2"], include=["metadatas"]),
    ]


def test_empty_unfiltered_collection_returns_without_get():
    aggregates = Mock()
    aggregates.count.return_value = 0

    assert _rows(aggregates) == []
    aggregates.get.assert_not_called()


def test_filtered_rows_keep_the_where_clause_path():
    aggregates = Mock()
    aggregates.get.return_value = {"metadatas": [{"vintage": 2024}]}

    rows = _rows(aggregates, {"vintage": 2024})

    assert rows == [{"vintage": 2024}]
    aggregates.get.assert_called_once_with(
        where={"vintage": 2024},
        include=["metadatas"],
        limit=5_000,
        offset=0,
    )


def test_numeric_string_filters_are_coerced_without_changing_text_dimensions():
    assert _where({"vintage": "202401", "mob": "6", "product": "202401"}) == {
        "$and": [{"vintage": 202401}, {"mob": 6}, {"product": "202401"}]
    }
    for invalid in ("202401x", "2024.01", "-1", "", "２０２４０１"):
        try:
            _where({"vintage": invalid})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid vintage accepted: {invalid}")


def test_segment_filters_use_aggregate_metadata_and_preserve_scope():
    import chromadb
    collection = chromadb.EphemeralClient().create_collection("segment_filter_test")
    collection.add(
        ids=["a", "b"], embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"vintage": 202401, "mob": 0, "product": "A", "channel": "Web",
             "strategy": "S", "accounts": 5, "enrolled_amount": 100, "over30_amount": 10},
            {"vintage": 202401, "mob": 0, "product": "B", "channel": "Web",
             "strategy": "S", "accounts": 20, "enrolled_amount": 100, "over30_amount": 40},
        ],
    )
    assert dashboard_dimension_values(collection) == {
        "product": ["A", "B"], "channel": ["Web"], "strategy": ["S"],
    }
    rows = cohort_curve(collection, {"product": "A"})
    assert len(rows) == 1
    assert rows[0]["measures"]["accounts"] == 5
    assert rows[0]["metrics"]["delinquency_rate_amount"] == 0.1


def test_synthetic_fraud_rates_and_shared_iqr():
    result = analyze_synthetic_fraud()
    assert result["tipo"] == "demostracion_sintetica"
    assert "no detecta fraude real" in result["aviso"]
    assert result["q1"] == 0.002
    assert result["q3"] == 0.004
    assert abs(result["limite_superior"] - 0.007) < 1e-12
    assert [(row["canal"], row["incidentes_simulados"], row["transacciones_simuladas"])
            for row in result["resultados"] if row["valor_atipico"]] == [
                ("Canal simulado F", 20, 1000)
            ]
    assert all(row["tasa"] == row["incidentes_simulados"] / row["transacciones_simuladas"]
               for row in result["resultados"])


def test_iqr_preserves_portfolio_convention_and_zero_spread():
    assert iqr_fences([5, 1, 4, 2, 3]) == (2, 4, -1.0, 7.0)
    assert iqr_fences([1, 1, 1, 1]) == (1, 1, 1, 1)
    try:
        iqr_fences([1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("Fewer than four values must be rejected")
    rows = [{"measures": {"accounts": 10}, "metrics": {"delinquency_rate_amount": value}}
            for value in [1, 1, 1, 1, 10]]
    with patch("ChromaDB.precomputed_queries.kpis_by_dimension", return_value=rows):
        assert anomaly_candidates(Mock(), "product", "delinquency_rate_amount") == []
    with patch("ChromaDB.precomputed_queries.kpis_by_dimension", return_value=rows[:3]):
        assert anomaly_candidates(Mock(), "product", "delinquency_rate_amount") == []


def test_portfolio_alerts_use_complete_peers_and_correct_denominators():
    rows = []
    for index in range(105):
        rate = 0.1 + (index % 4) * 0.01 if index < 104 else 0.8
        rows.append({
            "product": str(index),
            **_summarize([{"accounts": 100, "enrolled_amount": 200,
                           "over30_amount": 200 * rate, "enrolled_accounts": 50,
                           "over30_accounts": 5}]),
        })
    rows.append({"product": "small", **_summarize([{"accounts": 2, "enrolled_amount": 10}])})
    rows.append({"product": "zero", **_summarize([{"accounts": 100}])})
    with patch("ChromaDB.precomputed_queries.kpis_by_dimension", return_value=rows) as group:
        result = portfolio_alerts(Mock(), "product", "delinquency_rate_amount",
                                  {"vintage": 202401, "mob": 6, "channel": "Web"}, 10)
        assert result["peer_count"] == 105 and result["excluded_count"] == 2
        assert result["denominator"] == "enrolled_amount"
        assert result["candidates"][0]["product"] == "104"
        assert result["candidates"][0]["measures"]["enrolled_amount"] == 200
        group.assert_called_once()
        all_anomalies = anomaly_candidates(Mock(), "product", "delinquency_rate_amount",
                                           minimum_accounts=10)
        assert any(row["product"] == "104" for row in all_anomalies)
        accounts = portfolio_alerts(Mock(), "product", "delinquency_rate_accounts",
                                    {"vintage": 202401, "mob": 6}, 10)
        assert accounts["denominator"] == "enrolled_accounts"
        assert accounts["status"] == "zero_iqr" and accounts["candidates"] == []
    with patch("ChromaDB.precomputed_queries.kpis_by_dimension", return_value=rows[:3]):
        assert portfolio_alerts(Mock(), "product", "delinquency_rate_amount",
                                {"vintage": 202401, "mob": 6}, 10)["status"] == "insufficient_peers"
    for filters in ({"vintage": 202401}, {"vintage": 202401, "mob": 6, "product": "A"}):
        try:
            portfolio_alerts(Mock(), "product", "delinquency_rate_amount", filters, 10)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid alert scope was accepted")


if __name__ == "__main__":
    test_combining_cohorts_preserves_weighted_metrics_and_row_counts()
    test_unfiltered_rows_fetch_metadata_by_bounded_id_batches()
    test_empty_unfiltered_collection_returns_without_get()
    test_filtered_rows_keep_the_where_clause_path()
    test_numeric_string_filters_are_coerced_without_changing_text_dimensions()
    test_segment_filters_use_aggregate_metadata_and_preserve_scope()
    test_synthetic_fraud_rates_and_shared_iqr()
    test_iqr_preserves_portfolio_convention_and_zero_spread()
    test_portfolio_alerts_use_complete_peers_and_correct_denominators()
    print("Precomputed query tests passed.")
