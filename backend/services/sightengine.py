import httpx
import json
from fastapi import UploadFile
from core.config import settings

async def analyze_media(file: UploadFile | None = None, url: str | None = None) -> dict:
    """Analyzes an image file or URL using Sightengine."""
    output = None
    
    if file:
        files = {"media": (file.filename, file.file, file.content_type)}
        params = {
            "models": "genai", 
            'api_user': settings.SIGHTENGINE_USER,
            'api_secret': settings.SIGHTENGINE_API
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)
            output = response.json()
            
    elif url:
        params = {
            'url': url,
            'models': 'genai',
            'api_user': settings.SIGHTENGINE_USER,
            'api_secret': settings.SIGHTENGINE_API
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get('https://api.sightengine.com/1.0/check.json', params=params)
            output = response.json()

    if not output:
        return {"error": "Kein Bild oder URL angegeben!"}
    
    return output