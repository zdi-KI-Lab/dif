# Funktionale Dokumentation (Architektur & Logik)

**Projekt:** DiF-Check / „Fake Checker" (Demokratie im Feed)
**Fokus:** ausschließlich **Backend** ([backend/](../backend/)). Das Frontend wird bewusst ausgeklammert.

---

## 1. Applikationsstruktur

FastAPI-App ([main.py](../backend/main.py)) mit `root_path="/api"`, drei Routern und CORS beschränkt auf die Produktions-Domain. Schichtung:

- **`api/routes/`** — dünne HTTP-Layer, delegieren an Services ([analysis.py](../backend/api/routes/analysis.py), [text.py](../backend/api/routes/text.py), [image.py](../backend/api/routes/image.py)).
- **`services/`** — Geschäftslogik + externe API-Calls ([llm.py](../backend/services/llm.py), [search.py](../backend/services/search.py), [image.py](../backend/services/image.py), [sightengine.py](../backend/services/sightengine.py)).
- **`schemas/`** — Pydantic-Request-Modelle.
- **`utils/`** — Prompt-Loader + robuster LLM-JSON-Parser; Prompts als Markdown in `utils/prompts/`.

Alle externen Calls laufen **asynchron** über `httpx.AsyncClient`. Anfragen und LLM-Rohantworten werden nach `logs/LLM_responses.log` und stdout geloggt ([core/logger.py](../backend/core/logger.py)).

---

## 2. Eingesetzte KI-/Analyse-Modelle im Backend

| Dienst / Modell | Endpoint | Zuständigkeit | Aufgerufen in |
|---|---|---|---|
| **IONOS · `meta-llama/Llama-3.3-70B-Instruct`** (via `MODEL_ID`) | `IONOS_URL` (`…/v1/chat/completions`) | Textanalyse (Faktencheck), Fake-News-Text-Generierung, Bild-Prompt-Generierung | [services/llm.py](../backend/services/llm.py) |
| **IONOS · `black-forest-labs/FLUX.1-schnell`** (hartkodiert) | `…/v1/images/generations` | Text-zu-Bild-Generierung des „Beweis"-Bildes | [services/image.py](../backend/services/image.py) |
| **Tavily** | `https://api.tavily.com/search` | Websuche / Lateral Reading; wird vom LLM per Function-Calling ausgelöst (`search_depth: advanced`, max 3 Quellen) | [services/search.py](../backend/services/search.py) |
| **Sightengine · Modell `genai`** | `https://api.sightengine.com/1.0/check.json` | Erkennung KI-generierter Bilder (Upload oder URL) | [services/sightengine.py](../backend/services/sightengine.py) |

> **Hinweis:** Die README nennt „Meta-Llama-3.1". Aktiv konfiguriert ist jedoch **Llama-3.3-70B-Instruct**; die 405B-Variante ist in der `.env` auskommentiert. Das LLM ist frei über `MODEL_ID` austauschbar (OpenAI-kompatibles Schema).

---

## 3. Interne Endpunkte (Routen)

Backend-intern ohne `/api`-Präfix definiert; extern via Nginx unter `/api/...` erreichbar. Alle Methoden: **POST**.

| Externe Route | Backend-Route | Request-Schema | Service | Funktion |
|---|---|---|---|---|
| `/api/analyze` | `/analyze` | `AnalysisRequest {text, user_choice}` | `analyze_text` | Nachricht auf Wahrheitsgehalt prüfen (mit Websuche) |
| `/api/analyze-image` | `/analyze-image` | Multipart: `file` **oder** `url` | `analyze_media` | Bild auf KI-Generierung prüfen |
| `/api/generate-fake` | `/generate-fake` | `GenerationRequest {thema, zielgruppe, emotion, strategie}` | `generate_fake_text` | Fake-News-Text erzeugen |
| `/api/generate-image-prompt` | `/generate-image-prompt` | `ImagePromptRequest {schlagzeile, text}` | `generate_image_prompt` | Bild-Prompt aus Fake-News ableiten |
| `/api/generate-image-flux` | `/generate-image-flux` | `ImageGenRequest {prompt}` | `generate_flux_image` | Bild via FLUX generieren |

Laufzeit-Dokumentation: **`/api/docs`** (Swagger) und **`/api/openapi.json`**.

---

## 4. Datenfluss — Hauptfunktion 1: Nachrichten checken

Kernstück ist `analyze_text()` in [services/llm.py](../backend/services/llm.py). Es handelt sich um einen **zweistufigen LLM-Flow mit erzwungenem Tool-Calling** (agentischer Faktencheck):

```
POST /api/analyze  {text, user_choice}
   │
   ▼
[PASS 1]  IONOS Chat Completion
   messages = [ system: analyze_fake_text.md, user: <text> ]
   tools = [web_search],  tool_choice = "required"   ← LLM MUSS eine Suchanfrage stellen
   │
   ├─ LLM liefert tool_call → { query: "<neutrale Suchanfrage>" }
   │
   ▼
[TOOL]  search_tavily(query)
   → Tavily (advanced, max 3, include_answer)
   → formatierte Quellen ("Quelle: <url>\nInhalt: <content>")
   │
   ▼
[PASS 2]  IONOS Chat Completion (ohne Tools)
   messages += assistant(tool_call) + tool(search_results)
             + user("Vergleiche die Behauptung mit den Suchergebnissen …")
   → Antwort = Fließtext-Erklärung  +  JSON-Block
   │
   ▼
[PARSING]  utils/parser.py
   - llm_answer = Text vor dem ersten "{"
   - parse_llm_json() extrahiert den JSON-Block
   → Merge zu einem Response-Objekt
```

