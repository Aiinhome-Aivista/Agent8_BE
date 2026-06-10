import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RAGService:
    def __init__(self):
        self.model_name = "BAAI/bge-small-en-v1.5"
        self.encoder = SentenceTransformer(self.model_name)
        
        # Persistent storage configuration
        self.persist_directory = r"d:\Agent-8\Agent8_BE\vectorstore\chroma_db"
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory)
            
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection_name = "policy_documents"
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Insurance policy documents for RAG"}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

    def ingest_document(self, document_id: str, text: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
        
        # Chunk text
        chunks = self.text_splitter.split_text(text)
        
        # Prepare for Chroma
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{**metadata, "document_id": document_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Encode chunks
        embeddings = self.encoder.encode(chunks).tolist()
        
        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=chunks
        )

    def search_documents(self, query: str, top_k: int = 5, similarity_threshold: float = 0.75):
        query_embedding = self.encoder.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # In Chroma, lower distance = higher similarity. 
        # Typically cosine distance or L2. Assume default L2 or handle threshold contextually.
        # Filtering manually based on distance/score if needed.
        filtered_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i]
                # Dummy threshold check (depends on distance metric used, let's assume valid results)
                # In production, distance mapping to similarity is metric-dependent.
                filtered_results.append({
                    "id": results['ids'][0][i],
                    "document": doc,
                    "metadata": results['metadatas'][0][i],
                    "distance": distance
                })
        return filtered_results
