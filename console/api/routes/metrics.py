from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from console.database import get_db
from console.monitoring.service import MonitoringService

router = APIRouter()

@router.get("/droplets/{agent_id}")
async def get_agent_metrics(agent_id: str, lookback_minutes: int = 5, db: Session = Depends(get_db)):
    """Get recent metrics for an agent/droplet"""
    service = MonitoringService(db)
    return service.get_agent_metrics(agent_id, lookback_minutes)

@router.get("/executions/{execution_id}")
async def get_execution_metrics(execution_id: str, db: Session = Depends(get_db)):
    """Get metrics for a specific test execution"""
    service = MonitoringService(db)
    return service.get_execution_metrics(execution_id)

@router.get("/live")
async def get_live_metrics(db: Session = Depends(get_db)):
    """Get live metrics for all agents"""
    service = MonitoringService(db)
    # Collect recent metrics for all agents in buffer
    result = {}
    for agent_id in service.metrics_buffer.keys():
        metrics = service.get_agent_metrics(agent_id, lookback_minutes=1)
        if metrics:
            result[agent_id] = metrics[-1]  # Get most recent metrics
    return result