---
title: Messaging Assistant
emoji: 💬
colorFrom: green
colorTo: green
sdk: docker
pinned: false
---

# Messaging Assistant

A configurable RAG-powered messaging assistant framework that handles customer queries over WhatsApp and SMS. Demoed with a dental clinic knowledge base. Swap the knowledge base and five environment variables to deploy for any business.


## The Problem

Businesses accumulate large volumes of documentation, product manuals, policy documents, service catalogues, compliance guides, training materials. This knowledge exists but isn't accessible. Customer-facing staff spend hours manually searching through documents to answer queries. Customers wait. Errors happen when staff rely on memory instead of the source document.

A keyword search across hundreds of documents returns too many irrelevant results. A generic LLM hallucinates answers it wasn't trained on. What's needed is a system that retrieves accurately from the business's own large knowledge base and responds conversationally through the channels customers already use.

## Solution

A messaging assistant built on RAG that makes large document collections queryable over SMS and WhatsApp. Incoming messages are classified by intent, routed to the appropriate handler, and answered using context retrieved from a Pinecone vector store. The knowledge base can be any collection of documents — policies, catalogues, manuals, FAQs — embedded once and queried continuously. Session memory per phone number keeps conversations coherent across multiple messages.

## Features

- **Intent routing** — classifies every message as FAQ, general knowledge, or booking before responding
- **RAG-powered FAQ** — retrieves relevant chunks from the business knowledge base before answering
- **Booking agent** — LangGraph agent with Google Calendar integration for checking slots and confirming appointments
- **Session memory** — TTL-based conversation history keyed by phone number
- **Configurable per business** — business name, domain, phone, location, and hours all driven by environment variables
- **Africa's Talking integration** — receives and sends SMS and WhatsApp messages via webhook
- **Interactive demo UI** — chat interface for portfolio demonstration without requiring a phone

## Architecture

```
Incoming SMS/WhatsApp
    │
    ▼
Intent Classifier (Claude Haiku)
    │
    ├── FAQ → RAG Chain (Pinecone + Claude Haiku)
    │
    ├── General → LLM with domain guardrails
    │
    └── Booking → LangGraph Agent (Google Calendar)
    │
    ▼
Response sent via Africa's Talking
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| Orchestration | LangChain, LangGraph |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector DB | Pinecone Serverless |
| LLM | Claude Haiku (Anthropic) |
| Messaging | Africa's Talking (SMS + WhatsApp) |
| Booking | Google Calendar API |
| Monitoring | LangSmith |
| Deployment | Hugging Face Spaces (Docker) |

## Project Structure

```
messaging_assistant/
├── main.py               # FastAPI app, webhook and chat endpoints
├── intent_router.py      # Intent classification
├── query.py              # RAG chain with session memory
├── llm_client.py         # Anthropic client
├── sms_service.py        # Africa's Talking integration
├── session_manager.py    # TTL-based session memory
├── prompts_v2.py         # Configurable business prompts
├── ingest_pinecone.py    # Document embedding and ingestion
├── config.py             # Environment variable management
├── index.html            # Demo chat UI
├── booking/
│   ├── booking_agent.py  # LangGraph booking agent
│   ├── booking_tools.py  # Calendar tool definitions
│   └── calendar_service.py # Google Calendar integration
├── Dockerfile            # Container configuration
└── requirements.txt      # Dependencies
```

## Deploying for a New Business

1. Prepare your knowledge base document (plain text or PDF)
2. Run `ingest_pinecone.py` to embed and store it in Pinecone
3. Set these environment variables:

```bash
BUSINESS_NAME=Your Business Name
BUSINESS_PHONE= Your Business Number
BUSINESS_LOCATION=Your address
BUSINESS_HOURS=Mon-Fri 9am-5pm
BUSINESS_DOMAIN=your industry
```

4. Point your Africa's Talking webhook to `/sms-webhook`

## Running Locally

```bash
# Clone the repo
git clone https://github.com/Terry-Migwi/messaging-assistant
cd messaging-assistant

# Create .env with your keys
# ANTHROPIC_API_KEY=
# PINECONE_API_KEY=
# HUGGING_FACE_HUB_KEY=
# AT_USERNAME=sandbox
# AT_API_KEY=
# BUSINESS_NAME=
# BUSINESS_DOMAIN=

# Install dependencies
pip install -r requirements.txt

# Ingest your knowledge base
python ingest_pinecone.py

# Start the server
uvicorn main:app --reload
```

## Live Demo
[Try it on Hugging Face Spaces](https://huggingface.co/spaces/Tee-M/messaging-assistant)