from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import chromadb
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="db")
faq_collection = chroma_client.get_or_create_collection(name="faqs")

# Use Ollama's Phi-3.5 as LLM
llm = OllamaLLM(model="phi3.5", temperature=0.7)  # Add any other parameters if needed

# Use Hugging Face embeddings (Explicitly specify model)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Set up a retriever using ChromaDB
retriever = Chroma(persist_directory="db", embedding_function=embedding_model).as_retriever()

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

async def handle_message(update: Update, context: CallbackContext):
    """Handle user messages."""
    user_message = update.message.text
    response = qa.run(user_message)  # Query Phi-3.5
    #response = qa.invoke({"query": user_message})
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
