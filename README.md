# Veridoc

**A reliable bulk certificate generation and verification API.** Veridoc accepts one batch of recipients, reports invalid entries individually, generates personalized PDF certificates for valid entries, and exposes job progress, downloads, and public verification by random ID.

## Problem and features

Issuing certificates one at a time is repetitive and makes errors hard to track. Veridoc accepts up to 500 recipients per job and persists each outcome so one bad recipient or PDF failure does not erase other results.

Implemented features include FastAPI request validation, per-recipient validation reporting, SQLite persistence with SQLAlchemy, ReportLab PDF generation, background task processing, progress and paginated results, PDF retrieval, and unique verification IDs. This is a local assignment project, not a production deployment.

## Technology and architecture

Python 3.10+, FastAPI and Pydantic provide the HTTP API and input parsing. SQLAlchemy 2.x stores jobs and certificate records in SQLite. ReportLab creates the PDFs. Pytest and HTTPX exercise the API through FastAPI's test client. Uvicorn runs the server.

```text
app/
  api/          job, download, and verification routes
  services/     PDF rendering and job processing
  database.py   engine, session, and declarative base
  models.py     GenerationJob and CertificateRecord tables
  schemas.py    request and response validation
  main.py       app assembly and health endpoint
tests/          isolated API tests
generated_certificates/  local PDFs (ignored by Git)
```

`GenerationJob` has many `CertificateRecord` rows. A job stores batch-level details, counts, status, and validation errors. Each certificate row stores its recipient, individual status, optional PDF path and verification ID, and safe error text. The verification ID has a database uniqueness constraint.

## Request and processing flow

`POST /api/jobs/` validates job-level fields, then validates each recipient separately. Valid recipients and the job are committed before processing begins. FastAPI's in-process background task changes the job to `PROCESSING`, generates each PDF, and persists each result. Once processing ends, persisted results determine counts and the terminal status. Validation errors identify zero-based recipient indexes. Invalid recipients are represented in the job's validation error list; only valid recipients receive certificate records.

