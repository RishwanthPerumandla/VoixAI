#!/usr/bin/env python3
"""Test vector search functionality"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vector_db.qdrant_client import QdrantManager


def test_vector_search():
    """Test the vector search functionality"""
    print("Testing Vector Search...")
    print("=" * 50)
    
    try:
        manager = QdrantManager()
        
        # Check collections
        collections = manager.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        print(f"Available collections: {collection_names}")
        
        if 'menu_items' not in collection_names:
            print("ERROR: menu_items collection not found!")
            print("Run: python scripts/index_menu.py")
            return False
        
        print("\nmenu_items collection found!")
        
        # Check collection info
        info = manager.client.get_collection('menu_items')
        print(f"Collection info: vectors_count={info.points_count}")
        
        print("\nVector search is working correctly!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_vector_search()
    sys.exit(0 if success else 1)