**Struktur der Antwort** (vom Prompt [analyze_fake_text.md](../backend/utils/prompts/analyze_fake_text.md) vorgegeben): freundlicher Erklärtext (`llm_answer`) plus JSON mit `overall_score`, `risk_level`, `scores {quelle, emotion, evidenz, kontext}`, `warnsignale`, `lernmomente`, `handlungsempfehlungen`, `quellen_links` (max. 3). Die Analyse folgt einer 7-Schritt-Logik (Quelle → Kontext → Emotion → Evidenz → Gesamtscore/Risiko-Level nach Correctiv-Logik → Quellen/Lernmomente → Ausgabe).

**Robustheit:** Timeout 120 s; strukturierte Fehlerobjekte mit Fehlercodes bei `ReadTimeout` (`TIMEOUT`), HTTP-Fehlern (`API_UNAVAILABLE`), leeren Antworten (`EMPTY_RESPONSE` / `SECOND_PASS_EMPTY`) und fehlgeschlagenem Parsing (`JSON_FAILED`). Fällt (theoretisch) kein Tool-Call an, wird die Direktantwort ohne Websuche verarbeitet.

### 4b. Nebenfluss: Bild-Faktencheck (`/api/analyze-image`)

`analyze_media()` ([services/sightengine.py](../backend/services/sightengine.py)) nimmt entweder einen **Datei-Upload** (`POST` mit `files`) oder eine **URL** (`GET` mit `params`) entgegen, ruft Sightengine mit `models=genai` auf und gibt die **rohe Sightengine-JSON** zurück (u. a. Wahrscheinlichkeit für KI-Generierung). Kein LLM beteiligt.

---

## 5. Datenfluss — Hauptfunktion 2: Fake News generieren

Ein **dreistufiger, vom Client orchestrierter Prozess** — jeder Schritt ist ein eigener Endpunkt; das Frontend ruft sie sequenziell auf:

```
① POST /api/generate-fake  {thema, zielgruppe, emotion, strategie}
      → generate_fake_text()  →  IONOS (Llama 3.3)
      → JSON { schlagzeile, text, manipulationstechniken[], warnsignale[] }
                    │
                    ▼
② POST /api/generate-image-prompt  {schlagzeile, text}
      → generate_image_prompt()  →  IONOS (Llama 3.3)
      → { midjourney_prompt: "<deutscher Bild-Prompt>" }
        (Prompt zielt auf ein „authentisch-unperfektes" Beweisfoto,
         explizit ohne Text/Buchstaben im Bild)
                    │
                    ▼
③ POST /api/generate-image-flux  {prompt}
      → generate_flux_image()  →  IONOS FLUX.1-schnell (1024×1024, b64_json)
      → { image_url: "data:image/png;base64,…", revised_prompt }
```

- **Schritt ①** ([text.py](../backend/api/routes/text.py) → `generate_fake_text`): Erzeugt aus den vier Parametern über [generate_fake_text.md](../backend/utils/prompts/generate_fake_text.md) einen manipulativen Text als JSON. Der Prompt erzwingt reine JSON-Ausgabe; `parse_llm_json` sichert das Parsing ab.
- **Schritt ②** ([image.py](../backend/api/routes/image.py) → `generate_image_prompt`): Leitet aus Schlagzeile + Textauszug einen deutschen Bild-Prompt ab ([generate_image_prompt.md](../backend/utils/prompts/generate_image_prompt.md)). Rückgabe ist ein reiner String (Feldname `midjourney_prompt`, technisch aber für FLUX bestimmt).
- **Schritt ③** ([image.py](../backend/api/routes/image.py) → `generate_flux_image`): Ruft den IONOS-Bild-Endpoint mit `FLUX.1-schnell` auf und liefert das Bild als Base64-Data-URI zurück (kein externes Hosting).

**Didaktischer Zweck (Perspektivwechsel):** Der Nutzer erlebt, wie leicht sich Text **und** passendes „Beweisbild" für Desinformation synthetisieren lassen — die zurückgelieferten `manipulationstechniken` und `warnsignale` machen die Manipulation anschließend transparent.

---

## 6. Querschnitts-Aspekte

- **Prompt-Management:** Prompts sind als Markdown ausgelagert und werden beim Import von `services/llm.py` einmalig geladen ([utils/prompt_loader.py](../backend/utils/prompt_loader.py)). Änderungen am KI-Verhalten erfolgen ohne Code-Änderung über die `.md`-Dateien.
- **LLM-JSON-Parsing** ([utils/parser.py](../backend/utils/parser.py)): Extrahiert den JSON-Block zwischen erstem `{` und letztem `}`, korrigiert unbalancierte Klammern und parst mit `strict=False` — Toleranz gegenüber „geschwätzigen" LLM-Antworten.
- **Logging:** Zentraler Logger schreibt strukturiert (Anfragen, LLM-Rohantworten, Tool-Calls, Suchtreffer) nach Datei **und** stdout.
- **Sicherheit (Backend):** Die Endpunkte selbst sind **nicht authentifiziert** (keine Auth auf App-Ebene); der Zugriffsschutz liegt vorgelagert am Edge-Proxy per **Basic-Auth** (gesamte Seite inkl. `/api/*` hinter Login, siehe [DEPLOYMENT.md, Abschnitt 6](DEPLOYMENT.md#6-zugang-absichern-basic-auth)) sowie CORS-Restriktion und Rate-Limiting. Basic-Auth ist ein gemeinsames Login für alle; für feingranulareren Missbrauchsschutz wäre Auth/Quota **pro Client** auf den generativen Routen sinnvoll.
