from langchain_tavily import TavilySearch

from app.config import settings


def get_web_search() -> TavilySearch:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    return TavilySearch(max_results=5, tavily_api_key=settings.tavily_api_key)
