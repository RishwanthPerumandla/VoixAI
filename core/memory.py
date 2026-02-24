"""Memory Module - Short and long-term storage"""
import json
import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
import uuid


@dataclass
class CustomerProfile:
    """Customer profile with preferences"""
    name: str = ""
    phone: str = ""
    preferences: Dict = field(default_factory=dict)
    order_history: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WorkingMemory:
    """Session working memory"""
    session_id: str = ""
    customer_name: str = ""
    current_order: Dict = field(default_factory=dict)
    conversation_stage: str = "greeting"
    turns: List[Dict] = field(default_factory=list)
    offered_upsells: List[str] = field(default_factory=list)
    accepted_upsells: List[str] = field(default_factory=list)
    pending_modification: Optional[Dict] = None
    topics_discussed: List[str] = field(default_factory=list)
    customer_preferences: Dict = field(default_factory=dict)
    last_intent: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def add_turn(self, role: str, content: str, intent: str = ""):
        """Add a conversation turn"""
        self.turns.append({
            "role": role,
            "content": content,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 5 turns for working memory
        if len(self.turns) > 5:
            self.turns = self.turns[-5:]
    
    def get_context_for_llm(self) -> str:
        """Get recent conversation as context string"""
        if not self.turns:
            return ""
        
        context = []
        for turn in self.turns[-3:]:  # Last 3 turns
            role = "Customer" if turn["role"] == "user" else "Tasha"
            context.append(f"{role}: {turn['content']}")
        
        return "\n".join(context)


class MemoryManager:
    """Manages both working memory and long-term storage"""
    
    def __init__(self, db_path: str = "data/orders.db"):
        self.db_path = db_path
        self.working_memory: Dict[str, WorkingMemory] = {}  # session_id -> memory
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite tables"""
        with self._get_connection() as conn:
            # Customers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE,
                    name TEXT,
                    preferences TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visit TIMESTAMP
                )
            """)
            
            # Orders table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    session_id TEXT,
                    items TEXT,  -- JSON
                    total REAL,
                    status TEXT DEFAULT 'building',
                    special_instructions TEXT,
                    sentiment_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            """)
            
            # Conversation logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    order_id INTEGER,
                    turns TEXT,  -- JSON
                    intent_distribution TEXT,  -- JSON
                    sentiment_trajectory TEXT,  -- JSON
                    upsell_success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tickets table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT UNIQUE,
                    type TEXT,
                    description TEXT,
                    order_id INTEGER,
                    severity TEXT,
                    status TEXT DEFAULT 'open',
                    resolution TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        import os
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_session(self, session_id: str = None) -> str:
        """Create new session and return session_id"""
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        
        self.working_memory[session_id] = WorkingMemory(session_id=session_id)
        return session_id
    
    def get_memory(self, session_id: str) -> WorkingMemory:
        """Get working memory for session"""
        if session_id not in self.working_memory:
            self.create_session(session_id)
        return self.working_memory[session_id]
    
    def update_memory(self, session_id: str, updates: Dict):
        """Update working memory fields"""
        memory = self.get_memory(session_id)
        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
    
    def add_turn(self, session_id: str, role: str, content: str, intent: str = ""):
        """Add conversation turn to working memory"""
        memory = self.get_memory(session_id)
        memory.add_turn(role, content, intent)
    
    def get_or_create_customer(self, name: str = "", phone: str = "") -> int:
        """Get or create customer, return customer_id"""
        with self._get_connection() as conn:
            # Try to find by phone
            if phone:
                row = conn.execute(
                    "SELECT id FROM customers WHERE phone = ?",
                    (phone,)
                ).fetchone()
                if row:
                    return row["id"]
            
            # Create new customer
            cursor = conn.execute(
                "INSERT INTO customers (name, phone, preferences) VALUES (?, ?, ?)",
                (name, phone, '{}')
            )
            return cursor.lastrowid
    
    def update_customer_preferences(self, customer_id: int, preferences: Dict):
        """Update customer preferences"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE customers SET preferences = ? WHERE id = ?",
                (json.dumps(preferences), customer_id)
            )
    
    def get_customer_profile(self, customer_id: int) -> Optional[CustomerProfile]:
        """Get customer profile by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ?",
                (customer_id,)
            ).fetchone()
            
            if row:
                return CustomerProfile(
                    name=row["name"] or "",
                    phone=row["phone"] or "",
                    preferences=json.loads(row["preferences"] or '{}'),
                    created_at=row["created_at"]
                )
            return None
    
    def create_order(self, session_id: str, customer_id: int = None) -> int:
        """Create new order in database"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO orders (session_id, customer_id, items, status) VALUES (?, ?, ?, ?)",
                (session_id, customer_id, '[]', 'building')
            )
            return cursor.lastrowid
    
    def update_order(self, order_id: int, items: List[Dict], total: float = 0):
        """Update order items and total"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE orders SET items = ?, total = ? WHERE id = ?",
                (json.dumps(items), total, order_id)
            )
    
    def complete_order(self, order_id: int, instructions: str = ""):
        """Mark order as completed"""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE orders 
                   SET status = 'completed', 
                       completed_at = CURRENT_TIMESTAMP,
                       special_instructions = ?
                   WHERE id = ?""",
                (instructions, order_id)
            )
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "items": json.loads(row["items"] or '[]'),
                    "total": row["total"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"]
                }
            return None
    
    def create_ticket(self, ticket_type: str, description: str, 
                      order_id: int = None, severity: str = "medium") -> str:
        """Create support ticket"""
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO tickets 
                   (ticket_id, type, description, order_id, severity, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ticket_id, ticket_type, description, order_id, severity, 'open')
            )
        
        return ticket_id
    
    def save_conversation(self, session_id: str, order_id: int = None,
                         intent_distribution: Dict = None,
                         sentiment_trajectory: List = None):
        """Save complete conversation to database"""
        memory = self.get_memory(session_id)
        
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO conversations 
                   (session_id, order_id, turns, intent_distribution, sentiment_trajectory)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    order_id,
                    json.dumps(memory.turns),
                    json.dumps(intent_distribution or {}),
                    json.dumps(sentiment_trajectory or [])
                )
            )
    
    def get_order_history(self, customer_id: int, limit: int = 5) -> List[Dict]:
        """Get customer's order history"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM orders 
                   WHERE customer_id = ? AND status = 'completed'
                   ORDER BY completed_at DESC
                   LIMIT ?""",
                (customer_id, limit)
            ).fetchall()
            
            return [
                {
                    "id": row["id"],
                    "items": json.loads(row["items"] or '[]'),
                    "total": row["total"],
                    "completed_at": row["completed_at"]
                }
                for row in rows
            ]
    
    def clear_session(self, session_id: str):
        """Clear working memory for session"""
        if session_id in self.working_memory:
            del self.working_memory[session_id]
    
    def get_analytics(self) -> Dict:
        """Get conversation analytics"""
        with self._get_connection() as conn:
            # Total orders
            total_orders = conn.execute(
                "SELECT COUNT(*) as count FROM orders"
            ).fetchone()["count"]
            
            # Completed orders
            completed = conn.execute(
                "SELECT COUNT(*) as count FROM orders WHERE status = 'completed'"
            ).fetchone()["count"]
            
            # Average order value
            avg_order = conn.execute(
                "SELECT AVG(total) as avg FROM orders WHERE status = 'completed'"
            ).fetchone()["avg"] or 0
            
            # Open tickets
            open_tickets = conn.execute(
                "SELECT COUNT(*) as count FROM tickets WHERE status = 'open'"
            ).fetchone()["count"]
            
            return {
                "total_orders": total_orders,
                "completed_orders": completed,
                "completion_rate": completed / total_orders if total_orders > 0 else 0,
                "average_order_value": round(avg_order, 2),
                "open_tickets": open_tickets
            }
