import asyncio

import pytest
from fastapi.testclient import TestClient

from app.feature.service import build_greeting
from tests.conftest import APP_NAME


def test_create_greeting(client: TestClient) -> None:
    response = client.post("/greetings", json={"name": "world"})
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Hello, world! Welcome to {APP_NAME}.",
        "app_name": APP_NAME,
    }


def test_create_greeting_strips_whitespace(client: TestClient) -> None:
    response = client.post("/greetings", json={"name": "  world  "})
    assert response.status_code == 200
    assert response.json()["message"] == f"Hello, world! Welcome to {APP_NAME}."


@pytest.mark.parametrize("name", ["", "   ", "x" * 51])
def test_create_greeting_rejects_invalid_name(client: TestClient, name: str) -> None:
    assert client.post("/greetings", json={"name": name}).status_code == 422


def test_create_greeting_requires_name(client: TestClient) -> None:
    assert client.post("/greetings", json={}).status_code == 422


def test_openapi_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == APP_NAME


def test_build_greeting() -> None:
    result = asyncio.run(build_greeting("world", app_name="fahad"))
    assert result == "Hello, world! Welcome to fahad."
