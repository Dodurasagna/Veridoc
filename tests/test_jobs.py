def test_create_and_process_job(client, valid_payload):
    response = client.post("/api/jobs/", json=valid_payload)
    assert response.status_code == 202
    data = response.json()
    assert data["total_submitted"] == 2
    assert data["valid_count"] == 2
    status = client.get(f"/api/jobs/{data['job_id']}").json()
    assert status["status"] == "COMPLETED"
    assert status["successful_count"] == 2
    assert status["progress_percentage"] == 100


def test_invalid_recipient_is_reported_and_other_recipient_succeeds(client, valid_payload):
    valid_payload["recipients"].append({"name": "", "email": "invalid-email"})
    result = client.post("/api/jobs/", json=valid_payload).json()
    assert result["invalid_count"] == 1
    assert result["validation_errors"][0]["index"] == 2
    status = client.get(f"/api/jobs/{result['job_id']}").json()
    assert status["status"] == "COMPLETED_WITH_ERRORS"
    assert status["successful_count"] == 2


def test_malformed_job_level_input_is_rejected(client, valid_payload):
    valid_payload["course_name"] = "  "
    assert client.post("/api/jobs/", json=valid_payload).status_code == 422


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/not-a-job").status_code == 404
    assert client.get("/api/jobs/not-a-job/certificates").status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