Statuses are `PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, and `FAILED`. A job with all valid certificates generated and no invalid input is `COMPLETED`. Any validation errors or mixed generation outcomes result in `COMPLETED_WITH_ERRORS`. If all valid certificate generations fail, status is `FAILED`. A batch containing no valid recipients completes with errors. Progress is generated valid recipients divided by valid recipients; a job with none is 100% processed.

FastAPI background tasks run in the API process. They are convenient for this local project but are not a durable queue: a process restart can interrupt work. For production, use a durable worker queue and recovery strategy.

## API

All dates use ISO format `YYYY-MM-DD`. The request accepts 1–500 recipient values; malformed individual entries are reported while valid entries continue.

### Create a job

`POST /api/jobs/` returns HTTP 202 with a job ID.

```json
{
  "course_name": "Python Backend Development",
  "organization": "AEREO Learning Program",
  "issue_date": "2026-10-10",
  "recipients": [
    {"name": "Ananya Sharma", "email": "ananya@example.com"},
    {"name": "", "email": "bad-email"}
  ]
}
```

Example response:

```json
{
  "job_id": "<uuid>", "status": "PENDING", "total_submitted": 2,
  "valid_count": 1, "invalid_count": 1,
  "validation_errors": [{"index": 1, "reason": "..."}]
}
```

### Status and results

- `GET /api/jobs/{job_id}` returns status, persisted counts, pending count, progress percentage, timestamps, and validation errors.
- `GET /api/jobs/{job_id}/certificates?limit=50&offset=0` lists recipient outcomes. `limit` is 1–200; the response includes download URLs only for completed certificates.
- `GET /api/certificates/{certificate_id}` returns the PDF (`application/pdf`). Missing files return HTTP 410; unknown or unsuccessful records return HTTP 404.
- `GET /api/verify/{verification_id}` returns `valid: true` with certificate details for a completed certificate, or `valid: false` for an unknown ID.
- `GET /health` returns `{"status":"ok"}`.

Invalid job-level fields receive HTTP 422. Unknown jobs receive HTTP 404. Verification deliberately returns a simple negative result for an unknown ID.

## Run locally (Windows PowerShell)

From the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The application creates the SQLite tables at startup. Defaults are `veridoc.db` and `generated_certificates\`; set `DATABASE_URL` or `CERTIFICATE_OUTPUT_DIR` to choose other paths. Open interactive API documentation at <http://127.0.0.1:8000/docs>.

Submit a batch and save its response:

```powershell
$body = @{ course_name = 'Python Backend Development'; organization = 'AEREO Learning Program'; issue_date = '2026-10-10'; recipients = @(@{ name = 'Ananya Sharma'; email = 'ananya@example.com' }) } | ConvertTo-Json -Depth 5
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/jobs/ -ContentType 'application/json' -Body $body
$jobId = $job.job_id
$status = Invoke-RestMethod "http://127.0.0.1:8000/api/jobs/$jobId"
$results = Invoke-RestMethod "http://127.0.0.1:8000/api/jobs/$jobId/certificates"
$certificate = $results.certificates[0]
Invoke-WebRequest "http://127.0.0.1:8000$($certificate.download_url)" -OutFile .\certificate.pdf
Invoke-RestMethod "http://127.0.0.1:8000/api/verify/$($certificate.verification_id)"
```

If the results endpoint is checked while processing is underway, poll the status endpoint until it is terminal. Background tasks are in-process, so a server restart can interrupt an active batch.

## Tests

Tests use a temporary SQLite database and temporary certificate directory, not the default local files.

```powershell
pytest -v
```

The suite covers creation, validation, status/progress, PDF response contents, isolated generation failure, download, unknown IDs, and verification.

## Design choices and limitations

SQLite keeps local setup simple; PostgreSQL would suit concurrent production workloads better. Local PDF files avoid an external storage dependency. Recipient validation is isolated so a single bad input does not reject a whole batch. Verification IDs use `secrets.token_urlsafe` and a uniqueness constraint. The PDF is a proof of issuance, not a digital signature: verification checks the database record and does not prevent screenshots or edits to a downloaded copy.

Current limitations: no authentication, authorization, rate limiting, revocation flow, durable queue, cloud storage, or production monitoring. The background task is in-process. PDF generation uses a single built-in template and local filesystem paths.

## Learning notes

The project demonstrates request models, dependency-injected database sessions, ORM relationships, transactional persistence, background tasks, exception isolation, PDF generation, and API integration testing. The main design lesson is to persist each recipient outcome and derive job totals from those records, rather than trusting temporary in-memory counters.

## Interview preparation

**Why store a job and separate certificate records?** A job represents the shared batch data and aggregate status. A certificate row represents one recipient's independent result, which makes partial success and per-recipient retrieval straightforward.

**How do you keep one PDF failure from stopping the batch?** The processor wraps each recipient's PDF generation in its own exception handler, marks only that record failed, commits the result, and continues with the next record. The final job status and counters come from persisted record statuses.

**What are the limits of the background processing approach?** FastAPI background tasks run in the same process, so a server crash or restart can interrupt a batch. A durable queue such as Celery with Redis and retry/recovery behavior would be appropriate for production.

## Future scope

Potential extensions include Celery and Redis for durable queued jobs, PostgreSQL for concurrent workloads, cloud object storage, authentication and authorization, rate limiting and audit logs, certificate revocation, cryptographic digital signatures, deployment, and monitoring. These are proposed extensions and are not implemented here.

## GitHub publishing

No repository is initialized and nothing has been uploaded. After reviewing the files, use these commands:

```powershell
git init
git add .
git commit -m "Build Veridoc certificate generation API"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repository>.git
git push -u origin main
```

Create the empty public repository on GitHub first, then replace the placeholders. `.gitignore` excludes local databases, generated PDFs, environment files, virtual environments, and common IDE/cache artifacts.
