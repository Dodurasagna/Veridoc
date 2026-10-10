import logging
import os
import secrets
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import CertificateRecord, GenerationJob, utc_now
from app.services.certificate_generator import generate_certificate

logger = logging.getLogger(__name__)


def process_job(job_id: str) -> None:
    """Process persisted pending recipients; each PDF failure is isolated."""
    output_dir = Path(os.getenv("CERTIFICATE_OUTPUT_DIR", "generated_certificates"))
    with SessionLocal() as session:
        job = session.get(GenerationJob, job_id)
        if job is None:
            logger.error("Cannot process missing job %s", job_id)
            return
        job.status = "PROCESSING"
        session.commit()
        records = session.scalars(select(CertificateRecord).where(
            CertificateRecord.job_id == job_id,
            CertificateRecord.status == "PENDING",
        ).order_by(CertificateRecord.recipient_index)).all()
        for record in records:
            verification_id = secrets.token_urlsafe(24)
            try:
                path = generate_certificate(
                    output_dir=output_dir, certificate_id=record.id,
                    recipient_name=record.recipient_name, course_name=job.course_name,
                    organization=job.organization, issue_date=job.issue_date.isoformat(),
                    verification_id=verification_id,
                )
                record.status = "COMPLETED"
                record.verification_id = verification_id
                record.pdf_path = str(path)
                record.error_message = None
            except Exception:
                logger.exception("Certificate generation failed for record %s", record.id)
                record.status = "FAILED"
                record.error_message = "PDF generation failed. Please retry this certificate."
            session.commit()
            # Keep progress visible while the rest of the batch is still processing.
            statuses = session.scalars(select(CertificateRecord.status).where(
                CertificateRecord.job_id == job_id
            )).all()
            job.successful_count = statuses.count("COMPLETED")
            job.failed_count = statuses.count("FAILED")
            session.commit()

        job = session.get(GenerationJob, job_id)
        all_records = session.scalars(select(CertificateRecord).where(CertificateRecord.job_id == job_id)).all()
        job.successful_count = sum(item.status == "COMPLETED" for item in all_records)
        job.failed_count = sum(item.status == "FAILED" for item in all_records)
        pending_count = sum(item.status == "PENDING" for item in all_records)
        if pending_count:
            job.status = "PROCESSING"
        else:
            job.completed_at = utc_now()
            if job.failed_count and not job.successful_count and job.valid_count:
                job.status = "FAILED"
            elif job.failed_count or job.invalid_count:
                job.status = "COMPLETED_WITH_ERRORS"
            else:
                job.status = "COMPLETED"
        session.commit()
