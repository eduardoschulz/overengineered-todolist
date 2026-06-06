def test_register_creates_user(client):
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


def test_duplicate_email_returns_409(client):
    client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "secret123",
    })
    response = client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "other456",
    })
    assert response.status_code == 409
    assert "detail" in response.json()


def test_login_returns_token(client):
    client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={
        "email": "wrongpw@example.com",
        "password": "correct",
    })
    response = client.post("/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post("/auth/login", json={
        "email": "unknown@example.com",
        "password": "anything",
    })
    assert response.status_code == 401
