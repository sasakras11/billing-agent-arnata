"""Customer endpoints."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import get_db, Customer

router = APIRouter()


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str | None
    
    class Config:
        from_attributes = True


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all customers."""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers

