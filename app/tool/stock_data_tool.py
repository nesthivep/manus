from typing import Dict, Optional, Union
import os
import aiohttp
from app.tool.base import BaseTool
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def safe_float(value: Union[str, float, int, None], default: float = 0.0) -> float:
    """
    Safely convert input value to float
    
    Args:
        value: Input value
        default: Default value
        
    Returns:
        float: Converted float value
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

class StockSearch(BaseTool):
    base_url: str = 'https://push2.eastmoney.com/api/qt/clist/get'
    finance_url: str = 'https://push2.eastmoney.com/api/qt/stock/get'
    time_line_url: str = 'https://push2.eastmoney.com/api/qt/stock/trends2/get'
    daily_kline_url: str = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    stock_themes_url: str = 'https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax'
    headers: Dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://quote.eastmoney.com/",
    }
    max_observe: int = 15000  # Add max_observe attribute, set to 15000

    def __init__(self):
        super().__init__(
            name="stock_search",
            description="东方财富股票数据查询工具，用于获取股票实时行情、财务数据和K线走势。仅在用户明确请求股票数据时使用一次，获取数据后应使用其他工具（如PythonExecute）进行后续分析或可视化。"
        )
        # Update User-Agent in headers
        self.headers["User-Agent"] = os.environ.get('USER_AGENT', self.headers["User-Agent"])
        
        # Add tool parameter schema
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "股票名称或代码，或自然语言查询。例如：贵州茅台、600519、查询腾讯的股价。此工具只需调用一次获取完整数据。"
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str = "", **kwargs):
        """Implement abstract method execute"""
        if not query:
            return "请提供股票名称或代码"
        
        try:
            # Extract stock name (if query is natural language)
            stock_name = self.extract_stock_name(query)
            logger.info(f"查询股票：{query}，提取的股票名称：{stock_name}")
            
            # First try to search using the extracted stock name
            result = await self.search_stock(stock_name)
            
            # If search with extracted name fails, try using the original query
            if not result and stock_name != query:
                logger.info(f"使用提取的名称'{stock_name}'未找到匹配股票，尝试使用完整查询...")
                result = await self.search_stock(query)
                
            if result:
                # Return description text directly
                return result.get("description", "未能获取股票描述信息")
            else:
                return f"未找到与'{query}'匹配的股票，请尝试使用更准确的股票名称或代码"
        except Exception as e:
            logger.error(f"执行股票查询时发生错误: {str(e)}")
            return f"查询股票时出错: {str(e)}"

    async def fetch_finance_data(self, stock_code: str) -> Dict:
        """Get stock financial data"""
        if stock_code.startswith(('90', '92', '93', '94', '95', '96', '97', '98', '99')):
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
                async with session.get(self.finance_url, params=params, headers=self.headers) as response:
                    data = await response.json()
                    if not data or 'data' not in data:
                        logger.warning(f"Failed to get financial data for stock {stock_code}: Response data format error")
                        return self._get_default_finance_data()
                        
                    stock_data = data.get("data", {})
                    if not stock_data:
                        logger.warning(f"Failed to get financial data for stock {stock_code}: No data")
                        return self._get_default_finance_data()

                    return {
                        "total_shares": round(safe_float(stock_data.get("f84")) / 100000000, 2),
                        "circulating_shares": round(safe_float(stock_data.get("f85")) / 100000000, 2),
                        "eps": round(safe_float(stock_data.get("f55")), 4),
                        "net_profit": round(safe_float(stock_data.get("f105")) / 100000000, 2),
                        "revenue": round(safe_float(stock_data.get("f183")) / 100000000, 2),
                        "roe": round(safe_float(stock_data.get("f173")), 2),
                        "gross_profit_margin": round(safe_float(stock_data.get("f186")), 2),
                        "debt_ratio": round(safe_float(stock_data.get("f188")), 2),
                    }
        except Exception as e:
            logger.error(f"Failed to get financial data for stock {stock_code}: {str(e)}")
            return self._get_default_finance_data()

    def _get_default_finance_data(self) -> Dict:
        """Return default financial data"""
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
        Extract stock name from natural language query
        
        Args:
            query: User's natural language query
            
        Returns:
            str: Extracted possible stock name
        """
        # If input is empty, return directly
        if not query or len(query.strip()) == 0:
            return ""
            
        # Common prefixes and suffixes for identifying stock names
        prefixes = ["帮我查询", "帮我搜索", "帮我找", "帮我看看", "帮忙查询", "帮忙搜索", 
                  "帮我", "请帮我", "请帮我查询", "请帮我搜索", "请查询", "请搜索", 
                  "查询", "搜索", "查看", "想知道", "了解", "查一下", "分析", "帮我分析", "分析下", "帮我分析下",
                  "看看", "帮我看下", "了解下", "查询下", "搜索下", "分析一下", "看一下", "查一查", "分析一下"]
        
        suffixes = ["的股票", "的股票数据", "的行情", "的股价", "的走势", "股票", "这只股票", "这个股票", 
                  "公司", "的情况", "的信息", "的分时数据", "的K线", "的日K", "的数据", "的情况如何", 
                  "下周走势", "今日表现", "近期表现", "明天会涨吗", "怎么样", "股价多少", "值得买吗", "能买吗", "如何"]
        
        # Add more middle word patterns
        middle_words = ["这只", "这个", "这家", "的", "下", "这"]
        
        # Sort prefixes and suffixes by length from longest to shortest to avoid substring issues
        prefixes.sort(key=len, reverse=True)
        suffixes.sort(key=len, reverse=True)
        
        # Remove leading phrases
        cleaned_query = query
        for prefix in prefixes:
            if cleaned_query.lower().startswith(prefix.lower()):
                cleaned_query = cleaned_query[len(prefix):].strip()
                break  # Stop once a prefix is matched to avoid duplicate processing
        
        # Remove all possible suffixes, not just one
        changed = True
        while changed:
            changed = False
            for suffix in suffixes:
                if cleaned_query.lower().endswith(suffix.lower()):
                    cleaned_query = cleaned_query[:-len(suffix)].strip()
                    changed = True
                    break
        
        # Try to process middle modifiers
        for word in middle_words:
            if word in cleaned_query:
                parts = cleaned_query.split(word)
                if len(parts) >= 2:
                    # If the first part is non-empty and at least 2 characters, it might be a stock name
                    if parts[0] and len(parts[0]) >= 2:
                        cleaned_query = parts[0].strip()
                    # Otherwise keep original
                    break
        
        # If after processing the result is very short (less than 2 characters), may have processed too much, return original query
        if len(cleaned_query) < 2:
            # Try to extract possible stock names directly from the original query (2-4 consecutive Chinese characters)
            import re
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', query)
            if chinese_words:
                # Filter possible stock names (exclude common non-stock nouns)
                stop_words = ["股票", "走势", "分析", "行情", "查询", "搜索", "帮我", "请帮", "明天", "下周", "情况"]
                candidates = [word for word in chinese_words if word not in stop_words and len(word) >= 2]
                if candidates:
                    return candidates[0]  # Return the first possible stock name
            return query
        
        # If result is non-empty then return it, otherwise return the original query
        return cleaned_query if cleaned_query else query

    async def get_basic_data(self, query: str) -> Optional[Dict]:
        """
        Get stock basic data
        
        Args:
            query: Stock name or code
            
        Returns:
            Dict: Stock basic data dictionary, or None if not found
        """
        try:
            # Build query parameters
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
                "pn": 1
            }
            
            # Get total count
            params = {**base_params, "pn": 1, "pz": 1}
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, headers=self.headers) as response:
                    data = await response.json()
                    total = data.get("data", {}).get("total", 0)
            
            if total > 0:
                logger.info(f"Starting to search for stock: {query}")
                # Get all data
                page_size = 100
                total_pages = (total + page_size - 1) // page_size
                
                # Convert to lowercase for case-insensitive search
                query_lower = query.lower()
                
                # Try to split the query into several possible stock names/codes
                possible_stocks = []
                if len(query) >= 2:
                    # Add the complete query as a possible stock name
                    possible_stocks.append(query_lower)
                    
                    # If the query contains numeric and non-numeric parts, add them as possible stock code and name
                    numeric_part = ''.join(filter(str.isdigit, query))
                    alpha_part = ''.join(filter(lambda x: not x.isdigit(), query))
                    if numeric_part and len(numeric_part) >= 2:
                        possible_stocks.append(numeric_part)
                    if alpha_part and len(alpha_part) >= 2:
                        possible_stocks.append(alpha_part.lower())
                        
                    # Try to extract 2-6 character substrings as possible stock names
                    for start in range(len(query)):
                        for length in range(2, min(7, len(query) - start + 1)):
                            substr = query[start:start+length].lower()
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
                            async with session.get(self.base_url, params=params, headers=self.headers) as response:
                                data = await response.json()
                                stocks = data.get("data", {}).get("diff", [])
                                
                                if stocks:
                                    for stock in stocks:
                                        stock_code = stock.get("f12", "").lower()
                                        stock_name = stock.get("f14", "").lower()
                                        
                                        # Try different matching methods, assign different scores
                                        score = 0
                                        
                                        # Exact match to stock code gets highest score
                                        if query_lower == stock_code:
                                            score = 100
                                        # Exact match to stock name gets second highest score
                                        elif query_lower == stock_name:
                                            score = 90
                                        else:
                                            # Check all possible stock names/code substrings
                                            for possible in possible_stocks:
                                                # Substring contained in stock name
                                                if possible in stock_name:
                                                    substring_score = (len(possible) / len(stock_name)) * 80
                                                    score = max(score, substring_score)
                                                # Substring equals stock code
                                                elif possible == stock_code:
                                                    score = max(score, 85)
                                                # Substring is prefix of stock code
                                                elif stock_code.startswith(possible) and len(possible) >= 4:
                                                    prefix_score = (len(possible) / len(stock_code)) * 75
                                                    score = max(score, prefix_score)
                                        
                                        # If score is higher than current best match, update best match
                                        if score > best_score:
                                            # Preprocess market type
                                            market = "Other"
                                            if stock_code.startswith("6"):
                                                market = "Shanghai"
                                            elif stock_code.startswith(("0", "3")):
                                                market = "Shenzhen"
                                            elif stock_code.startswith(("4", "8")):
                                                market = "Beijing"
                                            
                                            best_match = {
                                                "code": stock_code,
                                                "name": stock_name,
                                                "current_price": safe_float(stock.get("f2", 0)),
                                                "change_percent": safe_float(stock.get("f3", 0)),
                                                "change_amount": safe_float(stock.get("f4", 0)),
                                                "volume": round(safe_float(stock.get("f5", 0)) / 10000, 2),
                                                "amount": round(safe_float(stock.get("f6", 0)) / 100000000, 2),
                                                "amplitude": safe_float(stock.get("f7", 0)),
                                                "turnover_rate": safe_float(stock.get("f8", 0)),
                                                "pe_ratio": safe_float(stock.get("f9", 0)),
                                                "volume_ratio": safe_float(stock.get("f10", 0)),
                                                "high": safe_float(stock.get("f15", 0)),
                                                "low": safe_float(stock.get("f16", 0)),
                                                "open": safe_float(stock.get("f17", 0)),
                                                "prev_close": safe_float(stock.get("f18", 0)),
                                                "total_value": round(safe_float(stock.get("f20", 0)) / 100000000, 2),
                                                "current_value": round(safe_float(stock.get("f21", 0)) / 100000000, 2),
                                                "pb_ratio": safe_float(stock.get("f23", 0)),
                                                "market": market,
                                                # Capital flow data
                                                "super_large_inflow": round(safe_float(stock.get("f64", 0)) / 100000000, 2),
                                                "super_large_outflow": round(safe_float(stock.get("f65", 0)) / 100000000, 2),
                                                "super_large_net_inflow": round(safe_float(stock.get("f66", 0)) / 100000000, 2),
                                                "large_inflow": round(safe_float(stock.get("f70", 0)) / 100000000, 2),
                                                "large_outflow": round(safe_float(stock.get("f71", 0)) / 100000000, 2),
                                                "large_net_inflow": round(safe_float(stock.get("f72", 0)) / 100000000, 2),
                                                "main_inflow": round((safe_float(stock.get("f64", 0)) + safe_float(stock.get("f70", 0))) / 100000000, 2),
                                                "main_outflow": round((safe_float(stock.get("f65", 0)) + safe_float(stock.get("f71", 0))) / 100000000, 2),
                                                "main_net_inflow": round(safe_float(stock.get("f62", 0)) / 100000000, 2),
                                                "match_score": score,
                                                "match_query": query,
                                                "exact_match": score >= 90
                                            }
                                            best_score = score
                                
                    except Exception as e:
                        logger.error(f"Failed to get page {page} data: {str(e)}")
                        continue
                
                if best_match:
                    logger.info(f"Found best matching stock: {best_match['name']}({best_match['code']}), match score: {best_match['match_score']}")
                    return best_match
                else:
                    logger.warning(f"No matching stock found for: {query}")
                    return None
            else:
                logger.error("Failed to get any stock data")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for stock: {str(e)}")
            return None

    async def fetch_time_line_data(self, stock_code: str) -> Dict:
        """Get stock real-time price data"""
        try:
            # Determine market code
            market = "1" if stock_code.startswith(("6", "9")) else "0"
            
            # Build request parameters
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "ndays": "1",  # Get current day data
                "iscr": "0",
                "iscca": "0",
                "secid": f"{market}.{stock_code}",
                "forcect": "1",  # Force get latest data
                "pos": "-0",     # Get from beginning
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.time_line_url, params=params, headers=self.headers) as response:
                    data = await response.json()
                    
                    if not data or "data" not in data:
                        logger.warning(f"Failed to get real-time data for stock {stock_code}: Data format error")
                        return {}
                        
                    trends_data = data["data"]
                    if not trends_data or "trends" not in trends_data:
                        logger.warning(f"Failed to get real-time data for stock {stock_code}: No data")
                        return {}
                    
                    # Process real-time data
                    processed_data = {
                        "stock_code": stock_code,
                        "stock_name": trends_data.get("name", ""),
                        "time_data": [],
                        "price_data": [],
                        "volume_data": [],
                        "avg_price_data": [],
                        "prev_close": safe_float(trends_data.get("preClose", 0))
                    }
                    
                    # Process all real-time data
                    for trend in trends_data["trends"]:
                        items = trend.split(",")
                        if len(items) >= 8:
                            time_str = items[0]
                            # Only keep trading time data (9:30-15:00)
                            try:
                                dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                                if (dt.hour == 9 and dt.minute >= 30) or \
                                   (dt.hour > 9 and dt.hour < 15) or \
                                   (dt.hour == 15 and dt.minute == 0):
                                    processed_data["time_data"].append(time_str)
                                    processed_data["price_data"].append(safe_float(items[2]))
                                    processed_data["volume_data"].append(safe_float(items[5])) 
                                    processed_data["avg_price_data"].append(safe_float(items[7]))
                            except ValueError:
                                continue
                    
                    return processed_data
                    
        except Exception as e:
            logger.error(f"Failed to get real-time data for stock {stock_code}: {str(e)}")
            return {}

    async def fetch_daily_kline_data(self, stock_code: str, days: int = 100) -> Dict:
        """Get stock daily K-line data"""
        try:
            # Determine market code
            market = "1" if stock_code.startswith(("6", "9")) else "0"
            
            # Build request parameters
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101",  # Daily K-line
                "fqt": "1",    # Forward adjustment
                "secid": f"{market}.{stock_code}",
                "beg": "0",    # Start time, 0 means get from the latest data backwards
                "end": "20500000",  # End time, default value
                "lmt": str(days),  # Number of days to get
                "forcect": "1",  # Force get latest data
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.daily_kline_url, params=params, headers=self.headers) as response:
                    data = await response.json()
                    
                    if not data or "data" not in data:
                        logger.warning(f"Failed to get daily K-line data for stock {stock_code}: Data format error")
                        return {}
                        
                    kline_data = data["data"]
                    if not kline_data or "klines" not in kline_data:
                        logger.warning(f"Failed to get daily K-line data for stock {stock_code}: No data")
                        return {}
                    
                    # Process K-line data
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
                        "turnover_rate_data": []
                    }
                    
                    # Ensure only get data for specified days
                    klines = kline_data["klines"][-days:] if len(kline_data["klines"]) > days else kline_data["klines"]
                    
                    for kline in klines:
                        items = kline.split(",")
                        if len(items) >= 11:
                            processed_data["date_data"].append(items[0])
                            processed_data["open_data"].append(safe_float(items[1]))
                            processed_data["close_data"].append(safe_float(items[2]))
                            processed_data["high_data"].append(safe_float(items[3]))
                            processed_data["low_data"].append(safe_float(items[4]))
                            processed_data["volume_data"].append(safe_float(items[5]) / 10000)
                            processed_data["amount_data"].append(safe_float(items[6]) / 10000)
                            processed_data["amplitude_data"].append(safe_float(items[7]))
                            processed_data["change_percent_data"].append(safe_float(items[8]))
                            processed_data["change_amount_data"].append(safe_float(items[9]))
                            processed_data["turnover_rate_data"].append(safe_float(items[10]))
                    
                    return processed_data
                    
        except Exception as e:
            logger.error(f"Failed to get daily K-line data for stock {stock_code}: {str(e)}")
            return {}

    async def search_stock(self, query: str) -> Optional[Dict]:
        """
        Search stock information in real-time by stock name or code
        
        Args:
            query: Stock name or code
            
        Returns:
            Dict: Stock information dictionary, or None if not found
        """
        try:
            # 1. Get basic data
            basic_data = await self.get_basic_data(query)
            if not basic_data:
                return None
                
            # 2. Get financial data
            finance_data = await self.fetch_finance_data(basic_data["code"])
            
            # 3. Get real-time data
            time_line_data = await self.fetch_time_line_data(basic_data["code"])
            
            # 4. Get daily K-line data
            daily_kline_data = await self.fetch_daily_kline_data(basic_data["code"])
            
            # 5. Merge data
            result = {
                **basic_data,
                **finance_data,
                "time_line": time_line_data,
                "daily_kline": daily_kline_data
            }
            
            # 6. Generate description text
            result["description"] = self.format_stock_description(result, time_line_data, daily_kline_data)
            
            return result
                
        except Exception as e:
            logger.error(f"Error searching for stock: {str(e)}")
            return None
            
    def format_stock_description(self, stock_data: Dict, time_line_data: Dict, daily_kline_data: Dict) -> str:
        """
        Format stock data into natural language description
        
        Args:
            stock_data: Stock basic data
            time_line_data: Real-time data
            daily_kline_data: Daily K-line data
            
        Returns:
            str: Formatted description text
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
        
        # Add real-time data description
        if time_line_data and time_line_data.get('time_data'):
            time_data = time_line_data['time_data']
            price_data = time_line_data['price_data']
            volume_data = time_line_data['volume_data']
            avg_price_data = time_line_data['avg_price_data']
            prev_close = time_line_data.get('prev_close', price_data[0])
            
            current_time = datetime.now()
            is_workday = current_time.weekday() < 5
            current_time_str = current_time.strftime('%H:%M')
            is_trading_time = '09:30' <= current_time_str <= '15:00'
            
            trading_status = (
                "休市" if not is_workday else
                "交易中" if is_trading_time else
                "已收盘"
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
            
            # Get date from first record
            date_str = time_data[0].split()[0]
            description += f"Intraday Details ({date_str}):\n"
            
            # Create time point set to prevent duplicates
            processed_times = set()
            for i, time_str in enumerate(time_data):
                current_time = time_str.split()[1]
                # Prevent duplicate time points
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
        
        # Add daily K-line data description
        daily_kline_description = ""
        if daily_kline_data and daily_kline_data.get('date_data'):
            date_data = daily_kline_data['date_data']
            change_percent_data = daily_kline_data['change_percent_data']
            
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
                    if i >= -len(date_data):  # Ensure index is within range
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

