from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="db")

# Load embedding model
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Load Chroma retriever
retriever = Chroma(persist_directory="db", embedding_function=embedding_model).as_retriever()

# Load LLM (Phi-3.5)
llm = OllamaLLM(model="phi3:3.5", temperature=0.7)

# Create QA Chain
qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# Test Phi-3.5 with a question
query = "How can I change my password?"
response = qa.run(query)

print(f"Bot Response: {response}")
