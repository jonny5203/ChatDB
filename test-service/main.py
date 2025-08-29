"""
Test Service - Health Check and Service Mesh Validation

Provides comprehensive health monitoring, service discovery validation,
and service mesh testing capabilities for the ChatDB system.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import httpx
import psycopg2
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaConnectionError
import os
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service configuration
SERVICE_URLS = {
    "training-orchestrator": os.getenv("TRAINING_ORCHESTRATOR_URL", "http://training-orchestrator:8000"),
    "ml-engine": os.getenv("ML_ENGINE_URL", "http://ml-engine:8000"),
    "query-parser": os.getenv("QUERY_PARSER_URL", "http://query-parser:8000"),
    "model-registry": os.getenv("MODEL_REGISTRY_URL", "http://model-registry:8000"),
    "db-connector": os.getenv("DB_CONNECTOR_URL", "http://db-connector:8080"),
    "api-gateway": os.getenv("API_GATEWAY_URL", "http://api-gateway:8080"),
    "prediction-service": os.getenv("PREDICTION_SERVICE_URL", "http://prediction-service:8080"),
}

DATABASE_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password'),
    'database': os.getenv('POSTGRES_DB', 'training_db')
}

KAFKA_CONFIG = {
    'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
    'timeout': 5
}

# Models
class ServiceHealth(BaseModel):
    name: str
    url: str
    status: str
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class SystemHealth(BaseModel):
    overall_status: str
    timestamp: datetime
    services: List[ServiceHealth]
    infrastructure: Dict[str, ServiceHealth]
    summary: Dict[str, int]

class ServiceMeshTest(BaseModel):
    test_name: str
    status: str
    duration_ms: int
    details: Dict[str, Any]
    error: Optional[str] = None

# Global state for caching
health_cache: Dict[str, Any] = {}
cache_timestamp: Optional[datetime] = None
CACHE_DURATION = 30  # seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Test Service starting up...")
    yield
    logger.info("Test Service shutting down...")

app = FastAPI(
    title="ChatDB Test Service",
    description="Health Check and Service Mesh Validation Service",
    version="1.0.0",
    lifespan=lifespan
)

async def check_service_health(service_name: str, url: str) -> ServiceHealth:
    """Check health of a single service."""
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try /health first, then /
            endpoints = ["/health", "/"]
            response = None
            
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{url}{endpoint}")
                    break
                except Exception:
                    continue
            
            if response is None:
                raise httpx.ConnectError("Could not connect to any endpoint")
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                try:
                    details = response.json()
                except Exception:
                    details = {"response": "OK"}
                
                return ServiceHealth(
                    name=service_name,
                    url=url,
                    status="healthy",
                    response_time_ms=response_time,
                    details=details
                )
            else:
                return ServiceHealth(
                    name=service_name,
                    url=url,
                    status="unhealthy",
                    response_time_ms=response_time,
                    error=f"HTTP {response.status_code}"
                )
                
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return ServiceHealth(
            name=service_name,
            url=url,
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e)
        )

async def check_database_health() -> ServiceHealth:
    """Check database connectivity."""
    start_time = time.time()
    
    try:
        connection = psycopg2.connect(**DATABASE_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        response_time = int((time.time() - start_time) * 1000)
        
        if result and result[0] == 1:
            return ServiceHealth(
                name="database",
                url=f"postgres://{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}",
                status="healthy",
                response_time_ms=response_time,
                details={"database": DATABASE_CONFIG['database']}
            )
        else:
            return ServiceHealth(
                name="database",
                url=f"postgres://{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}",
                status="unhealthy",
                response_time_ms=response_time,
                error="Invalid query result"
            )
            
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return ServiceHealth(
            name="database",
            url=f"postgres://{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}",
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e)
        )

async def check_kafka_health() -> ServiceHealth:
    """Check Kafka connectivity."""
    start_time = time.time()
    
    try:
        # Try to create a producer to test connectivity
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            api_version=(0, 10, 1),
            request_timeout_ms=5000
        )
        
        # Get cluster metadata
        metadata = producer.list_topics()
        producer.close()
        
        response_time = int((time.time() - start_time) * 1000)
        
        return ServiceHealth(
            name="kafka",
            url=KAFKA_CONFIG['bootstrap_servers'],
            status="healthy",
            response_time_ms=response_time,
            details={"topics": len(metadata.topics), "brokers": len(metadata.brokers)}
        )
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return ServiceHealth(
            name="kafka",
            url=KAFKA_CONFIG['bootstrap_servers'],
            status="unhealthy",
            response_time_ms=response_time,
            error=str(e)
        )

@app.get("/", response_model=Dict[str, str])
async def read_root():
    """Root endpoint returning service information."""
    return {
        "service": "ChatDB Test Service",
        "version": "1.0.0",
        "description": "Health Check and Service Mesh Validation",
        "endpoints": {
            "health": "/health - System health check",
            "services": "/services - Individual service health",
            "mesh": "/mesh - Service mesh validation",
            "metrics": "/metrics - System metrics"
        }
    }

@app.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Get comprehensive system health status."""
    global health_cache, cache_timestamp
    
    # Check cache validity
    if (cache_timestamp and 
        (datetime.now() - cache_timestamp).seconds < CACHE_DURATION and
        health_cache):
        return SystemHealth(**health_cache)
    
    logger.info("Performing full system health check...")
    
    # Check all services concurrently
    service_tasks = [
        check_service_health(name, url) 
        for name, url in SERVICE_URLS.items()
    ]
    
    # Check infrastructure components
    infrastructure_tasks = [
        check_database_health(),
        check_kafka_health()
    ]
    
    # Execute all checks concurrently
    service_results = await asyncio.gather(*service_tasks, return_exceptions=True)
    infrastructure_results = await asyncio.gather(*infrastructure_tasks, return_exceptions=True)
    
    # Process results
    services = []
    for result in service_results:
        if isinstance(result, ServiceHealth):
            services.append(result)
        else:
            logger.error(f"Service health check failed: {result}")
    
    infrastructure = {}
    for result in infrastructure_results:
        if isinstance(result, ServiceHealth):
            infrastructure[result.name] = result
        else:
            logger.error(f"Infrastructure health check failed: {result}")
    
    # Calculate overall status
    healthy_services = len([s for s in services if s.status == "healthy"])
    total_services = len(services)
    healthy_infrastructure = len([i for i in infrastructure.values() if i.status == "healthy"])
    total_infrastructure = len(infrastructure)
    
    # Overall status logic
    if healthy_services == total_services and healthy_infrastructure == total_infrastructure:
        overall_status = "healthy"
    elif healthy_services > 0 or healthy_infrastructure > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    summary = {
        "healthy_services": healthy_services,
        "total_services": total_services,
        "healthy_infrastructure": healthy_infrastructure,
        "total_infrastructure": total_infrastructure
    }
    
    result = SystemHealth(
        overall_status=overall_status,
        timestamp=datetime.now(),
        services=services,
        infrastructure=infrastructure,
        summary=summary
    )
    
    # Update cache
    health_cache = result.dict()
    cache_timestamp = datetime.now()
    
    return result

