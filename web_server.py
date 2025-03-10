import asyncio
import sys
import os
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path
from loguru import logger as loguru_logger

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger, define_log_level

# 活跃的 WebSocket 连接集合
active_websockets = set()

# WebSocket 日志 sink
async def websocket_sink(message):
    record = message.record
    log_entry = f"{record['time'].strftime('%Y-%m-%d %H:%M:%S')} | {record['level'].name} | {record['message']}"
    
    websockets_to_remove = set()
    for ws in active_websockets:
        try:
            await ws.send_text(f"LOG: {log_entry}")
        except Exception:
            websockets_to_remove.add(ws)
    
    for ws in websockets_to_remove:
        active_websockets.remove(ws)

# 线程安全的 sink 适配器
class WebSocketSink:
    def __init__(self):
        self.loop = None
    
    def __call__(self, message):
        if self.loop is None:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        
        asyncio.run_coroutine_threadsafe(websocket_sink(message), self.loop)
        return message["message"]

# 创建 FastAPI 应用
app = FastAPI(title="OpenManus Web UI")

# 创建 templates 和 static 目录
current_dir = Path(__file__).resolve().parent
templates_dir = current_dir / "templates"
static_dir = current_dir / "static"

# 确保目录存在
templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

# 设置模板和静态文件
templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 配置日志系统
@app.on_event("startup")
async def startup_event():
    # 配置 loguru 使用 WebSocket sink
    loguru_logger.remove()
    loguru_logger.add(sys.stdout, level="INFO")
    
    ws_sink = WebSocketSink()
    loguru_logger.add(ws_sink, level="INFO")
    
    # 配置 app logger
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add(ws_sink, level="INFO")
    
    logger.info("Web服务器已启动，等待连接...")

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 将 WebSocket 添加到活跃连接集合
    active_websockets.add(websocket)
    
    # 发送欢迎消息
    await websocket.send_text("LOG: WebSocket连接已建立，系统准备就绪")
    logger.info("新的WebSocket连接已建立")
    
    try:
        # 创建 Manus 代理
        agent = Manus()
        
        # 集成 main.py 的功能循环
        while True:
            try:
                # 接收用户输入
                prompt = await websocket.receive_text()
                
                if prompt.lower() in ["exit", "quit"]:
                    await websocket.send_text("会话已结束")
                    logger.info("用户主动结束会话")
                    break
                    
                if not prompt.strip():
                    await websocket.send_text("请输入有效的提示")
                    continue
                
                # 发送处理消息
                await websocket.send_text("正在处理您的请求...")
                logger.info(f"接收到用户请求: {prompt[:50]}...")
                
                try:
                    # 执行代理 - 所有 logger.info 都会被转发到 WebSocket
                    result = await agent.run(prompt)
                    
                    # 发送结果
                    logger.info("请求处理完成")
                    await websocket.send_text(f"RESULT: {str(result)}")
                    
                except Exception as e:
                    error_msg = f"处理请求时出错: {str(e)}"
                    logger.error(error_msg)
                    await websocket.send_text(f"ERROR: {error_msg}")
            
            except Exception as e:
                logger.error(f"WebSocket通信错误: {str(e)}")
                await websocket.send_text(f"ERROR: 通信错误: {str(e)}")
    
    except WebSocketDisconnect:
        logger.info("WebSocket连接已关闭")
    except Exception as e:
        logger.error(f"WebSocket处理时出错: {str(e)}")
    finally:
        # 移除 WebSocket
        if websocket in active_websockets:
            active_websockets.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)