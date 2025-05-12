from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from console.database import get_db
from console.orchestration.service import OrchestrationService
from common.models import TestConfiguration, TestExecution
from pydantic import BaseModel

router = APIRouter()

class TestConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    command: str
    parameters: dict = {}
    target_droplets: List[str] = []
    duration: Optional[int] = None
    created_by: str

@router.post("/", response_model=TestConfiguration)
async def create_test_config(config: TestConfigCreate, db: Session = Depends(get_db)):
    """Create a new test configuration"""
    service = OrchestrationService(db)
    
    # Convert to model
    test_config = TestConfiguration(
        id=None,  # Will be generated
        name=config.name,
        description=config.description,
        command=config.command,
        parameters=config.parameters,
        target_droplets=config.target_droplets,
        duration=config.duration,
        created_at=datetime.utcnow(),
        created_by=config.created_by
    )
    
    return service.create_test_config(test_config)

@router.get("/", response_model=List[TestConfiguration])
async def list_test_configs(db: Session = Depends(get_db)):
    """List all test configurations"""
    service = OrchestrationService(db)
    return service.list_test_configs()

@router.get("/{config_id}", response_model=TestConfiguration)
async def get_test_config(config_id: str, db: Session = Depends(get_db)):
    """Get a test configuration by ID"""
    service = OrchestrationService(db)
    config = service.get_test_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Test configuration not found")
    return config

@router.post("/{config_id}/execute", response_model=TestExecution)
async def execute_test(config_id: str, db: Session = Depends(get_db)):
    """Execute a test based on its configuration"""
    service = OrchestrationService(db)
    try:
        return service.execute_test(config_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/", response_model=List[TestExecution])
async def list_executions(db: Session = Depends(get_db)):
    """List all test executions"""
    service = OrchestrationService(db)
    return service.list_executions()

@router.get("/executions/{execution_id}", response_model=TestExecution)
async def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """Get a test execution by ID"""
    service = OrchestrationService(db)
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Test execution not found")
    return execution

@router.post("/executions/{execution_id}/abort", response_model=bool)
async def abort_execution(execution_id: str, db: Session = Depends(get_db)):
    """Abort a running test execution"""
    service = OrchestrationService(db)
    success = service.abort_execution(execution_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cannot abort execution")
    return success