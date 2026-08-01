#!/usr/bin/env python3
"""Generate the reproducible Planck-to-cosmos scale catalogue and TeX tables."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / "work/p3_planck_cosmos_v0_4"
INPUT = P3 / "data/planck_cosmos_inputs_v0_4.yaml"
CSV_OUTPUT = P3 / "data/planck_cosmos_landmarks_v0_4.csv"
JSON_OUTPUT = P3 / "data/planck_cosmos_metrics_v0_4.json"
TEX_PLANCK = P3 / "src/generated/planck_anchor_table.tex"
TEX_COSMIC = P3 / "src/generated/cosmic_landmark_table.tex"
TEX_CATALOGUE = P3 / "src/generated/selected_scale_catalogue_table.tex"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: YAML root is not a mapping")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt_scientific(value: float, digits: int = 6) -> str:
    if value == 0:
        return "0"
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10.0**exponent)
    return rf"{mantissa:.{digits - 1}f}\times 10^{{{exponent}}}"


def main() -> None:
    data = load_yaml(INPUT)
    constants = data["defining_constants"]
    anchors = data["planck_anchors"]
    conversions = data["unit_conversions"]
    cosmology = data["cosmology_baseline"]

    c = float(constants["speed_of_light"]["value_si"])
    h = float(constants["planck_constant"]["value_si"])
    hbar = h / (2.0 * math.pi)
    gravitational_constant = float(constants["gravitational_constant"]["value_si"])

    computed_planck = {
        "planck_length": math.sqrt(hbar * gravitational_constant / c**3),
        "planck_mass": math.sqrt(hbar * c / gravitational_constant),
        "planck_time": math.sqrt(hbar * gravitational_constant / c**5),
    }
    for key, computed in computed_planck.items():
        listed = float(anchors[key]["value_si"])
        uncertainty = float(anchors[key]["standard_uncertainty_si"])
        if abs(computed - listed) > 3.0 * uncertainty:
            raise ValueError(f"{key}: formula and listed CODATA value disagree")

    light_year = float(conversions["light_year"]["value_si"])
    julian_year = float(conversions["Julian_year"]["value_si"])
    megaparsec = float(conversions["megaparsec"]["value_si"])
    diameter = float(cosmology["horizon_diameter"]["value"]) * light_year
    age = float(cosmology["universe_age"]["value"]) * julian_year
    hubble_si = (
        float(cosmology["hubble_constant"]["value"]) * 1000.0 / megaparsec
    )
    rho_critical = 3.0 * hubble_si**2 / (
        8.0 * math.pi * gravitational_constant
    )
    radius = diameter / 2.0
    flat_horizon_volume = 4.0 * math.pi * radius**3 / 3.0
    mass_equivalents = {
        "cosmic_baryonic_mass_equivalent": (
            float(cosmology["omega_b"]["value"])
            * rho_critical
            * flat_horizon_volume
        ),
        "cosmic_matter_mass_equivalent": (
            float(cosmology["omega_m"]["value"])
            * rho_critical
            * flat_horizon_volume
        ),
        "cosmic_total_energy_mass_equivalent": (
            rho_critical * flat_horizon_volume
        ),
    }

    reference_values = {
        "length": float(anchors["planck_length"]["value_si"]),
        "mass": float(anchors["planck_mass"]["value_si"]),
        "time": float(anchors["planck_time"]["value_si"]),
    }
    rows: list[dict[str, str | float]] = []
    for entry in data["catalogue"]:
        record = dict(entry)
        if "derived" in record:
            value = mass_equivalents[str(record["id"])]
        else:
            value = float(record["value_si"])
        axis = str(record["axis"])
        coordinate = math.log10(value / reference_values[axis])
        rows.append(
            {
                "id": str(record["id"]),
                "axis": axis,
                "value_si": value,
                "unit_si": str(record["unit_si"]),
                "planck_log10_coordinate": coordinate,
                "role": str(record["role"]),
                "status": str(record["status"]),
                "convention": str(record["convention"]),
                "source": str(record["source"]),
            }
        )

    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    anchor_spans = {
        "length_legacy_span_decades": math.log10(
            diameter / reference_values["length"]
        ),
        "time_age_span_decades": math.log10(age / reference_values["time"]),
        "baryonic_mass_span_decades": math.log10(
            mass_equivalents["cosmic_baryonic_mass_equivalent"]
            / reference_values["mass"]
        ),
        "matter_mass_span_decades": math.log10(
            mass_equivalents["cosmic_matter_mass_equivalent"]
            / reference_values["mass"]
        ),
        "total_energy_mass_span_decades": math.log10(
            mass_equivalents["cosmic_total_energy_mass_equivalent"]
            / reference_values["mass"]
        ),
    }
    metrics = {
        "schema": {
            "id": "go-planck-cosmos-generated-metrics",
            "version": "0.4.0",
            "input_sha256": sha256(INPUT),
        },
        "computed_constants": {
            "hbar_J_s": hbar,
            "planck_length_m": computed_planck["planck_length"],
            "planck_mass_kg": computed_planck["planck_mass"],
            "planck_time_s": computed_planck["planck_time"],
        },
        "cosmology_landmark": {
            "horizon_diameter_m": diameter,
            "age_s": age,
            "H0_per_s": hubble_si,
            "critical_density_kg_per_m3": rho_critical,
            "flat_horizon_volume_m3": flat_horizon_volume,
            **mass_equivalents,
            **anchor_spans,
            "uncertainty_status": "not_propagated_without_full_covariance",
        },
        "catalogue_rows": len(rows),
    }
    with JSON_OUTPUT.open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2, sort_keys=True)
        stream.write("\n")

    TEX_PLANCK.write_text(
        "\n".join(
            [
                r"{\small",
                r"\begin{longtable}{L{0.17\linewidth}L{0.25\linewidth}L{0.22\linewidth}L{0.20\linewidth}}",
                r"\toprule",
                r"Anchor & Definition & 2022 CODATA value & Status\\",
                r"\midrule",
                rf"Planck length $\ell_P$ & $\sqrt{{\hbar G/c^3}}$ & ${fmt_scientific(float(anchors['planck_length']['value_si']))}\,\mathrm{{m}}$ & normalization, not a proved minimum length\\",
                rf"Planck mass $m_P$ & $\sqrt{{\hbar c/G}}$ & ${fmt_scientific(float(anchors['planck_mass']['value_si']))}\,\mathrm{{kg}}$ & normalization, not a minimum mass\\",
                rf"Planck time $t_P$ & $\sqrt{{\hbar G/c^5}}$ & ${fmt_scientific(float(anchors['planck_time']['value_si']))}\,\mathrm{{s}}$ & normalization, not a proved minimum duration\\",
                r"\bottomrule",
                r"\end{longtable}",
                r"}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    cosmic_rows = [
        (
            "Present comoving particle-horizon diameter",
            diameter,
            "m",
            anchor_spans["length_legacy_span_decades"],
            "rounded 93 Gly landmark",
        ),
        (
            "FLRW cosmic age",
            age,
            "s",
            anchor_spans["time_age_span_decades"],
            r"Planck 2018 baseline, $13.797\pm0.023$ Gyr",
        ),
        (
            "Baryonic mass-equivalent",
            mass_equivalents["cosmic_baryonic_mass_equivalent"],
            "kg",
            anchor_spans["baryonic_mass_span_decades"],
            r"$\Omega_b\rho_{c0}V$",
        ),
        (
            "All-matter mass-equivalent",
            mass_equivalents["cosmic_matter_mass_equivalent"],
            "kg",
            anchor_spans["matter_mass_span_decades"],
            r"$\Omega_m\rho_{c0}V$",
        ),
        (
            "Total-energy mass-equivalent",
            mass_equivalents["cosmic_total_energy_mass_equivalent"],
            "kg",
            anchor_spans["total_energy_mass_span_decades"],
            r"$\rho_{c0}V$",
        ),
    ]
    cosmic_lines = [
        r"{\small",
        r"\begin{longtable}{L{0.25\linewidth}L{0.20\linewidth}L{0.11\linewidth}L{0.25\linewidth}}",
        r"\toprule",
        r"Landmark & Value in SI & Coordinate & Convention\\",
        r"\midrule",
    ]
    for label, value, unit, coordinate, convention in cosmic_rows:
        cosmic_lines.append(
            rf"{label} & ${fmt_scientific(value)}\,\mathrm{{{unit}}}$ & ${coordinate:.4f}$ & {convention}\\"
        )
    cosmic_lines.extend([r"\bottomrule", r"\end{longtable}", r"}", ""])
    TEX_COSMIC.write_text("\n".join(cosmic_lines), encoding="utf-8")

    selected_ids = {
        "planck_length",
        "atomic_order",
        "human_length_reference",
        "earth_diameter",
        "astronomical_unit",
        "observable_particle_horizon_diameter",
        "electron_mass",
        "proton_mass",
        "planck_mass",
        "human_mass_reference",
        "earth_mass",
        "solar_mass",
        "planck_time",
        "femtosecond",
        "second",
        "day",
        "Julian_year",
        "universe_age",
    }
    selected = [row for row in rows if row["id"] in selected_ids]
    catalogue_lines = [
        r"{\small",
        r"\begin{longtable}{L{0.21\linewidth}L{0.08\linewidth}L{0.20\linewidth}L{0.12\linewidth}L{0.21\linewidth}}",
        r"\toprule",
        r"Entry & Axis & SI value & Coordinate & Status\\",
        r"\midrule",
        r"\endhead",
    ]
    for row in selected:
        label = str(row["id"]).replace("_", " ")
        value = fmt_scientific(float(row["value_si"]), digits=5)
        unit = str(row["unit_si"]).replace("*", r"\,")
        coordinate = float(row["planck_log10_coordinate"])
        status = str(row["status"]).replace("_", " ")
        catalogue_lines.append(
            rf"{label} & {row['axis']} & ${value}\,\mathrm{{{unit}}}$ & ${coordinate:.3f}$ & {status}\\"
        )
    catalogue_lines.extend([r"\bottomrule", r"\end{longtable}", r"}", ""])
    TEX_CATALOGUE.write_text("\n".join(catalogue_lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "csv": str(CSV_OUTPUT),
                "json": str(JSON_OUTPUT),
                "rows": len(rows),
                "tex_tables": [
                    str(TEX_PLANCK),
                    str(TEX_COSMIC),
                    str(TEX_CATALOGUE),
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
