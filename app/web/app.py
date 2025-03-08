from fastapi import FastAPI, WebSocket, Request, BackgroundTasks, HTTPException, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import uuid
import json
import webbrowser
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import time
from pydantic import BaseModel

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger
from app.web.log_handler import capture_session_logs, get_logs

# 控制是否自动打开浏览器 (读取环境变量，默认为True)
AUTO_OPEN_BROWSER = os.environ.get("AUTO_OPEN_BROWSER", "1") == "1"

app = FastAPI(title="OpenManus Web")

# 获取当前文件所在目录
current_dir = Path(__file__).parent
# 设置静态文件目录
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")
# 设置模板目录
templates = Jinja2Templates(directory=current_dir / "templates")

# 存储活跃的会话及其结果
active_sessions: Dict[str, dict] = {}

# 存储任务取消事件
cancel_events: Dict[str, asyncio.Event] = {}

@app.on_event("startup")
async def startup_event():
    """启动事件：应用启动时自动打开浏览器"""
    if AUTO_OPEN_BROWSER:
        # 延迟1秒以确保服务已经启动
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8000")).start()
        print("🌐 自动打开浏览器...")

class SessionRequest(BaseModel):
    prompt: str

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def create_chat_session(session_req: SessionRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "status": "processing",
        "result": None,
        "log": []
    }
    
    # 创建取消事件
    cancel_events[session_id] = asyncio.Event()
    
    background_tasks.add_task(process_prompt, session_id, session_req.prompt)
    return {"session_id": session_id}

@app.get("/api/chat/{session_id}")
async def get_chat_result(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 使用新的日志处理模块获取日志
    session = active_sessions[session_id]
    session["log"] = get_logs(session_id)
    
    return session

@app.post("/api/chat/{session_id}/stop")
async def stop_processing(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_id in cancel_events:
        cancel_events[session_id].set()
        
    active_sessions[session_id]["status"] = "stopped"
    active_sessions[session_id]["result"] = "处理已被用户停止"
    
    return {"status": "stopped"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    try:
        await websocket.accept()
        
        if session_id not in active_sessions:
            await websocket.send_text(json.dumps({"error": "Session not found"}))
            await websocket.close()
            return
        
        session = active_sessions[session_id]
        
        # 初始状态通知
        await websocket.send_text(json.dumps({
            "status": session["status"], 
            "log": session["log"]
        }))
        
        # 等待结果更新
        last_log_count = 0
        while session["status"] == "processing":
            await asyncio.sleep(0.5)
            
            # 检查日志更新
            current_log_count = len(session["log"])
            if current_log_count > last_log_count:
                await websocket.send_text(json.dumps({
                    "status": session["status"],
                    "log": session["log"][last_log_count:]
                }))
                last_log_count = current_log_count
            
            # 检查结果更新
            if session["result"]:
                await websocket.send_text(json.dumps({
                    "status": session["status"],
                    "result": session["result"],
                    "log": session["log"][last_log_count:]
                }))
        
        # 发送最终结果
        await websocket.send_text(json.dumps({
            "status": session["status"],
            "result": session["result"],
            "log": session["log"][last_log_count:]
        }))
        
        await websocket.close()
    except WebSocketDisconnect:
        # 客户端断开连接，正常操作
        pass
    except Exception as e:
        # 其他异常，记录日志但不中断应用
        print(f"WebSocket错误: {str(e)}")

async def process_prompt(session_id: str, prompt: str):
    try:
        # 使用新的日志捕获上下文管理器
        with capture_session_logs(session_id) as log:
            agent = Manus()
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agent,
            )
            
            log.info(f"开始执行: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            
            # 检查任务是否被取消
            cancel_event = cancel_events.get(session_id)
            if cancel_event and cancel_event.is_set():
                log.warning("处理已被用户取消")
                active_sessions[session_id]["status"] = "stopped"
                active_sessions[session_id]["result"] = "处理已被用户停止"
                return
            
            result = await flow.execute(prompt)
            
            log.info("处理完成")
            
            active_sessions[session_id]["status"] = "completed"
            active_sessions[session_id]["result"] = result
    except asyncio.CancelledError:
        # 这里不使用logger，避免类似问题
        print("处理已取消")
        active_sessions[session_id]["status"] = "stopped"
        active_sessions[session_id]["result"] = "处理已被取消"
    except Exception as e:
        # 这里不使用logger，避免类似问题
        error_msg = f"处理出错: {str(e)}"
        print(error_msg)
        active_sessions[session_id]["status"] = "error"
        active_sessions[session_id]["result"] = f"发生错误: {str(e)}"
    finally:
        # 清理取消事件
        if session_id in cancel_events:
            del cancel_events[session_id]
