"""catalog: a product-catalog HTTP service serving Product records as JSON."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="catalog")


class Product(BaseModel):
    sku: str
    name: str
    catalog: str


PRODUCTS = {
    "SKU-1": Product(sku="SKU-1", name="Walnut Desk", catalog="furniture"),
}


@app.get("/products/{sku}")
def read_product(sku: str) -> Product:
    product = PRODUCTS.get(sku)
    if product is None:
        raise HTTPException(status_code=404, detail="unknown sku")
    return product
