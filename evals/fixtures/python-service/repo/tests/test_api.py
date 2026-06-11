from fastapi.testclient import TestClient

from catalog.main import app

client = TestClient(app)


def test_read_product_returns_the_product():
    response = client.get("/products/SKU-1")
    assert response.status_code == 200
    assert response.json() == {
        "sku": "SKU-1",
        "name": "Walnut Desk",
        "catalog": "furniture",
    }
