from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from console.database import get_db
from console.provisioning.service import ProvisioningService
from common.models import Droplet
from pydantic import BaseModel

router = APIRouter()

class DropletCreate(BaseModel):
    name: str
    region: str
    size: str
    image: str
    ssh_keys: Optional[List[int]] = None
    tags: Optional[List[str]] = None

class BatchDropletCreate(BaseModel):
    count: int
    name_prefix: str
    region: str
    size: str
    image: str
    ssh_keys: Optional[List[int]] = None
    tags: Optional[List[str]] = None

@router.get("/", response_model=List[Droplet])
async def list_droplets(db: Session = Depends(get_db)):
    """
    List all managed droplets
    """
    service = ProvisioningService(db)
    return service.list_droplets()

@router.get("/refresh", response_model=List[Droplet])
async def refresh_droplets(db: Session = Depends(get_db)):
    """
    Refresh droplet information from DigitalOcean
    """
    service = ProvisioningService(db)
    return service.refresh_droplets()

@router.get("/{droplet_id}", response_model=Droplet)
async def get_droplet(droplet_id: str, db: Session = Depends(get_db)):
    """
    Get a specific droplet by ID
    """
    service = ProvisioningService(db)
    droplet = service.get_droplet(droplet_id)
    if not droplet:
        raise HTTPException(status_code=404, detail="Droplet not found")
    return droplet

@router.post("/", response_model=Droplet)
async def create_droplet(droplet: DropletCreate, db: Session = Depends(get_db)):
    """
    Create a new droplet
    """
    service = ProvisioningService(db)
    try:
        return service.create_droplet(
            name=droplet.name,
            region=droplet.region,
            size=droplet.size,
            image=droplet.image,
            ssh_keys=droplet.ssh_keys,
            tags=droplet.tags
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch", response_model=List[Droplet])
async def create_multiple_droplets(batch: BatchDropletCreate, db: Session = Depends(get_db)):
    """
    Create multiple droplets with the same configuration
    """
    service = ProvisioningService(db)
    try:
        return service.create_multiple_droplets(
            count=batch.count,
            name_prefix=batch.name_prefix,
            region=batch.region,
            size=batch.size,
            image=batch.image,
            ssh_keys=batch.ssh_keys,
            tags=batch.tags
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{droplet_id}", response_model=bool)
async def delete_droplet(droplet_id: str, db: Session = Depends(get_db)):
    """
    Delete a droplet
    """
    service = ProvisioningService(db)
    success = service.delete_droplet(droplet_id)
    if not success:
        raise HTTPException(status_code=404, detail="Droplet could not be deleted")
    return success