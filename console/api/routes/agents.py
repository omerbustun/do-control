from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel

from console.database import get_db
from console.api.models.db_models import DBDroplet
from common.models import AgentStatus

router = APIRouter()

class AgentRegistration(BaseModel):
    id: str
    hostname: str
    ip_address: str

@router.post("/register")
async def register_agent(registration: AgentRegistration, db: Session = Depends(get_db)):
    """
    Register an agent with the console
    """
    # Find droplet by IP address
    db_droplet = db.query(DBDroplet).filter(DBDroplet.ip_address == registration.ip_address).first()
    
    if db_droplet:
        # Update agent status
        db_droplet.agent_status = AgentStatus.READY.value
        db.commit()
        return {"status": "success", "droplet_id": db_droplet.id}
    else:
        # Create new entry for unknown agent
        db_droplet = DBDroplet(
            id=registration.id,
            name=registration.hostname,
            region="unknown",
            size="unknown",
            ip_address=registration.ip_address,
            status="active",
            created_at=datetime.utcnow(),
            agent_status=AgentStatus.READY.value
        )
        db.add(db_droplet)
        db.commit()
        return {"status": "success", "droplet_id": registration.id}