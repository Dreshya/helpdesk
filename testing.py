import chromadb

# === Connect to ChromaDB ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")

# === Retrieve all stored chunks with documents and embeddings ===
results = collection.get(ids=None, include=["documents", "embeddings", "metadatas"])

# === Display summary ===
print(f"🔍 Total Chunks Found: {len(results['ids'])}\n")

for i, (doc_id, doc_text, embedding) in enumerate(zip(results["ids"], results["documents"], results["embeddings"])):
    print(f"🧩 Chunk {i+1}")
    print(f"ID: {doc_id}")
    print(f"Text Preview: {doc_text[:300]}{'...' if len(doc_text) > 300 else ''}")
    print(f"Vector Size: {len(embedding)}\n{'-'*60}")

# === Optional: Show metadata if any ===
if results.get("metadatas"):
    print("\n🗂️ Metadata found:")
    for meta in results["metadatas"]:
        print(meta)
else:
    print("\nℹ️ No metadata stored with the chunks.")
