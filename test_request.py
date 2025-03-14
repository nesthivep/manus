import asyncio
import json
import httpx

async def test_api():
    """Send a test request to the API and print the response."""
    url = "http://localhost:8000/run"
    prompt = "List the files in the current directory"
    
    print(f"Sending request to {url} with prompt: '{prompt}'")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"prompt": prompt},
                timeout=10.0
            )
            
        if response.status_code == 200:
            result = response.json()
            print("\n=== API Response ===")
            print(json.dumps(result, indent=2))
            
            # Check for thought and action fields
            if "steps" in result and isinstance(result["steps"], list):
                for i, step in enumerate(result["steps"]):
                    print(f"\nStep {i+1}:")
                    for field in ["step", "thought", "action", "command", "error", "url", "termination_reason"]:
                        if field in step and step[field] is not None:
                            if field in ["thought", "action"]:
                                # Truncate long thought/action content for display
                                content = step[field]
                                if len(content) > 100:
                                    content = content[:97] + "..."
                                print(f"  {field}: {content}")
                            else:
                                print(f"  {field}: {step[field]}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    print("Testing the API...")
    asyncio.run(test_api())