"""testes de integracao para os endpoints de tarefas."""


def register_and_login(client, email: str, password: str) -> str:
    """registra um usuario e retorna o token JWT."""
    client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    """retorna o header de autorizacao com o token."""
    return {"Authorization": f"Bearer {token}"}


class TestCreateList:
    def test_create_list_returns_201(self, client):
        token = register_and_login(client, "list@test.com", "secret123")
        resp = client.post(
            "/lists/",
            json={"name": "My Tasks"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Tasks"
        assert data["owner_id"] is not None
        assert "id" in data
        assert "created_at" in data


class TestGetLists:
    def test_get_lists_returns_only_my_lists(self, client):
        token_a = register_and_login(client, "userA@test.com", "secret123")
        token_b = register_and_login(client, "userB@test.com", "secret456")

        client.post(
            "/lists/",
            json={"name": "A's List"},
            headers=auth_header(token_a),
        )
        client.post(
            "/lists/",
            json={"name": "B's List"},
            headers=auth_header(token_b),
        )

        resp = client.get("/lists/", headers=auth_header(token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "A's List"


class TestAddItem:
    def test_add_item_returns_201(self, client):
        token = register_and_login(client, "additem@test.com", "secret123")
        create_resp = client.post(
            "/lists/",
            json={"name": "Groceries"},
            headers=auth_header(token),
        )
        list_id = create_resp.json()["id"]

        resp = client.post(
            f"/lists/{list_id}/items",
            json={"title": "Buy milk"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Buy milk"
        assert data["items"][0]["is_completed"] is False


class TestCompleteItem:
    def test_complete_item_returns_200(self, client):
        token = register_and_login(client, "complete@test.com", "secret123")
        create_resp = client.post(
            "/lists/",
            json={"name": "Tasks"},
            headers=auth_header(token),
        )
        list_id = create_resp.json()["id"]
        add_resp = client.post(
            f"/lists/{list_id}/items",
            json={"title": "Do laundry"},
            headers=auth_header(token),
        )
        item_id = add_resp.json()["items"][0]["id"]

        resp = client.patch(
            f"/lists/{list_id}/items/{item_id}/complete",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["is_completed"] is True


class TestDeleteList:
    def test_delete_list_returns_204(self, client):
        token = register_and_login(client, "delete@test.com", "secret123")
        create_resp = client.post(
            "/lists/",
            json={"name": "To Delete"},
            headers=auth_header(token),
        )
        list_id = create_resp.json()["id"]

        resp = client.delete(
            f"/lists/{list_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204


class TestAccessControl:
    def test_cannot_access_another_users_list(self, client):
        token_a = register_and_login(client, "owner@test.com", "secret123")
        token_b = register_and_login(client, "intruder@test.com", "secret456")

        create_resp = client.post(
            "/lists/",
            json={"name": "Owner List"},
            headers=auth_header(token_a),
        )
        list_id = create_resp.json()["id"]

        resp = client.delete(
            f"/lists/{list_id}",
            headers=auth_header(token_b),
        )
        assert resp.status_code == 403


class TestUnauthenticated:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/lists/")
        assert resp.status_code == 401
