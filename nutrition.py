"""Dataset validation and non-digestibility-adjusted amino-acid scoring."""

import csv
from dataclasses import dataclass
import math
import re


ESSENTIAL = ("histidine", "isoleucine", "leucine", "lysine", "methionine",
             "phenylalanine", "threonine", "tryptophan", "valine")
AMINO_ACIDS = ESSENTIAL + ("cysteine", "tyrosine")
# WHO/FAO/UNU 2007 adult scoring pattern, mg amino acid / g protein.
# Methionine+cysteine and phenylalanine+tyrosine are combined scoring groups.
REFERENCE = (
    ("Histidine", ("histidine",), 15),
    ("Isoleucine", ("isoleucine",), 30),
    ("Leucine", ("leucine",), 59),
    ("Lysine", ("lysine",), 45),
    ("Methionine + cysteine", ("methionine", "cysteine"), 22),
    ("Phenylalanine + tyrosine", ("phenylalanine", "tyrosine"), 38),
    ("Threonine", ("threonine",), 23),
    ("Tryptophan", ("tryptophan",), 6),
    ("Valine", ("valine",), 39),
)
CSV_FIELDS = ["id", "name", "category", "protein_g"] + [f"{aa}_mg" for aa in AMINO_ACIDS]


@dataclass(frozen=True)
class Food:
    id: str
    name: str
    category: str
    protein_g: float
    amino: dict

    def to_dict(self):
        return {"id": self.id, "name": self.name, "category": self.category,
                "protein_g": self.protein_g,
                **{f"{key}_mg": value for key, value in self.amino.items()}}


def finite_number(value, label, minimum=0, maximum=100000):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.") from None
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number


def load_foods(stream):
    """Validate the whole CSV before the caller changes its linked-list store."""
    reader = csv.DictReader(stream)
    if reader.fieldnames != CSV_FIELDS:
        raise ValueError("CSV columns must match the downloadable template exactly.")
    foods, ids, names = [], set(), set()
    for line, row in enumerate(reader, 2):
        if len(foods) >= 250:
            raise ValueError("Import at most 250 foods for this teaching demo.")
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {line}: incorrect number of columns.")
        row = {key: value.strip() for key, value in row.items()}
        food_id, name, category = row["id"], row["name"], row["category"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", food_id):
            raise ValueError(f"Row {line}: use a lowercase id with letters, digits and hyphens.")
        if not name or len(name) > 80 or not category or len(category) > 40:
            raise ValueError(f"Row {line}: name (1–80) and category (1–40) are required.")
        if food_id in ids or name.casefold() in names:
            raise ValueError(f"Row {line}: duplicate food id or name.")
        protein = finite_number(row["protein_g"], f"Row {line} protein", 0.01, 100)
        amino = {aa: finite_number(row[f"{aa}_mg"], f"Row {line} {aa}") for aa in AMINO_ACIDS}
        if sum(amino.values()) > protein * 1000 * 1.05:
            raise ValueError(f"Row {line}: amino acid mass exceeds protein mass (5% rounding tolerance).")
        foods.append(Food(food_id, name, category, protein, amino))
        ids.add(food_id)
        names.add(name.casefold())
    if not foods:
        raise ValueError("The dataset must contain at least one food.")
    return foods


def analyze(portions, foods):
    """Portions are grams; source food values are per 100 g edible portion."""
    total_protein = 0.0
    amino = dict.fromkeys(AMINO_ACIDS, 0.0)
    for portion in portions:
        food = foods.find(lambda value: value.id == portion["food_id"])
        if food is None:
            raise ValueError("A selected food is no longer in the dataset.")
        scale = portion["grams"] / 100
        total_protein += food.protein_g * scale
        for aa in amino:
            amino[aa] += food.amino[aa] * scale
    groups = []
    for label, members, reference in REFERENCE:
        amount = sum(amino[aa] for aa in members)
        target = total_protein * reference
        coverage = amount / target * 100 if target else 0
        groups.append({"name": label, "amount_mg": round(amount, 2),
                       "reference_mg_per_g": reference, "target_mg": round(target, 2),
                       "coverage": round(coverage, 2), "meets": bool(target and amount >= target)})
    lowest = min(groups, key=lambda group: group["coverage"])
    return {"protein_g": round(total_protein, 2),
            "essential_mg": round(sum(amino[aa] for aa in ESSENTIAL), 2),
            "amino_mg": {aa: round(value, 2) for aa, value in amino.items()},
            "groups": groups, "score": lowest["coverage"] if total_protein else 0,
            "limiting": lowest["name"] if total_protein else None,
            "met_count": sum(group["meets"] for group in groups),
            "meets_pattern": bool(total_protein and all(group["meets"] for group in groups))}


ANALYSIS_METRICS = {"protein_g": "Protein (g / 100 g food)",
                    "essential_mg": "Essential amino acids (mg / 100 g food)",
                    "score": "Reference-pattern score (%)"}


def analysis_catalog(foods):
    rows = []
    for food in foods:
        profile = analyze([{"food_id": food.id, "grams": 100}], foods)
        rows.append({"id": food.id, "name": food.name, "category": food.category,
                     **{metric: profile[metric] for metric in ANALYSIS_METRICS},
                     "met_count": profile["met_count"], "groups": profile["groups"]})
    return rows


def complement_graph(foods):
    """Edge: 100 g + 100 g scores >5 points above the weaker single-food score.

    Illustrative pairing rule, not dietary advice; a pair need not meet every
    reference group. The undirected graph is constructed in O(n²) time.
    """
    items = list(foods)
    vectors = {}
    for food in items:
        vectors[food.id] = [sum(food.amino[aa] for aa in members) / reference
                            for _, members, reference in REFERENCE]
    graph = {food.id: [] for food in items}
    for i, left in enumerate(items):
        left_score = min(vectors[left.id]) / left.protein_g * 100
        for right in items[i + 1:]:
            right_score = min(vectors[right.id]) / right.protein_g * 100
            pair_score = min(a + b for a, b in zip(vectors[left.id], vectors[right.id]))
            pair_score = pair_score / (left.protein_g + right.protein_g) * 100
            if pair_score > min(left_score, right_score) + 5:
                graph[left.id].append(right.id)
                graph[right.id].append(left.id)
    return graph