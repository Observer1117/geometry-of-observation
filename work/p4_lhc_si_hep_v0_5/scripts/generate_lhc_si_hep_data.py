#!/usr/bin/env python3
"""Generate exact-definition conversion rows and the LHC numerical audit."""

from __future__ import annotations

import csv
import json
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

import yaml


getcontext().prec = 70

ROOT = Path(__file__).resolve().parents[3]
P4 = ROOT / "work/p4_lhc_si_hep_v0_5"
INPUT = P4 / "data/lhc_si_hep_inputs_v0_5.yaml"
CONVERSIONS_CSV = P4 / "data/si_hep_conversion_table_v0_5.csv"
METRICS_JSON = P4 / "data/lhc_si_hep_metrics_v0_5.json"
GENERATED = P4 / "src/generated"

PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816"
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root must be a mapping")
    return value


def sci(value: Decimal, digits: int = 12) -> str:
    if value.is_zero():
        return "0"
    return f"{value:.{digits}E}".replace("E+", "e").replace("E", "e")


def fixed(value: Decimal, places: int) -> str:
    return f"{value:.{places}f}"


def latex_number(value: str) -> str:
    if "e" not in value:
        return value
    mantissa, exponent = value.split("e", 1)
    return rf"{mantissa}\times 10^{{{int(exponent)}}}"


def mechanical_scale(
    *,
    a_length: int,
    b_mass: int,
    t_time: int,
    hbar: Decimal,
    c: Decimal,
    energy_anchor_joule: Decimal,
) -> tuple[int, int, int, Decimal]:
    """Return d_E, hbar exponent, c exponent, and one natural unit in SI."""

    d_energy = b_mass - a_length - t_time
    hbar_exponent = a_length + t_time
    c_exponent = a_length - 2 * b_mass
    scale = (
        (hbar**hbar_exponent)
        * (c**c_exponent)
        * (energy_anchor_joule**d_energy)
    )
    return d_energy, hbar_exponent, c_exponent, scale


def conversion_rows(
    hbar: Decimal, c: Decimal, gev_joule: Decimal
) -> list[dict[str, str]]:
    definitions = [
        ("energy", 2, 1, -2, "1 GeV", "J"),
        ("mass", 0, 1, 0, "1 GeV/c^2", "kg"),
        ("momentum", 1, 1, -1, "1 GeV/c", "kg m s^-1"),
        ("length", 1, 0, 0, "1 GeV^-1", "m"),
        ("duration", 0, 0, 1, "1 GeV^-1", "s"),
        ("area", 2, 0, 0, "1 GeV^-2", "m^2"),
        ("action", 2, 1, -1, "1", "J s"),
        ("force", 1, 1, -2, "1 GeV^2", "N"),
    ]
    rows: list[dict[str, str]] = []
    for quantity, a_length, b_mass, t_time, hep_unit, si_unit in definitions:
        d_energy, u_hbar, v_c, scale = mechanical_scale(
            a_length=a_length,
            b_mass=b_mass,
            t_time=t_time,
            hbar=hbar,
            c=c,
            energy_anchor_joule=gev_joule,
        )
        rows.append(
            {
                "quantity": quantity,
                "si_dimension_L": str(a_length),
                "si_dimension_M": str(b_mass),
                "si_dimension_T": str(t_time),
                "hep_energy_dimension": str(d_energy),
                "hbar_exponent": str(u_hbar),
                "c_exponent": str(v_c),
                "hep_unit": hep_unit,
                "si_value": sci(scale, 14),
                "si_unit": si_unit,
                "exactness": "exact definition; displayed decimal rounded",
            }
        )
    return rows


