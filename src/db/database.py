"""
Unified Database Interface
Supports PostgreSQL with SQLite fallback for development
"""

import os
import json
import aiosqlite
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Conversation:
    id: str
    session_id: str
    customer_id: Optional[str]
    channel: str
    started_at: datetime
    status: str


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    timestamp: datetime


@dataclass
class Order:
    id: str
    conversation_id: str
    customer_id: Optional[str]
    items: List[Dict]
    total_amount: float
    status: str


class DatabaseInterface:
    """Abstract database interface"""
    
    async def connect(self) -> bool:
        raise NotImplementedError
    
    async def disconnect(self):
        raise NotImplementedError
    
    async def create_customer(self, name: str, phone: str = None, email: str = None) -> Dict:
        raise NotImplementedError
    
    async def create_conversation(self, session_id: str, customer_id: str = None, channel: str = 'web') -> Conversation:
        raise NotImplementedError
    
    async def save_message(self, conversation_id: str, role: str, content: str, **kwargs):
        raise NotImplementedError
    
    async def create_order(self, conversation_id: str, customer_id: Optional[str], 
                          items: List[Dict], total: float, order_type: str = 'pickup') -> Order:
        raise NotImplementedError
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Message]:
        raise NotImplementedError


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation for development"""
    
    def __init__(self, db_path: str = "data/voixai_v3.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> bool:
        """Initialize SQLite connection"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            await self._init_tables()
            print(f"[SQLite] Connected to {self.db_path}")
            return True
        except Exception as e:
            print(f"[SQLite] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        if self.conn:
            await self.conn.close()
            print("[SQLite] Disconnected")
    
    async def _init_tables(self):
        """Create tables if not exist"""
        # Conversations table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                customer_id TEXT,
                channel TEXT DEFAULT 'web',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        """)
        
        # Messages table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                latency_ms INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Orders table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                customer_id TEXT,
                items TEXT NOT NULL,
                total_amount REAL NOT NULL,
                tax_amount REAL,
                status TEXT DEFAULT 'pending',
                order_type TEXT DEFAULT 'pickup',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        await self.conn.commit()
    
    async def create_customer(self, name: str, phone: str = None, email: str = None) -> Dict:
        """Create a customer (simplified for SQLite)"""
        import uuid
        customer_id = str(uuid.uuid4())
        return {
            "id": customer_id,
            "name": name,
            "phone_number": phone,
            "email": email
        }
    
    async def create_conversation(self, session_id: str, customer_id: str = None, channel: str = 'web') -> Conversation:
        """Create a new conversation"""
        import uuid
        conv_id = str(uuid.uuid4())
        
        await self.conn.execute(
            """
            INSERT INTO conversations (id, session_id, customer_id, channel, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (conv_id, session_id, customer_id, channel)
        )
        await self.conn.commit()
        
        return Conversation(
            id=conv_id,
            session_id=session_id,
            customer_id=customer_id,
            channel=channel,
            started_at=datetime.now(),
            status='active'
        )
    
    async def save_message(self, conversation_id: str, role: str, content: str, **kwargs):
        """Save a message"""
        await self.conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, latency_ms)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, kwargs.get('latency_ms'))
        )
        await self.conn.commit()
    
    async def create_order(self, conversation_id: str, customer_id: Optional[str],
                          items: List[Dict], total: float, order_type: str = 'pickup') -> Order:
        """Create an order"""
        import uuid
        order_id = str(uuid.uuid4())
        
        await self.conn.execute(
            """
            INSERT INTO orders (id, conversation_id, customer_id, items, total_amount, order_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (order_id, conversation_id, customer_id, json.dumps(items), total, order_type)
        )
        await self.conn.commit()
        
        return Order(
            id=order_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            items=items,
            total_amount=total,
            status='pending'
        )
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Message]:
        """Get conversation messages"""
        cursor = await self.conn.execute(
            """
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()
        
        return [
            Message(
                id=str(row['id']),
                conversation_id=row['conversation_id'],
                role=row['role'],
                content=row['content'],
                timestamp=datetime.fromisoformat(row['timestamp'])
            )
            for row in rows
        ]


class HybridMemoryManager:
    """
    Three-tier memory with unified database interface
    """
    
    def __init__(self, use_postgres: bool = False):
        self.use_postgres = use_postgres
        self.db: DatabaseInterface = None
        self.working_memory: Dict[str, Dict] = {}
    
    async def init(self) -> bool:
        """Initialize database connection"""
        if self.use_postgres:
            try:
                # Try PostgreSQL first
                from src.db.postgres_client import PostgresClient
                self.db = PostgresClient()
                success = await self.db.connect()
                if success:
                    await self.db.init_tables()
                    print("[Memory] Using PostgreSQL")
                    return True
            except Exception as e:
                print(f"[Memory] PostgreSQL unavailable: {e}")
        
        # Fallback to SQLite
        self.db = SQLiteDatabase()
        success = await self.db.connect()
        if success:
            print("[Memory] Using SQLite")
        return success
    
    async def start_conversation(self, session_id: str, customer_name: str) -> Dict:
        """Start a new conversation"""
        # Create customer
        customer = await self.db.create_customer(name=customer_name)
        
        # Create conversation
        conversation = await self.db.create_conversation(
            session_id=session_id,
            customer_id=customer.get('id')
        )
        
        # Initialize working memory
        self.working_memory[session_id] = {
            'customer': customer,
            'conversation': conversation,
            'messages': [],
            'order': {'items': []}
        }
        
        return {
            'customer_id': customer['id'],
            'conversation_id': conversation.id,
            'session_id': session_id
        }
    
    async def add_message(self, session_id: str, role: str, content: str, **kwargs):
        """Add message to memory"""
        if session_id not in self.working_memory:
            return
        
        memory = self.working_memory[session_id]
        
        # Add to working memory
        memory['messages'].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now()
        })
        
        # Persist to database
        conversation_id = memory['conversation'].id
        await self.db.save_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            **kwargs
        )
    
    async def save_order(self, session_id: str, order_data: Dict):
        """Save order to database"""
        if session_id not in self.working_memory:
            return
        
        memory = self.working_memory[session_id]
        
        order = await self.db.create_order(
            conversation_id=memory['conversation'].id,
            customer_id=memory['customer'].get('id'),
            items=order_data.get('items', []),
            total=order_data.get('total', 0),
            order_type=order_data.get('order_type', 'pickup')
        )
        
        memory['order_db'] = order
        return order
    
    def get_context(self, session_id: str, limit: int = 10) -> str:
        """Get recent conversation context"""
        if session_id not in self.working_memory:
            return ""
        
        messages = self.working_memory[session_id]['messages'][-limit:]
        context = []
        for msg in messages:
            role = "Customer" if msg['role'] == 'user' else "Tasha"
            context.append(f"{role}: {msg['content']}")
        
        return "\n".join(context)
    
    async def end_conversation(self, session_id: str):
        """Clean up conversation memory"""
        if session_id in self.working_memory:
            del self.working_memory[session_id]


# Singleton instance
_memory_manager: Optional[HybridMemoryManager] = None


async def get_memory_manager() -> HybridMemoryManager:
    """Get or create memory manager singleton"""
    global _memory_manager
    if _memory_manager is None:
        # Check if PostgreSQL is configured
        use_postgres = os.getenv('USE_POSTGRES', 'false').lower() == 'true'
        _memory_manager = HybridMemoryManager(use_postgres=use_postgres)
        await _memory_manager.init()
    return _memory_manager
