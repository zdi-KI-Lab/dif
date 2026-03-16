import json
from core.logger import logger

def parse_llm_json(content: str, context: str = "unknown") -> dict | None:
    """Extracts and parses JSON from a string outputted by an LLM."""
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1:
            return None
        
        json_str = content[start:end]
        
        if json_str.count('{') > json_str.count('}'):
            json_str += "}"
            
        return json.loads(json_str, strict=False)
    except Exception as e:
        logger.error(f"[{context}] JSON-Struktur-Fehler: {e}")
        return None