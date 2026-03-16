import httpx
from core.config import settings
from core.logger import logger


async def generate_flux_image(prompt: str) -> dict:
    if not settings.IONOS_API_TOKEN: 
        return {"error": "Kein IONOS API Key konfiguriert."}

    url = "https://openai.inference.de-txl.ionos.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {settings.IONOS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell", 
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"IONOS RAW ERROR: {error_msg}")
                return {"error": f"Bildfehler: {error_msg}"}
            
            data = response.json()
            
            if 'b64_json' in data['data'][0]:
                image_url = f"data:image/png;base64,{data['data'][0]['b64_json']}"
            elif 'url' in data['data'][0]:
                image_url = data['data'][0]['url']
            else:
                return {"error": "API hat weder URL noch Bilddaten gesendet."}
            
            logger.info("Bild erfolgreich generiert! (FLUX)")
            return {"image_url": image_url, "revised_prompt": prompt}
            
    except Exception as e:
        logger.error(f"Fehler bei Bildgenerierung (FLUX): {e}")
        return {"error": str(e)}