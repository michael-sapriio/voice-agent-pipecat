"""FastAPI application for outbound Vobiz calls."""
import logging
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator

from app.answer import answer_response
from app.bot import run_pipecat_call

load_dotenv(Path(__file__).resolve().parent / ".env")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Pipecat Vobiz Outbound")
CALL_API = "https://api.vobiz.ai/api/v1/Account/{auth_id}/Call/"


class StartCall(BaseModel):
    phone_number: str = Field(pattern=r"^\+[1-9]\d{6,14}$")
    from_number: str | None = None
    greeting: str | None = Field(default=None, max_length=500)

    @field_validator("from_number")
    @classmethod
    def validate_from_number(cls, value):
        if value is not None and not __import__("re").fullmatch(
            r"\+[1-9]\d{6,14}", value.strip()
        ):
            raise ValueError("from_number must be an E.164 phone number")
        return value.strip() if value else value


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pipecat-vobiz-outbound"}


@app.post("/start")
async def start(
    payload: StartCall,
    x_call_token: str | None = Header(default=None),
):
    token = os.getenv("CALL_API_TOKEN", "").strip()
    if token and x_call_token != token:
        raise HTTPException(status_code=401, detail="Invalid X-Call-Token")

    auth_id = os.getenv("VOBIZ_AUTH_ID", "").strip()
    auth_token = os.getenv("VOBIZ_AUTH_TOKEN", "").strip()
    public_url = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    caller = (
        payload.from_number or os.getenv("VOBIZ_PHONE_NUMBER", "")
    ).strip()

    if not auth_id or not auth_token or not public_url:
        raise HTTPException(
            status_code=500,
            detail="Configure VOBIZ_AUTH_ID, VOBIZ_AUTH_TOKEN and PUBLIC_URL",
        )
    if not caller.startswith("+"):
        raise HTTPException(
            status_code=400,
            detail="Provide an authorized E.164 caller ID",
        )

    answer_url = public_url + "/answer"
    if payload.greeting:
        answer_url += "?greeting=" + quote(payload.greeting, safe="")

    headers = {
        "X-Auth-ID": auth_id,
        "X-Auth-Token": auth_token,
        "Content-Type": "application/json",
    }
    body = {
        "from": caller,
        "to": payload.phone_number,
        "answer_url": answer_url,
        "answer_method": "POST",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                CALL_API.format(auth_id=auth_id),
                headers=headers,
                json=body,
            )
    except httpx.HTTPError as exc:
        logging.exception("Unable to reach Vobiz Call API")
        raise HTTPException(
            status_code=502,
            detail="Unable to reach Vobiz Call API",
        ) from exc

    if response.is_error:
        logging.error(
            "Vobiz API error %s: %s",
            response.status_code,
            response.text[:800],
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"Vobiz Call API returned {response.status_code}: "
                f"{response.text[:400]}"
            ),
        )

    try:
        result = response.json()
    except ValueError:
        result = {"raw_response": response.text[:800]}

    return {
        "status": "call_requested",
        "phone_number": payload.phone_number,
        "from_number": caller,
        "vobiz_response": result,
    }


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
        logging.info("Vobiz outbound websocket disconnected")
    except Exception:
        logging.exception("Outbound Pipecat call failed")
        try:
            await websocket.close(code=1011, reason="Agent pipeline error")
        except Exception:
            pass


@app.get("/")
async def root():
    return {
        "service": "Pipecat Vobiz outbound",
        "health": "/health",
        "start": "POST /start",
        "answer": "/answer",
        "websocket": "/ws",
    }
