# Deployment-Dokumentation (Getting Started)

**Projekt:** DiF-Check / „Fake Checker" (Demokratie im Feed)
**Zielgruppe dieses Dokuments:** Entwickler:innen / DevOps, die das System auf der IONOS-VM in Betrieb nehmen.

> **Sicherheitshinweis:** Die Datei `.env` im Projekt-Root enthält **echte, gültige Secrets** (IONOS-JWT, Tavily-Key, Sightengine-Credentials). Sie ist korrekt über `.gitignore` ausgeschlossen, liegt aber im Klartext auf der VM. In diesem Dokument werden ausschließlich **Variablennamen** verwendet, niemals Werte. Secrets nicht ins Repository committen.

---

## 1. Überblick der Architektur

Das System wird vollständig über **Docker Compose** orchestriert und besteht aus **drei Containern** in einem gemeinsamen Bridge-Netzwerk (`dif-network`). Nach außen ist ausschließlich der Reverse Proxy exponiert (Ports 80/443); Backend und Frontend sind rein netzwerkintern erreichbar.

```
Internet (443/80)
      │
      ▼
┌──────────────────────────────┐
│  nginx-service (dif-proxy)   │  jonasal/nginx-certbot
│  - TLS-Terminierung (Certbot)│  Ports 80:80, 443:443
│  - HTTP→HTTPS Redirect        │
│  - Security-Header, Ratelimit │
└─────────────┬────────────────┘
              │ proxy_pass http://frontend:80
              ▼
┌──────────────────────────────┐
│  frontend (nginx:alpine)     │  statisches SPA + API-Router
│  location /      → SPA        │
│  location /api/  → backend    │  (strippt /api/-Präfix)
└─────────────┬────────────────┘
              │ proxy_pass http://backend:8000/
              ▼
┌──────────────────────────────┐
│  backend (FastAPI/Uvicorn)   │  Python 3.11, Port 8000 (intern)
└──────────────────────────────┘
```

Wichtig: Es existieren **zwei Nginx-Ebenen**. Der `nginx-service` ist der TLS-Edge-Proxy; der `frontend`-Container ist zugleich Webserver für das SPA **und** interner API-Router.

---

## 2. Die Container im Detail

Quelle: [docker-compose.yml](../docker-compose.yml)

| Service | Image / Build | Ports | Zweck |
|---|---|---|---|
| `backend` | Build aus [backend/Dockerfile](../backend/Dockerfile) | keine (nur intern `:8000`) | FastAPI-Applikation (KI-Logik) |
| `frontend` | `nginx:alpine` | keine (nur intern `:80`) | Liefert SPA aus, routet `/api/` zum Backend |
| `nginx-service` | `jonasal/nginx-certbot:latest` | `80:80`, `443:443` | Edge Reverse Proxy + automatisches Let's-Encrypt |

### Backend-Container ([backend/Dockerfile](../backend/Dockerfile))

- Basis-Image: `python:3.11-slim`
- Dependencies (per `pip`, keine `requirements.txt`): `fastapi uvicorn pydantic httpx python-dotenv python-multipart`
- Startbefehl: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Volumes: `./backend:/app` und `./backend/logs:/app/logs`

> **Betriebshinweis:** Das Backend läuft mit `--reload` und einem Bind-Mount des Quellcodes (`./backend:/app`). Der Container führt damit effektiv den **Host-Code mit Hot-Reload** aus (Entwicklungsmodus). Für einen echten Produktivbetrieb sollte `--reload` entfernt und ggf. mit mehreren Uvicorn-Workern gestartet werden.

### Frontend-Container

Mountet das statische SPA (`./frontend` → `/usr/share/nginx/html`) und die interne Nginx-Config ([nginx/frontend.conf](../nginx/frontend.conf), read-only).

### nginx-service-Container

