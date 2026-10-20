import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from config import settings


# Helpers

def b64url(obj: dict) -> str:
    """JSON-encode a dict the way PyJWT does, then base64url it without padding."""
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def b64url_decode(segment: str) -> dict:
    """Undo b64url: add the stripped padding back, decode, parse JSON."""
    padded = segment + "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))

def sign(claims: dict) -> str:
    """Sign a token with the app's real key and algorithm (white-box: the test knows the secret)."""
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def in_minutes(n: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=n)

def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


# Tampered signature

def test_corrupted_signature_is_rejected(client: TestClient, test_user):
    token = login(client, test_user["email"], test_user["password"])
    assert client.get("/links", headers=bearer(token)).status_code == 200   # control: the real token works

    header, payload, signature = token.split(".")
    mid = len(signature) // 2
    replacement = "A" if signature[mid] != "A" else "B"
    corrupted = f"{header}.{payload}.{signature[:mid]}{replacement}{signature[mid + 1:]}"

    assert client.get("/links", headers=bearer(corrupted)).status_code == 401

def test_editing_sub_to_impersonate_another_user_is_rejected(client: TestClient, test_user):
    attacker = {"name": "Attacker", "email": "attacker@example.com", "password": "password123"}
    assert client.post("/auth/register", json=attacker).status_code == 200
    attacker_token = login(client, attacker["email"], attacker["password"])
    assert client.get("/links", headers=bearer(attacker_token)).status_code == 200   # control

    header, payload, signature = attacker_token.split(".")
    claims = b64url_decode(payload)
    assert b64url(claims) == payload   # re-encoding unchanged claims reproduces the segment exactly

    claims["sub"] = test_user["email"]   # become the victim
    forged = f"{header}.{b64url(claims)}.{signature}"

    assert client.get("/links", headers=bearer(forged)).status_code == 401


# Alg: none

def test_alg_none_token_is_rejected(client: TestClient, test_user):
    claims = {"sub": test_user["email"], "exp": int(in_minutes(30).timestamp())}
    assert client.get("/links", headers=bearer(sign(claims))).status_code == 200   # control: same claims, signed

    forged = b64url({"alg": "none", "typ": "JWT"}) + "." + b64url(claims) + "."

    assert client.get("/links", headers=bearer(forged)).status_code == 401


# ---------- 1.13 expiry ----------

def test_expired_token_is_rejected(client: TestClient, test_user):
    assert client.get("/links", headers=bearer(sign({"sub": test_user["email"], "exp": in_minutes(30)}))).status_code == 200   # control

    expired = sign({"sub": test_user["email"], "exp": in_minutes(-1)})

    assert client.get("/links", headers=bearer(expired)).status_code == 401

def test_token_without_exp_is_rejected(client: TestClient, test_user):
    assert client.get("/links", headers=bearer(sign({"sub": test_user["email"], "exp": in_minutes(30)}))).status_code == 200   # control

    no_exp = sign({"sub": test_user["email"]})

    assert client.get("/links", headers=bearer(no_exp)).status_code == 401


# Anonymous callers

@pytest.mark.parametrize("method, path", [
    ("POST", "/links"),
    ("GET", "/links"),
    ("DELETE", "/links/zzzzzzz"),
])
def test_protected_routes_refuse_anonymous_callers(client: TestClient, method, path):
    body = {"long_url": "https://www.example.com"} if method == "POST" else None
    response = client.request(method, path, json=body)
    assert response.status_code == 401


# Rate limiting
@pytest.mark.ratelimit
def test_login_is_rate_limited(client: TestClient):
    bad_login = {"username": "nobody@example.com", "password": "wrongpassword"}
    statuses = [client.post("/auth/login", data=bad_login).status_code for _ in range(6)]
    assert statuses == [401, 401, 401, 401, 401, 429]