def write_conversion_tex(rows: list[dict[str, str]]) -> None:
    selected = [
        next(row for row in rows if row["quantity"] == name)
        for name in ("energy", "mass", "momentum", "length", "duration", "area")
    ]
    labels = {
        "energy": "energy",
        "mass": "mass",
        "momentum": "momentum",
        "length": "length",
        "duration": "duration",
        "area": "area / cross section",
    }
    hep_units = {
        "energy": r"\mathrm{GeV}",
        "mass": r"\mathrm{GeV}/c^2",
        "momentum": r"\mathrm{GeV}/c",
        "length": r"\mathrm{GeV}^{-1}",
        "duration": r"\mathrm{GeV}^{-1}",
        "area": r"\mathrm{GeV}^{-2}",
    }
    si_units = {
        "energy": r"\mathrm{J}",
        "mass": r"\mathrm{kg}",
        "momentum": r"\mathrm{kg\,m\,s^{-1}}",
        "length": r"\mathrm{m}",
        "duration": r"\mathrm{s}",
        "area": r"\mathrm{m^2}",
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{@{}L{31mm}L{29mm}L{43mm}Y@{}}",
        r"\toprule",
        r"Quantity & HEP unit & SI representative & Exactness \\",
        r"\midrule",
    ]
    for row in selected:
        quantity = row["quantity"]
        si_value = latex_number(row["si_value"])
        lines.append(
            rf"{labels[quantity]} & \({hep_units[quantity]}\) & "
            rf"\({si_value}\ {si_units[quantity]}\) & "
            r"definition-exact; decimal rounded \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    (GENERATED / "conversion_table.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_lhc_audit_tex(metrics: dict[str, Any]) -> None:
    audit = metrics["lhc_run3_audit"]
    rows = [
        ("Reference proton total energy", audit["energy_GeV"], r"\mathrm{GeV}", "operational reference"),
        ("Proton mass energy", audit["proton_mass_energy_GeV"], r"\mathrm{GeV}", "CODATA 2022"),
        (r"Lorentz factor \(\gamma\)", audit["gamma"], "", "derived"),
        (r"Speed ratio \(\beta\)", audit["beta"], "", "derived"),
        (r"Stable \(1-\beta\)", audit["one_minus_beta"], "", "derived"),
        (r"Speed deficit \(c-v\)", audit["speed_deficit_m_per_s"], r"\mathrm{m\,s^{-1}}", "derived"),
        ("Momentum", audit["momentum_GeV_per_c"], r"\mathrm{GeV}/c", "derived"),
        (r"Magnetic rigidity \(B\rho\)", audit["magnetic_rigidity_T_m"], r"\mathrm{T\,m}", "derived"),
        ("Revolution frequency", audit["revolution_frequency_Hz"], r"\mathrm{Hz}", "rounded circumference"),
        (r"Symmetric head-on \(\sqrt{s}\)", audit["sqrt_s_GeV"], r"\mathrm{GeV}", "derived"),
    ]
    lines = [
        r"\begin{tabularx}{\linewidth}{@{}Y L{40mm} L{31mm}@{}}",
        r"\toprule",
        r"Quantity & Value & Status \\",
        r"\midrule",
    ]
    for label, value, unit, status in rows:
        value_tex = latex_number(value)
        suffix = rf"\,{unit}" if unit else ""
        lines.append(rf"{label} & \({value_tex}{suffix}\) & {status} \\")
    lines.extend([r"\bottomrule", r"\end{tabularx}"])
    (GENERATED / "lhc_audit_table.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    data = load_yaml(INPUT)
    constants = data["defining_constants"]
    c = Decimal(constants["speed_of_light"]["value_si"])
    h = Decimal(constants["planck_constant"]["value_si"])
    e = Decimal(constants["elementary_charge"]["value_si"])
    gev_joule = Decimal(constants["gigaelectronvolt"]["value_si"])
    hbar = h / (Decimal(2) * PI)

    rows = conversion_rows(hbar, c, gev_joule)
    CONVERSIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CONVERSIONS_CSV.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    reference = data["lhc_reference"]
    measured = data["measured_constants"]
    energy_gev = Decimal(reference["proton_total_energy"]["value"])
    mass_energy_gev = Decimal(measured["proton_mass_energy"]["value"])
    gamma = energy_gev / mass_energy_gev
    beta = (Decimal(1) - Decimal(1) / gamma**2).sqrt()
    one_minus_beta = (Decimal(1) / gamma**2) / (Decimal(1) + beta)
    momentum_gev_per_c = beta * energy_gev
    rigidity_coefficient = c / Decimal("1e9")
    charge_state = Decimal(reference["charge_state"]["value"])
    magnetic_rigidity = momentum_gev_per_c / (
        rigidity_coefficient * charge_state
    )
    circumference = Decimal(reference["circumference"]["value"])
    revolution_frequency = beta * c / circumference
    energy_joule = energy_gev * gev_joule
    sqrt_s_gev = Decimal(2) * energy_gev

    hbar_c = hbar * c
    gev_inverse_length_m = hbar_c / gev_joule
    gev_inverse_time_s = hbar / gev_joule
    gev_mass_kg = gev_joule / c**2
    gev_momentum_si = gev_joule / c
    gev_minus_two_m2 = gev_inverse_length_m**2
    mbarn_m2 = Decimal("1e-31")
    gev_minus_two_mbarn = gev_minus_two_m2 / mbarn_m2
    angular_frequency_per_gev = gev_joule / hbar
    ordinary_frequency_per_gev = gev_joule / h

    bunches = Decimal(reference["bunches_per_beam"]["value"])
    protons_per_bunch = Decimal(reference["protons_per_bunch"]["value"])
    bunch_energy_joule = energy_joule * protons_per_bunch
    approximate_beam_energy_joule = bunch_energy_joule * bunches

    metrics: dict[str, Any] = {
        "schema": {
            "id": "go-lhc-si-hep-metrics",
            "version": "0.5.0",
            "date": "2026-07-28",
        },
        "defining_constants": {
            "c_m_per_s": fixed(c, 0),
            "h_J_s": sci(h, 8),
            "hbar_J_s": sci(hbar, 16),
            "e_C": sci(e, 9),
            "GeV_J": sci(gev_joule, 9),
            "rigidity_coefficient": fixed(rigidity_coefficient, 9),
        },
        "standard_conversions": {
            "one_GeV_inverse_length_m": sci(gev_inverse_length_m, 15),
            "one_GeV_inverse_length_fm": fixed(
                gev_inverse_length_m / Decimal("1e-15"), 12
            ),
            "one_GeV_inverse_time_s": sci(gev_inverse_time_s, 15),
            "one_GeV_per_c2_kg": sci(gev_mass_kg, 15),
            "one_GeV_per_c_kg_m_per_s": sci(gev_momentum_si, 15),
            "one_GeV_minus2_m2": sci(gev_minus_two_m2, 15),
            "one_GeV_minus2_mbarn": fixed(gev_minus_two_mbarn, 12),
            "hbar_c_MeV_fm": fixed(
                hbar_c
                / (Decimal("1e6") * e)
                / Decimal("1e-15"),
                12,
            ),
            "angular_frequency_per_GeV_rad_per_s": sci(
                angular_frequency_per_gev, 15
            ),
            "ordinary_frequency_per_GeV_Hz": sci(
                ordinary_frequency_per_gev, 15
            ),
        },
        "lhc_run3_audit": {
            "epoch": reference["epoch"],
            "status_at_document_date": reference["current_status_at_document_date"],
            "energy_GeV": fixed(energy_gev, 0),
            "energy_J_per_proton": sci(energy_joule, 12),
            "proton_mass_energy_GeV": fixed(mass_energy_gev, 11),
            "gamma": sci(gamma, 11),
            "beta": fixed(beta, 14),
            "one_minus_beta": sci(one_minus_beta, 12),
            "speed_deficit_m_per_s": fixed(c * one_minus_beta, 9),
            "momentum_GeV_per_c": fixed(momentum_gev_per_c, 9),
            "magnetic_rigidity_T_m": fixed(magnetic_rigidity, 6),
            "revolution_frequency_Hz": fixed(revolution_frequency, 6),
            "turns_per_second_public_reference": "11245",
            "sqrt_s_GeV": fixed(sqrt_s_gev, 0),
            "approximate_bunch_energy_J": sci(bunch_energy_joule, 10),
            "approximate_beam_energy_J": sci(approximate_beam_energy_joule, 10),
            "mass_shell_relative_residual": sci(
                abs(
                    energy_gev**2
                    - momentum_gev_per_c**2
                    - mass_energy_gev**2
                )
                / energy_gev**2,
                8,
            ),
        },
        "exactness": {
            "definition_exact": [
                "c",
                "h",
                "e",
                "eV_to_J",
                "GeV_to_J",
                "rigidity_coefficient_for_declared_units",
            ],
            "measured": ["proton_mass_energy"],
            "operational_or_rounded": [
                "beam_energy",
                "circumference",
                "bunches_per_beam",
                "protons_per_bunch",
            ],
        },
    }
    METRICS_JSON.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    GENERATED.mkdir(parents=True, exist_ok=True)
    write_conversion_tex(rows)
    write_lhc_audit_tex(metrics)

    print(CONVERSIONS_CSV)
    print(METRICS_JSON)
    print(GENERATED / "conversion_table.tex")
    print(GENERATED / "lhc_audit_table.tex")


if __name__ == "__main__":
    main()