- Liest die Server-Konfiguration aus `./nginx/active` (gemountet nach `/etc/nginx/user_conf.d`).
- Verwaltet Zertifikate in `./letsencrypt` (gemountet nach `/etc/letsencrypt`).
- Erhält die Certbot-Kontakt-E-Mail über die Umgebungsvariable `CERTBOT_EMAIL` (aus `CERTBOT_UPDATES_RECEIVER`).
- `depends_on: [backend, frontend]`.

---

## 3. Zwingend erforderliche Umgebungsvariablen (`.env`)

Alle Variablen liegen in `.env` im Projekt-Root. Die Datei wird vom Backend (`env_file` in Compose, geladen via `python-dotenv` in [backend/core/config.py](../backend/core/config.py)), vom `Makefile` und von Compose selbst gelesen.

### 3.1 KI- & Analyse-Dienste (Backend-Pflicht)

| Variable | Verwendung im Code | Erforderlich |
|---|---|---|
| `IONOS_API_TOKEN` | Bearer-Token für IONOS AI Model Hub (LLM + FLUX). [services/llm.py](../backend/services/llm.py), [services/image.py](../backend/services/image.py) | **Ja** |
| `IONOS_URL` | Chat-Completions-Endpoint, z. B. `https://openai.inference.de-txl.ionos.com/v1/chat/completions` | **Ja** |
| `MODEL_ID` | Aktives LLM, aktuell `meta-llama/Llama-3.3-70B-Instruct` | **Ja** |
| `TAVILY_API_KEY` | Websuche für den Faktencheck. [services/search.py](../backend/services/search.py) | **Ja** |
| `SIGHTENGINE_USER` | Sightengine `api_user` (Bild-KI-Erkennung). [services/sightengine.py](../backend/services/sightengine.py) | **Ja** |
| `SIGHTENGINE_API` | Sightengine `api_secret` | **Ja** |
| `OPENAI_API_KEY` | In [config.py](../backend/core/config.py) eingelesen, aktuell **nicht genutzt** | Optional |

### 3.2 Infrastruktur / Deployment

| Variable | Verwendung |
|---|---|
| `DOMAIN` | Domain für Nginx-Config-Generierung (`make nginx-conf`) und Zertifikatspfade, z. B. `demokratie-im-feed.de` |
| `TARGET` | Proxy-Ziel des Edge-Proxys, i. d. R. `frontend:80` |
| `BASE_URL` | Basis-URL der Anwendung (z. B. `https://demokratie-im-feed.de`) |
| `CERTBOT_UPDATES_RECEIVER` | E-Mail für Let's-Encrypt-Benachrichtigungen (wird zu `CERTBOT_EMAIL`) |
| `SSL_DOCKER_MOUNT` | Legacy/optional, in aktueller Compose-Datei nicht referenziert |

> **CORS:** Zusätzlich ist im Backend ([main.py](../backend/main.py)) die erlaubte Origin **fest** auf `https://demokratie-im-feed.de` (+ `www`) gesetzt. Bei einer neuen Domain muss dies **im Code** angepasst werden (nicht per `.env`).

> **Typo in der aktuellen `.env`:** Hinter dem Wert von `SSL_DOCKER_MOUNT` steht ein loses `al.`. Die Variable wird in Compose nicht verwendet, daher ist der Effekt aktuell harmlos — beim Aufräumen entfernen.

### 3.3 Minimal-Template `.env`

```dotenv
# --- IONOS AI Model Hub ---
IONOS_API_TOKEN="<ionos-jwt-token>"
IONOS_URL="https://openai.inference.de-txl.ionos.com/v1/chat/completions"
MODEL_ID="meta-llama/Llama-3.3-70B-Instruct"

# --- Websuche (Faktencheck) ---
TAVILY_API_KEY="<tavily-key>"

# --- Bild-KI-Erkennung ---
SIGHTENGINE_USER="<sightengine-user-id>"
SIGHTENGINE_API="<sightengine-secret>"

# --- Infrastruktur ---
DOMAIN=demokratie-im-feed.de
BASE_URL=https://demokratie-im-feed.de
TARGET=frontend:80
CERTBOT_UPDATES_RECEIVER="ops@example.de"
```

