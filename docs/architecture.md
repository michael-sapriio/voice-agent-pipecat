# Architecture

## Overview

This repository contains two independent FastAPI applications that share the same Pipecat audio-processing design.

- Inbound: Vobiz calls a DID associated with a Vobiz Voice Application. Vobiz requests `/answer`, receives XML, and opens `/ws`.
- Outbound: an operator calls `/start`. The app calls the Vobiz Call API. When the callee answers, Vobiz requests `/answer` and opens `/ws`.

## Media pipeline

```text
Vobiz bidirectional WebSocket
       │
       ▼
FastAPIWebsocketTransport
       │
       ▼
VobizFrameSerializer
       │
       ▼
SarvamRealtimeSTTService
       │
       ▼
LLMContextAggregatorPair (user)
       │
       ▼
OpenAILLMService
       │
       ▼
CartesiaTTSService
       │
       ▼
FastAPIWebsocketTransport output
       │
       ▼
Vobiz → PSTN
```

The Pipecat pipeline configures audio input and output at `PIPELINE_SAMPLE_RATE`. The Vobiz stream's negotiated encoding and sample rate are read from its `start` event and passed to `VobizFrameSerializer`. `add_wav_header=False` is required for raw telephony media.

## Directory responsibilities

- `server.py`: FastAPI routes, health endpoint, answer webhook, WebSocket endpoint and (outbound only) Vobiz Call API endpoint.
- `app/answer.py`: generates Vobiz-compatible XML with the public WebSocket URL.
- `app/bot.py`: parses the Vobiz start event, configures the serializer, creates STT/LLM/TTS services and runs the Pipecat pipeline.
- `Dockerfile`: installs the pinned Pipecat and application dependencies.
- `docker-compose.yml`: runs the FastAPI application.
- `.env.example`: documents runtime configuration without real secrets.

## Port model

Both containers listen on port 8000 internally. Inbound publishes host port 8000; outbound publishes host port 8001. This allows both services to run on one development machine without a port collision.
