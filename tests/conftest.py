import os
import tempfile
from pathlib import Path

_test_root = Path(tempfile.mkdtemp(prefix="veridoc-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_test_root / 'tests.db'}"
os.environ["CERTIFICATE_OUTPUT_DIR"] = str(_test_root / "certificates")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def valid_payload():
    return {"course_name": "Python Backend Development", "organization": "AEREO Learning Program",
            "issue_date": "2026-10-10", "recipients": [
                {"name": "Ananya Sharma", "email": "ananya@example.com"},
                {"name": "Rahul Kumar", "email": "rahul@example.com"}]}
