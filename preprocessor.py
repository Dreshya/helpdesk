# xml_preprocessor.py
import os
from lxml import etree
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# === ChromaDB Setup ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# === Text Extraction ===
def extract_text_from_xml(file_path):
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    lines = []

    def recurse(element, path=""):
        current_path = f"{path}/{element.tag}" if path else element.tag
        if element.text and element.text.strip():
            lines.append(f"{current_path.replace('/', ' > ')}: {element.text.strip()}")
        for child in element:
            recurse(child, current_path)

    recurse(root)
    return "\n".join(lines)

# === Chunking ===
def chunk_text_linewise(text, chunk_size=30, chunk_overlap=10):
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    chunks = []
    i = 0
    while i < len(lines):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - chunk_overlap
    if lines and "\n".join(lines[-chunk_size:]) not in chunks[-1]:
        chunks.append("\n".join(lines[-chunk_size:]))
    return chunks

# === Embedding ===
def embed_chunks(chunks):
    return embedding_model.encode(chunks, show_progress_bar=True)

# === Storing in ChromaDB ===
def store_in_chromadb(chunks, embeddings, xml_filename):
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "source_file": os.path.basename(xml_filename),
            "chunk_index": i
        }
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{os.path.basename(xml_filename)}_chunk_{i}"],
            metadatas=[metadata]
        )

# === Main Pipeline ===
def process_and_store_xml(xml_path):
    raw_text = extract_text_from_xml(xml_path)
    chunks = chunk_text_linewise(raw_text)
    embeddings = embed_chunks(chunks)
    store_in_chromadb(chunks, embeddings, xml_path)
    return chunks
