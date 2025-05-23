from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from settings import llm, retriever

# === Memory Object ===
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# === Prompt Template (Optional - default one works too) ===
prompt_template = PromptTemplate.from_template("""
You are an intelligent support assistant. Use the following conversation and context to answer the user's question.
Keep your answers short, clear, and casual — like you're chatting with a friend.
Answer using no more than 5 short sentences. Only use the provided context to answer the question. If you're unsure, say "I am not sure."

Context:
{context}

Chat History:
{chat_history}

Question: {question}
""")

# === Conversational QA Chain ===
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory,
    combine_docs_chain_kwargs={"prompt": prompt_template}
)

# === Handle Conversation-Aware Query ===
def answer_query(query: str) -> str:
    response = qa_chain.invoke({"question": query})
    answer = response["answer"]

    # Telegram limit is 4096 characters
    if len(answer) > 4000:
        return answer[:4000] + "\n\n...(truncated)"
    return answer

