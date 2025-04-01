from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

qa = RetrievalQA.from_chain_type(llm=OpenAI(), retriever=db.as_retriever())

async def handle_message(update: Update, context: CallbackContext):
    user_query = update.message.text
    response = qa.run(user_query)
    await update.message.reply_text(response)
