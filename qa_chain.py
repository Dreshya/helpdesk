from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from settings import llm, get_retriever
from cachetools import TTLCache
import logging

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Memory per User ===
user_memories = {}

# === Cache ===
cache = TTLCache(maxsize=1000, ttl=3600)

# === Prompt Templates ===
prompt_template = PromptTemplate.from_template("""
You are a friendly, knowledgeable support buddy. Answer the user's question **in English only**, using the provided context from the specified document. Use the chat history to resolve references like "this" or "it" and maintain conversational context. Infer programming languages from frameworks (e.g., Django implies Python) and provide accurate, concise answers (up to 4 sentences). If the question is unclear or lacks context, say, "I'm not sure what you're referring to, can you clarify?" **All responses must be in English.**

Document Context:
{context}

Chat History:
{chat_history}

Current Question: {question}

Answer (in English):
""")

resolution_prompt = PromptTemplate.from_template("""
Based on the following answer, determine if the user's query was resolved (i.e., the answer fully addresses the question).
Return only "resolved" or "unresolved".

Answer: {answer}
""")

# === Response Cleaning ===
def clean_response(answer: str) -> str:
    answer = answer.strip().replace("\n\n", "\n").replace("Answer:", "")
    if answer and answer[-1] not in ".!?":
        answer += "."
    return answer

# === Handle Conversation-Aware Query ===
def answer_query(query: str, user_id: str, doc_id: str = None) -> tuple:
    cache_key = f"{user_id}:{doc_id}:{query}" if doc_id else f"{user_id}:{query}"
    if cache_key in cache:
        logger.info(f"Cache hit for {cache_key}")
        return cache[cache_key], None

    # Initialize memory for user if not exists
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Store up to 10 recent messages for context
        )

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=get_retriever(doc_id),
        memory=user_memories[user_id],
        combine_docs_chain_kwargs={"prompt": prompt_template}
    )
    
    try:
        response = qa_chain.invoke({"question": query})
        raw_answer = response["answer"]
        logger.info(f"Raw LLM response for user {user_id}: {raw_answer}")
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        return "Sorry, I'm having trouble connecting to the AI model. Try again later.", None

    answer = clean_response(raw_answer)
    if len(answer) > 4000:
        answer = answer[:4000] + "\n\n...(truncated)"
    logger.info(f"Cleaned response for user {user_id}: {answer}")

    # Check resolution using a simple LLMChain
    resolution_chain = LLMChain(
        llm=llm,
        prompt=resolution_prompt
    )
    try:
        resolution = resolution_chain.invoke({"answer": answer})["text"].strip()
    except Exception as e:
        logger.error(f"Resolution check failed: {e}")
        resolution = "unresolved"  # Default to unresolved if check fails
    
    cache[cache_key] = answer
    return answer, resolution