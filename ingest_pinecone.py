import os
import time


from config import HUGGING_FACE_API, PINECONE_API_KEY          
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX_NAME = "dental-clinic"       # name of your index in Pinecone
NAMESPACE  = "dental-clinic-docs"  # partition inside the index
DIMENSION  = 384                   # all-MiniLM-L6-v2 output size


def get_embeddings():
    # Unchanged from your original
    return HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=HUGGING_FACE_API
    )


def get_pinecone_client():
    """Initialise and return the Pinecone client."""
    return Pinecone(api_key=PINECONE_API_KEY)


def create_index_if_missing(pc: Pinecone):
    """
    Create the Pinecone index if it doesn't already exist.
    Pinecone needs to know the vector dimension and cloud region upfront.
    This only runs once — subsequent calls are skipped automatically.
    """
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",                        # cosine similarity — standard for sentence embeddings
            spec=ServerlessSpec(cloud="aws", region="us-east-1")  # free tier region
        )
        # Index takes a few seconds to initialise
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            print("Waiting for index to be ready...")
            time.sleep(2)
        print("Index ready.")
    else:
        print(f"Index '{INDEX_NAME}' already exists. Skipping creation.")


def build_vectorstore():
    """
    Run once to embed and store chunks in Pinecone.
    Equivalent to your original build_vectorstore() with Chroma.
    """
    # --- Load and split (unchanged) ---
    file_path = os.path.join(base_dir, "langchain", "dental_clinic.txt")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n--- ", "\nQ: ", "\n\n", "\n"],
        chunk_size=300,
        chunk_overlap=30,
        keep_separator=True
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    # --- Pinecone setup ---
    pc = get_pinecone_client()
    create_index_if_missing(pc)

    # --- Embed and store (replaces Chroma.from_documents) ---
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        index_name=INDEX_NAME,
        namespace=NAMESPACE
    )
    print(f"Stored {len(chunks)} chunks in Pinecone index '{INDEX_NAME}'.")
    return vectorstore


def load_vectorstore():
    """
    Load the existing Pinecone vectorstore without re-embedding.
    Equivalent to your original load_vectorstore() with Chroma.
    Called by query.py on every request.
    """
    pc = get_pinecone_client()
    return PineconeVectorStore(
        index=pc.Index(INDEX_NAME),
        embedding=get_embeddings(),
        namespace=NAMESPACE
    )


if __name__ == "__main__":
    build_vectorstore()