from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from search_engine import semantic_search

llm = OllamaLLM(model="phi3.5", temperature=0.7, max_tokens=50)

qa_prompt = PromptTemplate.from_template(
    "Answer the following question using ONLY the retrieved documents. "
    "Keep your response short, to the point, and similar to how a customer service agent would reply. "
    "If you don't know, say 'I'm not sure, please contact support for more details.'\n\n"
    "Question: {question}\n\n"
    "Relevant Information: {context}\n\n"
    "Short Answer:"
)

def generate_response(query):
    docs = semantic_search(query)
    context = "\n\n".join(docs)
    prompt = qa_prompt.format(question=query, context=context)
    return llm.invoke(prompt)