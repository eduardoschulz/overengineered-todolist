"""testes de integracao para os endpoints de tarefas (/tasks)."""


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


class TestCreateTask:
    def test_create_task_returns_201(self, client):
        token = register_and_login(client, "create@test.com", "secret123")
        resp = client.post(
            "/tasks/",
            json={"title": "Buy groceries", "description": "Milk, bread, eggs"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Buy groceries"
        assert data["description"] == "Milk, bread, eggs"
        assert data["status"] == "pending"
        assert data["created_by"] is not None
        assert "id" in data

    def test_create_task_with_assignee(self, client):
        token = register_and_login(client, "assigner@test.com", "secret123")
        resp = client.post(
            "/tasks/",
            json={
                "title": "Review PR",
                "assigned_to": "user-456",
                "status": "in_progress",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["assigned_to"] == "user-456"
        assert data["status"] == "in_progress"


class TestGetTask:
    def test_get_task_returns_200(self, client):
        token = register_and_login(client, "get@test.com", "secret123")
        create_resp = client.post(
            "/tasks/",
            json={"title": "Read book"},
            headers=auth_header(token),
        )
        task_id = create_resp.json()["id"]

        resp = client.get(f"/tasks/{task_id}", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["title"] == "Read book"

    def test_get_task_404(self, client):
        token = register_and_login(client, "get404@test.com", "secret123")
        resp = client.get(
            "/tasks/00000000-0000-0000-0000-000000000000",
            headers=auth_header(token),
        )
        assert resp.status_code == 404


class TestListTasksByAssignee:
    def test_list_tasks_by_assignee(self, client):
        token_a = register_and_login(client, "owner@test.com", "secret123")
        token_b = register_and_login(client, "assignee@test.com", "secret456")

        client.post(
            "/tasks/",
            json={"title": "Task for B", "assigned_to": "assignee@test.com"},
            headers=auth_header(token_a),
        )
        client.post(
            "/tasks/",
            json={"title": "Own task", "assigned_to": "owner@test.com"},
            headers=auth_header(token_a),
        )

        resp = client.get(
            "/tasks/",
            params={"assignedTo": "assignee@test.com"},
            headers=auth_header(token_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        titles = [t["title"] for t in data]
        assert "Task for B" in titles

    def test_list_tasks_empty_when_no_assignee(self, client):
        token = register_and_login(client, "empty@test.com", "secret123")
        resp = client.get("/tasks/", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []


class TestUpdateTask:
    def test_update_task_returns_200(self, client):
        token = register_and_login(client, "update@test.com", "secret123")
        create_resp = client.post(
            "/tasks/",
            json={"title": "Old title"},
            headers=auth_header(token),
        )
        task_id = create_resp.json()["id"]

        resp = client.put(
            f"/tasks/{task_id}",
            json={"title": "New title", "status": "done"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        assert data["status"] == "done"
        assert data["is_completed"] is True

    def test_update_task_by_non_owner_returns_403(self, client):
        token_a = register_and_login(client, "owner2@test.com", "secret123")
        token_b = register_and_login(client, "intruder2@test.com", "secret456")
        create_resp = client.post(
            "/tasks/",
            json={"title": "Owner task"},
            headers=auth_header(token_a),
        )
        task_id = create_resp.json()["id"]

        resp = client.put(
            f"/tasks/{task_id}",
            json={"title": "Hijacked"},
            headers=auth_header(token_b),
        )
        assert resp.status_code == 403


class TestDeleteTask:
    def test_delete_task_returns_204(self, client):
        token = register_and_login(client, "del@test.com", "secret123")
        create_resp = client.post(
            "/tasks/",
            json={"title": "To delete"},
            headers=auth_header(token),
        )
        task_id = create_resp.json()["id"]

        resp = client.delete(f"/tasks/{task_id}", headers=auth_header(token))
        assert resp.status_code == 204

    def test_delete_by_non_owner_returns_403(self, client):
        token_a = register_and_login(client, "owner3@test.com", "secret123")
        token_b = register_and_login(client, "intruder3@test.com", "secret456")
        create_resp = client.post(
            "/tasks/",
            json={"title": "Owner task"},
            headers=auth_header(token_a),
        )
        task_id = create_resp.json()["id"]

        resp = client.delete(f"/tasks/{task_id}", headers=auth_header(token_b))
        assert resp.status_code == 403


class TestUnauthenticated:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/tasks/", params={"assignedTo": "someone"})
        assert resp.status_code == 401
