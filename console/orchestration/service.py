from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import logging
from sqlalchemy.orm import Session

from console.api.models.db_models import DBTestConfiguration, DBTestExecution, DBDroplet
from console.messaging.service import MessagingService
from common.models import TestConfiguration, TestExecution, ExecutionStatus

logger = logging.getLogger(__name__)

class OrchestrationService:
    def __init__(self, db: Session, messaging_service: Optional[MessagingService] = None):
        self.db = db
        self.messaging_service = messaging_service or MessagingService()
    
    def create_test_config(self, config: TestConfiguration) -> TestConfiguration:
        """Create a new test configuration"""
        db_config = DBTestConfiguration(
            id=config.id or str(uuid.uuid4()),
            name=config.name,
            description=config.description,
            command=config.command,
            parameters=json.dumps(config.parameters),
            target_droplets=json.dumps(config.target_droplets),
            duration=config.duration,
            created_at=config.created_at or datetime.utcnow(),
            created_by=config.created_by
        )
        
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        
        return self._convert_config_to_model(db_config)
    
    def get_test_config(self, config_id: str) -> Optional[TestConfiguration]:
        """Get a test configuration by ID"""
        db_config = self.db.query(DBTestConfiguration).filter(DBTestConfiguration.id == config_id).first()
        if not db_config:
            return None
        return self._convert_config_to_model(db_config)
    
    def list_test_configs(self) -> List[TestConfiguration]:
        """List all test configurations"""
        db_configs = self.db.query(DBTestConfiguration).all()
        return [self._convert_config_to_model(c) for c in db_configs]
    
    def execute_test(self, config_id: str) -> TestExecution:
        """Execute a test based on its configuration"""
        config = self.get_test_config(config_id)
        if not config:
            raise ValueError(f"Test configuration {config_id} not found")
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution = DBTestExecution(
            id=execution_id,
            config_id=config_id,
            status=ExecutionStatus.PREPARING.value,
            start_time=datetime.utcnow()
        )
        
        self.db.add(execution)
        self.db.commit()
        
        # Prepare command for distribution
        command = {
            "command_id": str(uuid.uuid4()),
            "execution_id": execution_id,
            "command_type": "prepare",
            "command": config.command,
            "parameters": config.parameters,
            "target_droplets": config.target_droplets,
            "duration": config.duration,
            "preparation_time": 10,  # Allow 10 seconds for preparation
            "execution_time": None  # Will be set when all agents are ready
        }
        
        # Distribute command to target agents
        if config.target_droplets:
            for agent_id in config.target_droplets:
                # Check if droplet exists
                droplet = self.db.query(DBDroplet).filter(DBDroplet.id == agent_id).first()
                if not droplet:
                    logger.warning(f"Target droplet {agent_id} not found, skipping")
                    continue
                
                self.messaging_service.send_direct_command(agent_id, command)
        else:
            # Broadcast to all agents
            self.messaging_service.send_command(command)
        
        return self._convert_execution_to_model(execution)
    
    def get_execution(self, execution_id: str) -> Optional[TestExecution]:
        """Get test execution status by ID"""
        db_execution = self.db.query(DBTestExecution).filter(DBTestExecution.id == execution_id).first()
        if not db_execution:
            return None
        return self._convert_execution_to_model(db_execution)
    
    def list_executions(self) -> List[TestExecution]:
        """List all test executions"""
        db_executions = self.db.query(DBTestExecution).all()
        return [self._convert_execution_to_model(e) for e in db_executions]
    
    def abort_execution(self, execution_id: str) -> bool:
        """Abort a running test execution"""
        db_execution = self.db.query(DBTestExecution).filter(DBTestExecution.id == execution_id).first()
        if not db_execution:
            return False
        
        if db_execution.status not in [ExecutionStatus.PREPARING.value, ExecutionStatus.RUNNING.value]:
            return False
        
        # Update status
        db_execution.status = ExecutionStatus.ABORTED.value
        db_execution.end_time = datetime.utcnow()
        self.db.commit()
        
        # Send abort command
        command = {
            "command_id": str(uuid.uuid4()),
            "execution_id": execution_id,
            "command_type": "abort"
        }
        
        self.messaging_service.send_command(command)
        return True
    
    def _convert_config_to_model(self, db_config: DBTestConfiguration) -> TestConfiguration:
        """Convert database model to API model"""
        return TestConfiguration(
            id=db_config.id,
            name=db_config.name,
            description=db_config.description,
            command=db_config.command,
            parameters=json.loads(db_config.parameters) if db_config.parameters else {},
            target_droplets=json.loads(db_config.target_droplets) if db_config.target_droplets else [],
            duration=db_config.duration,
            created_at=db_config.created_at,
            created_by=db_config.created_by
        )
    
    def _convert_execution_to_model(self, db_execution: DBTestExecution) -> TestExecution:
        """Convert database model to API model"""
        return TestExecution(
            id=db_execution.id,
            config_id=db_execution.config_id,
            status=ExecutionStatus(db_execution.status),
            start_time=db_execution.start_time,
            end_time=db_execution.end_time,
            results=json.loads(db_execution.results) if db_execution.results else None
        )