from collections.abc import Mapping
from typing import Any
from unittest.mock import Mock, call

from ChromaDB.precomputed_queries import _rows, _summarize, combine_cohort_summaries


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


if __name__ == "__main__":
    test_combining_cohorts_preserves_weighted_metrics_and_row_counts()
    test_unfiltered_rows_fetch_metadata_by_bounded_id_batches()
    test_empty_unfiltered_collection_returns_without_get()
    test_filtered_rows_keep_the_where_clause_path()
    print("Precomputed query tests passed.")
