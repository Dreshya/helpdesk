from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from settings import llm, retriever

# === Custom Prompt ===
prompt_template = PromptTemplate.from_template("""
You are an intelligent support assistant. Answer the question using ONLY the information from the context below.
Do not mention where the context was located in the documentation.
If the answer is not contained in the context, say "I am not sure."

Context:
{context}

Question: {question}
""")

# === QA Chain ===
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt_template},
    return_source_documents=True
)

# === In-Memory Cache ===
response_cache = {}

def answer_query(query: str) -> str:
    if query in response_cache:
        print(f"[CACHE HIT] Returning cached result for: {query}")
        return response_cache[query]

    print(f"[CACHE MISS] Running QA chain for: {query}")
    response = qa_chain.invoke({"query": query})
    result = response["result"]
    response_cache[query] = result  # Store in cache
    return result