---

## 4. Nginx Reverse Proxy — Funktionsweise

Die Proxy-Konfiguration ist **zweistufig** und wird teilweise **generiert**.

### 4.1 Edge-Proxy (`nginx-service`)

Aktive Datei: `nginx/active/default.conf` — **generiert** aus dem Template [nginx/default.conf.template](../nginx/default.conf.template) durch das Makefile-Target `nginx-conf` (via `envsubst`, ersetzt `${DOMAIN}` und `${TARGET}`).

Aufgaben dieser Ebene:

- **TLS-Terminierung** mit Zertifikaten unter `/etc/letsencrypt/live/${DOMAIN}/` (`fullchain.pem` / `privkey.pem`); Erneuerung automatisch durch das `jonasal/nginx-certbot`-Image.
- **HTTP → HTTPS Redirect** (Port 80 → `301` auf `https`).
- **Security-Header:** `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`; `server_tokens off`.
- **Basic-Auth (Login-Schutz):** `auth_basic` im `location /` sperrt die **gesamte** Seite (Frontend **und** `/api/*`) hinter einen Login → Details und Einrichtung in [Abschnitt 6](#6-zugang-absichern-basic-auth).
- **Rate Limiting:** Zone `mylimit` mit `1000r/s`, Burst 1000.
- **Upload-Limit:** `client_max_body_size 6M`.
- **WebSocket-Upgrade-Map** aus [nginx/http-connection-upgrade-map.conf](../nginx/http-connection-upgrade-map.conf).
- **Proxy-Timeouts:** je 300 s (read/connect/send) — wichtig, da LLM-Antworten lange dauern können.
- Leitet **alles** weiter: `proxy_pass http://${TARGET}` (= `frontend:80`).

### 4.2 Interner Router (`frontend`)

Datei: [nginx/frontend.conf](../nginx/frontend.conf)

- `location /` → liefert das statische SPA (`try_files … /index.html`).
- `location /api/` → `proxy_pass http://backend:8000/` — der **abschließende Slash** entfernt das `/api/`-Präfix, sodass das Backend die Route ohne Präfix sieht (Browser `/api/analyze` → Backend `/analyze`).
- `client_max_body_size 10M`, Timeouts 300 s.

> Grund für den doppelten Nginx: TLS/Certbot und Sicherheits-Policies sind im Edge-Container gebündelt, während SPA-Serving + API-Routing beim Frontend-Container liegen. Das FastAPI-`root_path="/api"` ([main.py](../backend/main.py)) sorgt zusätzlich dafür, dass die Swagger-UI hinter dem Proxy unter `/api/docs` korrekt funktioniert.

---

## 5. Schritt-für-Schritt: Deployment auf der IONOS-VM

**Voraussetzungen auf der VM:** Docker + Docker Compose Plugin, Git, `make`. Der DNS **A-Record** der `DOMAIN` muss auf die öffentliche IP der VM zeigen (Pflicht, bevor Certbot Zertifikate ausstellen kann).

```bash
# 1. Repository klonen
git clone <repo-url> dif && cd dif

# 2. .env anlegen (siehe Abschnitt 3.3) und mit echten Secrets befüllen
$EDITOR .env

# 3. Nginx-Edge-Config aus Template generieren (Pflicht!)
#    Erzeugt ./nginx/active/default.conf mit DOMAIN/TARGET aus der .env
make nginx-conf

# 4. Docker-Netzwerk anlegen (idempotent)
make create-docker-network

# 5. Container bauen und starten
docker compose up -d --build

# 6. Status & Logs prüfen
docker compose ps
docker compose logs -f nginx-service   # TLS/Certbot-Ausstellung beobachten
docker compose logs -f backend         # Applikations-/LLM-Logs
```

### Verifikation nach dem Start

- `https://<DOMAIN>/` → SPA lädt.
- `https://<DOMAIN>/api/docs` → FastAPI Swagger-UI erreichbar.
- Smoke-Test der IONOS-Anbindung (im Backend-Container): `docker compose exec backend python api/test_api.py` → erwartete Antwort „Verbunden".

### Wichtige Reihenfolge-Fallstricke

1. **`make nginx-conf` ist zwingend vor `docker compose up`.** Ohne diesen Schritt ist `./nginx/active` leer und der Edge-Proxy startet ohne Server-Block.
2. Zeigt der DNS-Record noch nicht auf die VM, scheitert die Zertifikatsausstellung — Certbot versucht es periodisch erneut.
3. Der Zugang ist per **Basic-Auth** geschützt (Login-Gate vor der gesamten Seite). Wichtig bei einem Neuaufsetzen: die `.htpasswd`-**Datei** anlegen, **bevor** die Container gestartet werden. Einrichtung siehe [Abschnitt 6](#6-zugang-absichern-basic-auth).

### Updates ausrollen

```bash
git pull && make nginx-conf && docker compose up -d --build
```

Da das Backend den Code per Bind-Mount + `--reload` lädt, genügt für reine Backend-Code-Änderungen oft schon ein Neuladen ohne Rebuild.

> **Randnotiz:** Der Kommentar zum Makefile-Target `setup-project-prod` ([Makefile](../Makefile)) nennt `npm run docker:build` / `npm run docker:start` — es existiert jedoch **keine** `package.json`. Diese Angabe ist veraltet; maßgeblich sind die oben genannten `docker compose`-Befehle.

---

## 6. Zugang absichern (Basic-Auth)

Die gesamte Seite (Frontend **und** alle `/api/*`-Routen) ist hinter einem Login gesperrt, damit die kostenpflichtigen KI-Modelle nicht öffentlich nutzbar sind. Umgesetzt am Edge-Proxy (`nginx-service`), nicht im Backend.

**Wie es verdrahtet ist:**

- Die Direktiven `auth_basic` + `auth_basic_user_file /etc/nginx/.htpasswd` stehen im `location /` des HTTPS-Servers im Template [nginx/default.conf.template](../nginx/default.conf.template) (landen per `make nginx-conf` in der aktiven Config).
- Die Zugangsdaten liegen in der Datei `.htpasswd` im Projekt-Root, per Compose read-only als `/etc/nginx/.htpasswd` in den Proxy gemountet.

**Einrichtung (auf der VM):**

```bash
cd /home/zdi-ki-lab/dif

# 1. .htpasswd-DATEI mit Login "dif" anlegen (VOR dem ersten Container-Start).
#    openssl fragt das Passwort interaktiv ab -> kein Klartext in History/Chat.
printf 'dif:%s\n' "$(openssl passwd -apr1)" | sudo tee .htpasswd >/dev/null

# 2. Aktive Config generieren und Proxy neu laden
sudo make nginx-conf
sudo docker compose up -d nginx-service
```

**Prüfen:**

```bash
curl -I https://<DOMAIN>/                       # -> 401 Unauthorized
curl -I -u dif:DEINPASSWORT https://<DOMAIN>/   # -> 200 OK
```

**Betrieb:**

- **Passwort/Datei:** Im Klartext wird nichts gespeichert; in `.htpasswd` steht nur ein Hash (`dif:$apr1$…`). Passwort vergessen → Schritt 1 erneut ausführen (überschreibt den Hash).
- **Weitere Nutzer:** anhängen mit `printf 'name:%s\n' "$(openssl passwd -apr1)" | sudo tee -a .htpasswd`, danach `sudo docker compose exec nginx-service nginx -s reload`.
- **Deaktivieren:** die zwei `auth_basic`-Zeilen im Template entfernen → `sudo make nginx-conf` → `sudo docker compose restart nginx-service`.
- **Troubleshooting `not a directory` beim Start:** tritt nur auf, wenn der Container erstellt wurde, als `.htpasswd` noch **kein** File war (siehe Reihenfolge oben). Einmalig `sudo docker compose up -d --force-recreate nginx-service` behebt es.
