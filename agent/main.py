import os
import sys

# Add the parent directory to the path so we can import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
import json
import socket
import uuid
import threading
import requests
from typing import Dict, Any, Optional
from agent.executor.command import CommandExecutor
from common.synchronization import TimeSynchronizer
from common.messaging import MessageBroker, TopicType
from common.models import AgentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("do-control-agent")

class Agent:
    def __init__(self, console_url: str, kafka_bootstrap_servers: str,
                 kafka_security_protocol: str = "PLAINTEXT",
                 kafka_sasl_mechanism: str = "PLAIN",
                 kafka_sasl_username: str = "",
                 kafka_sasl_password: str = ""):
        self.console_url = console_url
        self.id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        self.time_sync = TimeSynchronizer()
        self.time_sync.sync()  # Initial sync
        
        # Initialize messaging
        self.broker = MessageBroker(
            bootstrap_servers=kafka_bootstrap_servers,
            security_protocol=kafka_security_protocol,
            sasl_mechanism=kafka_sasl_mechanism,
            sasl_username=kafka_sasl_username,
            sasl_password=kafka_sasl_password
        )
        
        # Agent state
        self.status = AgentStatus.READY
        self.current_execution = None
        
        # Initialize the command executor
        self.executor = CommandExecutor()
        self.current_execution = None
        
    def start(self) -> None:
        """Start the agent"""
        logger.info(f"Starting agent {self.id} on {self.hostname} ({self.ip_address})")
        
        # Register with console
        self._register_with_console()
        
        # Set up messaging
        self._setup_messaging()
        
        # Start metrics collection
        self._start_metrics_collection()
        
        # Keep agent running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down agent...")
            self.broker.close()
            
    def _register_with_console(self) -> None:
        """Register agent with the console"""
        try:
            response = requests.post(
                f"{self.console_url}/api/v1/agents/register",
                json={
                    "id": self.id,
                    "hostname": self.hostname,
                    "ip_address": self.ip_address
                }
            )
            response.raise_for_status()
            logger.info("Successfully registered with console")
        except Exception as e:
            logger.error(f"Failed to register with console: {e}")
            raise
            
    def _setup_messaging(self) -> None:
        """Set up messaging and start listening"""
        # Start consuming commands
        self.broker.start_consuming_in_thread(
            topic=TopicType.COMMANDS,
            group_id=f"agent-{self.id}",
            callback=self._handle_command,
            auto_commit=False
        )
        
    def _handle_command(self, key: str, message: Dict[str, Any]) -> None:
        """Handle incoming command"""
        try:
            # Only process commands if they are broadcast or specifically for this agent
            if key != "broadcast" and key != self.id:
                return
                
            logger.info(f"Received command: {message}")
            
            command_type = message.get('command_type')
            
            # Update status
            self._send_status(AgentStatus.BUSY)
            self.current_command = message
            
            # Process based on command type
            if command_type == 'execute':
                self._execute_command(message)
            elif command_type == 'prepare':
                self._prepare_execution(message)
            elif command_type == 'start':
                self._start_execution(message)
            elif command_type == 'abort':
                self._abort_execution()
            else:
                logger.warning(f"Unknown command type: {command_type}")
                
            # Return to ready
            self.current_command = None
            self._send_status(AgentStatus.READY)
            
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            self._send_status(AgentStatus.ERROR, {"error": str(e)})
            
    def _execute_command(self, command: Dict[str, Any]) -> None:
        """Execute a command directly"""
        command_id = command.get('command_id')
        cmd = command.get('command')
        timeout = command.get('timeout')

        if not cmd:
            logger.error(f"Invalid command, missing 'command' field: {command}")
            return

        # Execute command
        result = self.executor.execute(command_id, cmd, timeout)

        # Send status update
        status_details = {"command_id": command_id, "execution_status": result["status"]}
        if "message" in result:
            status_details["message"] = result["message"]

        self._send_status(AgentStatus.BUSY, status_details)

        # If execution is successful, wait for it to complete
        if result["status"] == "started":
            # Wait for result
            while True:
                time.sleep(1)
                result = self.executor.get_result(command_id)
                if result:
                    break
                
            # Send result
            self._send_command_result(command_id, result)
            
    def _send_command_result(self, command_id: str, result: Dict[str, Any]) -> None:
        """Send command execution result"""
        message = {
            "agent_id": self.id,
            "command_id": command_id,
            "timestamp": self.time_sync.get_synchronized_time(),
            "result": result
        }
        
        self.broker.publish(
            topic=TopicType.STATUS,
            key=f"agent.{self.id}.result",
            message=message
        )
        
    def _send_status(self, status: AgentStatus, details: Optional[Dict[str, Any]] = None) -> None:
        """Send status update to console"""
        self.status = status
        
        message = {
            "agent_id": self.id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "status": status.value,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        self.broker.publish(
            topic=TopicType.STATUS,
            key=f"agent.{self.id}.status",
            message=message
        )
        
    def _collect_metrics(self) -> None:
        """Collect and send system metrics"""
        while True:
            try:
                # Collect basic system metrics
                metrics = {
                    "cpu_percent": self._get_cpu_percent(),
                    "memory_percent": self._get_memory_percent(),
                    "disk_percent": self._get_disk_percent(),
                    "network": self._get_network_stats()
                }
                
                # Send metrics
                self.broker.publish(
                    topic=TopicType.METRICS,
                    key=f"metrics.system.{self.id}",
                    message={
                        "agent_id": self.id,
                        "timestamp": time.time(),
                        "metrics": metrics
                    }
                )
                
                time.sleep(5)  # Collect every 5 seconds
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                time.sleep(10)  # Longer delay on error
                
    def _start_metrics_collection(self) -> None:
        """Start metrics collection in a background thread"""
        thread = threading.Thread(target=self._collect_metrics, daemon=True)
        thread.start()

    def _prepare_execution(self, command: Dict[str, Any]) -> None:
        """
        Prepare for test execution
        """
        command_id = command.get('command_id')
        execution_id = command.get('execution_id')
        execution_time = command.get('execution_time')

        if not execution_time:
            logger.error(f"Invalid command, missing execution_time: {command}")
            return

        # Re-sync time
        self.time_sync.sync()

        # Store execution details
        self.current_execution = {
            'command_id': command_id,
            'execution_id': execution_id,
            'command': command.get('command'),
            'parameters': command.get('parameters', {}),
            'execution_time': execution_time
        }

        # Report readiness
        self._send_status(AgentStatus.READY, {
            "execution_id": execution_id,
            "command_id": command_id,
            "ready": True
        })

        # Schedule execution
        current_time = self.time_sync.get_synchronized_time()
        delay = execution_time - current_time

        if delay > 0:
            logger.info(f"Scheduled execution in {delay:.3f} seconds")
            threading.Timer(delay, self._start_scheduled_execution).start()
        else:
            logger.warning(f"Execution time already passed, executing immediately")
            self._start_scheduled_execution()

    def _start_scheduled_execution(self) -> None:
        """
        Start a scheduled test execution
        """
        if not self.current_execution:
            logger.error("No execution prepared")
            return

        execution_id = self.current_execution.get('execution_id')
        command_id = self.current_execution.get('command_id')
        command = self.current_execution.get('command')

        # Update status
        self._send_status(AgentStatus.BUSY, {
            "execution_id": execution_id,
            "command_id": command_id,
            "executing": True,
            "start_time": self.time_sync.get_synchronized_time()
        })

        # Execute the command
        result = self.executor.execute(
            command_id, 
            command, 
            self.current_execution.get('parameters', {}).get('timeout')
        )

        # Send initial status
        status_details = {
            "execution_id": execution_id,
            "command_id": command_id,
            "execution_status": result["status"]
        }
        if "message" in result:
            status_details["message"] = result["message"]

        self._send_status(AgentStatus.BUSY, status_details)

        # If execution is successful, wait for it to complete
        if result["status"] == "started":
            # Wait for result
            while True:
                time.sleep(1)
                result = self.executor.get_result(command_id)
                if result:
                    break
                
            # Send result
            self._send_command_result(command_id, result)

        # Clear current execution
        self.current_execution = None
        self._send_status(AgentStatus.READY)
        
    def _start_execution(self, command: Dict[str, Any]) -> None:
        """
        Start test execution
        """
        # Implementation will go here
        pass
        
    def _abort_execution(self) -> None:
        """
        Abort current execution
        """
        # Implementation will go here
        pass
        
    def _get_cpu_percent(self) -> float:
        # Simple implementation for now
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0
            
    def _get_memory_percent(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
            
    def _get_disk_percent(self) -> float:
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return 0.0
            
    def _get_network_stats(self) -> Dict[str, Any]:
        # Simple placeholder
        return {
            "bytes_sent": 0,
            "bytes_recv": 0
        }

if __name__ == "__main__":
    # Get configuration from environment
    console_url = os.environ.get("CONSOLE_URL", "http://localhost:8000")
    kafka_bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_security_protocol = os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    kafka_sasl_mechanism = os.environ.get("KAFKA_SASL_MECHANISM", "PLAIN")
    kafka_sasl_username = os.environ.get("KAFKA_SASL_USERNAME", "")
    kafka_sasl_password = os.environ.get("KAFKA_SASL_PASSWORD", "")
    
    # Create and start agent
    agent = Agent(
        console_url=console_url,
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        kafka_security_protocol=kafka_security_protocol,
        kafka_sasl_mechanism=kafka_sasl_mechanism,
        kafka_sasl_username=kafka_sasl_username,
        kafka_sasl_password=kafka_sasl_password
    )
    agent.start()