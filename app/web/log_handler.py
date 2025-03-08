"""
简单的日志处理模块，用于Web应用日志捕获
"""
import time
import threading
from typing import Dict, List, Callable, Optional
from contextlib import contextmanager

# 全局日志存储
session_logs: Dict[str, List[Dict]] = {}
_lock = threading.Lock()

def add_log(session_id: str, level: str, message: str) -> None:
    """添加日志到指定会话"""
    with _lock:
        if session_id not in session_logs:
            session_logs[session_id] = []
        
        session_logs[session_id].append({
            "level": level,
            "message": message,
            "timestamp": time.time()
        })

def get_logs(session_id: str) -> List[Dict]:
    """获取指定会话的日志"""
    with _lock:
        return session_logs.get(session_id, [])[:]

def clear_logs(session_id: str) -> None:
    """清除指定会话的日志"""
    with _lock:
        if session_id in session_logs:
            del session_logs[session_id]

class SimpleLogCapture:
    """简单的日志捕获器，不依赖loguru的复杂格式"""
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    def info(self, message: str) -> None:
        """记录信息级别日志"""
        add_log(self.session_id, "info", message)
        print(f"INFO: {message}")
    
    def warning(self, message: str) -> None:
        """记录警告级别日志"""
        add_log(self.session_id, "warning", message)
        print(f"WARNING: {message}")
    
    def error(self, message: str) -> None:
        """记录错误级别日志"""
        add_log(self.session_id, "error", message)
        print(f"ERROR: {message}")
    
    def debug(self, message: str) -> None:
        """记录调试级别日志"""
        add_log(self.session_id, "debug", message)
        print(f"DEBUG: {message}")

@contextmanager
def capture_session_logs(session_id: str):
    """创建一个简单的日志上下文"""
    logger = SimpleLogCapture(session_id)
    logger.info(f"开始处理请求 (Session ID: {session_id})")
    try:
        yield logger
    finally:
        logger.info("处理完成")
