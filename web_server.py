import asyncio
import os
import sys
import io
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path
import threading
import queue
import time

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger

# 创建一个自定义日志处理器类，用于捕获日志并发送到WebSocket
class WebSocketLogHandler:
    def __init__(self, websocket):
        self.websocket = websocket
        self.queue = queue.Queue()
        self.running = False
        self.thread = None
    
    async def send_log(self, message):
        if self.websocket and message:
            try:
                await self.websocket.send_text(f"LOG: {message}")
            except Exception as e:
                print(f"WebSocket发送日志失败: {str(e)}")
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._capture_logs)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _capture_logs(self):
        # 重定向stdout和stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # 使用一个管道来捕获输出
        pipe_out, pipe_in = os.pipe()
        
        # 创建新的stdout和stderr
        stdout_fd = os.dup(sys.stdout.fileno())
        stderr_fd = os.dup(sys.stderr.fileno())
        
        # 重定向到管道
        os.dup2(pipe_in, sys.stdout.fileno())
        os.dup2(pipe_in, sys.stderr.fileno())
        
        # 异步读取和发送日志
        def read_pipe():
            pipe_reader = os.fdopen(pipe_out, 'r')
            while self.running:
                try:
                    line = pipe_reader.readline()
                    if line:
                        self.queue.put(line.rstrip())
                    else:
                        time.sleep(0.1)
                except Exception as e:
                    print(f"读取日志失败: {str(e)}")
        
        # 启动读取线程
        read_thread = threading.Thread(target=read_pipe)
        read_thread.daemon = True
        read_thread.start()
        
        try:
            # 不断将日志从队列发送到WebSocket
            while self.running:
                try:
                    # 非阻塞获取日志
                    while not self.queue.empty():
                        log = self.queue.get_nowait()
                        asyncio.run(self.send_log(log))
                    time.sleep(0.1)
                except Exception as e:
                    print(f"处理日志队列失败: {str(e)}")
        finally:
            # 恢复原始stdout和stderr
            os.dup2(stdout_fd, sys.stdout.fileno())
            os.dup2(stderr_fd, sys.stderr.fileno())
            os.close(stdout_fd)
            os.close(stderr_fd)
            os.close(pipe_in)
            
            # 停止读取线程
            self.running = False
            read_thread.join(timeout=1)

app = FastAPI(title="OpenManus Web UI")

# 创建templates
current_dir = Path(__file__).resolve().parent
templates_dir = current_dir / "templates"

# 确保目录存在
templates_dir.mkdir(exist_ok=True)

# 设置模板和静态文件
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 创建日志处理器并启动
    log_handler = WebSocketLogHandler(websocket)
    log_handler.start()
    
    try:
        # 创建Manus代理
        agent = Manus()
        
        while True:
            # 接收用户输入
            prompt = await websocket.receive_text()
            
            if prompt.lower() in ["exit", "quit"]:
                await websocket.send_text("会话已结束")
                break
                
            if not prompt.strip():
                await websocket.send_text("请输入有效的提示")
                continue
                
            # 发送处理消息
            await websocket.send_text("正在处理您的请求...")
            
            try:
                # 执行代理
                await websocket.send_text("LOG: 开始处理请求...")
                result = await agent.run(prompt)
                # 发送结果
                await websocket.send_text(f"RESULT: {str(result)}")
            except Exception as e:
                logger.error(f"处理请求时出错: {str(e)}")
                await websocket.send_text(f"ERROR: 处理请求时出错: {str(e)}")
    
    except WebSocketDisconnect:
        logger.info("WebSocket连接已关闭")
    except Exception as e:
        logger.error(f"WebSocket处理时出错: {str(e)}")
    finally:
        # 停止日志处理器
        log_handler.stop()


@app.post("/api/prompt")
async def process_prompt(request: Request):
    """处理API请求，用于非WebSocket方式调用"""
    data = await request.json()
    prompt = data.get("prompt", "")
    
    if not prompt.strip():
        return {"status": "error", "message": "请输入有效的提示"}
    
    try:
        # 创建并运行代理
        agent = Manus()
        result = await agent.run(prompt)
        return {"status": "success", "result": str(result)}
    except Exception as e:
        logger.error(f"处理API请求时出错: {str(e)}")
        return {"status": "error", "message": f"处理请求时出错: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)