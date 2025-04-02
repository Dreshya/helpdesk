import chromadb

# Create a ChromaDB instance (persists data in the "db" folder)
chroma_client = chromadb.PersistentClient(path="db")

# Create a collection (like a database table)
faq_collection = chroma_client.get_or_create_collection(name="faqs")

faq_collection.add(
    ids=["faq1", "faq2"],
    metadatas=[{"category": "password"}, {"category": "refund"}],
    documents=[
        "How do I reset my password?",
        "What is the refund policy?"
    ]
)

query = "How can I change my password?"
results = faq_collection.query(
    query_texts=[query],
    n_results=2
)
print("Retrieved documents:", results)

