from fastapi import APIRouter, Response
from monitoring.prometheus_exporter import PrometheusMetricsExporter
from datetime import datetime

# Global exporter instance for the API to use
exporter = PrometheusMetricsExporter()

router = APIRouter(prefix="/metrics", tags=["monitoring"])

@router.get("/prometheus")
async def get_metrics():
    """Endpoint for Prometheus scraper"""
    return Response(content=exporter.get_metrics(), media_type="text/plain")

@router.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now().isoformat(),
        "version": "9.1.5"
    }
