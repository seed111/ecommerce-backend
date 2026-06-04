import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from services import dynamo

router = APIRouter()
USERS_TABLE = os.getenv("USERS_TABLE_NAME", "dev-users")


class UserCreate(BaseModel):
    name: str
    email: EmailStr


@router.post("/", status_code=201)
def create_user(user: UserCreate):
    if dynamo.query_by_index(USERS_TABLE, "email-index", "email", user.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    new_user = {
        "user_id": str(uuid.uuid4()),
        "name": user.name,
        "email": user.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    dynamo.put_item(USERS_TABLE, new_user)
    return new_user


@router.get("/{user_id}")
def get_user(user_id: str):
    user = dynamo.get_item(USERS_TABLE, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user