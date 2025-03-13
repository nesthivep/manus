import asyncio
import json
from typing import Optional, Dict, Any, List

import aiomysql
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.config import config
from app.tool.base import BaseTool, ToolResult

_MYSQL_DESCRIPTION = """
执行MySQL数据库查询并返回结果。支持的操作包括：
- 'execute': 执行SQL查询语句
- 'show_tables': 显示数据库中的所有表
- 'describe_table': 描述表结构
- 'switch_database': 切换到另一个配置的数据库
"""


class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = _MYSQL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "execute", 
                    "show_tables", 
                    "describe_table", 
                    "switch_database",
                    "get_database_info",
                    "list_databases"
                ],
                "description": "要执行的MySQL操作",
            },
            "query": {
                "type": "string",
                "description": "要执行的SQL查询语句",
            },
            "params": {
                "type": "array",
                "items": {"type": "string"},
                "description": "SQL查询的参数（用于参数化查询）",
            },
            "table_name": {
                "type": "string",
                "description": "表名（用于describe_table操作）",
            },
            "database_name": {
                "type": "string",
                "description": "要切换到的数据库配置名称（用于switch_database操作）",
            },
        },
        "required": ["action"],
        "dependencies": {
            "execute": ["query"],
            "describe_table": ["table_name"],
            "switch_database": ["database_name"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    pool: Optional[aiomysql.Pool] = Field(default=None, exclude=True)
    current_db_name: str = Field(default="default", exclude=True)
    
    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("参数不能为空")
        return v

    async def _ensure_connection(self) -> bool:
        """确保数据库连接已建立"""
        if self.pool is None:
            db_config = config.get_database_config(self.current_db_name)
            if not db_config:
                raise Exception(f"找不到数据库配置: {self.current_db_name}")
            
            try:
                self.pool = await aiomysql.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    user=db_config.user,
                    password=db_config.password,
                    db=db_config.database,
                    charset=db_config.charset,
                    autocommit=True
                )
                return True
            except Exception as e:
                raise Exception(f"无法连接到数据库 {self.current_db_name}: {str(e)}")
        return True

    async def execute(
        self,
        action: str,
        query: Optional[str] = None,
        params: Optional[List[str]] = None,
        table_name: Optional[str] = None,
        database_name: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        执行指定的MySQL操作。

        Args:
            action: 要执行的操作
            query: 要执行的SQL查询语句
            params: SQL查询的参数（用于参数化查询）
            table_name: 表名（用于describe_table操作）
            database_name: 数据库配置名称（用于switch_database操作）
            **kwargs: 其他参数

        Returns:
            ToolResult: 包含操作输出或错误信息
        """
        async with self.lock:
            try:
                if action == "switch_database":
                    if not database_name:
                        return ToolResult(error="switch_database操作需要提供数据库配置名称")
                    
                    if database_name not in config.database:
                        return ToolResult(error=f"找不到数据库配置: {database_name}")
                    
                    # 关闭现有连接
                    await self.cleanup()
                    
                    # 更新当前数据库名称
                    self.current_db_name = database_name
                    
                    # 测试新连接
                    await self._ensure_connection()
                    
                    db_config = config.get_database_config(self.current_db_name)
                    return ToolResult(output=f"已切换到数据库: {db_config.database}@{db_config.host}")
                
                # 确保连接已建立
                await self._ensure_connection()
                
                if action == "execute":
                    if not query:
                        return ToolResult(error="execute操作需要提供SQL查询语句")
                    
                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute(query, params or ())
                            
                            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                                result = await cursor.fetchall()
                                result_list = [dict(row) for row in result]
                                
                                # 处理JSON序列化问题
                                for row in result_list:
                                    for key, value in row.items():
                                        if isinstance(value, (bytes, bytearray)):
                                            row[key] = value.decode('utf-8', errors='replace')
                                
                                # 限制返回的数据量
                                if len(result_list) > 100:
                                    truncated_result = result_list[:100]
                                    return ToolResult(
                                        output=f"查询返回了 {len(result_list)} 行结果（仅显示前100行）:\n{json.dumps(truncated_result, ensure_ascii=False, default=str)}"
                                    )
                                else:
                                    return ToolResult(
                                        output=f"查询返回了 {len(result_list)} 行结果:\n{json.dumps(result_list, ensure_ascii=False, default=str)}"
                                    )
                            else:
                                affected_rows = cursor.rowcount
                                return ToolResult(output=f"执行成功，影响了 {affected_rows} 行")

                elif action == "show_tables":
                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute("SHOW TABLES")
                            tables = await cursor.fetchall()
                            table_list = [list(table.values())[0] for table in tables]
                            return ToolResult(
                                output=f"数据库中的表:\n{json.dumps(table_list, ensure_ascii=False)}"
                            )

                elif action == "describe_table":
                    if not table_name:
                        return ToolResult(error="describe_table操作需要提供表名")
                    
                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute(f"DESCRIBE {table_name}")
                            columns = await cursor.fetchall()
                            columns_list = [dict(column) for column in columns]
                            
                            # 处理JSON序列化问题
                            for column in columns_list:
                                for key, value in column.items():
                                    if isinstance(value, (bytes, bytearray)):
                                        column[key] = value.decode('utf-8', errors='replace')
                            
                            return ToolResult(
                                output=f"表 {table_name} 的结构:\n{json.dumps(columns_list, ensure_ascii=False, default=str)}"
                            )

                # 添加新操作的处理
                elif action == "get_database_info":
                    return await self.get_current_database_info()
                
                elif action == "list_databases":
                    return await self.list_available_databases()
                
                else:
                    return ToolResult(error=f"未知操作: {action}")
                
            except Exception as e:
                return ToolResult(error=f"MySQL操作 '{action}' 失败: {str(e)}")

    async def cleanup(self):
        """清理数据库连接资源"""
        async with self.lock:
            if self.pool is not None:
                self.pool.close()
                await self.pool.wait_closed()
                self.pool = None

    def __del__(self):
        """确保对象销毁时清理资源"""
        if self.pool is not None:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()
                
    async def get_current_database_info(self) -> ToolResult:
        """获取当前数据库连接信息"""
        async with self.lock:
            try:
                db_config = config.get_database_config(self.current_db_name)
                if not db_config:
                    return ToolResult(error=f"找不到数据库配置: {self.current_db_name}")
                
                info = {
                    "database_name": self.current_db_name,
                    "host": db_config.host,
                    "port": db_config.port,
                    "user": db_config.user,
                    "database": db_config.database,
                    "connected": self.pool is not None
                }
                
                return ToolResult(output=f"当前数据库连接信息:\n{json.dumps(info, ensure_ascii=False)}")
            except Exception as e:
                return ToolResult(error=f"获取数据库信息失败: {str(e)}")
                
    async def list_available_databases(self) -> ToolResult:
        """列出配置中所有可用的数据库"""
        try:
            available_dbs = []
            for name, db_config in config.database.items():
                available_dbs.append({
                    "name": name,
                    "host": db_config.host,
                    "database": db_config.database,
                    "is_current": name == self.current_db_name
                })
            
            return ToolResult(output=f"可用的数据库配置:\n{json.dumps(available_dbs, ensure_ascii=False)}")
        except Exception as e:
            return ToolResult(error=f"获取可用数据库列表失败: {str(e)}")

    def set_db_config(self, config: Dict[str, Any]):
        """设置数据库配置"""
        self.db_config.update(config)
        # 如果已经有连接池，则关闭它以便下次使用新配置
        if self.pool is not None:
            asyncio.create_task(self.cleanup())