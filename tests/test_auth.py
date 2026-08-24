from fastapi.testclient import TestClient

def test_new_user_registration(client: TestClient):
    response = client.post("/auth/register", json={"name": "Test User", "email": "test@example.com", "password": "password123"})
    assert response.status_code == 200
    assert response.json() == {"name": "Test User", "email": "test@example.com"}

def test_duplicate_user_registration(client: TestClient):
    # First registration should succeed
    response1 = client.post("/auth/register", json={"name": "Test User", "email": "test@example.com", "password": "password123"})
    assert response1.status_code == 200
    assert response1.json() == {"name": "Test User", "email": "test@example.com"}

    # Second registration with the same email should fail
    response2 = client.post("/auth/register", json={"name": "Another User", "email": "test@example.com", "password": "password123"})
    assert response2.status_code == 409

def test_user_login(client: TestClient, test_user):
    response = client.post("/auth/login", data={"username": test_user["email"], "password": test_user["password"]})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_failures_are_indistinguishable(client: TestClient, test_user):
    response1 = client.post("/auth/login", data={"username": test_user["email"], "password": "wrongpassword"})                                         
    assert response1.status_code == 401
    
    response2 = client.post("/auth/login", data={"username": "nonexistent@example.com", "password": "password123"})
    assert response1.status_code == response2.status_code
    assert response1.json()== response2.json()