import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import json

from console.provisioning.service import ProvisioningService
from console.api.models.db_models import DBDroplet
from common.models import Droplet, DropletStatus

@pytest.fixture
def mock_do_client():
    mock = Mock()
    return mock

@pytest.fixture
def provisioning_service(test_db, mock_do_client):
    return ProvisioningService(test_db, mock_do_client)

def test_list_droplets(provisioning_service, test_db):
    # Setup: Add some test droplets to the DB
    db_droplet = DBDroplet(
        id="123",
        name="test-droplet",
        region="nyc1",
        size="s-1vcpu-1gb",
        ip_address="192.168.1.1",
        status="active",
        created_at=datetime.utcnow(),
        tags=json.dumps(["test"])
    )
    test_db.add(db_droplet)
    test_db.commit()
    
    # Test
    droplets = provisioning_service.list_droplets()
    
    # Assert
    assert len(droplets) == 1
    assert droplets[0].id == "123"
    assert droplets[0].name == "test-droplet"
    assert droplets[0].status == DropletStatus.ACTIVE

def test_create_droplet(provisioning_service, mock_do_client, test_db):
    # Setup: Mock DO client create_droplet response
    mock_droplet = Droplet(
        id="456",
        name="new-droplet",
        region="nyc1",
        size="s-1vcpu-1gb",
        ip_address="192.168.1.2",
        status=DropletStatus.ACTIVE,
        created_at=datetime.utcnow(),
        tags=["test"]
    )
    mock_do_client.create_droplet.return_value = mock_droplet
    
    # Test
    result = provisioning_service.create_droplet(
        name="new-droplet",
        region="nyc1",
        size="s-1vcpu-1gb",
        image="ubuntu-20-04-x64",
        ssh_keys=[12345],
        tags=["test"]
    )
    
    # Assert
    mock_do_client.create_droplet.assert_called_once()
    assert result.id == "456"
    assert result.name == "new-droplet"
    
    # Verify DB entry was created
    db_droplet = test_db.query(DBDroplet).filter(DBDroplet.id == "456").first()
    assert db_droplet is not None
    assert db_droplet.name == "new-droplet"