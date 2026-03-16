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

    async with httpx.AsyncClient(timeout=60.0) as client:
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

    async with httpx.AsyncClient(timeout=60.0) as client:
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
    """Analyzes a text for fake news indicators, optionally using web search."""
    logger.info(f"USER-WAHL (Eindruck): {user_choice}")
    
    messages = [
        {"role": "system", "content": ANALYZE_TEXT_PROMPT},
        {"role": "user", "content": text}
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        # First pass: Ask the LLM if it needs to search the web
        response = await client.post(
            settings.IONOS_URL,
            headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
            json={
                "model": settings.MODEL_ID,
                "messages": messages,
                "tools": TOOLS_DEFINITION,
                "tool_choice": "auto"
            }
        )
        message = response.json()['choices'][0]['message']

        # Check if  LLM decided to use the web search tool
        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            args = json.loads(tool_call["function"]["arguments"])
            search_query = args.get("query")
            
            # Execute the search
            search_results = await search_tavily(search_query)
            
            # Append history and search results for the final pass
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

            # Second pass: Generate final analysis based on search results
            final_res = await client.post(
                settings.IONOS_URL,
                headers={"authorization": f"Bearer {settings.IONOS_API_TOKEN}"},
                json={"model": settings.MODEL_ID, "messages": messages}
            )
            raw_content = final_res.json()['choices'][0]['message']['content']
            logger.info("[FLOW] Analyse MIT Websuche abgeschlossen.")
        else:
            raw_content = message['content']
            logger.info("[FLOW] Analyse OHNE Websuche (Direktantwort).")

    # Extract JSON and leading text
    if "{" in raw_content:
        llm_text = raw_content.split("{", 1)[0].strip()
    else:
        llm_text = raw_content

    json_data = parse_llm_json(raw_content, "ANALYZE")
    
    if json_data:
        json_data["llm_answer"] = llm_text
        return json_data
    return {"llm_answer": raw_content, "error": "JSON_FAILED"}