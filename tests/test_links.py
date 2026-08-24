from fastapi.testclient import TestClient

def test_create_code(client: TestClient, auth_header):
    response = client.post("/links", json={"long_url": "https://www.example.com"}, headers=auth_header)
    assert response.status_code == 200
    assert "code" in response.json()
    assert "short_url" in response.json()
    code = response.json()["code"]
    short_url = response.json()["short_url"]
    assert short_url.endswith("/" + code)

def test_delete_code(client: TestClient, auth_header):
    # First, create a code to delete
    create_response = client.post("/links", json={"long_url": "https://www.example.com"}, headers=auth_header)
    assert create_response.status_code == 200
    code = create_response.json()["code"]

    # Now, delete the created code
    delete_response = client.delete(f"/links/{code}", headers=auth_header)
    assert delete_response.status_code == 204

    # Verify that the code no longer exists
    get_response = client.get(f"/links/{code}", headers=auth_header)
    assert get_response.status_code == 404

    #Delete the code without headers should return 401
    delete_response = client.delete(f"/links/{code}")
    assert delete_response.status_code == 401

def test_delete_non_existent_code(client: TestClient, auth_header):
    non_existent_code = "nonexistentcode"
    delete_response = client.delete(f"/links/{non_existent_code}", headers=auth_header)
    assert delete_response.status_code == 404

def test_delete_code_different_user(client: TestClient, auth_header):

    # First, create a code to delete
    create_response = client.post("/links", json={"long_url": "https://www.example.com"}, headers=auth_header)
    assert create_response.status_code == 200
    code = create_response.json()["code"]

    # Now, create a different user and try to delete the code
    different_user_data = {"name": "Different User", "email": "differentuser@example.com", "password": "password123"}
    different_user_response = client.post("/auth/register", json=different_user_data)
    assert different_user_response.status_code == 200

    #Login the new user to get the auth header
    login_response = client.post("/auth/login", data={"username": different_user_data["email"], "password": different_user_data["password"]})
    assert login_response.status_code == 200
    different_user_auth_header = { "Authorization": f"Bearer {login_response.json()['access_token']}" }

    # Try to delete the code as the different user
    delete_response = client.delete(f"/links/{code}", headers=different_user_auth_header)
    assert delete_response.status_code == 403

    #check link still exists for the original user
    get_response = client.get(f"/links/{code}", headers=auth_header, follow_redirects=False)
    assert get_response.status_code == 302

def test_get_all_links_for_current_user(client: TestClient, auth_header):
    # Create a few links for the current user
    urls = ["https://www.example1.com/page", "https://www.example2.com/page", "https://www.example3.com/page"]
    for url in urls:
        response = client.post("/links", json={"long_url": url}, headers=auth_header)
        assert response.status_code == 200

    # Get all links for the current user
    get_response = client.get("/links", headers=auth_header)
    assert get_response.status_code == 200
    links = get_response.json()
    assert len(links) == len(urls)
    for link in links:
        assert "code" in link
        assert "long_url" in link
        assert link["long_url"] in urls

# Create a link as user one and login as user two and check that user two cannot see user one's links
def test_get_all_links_for_different_user(client: TestClient, auth_header):
    # Create a link for the first user
    response = client.post("/links", json={"long_url": "https://www.example.come"}, headers=auth_header)
    assert response.status_code == 200

    # Now, create a different user and try to get all links
    different_user_data = {"name": "Different User", "email": "differentuser@example.com", "password": "password123"}
    different_user_response = client.post("/auth/register", json=different_user_data)
    assert different_user_response.status_code == 200

    # Login the new user to get the auth header
    login_response = client.post("/auth/login", data={"username": different_user_data["email"], "password": different_user_data["password"]})
    assert login_response.status_code == 200
    different_user_auth_header = { "Authorization": f"Bearer {login_response.json()['access_token']}" }

    # Try to get all links as the different user
    get_response = client.get("/links", headers=different_user_auth_header)
    assert get_response.status_code == 200
    links = get_response.json()
    assert len(links) == 0

# Invalid URL should return 422
def test_create_code_invalid_url(client: TestClient, auth_header):
    response = client.post("/links", json={"long_url": "invalid-url"}, headers=auth_header)
    assert response.status_code == 422 
