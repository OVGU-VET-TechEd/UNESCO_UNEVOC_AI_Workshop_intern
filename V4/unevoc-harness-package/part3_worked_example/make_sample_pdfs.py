#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_sample_pdfs.py — create the three input PDFs for the Part 3 demos.

Run this once, before either demo:

    python make_sample_pdfs.py

It writes three short PDFs into ./input_pdfs/ . Each one contains prose, a small
data table, and one figure with a caption — so the ingestion step has something
of each kind to handle, including a figure it must NOT try to read.

The content is invented for teaching purposes. It is not real safety data.
Replace ./input_pdfs/ with your own documents when you run this for real; both
demos simply read whatever PDFs are in that folder.
"""

from __future__ import annotations

import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "input_pdfs")

SITES = [
    {
        "file": "site_a_workshop_report.pdf",
        "title": "Site A — Metal Workshop: Annual Safety and Training Report",
        "intro": (
            "Site A operates a metal workshop used by first- and second-year apprentices "
            "in machining and welding. This report covers the four quarters of the "
            "reporting year and summarises recorded incidents, delivered training hours "
            "and the outcome of the annual equipment inspection."
        ),
        "body": (
            "Incident recording follows the workshop's standing procedure: every event "
            "requiring first aid or causing an interruption of more than fifteen minutes "
            "is logged, whether or not an injury resulted. Training hours count only "
            "supervised practical instruction; theory hours are recorded separately and "
            "are not included here. The rise in training hours in the third quarter "
            "reflects the introduction of the revised hot-work induction."
        ),
        "rows": [["Quarter", "Incidents", "Training hours"],
                 ["Q1", "7", "120"], ["Q2", "5", "140"],
                 ["Q3", "3", "210"], ["Q4", "2", "195"]],
        "caption": "Figure 1: Layout of the welding bays and extraction points.",
        "closing": (
            "The annual inspection recorded two non-conformities, both relating to "
            "extraction airflow in bays three and four. Both were closed before the end "
            "of the year. No equipment was withdrawn from service."
        ),
    },
    {
        "file": "site_b_hydraulics_report.pdf",
        "title": "Site B — Hydraulics Laboratory: Annual Safety and Training Report",
        "intro": (
            "Site B houses the hydraulics laboratory used for pressure-system training. "
            "Because the laboratory works at higher stored energies than the general "
            "workshop, its induction is longer and its incident threshold is lower."
        ),
        "body": (
            "Two of the incidents recorded in the first quarter involved hose failures on "
            "the older test rig, which has since been replaced. The remaining incidents "
            "were minor fluid contact events with no injury. Training hours include the "
            "mandatory eight-hour pressure-system induction taken by every new learner "
            "before any independent work is permitted."
        ),
        "rows": [["Quarter", "Incidents", "Training hours"],
                 ["Q1", "9", "160"], ["Q2", "6", "155"],
                 ["Q3", "4", "180"], ["Q4", "4", "175"]],
        "caption": "Figure 1: Pressure test rig, isolation valve positions.",
        "closing": (
            "The replacement of the older test rig in the second quarter is the most "
            "likely explanation for the reduction in the second half of the year, but no "
            "controlled comparison was performed and this should be read as an "
            "observation rather than a finding."
        ),
    },
    {
        "file": "site_c_electrical_report.pdf",
        "title": "Site C — Electrical Training Centre: Annual Safety and Training Report",
        "intro": (
            "Site C delivers electrical installation training, including circuit diagram "
            "interpretation, testing and fault finding. Learners work on de-energised "
            "training boards for the first two terms."
        ),
        "body": (
            "The centre records a low incident count throughout the year, consistent with "
            "the de-energised training model. The single third-quarter incident involved a "
            "hand tool rather than an electrical hazard. Training hours dipped in the "
            "fourth quarter because of the examination period, not because of reduced "
            "provision."
        ),
        "rows": [["Quarter", "Incidents", "Training hours"],
                 ["Q1", "2", "180"], ["Q2", "1", "185"],
                 ["Q3", "1", "190"], ["Q4", "0", "130"]],
        "caption": "Figure 1: Training board wiring schematic, bench 12.",
        "closing": (
            "No non-conformities were recorded at the annual inspection. The centre "
            "recommends that the fourth-quarter dip in training hours be smoothed in the "
            "next timetable revision."
        ),
    },
]


def _placeholder_figure() -> bytes:
    """Draw a small schematic-looking PNG so each PDF contains a real image.

    The demos must NOT read numbers out of this image. That is the point: it is a
    figure, and the ingestion step notes it by caption instead of guessing.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=(4.2, 1.9), dpi=130)
    axes.plot([0, 1, 1, 2, 2, 3], [0, 0, 1, 1, 0, 0], linewidth=2)
    axes.plot([0.5, 0.5], [0, 1.2], linewidth=1, linestyle="--")
    axes.scatter([1, 2], [1, 1], s=40)
    axes.set_xticks([]); axes.set_yticks([])
    axes.set_xlim(-0.2, 3.2); axes.set_ylim(-0.4, 1.6)
    for side in ("top", "right", "left", "bottom"):
        axes.spines[side].set_visible(False)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def build_pdf(spec: dict, figure_png: bytes) -> str:
    styles = getSampleStyleSheet()
    path = os.path.join(OUT_DIR, spec["file"])
    document = SimpleDocTemplate(path, pagesize=A4,
                                 leftMargin=22 * mm, rightMargin=22 * mm,
                                 topMargin=20 * mm, bottomMargin=20 * mm,
                                 title=spec["title"])
    story = [
        Paragraph(spec["title"], styles["Title"]),
        Spacer(1, 6),
        Paragraph(spec["intro"], styles["BodyText"]),
        Spacer(1, 6),
        Paragraph("Recorded figures", styles["Heading2"]),
    ]

    table = Table(spec["rows"], hAlign="LEFT", colWidths=[70, 70, 90])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff4f8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#101d29")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7d3dc")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 10),
              Paragraph("Commentary", styles["Heading2"]),
              Paragraph(spec["body"], styles["BodyText"]),
              Spacer(1, 10)]

    story.append(Image(io.BytesIO(figure_png), width=110 * mm, height=50 * mm))
    story.append(Paragraph(f"<i>{spec['caption']}</i>", styles["BodyText"]))
    story += [Spacer(1, 10),
              Paragraph("Inspection outcome", styles["Heading2"]),
              Paragraph(spec["closing"], styles["BodyText"])]

    document.build(story)
    return path


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    figure_png = _placeholder_figure()
    for spec in SITES:
        path = build_pdf(spec, figure_png)
        print(f"wrote {path}  ({os.path.getsize(path)} bytes)")
    print(f"\n{len(SITES)} PDFs are in {OUT_DIR}")
    print("Next:  python semi_agent.py --model <your-model>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
