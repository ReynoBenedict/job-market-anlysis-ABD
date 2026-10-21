from pathlib import Path

import pytest

from talentscope.normalization.role_evaluation import (
    cohen_kappa,
    evaluate,
    final_label,
    read_labels,
)


def _row(title: str, a: str, b: str, adjudicated: str = "") -> dict[str, str]:
    return {"title": title, "reviewer_a": a, "reviewer_b": b, "adjudicated": adjudicated}


def test_metrics_separate_coverage_precision_and_recall() -> None:
    rows = [
        _row("Barista", "FOOD_HOSPITALITY", "FOOD_HOSPITALITY"),  # correct
        _row("Kasir", "RETAIL_STORE", "RETAIL_STORE"),  # correct
        _row("Master of Ceremony", "OTHER", "OTHER"),  # correct OTHER
        _row(
            "Production Engineer", "PRODUCTION", "ENGINEERING", adjudicated="PRODUCTION"
        ),  # classifier: ENGINEERING
        _row(
            "Juru Parkir", "SECURITY_FACILITIES", "SECURITY_FACILITIES"
        ),  # classifier: OTHER (missed)
    ]
    result = evaluate(rows)
    assert result.titles == 5
    assert result.coverage == pytest.approx(3 / 5)  # Barista, Kasir, Production Engineer named
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(2 / 4)  # four titles have a named final label
    assert result.reviewer_agreement == pytest.approx(4 / 5)
    assert ("Production Engineer", "ENGINEERING", "PRODUCTION") in result.confusions
    assert result.families["SECURITY_FACILITIES"].recall == 0


def test_disagreement_needs_adjudication() -> None:
    with pytest.raises(ValueError, match="no adjudicated label"):
        final_label(_row("Host", "MARKETING", "OTHER"))


def test_kappa_is_one_for_perfect_and_zero_for_chance_agreement() -> None:
    assert cohen_kappa(["A", "B", "A", "B"], ["A", "B", "A", "B"]) == 1
    assert cohen_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"]) == 0


def test_unknown_codes_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "labels.csv"
    path.write_text(
        "title,reviewer_a,reviewer_b,adjudicated\nKasir,RETAIL,RETAIL_STORE,\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unknown family"):
        read_labels(path)
