import subprocess
import shlex
import os
import signal
import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

class CommandExecutor:
    def __init__(self):
        self.processes = {}
        self.results = {}
        self.lock = threading.Lock()
    
    def execute(self, command_id: str, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute a command and return the result
        """
        with self.lock:
            if command_id in self.processes:
                return {"status": "error", "message": f"Command {command_id} is already running"}
        
        try:
            # Split command safely
            args = shlex.split(command)
            
            # Start process
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid
            )
            
            with self.lock:
                self.processes[command_id] = process
            
            # Start monitoring thread
            threading.Thread(
                target=self._monitor_process,
                args=(command_id, process, timeout),
                daemon=True
            ).start()
            
            return {"status": "started", "command_id": command_id}
            
        except Exception as e:
            logger.error(f"Error executing command {command_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _monitor_process(self, command_id: str, process: subprocess.Popen, timeout: Optional[int] = None):
        """
        Monitor process execution and collect results
        """
        start_time = time.time()
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            
            result = {
                "status": "completed",
                "command_id": command_id,
                "exit_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": time.time() - start_time
            }
            
        except subprocess.TimeoutExpired:
            # Kill the process group
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.terminate()
            except:
                pass
            
            stdout, stderr = process.communicate()
            
            result = {
                "status": "timeout",
                "command_id": command_id,
                "exit_code": -1,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error monitoring process {command_id}: {e}")
            
            result = {
                "status": "error",
                "command_id": command_id,
                "message": str(e),
                "execution_time": time.time() - start_time
            }
        
        # Store result and clean up
        with self.lock:
            self.results[command_id] = result
            if command_id in self.processes:
                del self.processes[command_id]
    
    def get_result(self, command_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a command
        """
        with self.lock:
            return self.results.get(command_id)
    
    def abort(self, command_id: str) -> bool:
        """
        Abort a running command
        """
        with self.lock:
            if command_id not in self.processes:
                return False
            
            process = self.processes[command_id]
        
        try:
            # Kill the process group
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.terminate()
            return True
        except Exception as e:
            logger.error(f"Error aborting command {command_id}: {e}")
            return False
    
    def abort_all(self) -> List[str]:
        """
        Abort all running commands
        """
        aborted = []
        
        with self.lock:
            command_ids = list(self.processes.keys())
        
        for command_id in command_ids:
            if self.abort(command_id):
                aborted.append(command_id)
        
        return aborted