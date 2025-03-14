import asyncio
import json
import sys
import subprocess
import time
import signal
import os
from typing import Dict, Any

import httpx

async def test_api():
    """Test the refactored API to verify JSON array output format."""
    url = "http://localhost:8000/run"
    prompt = "List the files in the current directory"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"prompt": prompt},
                timeout=15.0  # Shorter timeout
            )
            
        if response.status_code == 200:
            result = response.json()
            print("\n=== API Response ===")
            print(json.dumps(result, indent=2))
            
            # Verify the response structure
            if "steps" in result and isinstance(result["steps"], list):
                print("\n✅ Response contains a 'steps' array as expected")
                
                # Check if steps have the required structure
                for i, step in enumerate(result["steps"]):
                    print(f"\nStep {i+1}:")
                    
                    # Check for step number
                    if "step" in step:
                        print(f"  ✅ Has 'step' field: {step['step']}")
                    else:
                        print(f"  ❌ Missing 'step' field")
                        
                    # Check for other fields
                    for field in ["error", "command", "url", "termination_reason", "thought", "action"]:
                        if field in step and step[field] is not None:
                            print(f"  ✅ Has '{field}' field: {step[field]}")
                
                # Verify the structure meets requirements
                print("\n=== Requirements Verification ===")
                
                # 1. API processes errors and normal outputs correctly
                has_error = any("error" in step for step in result["steps"])
                has_command = any("command" in step for step in result["steps"])
                print(f"1. API processes errors and outputs: {'✅ Yes' if has_error or has_command else '❌ No'}")
                
                # 2. Breaks response into JSON objects inside an array
                print(f"2. Response is in JSON array format: {'✅ Yes' if isinstance(result['steps'], list) else '❌ No'}")
                
                # 3. Response is well-formatted and readable
                print(f"3. Response is well-formatted: {'✅ Yes' if result['steps'] else '❌ No'}")
                
                # 4. Includes thought and action fields
                has_thought = any("thought" in step and step["thought"] is not None for step in result["steps"])
                has_action = any("action" in step and step["action"] is not None for step in result["steps"])
                print(f"4. Includes thought and action: {'✅ Yes' if has_thought and has_action else '❌ No'}")
                
            else:
                print("\n❌ Response does not contain a 'steps' array")
        else:
            print(f"\n❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")

def start_server():
    """Start the FastAPI server in the background."""
    print("Starting FastAPI server...")
    server_process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    # Wait for server to start
    time.sleep(3)
    return server_process

def stop_server(server_process):
    """Stop the FastAPI server."""
    print("Stopping FastAPI server...")
    os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
    server_process.wait()

if __name__ == "__main__":
    print("Testing the refactored API...")
    
    # Start server
    server_process = start_server()
    
    try:
        # Run test
        asyncio.run(test_api())
    finally:
        # Stop server
        stop_server(server_process)