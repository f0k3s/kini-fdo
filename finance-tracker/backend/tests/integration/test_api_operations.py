"""Дополнительные тесты HTTP-слоя: получение и удаление операций."""

from decimal import Decimal

import pytest


@pytest.fixture
def account(client):
    body = client.post(
        "/api/accounts", json={"name": "Основной", "initial_balance": "100.00"}
    ).json()
    return body


@pytest.fixture
def operation(client, account):
    body = client.post(
        "/api/operations",
        json={
            "account_id": account["id"],
            "type": "income",
            "amount": "10",
            "category": "прочее",
            "day": "2026-11-01",
        },
    ).json()
    assert body["amount"] == "10.00"
    return body


def test_get_operation_by_id(client, operation):
    response = client.get(f"/api/operations/{operation['id']}")
    assert response.status_code == 200
    assert response.json()["category"] == "прочее"


def test_get_missing_operation_returns_404(client):
    assert client.get("/api/operations/нет").status_code == 404


def test_delete_operation_returns_204(client, operation):
    assert client.delete(f"/api/operations/{operation['id']}").status_code == 204
    assert client.get(f"/api/operations/{operation['id']}").status_code == 404


def test_delete_missing_operation_returns_404(client):
    assert client.delete("/api/operations/нет").status_code == 404


def test_list_filters_by_month_and_type(client, operation):
    response = client.get(
        "/api/operations", params={"month": "2026-11", "type": "income"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_other_month_is_empty(client, operation):
    response = client.get("/api/operations", params={"month": "2026-12"})
    assert response.json() == []


def test_bad_month_in_list_returns_422(client):
    response = client.get("/api/operations", params={"month": "2026-13"})
    assert response.status_code == 422
