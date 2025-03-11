import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Page, Browser
from app.tool.base import BaseTool, ToolResult
from bs4 import BeautifulSoup


class WechatMPSearch(BaseTool):
    name: str = "wechat_mp_search"
    description: str = """Search WeChat Official Account articles and return relevant results.
Use this tool when you need to find information, articles on WeChat Official Accounts.
Returns a list of WeChat articles matching the search query, including titles, summaries, publisher information and other metadata.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) The search query to submit to WeChat MP search.",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) The number of search results to return. Default is 10.",
                "default": 10,
            },
            "max_retries": {
                "type": "integer",
                "description": "(optional) The maximum number of retries. Default is 3.",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    # 浏览器和页面实例
    _browser: Optional[Browser] = None
    _page: Optional[Page] = None

    async def execute(
        self,
        query: str,
        num_results: int = 10,
        max_retries: int = 3,
    ) -> ToolResult:
        """
        Execute WeChat MP article search

        Args:
            query: search query
            num_results: number of search results
            max_retries: maximum number of retries

        Returns:
            search results list
        """
        for retry in range(max_retries):
            try:
                results = await self._fetch_wechat_results(
                    query=query, num_results=num_results
                )
                return ToolResult(output=results)
            except Exception as e:
                if retry < max_retries - 1:
                    wait_time = 2 * (retry + 1)  # 指数退避
                    print(
                        f"Search error: {str(e)}, waiting {wait_time} seconds to retry ({retry+1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    return ToolResult(
                        error=f"Error searching WeChat articles: {str(e)}"
                    )

        return ToolResult(error="Reached maximum number of retries, search failed")

    async def _fetch_wechat_results(
        self, query: str, num_results: int
    ) -> List[Dict[str, Any]]:
        """Get WeChat MPsearch results"""

        async with async_playwright() as playwright:

            browser = await playwright.chromium.launch(headless=False)

            try:

                page = await browser.new_page()

                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    }
                )

                await page.goto("https://weixin.sogou.com/", wait_until="networkidle")

                await page.wait_for_selector("#query", timeout=10000)

                await page.fill("#query", query)

                await page.click("#searchForm input[type='submit']")

                await page.wait_for_selector(".news-box", timeout=10000)

                html_content = await page.content()

                # parse results
                results = []
                soup = BeautifulSoup(html_content, "html.parser")

                # parse article search results
                article_items = soup.select(".news-box .news-list li")

                for item in article_items[:num_results]:
                    try:
                        # extract article information
                        title_elem = item.select_one("h3 a")
                        title = (
                            title_elem.get_text(strip=True)
                            if title_elem
                            else "No title"
                        )
                        link = title_elem.get("href", "") if title_elem else ""
                        link = "https://weixin.sogou.com" + link

                        # extract summary
                        summary_elem = item.select_one(".txt-info")
                        summary = (
                            summary_elem.get_text(strip=True)
                            if summary_elem
                            else "No summary"
                        )

                        # extract publisher and time
                        account_elem = item.select_one(".all-time-y2")
                        account = (
                            account_elem.get_text(strip=True)
                            if account_elem
                            else "Unknown"
                        )

                        time_elem = item.select_one(".s2")
                        pub_time = (
                            time_elem.get_text(strip=True)
                            if time_elem
                            else "Unknown time"
                        )

                        img_elem = item.select_one(".img-box img")
                        thumbnail = img_elem.get("src", "") if img_elem else ""
                        thumbnail = "https:" + thumbnail

                        # generate hash value for title and link to avoid duplicate results
                        title_hash = hash(title) if title else 0
                        link_hash = hash(link) if link else 0

                        results.append(
                            {
                                "title": title,
                                "link": link,
                                "summary": summary,
                                "account": account,
                                "publish_time": pub_time,
                                "thumbnail": thumbnail,
                                "title_hash": title_hash,
                                "link_hash": link_hash,
                            }
                        )
                    except Exception as e:
                        print(f"Error parsing article item: {str(e)}")
                        continue

                return results

            finally:
                await browser.close()
