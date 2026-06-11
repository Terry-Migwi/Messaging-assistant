from pathlib import Path

_here = Path(__file__).resolve().parent

from llm_client import chat_llm
from ingest_pinecone import load_vectorstore
from prompts_v2 import RAG_SYSTEM_PROMPT
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from session_manager import SessionManager

# Load vectorstore
vectorstore = load_vectorstore()
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# Set up Claude
llm = chat_llm

# system prompt with chat history
prompt = ChatPromptTemplate.from_messages([
    ("system", RAG_SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Helper to format retrieved chunks
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# One shared instance — lives for the lifetime of the app process
session_manager = SessionManager(ttl_seconds=1800)  # 30-minute timeout

def get_session_history(session_id: str):
    return session_manager.get_session_history(session_id)

base_chain = (
    {
        "context": lambda x: format_docs(retriever.invoke(x["input"])),
        "input": lambda x: x["input"],
        "history": lambda x: x.get("history", [])
    }
    | prompt
    | llm
    | StrOutputParser()
)

chain_with_memory = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)


def ask(question: str, session_id: str = "default") -> str:
    """Ask the RAG chain a question and return the response string."""
    return chain_with_memory.invoke(
        {"input": question},
        config={"configurable": {"session_id": session_id}}
    )

# build an interactive loop
if __name__ == "__main__":
    print("\n=== Denta Clinic Assistant ===")
    print("Type 'exit' to quit\n")

    session_id = "patient_session_1"

    while True:
        question = input("Patient: ").strip()

        if question.lower() == "exit":
            print("Goodbye!")
            break

        if not question:
            print("Please ask a question.\n")
            continue

        print(f"\nAssistant: {ask(question, session_id)}\n")
        print("-" * 50)
