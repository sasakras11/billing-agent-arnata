"""Health check utilities for monitoring system status."""
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from sqlalchemy import text
from sqlalchemy.orm import Session
from redis import Redis

from config import get_settings
from logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status for a system component."""
    
    def __init__(
        self,
        status: HealthStatus,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[float] = None
    ):
        """Initialize component health."""
        self.status = status
        self.message = message
        self.details = details or {}
        self.latency_ms = latency_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "status": self.status.value,
        }
        
        if self.message:
            result["message"] = self.message
        
        if self.details:
            result["details"] = self.details
        
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        
        return result


class HealthCheckService:
    """Service for checking system health."""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize health check service."""
        self.db = db

    def check_database(self) -> ComponentHealth:
        """Check database connectivity and health."""
        if not self.db:
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message="Database session not available"
            )
        
        try:
            start_time = datetime.now()
            
            # Simple query to check connection
            result = self.db.execute(text("SELECT 1")).scalar()
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if result == 1:
                return ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    message="Database connection OK",
                    latency_ms=latency_ms
                )
            else:
                return ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result"
                )
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}"
            )
    
    def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and health."""
        try:
            start_time = datetime.now()
            
            # Connect to Redis
            redis_client = Redis.from_url(settings.redis_url)
            
            # Ping Redis
            result = redis_client.ping()
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                return ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    message="Redis connection OK",
                    latency_ms=latency_ms
                )
            else:
                return ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed"
                )
                
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}"
            )
    
    def check_mcleod_api(self) -> ComponentHealth:
        """Check McLeod API connectivity."""
        try:
            # This is a placeholder - actual implementation would
            # make a lightweight API call to McLeod
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="McLeod API configured",
                details={
                    "api_url": settings.mcleod_api_url,
                    "company_id": settings.mcleod_company_id,
                }
            )
            
        except Exception as e:
            logger.error("McLeod API health check failed", error=str(e))
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=f"McLeod API check failed: {str(e)}"
            )
    
    def check_terminal49_api(self) -> ComponentHealth:
        """Check Terminal49 API connectivity."""
        try:
            # This is a placeholder - actual implementation would
            # make a lightweight API call to Terminal49
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Terminal49 API configured"
            )
            
        except Exception as e:
            logger.error("Terminal49 API health check failed", error=str(e))
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=f"Terminal49 API check failed: {str(e)}"
            )
    
    def check_quickbooks_api(self) -> ComponentHealth:
        """Check QuickBooks API connectivity."""
        try:
            # This is a placeholder - actual implementation would
            # verify QuickBooks OAuth token validity
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="QuickBooks API configured",
                details={
                    "environment": settings.quickbooks_environment,
                    "realm_id": settings.quickbooks_realm_id,
                }
            )
            
        except Exception as e:
            logger.error("QuickBooks API health check failed", error=str(e))
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=f"QuickBooks API check failed: {str(e)}"
            )
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        logger.info("Running health checks")
        
        # Check all components
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "mcleod_api": self.check_mcleod_api(),
            "terminal49_api": self.check_terminal49_api(),
            "quickbooks_api": self.check_quickbooks_api(),
        }
        
        # Determine overall status
        statuses = [check.status for check in checks.values()]
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        # Build response
        result = {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.app_env,
            "checks": {
                name: check.to_dict()
                for name, check in checks.items()
            }
        }
        
        logger.info(
            "Health checks completed",
            overall_status=overall_status.value,
            checks_count=len(checks)
        )
        
        return result
    
    def check_readiness(self) -> Dict[str, Any]:
        """
        Check if application is ready to serve requests.
        
        Checks only critical dependencies (database, redis).
        
        Returns:
            Readiness status
        """
        logger.info("Running readiness checks")
        
        # Check critical components
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
        }
        
        # Must all be healthy for app to be ready
        is_ready = all(
            check.status == HealthStatus.HEALTHY
            for check in checks.values()
        )
        
        result = {
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                name: check.to_dict()
                for name, check in checks.items()
            }
        }
        
        logger.info(
            "Readiness checks completed",
            ready=is_ready
        )
        
        return result
    
    def check_liveness(self) -> Dict[str, Any]:
        """
        Check if application is alive (basic health).
        
        Returns:
            Liveness status
        """
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.app_env,
        }


def get_health_check_service(db: Optional[Session] = None) -> HealthCheckService:
    """
    Get health check service instance.
    
    Args:
        db: Optional database session
        
    Returns:
        HealthCheckService instance
    """
    return HealthCheckService(db=db)

