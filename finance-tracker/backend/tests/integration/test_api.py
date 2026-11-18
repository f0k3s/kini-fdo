"""Интеграционные тесты HTTP-слоя.

Проверяют коды ответов, сериализацию и связку роутер → сервис.
Логика уже покрыта юнит-тестами, здесь минимум повторов.
"""

from decimal import Decimal


def create_account(client, name="Основной", balance="1000.00"):
    response = client.post(
        "/api/accounts", json={"name": name, "initial_balance": balance}
    )
    assert response.status_code == 201
    return response.json()


class TestHealth:
    def test_health_ok(self, client):
        assert client.get("/health").json() == {"status": "ok"}


class TestAccountsApi:
    def test_create_returns_201_and_balance(self, client):
        body = create_account(client, "Кошелёк", "500.50")
        assert body["name"] == "Кошелёк"
        assert body["balance"] == "500.50"
        assert body["id"]

    def test_empty_name_returns_422(self, client):
        response = client.post("/api/accounts", json={"name": "", "initial_balance": "0"})
        assert response.status_code == 422

    def test_negative_balance_returns_422(self, client):
        response = client.post(
            "/api/accounts", json={"name": "Долг", "initial_balance": "-1"}
        )
        assert response.status_code == 422

    def test_list_returns_created(self, client):
        create_account(client, "А")
        create_account(client, "Б")
        assert len(client.get("/api/accounts").json()) == 2

    def test_missing_account_returns_404(self, client):
        assert client.get("/api/accounts/нет").status_code == 404

    def test_delete_returns_204(self, client):
        account = create_account(client)
        assert client.delete(f"/api/accounts/{account['id']}").status_code == 204
        assert client.get(f"/api/accounts/{account['id']}").status_code == 404


class TestOperationsApi:
    def test_create_income(self, client):
        account = create_account(client)
        response = client.post(
            "/api/operations",
            json={
                "account_id": account["id"],
                "type": "income",
                "amount": "500",
                "category": "зарплата",
                "day": "2026-11-01",
            },
        )
        assert response.status_code == 201
        assert response.json()["amount"] == "500.00"

    def test_type_alias_accepted(self, client):
        account = create_account(client)
        response = client.post(
            "/api/operations",
            json={
                "account_id": account["id"],
                "type": "расход",
                "amount": "100",
                "category": "продукты",
                "day": "2026-11-02",
            },
        )
        assert response.status_code == 201
        assert response.json()["type"] == "expense"

    def test_insufficient_funds_returns_400(self, client):
        account = create_account(client, balance="10.00")
        response = client.post(
            "/api/operations",
            json={
                "account_id": account["id"],
                "type": "expense",
                "amount": "11",
                "category": "продукты",
                "day": "2026-11-02",
            },
        )
        assert response.status_code == 400
        assert "недостаточно средств" in response.json()["detail"].lower()

    def test_unknown_account_returns_404(self, client):
        response = client.post(
            "/api/operations",
            json={
                "account_id": "нет",
                "type": "income",
                "amount": "1",
                "category": "прочее",
                "day": "2026-11-01",
            },
        )
        assert response.status_code == 404

    def test_balance_reflects_operations(self, client):
        account = create_account(client, balance="100.00")
        client.post(
            "/api/operations",
            json={
                "account_id": account["id"],
                "type": "income",
                "amount": "50",
                "category": "прочее",
                "day": "2026-11-01",
            },
        )
        client.post(
            "/api/operations",
            json={
                "account_id": account["id"],
                "type": "expense",
                "amount": "30",
                "category": "прочее",
                "day": "2026-11-02",
            },
        )
        body = client.get(f"/api/accounts/{account['id']}").json()
        assert body["balance"] == "120.00"


class TestReportApi:
    def test_report_after_operations(self, client):
        account = create_account(client, balance="0.00")
        for payload in (
            {"type": "income", "amount": "1000", "category": "зарплата", "day": "2026-11-01"},
            {"type": "expense", "amount": "250", "category": "продукты", "day": "2026-11-02"},
        ):
            client.post("/api/operations", json={"account_id": account["id"], **payload})
        body = client.get(
            "/api/reports/monthly", params={"month": "2026-11"}
        ).json()
        assert body["income"] == "1000.00"
        assert body["expense"] == "250.00"
        assert body["balance"] == "750.00"
        assert body["top_category"]["name"] == "продукты"

    def test_empty_month_returns_warning(self, client):
        body = client.get("/api/reports/monthly", params={"month": "2026-11"}).json()
        assert body["operations"] == 0
        assert body["warnings"]

    def test_bad_month_returns_422(self, client):
        response = client.get("/api/reports/monthly", params={"month": "2026-13"})
        assert response.status_code == 422
