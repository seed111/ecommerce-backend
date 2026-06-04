import os
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from services import dynamo, s3

router = APIRouter()
PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE_NAME", "dev-products")


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    stock: int = 0


class ProductResponse(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    category: str
    stock: int
    image_key: Optional[str] = None


@router.get("/", response_model=list[ProductResponse])
def list_products():
    return dynamo.scan_table(PRODUCTS_TABLE)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    item = dynamo.get_item(PRODUCTS_TABLE, {"product_id": product_id})
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    return item


@router.get("/category/{category}", response_model=list[ProductResponse])
def list_by_category(category: str):
    return dynamo.query_by_index(PRODUCTS_TABLE, "category-index", "category", category)


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate):
    item = {"product_id": str(uuid.uuid4()), **product.model_dump()}
    dynamo.put_item(PRODUCTS_TABLE, item)
    return item


@router.post("/{product_id}/image")
async def upload_image(product_id: str, file: UploadFile = File(...)):
    if not dynamo.get_item(PRODUCTS_TABLE, {"product_id": product_id}):
        raise HTTPException(status_code=404, detail="Product not found")
    content = await file.read()
    key = s3.upload_product_image(content, file.content_type, product_id)
    dynamo.update_item(
        PRODUCTS_TABLE,
        key={"product_id": product_id},
        update_expression="SET image_key = :key",
        expression_values={":key": key},
    )
    return {"image_key": key, "presigned_url": s3.generate_presigned_url(key)}