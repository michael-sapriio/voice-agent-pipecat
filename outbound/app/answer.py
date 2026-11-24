"""Generate the Vobiz Voice API answer XML for a bidirectional media stream."""
from __future__ import annotations

import html
import os
from urllib.parse import quote, urlsplit

from fastapi import Request
from fastapi.responses import Response


def build_answer_xml(public_url: str, greeting: str | None = None) -> str:
    """Build Vobiz Stream XML from a public HTTPS base URL."""
    base = public_url.strip().rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("PUBLIC_URL must be an absolute http(s) URL")

    # Vobiz reaches the public HTTPS tunnel, then upgrades to WSS.
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/ws"
    if greeting:
        ws_url += "?greeting=" + quote(greeting, safe="")

    content_type = (
        f"{os.getenv('VOBIZ_ENCODING', 'audio/x-mulaw')};"
        f"rate={int(os.getenv('VOBIZ_SAMPLE_RATE', '8000'))}"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        '  <Stream bidirectional="true" audioTrack="inbound" '
        'keepCallAlive="true" '
        f'contentType="{html.escape(content_type, quote=True)}">\n'
        f"    {html.escape(ws_url)}\n"
        "  </Stream>\n"
        "</Response>"
    )


async def answer_response(request: Request) -> Response:
    public_url = os.getenv("PUBLIC_URL", "").strip()
    if not public_url:
        return Response("PUBLIC_URL is not configured", status_code=500)

    try:
        xml = build_answer_xml(public_url, request.query_params.get("greeting"))
    except (ValueError, TypeError) as exc:
        return Response(str(exc), status_code=500)

    return Response(xml, media_type="application/xml")
