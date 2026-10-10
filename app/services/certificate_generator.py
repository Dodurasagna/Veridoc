import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas


def generate_certificate(*, output_dir: Path, certificate_id: str, recipient_name: str,
                         course_name: str, organization: str, issue_date: str,
                         verification_id: str) -> Path:
    """Create one PDF in the configured directory using only a generated filename."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target = (output_dir / f"{certificate_id}.pdf").resolve()
    if target.parent != output_dir.resolve():
        raise ValueError("Unsafe certificate output path")

    page_width, page_height = landscape(letter)
    pdf = canvas.Canvas(os.fspath(target), pagesize=(page_width, page_height))
    pdf.setTitle("Certificate of Achievement")
    pdf.setStrokeColor(colors.HexColor("#183B56"))
    pdf.setLineWidth(3)
    pdf.roundRect(28, 28, page_width - 56, page_height - 56, 14, stroke=1, fill=0)
    pdf.setStrokeColor(colors.HexColor("#D6A84F"))
    pdf.setLineWidth(1)
    pdf.roundRect(38, 38, page_width - 76, page_height - 76, 10, stroke=1, fill=0)

    pdf.setFillColor(colors.HexColor("#183B56"))
    pdf.setFont("Helvetica-Bold", 27)
    pdf.drawCentredString(page_width / 2, page_height - 115, "CERTIFICATE OF ACHIEVEMENT")
    pdf.setFillColor(colors.HexColor("#4A5560"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(page_width / 2, page_height - 160, "This certificate is proudly presented to")
    pdf.setFillColor(colors.HexColor("#183B56"))
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(page_width / 2, page_height - 205, recipient_name)
    pdf.setFillColor(colors.HexColor("#4A5560"))
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(page_width / 2, page_height - 245, f"for successfully completing {course_name}")
    pdf.drawCentredString(page_width / 2, page_height - 272, f"Issued by {organization} on {issue_date}")
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(page_width / 2, 65, f"Verification ID: {verification_id}")
    pdf.save()
    return target
