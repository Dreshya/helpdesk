import psycopg2
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# PostgreSQL
conn = psycopg2.connect(
    dbname="helpdesk",
    user="postgres",
    password="bot1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

def save_query(user_id, query, response, thread_id):
    cursor.execute(
        "INSERT INTO queries (user_id, query, response, thread_id) VALUES (%s, %s, %s, %s)",
        (user_id, query, response, thread_id)
    )
    conn.commit()

# ChromaDB
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="db")
vector_db = Chroma(persist_directory="db", embedding_function=embedding_model)
retriever = vector_db.as_retriever(search_kwargs={"k": 2})
