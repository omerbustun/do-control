import paramiko
import os
import logging
from typing import Dict, Any, Optional, Tuple
import tempfile
import time

logger = logging.getLogger(__name__)

AGENT_SETUP_SCRIPT = """#!/bin/bash
# Setup script for DO-Control Agent

# Install dependencies
apt-get update
apt-get install -y python3 python3-pip

# Create agent directory
mkdir -p /opt/do-control-agent

# Install Python dependencies
pip3 install pika psutil requests

# Create agent service
cat > /etc/systemd/system/do-control-agent.service << 'EOL'
[Unit]
Description=DO-Control Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/do-control-agent
ExecStart=/usr/bin/python3 /opt/do-control-agent/main.py
Restart=always
Environment=CONSOLE_URL={console_url}
Environment=RABBITMQ_URL={rabbitmq_url}

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl daemon-reload
systemctl enable do-control-agent
systemctl start do-control-agent

echo "DO-Control Agent installed successfully"
"""

class AgentDeployer:
    def __init__(self, console_url: str, rabbitmq_url: str):
        self.console_url = console_url
        self.rabbitmq_url = rabbitmq_url
    
    def deploy_agent(self, ip_address: str, ssh_key_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deploy the agent to a droplet
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Connect to the droplet
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if ssh_key_path:
                private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
                client.connect(ip_address, username="root", pkey=private_key)
            else:
                # Assume SSH agent forwarding is set up
                client.connect(ip_address, username="root")
            
            # Create setup script
            script_content = AGENT_SETUP_SCRIPT.format(
                console_url=self.console_url,
                rabbitmq_url=self.rabbitmq_url
            )
            
            # Create temporary file for script
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
                temp.write(script_content)
                temp_path = temp.name
            
            # Upload the setup script
            sftp = client.open_sftp()
            remote_path = "/tmp/setup_agent.sh"
            sftp.put(temp_path, remote_path)
            os.unlink(temp_path)  # Remove temporary file
            
            # Make script executable
            stdin, stdout, stderr = client.exec_command(f"chmod +x {remote_path}")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                return False, f"Failed to make script executable: {stderr.read().decode()}"
            
            # Upload agent code
            self._upload_agent_code(sftp)
            
            # Execute the script
            stdin, stdout, stderr = client.exec_command(f"bash {remote_path}")
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                return False, f"Failed to execute setup script: {stderr.read().decode()}"
            
            # Clean up
            client.exec_command(f"rm {remote_path}")
            
            # Close connections
            sftp.close()
            client.close()
            
            return True, "Agent deployed successfully"
            
        except Exception as e:
            logger.error(f"Error deploying agent to {ip_address}: {e}")
            return False, f"Error deploying agent: {str(e)}"
    
    def _upload_agent_code(self, sftp):
        """
        Upload agent code to the droplet
        """
        # Define the agent files to upload
        # In a real implementation, you'd package all agent code
        # Here we just create a simple main.py for demo purposes
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp:
            temp.write("""
import os
import time
import uuid
import socket
import json
import requests

# Basic agent implementation for demo
agent_id = str(uuid.uuid4())
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

console_url = os.environ.get("CONSOLE_URL")
rabbitmq_url = os.environ.get("RABBITMQ_URL")

print(f"Starting agent {agent_id} on {hostname} ({ip_address})")
print(f"Console URL: {console_url}")
print(f"RabbitMQ URL: {rabbitmq_url}")

# Register with console
try:
    response = requests.post(
        f"{console_url}/api/v1/agents/register",
        json={
            "id": agent_id,
            "hostname": hostname,
            "ip_address": ip_address
        }
    )
    print(f"Registration response: {response.status_code}")
except Exception as e:
    print(f"Error registering: {e}")

# Keep agent running
while True:
    time.sleep(10)
    print("Agent still running...")
""")
            temp_path = temp.name
        
        # Upload the file
        sftp.put(temp_path, "/opt/do-control-agent/main.py")
        os.unlink(temp_path)  # Remove temporary file