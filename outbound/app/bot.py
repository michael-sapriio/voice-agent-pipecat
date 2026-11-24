"""Pipecat audio pipeline for Vobiz bidirectional WebSocket media."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.vobiz import VobizFrameSerializer, parse_vobiz_start
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamRealtimeSTTService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

load_dotenv(override=False)

RATE = int(os.getenv("PIPELINE_SAMPLE_RATE", "8000"))


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.lower() in {"replace_me", "change_me"} or value.startswith("YOUR_"):
        raise RuntimeError(f"Set {name} in the module .env file")
    return value


async def run_pipecat_call(websocket, greeting: str | None = None) -> None:
    """Run one Pipecat pipeline for one Vobiz media WebSocket."""
    parsed = await parse_vobiz_start(websocket)
    call_id = parsed.get("call_id")
    stream_id = parsed.get("stream_id")
    encoding = parsed.get("encoding") or os.getenv(
        "VOBIZ_ENCODING", "audio/x-mulaw"
    )
    wire_rate = int(
        parsed.get("sample_rate") or os.getenv("VOBIZ_SAMPLE_RATE", "8000")
    )

    if not call_id or not stream_id:
        raise RuntimeError(
            "Vobiz start event did not include call_id and stream_id; "
            f"received keys: {sorted(parsed.keys())}"
        )

    logger.info(
        "Vobiz call={} stream={} encoding={} rate={}",
        call_id,
        stream_id,
        encoding,
        wire_rate,
    )

    serializer = VobizFrameSerializer(
        stream_id=stream_id,
        call_id=call_id,
        auth_id=required("VOBIZ_AUTH_ID"),
        auth_token=required("VOBIZ_AUTH_TOKEN"),
        params=VobizFrameSerializer.InputParams(
            encoding=encoding,
            vobiz_sample_rate=wire_rate,
            l16_byte_order=os.getenv("VOBIZ_L16_ENDIAN", "be"),
            auto_hang_up=True,
        ),
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    stt = SarvamRealtimeSTTService(
        api_key=required("SARVAM_API_KEY"),
        endpointing="vad",
        sample_rate=RATE,
        settings=SarvamRealtimeSTTService.Settings(
            model=os.getenv("SARVAM_STT_MODEL", "saaras:v3-realtime"),
            language_code=os.getenv("SARVAM_LANGUAGE", "auto"),
            stream_type=os.getenv("SARVAM_STREAM_TYPE", "fast"),
            mode="transcribe",
        ),
        should_interrupt=True,
    )

    llm = OpenAILLMService(
        api_key=required("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        ),
    )

    tts = CartesiaTTSService(
        api_key=required("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            model=os.getenv("CARTESIA_MODEL", "sonic-3.6"),
            voice=required("CARTESIA_VOICE_ID"),
        ),
        sample_rate=RATE,
    )

    opening = greeting or os.getenv(
        "DEFAULT_GREETING", "Hello! How can I help you today?"
    )
    context = LLMContext(
        [
            {
                "role": "system",
                "content": os.getenv(
                    "SYSTEM_PROMPT",
                    "You are a concise, friendly voice assistant. "
                    "Keep spoken replies brief.",
                ),
            },
            {
                "role": "user",
                "content": f"Start the call by saying: {opening}",
            },
        ]
    )
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer()
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=RATE,
            audio_out_sample_rate=RATE,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        logger.info("Vobiz media connected; generating greeting")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Vobiz media disconnected")
        await task.cancel()

    await PipelineRunner().run(task)
