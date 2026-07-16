# DiF-Check (Demokratie im Feed)

Ein interaktives Dashboard zur Förderung von Medienkompetenz, das Nutzern hilft, Desinformation (Fake News) zu erkennen und durch einen Perspektivwechsel zu verstehen, wie KI-generierte Inhalte erstellt werden.

> ⚠️ **Proof of Concept:** Dieses Projekt wurde primär für Bildungszwecke, Workshops und Prototyping entwickelt.

---

## Dokumentation

| Thema | Dokument |
|---|---|
| Deployment auf der VM (Getting Started, Env-Variablen, Nginx) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Backend-Architektur & Logik (Datenflüsse, KI-Modelle, Routen) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

---

## Schnellstart

Das System wird via Docker Compose orchestriert (Backend, Frontend, Nginx-Reverse-Proxy). Kurzform:

```bash
cp .env.example .env   # .env mit Secrets befüllen – siehe docs/DEPLOYMENT.md, Abschnitt 3
make nginx-conf        # Nginx-Config aus Template generieren (Pflicht vor dem Start)
make create-docker-network
docker compose up -d --build
```

Details, Voraussetzungen und Fallstricke: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Technologien & Tools

Das Projekt ist in Backend und Frontend aufgeteilt und wird via Docker orchestriert.

### Backend (Python)
* **FastAPI** – Web-Framework für die API-Endpunkte und automatische Swagger-Dokumentation.
* **Uvicorn** – ASGI-Webserver für die asynchronen HTTP-Anfragen.
* **Pydantic** – Datenvalidierung zwischen Frontend und Backend.
* **HTTPX** – Asynchroner HTTP-Client für die Anbindung der externen KIs.

### Frontend (HTML / JS)
* **React** – UI-Bibliothek für die interaktiven Komponenten (Chatbot, Fake News Fabrik, Quiz).
* **Tailwind CSS** – Utility-First CSS Framework für das responsive Design.

### Externe KI- & Analyse-APIs
* **IONOS AI** – Primäres Sprachmodell (`meta-llama/Llama-3.3-70B-Instruct`, konfigurierbar über `MODEL_ID`) für Textanalyse, Prompt-Generierung und das Schreiben der Fake News. Nutzt zudem `FLUX.1-schnell` für die Bildgenerierung.
* **Tavily** – Suchmaschinen-API, vom LLM für automatisiertes Lateral Reading (Faktencheck via Websuche) genutzt.
* **Sightengine** – Computer-Vision-API zur Erkennung KI-generierter Bilder.

### Infrastruktur
* **Docker & Docker Compose** – Containerisierung für konsistente Deployments.
* **Nginx** – Reverse Proxy: liefert das Frontend aus und routet `/api/`-Anfragen an das Python-Backend.

---

## Projektstruktur (Backend)

```text
backend/
├── main.py               # App-Initialisierung und Router-Setup
├── core/                 # Konfiguration (.env) und Logging
├── api/routes/           # API-Endpunkte (aufgeteilt in image, text, analysis)
├── schemas/              # Pydantic-Modelle (Datenstrukturen)
├── services/             # Geschäftslogik und API-Calls (LLM, Suche, Sightengine)
└── utils/                # Hilfsfunktionen (z. B. Prompt-Loader, JSON-Parser)
```

Eine ausführliche Beschreibung der Datenflüsse und internen Routen findet sich in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.
