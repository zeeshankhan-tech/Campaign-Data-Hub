"""Health endpoint smoke tests."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import create_app


def test_health_reports_ok_when_database_responds() -> None:
    """Health should report overall ok when SELECT 1 succeeds."""
    app = create_app()
    mock_session = MagicMock(spec=Session)
    mock_session.execute.return_value = None

    def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "app" in body
