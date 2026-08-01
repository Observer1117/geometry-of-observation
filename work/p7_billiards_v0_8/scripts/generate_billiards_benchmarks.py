#!/usr/bin/env python3
"""Generate deterministic benchmark data for the P7 billiards release."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
P7 = ROOT / "work/p7_billiards_v0_8"
CSV_PATH = P7 / "data/billiards_benchmarks_v0_8.csv"
JSON_PATH = P7 / "data/billiards_metrics_v0_8.json"


def entropy_bits(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("entropy requires a positive total")
    result = 0.0
    for count in counts.values():
        if count:
            probability = count / total
            result -= probability * math.log2(probability)
    return result


def cyclic_conditional_entropy_bits(word: str) -> float:
    if len(word) < 2:
        raise ValueError("cyclic transition entropy requires length >= 2")
    symbol_counts = Counter(word)
    pair_counts = Counter(
        (word[index], word[(index + 1) % len(word)])
        for index in range(len(word))
    )
    total = len(word)
    result = 0.0
    for (left, _right), pair_count in pair_counts.items():
        joint = pair_count / total
        conditional = pair_count / symbol_counts[left]
        result -= joint * math.log2(conditional)
    return result


def rectangle_eigenvalue(
    width: float,
    height: float,
    mode_x: int,
    mode_y: int,
) -> float:
    if width <= 0 or height <= 0:
        raise ValueError("rectangle sides must be positive")
    if mode_x <= 0 or mode_y <= 0:
        raise ValueError("Dirichlet mode numbers must be positive")
    return math.pi**2 * (
        (mode_x / width) ** 2 + (mode_y / height) ** 2
    )


def main() -> None:
    radius = 2.3
    tangent_coordinate = 0.4
    speed = 3.0
    boundary_length = 2.0 * math.pi * radius
    collision_advance = 2.0 * radius * math.acos(tangent_coordinate)
    rotation_number = math.acos(tangent_coordinate) / math.pi
    chord_length = (
        2.0 * radius * math.sqrt(1.0 - tangent_coordinate**2)
    )
    roof_time = chord_length / speed
    reduced_angular_momentum_coordinate = radius * tangent_coordinate

    alternating = "01010101"
    order_sensitive = "00110011"
    alternating_marginal = entropy_bits(Counter(alternating))
    order_sensitive_marginal = entropy_bits(Counter(order_sensitive))
    alternating_conditional = cyclic_conditional_entropy_bits(alternating)
    order_sensitive_conditional = cyclic_conditional_entropy_bits(
        order_sensitive
    )

    width = 2.0e-9
    height = 1.0e-9
    scale = 3.0
    lambda_11 = rectangle_eigenvalue(width, height, 1, 1)
    scaled_lambda_11 = rectangle_eigenvalue(
        scale * width,
        scale * height,
        1,
        1,
    )
    area_lambda = width * height * lambda_11
    scaled_area_lambda = (
        scale * width * scale * height * scaled_lambda_11
    )

    planck_h = 6.62607015e-34
    hbar = planck_h / (2.0 * math.pi)
    electron_mass = 9.1093837139e-31
    elementary_charge = 1.602176634e-19
    energy_joule = hbar**2 * lambda_11 / (2.0 * electron_mass)
    energy_ev = energy_joule / elementary_charge

    rows = [
        {
            "benchmark": "collision_measure_normalization",
            "quantity": "integral_mu_boundary",
            "value": 1.0,
            "unit": "1",
            "status": "exact",
        },
        {
            "benchmark": "disk_map",
            "quantity": "boundary_length",
            "value": boundary_length,
            "unit": "m",
            "status": "analytic",
        },
        {
            "benchmark": "disk_map",
            "quantity": "collision_advance",
            "value": collision_advance,
            "unit": "m",
            "status": "analytic",
        },
        {
            "benchmark": "disk_map",
            "quantity": "rotation_number",
            "value": rotation_number,
            "unit": "1",
            "status": "analytic",
        },
        {
            "benchmark": "disk_map",
            "quantity": "chord_length",
            "value": chord_length,
            "unit": "m",
            "status": "analytic",
        },
        {
            "benchmark": "disk_map",
            "quantity": "roof_time",
            "value": roof_time,
            "unit": "s",
            "status": "analytic",
        },
        {
            "benchmark": "disk_map",
            "quantity": "reduced_angular_momentum_coordinate",
            "value": reduced_angular_momentum_coordinate,
            "unit": "m",
            "status": "analytic_unit_direction",
        },
        {
            "benchmark": "symbol_order",
            "quantity": "alternating_marginal_entropy",
            "value": alternating_marginal,
            "unit": "bit",
            "status": "exact",
        },
        {
            "benchmark": "symbol_order",
            "quantity": "order_sensitive_marginal_entropy",
            "value": order_sensitive_marginal,
            "unit": "bit",
            "status": "exact",
        },
        {
            "benchmark": "symbol_order",
            "quantity": "alternating_conditional_entropy",
            "value": alternating_conditional,
            "unit": "bit",
            "status": "exact_cyclic",
        },
        {
            "benchmark": "symbol_order",
            "quantity": "order_sensitive_conditional_entropy",
            "value": order_sensitive_conditional,
            "unit": "bit",
            "status": "exact_cyclic",
        },
        {
            "benchmark": "rectangle_spectrum",
            "quantity": "lambda_11",
            "value": lambda_11,
            "unit": "m^-2",
            "status": "analytic",
        },
        {
            "benchmark": "rectangle_spectrum",
            "quantity": "scaled_lambda_11",
            "value": scaled_lambda_11,
            "unit": "m^-2",
            "status": "analytic",
        },
        {
            "benchmark": "rectangle_spectrum",
            "quantity": "lambda_scaling_ratio",
            "value": scaled_lambda_11 / lambda_11,
            "unit": "1",
            "status": "analytic",
        },
        {
            "benchmark": "rectangle_spectrum",
            "quantity": "area_lambda_11",
            "value": area_lambda,
            "unit": "1",
            "status": "analytic",
        },
        {
            "benchmark": "rectangle_spectrum",
            "quantity": "scaled_area_lambda_11",
            "value": scaled_area_lambda,
            "unit": "1",
            "status": "analytic",
        },
        {
            "benchmark": "energy_bridge",
            "quantity": "electron_energy_11",
            "value": energy_joule,
            "unit": "J",
            "status": "CODATA_2022_mass_input",
        },
        {
            "benchmark": "energy_bridge",
            "quantity": "electron_energy_11",
            "value": energy_ev,
            "unit": "eV",
            "status": "CODATA_2022_mass_input",
        },
    ]

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "benchmark",
                "quantity",
                "value",
                "unit",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "schema": {
            "id": "go-p7-billiards-benchmark-metrics",
            "version": "0.8.0",
            "date": "2026-07-28",
        },
        "inputs": {
            "disk": {
                "radius_m": radius,
                "p": tangent_coordinate,
                "speed_m_per_s": speed,
            },
            "symbol_words": [alternating, order_sensitive],
            "rectangle": {
                "width_m": width,
                "height_m": height,
                "scale": scale,
                "mode": [1, 1],
            },
            "constants": {
                "planck_h_J_s": planck_h,
                "electron_mass_kg": electron_mass,
                "elementary_charge_C": elementary_charge,
            },
        },
        "metrics": {
            row["quantity"] + "_" + row["unit"]: row["value"]
            for row in rows
        },
        "row_count": len(rows),
    }
    JSON_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(CSV_PATH)
    print(JSON_PATH)


if __name__ == "__main__":
    main()
