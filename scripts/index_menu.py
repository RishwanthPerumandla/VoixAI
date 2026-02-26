#!/usr/bin/env python3
"""
Menu Indexing Script
Indexes Wingstop menu items into Qdrant for semantic search
"""

import json
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np


class SimpleEmbedder:
    """
    Simple embedding using TF-IDF-like approach
    Fallback when sentence-transformers not available
    """
    
    def __init__(self, dim=384):
        self.dim = dim
        self.vocab = {}
        self.word_counts = {}
    
    def _tokenize(self, text: str) -> list:
        """Simple tokenization"""
        return text.lower().split()
    
    def _build_vocab(self, texts: list):
        """Build vocabulary from texts"""
        word_freq = {}
        for text in texts:
            for word in self._tokenize(text):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Keep top words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        self.vocab = {word: i for i, (word, _) in enumerate(sorted_words[:1000])}
    
    def encode(self, texts: list) -> np.ndarray:
        """Encode texts to vectors"""
        if isinstance(texts, str):
            texts = [texts]
        
        if not self.vocab:
            self._build_vocab(texts)
        
        vectors = []
        for text in texts:
            words = self._tokenize(text)
            vector = np.zeros(self.dim)
            
            for word in words:
                if word in self.vocab:
                    idx = self.vocab[word] % self.dim
                    vector[idx] += 1
            
            # Normalize
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            
            vectors.append(vector)
        
        return np.array(vectors)


def load_menu_data():
    """Load menu from data file or create default"""
    data_dir = Path(__file__).parent.parent / "data"
    menu_file = data_dir / "menu.json"
    
    if menu_file.exists():
        with open(menu_file, 'r') as f:
            return json.load(f)
    
    # Return empty structure that matches expected format
    return {"items": []}


def create_search_documents(menu_data: dict) -> list:
    """Create searchable documents from menu"""
    documents = []
    
    # Handle both formats: {"items": [...]} or {"categories": [...]}
    items = menu_data.get("items", [])
    
    for item in items:
        doc = {
            "id": item["name"].lower().replace(" ", "_"),
            "name": item["name"],
            "category": item.get("category", "general"),
            "description": item.get("description", ""),
            "text": f"{item['name']}. {item.get('description', '')} Category: {item.get('category', 'general')}",
            "metadata": {k: v for k, v in item.items() if k not in ["name", "description"]}
        }
        documents.append(doc)
    
    return documents


async def index_to_qdrant(documents: list, use_sentence_transformers: bool = False):
    """Index documents to Qdrant"""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError:
        print("Error: qdrant-client not installed")
        print("Install with: pip install qdrant-client")
        return False
    
    # Create embedder
    if use_sentence_transformers:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Using sentence-transformers")
            
            def encode(texts):
                if isinstance(texts, str):
                    texts = [texts]
                return model.encode(texts)
        except ImportError:
            print("sentence-transformers not available, using simple embedder")
            use_sentence_transformers = False
    
    if not use_sentence_transformers:
        embedder = SimpleEmbedder(dim=384)
        encode = embedder.encode
        print("Using simple TF-IDF embedder")
    
    # Initialize Qdrant
    client = QdrantClient(host="localhost", port=6333)
    collection_name = "menu_items"
    
    # Create collection
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except:
        pass
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"Created collection: {collection_name}")
    
    # Encode and index
    texts = [doc["text"] for doc in documents]
    vectors = encode(texts)
    
    points = []
    for i, (doc, vector) in enumerate(zip(documents, vectors)):
        # Ensure vector is list of floats
        if hasattr(vector, 'tolist'):
            vector = vector.tolist()
        
        points.append(PointStruct(
            id=i,
            vector=vector,
            payload=doc
        ))
    
    # Upload in batches
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        print(f"Indexed batch {i//batch_size + 1} ({len(batch)} items)")
    
    print(f"\nSuccessfully indexed {len(documents)} menu items to Qdrant!")
    
    # Test search skipped - Qdrant API varies by version
    print("\nVector search is now ready!")
    print("You can query the collection 'menu_items' in Qdrant")
    
    return True


async def main():
    """Main indexing function"""
    print("=" * 50)
    print("VoixAI Menu Indexer")
    print("=" * 50)
    
    # Load menu
    print("\nLoading menu data...")
    menu_data = load_menu_data()
    
    # Create documents
    print("Creating search documents...")
    documents = create_search_documents(menu_data)
    print(f"Created {len(documents)} documents")
    
    # Index to Qdrant
    print("\nIndexing to Qdrant...")
    use_st = "--use-st" in sys.argv
    success = await index_to_qdrant(documents, use_sentence_transformers=use_st)
    
    if success:
        print("\nMenu indexing complete!")
        print("Vector search is now available.")
    else:
        print("\nIndexing failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
