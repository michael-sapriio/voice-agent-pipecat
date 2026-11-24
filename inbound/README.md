# Pipecat + Vobiz — Inbound

This module is an independent FastAPI application that connects Vobiz Voice API media streams to a Pipecat pipeline:

**Vobiz → VobizFrameSerializer → Sarvam realtime STT → OpenAI LLM → Cartesia TTS → Vobiz**

## Prerequisites

- Docker Desktop and Docker Compose v2
- Python 3.12+ for local development
- Vobiz account and Auth ID / Auth Token
- Public HTTPS/WSS tunnel reachable by Vobiz (ngrok for development)
- Sarvam realtime STT access and API key
- OpenAI API key
- Cartesia API key and voice ID

## 1. Configure environment

From this module directory:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set the Vobiz credentials, public tunnel base URL, Sarvam/OpenAI/Cartesia keys and Cartesia voice ID. `PUBLIC_URL` must be the HTTPS base URL only; do not append `/answer` or `/ws`.

The project uses Pipecat `1.8.1` and `pipecat-vobiz` `0.0.3`, matching the supplied repository. Keep these pins while reproducing the existing tested integration.

## 2. Build and start

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f app
```

## 3. Expose the app

Inbound publishes host port 8000:

```powershell
ngrok http 8000
```

Configure the Vobiz Voice Application Answer URL as `https://YOUR-TUNNEL/answer` (POST), then attach your Vobiz DID to that application.

Check the local health endpoint:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## 4. Call flow

1. Caller dials your Vobiz DID.
2. Vobiz requests `PUBLIC_URL/answer`.
3. The application returns XML that opens a bidirectional WebSocket to `PUBLIC_URL/ws`.
4. Pipecat processes the stream and returns synthesized audio.

## 5. Test

Call the Vobiz DID from a test phone and monitor:

```powershell
docker compose logs -f app
```

## 6. Useful commands

```powershell
docker compose logs --tail 200 -f app
docker compose restart
docker compose down
```

## Endpoints

- `GET /health` — health check.
- `GET|POST /answer` — Vobiz answer webhook.
- `WS /ws` — bidirectional media stream.


## Important audio details

- `audioTrack="inbound"` is used for the bidirectional Vobiz stream.
- `add_wav_header=False` is intentional for raw telephony audio.
- The Vobiz `start` event's encoding and sample rate are passed to the serializer.
- `PIPELINE_SAMPLE_RATE` controls the Pipecat processing sample rate. Keep it consistent with your tested audio configuration.

## Security and production

Keep `.env` private. Do not expose the outbound `/start` endpoint publicly without setting `CALL_API_TOKEN` or placing it behind an authenticated gateway. Before production, add provider callback authentication where supported, rate limiting, concurrency/CPS controls, call-state persistence, monitoring, consent/DND controls and load testing.
