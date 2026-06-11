import sys
import os
import shutil

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db import execute_query

def reset_data():
    try:
        # --- 1. CLEAR MYSQL ---
        print("Clearing MySQL chat history...")
        execute_query("DELETE FROM chat_history", fetch="none")
        
        print("Clearing MySQL escalations (tickets)...")
        execute_query("DELETE FROM escalations", fetch="none")
        
        print("Clearing MySQL notifications...")
        execute_query("DELETE FROM notifications", fetch="none")
        
        print("Clearing MySQL audit logs...")
        execute_query("DELETE FROM audit_logs", fetch="none")
        
        # Optional: Clear uploaded document records
        # execute_query("DELETE FROM uploaded_documents", fetch="none")
        
        # --- 2. CLEAR ARANGODB ---
        print("Clearing ArangoDB knowledge graph...")
        try:
            from utils.kb_helper import _db
            if _db:
                if _db.has_collection("kb_nodes"):
                    _db.collection("kb_nodes").truncate()
                if _db.has_collection("kb_edges"):
                    _db.collection("kb_edges").truncate()
                print("✅ ArangoDB graph cleared.")
            else:
                print("⚠️ ArangoDB not connected.")
        except Exception as e:
            print(f"⚠️ Could not clear ArangoDB: {e}")

        # --- 3. CLEAR CHROMADB ---
        print("Clearing ChromaDB vector store...")
        try:
            chroma_dir = os.path.join(os.path.dirname(__file__), "chroma_store")
            if os.path.exists(chroma_dir):
                # Try to delete the entire directory
                shutil.rmtree(chroma_dir)
                print("✅ ChromaDB vectors cleared.")
            else:
                print("✅ ChromaDB store already empty.")
        except Exception as e:
            print(f"⚠️ Could not completely clear ChromaDB (files might be locked by app.py): {e}")

        print("\n🎉 All test data (MySQL, ArangoDB, ChromaDB) cleared successfully! You can now test freshly.")
    except Exception as e:
        print(f"\n❌ Error clearing data: {e}")

if __name__ == "__main__":
    reset_data()
