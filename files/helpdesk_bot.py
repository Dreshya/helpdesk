from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import chromadb
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import psycopg2
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


# Use Ollama's Phi-3.5 as LLM
llm = OllamaLLM(model="phi3.5", temperature=0.7, max_tokens=50)  # Shorter responses

# Use Hugging Face embeddings (Explicitly specify model)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Ensure ChromaDB uses the correct persistent directory
chroma_client = chromadb.PersistentClient(path="db")

# Use Chroma's native LangChain wrapper
vector_db = Chroma(
    persist_directory="db",
    embedding_function=embedding_model
)

# Ensure documents are added properly
vector_db.add_texts(
    texts=["How do I reset my password?", "Where can I contact customer support?"],
    metadatas=[{"category": "password"}, {"category": "support"}],
    ids=["1", "2"]
)

# Set up retriever
retriever = vector_db.as_retriever(search_kwargs={"k": 2})  # k = max docs available


from langchain.prompts import PromptTemplate

# Define a prompt template for short, factual responses
qa_prompt = PromptTemplate.from_template(
    "Answer the following question using ONLY the retrieved documents. "
    "Keep your response short, to the point, and similar to how a customer service agent would reply. "
    "If you don't know, say 'I'm not sure, please contact support for more details.'\n\n"
    "Question: {question}\n\n"
    "Relevant Information: {context}\n\n"
    "Short Answer:"
)

# Create QA chain with custom prompt
qa = RetrievalQA.from_chain_type(
    llm=llm, 
    retriever=retriever,
    chain_type_kwargs={"prompt": qa_prompt}
)


# Enable logging for debugging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your actual bot token
TOKEN = "7400853171:AAFM5DVXu1w9Jx_mN3xgbP5SHfWFr3cK3kk"

# Define command handlers
async def start(update: Update, context: CallbackContext):
    """Send a welcome message when /start is issued."""
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. How can I assist you?")

# PostgreSQL connection setup
conn = psycopg2.connect(
    dbname="helpdesk",
    user="postgres",
    password="bot1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

async def handle_message(update: Update, context: CallbackContext):
    """Handle user messages."""
    user_id = update.message.chat_id
    user_message = update.message.text

    # Step 1: Retrieve relevant documents from ChromaDB
    results = retriever.invoke(user_message)

    # Step 2: Log the retrieved documents
    logger.info(f"Retrieved documents: {results}")

    # Step 3: If no relevant documents, return a default message
    if not results:
        await update.message.reply_text("I couldn't find related information. Please try rephrasing.")
        return

    # Step 4: Use retrieved data for RAG response with `run()`
    response_text = qa.run(user_message)  # `run()` ensures a clean text response

    # Store user query in PostgreSQL
    cursor.execute(
        "INSERT INTO queries (user_id, query, response, thread_id) VALUES (%s, %s, %s, %s)",
        (user_id, user_message, response_text, "thread_001")
    )
    conn.commit()

    # Step 5: Send the response to the user
    await update.message.reply_text(response_text)



# Main function to run the bot using polling
def main():
    """Start the bot."""
    app = Application.builder().token(TOKEN).build()

    # Add command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot using polling
    app.run_polling()

if __name__ == "__main__":
    main()
