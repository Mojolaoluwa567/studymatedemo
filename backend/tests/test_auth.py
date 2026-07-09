def test_signup_success(client):
    resp = client.post("/signup", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "StrongPass1!",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["username"] == "newuser"
    assert "access_token" in data


def test_signup_weak_password_rejected(client):
    resp = client.post("/signup", json={
        "username": "weakuser",
        "email": "weak@example.com",
        "password": "weak",
    })
    assert resp.status_code == 400
    assert "Password must contain" in resp.get_json()["error"]


def test_signup_duplicate_username_rejected(client):
    client.post("/signup", json={
        "username": "dupeuser",
        "email": "dupe1@example.com",
        "password": "StrongPass1!",
    })
    resp = client.post("/signup", json={
        "username": "dupeuser",
        "email": "dupe2@example.com",
        "password": "StrongPass1!",
    })
    assert resp.status_code == 409


def test_login_success(client):
    client.post("/signup", json={
        "username": "loginuser",
        "email": "loginuser@example.com",
        "password": "StrongPass1!",
    })
    resp = client.post("/login", json={
        "username": "loginuser",
        "password": "StrongPass1!",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password_rejected(client):
    client.post("/signup", json={
        "username": "loginuser2",
        "email": "loginuser2@example.com",
        "password": "StrongPass1!",
    })
    resp = client.post("/login", json={
        "username": "loginuser2",
        "password": "WrongPass1!",
    })
    assert resp.status_code == 401