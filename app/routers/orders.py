import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import dynamo

router = APIRouter()
ORDERS_TABLE = os.getenv("ORDERS_TABLE_NAME", "dev-orders")
PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE_NAME", "dev-products")


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    user_id: str
    items: list[OrderItem]


@router.post("/", status_code=201)
def create_order(order: OrderCreate):
    items_with_price = []
    total = 0.0

    for item in order.items:
        product = dynamo.get_item(PRODUCTS_TABLE, {"product_id": item.product_id})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        line_total = float(product["price"]) * item.quantity
        total += line_total
        items_with_price.append({
            "product_id": item.product_id,
            "name": product["name"],
            "quantity": item.quantity,
            "unit_price": float(product["price"]),
            "line_total": line_total,
        })

    new_order = {
        "order_id": str(uuid.uuid4()),
        "user_id": order.user_id,
        "items": items_with_price,
        "total_amount": round(total, 2),
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    dynamo.put_item(ORDERS_TABLE, new_order)
    return new_order


@router.get("/user/{user_id}")
def get_user_orders(user_id: str):
    return dynamo.query_by_index(ORDERS_TABLE, "user-orders-index", "user_id", user_id)


@router.get("/{order_id}")
def get_order(order_id: str, user_id: str):
    order = dynamo.get_item(ORDERS_TABLE, {"order_id": order_id, "user_id": user_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order