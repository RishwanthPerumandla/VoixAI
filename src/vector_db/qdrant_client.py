"""
Qdrant Vector Database Client
Handles semantic search for menu items
"""

import json
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient as QdrantLib
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.config import settings


class QdrantManager:
    """
    Manager for Qdrant vector database
    Handles menu embeddings and semantic search
    """
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.client = QdrantLib(host=self.host, port=self.port)
        self.collection_name = "menu_items"
        self.vector_size = 384  # all-MiniLM-L6-v2 embedding size
    
    async def init_collection(self):
        """Initialize the menu_items collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"[Qdrant] Created collection: {self.collection_name}")
            else:
                print(f"[Qdrant] Collection exists: {self.collection_name}")
            
            return True
            
        except Exception as e:
            print(f"[Qdrant] Error initializing: {e}")
            return False
    
    async def index_menu_items(self, menu_items: List[Dict]):
        """
        Index menu items with embeddings
        
        Args:
            menu_items: List of menu items with name, description, category, etc.
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load embedding model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            points = []
            for idx, item in enumerate(menu_items):
                # Create text for embedding
                text = f"{item.get('name', '')} {item.get('description', '')} {item.get('category', '')}"
                
                # Generate embedding
                embedding = model.encode(text).tolist()
                
                # Create point
                point = PointStruct(
                    id=idx,
                    vector=embedding,
                    payload={
                        "name": item.get("name"),
                        "category": item.get("category"),
                        "price": item.get("price"),
                        "description": item.get("description"),
                        "allergens": item.get("allergens", []),
                        "spiciness": item.get("spiciness", "mild")
                    }
                )
                points.append(point)
            
            # Upsert points
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            print(f"[Qdrant] Indexed {len(points)} menu items")
            return True
            
        except Exception as e:
            print(f"[Qdrant] Error indexing: {e}")
            return False
    
    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Semantic search for menu items
        
        Args:
            query: Search query (e.g., "spicy wings", "something healthy")
            limit: Maximum results
            
        Returns:
            List of matching menu items with scores
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Generate query embedding
            query_vector = model.encode(query).tolist()
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            # Format results
            items = []
            for result in results:
                items.append({
                    "name": result.payload.get("name"),
                    "category": result.payload.get("category"),
                    "price": result.payload.get("price"),
                    "description": result.payload.get("description"),
                    "score": result.score,
                    "allergens": result.payload.get("allergens", []),
                    "spiciness": result.payload.get("spiciness", "mild")
                })
            
            return items
            
        except Exception as e:
            print(f"[Qdrant] Search error: {e}")
            return []
    
    async def hybrid_search(self, query: str, category: str = None, limit: int = 5) -> List[Dict]:
        """
        Hybrid search: semantic + keyword + filters
        
        Args:
            query: Search query
            category: Filter by category
            limit: Maximum results
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            query_vector = model.encode(query).tolist()
            
            # Build filter
            filter_condition = None
            if category:
                filter_condition = {
                    "must": [
                        {"key": "category", "match": {"value": category}}
                    ]
                }
            
            # Search with filter
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=filter_condition,
                limit=limit
            )
            
            items = []
            for result in results:
                items.append({
                    "name": result.payload.get("name"),
                    "category": result.payload.get("category"),
                    "price": result.payload.get("price"),
                    "description": result.payload.get("description"),
                    "score": result.score,
                    "allergens": result.payload.get("allergens", [])
                })
            
            return items
            
        except Exception as e:
            print(f"[Qdrant] Hybrid search error: {e}")
            return []
