from bs4 import BeautifulSoup
import markdown
import glob
from database import vector_db

def extract_text_from_docs(doc_folder="docs/"):
    docs = []
    for file in glob.glob(f"{doc_folder}/*"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            if file.endswith(".md"):
                html = markdown.markdown(content)
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text()
            elif file.endswith(".html"):
                soup = BeautifulSoup(content, "html.parser")
                text = soup.get_text()
            else:
                continue
            docs.append(text)
    return docs

def embed_docs():
    texts = extract_text_from_docs("docs")
    metadatas = [{"source": f"doc_{i}"} for i in range(len(texts))]
    vector_db.add_texts(texts=texts, metadatas=metadatas)

if __name__ == "__main__":
    embed_docs()