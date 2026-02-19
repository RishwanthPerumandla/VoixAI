"""Basic tests for VoixAI components"""
import os
import sys

# Load environment variables before importing modules
from dotenv import load_dotenv
load_dotenv()

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.order_manager import OrderManager
from core.llm_agent import ConversationAgent, ConversationState


class TestOrderManager:
    """Test OrderManager functionality"""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database"""
        db_path = tmp_path / "test.db"
        return OrderManager(str(db_path))
    
    def test_create_order(self, db):
        """Test order creation"""
        order_id = db.create_order("test-session")
        assert order_id is not None
        assert order_id > 0
    
    def test_update_order_items(self, db):
        """Test updating order items"""
        order_id = db.create_order("test-session")
        items = [{"name": "wings", "qty": 10, "modifiers": "lemon pepper"}]
        db.update_order_items(order_id, items)
        
        order = db.get_order(order_id)
        assert order is not None
        assert order["total_items"] == 10
        assert len(order["items"]) == 1
    
    def test_complete_order(self, db):
        """Test order completion"""
        order_id = db.create_order("test-session")
        db.complete_order(order_id, "extra crispy")
        
        order = db.get_order(order_id)
        assert order["status"] == "completed"
        assert order["special_instructions"] == "extra crispy"


class TestConversationAgent:
    """Test ConversationAgent functionality"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        config = {
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.3,
            "max_tokens": 150
        }
        # Skip if no API key
        if not os.getenv("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")
        return ConversationAgent(config)
    
    def test_initial_state(self, agent):
        """Test initial state is GREETING"""
        summary = agent.get_order_summary()
        assert summary["state"] == "greeting"
        assert summary["total_items"] == 0
    
    def test_simple_confirmation(self, agent):
        """Test yes/no detection in CONFIRMING state"""
        # Force state to CONFIRMING
        agent.state = ConversationState.CONFIRMING
        agent.order_items = [{"name": "wings", "qty": 10}]
        
        # Test yes
        response, data = agent.process("yes")
        assert agent.state == ConversationState.CLOSING
        assert "confirmed" in response.lower() or "great" in response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
