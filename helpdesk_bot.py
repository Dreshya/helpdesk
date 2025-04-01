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
llm = OllamaLLM(model="phi3.5", temperature=0.7)  # Add any other parameters if needed

# Use Hugging Face embeddings (Explicitly specify model)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="db")
faq_collection = chroma_client.get_or_create_collection(name="faqs")

# Set up a retriever using ChromaDB
retriever = Chroma(persist_directory="db", embedding_function=embedding_model).as_retriever()

faq_collection.add(
    ids=["1", "2"],  # Unique IDs
    documents=["How do I reset my password?", "Where can I contact customer support?"],
    metadatas=[{"category": "password"}, {"category": "support"}]
)

test_query = "password reset"
results = retriever.get_relevant_documents(test_query)
print("Retrieved documents:", results)

# Create QA chain using Phi-3.5
qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# Enable logging for debugging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your actual bot token
TOKEN = "7400853171:AAErpgO0P4SaU4ADP_p7zMxjfT26dCE5JbE"

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
    results = retriever.get_relevant_documents(user_message)

    # Step 2: Log the retrieved documents
    logger.info(f"Retrieved documents: {results}")

    # Step 3: If no relevant documents, return a default message
    if not results:
        await update.message.reply_text("I couldn't find related information. Please try rephrasing.")
        return

    # Step 4: Use retrieved data for RAG response
    response = qa.run(user_message)

    # Store user query in PostgreSQL
    cursor.execute(
        "INSERT INTO queries (user_id, query, response, thread_id) VALUES (%s, %s, %s, %s)",
        (user_id, user_message, response, "thread_001")  # Thread ID for tracking
    )
    conn.commit()

    # Step 5: Send the response to the user
    await update.message.reply_text(response)


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
