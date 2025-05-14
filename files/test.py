import chromadb
import json
import argparse

def inspect_chroma(
    db_path="./db",
    collection_name="company_docs",
    include_embeddings=False,
    filter_key=None,
    filter_value=None,
    export_file="chroma_dump.json"
):
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name=collection_name)

    # Prepare filter if provided
    where_clause = {filter_key: filter_value} if filter_key and filter_value else {}

    # Set what to include
    include_fields = ["documents", "metadatas"]
    if include_embeddings:
        include_fields.append("embeddings")

    # Query all data
    results = collection.get(where=where_clause, include=include_fields)

    # Display results
    print(f"Found {len(results['ids'])} records in collection '{collection_name}'\n")
    for i in range(len(results["ids"])):
        print(f"ID: {results['ids'][i]}")
        print(f"Document: {results['documents'][i]}")
        print(f"Metadata: {results['metadatas'][i]}")
        if include_embeddings:
            print(f"Embedding (first 5 dims): {results['embeddings'][i][:5]}...")
        print("-" * 40)

    # Optional export
    if export_file:
        with open(export_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults exported to {export_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect ChromaDB collection")
    parser.add_argument("--db_path", type=str, default="./chroma_db", help="Path to ChromaDB folder")
    parser.add_argument("--collection", type=str, required=True, help="Name of the collection")
    parser.add_argument("--include_embeddings", action="store_true", help="Include embeddings in the output")
    parser.add_argument("--filter_key", type=str, help="Metadata key to filter")
    parser.add_argument("--filter_value", type=str, help="Metadata value to filter")
    parser.add_argument("--export", type=str, help="File path to export results as JSON")

    args = parser.parse_args()

    inspect_chroma(
        db_path=args.db_path,
        collection_name=args.collection,
        include_embeddings=args.include_embeddings,
        filter_key=args.filter_key,
        filter_value=args.filter_value,
        export_file=args.export
    )
