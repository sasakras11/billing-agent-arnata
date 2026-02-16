"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import get_db
from health_checks import HealthCheckService

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint (database and core dependencies)."""
    service = HealthCheckService(db=db)
    result = service.check_all()
    return result


@router.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    # TODO: Wire to metrics.MetricsCollector when needed
    return {
        "uptime": "N/A",
        "requests_total": "N/A",
    }

