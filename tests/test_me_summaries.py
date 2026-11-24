from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.api.deps import get_analytics_service
from app.api.v1.endpoints.analytics import router
from app.services.analytics_service import SummaryResponse


def _build_app():
    app = FastAPI()
    app.include_router(router)
    mock_svc = MagicMock()
    mock_svc.get_summary.return_value = SummaryResponse(
        tenant_id=uuid4(),
        active_work_orders=2,
        completed_work_orders=5,
        total_revenue=1500.0,
        total_alerts=1,
    )
    app.dependency_overrides[get_analytics_service] = lambda: mock_svc
    return app


def test_me_customer_and_employee_summaries(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    class _FakeSigningKey:
        key = public_key

    class _FakeJwkClient:
        def get_signing_key_from_jwt(self, _tok):
            return _FakeSigningKey()

    monkeypatch.setattr("app.core.security.get_jwk_client", lambda _url: _FakeJwkClient())

    tenant_id = str(uuid4())
    user_id = str(uuid4())
    customer_token = jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "roles": ["CUSTOMER"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )
    employee_token = jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "roles": ["TECHNICIAN"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
    )

    client = TestClient(_build_app())

    res_cust = client.get("/api/v1/analytics/me/customer-summary", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_cust.status_code == 200
    assert res_cust.json()["customerId"] == user_id
    assert res_cust.json()["activeWorkOrdersCount"] == 2

    res_forbidden = client.get("/api/v1/analytics/me/employee-summary", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_forbidden.status_code == 403

    res_emp = client.get("/api/v1/analytics/me/employee-summary", headers={"Authorization": f"Bearer {employee_token}"})
    assert res_emp.status_code == 200
    assert res_emp.json()["employeeId"] == user_id
    assert res_emp.json()["completedTasksCount"] == 5
