from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from settings import llm, get_retriever
from cachetools import TTLCache
from fuzzywuzzy import process
import logging
import re

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Cache ===
cache = TTLCache(maxsize=1000, ttl=3600)

# === Memory and Session per User ===
user_memories = {}
user_sessions = {}  # Tracks active doc_id per user

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

# === Response Cleaning ===
def clean_response(answer: str) -> str:
    answer = re.sub(r'[^\x20-\x7E\n]', '', answer.strip())
    answer = re.sub(r'\s+', ' ', answer)
    if answer and answer[-1] not in ".!?":
        answer += "."
    return answer[:4000]

# === Clear Cache and Memory ===
def clear_cache_and_memory():
    cache.clear()
    user_memories.clear()
    user_sessions.clear()
    logger.info("Cache, user memories, and sessions cleared.")

# === End Session ===
def end_session(user_id: str) -> str:
    if user_id in user_sessions:
        del user_sessions[user_id]
    if user_id in user_memories:
        del user_memories[user_id]
    logger.info(f"Session ended for user {user_id}")
    return "Session ended. Please specify a new project to start a new session."

# === Fuzzy Match Project Name ===
def get_closest_project_name(query: str, project_names: list, threshold: int = 80) -> str:
    # Extract the closest matching project name from the query
    match = process.extractOne(query, project_names)
    if match and match[1] >= threshold:
        logger.info(f"Fuzzy match found: {match[0]} for query '{query}' with score {match[1]}")
        return match[0]
    return None

# === Fetch Unique Project Names from Chroma ===
def get_project_names(retriever) -> list:
    try:
        # Fetch all documents without filtering to get unique doc_ids
        all_docs = retriever.vectorstore.similarity_search_with_score(
            query="",
            k=1000  # Large enough to get all documents; adjust as needed
        )
        project_names = list(set(doc.metadata.get("doc_id") for doc, _ in all_docs if doc.metadata.get("doc_id")))
        logger.info(f"Fetched project names from Chroma: {project_names}")
        return project_names
    except Exception as e:
        logger.error(f"Failed to fetch project names from Chroma: {e}")
        return []

# === Check if Query is Broad ===
def is_broad_query(query: str) -> bool:
    # Simple heuristic: query contains "details" or is short and generic
    query_lower = query.lower()
    return "details" in query_lower or len(query_lower.split()) <= 5

# === Handle Query ===
def answer_query(query: str, user_id: str, doc_id: str = None) -> str:
    # Check for session end command
    if query.lower().strip() in ["end session", "stop session", "exit"]:
        return end_session(user_id)

    # Initialize retriever to fetch project names
    try:
        retriever = get_retriever(doc_id or "default")
        project_names = get_project_names(retriever)
        if not project_names:
            logger.warning("No project names found in Chroma")
            return "No projects found in the documentation. Please specify a valid project name."
    except Exception as e:
        logger.error(f"Retriever initialization failed: {e}")
        return "Error accessing project documentation. Please try again later."

    # Check if user has an active session
    if user_id not in user_sessions:
        if not doc_id:
            matched_project = get_closest_project_name(query, project_names)
            if matched_project:
                doc_id = matched_project
                logger.info(f"Assigned doc_id '{doc_id}' based on fuzzy matching for query: {query}")
            else:
                logger.warning(f"No matching project found for query: {query}")
                return f"No project found matching '{query}'. Please specify a valid project name to start a session."
        elif doc_id not in project_names:
            logger.warning(f"Invalid doc_id provided: {doc_id}")
            return f"No project found matching '{doc_id}'. Please specify a valid project name to start a session."
        user_sessions[user_id] = doc_id
        logger.info(f"Started session for user {user_id} with doc_id: {doc_id}")
    else:
        # Check if query references a different project
        matched_project = get_closest_project_name(query, project_names)
        if matched_project and matched_project != user_sessions[user_id]:
            logger.info(f"User {user_id} attempted to query different project: {matched_project}")
            return f"Since you are enquiring about another project ('{matched_project}'), please end this session with 'end session' and start a new one."
        doc_id = user_sessions[user_id]

    cache_key = f"{user_id}:{doc_id}:{query}"
    if cache_key in cache:
        logger.info(f"Cache hit for {cache_key}")
        return cache[cache_key]

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

        if not docs_with_scores:
            logger.warning(f"No documents found for doc_id: {doc_id}")
            return f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details."

        # For broad queries, prioritize documents with ProjectInfo
        if is_broad_query(query):
            project_info_docs = [(doc, score) for doc, score in docs_with_scores if "ProjectInfo" in doc.page_content]
            if project_info_docs:
                most_relevant_doc = min(project_info_docs, key=lambda x: x[1])
                logger.info(f"Selected ProjectInfo document with score: {most_relevant_doc[1]}")
            else:
                most_relevant_doc = min(docs_with_scores, key=lambda x: x[1])
                logger.info(f"No ProjectInfo found, selected most relevant document with score: {most_relevant_doc[1]}")
        else:
            most_relevant_doc = min(docs_with_scores, key=lambda x: x[1])
            logger.info(f"Selected most relevant document with score: {most_relevant_doc[1]}")

        context = most_relevant_doc[0].page_content
 
    except Exception as e:
        logger.error(f"Retriever failed for doc_id {doc_id}: {e}")
        return f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details."

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
        return "Sorry, I'm having trouble connecting to the AI model. Try again later."

    # Clean and validate response
    answer = clean_response(raw_answer)
    if not answer or len(answer.strip()) < 10 or "sorry" in answer.lower() or "couldn't find" in answer.lower():
        logger.warning(f"Invalid or empty response: {answer}")
        answer = f"I couldn't find relevant information for '{doc_id}' in the documentation. Please clarify or provide more details."

    # Save to memory
    user_memories[user_id].save_context({"question": query}, {"answer": answer})

    cache[cache_key] = answer
    logger.info(f"Final response for user {user_id}: {answer}")
    return answer