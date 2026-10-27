from main import app

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# IDs match the contract-derived case table. Expected values are literal
# business expectations, independent of calculate_discount and its output.
@pytest.mark.parametrize(
    "amount, expected",
    [
        pytest.param(1, {"amount": 1, "discount": 0, "payable": 1}, id="Q01"),
        pytest.param(5000, {"amount": 5000, "discount": 0, "payable": 5000}, id="Q02"),
        pytest.param(9999, {"amount": 9999, "discount": 0, "payable": 9999}, id="Q03"),
        pytest.param(10000, {"amount": 10000, "discount": 1000, "payable": 9000}, id="Q04"),
        pytest.param(10001, {"amount": 10001, "discount": 1000, "payable": 9001}, id="Q05"),
        pytest.param(20000, {"amount": 20000, "discount": 1000, "payable": 19000}, id="Q06"),
        pytest.param(100000, {"amount": 100000, "discount": 1000, "payable": 99000}, id="Q07"),
    ],
)
def test_quote_success(client, amount, expected):
    response = client.post("/quotes", json={"amount": amount})

    assert response.status_code == 200
    # Exact equality also verifies the three response fields and no extras.
    assert response.json() == expected


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"amount": 0}, id="E01"),
        pytest.param({"amount": 100001}, id="E02"),
        pytest.param({}, id="E03"),
        pytest.param({"amount": "10000"}, id="E05"),
        pytest.param({"amount": 10000.5}, id="E06"),
        pytest.param({"amount": 10000.0}, id="E07"),
        pytest.param({"amount": True}, id="E08"),
        pytest.param({"amount": False}, id="E09"),
        pytest.param({"amount": None}, id="E10"),
        pytest.param({"amount": [10000]}, id="E11"),
        pytest.param({"amount": {}}, id="E12"),
    ],
)
def test_quote_invalid_amount(client, body):
    response = client.post("/quotes", json=body)

    assert response.status_code == 422
    # Follow the supplied tests' FastAPI error envelope convention without
    # freezing version-dependent error messages or error-list ordering.
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(error.get("loc") == ["body", "amount"] for error in detail)


def test_quote_missing_body_E04(client):
    response = client.post("/quotes")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(error.get("loc") == ["body"] for error in detail)
