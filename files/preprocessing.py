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

    def recurse(element, path=""):
        current_path = f"{path}/{element.tag}" if path else element.tag

        # If element has meaningful text
        if element.text and element.text.strip():
            lines.append(f"{current_path.replace('/', ' > ')}: {element.text.strip()}")

        # Recurse into children
        for child in element:
            recurse(child, current_path)

    recurse(root)
    return "\n".join(lines)




# === 2. Chunking ===
def chunk_text_linewise(text, chunk_size=30, chunk_overlap=10):
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]  # Keep all non-empty lines

    chunks = []
    i = 0

    while i < len(lines):
        chunk = "\n".join(lines[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - chunk_overlap

    # Ensure last few lines are not missed
    if lines and "\n".join(lines[-chunk_size:]) not in chunks[-1]:
        final_chunk = "\n".join(lines[-chunk_size:])
        chunks.append(final_chunk)

    return chunks




# === 3. Embedding ===
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_chunks(chunks):
    return embedding_model.encode(chunks, show_progress_bar=True)

# === 4. Store in ChromaDB ===
chroma_client = chromadb.PersistentClient(path="./chroma_storage")
collection = chroma_client.get_or_create_collection(name="xml_knowledge")

def store_in_chromadb(chunks, embeddings, xml_path):
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = {
            "source_file": os.path.basename(xml_path),
            "chunk_index": i,
        }
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"xml_chunk_{i}"],
            metadatas=[metadata]
        )


# === 5. Pipeline ===
def process_and_store_xml(xml_path):
    print(f"Processing: {xml_path}")
    raw_text = extract_text_from_xml(xml_path)

    all_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    print(f"Total extracted lines: {len(all_lines)}")

    chunks = chunk_text_linewise(raw_text)
    print(f"Total chunks created: {len(chunks)}")

    # Debug: ensure last few lines are covered
    print("Last 5 lines extracted:")
    print("\n".join(all_lines[-5:]))
    print("Last chunk preview:")
    print(chunks[-1])

    embeddings = embed_chunks(chunks)
    store_in_chromadb(chunks, embeddings, xml_path)
    print(f"Stored {len(chunks)} chunks in ChromaDB.")



# === Run the pipeline ===
if __name__ == "__main__":
    xml_file_path = "project_doc.xml"  # Replace with your XML path
    process_and_store_xml(xml_file_path)
