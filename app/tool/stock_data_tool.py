import logging
import os
from datetime import datetime
from typing import Dict, Optional, Union

import aiohttp

from app.tool.base import BaseTool


# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)


def safe_float(value: Union[str, float, int, None], default: float = 0.0) -> float:
    """
    安全地将输入值转换为浮点数

    Args:
        value: 输入值
        default: 默认值

    Returns:
        float: 转换后的浮点数
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class StockSearch(BaseTool):
    base_url: str = "https://push2.eastmoney.com/api/qt/clist/get"
    finance_url: str = "https://push2.eastmoney.com/api/qt/stock/get"
    time_line_url: str = "https://push2.eastmoney.com/api/qt/stock/trends2/get"
    daily_kline_url: str = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    stock_themes_url: str = (
        "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax"
    )
    headers: Dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://quote.eastmoney.com/",
    }

    def __init__(self):
        super().__init__(
            name="stock_search",
            description="东方财富股票数据查询工具，用于获取股票实时行情、财务数据和K线走势。仅在用户明确请求股票数据时使用一次，获取数据后应使用其他工具（如PythonExecute）进行后续分析或可视化。",
        )
        # 更新 headers 中的 User-Agent
        self.headers["User-Agent"] = os.environ.get(
            "USER_AGENT", self.headers["User-Agent"]
        )

        # 添加工具参数架构
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "股票名称或代码，或自然语言查询。例如：贵州茅台、600519、查询腾讯的股价。此工具只需调用一次获取完整数据。",
                }
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "", **kwargs):
        """实现抽象方法 execute"""
        if not query:
            return "请提供股票名称或代码"

        try:
            # 提取股票名称（如果查询是自然语言）
            stock_name = self.extract_stock_name(query)
            logger.info(f"查询股票：{query}，提取的股票名称：{stock_name}")

            # 先尝试使用提取的股票名称搜索
            result = await self.search_stock(stock_name)

            # 如果提取的名称搜索失败，尝试使用原始查询
            if not result and stock_name != query:
                logger.info(f"使用提取的名称'{stock_name}'未找到匹配股票，尝试使用完整查询...")
                result = await self.search_stock(query)

            if result:
                # 直接返回描述文本
                return result.get("description", "未能获取股票描述信息")
            else:
                return f"未找到与'{query}'匹配的股票，请尝试使用更准确的股票名称或代码"
        except Exception as e:
            logger.error(f"执行股票查询时发生错误: {str(e)}")
            return f"查询股票时出错: {str(e)}"

    async def fetch_finance_data(self, stock_code: str) -> Dict:
        """获取股票财务数据"""
        if stock_code.startswith(
            ("90", "92", "93", "94", "95", "96", "97", "98", "99")
        ):
            return self._get_default_finance_data()

        market = "1" if stock_code.startswith(("6", "9")) else "0"
        params = {
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "invt": 2,
            "fltt": 2,
            "fields": "f84,f85,f55,f105,f183,f173,f186,f188",
            "secid": f"{market}.{stock_code}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.finance_url, params=params, headers=self.headers
                ) as response:
                    data = await response.json()
                    if not data or "data" not in data:
                        logger.warning(f"获取股票 {stock_code} 财务数据失败: 返回数据格式错误")
                        return self._get_default_finance_data()

                    stock_data = data.get("data", {})
                    if not stock_data:
                        logger.warning(f"获取股票 {stock_code} 财务数据失败: 无数据")
                        return self._get_default_finance_data()

                    return {
                        "total_shares": round(
                            safe_float(stock_data.get("f84")) / 100000000, 2
                        ),
                        "circulating_shares": round(
                            safe_float(stock_data.get("f85")) / 100000000, 2
                        ),
                        "eps": round(safe_float(stock_data.get("f55")), 4),
                        "net_profit": round(
                            safe_float(stock_data.get("f105")) / 100000000, 2
                        ),
                        "revenue": round(
                            safe_float(stock_data.get("f183")) / 100000000, 2
                        ),
                        "roe": round(safe_float(stock_data.get("f173")), 2),
                        "gross_profit_margin": round(
                            safe_float(stock_data.get("f186")), 2
                        ),
                        "debt_ratio": round(safe_float(stock_data.get("f188")), 2),
                    }
        except Exception as e:
            logger.error(f"获取股票 {stock_code} 财务数据失败: {str(e)}")
            return self._get_default_finance_data()

    def _get_default_finance_data(self) -> Dict:
        """返回默认的财务数据"""
        return {
            "total_shares": 0,
            "circulating_shares": 0,
            "eps": 0,
            "net_profit": 0,
            "revenue": 0,
            "roe": 0,
            "gross_profit_margin": 0,
            "debt_ratio": 0,
        }

    def extract_stock_name(self, query: str) -> str:
        """
        从自然语言查询中提取股票名称

        Args:
            query: 用户的自然语言查询

        Returns:
            str: 提取出的可能的股票名称
        """
        # 如果输入为空，直接返回
        if not query or len(query.strip()) == 0:
            return ""

        # 常见的引导词和后缀词，用于识别股票名称
        prefixes = [
            "帮我查询",
            "帮我搜索",
            "帮我找",
            "帮我看看",
            "帮忙查询",
            "帮忙搜索",
            "帮我",
            "请帮我",
            "请帮我查询",
            "请帮我搜索",
            "请查询",
            "请搜索",
            "查询",
            "搜索",
            "查看",
            "想知道",
            "了解",
            "查一下",
            "分析",
            "帮我分析",
            "分析下",
            "帮我分析下",
            "看看",
            "帮我看下",
            "了解下",
            "查询下",
            "搜索下",
            "分析一下",
            "看一下",
            "查一查",
            "分析一下",
        ]

        suffixes = [
            "的股票",
            "的股票数据",
            "的行情",
            "的股价",
            "的走势",
            "股票",
            "这只股票",
            "这个股票",
            "公司",
            "的情况",
            "的信息",
            "的分时数据",
            "的K线",
            "的日K",
            "的数据",
            "的情况如何",
            "下周走势",
            "今日表现",
            "近期表现",
            "明天会涨吗",
            "怎么样",
            "股价多少",
            "值得买吗",
            "能买吗",
            "如何",
        ]

        # 添加更多中间词模式
        middle_words = ["这只", "这个", "这家", "的", "下", "这"]

        # 按照长度从长到短排序前缀和后缀，避免子字符串问题
        prefixes.sort(key=len, reverse=True)
        suffixes.sort(key=len, reverse=True)

        # 去除引导词
        cleaned_query = query
        for prefix in prefixes:
            if cleaned_query.lower().startswith(prefix.lower()):
                cleaned_query = cleaned_query[len(prefix) :].strip()
                break  # 一旦匹配到一个前缀就停止，避免重复处理

        # 去除所有可能的后缀，不仅仅是一个
        changed = True
        while changed:
            changed = False
            for suffix in suffixes:
                if cleaned_query.lower().endswith(suffix.lower()):
                    cleaned_query = cleaned_query[: -len(suffix)].strip()
                    changed = True
                    break

        # 尝试处理中间的修饰词
        for word in middle_words:
            if word in cleaned_query:
                parts = cleaned_query.split(word)
                if len(parts) >= 2:
                    # 如果分割后的第一部分非空，并且长度至少为2个字符，则可能是股票名称
                    if parts[0] and len(parts[0]) >= 2:
                        cleaned_query = parts[0].strip()
                    # 否则保留原样
                    break

        # 如果前后都处理完，结果非常短（小于2个字符），可能处理过度，返回原始查询
        if len(cleaned_query) < 2:
            # 尝试直接从原始查询中提取可能的股票名称（2-4个中文字符连续的部分）
            import re

            chinese_words = re.findall(r"[\u4e00-\u9fa5]{2,4}", query)
            if chinese_words:
                # 筛选可能的股票名称（排除常见的非股票名词）
                stop_words = [
                    "股票",
                    "走势",
                    "分析",
                    "行情",
                    "查询",
                    "搜索",
                    "帮我",
                    "请帮",
                    "明天",
                    "下周",
                    "情况",
                ]
                candidates = [
                    word
                    for word in chinese_words
                    if word not in stop_words and len(word) >= 2
                ]
                if candidates:
                    return candidates[0]  # 返回第一个可能的股票名称
            return query

        # 如果结果非空则返回，否则返回原始查询
        return cleaned_query if cleaned_query else query

    async def get_basic_data(self, query: str) -> Optional[Dict]:
        """
        获取股票基本数据

        Args:
            query: 股票名称或代码

        Returns:
            Dict: 股票基本数据字典，如果未找到返回None
        """
        try:
            # 构建查询条件
            base_params = {
                "po": 0,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "wbp2u": "|0|0|0|web",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f15,f16,f17,f18,f20,f21,f23,f62,f64,f65,f66,f70,f71,f72",
                "pz": 100,
                "pn": 1,
            }

            # 获取总数
            params = {**base_params, "pn": 1, "pz": 1}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url, params=params, headers=self.headers
                ) as response:
                    data = await response.json()
                    total = data.get("data", {}).get("total", 0)

            if total > 0:
                logger.info(f"开始搜索股票: {query}")
                # 获取所有数据
                page_size = 100
                total_pages = (total + page_size - 1) // page_size

                # 转换为小写进行不区分大小写的搜索
                query_lower = query.lower()

                # 尝试将query拆分成几个可能的股票名称/代码
                possible_stocks = []
                if len(query) >= 2:
                    # 添加完整查询作为可能的股票名称
                    possible_stocks.append(query_lower)

                    # 如果查询包含数字和非数字部分，分别添加为可能的股票代码和名称
                    numeric_part = "".join(filter(str.isdigit, query))
                    alpha_part = "".join(filter(lambda x: not x.isdigit(), query))
                    if numeric_part and len(numeric_part) >= 2:
                        possible_stocks.append(numeric_part)
                    if alpha_part and len(alpha_part) >= 2:
                        possible_stocks.append(alpha_part.lower())

                    # 尝试提取2-6个字符的子串作为可能的股票名称
                    for start in range(len(query)):
                        for length in range(2, min(7, len(query) - start + 1)):
                            substr = query[start : start + length].lower()
                            if substr not in possible_stocks:
                                possible_stocks.append(substr)
                else:
                    possible_stocks.append(query_lower)

                best_match = None
                best_score = 0

                for page in range(1, total_pages + 1):
                    params = {**base_params, "pn": page}
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                self.base_url, params=params, headers=self.headers
                            ) as response:
                                data = await response.json()
                                stocks = data.get("data", {}).get("diff", [])

                                if stocks:
                                    for stock in stocks:
                                        stock_code = stock.get("f12", "").lower()
                                        stock_name = stock.get("f14", "").lower()

                                        # 尝试不同的匹配方式，赋予不同的分数
                                        score = 0

                                        # 完全匹配股票代码得分最高
                                        if query_lower == stock_code:
                                            score = 100
                                        # 完全匹配股票名称得分次高
                                        elif query_lower == stock_name:
                                            score = 90
                                        else:
                                            # 检查所有可能的股票名称/代码子串
                                            for possible in possible_stocks:
                                                # 子串包含在股票名称中
                                                if possible in stock_name:
                                                    substring_score = (
                                                        len(possible) / len(stock_name)
                                                    ) * 80
                                                    score = max(score, substring_score)
                                                # 子串等于股票代码
                                                elif possible == stock_code:
                                                    score = max(score, 85)
                                                # 子串是股票代码的前缀
                                                elif (
                                                    stock_code.startswith(possible)
                                                    and len(possible) >= 4
                                                ):
                                                    prefix_score = (
                                                        len(possible) / len(stock_code)
                                                    ) * 75
                                                    score = max(score, prefix_score)

                                        # 如果得分比当前最佳匹配高，更新最佳匹配
                                        if score > best_score:
                                            # 预处理市场类型
                                            market = "其他"
                                            if stock_code.startswith("6"):
                                                market = "上证"
                                            elif stock_code.startswith(("0", "3")):
                                                market = "深证"
                                            elif stock_code.startswith(("4", "8")):
                                                market = "北证"

                                            best_match = {
                                                "code": stock_code,
                                                "name": stock_name,
                                                "current_price": safe_float(
                                                    stock.get("f2", 0)
                                                ),
                                                "change_percent": safe_float(
                                                    stock.get("f3", 0)
                                                ),
                                                "change_amount": safe_float(
                                                    stock.get("f4", 0)
                                                ),
                                                "volume": round(
                                                    safe_float(stock.get("f5", 0))
                                                    / 10000,
                                                    2,
                                                ),
                                                "amount": round(
                                                    safe_float(stock.get("f6", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "amplitude": safe_float(
                                                    stock.get("f7", 0)
                                                ),
                                                "turnover_rate": safe_float(
                                                    stock.get("f8", 0)
                                                ),
                                                "pe_ratio": safe_float(
                                                    stock.get("f9", 0)
                                                ),
                                                "volume_ratio": safe_float(
                                                    stock.get("f10", 0)
                                                ),
                                                "high": safe_float(stock.get("f15", 0)),
                                                "low": safe_float(stock.get("f16", 0)),
                                                "open": safe_float(stock.get("f17", 0)),
                                                "prev_close": safe_float(
                                                    stock.get("f18", 0)
                                                ),
                                                "total_value": round(
                                                    safe_float(stock.get("f20", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "current_value": round(
                                                    safe_float(stock.get("f21", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "pb_ratio": safe_float(
                                                    stock.get("f23", 0)
                                                ),
                                                "market": market,
                                                # 资金流向数据
                                                "super_large_inflow": round(
                                                    safe_float(stock.get("f64", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "super_large_outflow": round(
                                                    safe_float(stock.get("f65", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "super_large_net_inflow": round(
                                                    safe_float(stock.get("f66", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "large_inflow": round(
                                                    safe_float(stock.get("f70", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "large_outflow": round(
                                                    safe_float(stock.get("f71", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "large_net_inflow": round(
                                                    safe_float(stock.get("f72", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "main_inflow": round(
                                                    (
                                                        safe_float(stock.get("f64", 0))
                                                        + safe_float(
                                                            stock.get("f70", 0)
                                                        )
                                                    )
                                                    / 100000000,
                                                    2,
                                                ),
                                                "main_outflow": round(
                                                    (
                                                        safe_float(stock.get("f65", 0))
                                                        + safe_float(
                                                            stock.get("f71", 0)
                                                        )
                                                    )
                                                    / 100000000,
                                                    2,
                                                ),
                                                "main_net_inflow": round(
                                                    safe_float(stock.get("f62", 0))
                                                    / 100000000,
                                                    2,
                                                ),
                                                "match_score": score,
                                                "match_query": query,
                                                "exact_match": score >= 90,
                                            }
                                            best_score = score

                    except Exception as e:
                        logger.error(f"获取第{page}页数据失败: {str(e)}")
                        continue

                if best_match:
                    logger.info(
                        f"找到最佳匹配股票: {best_match['name']}({best_match['code']}), 匹配分数: {best_match['match_score']}"
                    )
                    return best_match
                else:
                    logger.warning(f"未找到匹配的股票: {query}")
                    return None
            else:
                logger.error("未获取到任何股票数据")
                return None

        except Exception as e:
            logger.error(f"搜索股票时发生错误: {str(e)}")
            return None

    async def fetch_time_line_data(self, stock_code: str) -> Dict:
        """获取股票分时K线数据"""
        try:
            # 确定市场代码
            market = "1" if stock_code.startswith(("6", "9")) else "0"

            # 构建请求参数
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "ndays": "1",  # 获取当天数据
                "iscr": "0",
                "iscca": "0",
                "secid": f"{market}.{stock_code}",
                "forcect": "1",  # 强制获取最新数据
                "pos": "-0",  # 从头开始获取
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.time_line_url, params=params, headers=self.headers
                ) as response:
                    data = await response.json()

                    if not data or "data" not in data:
                        logger.warning(f"获取股票 {stock_code} 分时数据失败: 数据格式错误")
                        return {}

                    trends_data = data["data"]
                    if not trends_data or "trends" not in trends_data:
                        logger.warning(f"获取股票 {stock_code} 分时数据失败: 无数据")
                        return {}

                    # 处理分时数据
                    processed_data = {
                        "stock_code": stock_code,
                        "stock_name": trends_data.get("name", ""),
                        "time_data": [],
                        "price_data": [],
                        "volume_data": [],
                        "avg_price_data": [],
                        "prev_close": safe_float(trends_data.get("preClose", 0)),
                    }

                    # 处理所有分时数据
                    for trend in trends_data["trends"]:
                        items = trend.split(",")
                        if len(items) >= 8:
                            time_str = items[0]
                            # 只保留交易时间段的数据（9:30-15:00）
                            try:
                                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                                if (
                                    (dt.hour == 9 and dt.minute >= 30)
                                    or (dt.hour > 9 and dt.hour < 15)
                                    or (dt.hour == 15 and dt.minute == 0)
                                ):
                                    processed_data["time_data"].append(time_str)
                                    processed_data["price_data"].append(
                                        safe_float(items[2])
                                    )
                                    processed_data["volume_data"].append(
                                        safe_float(items[5])
                                    )
                                    processed_data["avg_price_data"].append(
                                        safe_float(items[7])
                                    )
                            except ValueError:
                                continue

                    return processed_data

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 分时数据失败: {str(e)}")
            return {}

    async def fetch_daily_kline_data(self, stock_code: str, days: int = 100) -> Dict:
        """获取股票日K线数据"""
        try:
            # 确定市场代码
            market = "1" if stock_code.startswith(("6", "9")) else "0"

            # 构建请求参数
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101",  # 日K线
                "fqt": "1",  # 前复权
                "secid": f"{market}.{stock_code}",
                "beg": "0",  # 开始时间，0表示从最新数据开始往前获取
                "end": "20500000",  # 结束时间，默认值
                "lmt": str(days),  # 获取天数
                "forcect": "1",  # 强制获取最新数据
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.daily_kline_url, params=params, headers=self.headers
                ) as response:
                    data = await response.json()

                    if not data or "data" not in data:
                        logger.warning(f"获取股票 {stock_code} 日K线数据失败: 数据格式错误")
                        return {}

                    kline_data = data["data"]
                    if not kline_data or "klines" not in kline_data:
                        logger.warning(f"获取股票 {stock_code} 日K线数据失败: 无数据")
                        return {}

                    # 处理K线数据
                    processed_data = {
                        "stock_code": stock_code,
                        "stock_name": kline_data.get("name", ""),
                        "date_data": [],
                        "open_data": [],
                        "close_data": [],
                        "high_data": [],
                        "low_data": [],
                        "volume_data": [],
                        "amount_data": [],
                        "amplitude_data": [],
                        "change_percent_data": [],
                        "change_amount_data": [],
                        "turnover_rate_data": [],
                    }

                    # 确保只获取指定天数的数据
                    klines = (
                        kline_data["klines"][-days:]
                        if len(kline_data["klines"]) > days
                        else kline_data["klines"]
                    )

                    for kline in klines:
                        items = kline.split(",")
                        if len(items) >= 11:
                            processed_data["date_data"].append(items[0])
                            processed_data["open_data"].append(safe_float(items[1]))
                            processed_data["close_data"].append(safe_float(items[2]))
                            processed_data["high_data"].append(safe_float(items[3]))
                            processed_data["low_data"].append(safe_float(items[4]))
                            processed_data["volume_data"].append(
                                safe_float(items[5]) / 10000
                            )
                            processed_data["amount_data"].append(
                                safe_float(items[6]) / 10000
                            )
                            processed_data["amplitude_data"].append(
                                safe_float(items[7])
                            )
                            processed_data["change_percent_data"].append(
                                safe_float(items[8])
                            )
                            processed_data["change_amount_data"].append(
                                safe_float(items[9])
                            )
                            processed_data["turnover_rate_data"].append(
                                safe_float(items[10])
                            )

                    return processed_data

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 日K线数据失败: {str(e)}")
            return {}

    async def search_stock(self, query: str) -> Optional[Dict]:
        """
        根据股票名称或代码实时搜索股票信息

        Args:
            query: 股票名称或代码

        Returns:
            Dict: 股票信息字典，如果未找到返回None
        """
        try:
            # 1. 获取基本数据
            basic_data = await self.get_basic_data(query)
            if not basic_data:
                return None

            # 2. 获取财务数据
            finance_data = await self.fetch_finance_data(basic_data["code"])

            # 3. 获取分时数据
            time_line_data = await self.fetch_time_line_data(basic_data["code"])

            # 4. 获取日K线数据
            daily_kline_data = await self.fetch_daily_kline_data(basic_data["code"])

            # 5. 合并数据
            result = {
                **basic_data,
                **finance_data,
                "time_line": time_line_data,
                "daily_kline": daily_kline_data,
            }

            # 6. 生成描述文本
            result["description"] = self.format_stock_description(
                result, time_line_data, daily_kline_data
            )

            return result

        except Exception as e:
            logger.error(f"搜索股票时发生错误: {str(e)}")
            return None

    def format_stock_description(
        self, stock_data: Dict, time_line_data: Dict, daily_kline_data: Dict
    ) -> str:
        """
        格式化股票数据为自然语言描述

        Args:
            stock_data: 股票基本数据
            time_line_data: 分时数据
            daily_kline_data: 日K线数据

        Returns:
            str: 格式化后的描述文本
        """
        description = (
            f"【基本信息】\n"
            f"股票名称：{stock_data['name']}\n"
            f"股票代码：{stock_data['code']}\n"
            f"所属市场：{stock_data['market']}\n\n"
            f"【实时行情】\n"
            f"最新价：{stock_data['current_price']}元\n"
            f"涨跌幅：{stock_data['change_percent']}%\n"
            f"涨跌额：{stock_data['change_amount']}元\n"
            f"今开：{stock_data['open']}元\n"
            f"最高：{stock_data['high']}元\n"
            f"最低：{stock_data['low']}元\n"
            f"昨收：{stock_data['prev_close']}元\n\n"
            f"【交易数据】\n"
            f"成交量：{stock_data['volume']}万手\n"
            f"成交额：{stock_data['amount']}亿\n"
            f"振幅：{stock_data['amplitude']}%\n"
            f"换手率：{stock_data['turnover_rate']}%\n"
            f"量比：{stock_data['volume_ratio']}\n\n"
            f"【市值数据】\n"
            f"总市值：{stock_data['total_value']}亿\n"
            f"流通市值：{stock_data['current_value']}亿\n"
            f"总股本：{stock_data['total_shares']}亿股\n"
            f"流通股：{stock_data['circulating_shares']}亿股\n\n"
            f"【估值指标】\n"
            f"市盈率(PE)：{stock_data['pe_ratio']}\n"
            f"市净率(PB)：{stock_data['pb_ratio']}\n\n"
            f"【财务数据】\n"
            f"每股收益(EPS)：{stock_data['eps']}元\n"
            f"净利润：{stock_data['net_profit']}亿\n"
            f"营业收入：{stock_data['revenue']}亿\n"
            f"净资产收益率(ROE)：{stock_data['roe']}%\n"
            f"毛利率：{stock_data['gross_profit_margin']}%\n"
            f"资产负债率：{stock_data['debt_ratio']}%\n\n"
            f"【资金流向】\n"
            f"主力资金净流入：{stock_data['main_net_inflow']}亿\n"
            f"主力资金流入：{stock_data['main_inflow']}亿\n"
            f"主力资金流出：{stock_data['main_outflow']}亿\n"
            f"超大单净流入：{stock_data['super_large_net_inflow']}亿\n"
            f"大单净流入：{stock_data['large_net_inflow']}亿\n\n"
        )

        # 添加分时K线数据描述
        if time_line_data and time_line_data.get("time_data"):
            time_data = time_line_data["time_data"]
            price_data = time_line_data["price_data"]
            volume_data = time_line_data["volume_data"]
            avg_price_data = time_line_data["avg_price_data"]
            prev_close = time_line_data.get("prev_close", price_data[0])

            current_time = datetime.now()
            is_workday = current_time.weekday() < 5
            current_time_str = current_time.strftime("%H:%M")
            is_trading_time = "09:30" <= current_time_str <= "15:00"

            trading_status = (
                "休市" if not is_workday else "交易中" if is_trading_time else "已收盘"
            )

            description += f"【分时行情】（{trading_status}）\n"
            description += f"数据区间：{time_data[0]} 至 {time_data[-1]}\n"

            latest_price = price_data[-1]
            price_change = latest_price - prev_close
            price_change_percent = (price_change / prev_close) * 100

            intraday_high = max(price_data)
            intraday_low = min(price_data)
            intraday_high_time = time_data[price_data.index(intraday_high)].split()[1]
            intraday_low_time = time_data[price_data.index(intraday_low)].split()[1]

            description += (
                f"最新价：{latest_price:.2f}元\n"
                f"涨跌幅：{price_change_percent:+.2f}%\n"
                f"涨跌额：{price_change:+.2f}元\n"
                f"成交总量：{sum(volume_data):.0f}手\n"
                f"均价：{sum(price_data) / len(price_data):.2f}元\n"
                f"分时最高：{intraday_high:.2f}元（{intraday_high_time}）\n"
                f"分时最低：{intraday_low:.2f}元（{intraday_low_time}）\n\n"
            )

            # 获取日期（从第一条记录中提取）
            date_str = time_data[0].split()[0]
            description += f"分时明细（{date_str}）：\n"

            # 创建时间点集合，防止重复
            processed_times = set()
            for i, time_str in enumerate(time_data):
                current_time = time_str.split()[1]
                # 防止重复时间点
                time_key = f"{date_str} {current_time}"
                if time_key in processed_times:
                    continue
                processed_times.add(time_key)

                price_change = price_data[i] - prev_close
                price_change_percent = (price_change / prev_close) * 100
                description += (
                    f"{current_time} "
                    f"价格：{price_data[i]:.2f}元 "
                    f"涨跌：{price_change_percent:+.2f}% "
                    f"成交量：{volume_data[i]:.0f}手 "
                    f"均价：{avg_price_data[i]:.2f}元\n"
                )
            description += "------------------------\n\n"

        # 添加日K线数据描述
        daily_kline_description = ""
        if daily_kline_data and daily_kline_data.get("date_data"):
            date_data = daily_kline_data["date_data"]
            change_percent_data = daily_kline_data["change_percent_data"]

            if len(date_data) >= 60:
                recent_change_percent_data = change_percent_data[-60:]
                recent_date_data = date_data[-60:]
                up_days = sum(1 for cp in recent_change_percent_data if cp > 0)
                down_days = sum(1 for cp in recent_change_percent_data if cp < 0)
                flat_days = len(recent_change_percent_data) - up_days - down_days

                daily_kline_description += "【日K线统计】（近60个交易日）\n"
                daily_kline_description += (
                    f"涨跌统计：\n"
                    f"上涨天数：{up_days}天\n"
                    f"下跌天数：{down_days}天\n"
                    f"平盘天数：{flat_days}天\n"
                )

                if recent_change_percent_data:
                    max_change = max(recent_change_percent_data)
                    min_change = min(recent_change_percent_data)
                    max_date_index = recent_change_percent_data.index(max_change)
                    min_date_index = recent_change_percent_data.index(min_change)

                    daily_kline_description += (
                        f"最大涨幅：{max_change:.2f}%（{recent_date_data[max_date_index]}）\n"
                        f"最大跌幅：{min_change:.2f}%（{recent_date_data[min_date_index]}）\n\n"
                    )

                daily_kline_description += "日K线明细（近10个交易日）：\n"
                # 只显示最近10个交易日的明细
                for i in range(-1, -11, -1):
                    if i >= -len(date_data):  # 确保索引在范围内
                        daily_kline_description += (
                            f"{date_data[i]} "
                            f"开盘：{daily_kline_data['open_data'][i]:.2f} "
                            f"收盘：{daily_kline_data['close_data'][i]:.2f} "
                            f"最高：{daily_kline_data['high_data'][i]:.2f} "
                            f"最低：{daily_kline_data['low_data'][i]:.2f} "
                            f"成交量：{daily_kline_data['volume_data'][i]:.2f}万手 "
                            f"涨跌幅：{daily_kline_data['change_percent_data'][i]:+.2f}% "
                            f"涨跌额：{daily_kline_data['change_amount_data'][i]:+.2f}元\n"
                        )
                daily_kline_description += "\n"

        description += daily_kline_description
        return description
