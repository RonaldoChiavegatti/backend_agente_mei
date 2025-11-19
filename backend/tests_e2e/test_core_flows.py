import os
import time
import uuid
from io import BytesIO
from typing import Dict

JOB_COMPLETION_TIMEOUT = int(os.environ.get("E2E_DOCUMENT_TIMEOUT", "240"))


def _register_and_login(api_client) -> Dict[str, str]:
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"e2e_{unique_suffix}@example.com"
    password = "E2eTest!123"

    register_response = api_client.post(
        "/auth/register",
        json={"full_name": "E2E Tester", "email": email, "password": password},
    )
    assert register_response.status_code == 201, register_response.text
    body = register_response.json()

    login_response = api_client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]

    return {"id": body["id"], "email": email, "token": token}


def _poll_document_job(api_client, job_id: str, token: str) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + JOB_COMPLETION_TIMEOUT
    last_body: Dict[str, str] | None = None

    while time.time() < deadline:
        response = api_client.get(f"/documents/jobs/{job_id}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        last_body = body
        if body.get("status") == "concluido":
            return body
        if body.get("status") == "falhou":
            raise AssertionError(f"Job {job_id} failed: {body}")
        time.sleep(5)

    raise AssertionError(
        f"Job {job_id} did not complete in {JOB_COMPLETION_TIMEOUT}s. "
        f"Last response: {last_body}"
    )


def test_user_can_register_and_login(api_client):
    user = _register_and_login(api_client)
    assert uuid.UUID(user["id"])  # validates UUID format
    assert user["token"].startswith("ey"), "Expected a JWT access token"


def test_document_upload_and_status_tracking(api_client):
    user = _register_and_login(api_client)
    files = {
        "file": (
            "e2e.pdf",
            BytesIO(b"%PDF-1.4\n%Minimal test PDF"),
            "application/pdf",
        )
    }
    data = {"document_type": "NOTA_FISCAL_EMITIDA"}
    headers = {"Authorization": f"Bearer {user['token']}"}

    upload_response = api_client.post(
        "/documents/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_response.status_code == 202, upload_response.text
    job = upload_response.json()
    final_job = _poll_document_job(api_client, job["id"], user["token"])

    assert final_job["status"] == "concluido"

    jobs_response = api_client.get("/documents/jobs", headers=headers)
    assert jobs_response.status_code == 200, jobs_response.text
    job_ids = {item["id"] for item in jobs_response.json()}
    assert job["id"] in job_ids


def test_billing_charge_flow(api_client, ensure_user_balance):
    user = _register_and_login(api_client)
    ensure_user_balance(user_id := user["id"], amount := 200)

    charge_payload = {
        "user_id": user_id,
        "amount": 50,
        "description": "E2E document analysis",
    }
    charge_response = api_client.post("/billing/charge-tokens", json=charge_payload)
    assert charge_response.status_code == 200, charge_response.text

    headers = {"Authorization": f"Bearer {user['token']}"}
    balance_response = api_client.get(f"/billing/balance/{user_id}", headers=headers)
    assert balance_response.status_code == 200, balance_response.text
    balance = balance_response.json()["balance"]
    assert balance == amount - charge_payload["amount"]

    transactions = api_client.get(
        f"/billing/transactions/{user_id}", headers=headers
    )
    assert transactions.status_code == 200, transactions.text
    transaction_tokens = [item["tokens"] for item in transactions.json()]
    assert charge_payload["amount"] in transaction_tokens
