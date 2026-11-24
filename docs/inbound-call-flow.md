# Inbound call flow

1. Caller dials the Vobiz DID.
2. Vobiz routes the DID to the configured Voice Application.
3. Vobiz sends an HTTP request to `PUBLIC_URL/answer`.
4. FastAPI returns XML containing a bidirectional stream URL.
5. Vobiz opens a WebSocket to `PUBLIC_URL/ws`.
6. `parse_vobiz_start()` reads the Vobiz start event and negotiated media details.
7. `VobizFrameSerializer` handles telephony media framing.
8. Pipecat runs Sarvam realtime STT → OpenAI → Cartesia TTS.
9. Generated audio is streamed back to Vobiz and the caller.

## Configure

From `inbound/`:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose build
docker compose up -d
ngrok http 8000
```

Set `PUBLIC_URL` to the tunnel HTTPS base URL (without `/answer`), recreate the container, and set the Vobiz Voice Application Answer URL to `https://YOUR-DOMAIN/answer` using POST.

The XML uses `audioTrack="inbound"` and the pipeline uses `add_wav_header=False`. These are intentional for the bidirectional raw-audio stream used by this integration.

## Test

```powershell
Invoke-RestMethod http://localhost:8000/health
docker compose logs -f app
```

Call the DID from a test phone and verify the greeting, caller transcription and agent response.
