# Voice Agent — Pipecat + Vobiz

A real-time telephone voice-agent implementation using **Vobiz Voice API**, bidirectional WebSockets, **Pipecat**, **Sarvam realtime STT**, **OpenAI LLM**, and **Cartesia TTS**.

This repository contains two independently runnable applications:

- `inbound/` — handles calls placed by a caller to your Vobiz DID.
- `outbound/` — initiates calls through the Vobiz Call API and handles the answered call.

The applications use FastAPI for HTTP/webhook endpoints and WebSockets for bidirectional audio streaming.

## Repository structure

```text
voice-agent-pipecat/
├── .gitignore
├── LICENSE
├── README.md
├── docs/
│   ├── architecture.md
│   ├── inbound-call-flow.md
│   ├── outbound-call-flow.md
│   └── troubleshooting.md
├── inbound/
│   ├── .dockerignore
│   ├── .env.example
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── server.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── answer.py
│   │   └── bot.py
│   └── tests/
│       ├── test_answer.py
│       └── test_health.py
└── outbound/
    ├── .dockerignore
    ├── .env.example
    ├── README.md
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── server.py
    ├── app/
    │   ├── __init__.py
    │   ├── answer.py
    │   └── bot.py
    └── tests/
        ├── test_answer.py
        └── test_health.py
```

## Architecture

```text
Vobiz PSTN call
      │
      ▼
Vobiz Voice API / Call API
      │
      ├── HTTP answer webhook (/answer)
      │       └── XML instructs Vobiz to open a bidirectional stream
      │
      └── WebSocket media stream (/ws)
              │
              ▼
        FastAPI application
              │
              ▼
          Pipecat pipeline
              ├── VobizFrameSerializer
              ├── Sarvam realtime STT
              ├── OpenAI LLM
              └── Cartesia TTS
              │
              ▼
        Vobiz → PSTN caller
```

## Technology stack

| Component | Technology |
|---|---|
| Telephony | Vobiz Voice API and SIP/PSTN |
| HTTP API and webhook server | FastAPI + Uvicorn |
| Real-time audio pipeline | Pipecat |
| Vobiz media protocol | `pipecat-vobiz` serializer |
| Speech-to-text | Sarvam realtime STT |
| LLM | OpenAI |
| Text-to-speech | Cartesia |
| Containerization | Docker + Docker Compose |

The dependency versions retain the versions from the supplied project: Pipecat `1.8.1` and `pipecat-vobiz` `0.0.3`. Validate compatibility before upgrading these pins.

## Prerequisites

- Windows, macOS or Linux
- Docker Desktop / Docker Engine with Docker Compose v2
- A Vobiz account with an inbound DID and/or outbound calling enabled
- Vobiz Auth ID and Auth Token
- Sarvam API key with realtime STT entitlement
- OpenAI API key
- Cartesia API key and voice ID
- A public HTTPS/WSS endpoint reachable by Vobiz (ngrok is suitable for development)

## Quick start — inbound

Run PowerShell from the repository root:

```powershell
cd inbound
Copy-Item .env.example .env
notepad .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f app
```

In a second terminal, expose the inbound app:

```powershell
ngrok http 8000
```

Copy the HTTPS URL into `PUBLIC_URL` in `inbound/.env` (base URL only, without `/answer`), then recreate the app:

```powershell
docker compose up -d --force-recreate
Invoke-RestMethod http://localhost:8000/health
```

Configure the Vobiz Voice Application Answer URL as:

```text
https://YOUR-NGROK-DOMAIN/answer
```

Attach the inbound DID to that Voice Application and place a test call.

Detailed instructions: [inbound/README.md](inbound/README.md).

## Quick start — outbound

Open another PowerShell window:

```powershell
cd outbound
Copy-Item .env.example .env
notepad .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f app
```

Expose outbound port `8001`:

(Steps to set up ngrok listed at the bottom)

```powershell
ngrok http 8001
```

Set the outbound tunnel HTTPS URL in `outbound/.env` as `PUBLIC_URL`, then recreate the container:

```powershell
docker compose up -d --force-recreate
Invoke-RestMethod http://localhost:8001/health
```

Initiate a test call:

```powershell
$PHONE = "+919876543210"

$body = @{
    phone_number = $PHONE
    greeting = "Hello! This is an AI assistant calling. Is this a good time to speak?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8001/start" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

If `CALL_API_TOKEN` is configured, include the `X-Call-Token` header. See [outbound/README.md](outbound/README.md).

## Run both applications simultaneously

The applications have independent Compose projects and environment files.

| Application | Container | Host port | Container port |
|---|---|---:|---:|
| Inbound | `pipecat_vobiz_inbound_app` | 8000 | 8000 |
| Outbound | `pipecat_vobiz_outbound_app` | 8001 | 8000 |

Start each from its own directory. The outbound Compose mapping is deliberately `8001:8000` to avoid a host-port collision.

Use separate public tunnels and set the matching `PUBLIC_URL` in each module's `.env`.

## Environment and secrets

1. Copy the module's `.env.example` to `.env`.
2. Populate credentials locally.
3. Do not commit `.env`, API keys, Vobiz Auth Tokens, SIP credentials or call data.
4. Root `.gitignore` excludes environment files from Git.
5. Each module's `.dockerignore` excludes `.env` from its build context. Compose injects it at runtime using `env_file`.

## Tests

The tests validate XML generation and basic HTTP health endpoints. They do not make paid calls or validate provider credentials.

From either module directory:

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

## Production-readiness notes

This repository is a development / integration baseline, not a production-certified dialer. Before production, add or verify:

- Vobiz webhook signature or callback authentication, where supported.
- Authentication and network restrictions for `/start`.
- Rate limits, concurrency controls and per-campaign CPS limits.
- Consent, DND/DNC, calling-window and retry controls.
- Call lifecycle persistence, idempotency and reconciliation.
- Structured logs, metrics, tracing and alerting.
- Secrets management and credential rotation.
- Load, soak, failure-recovery and media-quality testing.
- Data retention, recording and privacy controls.

`/start` is protected by `CALL_API_TOKEN` when that variable is set. Configure a strong random value before exposing the outbound API publicly. Do not expose the endpoint without authentication.

======================
Steps to set-up ngrok
======================

1. Create an ngrok Account and Copy Your Authtoken:
Go to ngrok.com and sign up for an account. Once signed in, open the ngrok Dashboard and copy your Authtoken (found under Setup / Authtoken).

2. Install ngrok on Windows
<powershell>
	winget install ngrok.ngrok

3. Connect Your Authtoken to the ngrok Agent
<powershell>
	ngrok config add-authtoken 'YOUR_NGROK_AUTHTOKEN'

4. Start Your FastAPI Server and Expose Port 8000
<powershell>
	ngrok http 8000

Verification: ngrok displays a Forwarding URL (such as https://<random>.ngrok-free.app or your ngrok domain) pointing to http://localhost:8000,
and GET <your-ngrok-url>/health returns {"status":"ok","service":"pipecat-vobiz-outbound"}.

5. Set PUBLIC_URL for Vobiz Callbacks

Copy the https://... Forwarding URL from ngrok (without a trailing slash) into your .env as PUBLIC_URL,
and restart your FastAPI server so answer_url points to https://<your-ngrok-url>/answer

===================================================================


## License

See [LICENSE](LICENSE).
