# Pipecat + Vobiz — Outbound

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

Outbound publishes host port 8001 on the host (the container listens on 8000):

```powershell
ngrok http 8001
```

Set this outbound tunnel HTTPS URL in `PUBLIC_URL`, then recreate the container:

```powershell
docker compose up -d --force-recreate
```

Check the local health endpoint:

```powershell
Invoke-RestMethod http://localhost:8001/health
```

## 4. Call flow

1. An operator sends `POST /start` with `phone_number` and optional `from_number` / `greeting`.
2. The application calls the Vobiz Call API.
3. After the callee answers, Vobiz requests `PUBLIC_URL/answer`.
4. The application returns XML that opens a bidirectional WebSocket to `PUBLIC_URL/ws`.
5. Pipecat processes the stream and returns synthesized audio.

## 5. Test

From PowerShell, initiate a test call:

```powershell
$PHONE = "+919876543210"

$body = @{
    phone_number = $PHONE
    greeting = "Hello! This is an AI assistant calling."
} | ConvertTo-Json

$headers = @{}
# If CALL_API_TOKEN is set in .env:
# $headers["X-Call-Token"] = "YOUR_CONFIGURED_TOKEN"

Invoke-RestMethod `
    -Uri "http://localhost:8001/start" `
    -Method POST `
    -ContentType "application/json" `
    -Headers $headers `
    -Body $body
```

The `phone_number` field is required and must be E.164. `from_number` is optional and defaults to `VOBIZ_PHONE_NUMBER`. The caller ID must be authorized on your Vobiz account. Set `CALL_API_TOKEN` and provide `X-Call-Token` before exposing `/start` publicly.

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
- `POST /start` — initiates a Vobiz outbound call.

## Important audio details

- `audioTrack="inbound"` is used for the bidirectional Vobiz stream.
- `add_wav_header=False` is intentional for raw telephony audio.
- The Vobiz `start` event's encoding and sample rate are passed to the serializer.
- `PIPELINE_SAMPLE_RATE` controls the Pipecat processing sample rate. Keep it consistent with your tested audio configuration.

## Security and production

Keep `.env` private. Do not expose the outbound `/start` endpoint publicly without setting `CALL_API_TOKEN` or placing it behind an authenticated gateway. Before production, add provider callback authentication where supported, rate limiting, concurrency/CPS controls, call-state persistence, monitoring, consent/DND controls and load testing.
