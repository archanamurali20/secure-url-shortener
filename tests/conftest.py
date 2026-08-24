
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from main import app, get_session, limiter
from config import settings
@pytest.fixture(name="session")
def session_fixture():
    test_engine = create_engine(settings.TEST_DATABASE_URL)
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture(name="client")
def client_fixture(session:Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="rate_limiter", autouse=True)
def rate_limiter_fixture():
    limiter.enabled = False
    yield
    limiter.enabled = True

@pytest.fixture(name="test_user")
def test_user_fixture(client: TestClient):
    user_data = {"name": "Test User", "email": "test@example.com", "password": "password123"}
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 200
    return user_data

@pytest.fixture(name="auth_header")
def auth_header_fixture(client: TestClient, test_user):
    login_data = {"username": test_user["email"], "password": test_user["password"]}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    return { "Authorization": f"Bearer {response.json()['access_token']}" }