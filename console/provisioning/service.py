from typing import List, Optional, Dict, Any, Tuple
from console.provisioning.do_client import DigitalOceanClient
from common.models import Droplet, DropletStatus, AgentStatus
from sqlalchemy.orm import Session
from console.api.models.db_models import DBDroplet
import json
import logging
from console.provisioning.deployer import AgentDeployer
from console.config import settings

logger = logging.getLogger(__name__)

class ProvisioningService:
    def __init__(self, db: Session, do_client: Optional[DigitalOceanClient] = None):
        self.db = db
        self.do_client = do_client or DigitalOceanClient()
    
    def list_droplets(self) -> List[Droplet]:
        """
        List all droplets managed by the system
        """
        db_droplets = self.db.query(DBDroplet).all()
        return [self._convert_to_model(db_droplet) for db_droplet in db_droplets]
    
    def get_droplet(self, droplet_id: str) -> Optional[Droplet]:
        """
        Get a specific droplet by ID
        """
        db_droplet = self.db.query(DBDroplet).filter(DBDroplet.id == droplet_id).first()
        if not db_droplet:
            return None
        return self._convert_to_model(db_droplet)
    
    def create_droplet(self,
                      name: str,
                      region: str,
                      size: str,
                      image: str,
                      ssh_keys: Optional[List[int]] = None,
                      tags: Optional[List[str]] = None) -> Droplet:
        """
        Create a new droplet
        """
        try:
            # Create in DigitalOcean
            droplet = self.do_client.create_droplet(
                name=name,
                region=region,
                size=size,
                image=image,
                ssh_keys=ssh_keys,
                tags=tags
            )
            
            # Create in our database
            db_droplet = DBDroplet(
                id=droplet.id,
                name=droplet.name,
                region=droplet.region,
                size=droplet.size,
                ip_address=droplet.ip_address,
                status=droplet.status.value,
                created_at=droplet.created_at,
                tags=json.dumps(droplet.tags) if droplet.tags else json.dumps([])
            )
            
            self.db.add(db_droplet)
            self.db.commit()
            
            return droplet
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating droplet: {str(e)}")
            raise
    
    def create_multiple_droplets(self,
                               count: int,
                               name_prefix: str,
                               region: str,
                               size: str,
                               image: str,
                               ssh_keys: Optional[List[int]] = None,
                               tags: Optional[List[str]] = None) -> List[Droplet]:
        """
        Create multiple droplets with the same configuration
        """
        droplets = []
        
        try:
            # Create all droplets in DigitalOcean
            for i in range(count):
                droplet_name = f"{name_prefix}-{i+1}"
                droplet = self.do_client.create_droplet(
                    name=droplet_name,
                    region=region,
                    size=size,
                    image=image,
                    ssh_keys=ssh_keys,
                    tags=tags
                )
                
                # Create in our database
                db_droplet = DBDroplet(
                    id=droplet.id,
                    name=droplet.name,
                    region=droplet.region,
                    size=droplet.size,
                    ip_address=droplet.ip_address,
                    status=droplet.status.value,
                    created_at=droplet.created_at,
                    tags=json.dumps(droplet.tags) if droplet.tags else json.dumps([])
                )
                
                self.db.add(db_droplet)
                droplets.append(droplet)
            
            self.db.commit()
            return droplets
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating multiple droplets: {str(e)}")
            raise
    
    def delete_droplet(self, droplet_id: str) -> bool:
        """
        Delete a droplet
        """
        try:
            # Delete from DigitalOcean
            success = self.do_client.delete_droplet(droplet_id)
            if not success:
                return False
            
            # Delete from our database
            db_droplet = self.db.query(DBDroplet).filter(DBDroplet.id == droplet_id).first()
            if db_droplet:
                self.db.delete(db_droplet)
                self.db.commit()
            
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting droplet: {str(e)}")
            return False
    
    def refresh_droplets(self) -> List[Droplet]:
        """
        Refresh droplet information from DigitalOcean
        """
        try:
            # Get all droplets from DigitalOcean
            do_droplets = self.do_client.list_droplets()
            do_droplet_ids = {d.id for d in do_droplets}
            
            # Get all droplets from our database
            db_droplets = self.db.query(DBDroplet).all()
            db_droplet_ids = {d.id for d in db_droplets}
            
            # Update existing droplets
            for do_droplet in do_droplets:
                if do_droplet.id in db_droplet_ids:
                    # Update in database
                    db_droplet = self.db.query(DBDroplet).filter(DBDroplet.id == do_droplet.id).first()
                    db_droplet.status = do_droplet.status.value
                    db_droplet.ip_address = do_droplet.ip_address
                    db_droplet.tags = json.dumps(do_droplet.tags) if do_droplet.tags else json.dumps([])
                else:
                    # Add to database
                    db_droplet = DBDroplet(
                        id=do_droplet.id,
                        name=do_droplet.name,
                        region=do_droplet.region,
                        size=do_droplet.size,
                        ip_address=do_droplet.ip_address,
                        status=do_droplet.status.value,
                        created_at=do_droplet.created_at,
                        tags=json.dumps(do_droplet.tags) if do_droplet.tags else json.dumps([])
                    )
                    self.db.add(db_droplet)
            
            # Remove droplets that no longer exist in DigitalOcean
            for db_id in db_droplet_ids - do_droplet_ids:
                db_droplet = self.db.query(DBDroplet).filter(DBDroplet.id == db_id).first()
                if db_droplet:
                    self.db.delete(db_droplet)
            
            self.db.commit()
            
            # Return updated list
            return [self._convert_to_model(d) for d in self.db.query(DBDroplet).all()]
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error refreshing droplets: {str(e)}")
            raise
    
    def _convert_to_model(self, db_droplet: DBDroplet) -> Droplet:
        """
        Convert database model to API model
        """
        return Droplet(
            id=db_droplet.id,
            name=db_droplet.name,
            region=db_droplet.region,
            size=db_droplet.size,
            ip_address=db_droplet.ip_address,
            status=DropletStatus(db_droplet.status),
            created_at=db_droplet.created_at,
            tags=json.loads(db_droplet.tags) if db_droplet.tags else []
        )
    
    def deploy_agent(self, droplet_id: str, ssh_key_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deploy agent to a droplet
        """
        # Get droplet
        droplet = self.get_droplet(droplet_id)
        if not droplet:
            return False, f"Droplet {droplet_id} not found"

        # Check if droplet is active
        if droplet.status != DropletStatus.ACTIVE:
            return False, f"Droplet {droplet_id} is not active"

        # Deployer
        deployer = AgentDeployer(
            console_url=f"http://{settings.API_HOST}:{settings.API_PORT}",
            rabbitmq_url=settings.RABBITMQ_URL
        )

        # Deploy agent
        success, message = deployer.deploy_agent(droplet.ip_address, ssh_key_path)

        if success:
            # Update agent status in database
            db_droplet = self.db.query(DBDroplet).filter(DBDroplet.id == droplet_id).first()
            if db_droplet:
                db_droplet.agent_status = AgentStatus.INSTALLING.value
                self.db.commit()

        return success, message