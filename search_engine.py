from database import retriever
from preprocess_docs import extract_text_from_docs

def semantic_search(query):
    relevant_docs = retriever.get_relevant_documents(query)
    if relevant_docs and any(len(doc.page_content.strip()) > 5 for doc in relevant_docs):
        print("Retrieved from chromadb : ", relevant_docs)
        return [doc.page_content for doc in relevant_docs]
    else:
        fallback_docs = extract_text_from_docs("docs/")
        filtered_docs = [doc for doc in fallback_docs if query.lower() in doc.lower()]
        print("Retrieved from markdown.")
        return filtered_docs[:2] if filtered_docs else fallback_docs[:1]