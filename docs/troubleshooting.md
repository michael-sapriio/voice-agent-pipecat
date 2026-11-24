# Troubleshooting

## Docker cannot find `.env`

Run `Copy-Item .env.example .env` from the relevant module directory. Compose resolves `env_file` relative to the Compose file.

## Port is already allocated

Inbound uses host port 8000. Outbound uses host port 8001. Confirm the correct module's Compose file and run `docker compose ps`.

## Vobiz cannot reach the application

- Confirm the tunnel is running and its HTTPS URL is reachable publicly.
- Confirm `PUBLIC_URL` contains the tunnel base URL only, without `/answer` or `/ws`.
- Recreate the container after changing `.env`.
- Confirm the Vobiz Answer URL is `PUBLIC_URL/answer`.
- Check tunnel request logs and `docker compose logs -f app`.

## WebSocket does not connect

- Confirm Vobiz is opening `wss://.../ws`.
- Confirm the public tunnel supports WebSocket upgrades.
- Confirm the WebSocket path is `/ws`.
- Inspect the Vobiz stream start event and application logs.

## Call connects but there is no audio

- Check the Vobiz start event's negotiated `encoding` and `sample_rate`.
- Keep `add_wav_header=False` for raw telephony audio.
- Confirm `VOBIZ_ENCODING`, `VOBIZ_SAMPLE_RATE` and `PIPELINE_SAMPLE_RATE`.
- Inspect serializer and Pipecat logs.

## Sarvam returns an authentication or model error

Check `SARVAM_API_KEY`, realtime STT entitlement, `SARVAM_STT_MODEL`, language and stream settings. The supplied project pins Pipecat and `pipecat-vobiz`; do not change model or plugin versions without testing compatibility.

## OpenAI or Cartesia errors

Check API key, billing/credits, model name and Cartesia voice ID. Confirm that the selected voice is available to the Cartesia account.

## Outbound `/start` returns 401

If `CALL_API_TOKEN` is set, include the matching `X-Call-Token` header.

## Outbound `/start` returns 502

Check Vobiz Auth ID and Auth Token, account permissions, caller ID authorization, balance, destination permissions and Vobiz API response in the container logs.

## Useful commands

```powershell
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --tail 200 -f app
docker compose restart
docker compose down
```
