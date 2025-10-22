"""Container endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from models import get_db, Container

router = APIRouter()


class ContainerResponse(BaseModel):
    id: int
    container_number: str
    current_status: str | None
    location: str | None
    last_free_day: datetime | None
    
    class Config:
        from_attributes = True


@router.get("/containers", response_model=List[ContainerResponse])
async def list_containers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all containers."""
    containers = db.query(Container).offset(skip).limit(limit).all()
    return containers


@router.get("/containers/{container_number}", response_model=ContainerResponse)
async def get_container(container_number: str, db: Session = Depends(get_db)):
    """Get container by number."""
    container = (
        db.query(Container)
        .filter(Container.container_number == container_number)
        .first()
    )
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container

