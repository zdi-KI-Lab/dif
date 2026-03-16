
#  DiF-Check (Demokratie im Feed)

Ein interaktives Dashboard zur Förderung von Medienkompetenz, das Nutzern hilft, Desinformation (Fake News) zu erkennen und durch einen Perspektivwechsel zu verstehen, wie KI-generierte Inhalte erstellt werden.

---

## ⚠️ Wichtiger Sicherheitshinweis (Proof of Concept)

Dieses Projekt ist ein **Proof of Concept (PoC)** und wurde primär für Bildungszwecke, Workshops und Prototyping entwickelt. 

---

## Verwendete Technologien & Tools

Dieses Projekt ist in Backend und Frontend aufgeteilt und wird via Docker orchestriert.

### Backend (Python)
* **FastAPI:** Das Web-Framework für die API-Endpunkte und automatische Swagger-Dokumentation.
* **Uvicorn:** Der ASGI-Webserver, der die asynchronen HTTP-Anfragen verarbeitet.
* **Pydantic:** Für die strikte Datenvalidierung zwischen Frontend und Backend.
* **HTTPX:** Asynchroner HTTP-Client für die performante Anbindung der externen KIs.

### Frontend (HTML / JS)
* **React:** UI-Bibliothek für den Aufbau der interaktiven Komponenten (Chatbot, Fake News Fabrik, Quiz).
* **Tailwind CSS:** Utility-First CSS Framework für das responsive Design.

### Externe KI- & Analyse-APIs
* **IONOS AI:** Primäres Sprachmodell (Meta-Llama-3.1) für die Textanalyse, Prompt-Generierung und das Schreiben der Fake News. Nutzt zudem `FLUX.1-schnell` für die Bildgenerierung.
* **Tavily:** Suchmaschinen-API, die vom LLM für automatisiertes Lateral Reading (Faktencheck via Websuche) genutzt wird.
* **Sightengine:** Computer-Vision-API zur Erkennung von KI-generierten Bildern.

### Infrastruktur
* **Docker & Docker Compose:** Containerisierung für konsistente Deployments.
* **Nginx:** Reverse Proxy, der das Frontend ausliefert und `/api/`-Anfragen an das Python-Backend routet.

---

## Projektstruktur (Backend)

Das Backend folgt den Prinzipien des *Clean Code* und der *Separation of Concerns*:

```text
backend/
├── main.py               # App-Initialisierung und Router-Setup
├── core/                 # Konfiguration (.env) und Logging
├── api/routes/           # API-Endpunkte (aufgeteilt in image, text, analysis)
├── schemas/              # Pydantic-Modelle (Datenstrukturen)
├── services/             # Geschäftslogik und API-Calls (LLM, Suche, Sightengine)
└── utils/                # Hilfsfunktionen (z.B. Prompt-Loader, JSON-Parser)
