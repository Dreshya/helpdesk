from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import os
import glob
import markdown
from bs4 import BeautifulSoup
import chromadb
import psycopg2

from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate

# === Disable OneDNN warnings ===
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# === Logging ===
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# === Load LLM & Embeddings ===
llm = OllamaLLM(model="phi3.5", temperature=0.7, max_tokens=50)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# === PostgreSQL Setup ===
conn = psycopg2.connect(
    dbname="helpdesk",
    user="postgres",
    password="bot1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# === Custom Prompt ===
qa_prompt = PromptTemplate.from_template(
    "Answer the following question using ONLY the retrieved documents. "
    "Keep your response short, to the point, and similar to how a customer service agent would reply. "
    "If you don't know, say 'I'm not sure, please contact support for more details.'\n\n"
    "Question: {question}\n\n"
    "Relevant Information: {context}\n\n"
    "Short Answer:"
)

# === Markdown/HTML Text Extraction ===
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

# === Preprocess & Embed Documents into ChromaDB ===
def populate_chromadb():
    doc_texts = extract_text_from_docs(doc_folder="docs/")
    if not doc_texts:
        print("No docs found.")
        return
    ids = [f"doc_{i}" for i in range(len(doc_texts))]
    client = chromadb.PersistentClient(path="db")
    collection = client.get_or_create_collection("helpdesk")
    collection.add(documents=doc_texts, ids=ids)

# === Semantic Search Setup ===
chroma_client = chromadb.PersistentClient(path="db")
vector_db = Chroma(persist_directory="db", embedding_function=embedding_model)
retriever = vector_db.as_retriever(search_kwargs={"k": 2})

# === Telegram Command Handlers ===
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. How can I assist you?")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_message = update.message.text

    # Step 1: Semantic search from ChromaDB
    relevant_docs = retriever.get_relevant_documents(user_message)
    if relevant_docs and any(len(doc.page_content.strip()) > 5 for doc in relevant_docs):
        logger.info("Sufficient semantic match found in ChromaDB")
        context_text = "\n\n".join([doc.page_content for doc in relevant_docs])
    else:
        # Step 2: Fallback to raw docs
        logger.info("No good match in ChromaDB — falling back to markdown/html docs")
        fallback_docs = extract_text_from_docs(doc_folder="docs/")
        filtered_docs = [doc for doc in fallback_docs if user_message.lower() in doc.lower()]
        context_text = "\n\n".join(filtered_docs[:2]) if filtered_docs else "\n\n".join(fallback_docs[:1])

    # Step 3: Generate LLM response
    prompt = qa_prompt.format(question=user_message, context=context_text)
    response_text = llm.invoke(prompt)

    # Step 4: Save to PostgreSQL
    cursor.execute(
        "INSERT INTO queries (user_id, query, response, thread_id) VALUES (%s, %s, %s, %s)",
        (user_id, user_message, response_text, "thread_001")
    )
    conn.commit()

    await update.message.reply_text(response_text)

# === Run the Bot ===
def main():
    print("Populating vector DB...")
    populate_chromadb()
    print("Starting bot...")

    app = Application.builder().token("7400853171:AAHZ5yw2iE9skXDRkel9TxrFS3eKfkGEMPg").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
