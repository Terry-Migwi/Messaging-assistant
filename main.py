import os
from dotenv import load_dotenv
load_dotenv() 

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from llm_client import anthropic_client, MODEL
from prompts_v2 import GENERAL_SYSTEM_PROMPT
from sms_service import send_sms
#from ingest_chroma import ingest
from ingest_pinecone import build_vectorstore, load_vectorstore
from query import chain_with_memory, session_manager
from intent_router import classify_intent
from booking.booking_agent import run_booking_agent
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — bot is ready")
    
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


@app.post("/sms-webhook")
async def sms_webhook(
    from_number: str = Form(..., alias="from"),
    to: str = Form(...),
    text: str = Form(...),
    id: str = Form(None),
    date: str = Form(None)
):
    logger.info(f"Message from: {from_number} | text: {text}")

    try:                                                 
        # ── Step 1: classify intent ───────────────────────────────────────────
        intent = classify_intent(text)
        logger.info(f"Intent: {intent}")

        # ── Step 2: route to the right handler ───────────────────────────────
        if intent == "booking":
            answer = _handle_booking(text, from_number)
        elif intent == "general":
            answer = _handle_general(text)
        else:
            answer = _handle_faq(text, from_number)

        logger.info(f"Answer: {answer}")

    except Exception as e:                              
        logger.error(f"Failed to process message from {from_number}: {e}")
        answer = "Sorry, we encountered an issue. Please call us on 0762 223 925."

    send_sms(to=from_number, message=answer)            
    return PlainTextResponse("OK", status_code=200)


def _handle_faq(text: str, from_number: str) -> str:
    """Route to existing RAG chain — unchanged from before."""
    return chain_with_memory.invoke(
        {"input": text},
        config={"configurable": {"session_id": from_number}}
    )


def _handle_booking(text: str, from_number: str) -> str:
    """
    Route to booking agent.
    Retrieves existing conversation history from SessionManager
    so the booking agent has full context across turns.
    """
    session_history = session_manager.get_session_history(from_number)
    history = session_history.messages

    response = run_booking_agent(
        message=text,
        history=history,
        phone=from_number
    )

    session_history.add_message(HumanMessage(content=text))
    session_history.add_message(AIMessage(content=response))

    return response


def _handle_general(text: str) -> str:
    response = anthropic_client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=GENERAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    return response.content[0].text.strip()

# If response was cut off (stop_reason is not end_turn), retry with simpler prompt
    if response.stop_reason != "end_turn":
        retry = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=GENERAL_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": text},
                {"role": "assistant", "content": result},
                {"role": "user", "content": "Please summarise that in 2 sentences maximum."}
            ]
        )
        return retry.content[0].text.strip()
    
    return result

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        intent = classify_intent(request.message)
        logger.info(f"Chat intent: {intent}")

        if intent == "booking":
            answer = "Booking is available via Whatsapp/SMS. To book an appointment, text us on our clinic number."
        elif intent == "general":
            answer = _handle_general(request.message)
        else:
            answer = _handle_faq(request.message, "demo-user")

        return {"response": answer, "intent": intent}

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#@app.get("/")
#def health_check():
 #   return {"status": "AI assistant is running"}

@app.get("/health")
def health_check():
    return {"status": "AI assistant is running"}