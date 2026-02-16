"""Load endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from models import get_db, Load

router = APIRouter()


class LoadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mcleod_order_id: str
    container_number: str | None
    status: str


@router.get("/loads", response_model=List[LoadResponse])
async def list_loads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all loads."""
    loads = db.query(Load).offset(skip).limit(limit).all()
    return loads


@router.get("/loads/{load_id}", response_model=LoadResponse)
async def get_load(load_id: int, db: Session = Depends(get_db)):
    """Get load by ID."""
    load = db.query(Load).filter(Load.id == load_id).first()
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    return load

