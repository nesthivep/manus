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
from app.web.thinking_tracker import ThinkingTracker, generate_thinking_steps

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
            "log": session["log"],
            "thinking_steps": ThinkingTracker.get_thinking_steps(session_id)
        }))
        
        # 等待结果更新
        last_log_count = 0
        last_thinking_step_count = 0
        
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
            
            # 检查思考步骤更新
            thinking_steps = ThinkingTracker.get_thinking_steps(session_id)
            current_thinking_step_count = len(thinking_steps)
            if current_thinking_step_count > last_thinking_step_count:
                await websocket.send_text(json.dumps({
                    "status": session["status"],
                    "thinking_steps": thinking_steps[last_thinking_step_count:]
                }))
                last_thinking_step_count = current_thinking_step_count
            
            # 检查结果更新
            if session["result"]:
                await websocket.send_text(json.dumps({
                    "status": session["status"],
                    "result": session["result"],
                    "log": session["log"][last_log_count:],
                    "thinking_steps": ThinkingTracker.get_thinking_steps(session_id, last_thinking_step_count)
                }))
        
        # 发送最终结果
        await websocket.send_text(json.dumps({
            "status": session["status"],
            "result": session["result"],
            "log": session["log"][last_log_count:],
            "thinking_steps": ThinkingTracker.get_thinking_steps(session_id, last_thinking_step_count)
        }))
        
        await websocket.close()
    except WebSocketDisconnect:
        # 客户端断开连接，正常操作
        pass
    except Exception as e:
        # 其他异常，记录日志但不中断应用
        print(f"WebSocket错误: {str(e)}")

# 在适当位置添加LLM通信钩子
from app.web.thinking_tracker import ThinkingTracker

# 修改通信跟踪器的实现方式
class LLMCommunicationTracker:
    """跟踪与LLM的通信内容，使用monkey patching代替回调"""
    
    def __init__(self, session_id: str, agent=None):
        self.session_id = session_id
        self.agent = agent
        self.original_run_method = None
        
        # 如果提供了agent，安装钩子
        if agent and hasattr(agent, "llm") and hasattr(agent.llm, "completion"):
            self.install_hooks()
    
    def install_hooks(self):
        """安装钩子以捕获LLM通信内容"""
        if not self.agent or not hasattr(self.agent, "llm"):
            return False
            
        # 保存原始方法
        llm = self.agent.llm
        if hasattr(llm, "completion"):
            self.original_completion = llm.completion
            # 替换为我们的包装方法
            llm.completion = self._wrap_completion(self.original_completion)
            return True
        return False
    
    def uninstall_hooks(self):
        """卸载钩子，恢复原始方法"""
        if self.agent and hasattr(self.agent, "llm") and self.original_completion:
            self.agent.llm.completion = self.original_completion
    
    def _wrap_completion(self, original_method):
        """包装LLM的completion方法以捕获输入和输出"""
        session_id = self.session_id
        
        async def wrapped_completion(*args, **kwargs):
            # 记录输入
            prompt = kwargs.get('prompt', '')
            if not prompt and args:
                prompt = args[0]
            if prompt:
                ThinkingTracker.add_communication(session_id, "发送到LLM", 
                                                prompt[:500] + ("..." if len(prompt) > 500 else ""))
            
            # 调用原始方法
            result = await original_method(*args, **kwargs)
            
            # 记录输出
            if result:
                content = result
                if isinstance(result, dict) and 'content' in result:
                    content = result['content']
                elif hasattr(result, 'content'):
                    content = result.content
                
                if isinstance(content, str):
                    ThinkingTracker.add_communication(session_id, "从LLM接收", 
                                                    content[:500] + ("..." if len(content) > 500 else ""))
            
            return result
        
        return wrapped_completion

# 导入新创建的LLM包装器
from app.agent.llm_wrapper import LLMCallbackWrapper

