from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# === Embeddings ===
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# === Vector Store ===
vector_db = Chroma(
    persist_directory="chroma_storage",
    collection_name="xml_knowledge",
    embedding_function=embedding_model
)

def get_retriever(doc_id: str = None):
    if doc_id:
        return vector_db.as_retriever(
            search_kwargs={"k": 3, "filter": {"doc_id": doc_id}}
        )
    return vector_db.as_retriever(search_kwargs={"k": 3})

# === LLM Model ===
llm = OllamaLLM(model="mistral", temperature=0.2)