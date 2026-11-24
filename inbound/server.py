"""FastAPI application for inbound Vobiz calls."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from app.answer import answer_response
from app.bot import run_pipecat_call

load_dotenv(Path(__file__).resolve().parent / ".env")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Pipecat Vobiz Inbound")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pipecat-vobiz-inbound"}


@app.api_route("/answer", methods=["GET", "POST"])
async def answer(request: Request):
    return await answer_response(request)


@app.websocket("/ws")
async def media_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        await run_pipecat_call(
            websocket,
            websocket.query_params.get("greeting"),
        )
    except WebSocketDisconnect:
        logging.info("Vobiz inbound websocket disconnected")
    except Exception:
        logging.exception("Inbound Pipecat call failed")
        try:
            await websocket.close(code=1011, reason="Agent pipeline error")
        except Exception:
            pass


@app.get("/")
async def root():
    return {
        "service": "Pipecat Vobiz inbound",
        "health": "/health",
        "answer": "/answer",
        "websocket": "/ws",
    }
