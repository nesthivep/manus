from fastapi import FastAPI, Request
import uvicorn
from app.agent.manus import Manus
from app.logger import logger
from typing import List, Dict, Any, Optional
from app.schema import AgentState

app = FastAPI()

async def run_agent(request: Request):
    data = await request.json()
    prompt = data.get('prompt')
    if not prompt:
        return {"steps": [{"step": 0, "error": "No prompt provided"}]}
    agent = Manus()
    try:
        logger.warning("Processing your request...")
        result = await agent.run(prompt)
        logger.info("Request processing completed.")
        return {"steps": result}
    except Exception as e:
        return {"steps": [{"step": 0, "error": str(e)}]}

@app.post('/run')
async def run_endpoint(request: Request):
    return await run_agent(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