# 修改process_prompt函数，确保记录真实通信而不是模拟数据
async def process_prompt(session_id: str, prompt: str):
    try:
        # 使用新的日志捕获上下文管理器
        with capture_session_logs(session_id) as log:
            # 初始化思考跟踪
            ThinkingTracker.start_tracking(session_id)
            ThinkingTracker.add_thinking_step(session_id, "开始处理用户请求")
            
            # 直接记录用户输入的prompt
            ThinkingTracker.add_communication(session_id, "用户输入", prompt)
            
            # 初始化代理和任务流程
            ThinkingTracker.add_thinking_step(session_id, "初始化AI代理和任务流程")
            agent = Manus()
            
            # 使用包装器包装LLM
            if hasattr(agent, "llm"):
                original_llm = agent.llm
                wrapped_llm = LLMCallbackWrapper(original_llm)
                
                # 注册回调函数
                def on_before_request(data):
                    # 提取请求内容
                    prompt_content = None
                    if data.get("args") and len(data["args"]) > 0:
                        prompt_content = str(data["args"][0])
                    elif data.get("kwargs") and "prompt" in data["kwargs"]:
                        prompt_content = data["kwargs"]["prompt"]
                    else:
                        prompt_content = str(data)
                    
                    # 记录通信内容
                    print(f"发送到LLM: {prompt_content[:100]}...")
                    ThinkingTracker.add_communication(session_id, "发送到LLM", prompt_content)
                
                def on_after_request(data):
                    # 提取响应内容
                    response = data.get("response", "")
                    response_content = ""
                    
                    # 尝试从不同格式中提取文本内容
                    if isinstance(response, str):
                        response_content = response
                    elif isinstance(response, dict):
                        if "content" in response:
                            response_content = response["content"]
                        elif "text" in response:
                            response_content = response["text"]
                        else:
                            response_content = str(response)
                    elif hasattr(response, "content"):
                        response_content = response.content
                    else:
                        response_content = str(response)
                    
                    # 记录通信内容
                    print(f"从LLM接收: {response_content[:100]}...")
                    ThinkingTracker.add_communication(session_id, "从LLM接收", response_content)
                
                # 注册回调
                wrapped_llm.register_callback("before_request", on_before_request)
                wrapped_llm.register_callback("after_request", on_after_request)
                
                # 替换原始LLM
                agent.llm = wrapped_llm
            
            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agent,
            )
            
            # 记录处理开始
            ThinkingTracker.add_thinking_step(session_id, f"分析用户请求: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            log.info(f"开始执行: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            
            # 检查任务是否被取消
            cancel_event = cancel_events.get(session_id)
            if cancel_event and cancel_event.is_set():
                log.warning("处理已被用户取消")
                ThinkingTracker.mark_stopped(session_id)
                active_sessions[session_id]["status"] = "stopped"
                active_sessions[session_id]["result"] = "处理已被用户停止"
                return
            
            # 跟踪计划创建过程
            ThinkingTracker.add_thinking_step(session_id, "创建任务执行计划")
            ThinkingTracker.add_thinking_step(session_id, "开始执行任务计划")
            
            # 移除手动模拟步骤，让真实的流程执行生成通信记录
            
            # 执行实际处理
            result = await flow.execute(prompt)
            
            # 记录完成情况
            log.info("处理完成")
            ThinkingTracker.add_conclusion(session_id, "任务处理完成！已生成结果。")
            
            active_sessions[session_id]["status"] = "completed"
            active_sessions[session_id]["result"] = result
            active_sessions[session_id]["thinking_steps"] = ThinkingTracker.get_thinking_steps(session_id)
            
    except asyncio.CancelledError:
        # 处理取消情况
        print("处理已取消")
        ThinkingTracker.mark_stopped(session_id)
        active_sessions[session_id]["status"] = "stopped"
        active_sessions[session_id]["result"] = "处理已被取消"
    except Exception as e:
        # 处理错误情况
        error_msg = f"处理出错: {str(e)}"
        print(error_msg)
        ThinkingTracker.add_error(session_id, f"处理遇到错误: {str(e)}")
        active_sessions[session_id]["status"] = "error"
        active_sessions[session_id]["result"] = f"发生错误: {str(e)}"
    finally:
        # 清理资源
        if 'agent' in locals() and hasattr(agent, "llm") and isinstance(agent.llm, LLMCallbackWrapper):
            try:
                # 正确地移除回调
                if 'on_before_request' in locals():
                    agent.llm._callbacks["before_request"].remove(on_before_request)
                if 'on_after_request' in locals():
                    agent.llm._callbacks["after_request"].remove(on_after_request)
            except (ValueError, Exception) as e:
                print(f"清理回调时出错: {str(e)}")
                
        # 清理取消事件
        if session_id in cancel_events:
            del cancel_events[session_id]

# 添加一个新的API端点来获取思考步骤
@app.get("/api/thinking/{session_id}")
async def get_thinking_steps(session_id: str, start_index: int = 0):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "status": ThinkingTracker.get_status(session_id),
        "thinking_steps": ThinkingTracker.get_thinking_steps(session_id, start_index)
    }

# 添加获取进度信息的API端点
@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ThinkingTracker.get_progress(session_id)
