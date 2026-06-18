import json
import httpx
from core.config import settings
from core.logger import logger
from utils.parser import parse_llm_json
from services.search import search_tavily
from utils.prompt_loader import load_prompt  

ANALYZE_TEXT_PROMPT = load_prompt("analyze_fake_text.md")
GENERATE_TEXT_PROMPT = load_prompt("generate_fake_text.md")
GENERATE_IMAGE_PROMPT = load_prompt("generate_image_prompt.md")

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Sucht nach Fakten im Internet. WICHTIG: Formuliere die Suchanfrage neutral und ergebnisoffen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Ein präziser Suchbegriff für den Faktencheck, z.B. 'Zoologe Dr. Felix Braun Sonnental echt'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

async def generate_fake_text(thema: str, zielgruppe: str, emotion: str, strategie: str) -> dict:
    """Generates the fake news text based on user parameters."""
    logger.info(f"PARAMETER: Thema: {thema} | Zielgruppe: {zielgruppe} | Emotion: {emotion} | Strategie: {strategie}")

    prompt = GENERATE_TEXT_PROMPT.format(
        thema=thema, zielgruppe=zielgruppe, emotion=emotion, strategie=strategie
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            settings.IONOS_URL,
            headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
            json={
                "model": settings.MODEL_ID,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
    
    raw_content = response.json()['choices'][0]['message']['content']
    logger.info(f"LLM-ROHANTWORT:\n{raw_content}")
    
    json_data = parse_llm_json(raw_content, "GENERATE")
    return json_data if json_data else {"error": "Generierung fehlgeschlagen"}

async def generate_image_prompt(schlagzeile: str, text_snippet: str) -> str:
    """Generates a Flux prompt based on the generated fake news."""
    formatted_prompt = GENERATE_IMAGE_PROMPT.format(schlagzeile=schlagzeile, text_snippet=text_snippet)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            settings.IONOS_URL,
            headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
            json={
                "model": settings.MODEL_ID,
                "messages": [{"role": "user", "content": formatted_prompt}]
            }
        )
    
    return response.json()['choices'][0]['message']['content'].strip()

async def analyze_text(text: str, user_choice: str) -> dict:
    """
    Analyzes a text for fake news indicators, optionally using web search.
    Includes robust error handling for timeouts and API failures.
    """
    logger.info(f"USER-WAHL (Eindruck): {user_choice}")
    
    messages = [
        {"role": "system", "content": ANALYZE_TEXT_PROMPT},
        {"role": "user", "content": text}
    ]

    raw_content = ""
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            
            response = await client.post(
                settings.IONOS_URL,
                headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
                json={
                    "model": settings.MODEL_ID,
                    "messages": messages,
                    "tools": TOOLS_DEFINITION,
                    "tool_choice": "required"
                }
            )

            
            response.raise_for_status()
            resp_data = response.json()
            if not resp_data.get('choices'):
                logger.error(f"API returned no choices: {resp_data}")
                return {"llm_answer": "Die KI hat keine Antwort geliefert.", "error": "EMPTY_RESPONSE"}

            message = resp_data['choices'][0]['message']

            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0]
                args = json.loads(tool_call["function"]["arguments"])
                search_query = args.get("query")
                
                logger.info(f"[FLOW] Tool Call detected. Suche nach: {search_query}")
                
                # Execute the search 
                search_results = await search_tavily(search_query)
                
                # Append history for the second pass
                messages.append(message)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": "web_search",
                    "content": search_results
                })
                messages.append({
                    "role": "user", 
                    "content": "Vergleiche die Behauptung mit den Suchergebnissen.\nFORMAT-ANWEISUNG:\n1. ZUERST: Eine kurze Erklärung an den Nutzer.\n2. DANACH: Der JSON-Block."
                })

                # --- PASS 2: Final Analysis (incorporating search results) ---
                final_res = await client.post(
                    settings.IONOS_URL,
                    headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
                    json={"model": settings.MODEL_ID, "messages": messages}
                )
                final_res.raise_for_status()
                
                final_data = final_res.json()
                if not final_data.get('choices'):
                    return {"llm_answer": "Zweit-Analyse fehlgeschlagen.", "error": "SECOND_PASS_EMPTY"}
                
                raw_content = final_data['choices'][0]['message']['content']
                logger.info("[FLOW] Analyse MIT Websuche abgeschlossen.")
            
            else:
                raw_content = message.get('content', '')
                logger.info("[FLOW] Analyse OHNE Websuche (Direktantwort).")

    except httpx.ReadTimeout:
        logger.error("IONOS API Timeout nach 120 Sekunden.")
        return {"llm_answer": "Der KI-Dienst hat zu lange für eine Antwort gebraucht (Timeout).", "error": "TIMEOUT"}
    except httpx.HTTPStatusError as e:
        logger.error(f"IONOS API Fehler {e.response.status_code}: {e.response.text}")
        return {"llm_answer": "Der KI-Dienst ist derzeit überlastet oder nicht erreichbar.", "error": "API_UNAVAILABLE"}
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in analyze_text: {str(e)}")
        return {"llm_answer": "Ein technischer Fehler ist in der Verarbeitung aufgetreten.", "error": str(e)}

    if not raw_content:
        return {"llm_answer": "Kein Inhalt generiert.", "error": "NO_CONTENT"}

    if "{" in raw_content:
        llm_text = raw_content.split("{", 1)[0].strip()
    else:
        llm_text = raw_content

    json_data = parse_llm_json(raw_content, "ANALYZE")
    
    if json_data:
        json_data["llm_answer"] = llm_text
        return json_data
    
    return {"llm_answer": raw_content, "error": "JSON_FAILED"}