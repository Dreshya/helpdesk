import os
import markdown2
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import chromadb

# ---- 1. Extract Text ----
def extract_text_from_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html = markdown2.markdown(f.read())
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def extract_text_from_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    return soup.get_text()

def extract_text_auto(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".md":
        return extract_text_from_markdown(file_path)
    elif ext in [".html", ".htm"]:
        return extract_text_from_html(file_path)
    else:
        raise ValueError("Unsupported file type: must be .md or .html")

# ---- 2. Split into Chunks ----
def split_text(text, chunk_size=500):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# ---- 3. Process and Store ----
def process_and_store(file_path, collection_name="company_docs", db_path="./db"):
    print(f"📥 Loading file: {file_path}")
    raw_text = extract_text_auto(file_path)
    chunks = split_text(raw_text)
    print(f"✂️ Split into {len(chunks)} chunks")

    # Load embedding model
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = embedder.encode(chunks).tolist()

    # Initialize Chroma
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(collection_name)

    # Store in Chroma
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"source": os.path.basename(file_path)} for _ in chunks],
        ids=[f"{os.path.basename(file_path)}_chunk{i}" for i in range(len(chunks))]
    )

    print(f"✅ Stored {len(chunks)} chunks in collection '{collection_name}'")

# ---- 4. Run ----
if __name__ == "__main__":
    your_file = "how-to-update-profile.md"  # ← Change this to your actual .md or .html file
    process_and_store(your_file)
