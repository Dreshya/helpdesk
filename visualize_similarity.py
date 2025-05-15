# === [1] Imports ===
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# === [2] Load Embedding Model and VectorStore ===
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma(
    persist_directory="./chroma_storage",
    collection_name="xml_knowledge",
    embedding_function=embedding_model
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Set k for top-k results

# === [3] Define Your Query ===
query = "What are the modules involved in this project and its uses?"

# === [4] Embed the Query and Retrieve Results ===
query_embedding = embedding_model.embed_query(query)
retrieved_docs = retriever.get_relevant_documents(query)

# === [5] Get All Stored Embeddings (Raw from Chroma) ===
collection = vectorstore._collection
all_embeddings = []
all_texts = []

# You can access raw documents and embeddings via Chroma client
docs = collection.get(include=["embeddings", "documents"])
for emb, text in zip(docs["embeddings"], docs["documents"]):
    all_embeddings.append(emb)
    all_texts.append(text)

# === [6] Add the Query Embedding ===
all_embeddings = np.array(all_embeddings)
all_embeddings_with_query = np.vstack([all_embeddings, query_embedding])
labels = ["Doc"] * len(all_embeddings) + ["Query"]

# === [7] Apply t-SNE for Dimensionality Reduction ===
num_embeddings = len(all_embeddings_with_query)
perplexity = min(5, num_embeddings - 1)
tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42) 
reduced_embeddings = tsne.fit_transform(all_embeddings_with_query)

# === [8] Plot the Embeddings ===
plt.figure(figsize=(10, 7))
for i, label in enumerate(labels):
    color = "red" if label == "Query" else "blue"
    plt.scatter(reduced_embeddings[i, 0], reduced_embeddings[i, 1], c=color, label=label if i == len(labels)-1 else "", alpha=0.7)

plt.title("t-SNE Visualization of Embedding Space")
plt.legend()
plt.grid(True)
plt.show()
