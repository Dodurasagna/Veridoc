from pathlib import Path


def test_pdf_download_and_verification(client, valid_payload):
    created = client.post("/api/jobs/", json=valid_payload).json()
    records = client.get(f"/api/jobs/{created['job_id']}/certificates").json()["certificates"]
    first = records[0]
    pdf = client.get(first["download_url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-") and pdf.content.rstrip().endswith(b"%%EOF")
    verified = client.get(f"/api/verify/{first['verification_id']}")
    assert verified.json()["valid"] is True
    assert verified.json()["recipient_name"] == "Ananya Sharma"
    assert client.get("/api/verify/unknown-id").json()["valid"] is False


def test_failure_is_isolated_and_not_downloadable(client, valid_payload, monkeypatch):
    import app.services.job_processor as processor

    original = processor.generate_certificate

    def fail_one(**kwargs):
        if kwargs["recipient_name"] == "Ananya Sharma":
            raise OSError("simulated disk issue")
        return original(**kwargs)

    monkeypatch.setattr(processor, "generate_certificate", fail_one)
    created = client.post("/api/jobs/", json=valid_payload).json()
    status = client.get(f"/api/jobs/{created['job_id']}").json()
    assert status["status"] == "COMPLETED_WITH_ERRORS"
    assert status["successful_count"] == 1
    assert status["failed_count"] == 1
    results = client.get(f"/api/jobs/{created['job_id']}/certificates").json()["certificates"]
    failed = next(item for item in results if item["status"] == "FAILED")
    assert failed["error_message"]
    assert client.get(f"/api/certificates/{failed['certificate_id']}").status_code == 404


def test_unknown_certificate_is_404(client):
    assert client.get("/api/certificates/no-such-certificate").status_code == 404
