# modularise llm client 
import os
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic

MODEL = "claude-haiku-4-5-20251001"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

chat_llm = ChatAnthropic(
    model=MODEL,
    anthropic_api_key=ANTHROPIC_API_KEY,
    temperature=0,
)