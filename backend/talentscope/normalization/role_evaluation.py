"""Evaluation of the rule-based role taxonomy against reviewed labels.

Procedure (docs/ml/ROLE_EVALUATION.md):
1. ``sample``: draw a seeded random sample of job titles and write them WITHOUT the
   classifier's output, so reviewers label blind.
2. Two reviewers label every title independently with one family code each, following
   the written guideline; a third column records the adjudicated label for disagreements.
3. ``score``: compare the classifier with the adjudicated labels and report coverage,
   precision, recall, per-family errors, and inter-reviewer agreement (Cohen's kappa).

Pure functions here; the CLI wrapper lives in talentscope.cli.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from talentscope.normalization.role_family import ROLE_TAXONOMY_VERSION, classify_role_family
from talentscope.vocab import RoleFamily

LABEL_COLUMNS = ("reviewer_a", "reviewer_b", "adjudicated")


@dataclass
class FamilyScore:
    support: int = 0  # titles whose adjudicated label is this family
    predicted: int = 0  # titles the classifier put in this family
    correct: int = 0

    @property
    def precision(self) -> float | None:
        return self.correct / self.predicted if self.predicted else None

    @property
    def recall(self) -> float | None:
        return self.correct / self.support if self.support else None


@dataclass
class Evaluation:
    taxonomy_version: str
    titles: int
    coverage: float  # share of titles the classifier assigns to a named family
    precision: float  # among titles assigned a named family, share that match the label
    recall: float  # among titles whose label is a named family, share found by the classifier
    accuracy: float  # all titles, OTHER included
    reviewer_agreement: float
    cohen_kappa: float
    families: dict[str, FamilyScore] = field(default_factory=dict)
    confusions: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (title, predicted, label)


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    valid = {family.value for family in RoleFamily}
    for number, row in enumerate(rows, start=2):
        for column in LABEL_COLUMNS:
            if row.get(column) and row[column] not in valid:
                raise ValueError(f"line {number}: unknown family {row[column]!r} in {column}")
        if not row.get("reviewer_a") or not row.get("reviewer_b"):
            raise ValueError(f"line {number}: both reviewers must label every title")
    return rows


def final_label(row: dict[str, str]) -> str:
    """The reviewers' label when they agree, otherwise the adjudicated one."""
    if row["reviewer_a"] == row["reviewer_b"]:
        return row["reviewer_a"]
    if not row.get("adjudicated"):
        raise ValueError(
            f"reviewers disagree on {row['title']!r} and no adjudicated label is given"
        )
    return row["adjudicated"]


def cohen_kappa(first: list[str], second: list[str]) -> float:
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / len(first)
    a_counts, b_counts = Counter(first), Counter(second)
    expected = sum(a_counts[label] * b_counts[label] for label in a_counts) / len(first) ** 2
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def evaluate(rows: list[dict[str, str]]) -> Evaluation:
    other = RoleFamily.OTHER.value
    families: dict[str, FamilyScore] = {family.value: FamilyScore() for family in RoleFamily}
    confusions = []
    named_predicted = named_labels = named_correct_predicted = named_found = correct = 0
    for row in rows:
        predicted = classify_role_family(row["title"]).value
        label = final_label(row)
        families[label].support += 1
        families[predicted].predicted += 1
        if predicted == label:
            families[label].correct += 1
            correct += 1
        else:
            confusions.append((row["title"], predicted, label))
        if predicted != other:
            named_predicted += 1
            named_correct_predicted += predicted == label
        if label != other:
            named_labels += 1
            named_found += predicted == label
    first = [row["reviewer_a"] for row in rows]
    second = [row["reviewer_b"] for row in rows]
    return Evaluation(
        taxonomy_version=ROLE_TAXONOMY_VERSION,
        titles=len(rows),
        coverage=named_predicted / len(rows),
        precision=named_correct_predicted / named_predicted if named_predicted else 0.0,
        recall=named_found / named_labels if named_labels else 0.0,
        accuracy=correct / len(rows),
        reviewer_agreement=sum(a == b for a, b in zip(first, second, strict=True)) / len(rows),
        cohen_kappa=cohen_kappa(first, second),
        families={
            code: score for code, score in families.items() if score.support or score.predicted
        },
        confusions=confusions,
    )