@app.get("/services", response_model=List[ServiceHealth])
async def get_service_health():
    """Get health status of all microservices."""
    service_tasks = [
        check_service_health(name, url) 
        for name, url in SERVICE_URLS.items()
    ]
    
    results = await asyncio.gather(*service_tasks, return_exceptions=True)
    
    services = []
    for result in results:
        if isinstance(result, ServiceHealth):
            services.append(result)
        else:
            logger.error(f"Service health check failed: {result}")
    
    return services

@app.get("/services/{service_name}", response_model=ServiceHealth)
async def get_specific_service_health(service_name: str):
    """Get health status of a specific service."""
    if service_name not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return await check_service_health(service_name, SERVICE_URLS[service_name])

@app.get("/infrastructure", response_model=Dict[str, ServiceHealth])
async def get_infrastructure_health():
    """Get health status of infrastructure components."""
    tasks = [
        check_database_health(),
        check_kafka_health()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    infrastructure = {}
    for result in results:
        if isinstance(result, ServiceHealth):
            infrastructure[result.name] = result
        else:
            logger.error(f"Infrastructure health check failed: {result}")
    
    return infrastructure

@app.get("/mesh", response_model=List[ServiceMeshTest])
async def test_service_mesh():
    """Test service mesh connectivity and communication patterns."""
    tests = []
    
    # Test 1: Service Discovery
    start_time = time.time()
    try:
        service_results = await get_service_health()
        discovered_services = len([s for s in service_results if s.status == "healthy"])
        
        tests.append(ServiceMeshTest(
            test_name="service_discovery",
            status="passed" if discovered_services > 0 else "failed",
            duration_ms=int((time.time() - start_time) * 1000),
            details={
                "discovered_services": discovered_services,
                "total_services": len(SERVICE_URLS)
            }
        ))
    except Exception as e:
        tests.append(ServiceMeshTest(
            test_name="service_discovery",
            status="failed",
            duration_ms=int((time.time() - start_time) * 1000),
            details={},
            error=str(e)
        ))
    
    # Test 2: Cross-service Communication
    start_time = time.time()
    try:
        # Test training orchestrator to ML engine communication pattern
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get jobs from training orchestrator
            response = await client.get(f"{SERVICE_URLS['training-orchestrator']}/jobs")
            communication_success = response.status_code == 200
        
        tests.append(ServiceMeshTest(
            test_name="cross_service_communication",
            status="passed" if communication_success else "failed",
            duration_ms=int((time.time() - start_time) * 1000),
            details={"test_endpoint": "/jobs", "status_code": response.status_code}
        ))
    except Exception as e:
        tests.append(ServiceMeshTest(
            test_name="cross_service_communication",
            status="failed",
            duration_ms=int((time.time() - start_time) * 1000),
            details={},
            error=str(e)
        ))
    
    # Test 3: Load Balancing (if multiple instances)
    start_time = time.time()
    tests.append(ServiceMeshTest(
        test_name="load_balancing",
        status="skipped",
        duration_ms=int((time.time() - start_time) * 1000),
        details={"reason": "Single instance deployment"}
    ))
    
    return tests

@app.get("/metrics", response_model=Dict[str, Any])
async def get_system_metrics():
    """Get system performance metrics."""
    health_data = await get_system_health()
    
    # Calculate response time statistics
    service_response_times = [
        s.response_time_ms for s in health_data.services 
        if s.response_time_ms is not None
    ]
    
    infrastructure_response_times = [
        i.response_time_ms for i in health_data.infrastructure.values()
        if i.response_time_ms is not None
    ]
    
    all_response_times = service_response_times + infrastructure_response_times
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "uptime_check": {
            "services_up": health_data.summary["healthy_services"],
            "services_total": health_data.summary["total_services"],
            "infrastructure_up": health_data.summary["healthy_infrastructure"],
            "infrastructure_total": health_data.summary["total_infrastructure"],
            "overall_availability": (
                (health_data.summary["healthy_services"] + health_data.summary["healthy_infrastructure"]) /
                (health_data.summary["total_services"] + health_data.summary["total_infrastructure"])
                if (health_data.summary["total_services"] + health_data.summary["total_infrastructure"]) > 0
                else 0
            )
        },
        "performance": {
            "avg_response_time_ms": sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            "min_response_time_ms": min(all_response_times) if all_response_times else 0,
            "max_response_time_ms": max(all_response_times) if all_response_times else 0,
            "total_checks": len(all_response_times)
        },
        "service_breakdown": {
            service.name: {
                "status": service.status,
                "response_time_ms": service.response_time_ms
            } for service in health_data.services
        }
    }
    
    return metrics

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
