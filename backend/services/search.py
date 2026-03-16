import httpx
from core.config import settings
from core.logger import logger

async def search_tavily(query: str) -> str:
    """Executes a web search using the Tavily API."""
    logger.info(f"[TOOL_CALL] Starte Websuche für: {query}")
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced", 
        "max_results": 3,
        "include_answer": True
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        data = response.json()
        results = data.get("results", [])
        
        logger.info(f"[SEARCH_RESULT] {len(results)} Quellen gefunden.")
        
        formatted_results = []
        for res in results:
            formatted_results.append(f"Quelle: {res['url']}\nInhalt: {res['content']}")
            
        return "\n\n".join(formatted_results)