

import sys
import logging
from pathlib import Path
from typing import Annotated
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from llm_client import chat_llm
from prompts_v2 import BOOKING_SYSTEM_PROMPT
from booking.booking_tools import BOOKING_TOOLS

logger = logging.getLogger(__name__)

# ── state ─────────────────────────────────────────────────────────────────────
# State is what gets passed between nodes in the graph.
# add_messages is a reducer — it appends new messages rather than replacing.

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── system prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = BOOKING_SYSTEM_PROMPT


# ── agent factory ─────────────────────────────────────────────────────────────

def create_booking_agent():
    """
    Build and return a LangGraph booking agent.

    The graph has two nodes:
      - call_llm  : Claude reasons and optionally requests a tool call
      - run_tools : executes whichever tool Claude requested

    Returns:
        Compiled LangGraph agent (callable with {"messages": [...]})
    """
    llm = chat_llm
    # Bind tools to the LLM so Claude knows they exist
    llm_with_tools = llm.bind_tools(BOOKING_TOOLS)

    # ── node 1: call the LLM ──────────────────────────────────────────────────
    def call_llm(state: AgentState, config: RunnableConfig) -> dict:
        """Send the full message history to Claude and get a response."""
        # System prompt is already the first message — pass state as-is
        response = llm_with_tools.invoke(state["messages"], config)
        return {"messages": [response]}

    # ── node 2: run tools ─────────────────────────────────────────────────────
    # ToolNode automatically finds and executes tool calls in the last message
    tool_node = ToolNode(BOOKING_TOOLS)

    # ── routing logic ─────────────────────────────────────────────────────────
    def should_use_tool(state: AgentState) -> str:
        """
        Check if Claude's last message contains a tool call.
        If yes → go to run_tools node
        If no  → end the graph (Claude has a final answer)
        """
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "run_tools"
        return END

    # ── build graph ───────────────────────────────────────────────────────────
    graph = StateGraph(AgentState)

    graph.add_node("call_llm", call_llm)
    graph.add_node("run_tools", tool_node)

    graph.set_entry_point("call_llm")

    # After call_llm: check if we need a tool or we're done
    graph.add_conditional_edges("call_llm", should_use_tool)

    # After running a tool: always go back to call_llm to reason about result
    graph.add_edge("run_tools", "call_llm")

    return graph.compile()


# ── module-level agent instance ───────────────────────────────────────────────
# Created once and reused across all sessions
booking_agent = create_booking_agent()


def run_booking_agent(message: str, history: list[BaseMessage], 
                      phone: str) -> str:
    """
    Run the booking agent for a single patient message.

    Args:
        message: The patient's current message
        history: Full conversation history as a list of BaseMessages
        phone:   Patient's WhatsApp number from the webhook (e.g. +254712345678)

    Returns:
        The agent's response as a plain string
    """
    from langchain_core.messages import SystemMessage

    # Inject phone number so agent never needs to ask for it
    system_with_phone = SYSTEM_PROMPT + f"\n\nPatient's WhatsApp number: {phone}"

    state = {
        "messages": [SystemMessage(content=system_with_phone)] 
                    + history 
                    + [HumanMessage(content=message)]
    }

    result = booking_agent.invoke(state)
    last_message = result["messages"][-1]
    return last_message.content