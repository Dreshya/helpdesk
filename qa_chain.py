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

def answer_query(query: str) -> str:
    response = qa_chain.invoke({"query": query})
    return response["result"]
