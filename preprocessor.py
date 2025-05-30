import os
import logging
from lxml import etree
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ChromaDB Setup ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# === Text Extraction ===
def extract_text_from_xml(file_path):
    parser = etree.XMLParser(recover=True)
    try:
        tree = etree.parse(file_path, parser)
    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error in {file_path}: {e}")
        return ""
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
def chunk_text(raw_text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    return text_splitter.split_text(raw_text)

# === Embedding ===
def embed_chunks(chunks):
    return embedding_model.encode(chunks, show_progress_bar=True)

# === Storing in ChromaDB ===
def store_in_chromadb(chunks, embeddings, xml_filename, doc_id=None):
    doc_id = doc_id or os.path.basename(xml_filename)
    existing_ids = collection.get()['ids']
    if any(id.startswith(f"{doc_id}_chunk_") for id in existing_ids):
        logger.warning(f"Document {doc_id} already processed. Skipping.")
        return
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "source_file": os.path.basename(xml_filename),
            "doc_id": doc_id,
            "chunk_index": i
        }
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"{doc_id}_chunk_{i}"],
            metadatas=[metadata]
        )

# === Main Pipeline ===
def process_and_store_xml(xml_path, doc_id=None):
    raw_text = extract_text_from_xml(xml_path)
    if not raw_text:
        return []
    chunks = chunk_text(raw_text)
    embeddings = embed_chunks(chunks)
    store_in_chromadb(chunks, embeddings, xml_path, doc_id)
    return chunks