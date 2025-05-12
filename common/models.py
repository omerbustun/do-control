from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DropletStatus(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    OFFLINE = "offline"
    DELETING = "deleting"
    ERROR = "error"


class AgentStatus(str, Enum):
    UNINSTALLED = "uninstalled"
    INSTALLING = "installing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class Droplet(BaseModel):
    id: str
    name: str
    region: str
    size: str
    ip_address: str
    status: DropletStatus
    created_at: datetime
    tags: List[str] = []
    agent_status: Optional[AgentStatus] = None


class TestConfiguration(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    command: str
    parameters: Dict[str, Any] = {}
    target_droplets: List[str]
    duration: Optional[int] = None
    created_at: datetime
    created_by: str


class TestExecution(BaseModel):
    id: str
    config_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    droplet_results: Optional[Dict[str, Dict[str, Any]]] = None