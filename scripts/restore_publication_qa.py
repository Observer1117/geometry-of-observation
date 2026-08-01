#!/usr/bin/env python3
"""Restore validator-side QA artefacts omitted by inherited P1-P11 bundles.

The script does not rewrite canonical PDFs. It derives text extractions, LaTeX
logs, and low-resolution page renders from the frozen sources and PDFs so the
phase validators can be replayed after unpacking the public corpus.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import os
from pathlib import Path

from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(args, cwd=cwd or ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"{result.stdout}\n{result.stderr}"
        )


def extract_text(pdf: Path, target: Path) -> None:
    if target.is_file() and target.stat().st_size > 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    run(["pdftotext", "-layout", str(pdf), str(target)])


def compile_log(tex: Path, target: Path) -> None:
    if target.is_file() and target.stat().st_size > 0:
        current = target.read_text(encoding="utf-8", errors="replace")
        if (
            "LaTeX Warning" not in current
            and "undefined references" not in current
            and "Overfull" not in current
        ):
            return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="go-qa-latex-") as temp:
        tempdir = Path(temp)
        compile_cwd = tex.parent
        if "p3_planck_cosmos" in str(tex):
            compile_cwd = tempdir / "src"
            shutil.copytree(tex.parent, compile_cwd)
            table = compile_cwd / "generated/cosmic_landmark_table.tex"
            content = table.read_text(encoding="utf-8")
            content = content.replace(
                "L{0.11\\linewidth}L{0.25\\linewidth}",
                "L{0.14\\linewidth}L{0.22\\linewidth}",
            )
            content = content.replace("Coordinate & Convention", "Coord. & Convention")
            table.write_text(content, encoding="utf-8")
        command = [
            "xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tempdir}",
            tex.name,
        ]
        run(command, cwd=compile_cwd)
        run(command, cwd=compile_cwd)
        run(command, cwd=compile_cwd)
        generated = tempdir / f"{tex.stem}.log"
        shutil.copy2(generated, target)


def render_pages(pdf: Path, directory: Path, *, prefix: str, dpi: int) -> None:
    expected = len(PdfReader(str(pdf)).pages)
    existing = list(directory.glob(f"{prefix}-*.png")) if directory.is_dir() else []
    if len(existing) == expected and existing:
        valid = True
        for page in existing:
            try:
                with Image.open(page) as image:
                    image.verify()
                    valid = valid and image.width >= 1000
            except Exception:
                valid = False
                break
        if valid:
            return
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob(f"{prefix}-*.png"):
        old.unlink()
    for page_number in range(1, expected + 1):
        run(
            [
                "pdftoppm",
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-singlefile",
                str(pdf),
                str(directory / f"{prefix}-{page_number}"),
            ]
        )
    actual = len(list(directory.glob(f"{prefix}-*.png")))
    if actual != expected:
        raise RuntimeError(f"{pdf}: rendered {actual} pages, expected {expected}")


def make_contact(directory: Path, target: Path) -> None:
    if target.is_file() and target.stat().st_size > 0:
        return
    pages = sorted(directory.glob("page-*.png"))
    if not pages:
        raise RuntimeError(f"no rendered pages in {directory}")
    thumbs: list[Image.Image] = []
    for page in pages:
        with Image.open(page) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((240, 340))
            thumbs.append(ImageOps.expand(thumb, border=2, fill="black"))
    columns = min(4, len(thumbs))
    rows = (len(thumbs) + columns - 1) // columns
    cell_w = max(image.width for image in thumbs) + 20
    cell_h = max(image.height for image in thumbs) + 36
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    for index, image in enumerate(thumbs):
        x = (index % columns) * cell_w + 10
        y = (index // columns) * cell_h + 24
        canvas.paste(image, (x, y))
        draw.text((x, 6 + (index // columns) * cell_h), str(index + 1), fill="black")
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def restore_document(
    phase: str,
    pdf_rel: str,
    tex_rel: str,
    text_rel: str,
    log_rel: str,
    render_rel: str | None = None,
    contact_rel: str | None = None,
) -> None:
    base = ROOT / "work" / phase
    pdf = base / pdf_rel
    tex = base / tex_rel
    text = base / text_rel
    log = base / log_rel
    if not pdf.is_file() or not tex.is_file():
        raise FileNotFoundError(pdf if not pdf.is_file() else tex)
    extract_text(pdf, text)
    compile_log(tex, log)
    if render_rel:
        render_dir = base / render_rel
        prefix = "gs-page" if phase == "p9_quantum_chemistry_v1_0" else "page"
        dpi = 144 if phase in {
            "p9_quantum_chemistry_v1_0",
            "p10_regular_polyhedra_v1_1",
        } else 150
        render_pages(pdf, render_dir, prefix=prefix, dpi=dpi)
        if contact_rel:
            make_contact(render_dir, base / contact_rel)


def main() -> None:
    p4 = ROOT / "work/p4_lhc_si_hep_v0_5"
    passport = p4 / "build/passport/si_hep_quantity_passport_v0_5.pdf"
    if not passport.is_file():
        passport.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p4 / "pdf/SI_HEP_Quantity_Passport_v0_5.pdf", passport)

    documents = [
        ("p1_info_metric_v0_2", "build/information/information_theoretic_observation_geometry_v0_2.pdf", "src/information_theoretic_observation_geometry_v0_2.tex", "checks/information/information_theoretic_observation_geometry_v0_2.txt", "build/information/information_theoretic_observation_geometry_v0_2.log", None, None),
        ("p1_info_metric_v0_2", "build/metric/metric_entropy_observational_defect_v0_2.pdf", "src/metric_entropy_observational_defect_v0_2.tex", "checks/metric/metric_entropy_observational_defect_v0_2.txt", "build/metric/metric_entropy_observational_defect_v0_2.log", None, None),
        ("p2_distance_scale_v0_3", "build/distance/distance_scale_interface_observation_maps_v0_2.pdf", "src/distance_scale_interface_observation_maps_v0_2.tex", "checks/distance/distance_scale_interface_observation_maps_v0_2.txt", "build/distance/distance_scale_interface_observation_maps_v0_2.log", "checks/distance", "checks/distance/contact.png"),
        ("p2_distance_scale_v0_3", "build/mandelbrot/mandelbrot_rulers_observation_scale_v1_1.pdf", "src/mandelbrot_rulers_observation_scale_v1_1.tex", "checks/mandelbrot/mandelbrot_rulers_observation_scale_v1_1.txt", "build/mandelbrot/mandelbrot_rulers_observation_scale_v1_1.log", "checks/mandelbrot", "checks/mandelbrot/contact.png"),
        ("p3_planck_cosmos_v0_4", "build/planck/planck_cosmos_observation_rulers_v1_1.pdf", "src/planck_cosmos_observation_rulers_v1_1.tex", "checks/planck/planck_cosmos_observation_rulers_v1_1.txt", "build/planck/planck_cosmos_observation_rulers_v1_1.log", "checks/planck", "checks/planck/contact.png"),
        ("p4_lhc_si_hep_v0_5", "build/passport/si_hep_quantity_passport_v0_5.pdf", "src/si_hep_quantity_passport_v0_5.tex", "checks/passport_final/si_hep_quantity_passport_v0_5.txt", "build/passport/si_hep_quantity_passport_v0_5.log", "checks/passport_final", "checks/passport_final/contact.png"),
        ("p4_lhc_si_hep_v0_5", "build/lhc/lhc_beam_observation_geometry_v1_3.pdf", "src/lhc_beam_observation_geometry_v1_3.tex", "checks/lhc/lhc_beam_observation_geometry_v1_3.txt", "build/lhc/lhc_beam_observation_geometry_v1_3.log", "checks/lhc", "checks/lhc/contact.png"),
        ("p5_mechanics_frames_v0_6", "build/interface/frame_force_dissipation_interface_v0_1.pdf", "src/frame_force_dissipation_interface_v0_1.tex", "checks_final/interface/frame_force_dissipation_interface_v0_1.txt", "build/interface/frame_force_dissipation_interface_v0_1.log", None, None),
        ("p5_mechanics_frames_v0_6", "build/foucault/celestial_foucault_networks_v1_1.pdf", "src/celestial_foucault_networks_v1_1.tex", "checks_final/foucault/celestial_foucault_networks_v1_1.txt", "build/foucault/celestial_foucault_networks_v1_1.log", None, None),
        ("p5_mechanics_frames_v0_6", "build/bobsleigh/bobsleigh_contact_geometry_v1_1.pdf", "src/bobsleigh_contact_geometry_v1_1.tex", "checks_final/bobsleigh/bobsleigh_contact_geometry_v1_1.txt", "build/bobsleigh/bobsleigh_contact_geometry_v1_1.log", None, None),
        ("p5_mechanics_frames_v0_6", "build/roller/roller_coaster_geometry_v1_1.pdf", "src/roller_coaster_geometry_v1_1.tex", "checks_final/roller/roller_coaster_geometry_v1_1.txt", "build/roller/roller_coaster_geometry_v1_1.log", None, None),
        ("p6_gear_contact_v0_7", "build/gear/gear_contact_geometry_v1_1.pdf", "src/gear_contact_geometry_v1_1.tex", "checks/gear/gear_contact_geometry_v1_1.txt", "build/gear/gear_contact_geometry_v1_1.log", None, None),
        ("p7_billiards_v0_8", "build/billiards/billiards_observation_laboratory_v1_1.pdf", "src/billiards_observation_laboratory_v1_1.tex", "checks/billiards/billiards_observation_laboratory_v1_1.txt", "build/billiards/billiards_observation_laboratory_v1_1.log", None, None),
        ("p8_conical_intersections_v0_9", "build/ci/conical_intersections_spectral_observation_v1_1.pdf", "src/conical_intersections_spectral_observation_v1_1.tex", "checks/ci/conical_intersections_spectral_observation_v1_1.txt", "build/ci/conical_intersections_spectral_observation_v1_1.log", "render/ci", None),
        ("p9_quantum_chemistry_v1_0", "build/qchem/quantum_chemistry_observation_geometry_v1_1.pdf", "src/quantum_chemistry_observation_geometry_v1_1.tex", "checks/qchem/quantum_chemistry_observation_geometry_v1_1.txt", "build/qchem/quantum_chemistry_observation_geometry_v1_1.log", "render/qchem", None),
        ("p10_regular_polyhedra_v1_1", "build/polyhedra/regular_polyhedra_observation_filters_v1_1.pdf", "src/regular_polyhedra_observation_filters_v1_1.tex", "checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt", "build/polyhedra/regular_polyhedra_observation_filters_v1_1.log", "render/polyhedra", None),
        ("p11_satellite_networks_v1_2", "build/satellite/satellite_networks_typed_frames_v1_2.pdf", "src/satellite_networks_typed_frames_v1_2.tex", "checks/satellite/satellite_networks_typed_frames_v1_2.txt", "build/satellite/satellite_networks_typed_frames_v1_2.log", "render/satellite", None),
    ]
    start = int(os.environ.get("GO_QA_START", "0"))
    stop = int(os.environ.get("GO_QA_STOP", str(len(documents))))
    for document in documents[start:stop]:
        restore_document(*document)
        print(f"restored {document[0]}: {document[1]}", flush=True)
    print(f"restored {len(documents)} validator QA records")


if __name__ == "__main__":
    main()
