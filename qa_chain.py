from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from settings import llm, get_retriever
from cachetools import TTLCache
import logging
import re

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Cache ===
cache = TTLCache(maxsize=1000, ttl=3600)

# === Memory per User ===
user_memories = {}

# === Prompt Templates ===
prompt_template = PromptTemplate.from_template("""
You are a support bot answering **in English only** using **ONLY** the provided document context for ID '{doc_id}'. **Do not use external knowledge, assumptions, or general information.** Provide a concise answer (up to 4 sentences, max 200 words) directly based on the context. If the context does not contain specific details to answer the question (e.g., usage instructions, steps, or procedures), respond: "I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details."

Document Context:
{context}

Chat History:
{chat_history}

Current Question: {question}

Answer (in English):
""")

resolution_prompt = PromptTemplate.from_template("""
Based on the answer and question context, determine if the query was resolved (i.e., the answer provides specific, relevant details from the document context). If the answer is generic, lacks concrete instructions, or uses "I couldn't find relevant information," return "unresolved". Return "resolved" only if the answer directly addresses the question with context-specific details.

Question: {question}
Answer: {answer}
""")

# === Response Cleaning ===
def clean_response(answer: str) -> str:
    answer = re.sub(r'[^\x20-\x7E\n]', '', answer.strip())
    answer = re.sub(r'\s+', ' ', answer)
    if answer and answer[-1] not in ".!?":
        answer += "."
    return answer[:4000]

# === Clear Cache ===
def clear_cache_and_memory():
    cache.clear()
    user_memories.clear()
    logger.info("Cache and user memories cleared.")

# # === Check Content Relevance ===
# def is_content_relevant(content: str, query: str) -> bool:
#     """Check if content contains keywords relevant to usage instructions."""
#     usage_keywords = [
#         "use", "using", "login", "access", "step", "procedure", "instruction",
#         "guide", "how to", "navigate", "operate", "run", "execute", "interface"
#     ]
#     query_lower = query.lower()
#     content_lower = content.lower()
#     # Require at least one usage keyword in content and query
#     return any(keyword in query_lower for keyword in usage_keywords) and \
#            any(keyword in content_lower for keyword in usage_keywords)

# === Handle Query ===
# === Handle Query ===
def answer_query(query: str, user_id: str, doc_id: str = None) -> tuple:
    cache_key = f"{user_id}:{doc_id}:{query}" if doc_id else f"{user_id}:{query}"
    if cache_key in cache:
        logger.info(f"Cache hit for {cache_key}")
        return cache[cache_key], "resolved"

    # Initialize memory
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="question",
            k=5
        )

    # Fetch document from Chroma
    try:
        retriever = get_retriever(doc_id)
        docs_with_scores = retriever.vectorstore.similarity_search_with_score(
            query=query,
            k=15,
            filter={"doc_id": doc_id}  # Filter by doc_id in embedding_metadata
        )
        logger.info(f"Retrieved context for doc_id: {doc_id}, Documents: {len(docs_with_scores)}")
        for doc, score in docs_with_scores:
            logger.info(f"Doc content: {doc.page_content}, Metadata: {doc.metadata}, Score: {score}")

        relevant_docs = [doc for doc, score in docs_with_scores if score < 1.8]
        if not relevant_docs:
            logger.warning(f"No relevant documents found for doc_id: {doc_id}")
            return f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details.", "unresolved"

        context = " ".join([doc.page_content for doc in relevant_docs])

    except Exception as e:
        logger.error(f"Retriever failed for doc_id {doc_id}: {e}")
        return f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details.", "unresolved"

    # Generate answer using LLM
    qa_chain = LLMChain(
        llm=llm,
        prompt=prompt_template.partial(doc_id=doc_id or "unknown")
    )
    try:
        response = qa_chain.invoke({
            "question": query,
            "context": context,
            "chat_history": user_memories[user_id].load_memory_variables({})["chat_history"]
        })
        raw_answer = response["text"]
        logger.info(f"Raw LLM response for user {user_id}: {raw_answer}")
    except Exception as e:
        logger.error(f"LLM invocation failed for user {user_id}: {e}")
        return "Sorry, I'm having trouble connecting to the AI model. Try again later.", "unresolved"

    # Clean and validate response
    answer = clean_response(raw_answer)
    if not answer or len(answer.strip()) < 10 or "sorry" in answer.lower() or "couldn't find" in answer.lower():
        logger.warning(f"Invalid or empty response: {answer}")
        answer = f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details."
        resolution = "unresolved"
    else:
        resolution_chain = LLMChain(llm=llm, prompt=resolution_prompt)
        try:
            resolution = resolution_chain.invoke({"answer": answer, "question": query})["text"].strip()
        except Exception as e:
            logger.error(f"Resolution check failed: {e}")
            resolution = "unresolved"

    # Save to memory
    user_memories[user_id].save_context({"question": query}, {"answer": answer})

    cache[cache_key] = answer
    logger.info(f"Final response for user {user_id}: {answer}")
    return answer, resolution
