"""
Web information fetching actions.
"""
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any

from app.services.actions.base import ActionExecutor, ActionResult
from app.services.actions.registry import action_registry
from app.core.logging import logger


@action_registry.register("fetch_web_info")
class FetchWebInfoAction(ActionExecutor):
    """
    Fetch information from a web page.

    Parameters:
        url: URL to fetch
        extract: Optional CSS selector or XPath to extract specific content
    """

    def validate_parameters(self) -> None:
        """Validate parameters."""
        if "url" not in self.parameters:
            raise ValueError("Missing required parameter: url")

        url = self.parameters["url"]
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {url}")

    async def execute(self) -> ActionResult:
        """Fetch web page content."""
        try:
            url = self.parameters["url"]
            extract_selector = self.parameters.get("extract")

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract specific content if selector provided
                if extract_selector:
                    elements = soup.select(extract_selector)
                    content = [elem.get_text(strip=True) for elem in elements]
                else:
                    # Get page title and meta description
                    title = soup.title.string if soup.title else "No title"
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    description = meta_desc.get("content") if meta_desc else ""

                    content = {
                        "title": title,
                        "description": description,
                        "text_preview": soup.get_text()[:500]
                    }

                logger.info(f"Fetched web content from {url}")

                return ActionResult(
                    success=True,
                    data={
                        "url": url,
                        "status_code": response.status_code,
                        "content": content
                    }
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return ActionResult(
                success=False,
                error=f"HTTP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching web content: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """Simulate web fetch."""
        return ActionResult(
            success=True,
            data={
                "dry_run": True,
                "url": self.parameters["url"],
                "message": "Would fetch content from this URL"
            }
        )

    def get_description(self) -> str:
        """Get action description."""
        return f"Fetch information from {self.parameters.get('url', 'unknown URL')}"

    def get_safety_warnings(self) -> list[str]:
        """Get safety warnings."""
        return [
            "This will access an external website",
            "Ensure the URL is from a trusted source"
        ]


@action_registry.register("search_web")
class SearchWebAction(ActionExecutor):
    """
    Search the web using a search engine.

    Parameters:
        query: Search query
        max_results: Maximum number of results (default: 5)
    """

    def validate_parameters(self) -> None:
        """Validate parameters."""
        if "query" not in self.parameters:
            raise ValueError("Missing required parameter: query")

    async def execute(self) -> ActionResult:
        """Perform web search."""
        try:
            query = self.parameters["query"]
            max_results = self.parameters.get("max_results", 5)

            # Note: In production, you would use a search API like Google Custom Search
            # or DuckDuckGo API. For now, we'll return a placeholder.

            logger.info(f"Web search executed: {query}")

            return ActionResult(
                success=True,
                data={
                    "query": query,
                    "message": "Web search would be performed (search API not configured)",
                    "note": "To enable: configure Google Custom Search API or DuckDuckGo API"
                }
            )

        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )

    async def dry_run(self) -> ActionResult:
        """Simulate web search."""
        return ActionResult(
            success=True,
            data={
                "dry_run": True,
                "query": self.parameters["query"],
                "message": f"Would search for: {self.parameters['query']}"
            }
        )

    def get_description(self) -> str:
        """Get action description."""
        return f"Search the web for: {self.parameters.get('query', 'unknown')}"
