import asyncio
import httpx
from core.config import settings

async def test_ionos():
    print(f"Versuche Verbindung zu IONOS herzustellen...")
    print(f"URL: {settings.IONOS_URL}")
    print(f"Model: {settings.MODEL_ID}")
    print("-" * 40)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.IONOS_URL,
                headers={"Authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
                json={
                    "model": settings.MODEL_ID,
                    "messages": [{"role": "user", "content": "Antworte nur mit dem Wort: Verbunden"}]
                }
            )
            
            print(f"HTTP Status: {response.status_code}")
            print("Antwort vom Server:")
            print(response.json())
            
    except httpx.ReadTimeout:
        print("FEHLER: Timeout! Der Server hat nach 30 Sekunden nicht geantwortet.")
    except Exception as e:
        print(f"FEHLER: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ionos())