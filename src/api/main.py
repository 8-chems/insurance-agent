import asyncio
import json
import sys
import uuid

from fastapi import Depends, FastAPI, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from src.agent.agent import root_agent
from src.api.auth import verified_customer
from src.common.config import settings
from src.verify.cite import render
from src.verify.evidence import Evidence
from src.verify.policy import verify_answer

APP = "insurance"
app = FastAPI(title="Insurance Agent API")
try:
    from src.common.telemetry import setup
    setup(app)
except Exception:                       # tracing is optional locally
    pass

sessions = (DatabaseSessionService(db_url=settings.sessions_db_url)
            if settings.sessions_db_url else InMemorySessionService())
runner = Runner(agent=root_agent, app_name=APP, session_service=sessions)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None


@app.get("/api/v1/health")
def health():
    return {"ok": True}


@app.post("/api/v1/chat")
async def chat(body: ChatIn, cust: str = Depends(verified_customer)):
    if body.conversation_id:
        s = await sessions.get_session(app_name=APP, user_id=cust, session_id=body.conversation_id)
        if s is None:                    # also covers someone else's id
            raise HTTPException(404)
        sid = s.id
    else:
        sid = str(uuid.uuid4())
        await sessions.create_session(app_name=APP, user_id=cust, session_id=sid,
                                      state={"authenticated_customer_id": cust})
    draft = ""
    async for ev in runner.run_async(user_id=cust, session_id=sid,
            new_message=types.Content(role="user", parts=[types.Part(text=body.message)])):
        if ev.is_final_response() and ev.content and ev.content.parts:
            draft = ev.content.parts[0].text or ""
    s = await sessions.get_session(app_name=APP, user_id=cust, session_id=sid)
    ledger = {e["source_id"]: Evidence(**e) for e in s.state.get("evidence", [])}
    text, status, checked = await asyncio.to_thread(verify_answer, draft, ledger)
    answer, sources = render(text, ledger)
    print(json.dumps({"severity": "INFO", "event": "verification", "status": status,
                      "total": len(checked),
                      "supported": sum(c.label == "supported" for c in checked),
                      "unsupported": sum(c.label == "unsupported" for c in checked),
                      "contradicted": sum(c.label == "contradicted" for c in checked)}), file=sys.stdout)
    return {"conversation_id": sid, "answer": answer, "sources": sources, "status": status}
