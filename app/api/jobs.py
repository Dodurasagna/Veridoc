from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import CertificateRecord, GenerationJob
from app.schemas import JobCreate, JobCreatedResponse, RecipientInput
from app.services.job_processor import process_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/", response_model=JobCreatedResponse, status_code=202)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks,
               session: Session = Depends(get_session)):
    if payload.issue_date > date.today():
        raise HTTPException(status_code=422, detail="issue_date cannot be in the future")

    errors = []
    valid = []
    for index, raw in enumerate(payload.recipients):
        try:
            valid.append((index, RecipientInput.model_validate(raw)))
        except ValidationError as exc:
            errors.append({"index": index, "reason": exc.errors()[0]["msg"]})

    job = GenerationJob(
        course_name=payload.course_name, organization=payload.organization,
        issue_date=payload.issue_date, status="PENDING", total_submitted=len(payload.recipients),
        valid_count=len(valid), invalid_count=len(errors), validation_errors=errors,
    )
    session.add(job)
    session.flush()
    for index, recipient in valid:
        session.add(CertificateRecord(job_id=job.id, recipient_index=index,
                                      recipient_name=recipient.name, recipient_email=recipient.email))
    session.commit()
    session.refresh(job)
    if valid:
        background_tasks.add_task(process_job, job.id)
    else:
        job.status = "COMPLETED_WITH_ERRORS"
        from app.models import utc_now
        job.completed_at = utc_now()
        session.commit()
    return JobCreatedResponse(job_id=job.id, status=job.status,
                              total_submitted=job.total_submitted, valid_count=job.valid_count,
                              invalid_count=job.invalid_count, validation_errors=errors)


@router.get("/{job_id}")
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    pending = max(job.valid_count - job.successful_count - job.failed_count, 0)
    processed = job.successful_count + job.failed_count
    progress = round(processed / job.valid_count * 100, 2) if job.valid_count else 100.0
    return {"job_id": job.id, "status": job.status, "total_submitted": job.total_submitted,
            "valid_count": job.valid_count, "invalid_count": job.invalid_count,
            "successful_count": job.successful_count, "failed_count": job.failed_count,
            "pending_count": pending, "progress_percentage": progress,
            "created_at": job.created_at, "completed_at": job.completed_at,
            "validation_errors": job.validation_errors}


@router.get("/{job_id}/certificates")
def list_certificates(job_id: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                      session: Session = Depends(get_session)):
    if session.get(GenerationJob, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    records = session.scalars(select(CertificateRecord).where(CertificateRecord.job_id == job_id)
                              .order_by(CertificateRecord.recipient_index).limit(limit).offset(offset)).all()
    return {"job_id": job_id, "limit": limit, "offset": offset,
            "certificates": [{"certificate_id": r.id, "recipient_index": r.recipient_index,
                              "recipient_name": r.recipient_name, "recipient_email": r.recipient_email,
                              "status": r.status, "verification_id": r.verification_id,
                              "error_message": r.error_message,
                              "download_url": f"/api/certificates/{r.id}" if r.status == "COMPLETED" else None}
                             for r in records]}
