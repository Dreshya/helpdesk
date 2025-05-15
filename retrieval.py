# === [1] Import Required Modules ===
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# === [2] Load Your Embeddings from ChromaDB ===
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma(
    persist_directory="./chroma_storage",  # Make sure this matches your embedding step
    collection_name="xml_knowledge",
    embedding_function=embedding_model
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# === [3] Load Phi-3.5 via Ollama ===
llm = Ollama(model="phi3.5", temperature=0.2)

# === [4] Define Custom Prompt to Prevent Hallucination ===
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are an intelligent support assistant. Answer the question using ONLY the information from the context below.
If the answer is not contained in the context, say "I don't know."

Context:
{context}

Question: {question}
"""
)

# === [5] Build the RetrievalQA Chain ===
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",  # "stuff" is fast and suitable for small contexts
    chain_type_kwargs={"prompt": prompt_template},
    return_source_documents=True  # Optional: lets you inspect retrieved sources
)

# === [6] Ask a Question and Get an Answer ===
def ask_question(query: str):
    result = qa_chain({"query": query})

    print("\n📌 Answer:")
    print(result["result"])

    print("\n📚 Retrieved Source Chunks:")
    for i, doc in enumerate(result["source_documents"]):
        print(f"\n--- Chunk {i+1} ---\n{doc.page_content.strip()}")

# === [7] Example Usage ===
if __name__ == "__main__":
    user_question = input("\n❓ Ask your question: ")
    ask_question(user_question)
