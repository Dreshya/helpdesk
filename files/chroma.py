import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("helpdesk_faq")

# Load embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Documents
docs = [
    "How can I reset my password?",
    "Where can I view my order history?",
    "How to contact support?"
]
embeddings = embedder.encode(docs).tolist()

# Add documents
collection.add(
    documents=docs,
    embeddings=embeddings,
    metadatas=[{"source": "faq"} for _ in docs],
    ids=[f"doc_{i}" for i in range(len(docs))]
)

# Query
query = "forgot password"
query_embedding = embedder.encode([query]).tolist()
results = collection.query(query_embeddings=query_embedding, n_results=1)

print(results)
