import os
from lxml import etree
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# === 1. XML Text Extraction ===
def extract_text_from_xml(file_path):
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    lines = []

    def recurse(element, depth=0):
        indent = "  " * depth
        tag_line = f"{indent}<{element.tag}>"
        lines.append(tag_line)

        if element.text and element.text.strip():
            lines.append(f"{indent}  {element.text.strip()}")

        for child in element:
            recurse(child, depth + 1)

        end_tag = f"{indent}</{element.tag}>"
        lines.append(end_tag)

    recurse(root)
    return "\n".join(lines)



# === 2. Chunking ===
def chunk_text(text, chunk_size=30, chunk_overlap=10):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    start = 0

    while start < len(lines):
        end = start + chunk_size
        chunk = "\n".join(lines[start:end])
        chunks.append(chunk)

        if end >= len(lines):  # ensure final lines aren't skipped
            break

        start += chunk_size - chunk_overlap

    return chunks




# === 3. Embedding ===
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_chunks(chunks):
    return embedding_model.encode(chunks, show_progress_bar=True)

# === 4. Store in ChromaDB ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")

def store_in_chromadb(chunks, embeddings):
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"xml_chunk_{i}"]
        )

# === 5. Pipeline ===
def process_and_store_xml(xml_path):
    print(f"Processing: {xml_path}")
    raw_text = extract_text_from_xml(xml_path)
    chunks = chunk_text(raw_text)
    embeddings = embed_chunks(chunks)
    store_in_chromadb(chunks, embeddings)
    print(f"Stored {len(chunks)} chunks in ChromaDB.")

# === Run the pipeline ===
if __name__ == "__main__":
    xml_file_path = "project_doc.xml"  # Replace with your XML path
    process_and_store_xml(xml_file_path)
