import asyncio
import os
from pathlib import Path
from typing import Optional

import asyncssh
from app.exceptions import ToolError
from app.tool.base import BaseTool, CLIResult, ToolResult


_SSH_DESCRIPTION = """Execute commands on a remote host via SSH.
* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file.
* Interactive: If a command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call with an empty `command` to retrieve additional logs.
* Timeout: If a command execution result says "Command timed out", the assistant should retry running the command in the background.
"""


class _SSHSession:
    """A session of an SSH connection."""

    _started: bool
    _connection: Optional[asyncssh.SSHClientConnection]
    _host: str
    _private_key: str

    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self, host: str, private_key: str):
        self._started = False
        self._timed_out = False
        self._connection = None
        self._host = host
        self._private_key = private_key

    async def start(self):
        if self._started:
            return

        try:
            self._connection = await asyncssh.connect(
                self._host,
                client_keys=[self._private_key],
                known_hosts=None,  # In production, you should verify known hosts
            )
            self._started = True
        except Exception as e:
            raise ToolError(f"Failed to connect to {self._host}: {str(e)}")

    def stop(self):
        """Close the SSH connection."""
        if not self._started or not self._connection:
            raise ToolError("Session has not started.")
        self._connection.close()
        self._started = False

    async def run(self, command: str):
        """Execute a command on the remote host."""
        if not self._started or not self._connection:
            raise ToolError("Session has not started.")

        if self._timed_out:
            raise ToolError(
                f"timed out: command has not returned in {self._timeout} seconds and must be retried",
            )

        try:
            async with asyncio.timeout(self._timeout):
                # Execute command using the correct asyncssh API
                process = await self._connection.create_process(
                    f"{command}; echo '{self._sentinel}'",
                    encoding="utf-8",
                )
                
                # Gather stdout and stderr
                stdout, stderr = await process.communicate()
                
                # Remove sentinel from output
                if self._sentinel in stdout:
                    stdout = stdout[: stdout.index(self._sentinel)]

                # Clean up trailing newlines
                if stdout.endswith("\n"):
                    stdout = stdout[:-1]
                if stderr.endswith("\n"):
                    stderr = stderr[:-1]

                return CLIResult(output=stdout, error=stderr)

        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: command has not returned in {self._timeout} seconds and must be retried",
            ) from None
        except Exception as e:
            raise ToolError(f"Failed to execute command: {str(e)}")


class SSH(BaseTool):
    """A tool for executing commands on remote hosts via SSH"""

    name: str = "ssh"
    description: str = _SSH_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute on the remote host. Can be empty to view additional logs when previous exit code is `-1`.",
            },
            "restart": {
                "type": "boolean",
                "description": "If true, restarts the SSH connection.",
            },
            "host": {
                "type": "string",
                "description": "The hostname or IP address of the SSH server.",
            },
            "private_key": {
                "type": "string",
                "description": "Path to the private key file for authentication. Defaults to ~/.ssh/id_rsa or ~/.ssh/id_ed25519 if they exist.",
            },
        },
        "required": ["command"],
    }

    _session: Optional[_SSHSession] = None
    _host: Optional[str] = None
    _private_key: Optional[str] = None

    def __init__(self, host: Optional[str] = None, private_key: Optional[str] = None):
        super().__init__()
        self._host = host
        self._private_key = private_key or self._default_private_key()

    def _default_private_key(self) -> Optional[str]:
        """Get the default private key path from the user's ~/.ssh directory."""
        home = str(Path.home())
        ssh_dir = os.path.join(home, ".ssh")
        
        # Check for common private key files
        for key_file in ["id_rsa", "id_ed25519", "id_dsa", "id_ecdsa"]:
            key_path = os.path.join(ssh_dir, key_file)
            if os.path.isfile(key_path):
                return key_path
        
        return None

    async def execute(
        self, command: str | None = None, restart: bool = False, host: Optional[str] = None, private_key: Optional[str] = None, **kwargs
    ) -> CLIResult:
        # Use parameters passed to execute() if provided, otherwise use the ones from __init__
        current_host = host or self._host
        current_private_key = private_key or self._private_key or self._default_private_key()
        
        # Check if we have the required parameters
        if not current_host:
            return ToolResult(error="SSH connection requires a host parameter.")
        
        if not current_private_key:
            return ToolResult(error="No private key found. Please specify a private key path.")
        
        if restart or self._session is None or (host and host != self._host) or (private_key and private_key != self._private_key):
            if self._session:
                self._session.stop()
            self._session = _SSHSession(current_host, current_private_key)
            await self._session.start()
            
            # Update instance variables if we're using new ones
            if host:
                self._host = host
            if private_key:
                self._private_key = private_key
                
            return ToolResult(system=f"SSH connection established to {current_host}.")

        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")


if __name__ == "__main__":
    # Example usage
    ssh = SSH(host="example.com", private_key="/path/to/private/key")
    result = asyncio.run(ssh.execute("ls -l"))
    print(result) 