"""Aggregate API routers."""

from fastapi import APIRouter

from app.api.routes import deliveries, health, ingestions, metrics

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(deliveries.router)
api_router.include_router(ingestions.router)
