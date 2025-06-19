import os
import logging
from lxml import etree
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import io

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === ChromaDB Setup ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# === Text Extraction ===
def extract_text_from_xml(xml_input):
    parser = etree.XMLParser(recover=True)
    try:
        if isinstance(xml_input, (str, os.PathLike)):
            # Handle file path
            tree = etree.parse(xml_input, parser)
        elif isinstance(xml_input, bytes):
            # Handle bytes input
            tree = etree.parse(io.BytesIO(xml_input), parser)
        else:
            raise ValueError(f"Expected str, os.PathLike, or bytes, got {type(xml_input)}")
    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error: {e}")
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
def store_in_chromadb(chunks, embeddings, source_identifier, doc_id):
    doc_id = doc_id or source_identifier
    existing_ids = collection.get()['ids']
    if any(id.startswith(f"{doc_id}_chunk_") for id in existing_ids):
        logger.warning(f"Document {doc_id} already processed. Skipping.")
        return
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "source_file": source_identifier,
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
def process_and_store_xml(xml_input, doc_id=None):
    raw_text = extract_text_from_xml(xml_input)
    if not raw_text:
        return []
    chunks = chunk_text(raw_text)
    embeddings = embed_chunks(chunks)
    # Use doc_id as source_identifier if no file path is provided
    source_identifier = os.path.basename(xml_input) if isinstance(xml_input, str) else doc_id or "uploaded_xml"
    store_in_chromadb(chunks, embeddings, source_identifier, doc_id)
    logger.info(f"Stored {len(chunks)} chunks for doc_id: {doc_id}")
    return chunks