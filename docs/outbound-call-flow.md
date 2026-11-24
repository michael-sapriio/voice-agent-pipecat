# Outbound call flow

1. An operator sends `POST /start` with an E.164 `phone_number`, optional `from_number` and optional `greeting`.
2. FastAPI validates the request and checks `X-Call-Token` when `CALL_API_TOKEN` is configured.
3. The application calls the Vobiz Call API with `from`, `to`, `answer_url` and `answer_method`.
4. Vobiz dials the destination.
5. When answered, Vobiz requests `PUBLIC_URL/answer`.
6. FastAPI returns XML that opens a bidirectional WebSocket at `PUBLIC_URL/ws`.
7. Pipecat parses the Vobiz start event and runs Sarvam STT → OpenAI → Cartesia TTS.
8. Audio is returned to the caller over the Vobiz stream.

## Configure and run

From `outbound/`:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose build
docker compose up -d
ngrok http 8001
```

Set `PUBLIC_URL` to the outbound tunnel HTTPS base URL, recreate the app, and check `http://localhost:8001/health`.

## Trigger a test call

```powershell
$body = @{
    phone_number = "+919876543210"
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

Use an authorized test number and caller ID. A call can incur telephony and AI-provider charges.
