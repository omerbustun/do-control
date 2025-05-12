from pydo import Client
from typing import List, Dict, Any, Optional
from console.config import settings
from common.models import Droplet, DropletStatus
from datetime import datetime
import os


class DigitalOceanClient:
    def __init__(self, api_token: Optional[str] = None):
        self.token = api_token or settings.DO_API_TOKEN
        if not self.token:
            raise ValueError("DigitalOcean API token is required")
        self.client = Client(token=self.token)
    
    def list_droplets(self) -> List[Droplet]:
        result = self.client.droplets.list()
        return [self._convert_droplet(d) for d in result["droplets"]]
    
    def get_droplet(self, droplet_id: str) -> Optional[Droplet]:
        try:
            result = self.client.droplets.get(droplet_id=droplet_id)
            return self._convert_droplet(result["droplet"])
        except Exception:
            return None
    
    def create_droplet(self, 
                      name: str, 
                      region: str, 
                      size: str, 
                      image: str, 
                      ssh_keys: Optional[List[int]] = None,
                      tags: Optional[List[str]] = None) -> Droplet:
        
        payload = {
            "name": name,
            "region": region,
            "size": size,
            "image": image,
            "ssh_keys": ssh_keys or [],
            "tags": tags or []
        }
        
        result = self.client.droplets.create(**payload)
        return self._convert_droplet(result["droplet"])
    
    def create_multiple_droplets(self, 
                                count: int,
                                name_prefix: str,
                                region: str,
                                size: str,
                                image: str,
                                ssh_keys: Optional[List[int]] = None,
                                tags: Optional[List[str]] = None) -> List[Droplet]:
        
        droplets = []
        for i in range(count):
            droplet_name = f"{name_prefix}-{i+1}"
            droplet = self.create_droplet(
                name=droplet_name,
                region=region,
                size=size,
                image=image,
                ssh_keys=ssh_keys,
                tags=tags
            )
            droplets.append(droplet)
        
        return droplets
    
    def delete_droplet(self, droplet_id: str) -> bool:
        try:
            self.client.droplets.delete(droplet_id=droplet_id)
            return True
        except Exception:
            return False
    
    def _convert_droplet(self, do_droplet: Dict[str, Any]) -> Droplet:
        # Get the IP address - prefer public IPv4
        ip_address = "0.0.0.0"
        
        if "networks" in do_droplet and "v4" in do_droplet["networks"]:
            v4_networks = do_droplet["networks"]["v4"]
            for network in v4_networks:
                if network.get("type") == "public":
                    ip_address = network.get("ip_address")
                    break
            
            # If no public IP, use private IP
            if ip_address == "0.0.0.0" and v4_networks:
                ip_address = v4_networks[0].get("ip_address")
        
        # Map DigitalOcean status to our status enum
        status_map = {
            "new": DropletStatus.CREATING,
            "active": DropletStatus.ACTIVE,
            "off": DropletStatus.OFFLINE,
            "archive": DropletStatus.DELETING
        }
        
        status = status_map.get(do_droplet.get("status", ""), DropletStatus.ERROR)
        
        return Droplet(
            id=str(do_droplet["id"]),
            name=do_droplet["name"],
            region=do_droplet["region"]["slug"] if isinstance(do_droplet.get("region"), dict) else do_droplet.get("region", ""),
            size=do_droplet.get("size_slug", do_droplet.get("size", "")),
            ip_address=ip_address,
            status=status,
            created_at=datetime.fromisoformat(do_droplet["created_at"]) if "created_at" in do_droplet else datetime.utcnow(),
            tags=do_droplet.get("tags", [])
        )