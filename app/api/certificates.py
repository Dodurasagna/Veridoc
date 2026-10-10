import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import CertificateRecord

router = APIRouter(tags=["certificates"])


@router.get("/api/certificates/{certificate_id}")
def download_certificate(certificate_id: str, session: Session = Depends(get_session)):
    record = session.get(CertificateRecord, certificate_id)
    if record is None or record.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="Certificate not found")
    output_dir = Path(os.getenv("CERTIFICATE_OUTPUT_DIR", "generated_certificates")).resolve()
    expected_path = (output_dir / f"{record.id}.pdf").resolve()
    path = Path(record.pdf_path or "").resolve()
    if path != expected_path or not path.is_file():
        raise HTTPException(status_code=410, detail="Generated certificate file is missing")
    return FileResponse(path, media_type="application/pdf", filename=f"certificate-{record.id}.pdf")


@router.get("/api/verify/{verification_id}")
def verify_certificate(verification_id: str, session: Session = Depends(get_session)):
    record = session.scalar(select(CertificateRecord).where(
        CertificateRecord.verification_id == verification_id,
        CertificateRecord.status == "COMPLETED",
    ))
    if record is None:
        return {"valid": False, "message": "Certificate could not be verified"}
    return {"valid": True, "certificate_id": record.id,
            "recipient_name": record.recipient_name,
            "course_name": record.job.course_name,
            "organization": record.job.organization,
            "issue_date": record.job.issue_date,
            "verification_id": record.verification_id}
